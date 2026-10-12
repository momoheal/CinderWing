"""桌宠主窗口：透明置顶无边框，显示序列帧动画，处理点击、长按与拖拽。

待机节奏（安静、不吸引注意力）：
- 大部分时间静止显示站姿，只有身体轻微起伏；
- 每隔几秒眨一次眼（播放 idle 序列）；
- 每隔几十秒偶尔挠一次痒痒；
- 连续约 2 分钟没有任何互动和通知 → 自动入睡，点击唤醒。

互动规律（确定性，不随机）：
- 点头部（窗口上部）→ tap1 咆哮喷火
- 点身体（窗口中下部）→ tap2 扑咬
- 按住不动约 0.6 秒 → tap3 打哈欠睡觉（保持到下次点击）
- 拖动 → drag 被抓起缓慢晃动，松手晕倒后回站姿

任务通知（由 Bubble 的 state_changed 驱动）：
- START / PROGRESS / WAITING → talk 说话动作（气泡可见期间循环）
- DONE → happy 开心庆祝
- FAIL → drag 晕倒帧
"""
import logging
import math
import random

from PySide6.QtCore import Qt, QPoint, QRect, QTimer
from PySide6.QtGui import QAction, QActionGroup, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from app import config_store, packs as packs_mod, skill_import
from app.sprite_anim import SpritePlayer

PET_SIZE = 240           # 窗口边长（逻辑像素）
DRAG_THRESHOLD = 6       # 鼠标移动超过这个距离才算拖拽，否则算点击
DROP_DIZZY_MS = 800      # 松手后晕乎姿势停留时间
FAIL_DIZZY_MS = 1400     # 任务失败晕乎姿势停留时间
LONG_PRESS_MS = 600      # 按住不动超过这个时长 → 睡觉
HEAD_ZONE = 0.42         # 点击位置在窗口上部这个比例以内 → 点头部（咆哮）

# 眨眼间隔（安静时偶尔眨，不频繁吸引注意力）
CYCLE_MIN_MS = 1800
CYCLE_MAX_MS = 4200
# 偶尔挠痒痒的间隔
SCRATCH_MIN_MS = 30000
SCRATCH_MAX_MS = 70000
# 挠痒/入睡时刻恰好撞上眨眼等短动作时，短时间后重试（而不是
# 重新掷一个完整间隔，否则挠痒可能一直被眨眼挤掉）
RETRY_SOON_MIN_MS = 1200
RETRY_SOON_MAX_MS = 2600
# 多久没有任何动静 → 自动入睡
AUTO_SLEEP_S = 120

# 熟睡时的起伏（睡眠帧本身是蜷缩静止的，这里给极轻微的整体起伏）：
# 周期与幅度
SLEEP_BOB_PERIOD_S = 2.8
SLEEP_RISE_PX = 2


