# 桌宠形象工坊 · CinderWing Asset Forge

这是一个**豆包工作（Doubao Work）自定义技能**，也可在兼容同类 SKILL.md 规范的
AI Agent 中使用。

## 它能做什么

给 Agent 一张角色概念图，它就会：

1. 按桌宠需要的 9 套动作（待机呼吸、眨眼、喷火、扑咬、入睡、被拖拽、开心、
   说话、挠痒）逐套生成青蓝幕布条图；
2. 调用 CinderWing 仓库的 `tools/pack_build.py` 自动抠像、切帧、对齐、质检；
3. 产出一个角色包，宠物右键菜单「更换形象」里立刻能换上。

## 安装方式

**方式一（推荐）：在桌宠里一键导入**

右键宠物 →「更换形象」→「制作新形象（导入生成技能）…」，
技能会自动复制到豆包工作的 `.user_skills` 目录，然后在豆包工作里
上传概念图并说：

> 用「桌宠形象工坊」给我生成一套新形象，角色包 id 叫 xxx，名字叫 xxx

**方式二：手动安装**

把本目录整个复制到：

```
%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\cinderwing-asset-forge\
```

重新打开一个豆包工作会话即可生效。

## 前置条件

- 已克隆 CinderWing 仓库并装好依赖（`pip install -r requirements.txt`）；
- 首次构建会自动下载约 176MB 的 u2net 抠图模型（也可预置到 `tools/.u2net`）。

## 文件说明

- `SKILL.md`：技能主流程（给 Agent 读）；
- `references/animation-brief.md`：9 套动作的生图规范与硬约束；
- `references/pack-spec.md`：角色包结构、sheets.json、构建与品红质检清单；
- `templates/sheets.json`：条图切格声明模板。
