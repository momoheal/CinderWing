"""角色包（皮肤）系统。

一个角色包就是一个文件夹，结构如下：

    packs/<角色包id>/
        pack.json        # {"id","name","author","fps":{...可选}}
        preview.png      # 可选，菜单里的预览图
        frames/
            idle/00.png ...      # 9 套动作，每套若干 256x256 透明 PNG
            blink/ ...
            tap1/ tap2/ tap3/ drag/ happy/ talk/ scratch/

- 内置默认形象随程序发布（assets/frames，id=cinderwing）。
- 用户自己的角色包放在可写数据目录的 packs/ 下：
    打包态 = %APPDATA%\\GeoHarbourPet\\packs
    开发态 = 项目 assets/packs
- 某套动作缺失时自动回退用默认形象的同名动作，保证角色包可以"先做几套"。
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from app import config_store, paths

ANIMS = ["idle", "blink", "tap1", "tap2", "tap3",
         "drag", "happy", "talk", "scratch"]

DEFAULT_FPS = {
    "idle": 2, "blink": 9, "tap1": 9, "tap2": 9, "tap3": 7, "drag": 2,
    "happy": 9, "talk": 8, "scratch": 7,
}

BUILTIN_ID = "cinderwing"
CONFIG_KEY = "pack_id"


@dataclass
class Pack:
    id: str
    name: str
    frames_root: Path          # 其下是 <anim>/NN.png
    author: str = ""
    fps: dict = field(default_factory=dict)
    preview: str = ""
    is_builtin: bool = False
    root: Path = None          # 包根目录（用户包才有 preview/meta）

    def fps_for(self, anim: str) -> int:
        return int(self.fps.get(anim, DEFAULT_FPS.get(anim, 12)))

    def frame_dir(self, anim: str) -> Path | None:
        d = self.frames_root / anim
        if d.is_dir() and any(d.glob("*.png")):
            return d
        return None

    def frame_files(self, anim: str) -> list[str]:
        d = self.frame_dir(anim)
        if d is None:
            return []
        return sorted(str(p) for p in d.glob("*.png"))

    def available_anims(self) -> list[str]:
        return [a for a in ANIMS if self.frame_dir(a) is not None]


def packs_dir() -> Path:
    """用户角色包目录（可写），不存在就创建。"""
    d = paths.data_dir() / "packs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def builtin_pack() -> Pack:
    return Pack(
        id=BUILTIN_ID,
        name="小烬翼（默认）",
        frames_root=Path(paths.asset_path("frames")),
        is_builtin=True,
        root=Path(paths.asset_path(".")),
    )


def _load_user_pack(pack_dir: Path) -> Pack | None:
    meta = {}
    meta_file = pack_dir / "pack.json"
    if meta_file.is_file():
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            logging.warning("角色包 pack.json 解析失败: %s", pack_dir)
            return None
    frames_root = pack_dir / "frames"
    if not frames_root.is_dir():
        return None
    pid = str(meta.get("id") or pack_dir.name)
    if pid == BUILTIN_ID:
        pid = pack_dir.name  # 不允许冒充内置包
    preview = pack_dir / "preview.png"
    return Pack(
        id=pid,
        name=str(meta.get("name") or pack_dir.name),
        author=str(meta.get("author", "")),
        fps=meta.get("fps") if isinstance(meta.get("fps"), dict) else {},
        preview=str(preview) if preview.is_file() else "",
        frames_root=frames_root,
        is_builtin=False,
        root=pack_dir,
    )


def list_packs() -> list[Pack]:
    """内置形象排第一，其余按名字排序。"""
    packs = [builtin_pack()]
    for d in sorted(packs_dir().iterdir()):
        if d.is_dir():
            pack = _load_user_pack(d)
            if pack is not None:
                packs.append(pack)
    return packs


def get_pack(pid: str) -> Pack:
    for p in list_packs():
        if p.id == pid:
            return p
    return builtin_pack()


def selected_id() -> str:
    pid = config_store.get(CONFIG_KEY)
    valid = {p.id for p in list_packs()}
    return pid if pid in valid else BUILTIN_ID


def selected_pack() -> Pack:
    return get_pack(selected_id())


def set_selected(pid: str) -> None:
    config_store.update(**{CONFIG_KEY: pid})
