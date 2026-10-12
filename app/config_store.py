"""config.json 的统一读写：位置、当前形象等所有设置都存这里。

零基础说明：
- 以前只有窗口位置，直接整体覆写；新增形象设置后必须"读出→改一项→写回"，
  否则会把别的设置冲掉。这个小模块就负责这件事。
"""
import json
import os

from app import paths


def load() -> dict:
    try:
        with open(paths.config_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save(data: dict) -> None:
    os.makedirs(os.path.dirname(paths.config_path()), exist_ok=True)
    tmp = paths.config_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, paths.config_path())


def get(key, default=None):
    return load().get(key, default)


def update(**kwargs) -> dict:
    data = load()
    data.update(kwargs)
    save(data)
    return data
