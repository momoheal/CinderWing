"""任务事件通知气泡：在宠物上方弹出，明确写出任务发生了什么。

- 五类事件：START / PROGRESS / WAITING / DONE / FAIL
- 每个任务带一条实时进度条（0–100%），进度更新走 update_progress()，
  只重绘、不打断宠物动作；
- 气泡里同时可能有多个任务：点击气泡展开“任务进度”面板，列出全部
  任务及其进度条，再点一次收起；
- 同一任务的新事件立即替换当前内容；不同任务都在面板里可见；
- 气泡尾巴与框体是同一条连续轮廓（融合，不画单独三角）。
"""
import time
from dataclasses import dataclass, field

from PySide6.QtCore import Qt, QTimer, QRect, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QFont, QPen, QFontMetrics
from PySide6.QtWidgets import QApplication, QWidget

MAX_WIDTH = 340
PANEL_WIDTH = 372
MIN_WIDTH = 220
MARGIN = 14
LINE_GAP = 4
TAIL_W = 16
TAIL_H = 10
RADIUS = 12
BAR_H = 8
BTN_PAD_V = 7       # 决策按钮上下内边距
BTN_GAP = 6         # 按钮间距
BTN_R = 9
BTN_MIN_H = 34

ACTIVE_MS = 12000        # 运行中的任务，最后一次更新后气泡停留时长
WAITING_MS = 20000       # “需要你决策”停留更久
TERMINAL_MS = 8000       # 完成 / 失败提示停留时长
SWEEP_MS = 500

BG = QColor(38, 38, 44, 246)
TEXT = QColor(240, 240, 242)
SUBTLE = QColor(176, 176, 184)
TRACK = QColor(66, 66, 74)

KINDS = {
    "START":    ("任务开始", QColor(255, 159, 84)),
    "PROGRESS": ("任务进度", QColor(255, 206, 84)),
    "WAITING":  ("需要你决策", QColor(255, 99, 99)),
    "DONE":     ("任务完成", QColor(108, 214, 139)),
    "FAIL":     ("任务失败", QColor(255, 99, 99)),
}
TERMINAL_KINDS = ("DONE", "FAIL")
ACTIVE_KINDS = ("START", "PROGRESS", "WAITING")


@dataclass
class Task:
    key: str
    name: str
    kind: str
    body: str
    progress: float | None = None
    updated: float = field(default_factory=time.monotonic)
    conv_id: str | None = None
    section_id: str | None = None
    # 决策点（interaction_ask_block，10082）结构化内容：
    # {"questions": [{"title", "type"(1单选/2多选/3自由文本),
    #                 "options": [{"id","label"}], "allow_text": bool}]}
    ask: dict | None = None

    @property
    def terminal(self):
        return self.kind in TERMINAL_KINDS

    @property
    def color(self):
        return KINDS[self.kind][1]

    @property
    def title(self):
        return KINDS[self.kind][0]

    @property
    def jumpable(self):
        """有真实会话 id（数字串）才能点气泡跳过去。"""
        return bool(self.conv_id and str(self.conv_id).isdigit())

    def ask_buttons(self):
        """把决策问题展平成按钮列表：[("option"|"free", 文案)]。

        答案必须在豆包工作客户端里提交（其内部 IM 通道外部无法代发），
        所以每个按钮点击后都是跳到对应会话，由用户在客户端点最后一下。"""
        out = []
        if not self.ask:
            return out
        for q in self.ask.get("questions", []):
            opts = q.get("options") or []
            for o in opts:
                label = (o.get("label") or "").strip()
                if label:
                    out.append(("option", label))
            if not opts or q.get("allow_text"):
                out.append(("free",
                            "打开豆包，输入自定义回答 →" if not opts
                            else "自定义回答…"))
        return out


def _wrap(text, font, max_w):
    fm = QFontMetrics(font)
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        trial = cur + ch
        if fm.horizontalAdvance(trial) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _elide(text, font, max_w):
    fm = QFontMetrics(font)
    if fm.horizontalAdvance(text) <= max_w:
        return text
    out = text
    while out and fm.horizontalAdvance(out + "…") > max_w:
        out = out[:-1]
    return out + "…"


