"""M6 角色包系统离屏测试：内置包、用户包发现、切换、缺失动作回退、设置持久化。"""
import os
import shutil
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app import config_store, packs as packs_mod
from app.pet_window import PetWindow

app = QApplication([])
failures = []

def check(cond, msg):
    print(("PASS" if cond else "FAIL"), "-", msg)
    if not cond:
        failures.append(msg)

# 1. 内置包
builtin = packs_mod.builtin_pack()
check(builtin.id == "cinderwing", "内置包 id=cinderwing")
check(len(builtin.available_anims()) == 9, f"内置包 9 套动作齐全（{len(builtin.available_anims())}）")

# 2. 窗口用默认包启动，9 套帧都装载成功
win = PetWindow(None)
check(set(win.player.frames) == set(packs_mod.ANIMS), "播放器装载了全部 9 套帧")
check(win.player.pack.id == "cinderwing", "首次启动默认形象")

# 3. 造一个测试用户包：只给 idle 和 tap1，其余动作应回退默认
test_dir = packs_mod.packs_dir() / "unit-test-pup"
if test_dir.exists():
    shutil.rmtree(test_dir)
frames = test_dir / "frames"
os.makedirs(frames / "idle")
os.makedirs(frames / "tap1")
shutil.copy(builtin.frame_files("idle")[0], frames / "idle" / "00.png")
for i, f in enumerate(builtin.frame_files("tap1")[:3]):
    shutil.copy(f, frames / "tap1" / f"{i:02d}.png")
import json
with open(test_dir / "pack.json", "w", encoding="utf-8") as f:
    json.dump({"id": "unit-test-pup", "name": "测试小狗", "author": "tester",
               "fps": {"idle": 3}}, f, ensure_ascii=False)

packs_list = packs_mod.list_packs()
test_pack = next((p for p in packs_list if p.id == "unit-test-pup"), None)
check(test_pack is not None, "用户角色包被扫描到")
check(test_pack and test_pack.name == "测试小狗", "pack.json 名称生效")

# 4. 切换到测试包：idle 用新包（1帧），blink 回退默认（5帧）
win._switch_pack = win._switch_pack  # noqa  (ensure method exists)
win.player.set_pack(test_pack)
check(len(win.player.frames["idle"]) == 1, "idle 使用用户包帧（1 帧）")
check(len(win.player.frames["blink"]) == 5, "缺失的 blink 回退默认包（5 帧）")
check(win.player.fps_map["idle"] == 3, "用户包 fps 覆盖生效")
packs_mod.set_selected("unit-test-pup")
check(packs_mod.selected_id() == "unit-test-pup", "选择结果写入配置")

# 5. 切回默认并持久化
packs_mod.set_selected(packs_mod.BUILTIN_ID)
win.player.set_pack(packs_mod.selected_pack())
check(len(win.player.frames["idle"]) == 8, "切回默认形象后 idle 恢复 8 帧")
check(packs_mod.selected_id() == "cinderwing", "配置已切回默认")

# 6. 无效 id 自动回退
packs_mod.set_selected("not-exist")
check(packs_mod.selected_id() == "cinderwing", "无效形象 id 自动回退默认")
packs_mod.set_selected(packs_mod.BUILTIN_ID)

# 清理
shutil.rmtree(test_dir)
check(not test_dir.exists(), "测试包已清理")

# 7. 右键菜单结构：换装子菜单列出形象包 + 两个操作项
win2 = PetWindow(None)
menu, handlers = win2._build_context_menu()
top_texts = [a.text() for a in menu.actions() if a.text()]
check("更换形象" in top_texts, "顶层菜单有「更换形象」")
m_skin = menu._skin_submenu
skin_texts = [a.text() for a in m_skin.actions()]
check(any("小烬翼" in t and "内置" in t for t in skin_texts),
      f"子菜单列出内置形象：{skin_texts}")
check("打开形象文件夹" in skin_texts, "子菜单有「打开形象文件夹」")
check("制作新形象（导入生成技能）…" in skin_texts, "子菜单有「制作新形象」")
switched = []
win2._switch_pack = lambda pid: switched.append(pid)
for act, fn in handlers.items():
    if act.text().startswith("小烬翼"):
        fn()
check(switched == ["cinderwing"], f"点形象项触发切换：{switched}")

# 8. 离屏渲染菜单与子菜单，存图供人工目检
from PySide6.QtTest import QTest
menu.resize(menu.sizeHint())
menu.show()
QTest.qWait(120)
shot_dir = os.path.dirname(os.path.abspath(__file__))
menu.grab().save(os.path.join(shot_dir, "_m6_menu_render.png"))
m_skin.resize(m_skin.sizeHint())
m_skin.show()
QTest.qWait(120)
m_skin.grab().save(os.path.join(shot_dir, "_m6_skinmenu_render.png"))
menu.close()
m_skin.close()
check(True, "菜单离屏渲染图已生成")

print()
if failures:
    print(f"{len(failures)} 项失败")
    sys.exit(1)
print("M6 角色包测试全部通过")
