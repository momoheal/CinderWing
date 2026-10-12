"""统一的路径管理：开发态与打包态（PyInstaller）都从这里取路径。

- 只读资源（frames 帧图、sfx 音效、skills 技能包）：
    开发态 = 项目根；打包态 = 解包目录（sys._MEIPASS）。
- 可写数据（pet.log 日志、config.json 位置记忆、packs 角色包）：
    开发态仍写在项目 assets 里；打包态写进 %APPDATA%\\CinderWing，
    这样升级重装不会丢位置，普通用户目录也一定有写权限。
"""
import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "CinderWing"
LEGACY_APP_DIR_NAME = "GeoHarbourPet"  # v1.1.x 旧目录，首次启动自动迁移


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_root() -> Path:
    """只读资源根目录（其下有 assets/、skills/）。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def asset_path(rel: str) -> str:
    """只读资源：asset_path('frames') / asset_path('sfx/click.wav')。"""
    return str(resource_root() / "assets" / rel)


def _migrate_legacy(base: Path) -> Path:
    """v1.1.x 的旧数据目录首次启动时整体迁移到 CinderWing。"""
    new = base / APP_DIR_NAME
    old = base / LEGACY_APP_DIR_NAME
    if new.exists() or not old.exists():
        return new
    try:
        old.rename(new)
    except OSError:
        # 跨卷或文件被占用时退化为复制
        shutil.copytree(old, new, dirs_exist_ok=True)
    return new


def data_dir() -> Path:
    """可写数据目录，不存在就创建。"""
    if is_frozen():
        base = Path(os.environ.get("APPDATA") or str(Path.home()))
        d = _migrate_legacy(base)
    else:
        d = Path(__file__).resolve().parent.parent / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path() -> str:
    return str(data_dir() / "pet.log")


def config_path() -> str:
    return str(data_dir() / "config.json")
