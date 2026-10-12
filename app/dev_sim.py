"""开发演示：模拟两个任务并发执行的完整事件流。

演示内容（M2 接上真实数据源前的预览）：
- 两个任务先后开始，气泡里都有实时进度条；
- 点击气泡可展开“任务进度”面板，同时看到两个任务；
- 任务 A 中途“需要你决策”，随后继续并完成；任务 B 最后完成。

动作由 Bubble.state_changed 驱动（talk / happy / 晕倒），
进度数字更新只重绘气泡，不打断宠物动作。
"""
from PySide6.QtCore import QTimer

NAME_A = "整理本周设计素材清单"
KEY_A = "demo-task-a"
CONV_A = "99900000000000001"
NAME_B = "导出龙巢宣传页切图"
KEY_B = "demo-task-b"
CONV_B = "99900000000000002"

A_STATUSES = [
    "正在收集素材…",
    "素材已收集完，正在分类…",
    "正在识别重复文件…",
]
A_STATUSES_2 = [
    "已按确认清理重复素材，继续整理…",
    "正在生成清单目录…",
    "正在校对文件命名…",
]
B_STATUSES = [
    "正在加载画板…",
    "正在导出切图…",
    "正在压缩图片…",
    "正在上传切图…",
]


def simulate(pet_window):
    bubble = pet_window.bubble
    elapsed = {"s": 0.0}

    def at(sec, fn):
        QTimer.singleShot(int(sec * 1000), fn)

    # ---- 固定事件节点 ----
    at(0, lambda: (
        bubble.notify("START", f"「{NAME_A}」开始了", KEY_A, NAME_A, 0,
                      CONV_A, None),
        pet_window.sfx.play("click"),
    ))
    at(2.5, lambda: (
        bubble.notify("START", f"「{NAME_B}」开始了", KEY_B, NAME_B, 0,
                      CONV_B, None),
        pet_window.sfx.play("click"),
    ))
    at(9, lambda: bubble.notify(
        "WAITING", "需要你确认：如何处理这 12 个重复素材？", KEY_A, NAME_A,
        None, CONV_A, None,
        ask={"questions": [{
            "title": "需要你确认：如何处理这 12 个重复素材？",
            "type": 1,
            "options": [
                {"id": "opt-keep", "label": "全部保留，只在清单里标注重复"},
                {"id": "opt-move", "label": "移到「待确认」文件夹"},
                {"id": "opt-delete", "label": "直接删除重复文件"},
            ],
            "allow_text": True,
        }]}))
    at(14, lambda: bubble.notify(
        "PROGRESS", "已按确认清理重复素材，继续整理…", KEY_A, NAME_A, 65,
        CONV_A, None))
    at(18, lambda: (
        bubble.notify("DONE", f"「{NAME_A}」完成了", KEY_A, NAME_A, 100,
                      CONV_A, None),
        pet_window.sfx.play("click"),
    ))
    at(23, lambda: (
        bubble.notify("DONE", f"「{NAME_B}」完成了", KEY_B, NAME_B, 100,
                      CONV_B, None),
        pet_window.sfx.play("click"),
    ))

    # ---- 每秒一次的实时进度 ----
    def tick():
        elapsed["s"] += 1.0
        s = elapsed["s"]
        # A：0–9s 走到 60%；等待决策期间不动；14–18s 从 65% 走到 100%
        if 1 <= s < 9:
            bubble.update_progress(KEY_A, int(s / 9 * 60),
                                   A_STATUSES[min(int(s // 3), 2)],
                                   CONV_A, None)
        elif 14 < s < 18:
            bubble.update_progress(KEY_A, 65 + int((s - 14) / 4 * 35),
                                   A_STATUSES_2[min(int((s - 14) // 1.4), 2)],
                                   CONV_A, None)
        # B：3–23s 缓慢走到 100%
        if 3 <= s < 23:
            bubble.update_progress(KEY_B, int((s - 3) / 20 * 100),
                                   B_STATUSES[min(int((s - 3) // 5), 3)],
                                   CONV_B, None)
        if s >= 25:
            timer.stop()

    timer = QTimer()
    timer.setInterval(1000)
    timer.timeout.connect(tick)
    timer.start()
