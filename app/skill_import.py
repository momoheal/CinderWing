"""一键导入"桌宠形象工坊"生成 Skill 到豆包工作。

豆包工作的自定义技能放在当前用户的：
    %LOCALAPPDATA%\\DoubaoWork\\User Data\\Default\\.doubaowork\\
        agent_mode\\workspace\\.user_skills\\<技能名>\\SKILL.md
把随仓库附带的 skills/cinderwing-asset-forge 整个目录复制过去，
重启（或新开会话）后在豆包工作对话里就能让 AI 按规范生成新形象。
"""
import logging
import os
import shutil
from pathlib import Path

from app import packs, paths

SKILL_DIR_NAME = "cinderwing-asset-forge"


def bundled_skill_dir() -> Path:
    """随程序/仓库附带的技能目录。"""
    return paths.resource_root() / "skills" / SKILL_DIR_NAME


def doubao_skills_dir() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    return (Path(local) / "DoubaoWork" / "User Data" / "Default"
            / ".doubaowork" / "agent_mode" / "workspace"
            / ".user_skills" / SKILL_DIR_NAME)


def import_skill() -> tuple[bool, str]:
    """复制技能目录。返回 (是否成功, 说明文字)。"""
    src = bundled_skill_dir()
    dst = doubao_skills_dir()
    if not src.is_dir():
        return False, f"没有找到随程序附带的形象工坊技能目录：{src}"
    if dst is None:
        return False, "没有找到豆包工作的技能目录，请确认已安装豆包工作客户端。"
    try:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        logging.info("形象工坊技能已导入: %s", dst)
        return True, str(dst)
    except Exception as e:
        logging.exception("导入形象工坊技能失败")
        return False, f"导入失败：{e}"


def open_packs_folder() -> None:
    """在资源管理器里打开角色包目录（新形象做好后放这里）。"""
    d = packs.packs_dir()
    os.startfile(str(d))


def bring_doubao_to_front() -> None:
    try:
        from app import activator
        activator.bring_to_front()
    except Exception:
        logging.exception("唤起豆包工作失败")
