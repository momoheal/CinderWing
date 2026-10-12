# 角色包规范与构建/质检

## 目录结构

```
<packs 父目录>/
├── qa_<id>.png            # 品红底质检拼图（构建时自动生成）
└── <id>/
    ├── pack.json          # 元信息（自动生成，可手改显示名/fps）
    ├── preview.png        # 菜单预览图（自动取 idle 首帧）
    └── frames/
        ├── idle/00.png 01.png ...
        ├── blink/
        ├── tap1/
        ├── tap2/
        ├── tap3/
        ├── drag/
        ├── happy/
        ├── talk/
        └── scratch/
```

- 每帧 256×256 透明 PNG，角色约 205px 高、脚底对齐画布底部留 18px。
- packs 父目录（宠物右键「打开形象文件夹」就是这里）：
  - 打包版：`%APPDATA%\CinderWing\packs`
  - 开发态：`<仓库>\assets\packs`
- 缺少某套动作时，程序自动用内置默认形象的同名动作顶上，不会崩。

## 输入：sheets 文件夹

```
<工作目录>/sheets/
    sheets.json            # 可选但推荐
    idle.png / idle_2.png ...（每个动作一张或多张条图）
```

sheets.json：

```json
{
  "idle":    {"file": "idle.png", "cells": 8},
  "blink":   {"file": "blink.png", "cells": 5},
  "tap1":    {"file": "tap1.png", "cells": 9},
  "tap2":    {"file": "tap2.png", "cells": 5},
  "tap3":    {"file": "tap3.png", "cells": 7},
  "drag":    {"file": "drag.png", "cells": 6},
  "happy":   {"file": "happy.png", "cells": 3},
  "talk":    {"file": "talk.png", "cells": 9},
  "scratch": {"file": "scratch.png", "cells": 4}
}
```

- 多张条图拼一个动作时，把文件命名为 `tap1_a.png`、`tap1_b.png`，并在
  sheets.json 里写成数组：
  `"tap1": [{"file":"tap1_a.png","cells":3},{"file":"tap1_b.png","cells":3},{"file":"tap1_c.png","cells":2}]`
- 可选字段：`"rows": 2`（多排网格，默认 1）、`"anchor": "bottom"|"center"`
  （拖拽类可用 center，默认 bottom）、`"target_h": 205`、`"side": 24`。
- 不写 sheets.json 时：文件名 `<动作>_<格数>.png`（如 `happy_3.png`）；
  再不行就按宽高比自动猜格数。

## pack.json（自动生成）

```json
{
  "id": "lava-pup",
  "name": "熔岩小狗",
  "author": "你的名字",
  "version": 1,
  "generator": "pack_build 1.0",
  "fps": {"idle": 2, "blink": 9, "tap1": 9, "tap2": 9,
          "tap3": 7, "drag": 2, "happy": 9, "talk": 8, "scratch": 7}
}
```

fps 可手动微调（数字越大动作越快）。

## 构建命令

```powershell
$env:U2NET_HOME="<REPO>\tools\.u2net"
<REPO>\.venv\Scripts\python.exe <REPO>\tools\pack_build.py `
  "<工作目录>\sheets" --id lava-pup --name "熔岩小狗" --author "名字"
```

- 首次运行 rembg 会自动下载 u2net 模型（约 176MB）到 U2NET_HOME。
- 想先输出到别处检查，加 `--out D:\some\packs`。

## QA 质检清单（必须在品红 RGB(200,30,160) 底上看，禁止白底）

构建自动生成 `qa_<id>.png`，每套动作一行。逐行检查：

- [ ] **身体内部没有透明洞/白块**（品红透进来或发白的区域都是事故；
      白底下浅色高光问题会被遮住，所以必须用品红底）；
- [ ] 每帧角色的全部外延肢体（翅膀/角/尾巴/耳朵/长道具）完整、没有被裁；
- [ ] 轮廓边缘没有青蓝色描边（幕布溢色残留）；
- [ ] 同套各帧角色大小、站位一致，没有忽大忽小、水平漂移；
- [ ] idle 只有胸腹轻微起伏，没有整体上下晃/缩放；
- [ ] blink 只有眼睛变化，头没有转；
- [ ] tap1 特效只从嘴/发射点出来，爪子和地面没有火；
- [ ] tap3 最后一帧睡姿完整、翅膀对称搭身；
- [ ] drag 帧之间是缓慢晃动，不是快速跳帧；
- [ ] 没有混入邻格角色、没有青蓝底残留块、没有文字水印。

脚本会对帧间内容占比异常（某帧明显缺肉或多东西）打印 `[警告]`，
看到警告必须在质检图上人工确认。不合格的帧只重做对应动作的条图并重跑构建。
