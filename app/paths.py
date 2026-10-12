"""统一的路径管理：开发态与打包态（PyInstaller）都从这里取路径。

- 只读资源（frames 帧图、sfx 音效）：
    开发态 = 项目根/assets；打包态 = 解包目录（sys._MEIPASS）/assets。
- 可写数据（pet.log 日志、config.json 位置记忆）：
    开发态仍写在项目 assets 里（和以前一致）；
    打包态写进 %APPDATA%\\GeoHarbourPet，
    这样升级重装不会丢位置，普通用户目录也一定有写权限。
"""
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_root() -> Path:
    """只读资源根目录（其下有 assets/）。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def asset_path(rel: str) -> str:
    """只读资源：asset_path('frames') / asset_path('sfx/click.wav')。"""
    return str(resource_root() / "assets" / rel)


def data_dir() -> Path:
    """可写数据目录，不存在就创建。"""
    if is_frozen():
        base = os.environ.get("APPDATA") or str(Path.home())
        d = Path(base) / "GeoHarbourPet"
    else:
        d = Path(__file__).resolve().parent.parent / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path() -> str:
    return str(data_dir() / "pet.log")


def config_path() -> str:
    return str(data_dir() / "config.json")
