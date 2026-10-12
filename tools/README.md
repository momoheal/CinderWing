# tools/ 脚本索引

开发、构建、测试与排障用的脚本都在这里。程序运行只依赖 `app/`，本目录不参与打包。

## 正式流水线（常用）

| 脚本 | 用途 |
|---|---|
| `build_frames.py` | 美术流水线 v0.8：把 `assets/sheets/` 的 AI 条图抠像、切帧、程序化加工，输出到 `assets/frames/` |
| `pack_build.py` | **M6 通用角色包构建器**：任意角色的条图文件夹 → 抠像切帧 → 可换装角色包（见 `skills/cinderwing-asset-forge/`） |
| `_make_tap3.py` | 生成 tap3（哈欠→睡眠）帧的前置脚本，build_frames 前先跑 |
| `make_icon.py` | 生成 `assets/app.ico`（16–256 多尺寸） |
| `make_sounds.py` | 生成 `assets/sfx/` 的 5 个音效 |
| `build_exe.bat` | 一键 PyInstaller 打包，完成后自动跑 post_build.py |
| `post_build.py` | 打包后处理：复制开机自启脚本、转换编码（bat=ASCII/CRLF，ps1/txt=UTF-8 BOM/CRLF） |
| `installer/` | 开机自启安装/卸载脚本（ps1 + bat + 使用说明） |

## 自动化测试

| 脚本 | 用途 |
|---|---|
| `test_m6_packs.py` | M6 离屏测试：角色包扫描/切换/回退/fps/菜单结构（19 项） |
| `test_m5_menu_ask.py` | M5 离屏测试：右键菜单、决策选项气泡（7 项） |
| `test_m3_jump.py` | M3 离屏测试：气泡/面板点击跳转（5 项） |
| `_test_source_once.py` | M2 数据源离线回归：快照 → 读任务 → 打印状态 |
| `audit_idle.py` / `audit_clicks.py` | 闲置动画 / 点击反应的自动巡检 |
| `harness_flow.py` / `run_harness.bat` | 互动全流程演练 |

## 截图与观察

| 脚本 | 用途 |
|---|---|
| `capture_pet.py` | 抓开发态宠物窗口（品红垫底，便于查抠像） |
| `capture_by_title.py` | 按窗口标题抓打包版宠物 |
| `grab_bubble2.py` | 按进程抓全部 Qt 窗口（含高气泡，M5 推荐） |
| `grab_bubble.py` | 旧版抓气泡（高度 <200 会漏，已被 2 代取代） |
| `_m5_shot_menu.py` / `_m5_shot_submenu.py` | 真机右键菜单/子菜单抓拍 |
| `bubble_preview.py` | 气泡离屏预览 |

## 数据源排障（M2 相关）

| 脚本 | 用途 |
|---|---|
| `_diag_default_store.py`～`_diag_default_store4.py` | default-chat-im-protocol-store 反序列化失败的逐层诊断（v1.1.0 blob 兜底修复的排查记录） |
| `_probe_10082.py` / `_probe_10082_all.py` | 实时探测 interaction_ask_block（10082 决策块） |
| `_probe_cc7a.py` | 指定任务样本探测 |
| `_m2_watch.py` / `_start_watch.bat` | 长时间轮询观察（7200 轮） |
| `watch_tasks.py` / `db_probe.py` / `idb_spike*.py` | 早期 IndexedDB 结构探针 |
| `_m3_scan_routes.py` / `_m3_scan_routes2.py` | 扫描客户端 deep-link 路由表 |

## 其他

- `_keep_dirs.py` / `_keep_dir.bat`：特定开发环境下临时目录被清理时的守护脚本，与产品无关。
- `*.png / *.jpg`：排障与质检中间图（品红底检查图只作过程记录）。
- 下划线开头的脚本多为一次性诊断/实验脚本，保留作为排查轨迹，可随时删除。

## AI 抠图模型位置（不入库）

`build_frames.py` 使用 rembg + u2net，模型文件约 176MB，需自行放置：

```
tools/.u2net/models/u2net/u2net.onnx
```

设置环境变量 `U2NET_HOME=工具目录\.u2net` 后首次运行 rembg 也会自动下载。