class PetWindow(QWidget):
    def __init__(self, sfx):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(PET_SIZE, PET_SIZE)
        self.setWindowTitle("CinderWing")

        self.sfx = sfx
        self.bubble = None  # 由 main 注入（任务通知气泡）
        self.player = SpritePlayer()
        self.player.frame_changed.connect(self._on_frame)
        self.player.finished.connect(self._on_anim_finished)
        self._pix = None

        self._press_pos = None
        self._press_local_y = 0
        self._drag_offset = QPoint()
        self._dragging = False
        self._long_pressed = False
        self._long_timer = QTimer(self)
        self._long_timer.setSingleShot(True)
        self._long_timer.timeout.connect(self._on_long_press)

        # 眨眼 / 挠痒痒：单次定时器，随机间隔
        self._cycle_timer = QTimer(self)
        self._cycle_timer.setSingleShot(True)
        self._cycle_timer.timeout.connect(self._maybe_blink)
        self._scratch_timer = QTimer(self)
        self._scratch_timer.setSingleShot(True)
        self._scratch_timer.timeout.connect(self._maybe_scratch)

        # 自动入睡：安静足够久后触发
        self._sleep_timer = QTimer(self)
        self._sleep_timer.setSingleShot(True)
        self._sleep_timer.timeout.connect(self._auto_sleep)

        # 晕倒（松手/失败）后回站姿
        self._drop_timer = QTimer(self)
        self._drop_timer.setSingleShot(True)
        self._drop_timer.timeout.connect(self._drop_wake)

        # 环境动效时钟（站姿呼吸 / 熟睡起伏共用），始终缓慢运行
        self._sleeping = False
        self._ambient_t = 0.0
        self._ambient_timer = QTimer(self)
        self._ambient_timer.setInterval(60)
        self._ambient_timer.timeout.connect(self._ambient_tick)
        self._ambient_timer.start()

        self._place_initial()
        self._enter_rest()

    # ---------- 显示 ----------
    def _on_frame(self, pix):
        self._pix = pix
        self.update()

    def paintEvent(self, event):
        if self._pix is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._sleeping:
            # 熟睡时极轻微的整体起伏；清醒时的呼吸已经做在 idle 序列帧
            # 里（肚子微微起伏），不再整体上下晃动。
            wave = 0.5 * (1 - math.cos(2 * math.pi * self._ambient_t / SLEEP_BOB_PERIOD_S))
            dy = int(round(SLEEP_RISE_PX * wave))
            p.drawPixmap(QRect(0, -dy, self.width(), self.height()), self._pix)
        else:
            p.drawPixmap(0, 0, self.width(), self.height(), self._pix)

    def _ambient_tick(self):
        self._ambient_t += 0.06
        self.update()

    # ---------- 安静待机：静止站姿 + 偶尔微动 ----------
    def _quiet(self):
        """没有任何互动、没有通知、也没有一次性动作在播放。
        idle 呼吸循环算安静状态，眨眼/挠痒可以随时打断它。"""
        return (self._press_pos is None and not self._dragging
                and self.player.name in (None, "idle")
                and not self._bubble_showing())

    def _bubble_showing(self):
        return self.bubble is not None and getattr(self.bubble, "_showing", False)

    def _enter_rest(self):
        """进入/回到清醒待机：肚子呼吸循环 + 重新安排眨眼、挠痒、入睡。"""
        self._sleeping = False
        self.player.play("idle", loop=True)
        self._cycle_timer.start(random.randint(CYCLE_MIN_MS, CYCLE_MAX_MS))
        self._scratch_timer.start(random.randint(SCRATCH_MIN_MS, SCRATCH_MAX_MS))
        self._sleep_timer.start(AUTO_SLEEP_S * 1000)

    def _back_to_idle(self, reschedule_scratch=False):
        """眨眼/挠痒等自发小动作结束后：回到呼吸循环。
        只重排眨眼；挠痒定时器默认保持不动——否则每 4 秒一次的眨眼
        会把 30~70 秒的挠痒倒计时无限重置，挠痒永远播不出来。"""
        if self._sleeping or self._bubble_showing():
            return
        self.player.play("idle", loop=True)
        self._cycle_timer.start(random.randint(CYCLE_MIN_MS, CYCLE_MAX_MS))
        if reschedule_scratch:
            self._scratch_timer.start(random.randint(SCRATCH_MIN_MS, SCRATCH_MAX_MS))

    def _drop_wake(self):
        logging.info("drop wake: returning to standing idle")
        self._enter_rest()

    def _maybe_blink(self):
        if self._quiet():
            self.player.play("blink")  # 播一遍明确的睁眼→闭眼→睁眼
        else:
            self._cycle_timer.start(random.randint(CYCLE_MIN_MS, CYCLE_MAX_MS))

    def _maybe_scratch(self):
        if self._quiet():
            self.player.play("scratch")  # 偶尔挠一次痒痒
        else:
            # 撞上眨眼/短动作：很快再试，别让挠痒被无限期挤掉
            self._scratch_timer.start(
                random.randint(RETRY_SOON_MIN_MS, RETRY_SOON_MAX_MS))

    def _auto_sleep(self):
        if self._quiet():
            logging.info("auto sleep: idle for %ds", AUTO_SLEEP_S)
            self._enter_sleep()
        else:
            # 恰好有短动作在播：2 秒后再检查一次
            self._sleep_timer.start(2000)

    def _enter_sleep(self):
        self._cycle_timer.stop()
        self._scratch_timer.stop()
        if self.sfx:
            self.sfx.play("tap3")
        self.player.play("tap3", hold_last=True)
        self._sleeping = True

    # ---------- 任务通知动作 ----------
    def jump_to_task(self, key):
        """M3：点气泡 → 打开豆包工作里该任务所在的会话。"""
        from app import activator
        task = None
        if self.bubble is not None:
            task = self.bubble.tasks.get(key)
        if task is None:
            return
        logging.info("jump requested: key=%s conv=%s", key, task.conv_id)
        if self.sfx:
            self.sfx.play("click")
        if task.conv_id:
            activator.activate_conversation(task.conv_id, task.section_id)
        else:
            logging.info("jump requested but no conversation id; ignored")

    def on_bubble_state(self, kind):
        logging.info("bubble state: %r", kind)
        if not kind:
            # queue empty: return to standing unless sleeping / drop pending
            if not self._sleeping and not self._drop_timer.isActive():
                self._enter_rest()
            return
        # an event is activity and cancels auto-sleep / sleeping
        self._sleep_timer.stop()
        if self._sleeping:
            self._sleeping = False
        self._cycle_timer.stop()
        self._scratch_timer.stop()
        self._drop_timer.stop()
        if kind in ("START", "PROGRESS", "WAITING"):
            self.player.play("talk", loop=True)
        elif kind == "DONE":
            if self.sfx:
                self.sfx.play("click")
            self.player.play("happy")
        elif kind == "FAIL":
            self.player.show_frame("drag", 5)
            self._drop_timer.start(FAIL_DIZZY_MS)

    # ---------- 右键菜单 ----------
    def _build_context_menu(self) -> tuple[QMenu, dict]:
        """构建右键菜单。返回 (menu, handlers)，handlers 把 QAction 映射到
        处理函数；拆出来是为了离屏测试也能校验菜单结构。"""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#2b2b30;color:#f0f0f2;border:1px solid #4a4a52;"
            "border-radius:8px;padding:4px;}"
            "QMenu::item{padding:6px 22px;border-radius:6px;}"
            "QMenu::item:selected{background:#c0392b;}"
            "QMenu::separator{height:1px;background:#4a4a52;margin:4px 8px;}")

        handlers = {}
        act_progress = menu.addAction("任务进度（多任务面板）")
        handlers[act_progress] = self._open_progress_panel

        m_play = menu.addMenu("逗逗它")
        for text, fn in (("喷火", lambda: self._manual_play("tap1")),
                         ("扑咬", lambda: self._manual_play("tap2")),
                         ("开心欢呼", lambda: self._manual_play("happy")),
                         ("去睡觉", self._sleep_from_menu)):
            act = m_play.addAction(text)
            handlers[act] = fn

        m_skin = menu.addMenu("更换形象")
        skin_group = QActionGroup(m_skin)
        skin_group.setExclusive(True)
        current = packs_mod.selected_id()
        for pack in packs_mod.list_packs():
            label = pack.name + ("（内置）" if pack.is_builtin else "")
            act = QAction(label, m_skin)
            act.setCheckable(True)
            act.setChecked(pack.id == current)
            skin_group.addAction(act)
            m_skin.addAction(act)
            handlers[act] = lambda pid=pack.id: self._switch_pack(pid)
        m_skin.addSeparator()
        act_open_packs = m_skin.addAction("打开形象文件夹")
        act_make_skin = m_skin.addAction("制作新形象（导入生成技能）…")
        handlers[act_open_packs] = skill_import.open_packs_folder
        handlers[act_make_skin] = self._make_new_skin
        menu._skin_submenu = m_skin  # 供测试/外部读取

        menu.addSeparator()
        act_sound = QAction("音效开关", menu)
        act_sound.setCheckable(True)
        act_sound.setChecked(bool(self.sfx and self.sfx.enabled))
        if self.sfx is not None:
            handlers[act_sound] = lambda: setattr(
                self.sfx, "enabled", act_sound.isChecked())
        menu.addAction(act_sound)
        menu.addSeparator()
        act_hide = menu.addAction("隐藏宠物（托盘恢复）")
        act_quit = menu.addAction("退出")
        handlers[act_hide] = self.hide
        handlers[act_quit] = QApplication.instance().quit
        return menu, handlers

    def _sleep_from_menu(self):
        self._long_pressed = True
        self._enter_sleep()

    def contextMenuEvent(self, event):
        menu, handlers = self._build_context_menu()
        chosen = menu.exec(event.globalPos())
        if chosen is not None and chosen in handlers:
            handlers[chosen]()

    def _open_progress_panel(self):
        if self.bubble is not None and self.bubble.show_panel():
            if self.sfx:
                self.sfx.play("click")
            return
        # 没有进行中的任务：给一条待命提示（顺带播开心动作）
        if self.bubble is not None:
            self.bubble.notify("DONE", "现在没有进行中的任务，小龙在待命",
                               key="menu-idle", name="小龙", progress=100)

    # ---------- 更换形象 ----------
    def _switch_pack(self, pack_id: str):
        pack = packs_mod.get_pack(pack_id)
        self.player.set_pack(pack)
        packs_mod.set_selected(pack_id)
        if self.sfx:
            self.sfx.play("click")
        # 换装后无论在睡觉还是放动作，都回到新形象的待机
        self._sleeping = False
        self._drop_timer.stop()
        self._enter_rest()
        if self.bubble is not None:
            self.bubble.notify(
                "DONE", f"已换上新形象：{pack.name}",
                key="skin-switched", name="形象工坊", progress=100)

    def _make_new_skin(self):
        """把生成技能导入豆包工作，再打开形象文件夹并唤起客户端。"""
        ok, info = skill_import.import_skill()
        skill_import.open_packs_folder()
        skill_import.bring_doubao_to_front()
        if self.bubble is not None:
            if ok:
                self.bubble.notify(
                    "WAITING",
                    "形象工坊技能已导入豆包工作。请在豆包工作里上传角色概念图，"
                    "并说「用桌宠形象工坊生成新形象」；做好的角色包放进刚打开的 "
                    "packs 文件夹后，回这里右键「更换形象」即可。",
                    key="skin-make", name="形象工坊", progress=10)
            else:
                self.bubble.notify(
                    "FAIL", f"技能自动导入失败：{info}（可手动把仓库 skills 目录"
                            "复制到豆包工作的 .user_skills）",
                    key="skin-make-fail", name="形象工坊", progress=100)

    def _manual_play(self, name):
        """右键菜单里手动触发的互动动作。"""
        if self._sleeping:
            self._sleeping = False
        self._press_pos = None
        self._dragging = False
        self._drop_timer.stop()
        self._sleep_timer.stop()
        if self.sfx:
            self.sfx.play(name if name in ("tap1", "tap2") else "click")
        self.player.play(name)

    # ---------- 鼠标：点头部/点身体、长按、拖拽 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton and self.bubble is not None:
            # 隐藏的测试入口：鼠标中键点宠物，弹一条示例完成通知
            self.bubble.notify("DONE", "「示例任务：整理本周设计素材清单」完成了",
                               key="demo-done", name="示例任务", progress=100)
            return
        if event.button() == Qt.LeftButton:
            if self._sleeping:
                # 唤醒熟睡的小龙，随后这次按压照常处理（可点击/拖拽）
                self._sleeping = False
                self.player.stop()
            self._sleep_timer.stop()
            self._cycle_timer.stop()
            self._scratch_timer.stop()
            self._press_pos = event.globalPosition().toPoint()
            self._press_local_y = event.position().y()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._dragging = False
            self._long_pressed = False
            self._long_timer.start(LONG_PRESS_MS)

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            return
        g = event.globalPosition().toPoint()
        if not self._dragging and (g - self._press_pos).manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
            self._long_timer.stop()
            if self.sfx:
                self.sfx.play("drag")
            self.player.play("drag", loop=True, hold=5)  # 只循环前5帧慢晃
        if self._dragging:
            self.move(g - self._drag_offset)
            if self.bubble is not None:
                self.bubble.reposition()

    def mouseReleaseEvent(self, event):
        logging.info("release: press_pos=%s dragging=%s long=%s",
                     self._press_pos is not None, self._dragging, self._long_pressed)
        if self._press_pos is None:
            return
        self._press_pos = None
        self._long_timer.stop()
        if self._dragging:
            self._dragging = False
            self._save_pos()
            self.player.show_frame("drag", 5)  # 松手：晕倒姿势
            self._drop_timer.start(DROP_DIZZY_MS)
            logging.info("drag released: drop frame shown, wake scheduled %dms", DROP_DIZZY_MS)
        elif self._long_pressed:
            pass  # 已进入熟睡：保持到下次点击唤醒，不回站姿
        else:
            # 按点击位置分区（确定性）：头部→咆哮喷火，身体→扑咬
            action = "tap1" if self._press_local_y < self.height() * HEAD_ZONE else "tap2"
            self._sleep_timer.stop()
            if self.sfx:
                self.sfx.play(action)
            self.player.play(action)

    def _on_long_press(self):
        if self._press_pos is not None and not self._dragging:
            self._long_pressed = True
            self._enter_sleep()

    def _on_anim_finished(self, name):
        # one-shot action finished:
        # - bubble still on screen -> resume the talking loop
        # - sleeping (tap3 holds its own last frame anyway) -> stay asleep
        # - ambient blink/scratch -> back to idle breath without touching
        #   the auto-sleep timer
        # - a click reaction (tap1/tap2/happy) -> full rest reset, which
        #   re-arms the auto-sleep timer (interaction counts as activity)
        if self._bubble_showing():
            self.player.play("talk", loop=True)
        elif self._sleeping:
            pass
        elif name == "blink":
            self._back_to_idle()
        elif name == "scratch":
            self._back_to_idle(reschedule_scratch=True)
        else:
            self._enter_rest()

    # ---------- 位置记忆 ----------
    def _place_initial(self):
        try:
            pos = config_store.get("pos")
            x, y = pos
            self.move(x, y)
            return
        except Exception:
            pass
        screen = self.screen().availableGeometry()
        self.move(screen.right() - self.width() + 1,
                  screen.bottom() - self.height() + 1)

    def _save_pos(self):
        config_store.update(pos=[self.x(), self.y()])

    # ---------- 关闭收托盘 ----------
    def closeEvent(self, event):
        event.ignore()
        self.hide()