class Bubble(QWidget):
    # kind when a NEW event state should trigger a pet reaction;
    # "" when the bubble disappears. Pure progress repaints do not emit.
    state_changed = Signal(str)
    # 用户点击了可跳转的任务（需要决策的任务或面板里的任务行），
    # 参数为任务 key；由主窗口接到后调 activator 打开豆包会话。
    jump_requested = Signal(str)

    def __init__(self, pet_window):
        super().__init__()
        self._pet = pet_window
        self.tasks: dict[str, Task] = {}
        self._showing = False
        self._expanded = False
        self._featured: str | None = None
        self._last_state = ""
        self._row_rects: dict[str, QRect] = {}  # 多任务面板每行的热区
        self._opt_rects: list[QRect] = []       # 决策选项按钮热区
        self._hover_opt = -1
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide)

        self._sweep = QTimer(self)
        self._sweep.setInterval(SWEEP_MS)
        self._sweep.timeout.connect(self._sweep_tasks)
        self._sweep.start()

    # ---------- 对外接口 ----------
    def notify(self, kind: str, body: str, key: str = "default",
               name: str | None = None, progress: float | None = None,
               conv_id: str | None = None, section_id: str | None = None,
               ask: dict | None = None):
        """报告一个任务事件（状态节点）。同 key 立即更新，不排队。"""
        now = time.monotonic()
        old = self.tasks.get(key)
        kind_changed = old is None or old.kind != kind
        if old is None:
            prog = None if progress is None else float(progress)
            task = Task(key, name or key, kind, body, prog, now,
                        conv_id, section_id, ask)
            if kind == "DONE":
                task.progress = 100.0
            self.tasks[key] = task
        else:
            old.kind = kind
            old.body = body
            old.updated = now
            if name:
                old.name = name
            if progress is not None:
                old.progress = float(progress)
            if conv_id:
                old.conv_id = conv_id
                old.section_id = section_id
            if ask is not None:
                old.ask = ask
            if kind == "DONE":
                old.progress = 100.0
        if kind in ACTIVE_KINDS and self.tasks[key].progress is None:
            self.tasks[key].progress = 0.0
        self._featured = self._pick_featured()
        self._show(kind_changed and kind != self._last_state, kind)
        self._restart_hide_timer()

    def show_panel(self) -> bool:
        """右键菜单入口：展开多任务进度面板。没有任务时返回 False。"""
        if not self.tasks:
            return False
        self._featured = self._pick_featured()
        self._showing = True
        self._expanded = True
        self._hide_timer.stop()
        self._render()
        return True

    def update_progress(self, key: str, percent: float, body: str | None = None,
                        conv_id: str | None = None, section_id: str | None = None):
        """实时进度：只更新数字和状态文字，不触发宠物新动作。"""
        task = self.tasks.get(key)
        if task is None or task.terminal:
            return
        task.progress = max(0.0, min(100.0, float(percent)))
        if body:
            task.body = body
        if conv_id:
            task.conv_id = conv_id
            task.section_id = section_id
        task.updated = time.monotonic()
        self._featured = self._pick_featured()
        if not self._showing:
            self._show(True, task.kind)
        else:
            self._render()
        if not self._expanded:
            self._restart_hide_timer()

    def clear(self):
        self.tasks.clear()
        self._expanded = False
        self._featured = None
        self._hide_timer.stop()
        self._showing = False
        self.hide()
        self._emit("")

    # ---------- 内部 ----------
    def _emit(self, kind):
        if kind != self._last_state:
            self._last_state = kind
            self.state_changed.emit(kind)

    def _show(self, should_emit, kind):
        self._showing = True
        self._render()
        if should_emit:
            self._emit(kind)

    def _restart_hide_timer(self):
        if self._expanded:
            self._hide_timer.stop()
            return
        t = self.tasks.get(self._featured) if self._featured else None
        if t is None:
            return
        if t.kind == "WAITING":
            # 决策点必须一直挂着等用户处理，不能自动消失
            self._hide_timer.stop()
        elif t.terminal:
            self._hide_timer.start(TERMINAL_MS)
        else:
            self._hide_timer.start(ACTIVE_MS)

    def _hide(self):
        self._showing = False
        self._expanded = False
        self.hide()
        self._emit("")

    def _sweep_tasks(self):
        now = time.monotonic()
        expired = [k for k, t in self.tasks.items()
                   if t.terminal and now - t.updated > TERMINAL_MS / 1000]
        for k in expired:
            del self.tasks[k]
        if not expired:
            return
        if self._featured not in self.tasks:
            self._featured = self._pick_featured()
        if self._featured is None:
            if self._showing:
                self._hide()
        elif self._showing:
            self._render()
            t = self.tasks[self._featured]
            if not t.terminal:
                # an active task is back in the spotlight: resume talking
                self._emit(t.kind)

    def _pick_featured(self):
        if not self.tasks:
            return None
        tasks = list(self.tasks.values())
        # urgency: needs-decision first, then fresh finish/failure notices,
        # then whatever active task updated most recently
        waiting = [t for t in tasks if t.kind == "WAITING"]
        if waiting:
            return max(waiting, key=lambda t: t.updated).key
        terminal = [t for t in tasks if t.terminal]
        if terminal:
            return max(terminal, key=lambda t: t.updated).key
        return max(tasks, key=lambda t: t.updated).key

    def _ordered_tasks(self):
        return sorted(self.tasks.values(), key=lambda t: t.updated, reverse=True)

    def _render(self):
        self._featured = self._pick_featured()
        self._resize_to_content()
        self._position()
        self.show()
        self.raise_()
        self.update()

    # ---------- 尺寸 ----------
    def _fonts(self):
        f_title = QFont(); f_title.setPointSize(9); f_title.setBold(True)
        f_body = QFont(); f_body.setPointSize(10)
        f_name = QFont(); f_name.setPointSize(8)
        f_hint = QFont(); f_hint.setPointSize(8)
        return f_title, f_body, f_name, f_hint

    def _collapsed_items(self, t, inner_w, f_body, f_hint):
        """折叠态的有序绘制/测量序列：

        ("lines", 行列表)  正文或问题标题
        ("space", px)      垂直留白
        ("bar",)           进度条
        ("button", 类型, 文案, 行数, 高度)
        ("hint", 文案)
        """
        hb = QFontMetrics(f_body).height()
        items = []
        if t.kind == "WAITING" and t.ask:
            for q in t.ask.get("questions", []):
                items.append(("lines",
                              _wrap(q.get("title") or "请回答以下问题",
                                    f_body, inner_w)))
                items.append(("space", 4))
                opts = q.get("options") or []
                for o in opts:
                    label = (o.get("label") or "").strip()
                    if not label:
                        continue
                    lines = _wrap(label, f_body, inner_w - 24)
                    h = max(BTN_MIN_H,
                            BTN_PAD_V * 2 + len(lines) * (hb + 1))
                    items.append(("button", "option", label, lines, h))
                if not opts or q.get("allow_text"):
                    label = ("打开豆包，输入自定义回答 →" if not opts
                             else "自定义回答…")
                    lines = _wrap(label, f_body, inner_w - 24)
                    h = max(BTN_MIN_H,
                            BTN_PAD_V * 2 + len(lines) * (hb + 1))
                    items.append(("button", "free", label, lines, h))
                items.append(("space", 6))
            if t.progress is not None:
                items.append(("bar",))
            items.append(("hint", "点击选项 → 打开豆包，在里面确认发送"))
            return items
        # 普通事件：正文 + 进度条 + 底部提示
        items.append(("lines", _wrap(t.body, f_body, inner_w)))
        if t.progress is not None:
            items.append(("space", 8))
            items.append(("bar",))
        if t.kind == "WAITING" and t.jumpable:
            items.append(("hint", "点击打开豆包，去处理决策 →"))
        elif len(self.tasks) > 1:
            items.append(("hint", "点击查看全部任务"))
        return items

    def _resize_to_content(self):
        f_title, f_body, f_name, f_hint = self._fonts()
        hb, hh, hn, hhint = (QFontMetrics(f).height() for f in
                             (f_title, f_body, f_name, f_hint))
        width = MIN_WIDTH
        if self._expanded:
            width = PANEL_WIDTH
        else:
            t = self.tasks.get(self._featured) if self._featured else None
            if t:
                if t.kind == "WAITING" and t.ask:
                    widest = 0
                    for q in t.ask.get("questions", []):
                        widest = max(widest, max(
                            (QFontMetrics(f_body).horizontalAdvance(l)
                             for l in _wrap(q.get("title") or "",
                                            f_body, MAX_WIDTH - 2 * MARGIN)),
                            default=0))
                        for o in q.get("options") or []:
                            for l in _wrap((o.get("label") or ""),
                                          f_body, MAX_WIDTH - 2 * MARGIN - 24):
                                widest = max(widest,
                                             QFontMetrics(f_body)
                                             .horizontalAdvance(l) + 24)
                    width = max(MIN_WIDTH, min(MAX_WIDTH,
                                               widest + 2 * MARGIN + 24))
                else:
                    lines = _wrap(t.body, f_body, MAX_WIDTH - 2 * MARGIN)
                    body_w = max((QFontMetrics(f_body).horizontalAdvance(l)
                                  for l in lines), default=0)
                    name_w = QFontMetrics(f_name).horizontalAdvance(t.name) + 70
                    width = max(MIN_WIDTH, min(MAX_WIDTH,
                                               max(body_w, name_w) + 2 * MARGIN))
        h = MARGIN + hh + 6
        if self._expanded:
            for t in self._ordered_tasks():
                h += max(46, hh + hn + 18)
            h += hhint + 6
        else:
            t = self.tasks.get(self._featured) if self._featured else None
            if t:
                inner_w = width - 2 * MARGIN
                for it in self._collapsed_items(t, inner_w, f_body, f_hint):
                    kind = it[0]
                    if kind == "lines":
                        h += len(it[1]) * (hb + LINE_GAP)
                    elif kind == "space":
                        h += it[1]
                    elif kind == "bar":
                        h += 14 + BAR_H
                    elif kind == "button":
                        h += it[4] + BTN_GAP
                    elif kind == "hint":
                        h += hhint + 8
        h += MARGIN + TAIL_H
        self.resize(width, int(h))

    def _position(self):
        pr = self._pet.geometry()
        center = pr.center()
        screen = (QApplication.screenAt(center) or self._pet.screen()
                  or self.screen())
        sg = screen.availableGeometry()
        x = center.x() - self.width() // 2
        y = pr.top() - self.height() - 6
        x = max(sg.left() + 8, min(x, sg.right() - self.width() - 8))
        self._tail_top = False
        if y < sg.top() + 4:
            y = pr.bottom() + 6
            self._tail_top = True
        self.move(x, y)

    def reposition(self):
        if self._showing:
            self._position()

    # ---------- 绘制 ----------
    def _bubble_path(self, w, h):
        """框体 + 尾巴的单条连续外轮廓（描边不会在尾巴根部产生接缝）。"""
        r = RADIUS
        if self._tail_top:
            bb = TAIL_H  # body bottom
            top = TAIL_H
            cx = max(r + TAIL_W // 2, min(w - r - TAIL_W // 2, w // 2))
            path = QPainterPath()
            path.moveTo(r, top)
            path.lineTo(cx - TAIL_W // 2, top)
            path.lineTo(cx, 0)
            path.lineTo(cx + TAIL_W // 2, top)
            path.lineTo(w - r, top)
            path.arcTo(QRectF(w - 2 * r, top, 2 * r, 2 * r), -90, 90)
            path.lineTo(w, h - r)
            path.arcTo(QRectF(w - 2 * r, h - 2 * r, 2 * r, 2 * r), 0, 90)
            path.lineTo(r, h)
            path.arcTo(QRectF(0, h - 2 * r, 2 * r, 2 * r), 90, 90)
            path.lineTo(0, top + r)
            path.arcTo(QRectF(0, top, 2 * r, 2 * r), 180, 90)
            path.closeSubpath()
            return path
        bb = h - TAIL_H
        cx = max(r + TAIL_W // 2, min(w - r - TAIL_W // 2, w // 2))
        path = QPainterPath()
        path.moveTo(cx - TAIL_W // 2, bb)
        path.lineTo(cx, h)
        path.lineTo(cx + TAIL_W // 2, bb)
        path.lineTo(w - r, bb)
        path.arcTo(QRectF(w - 2 * r, bb - 2 * r, 2 * r, 2 * r), -90, 90)
        path.lineTo(w, r)
        path.arcTo(QRectF(w - 2 * r, 0, 2 * r, 2 * r), 0, 90)
        path.lineTo(r, 0)
        path.arcTo(QRectF(0, 0, 2 * r, 2 * r), 90, 90)
        path.lineTo(0, bb - r)
        path.arcTo(QRectF(0, bb - 2 * r, 2 * r, 2 * r), 180, 90)
        path.closeSubpath()
        return path

    def _bar(self, p, rect: QRect, color: QColor, percent: float | None):
        p.setPen(Qt.NoPen)
        p.setBrush(TRACK)
        p.drawRoundedRect(rect, 4, 4)
        if percent is None:
            return
        fill_w = int(rect.width() * max(0.0, min(1.0, percent / 100.0)))
        if fill_w > 2:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(rect), 4, 4)
            p.save()
            p.setClipPath(clip)
            p.setBrush(color)
            p.drawRect(QRect(rect.left(), rect.top(), fill_w, rect.height()))
            p.restore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        f_title, f_body, f_name, f_hint = self._fonts()

        featured = self.tasks.get(self._featured) if self._featured else None
        accent = featured.color if featured else KINDS["PROGRESS"][1]
        self._row_rects = {}
        path = self._bubble_path(self.width(), self.height())
        p.setPen(Qt.NoPen)
        p.setBrush(BG)
        p.drawPath(path)
        p.setPen(QPen(accent, 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        x = MARGIN
        y = MARGIN
        inner_w = self.width() - 2 * MARGIN

        if self._expanded:
            p.setFont(f_title)
            p.setPen(accent)
            p.drawText(QRect(x, y - 2, inner_w * 0.6, QFontMetrics(f_title).height()),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       f"任务进度（{len(self.tasks)}）")
            p.setFont(f_hint)
            p.setPen(SUBTLE)
            p.drawText(QRect(x + int(inner_w * 0.4), y - 2, int(inner_w * 0.6),
                             QFontMetrics(f_hint).height()),
                       Qt.AlignRight | Qt.AlignVCenter, "点任务打开 · 空白收起")
            y += QFontMetrics(f_title).height() + 6
            self._row_rects = {}
            for t in self._ordered_tasks():
                row_h = max(46, QFontMetrics(f_body).height()
                            + QFontMetrics(f_name).height() + 18)
                self._row_rects[t.key] = QRect(x, y, inner_w, row_h)
                self._paint_row(p, t, x, y, inner_w, f_body, f_name)
                y += row_h
            p.end()
            return

        if featured is None:
            p.end()
            return

        # header: kind title (left, colored) + task name (right, subtle)
        p.setFont(f_title)
        p.setPen(accent)
        p.drawText(QRect(x, y - 2, inner_w * 0.55,
                         QFontMetrics(f_title).height()),
                   Qt.AlignLeft | Qt.AlignVCenter, featured.title)
        p.setFont(f_name)
        p.setPen(SUBTLE)
        name = _elide(featured.name, f_name, int(inner_w * 0.55))
        p.drawText(QRect(x + int(inner_w * 0.45), y - 2, int(inner_w * 0.55),
                         QFontMetrics(f_name).height()),
                   Qt.AlignRight | Qt.AlignVCenter, name)
        y += QFontMetrics(f_title).height() + 6

        self._opt_rects = []
        fm = QFontMetrics(f_body)
        fhint_h = QFontMetrics(f_hint).height()
        btn_idx = 0
        for it in self._collapsed_items(featured, inner_w, f_body, f_hint):
            kind = it[0]
            if kind == "lines":
                p.setFont(f_body)
                p.setPen(TEXT)
                for line in it[1]:
                    p.drawText(QRect(x, y, inner_w, fm.height() + 2),
                               Qt.AlignLeft | Qt.AlignVCenter, line)
                    y += fm.height() + LINE_GAP
            elif kind == "space":
                y += it[1]
            elif kind == "bar":
                bar_rect = QRect(x, y + 2, inner_w - 46, BAR_H)
                self._bar(p, bar_rect, featured.color, featured.progress)
                p.setFont(f_name)
                p.setPen(TEXT)
                pct = 0 if featured.progress is None else featured.progress
                p.drawText(QRect(x + inner_w - 42, y - 1, 42, BAR_H + 6),
                           Qt.AlignRight | Qt.AlignVCenter,
                           f"{int(round(pct))}%")
                y += 14 + BAR_H
            elif kind == "button":
                _, bkind, label, lines, bh = it
                rect = QRect(x, y, inner_w, bh)
                self._opt_rects.append(rect)
                hover = (btn_idx == self._hover_opt)
                p.setPen(QPen(QColor(255, 122, 122) if bkind == "option"
                              else QColor(150, 150, 158), 1.2))
                p.setBrush(QColor(255, 99, 99, 58 if hover else 34)
                           if bkind == "option"
                           else QColor(255, 255, 255, 26 if hover else 14))
                p.drawRoundedRect(rect, BTN_R, BTN_R)
                p.setFont(f_body)
                p.setPen(TEXT if bkind == "option" else SUBTLE)
                ty = y + BTN_PAD_V
                for line in lines:
                    p.drawText(QRect(x + 12, ty, inner_w - 24,
                                     fm.height() + 1),
                               Qt.AlignLeft | Qt.AlignVCenter, line)
                    ty += fm.height() + 1
                y += bh + BTN_GAP
                btn_idx += 1
            elif kind == "hint":
                p.setFont(f_hint)
                p.setPen(QColor(255, 138, 138)
                         if featured.kind == "WAITING" else SUBTLE)
                p.drawText(QRect(x, y + 2, inner_w, fhint_h),
                           Qt.AlignLeft | Qt.AlignVCenter, it[1])
                y += fhint_h + 8
        p.end()

    def _paint_row(self, p, t: Task, x, y, w, f_body, f_name):
        hb, hn = QFontMetrics(f_body).height(), QFontMetrics(f_name).height()
        p.setPen(Qt.NoPen)
        p.setBrush(t.color)
        p.drawEllipse(QRect(x, y + 2, 8, 8))
        p.setFont(f_name)
        p.setPen(TEXT)
        p.drawText(QRect(x + 14, y, w - 70, hn),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   _elide(t.name, f_name, w - 70))
        pct = "" if t.progress is None else f"{int(round(t.progress))}%"
        p.drawText(QRect(x + w - 52, y, 52, hn),
                   Qt.AlignRight | Qt.AlignVCenter, pct)
        p.setFont(f_body)
        p.setPen(SUBTLE)
        p.drawText(QRect(x + 14, y + hn, w - 14, hb),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   _elide(t.body, f_body, w - 14))
        bar_y = y + hn + hb + 3
        self._bar(p, QRect(x + 14, bar_y, w - 14, 6), t.color,
                  t.progress if t.progress is not None else 0.0)

    # ---------- 鼠标：点任务跳转 / 展开多任务面板 ----------
    def _row_at(self, pos):
        for key, rect in self._row_rects.items():
            if rect.contains(pos):
                return key
        return None

    def mouseMoveEvent(self, event):
        # 悬停在手型热区上给光标反馈
        pos = event.position().toPoint()
        hand = False
        self._hover_opt = -1
        if self._expanded:
            key = self._row_at(pos)
            hand = bool(key and self.tasks.get(key)
                        and self.tasks[key].jumpable)
        else:
            t = self.tasks.get(self._featured) if self._featured else None
            if t and t.kind == "WAITING":
                for i, r in enumerate(self._opt_rects):
                    if r.contains(pos):
                        self._hover_opt = i
                hand = bool(t.jumpable)
        if self._hover_opt >= 0:
            self.update()
        self.setCursor(Qt.PointingHandCursor if hand else Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.position().toPoint()

        if self._expanded:
            key = self._row_at(pos)
            task = self.tasks.get(key) if key else None
            if task and task.jumpable:
                self.jump_requested.emit(task.key)
                return
            # 点空白：收起面板
            self._expanded = False
            self._render()
            self._restart_hide_timer()
            return

        featured = self.tasks.get(self._featured) if self._featured else None
        # 需要决策的任务：点气泡直接打开豆包对应会话
        if featured and featured.kind == "WAITING" and featured.jumpable:
            self.jump_requested.emit(featured.key)
            return
        # 其他情况：展开/收起多任务面板
        self._expanded = not self._expanded
        self._render()
        if self._expanded:
            self._hide_timer.stop()
        else:
            self._restart_hide_timer()
