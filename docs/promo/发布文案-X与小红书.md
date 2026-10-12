# CinderWing 发布文案（X + 小红书）

> 配图建议统一用仓库 `docs/images/` 下的图（已随开源仓库公开，链接不会挂）：
> - `m7-pet-hero.png` 小龙主图
> - `m5-ask-bubble.png` 决策选项气泡
> - `m3-task-panel.png` 多任务进度面板
> - `m7-context-menu.png` 右键菜单
> - `m7-skin-menu.png` 更换形象菜单
> - `m7-play-menu.png` 逗逗它子菜单
>
> 仓库：https://github.com/momoheal/CinderWing
> Release（免 Python 绿色包）：https://github.com/momoheal/CinderWing/releases/tag/v1.2.0

---

## 一、X（Twitter）英文线程 · 主发版本

> X 单条 280 字符限制，下面每条都按限制写好，可直接逐条发；
> 配图顺序见每条开头标注。X 线程最多在第 1、3、5 条各带图。

**1/（配图：m7-pet-hero + m5-ask-bubble）**

I'm a product designer with basically zero coding background — and I just open-sourced my first real desktop app.

Meet CinderWing: a chibi dragon living on your Windows desktop who watches your AI agents work. Task starts, needs your decision, or finishes → he tells you in a bubble with a live progress bar. Click → jump back to the chat.

**2/**

What he does:
· read-only local monitoring of Doubao Work agent tasks (IndexedDB polling, no server, no API keys)
· multi-task progress panel
· clickable decision buttons right inside the bubble
· deep-link jump straight into the conversation
· 52 sprite frames: breathing, blinking, fire breath, drag sway, sleeps when ignored 🐉

**3/（配图：m3-task-panel + m7-context-menu）**

He's a plugin, not a fixed character:
drop a character-pack folder in and switch skins from the right-click menu.

The fun part is the Asset Forge skill — give an AI ONE concept image of your OC, and it generates all 9 animation sheets, cuts them out, QA-checks every frame on a magenta background, and packages a working desktop pet.

**4/**

The whole thing was built with an AI coding agent (Doubao Work), Python + PySide6.

The repo documents the full beginner journey: transparent borderless windows, reverse-reading a Chromium IndexedDB, the AI cutout pipeline that finally killed the white-pixel artifacts, and PyInstaller packaging. Notes are in Chinese but code is universal.

**5/（配图：m7-skin-menu + m7-play-menu）**

Free & open source:
· code: MIT
· art/audio: CC BY-NC 4.0
· Windows 10/11, ready-to-run zip — no Python install needed

⭐ Repo + download:
github.com/momoheal/CinderWing

Would love feedback from anyone building desktop companions or agent-monitoring toys. RTs hugely appreciated 🙏

---

## 二、X 中文版（可作为引用推文或单独发中文圈）

**配图：m7-pet-hero + m5-ask-bubble + m3-task-panel + m7-skin-menu**

我是一个几乎零编程基础的设计师，这是我第一个正经开源的桌面软件：CinderWing 小烬翼。

一只住在 Windows 桌面上的 Q 版小黑龙，会盯着你的 AI 助手干活：任务开始、推进、需要你做选择、完成，它都会弹气泡告诉你，还带实时进度条，点一下直接跳回对应会话。

· 纯本地只读解析，不上传、不登录、没有服务器
· 多任务进度面板、决策点直接给可点选项
· 52 帧手绘级序列帧：呼吸、眨眼、喷火、被拖会晃、不理它会睡觉
· 形象是插件：上传一张角色概念图给 AI，就能自动生成 9 套动作并打包成新皮肤
· 全程用 AI 编程助手 + Python/PySide6 做的，仓库里有零基础全过程笔记

代码 MIT、美术 CC BY-NC，Windows 免安装绿色包已发 Release：
github.com/momoheal/CinderWing
欢迎桌面宠物/Agent 方向的朋友来玩，求转发 🐉

#开源 #Python #桌面宠物 #AI编程 #PySide6

---

## 三、小红书图文（中文）

**标题（二选一）：**

1. 零基础设计师靠 AI 写出了一只会汇报工作的桌面龙🐉开源了
2. 谁懂啊！AI 干活时终于有只小龙蹲在桌面给我报进度了

**正文：**

姐妹们/朋友们，我一个不会写代码的设计师，真的把自己的桌面宠物做出来了，还开源了😭

🐉 **它是什么**
一只 Q 版黑红小幼龙「小烬翼」，常驻在电脑桌面角落。
我用豆包工作（Doubao Work）跑 AI 任务的时候，它会盯着任务状态：
· 任务开始 → 弹气泡说一声
· 干活中 → 气泡上有实时进度条
· AI 问我选择题 → 选项直接变成按钮，点一下跳回对话框确认
· 好几个任务一起跑 → 点开就是多任务进度面板
· 任务结束 → 明确告诉你哪个任务完成了

✨ **它还会撒娇**
平时安安静静轻微呼吸、偶尔眨眼、偶尔挠挠痒；
久了不理它，会自己蜷起来睡觉（肚子还会起伏）；
点头部喷火、点身体扑咬、拖拽会慢悠悠晃、松手还会晕一下——
互动手感参考的是收藏式桌宠那种密度。

🎨 **最有成就感的：能换皮**
每只宠物就是一个文件夹插件。
我还做了一个「形象工坊」AI 技能：
只要喂给 AI 一张你家 OC / 喜欢的角色概念图，
它就会按桌宠需要的 9 套动作自动生成动画素材，
自动抠图、逐帧质检、打包成可切换的新皮肤。
理论上你可以把任何角色养在桌面上（版权自用哦）。

🛠️ **零基础是怎么做出来的**
全程和 AI 编程助手结对写的，Python + PySide6，
透明无边框窗口、读取本地数据库、AI 抠像修白块、打包成 exe……
踩的每一个坑我都写了白话笔记，放在仓库 docs 里，
想抄作业的零基础同学可以跟着走一遍。

📦 **怎么玩**
Windows 10/11，Release 里下载压缩包解压双击就能跑，不用装 Python；
想二开的直接 clone 仓库，代码 MIT 协议，美术资源 CC BY-NC。

GitHub 搜：**CinderWing**（链接放评论区/主页简介啦）

第一次做开源，紧张，有问题欢迎评论区问我，我会继续更新的！

**标签：**
#桌面宠物 #开源项目 #AI编程 #Python #程序员浪漫 #效率神器 #豆包 #OC #虚拟形象 #零基础学编程 #独立开发

**配图顺序建议（6 张以内）：**
1. m7-pet-hero.png（封面，小龙大图）
2. m5-ask-bubble.png（决策选项气泡，最有卖点）
3. m3-task-panel.png（多任务面板）
4. m7-skin-menu.png（更换形象）
5. m7-context-menu.png（右键菜单全貌）
6. m7-play-menu.png（逗逗它互动）

**小红书发布注意：**
- 正文里不要直接贴 GitHub 链接（会被限流），写"链接放评论区"，
  发布后第一条评论发链接；如果评论也被吞，就把链接放个人简介。
- 封面图建议加一行大字标题，例如"会汇报 AI 任务的桌面龙"。

---

## 四、发布顺序建议

1. 先发 X 英文线程（海外开发者/独立制作圈是这个项目最容易被看到的地方）
2. 同天发小红书（中文设计/AI 圈）
3. X 中文版可作为自己线程第 5 条下面的引用推文，或隔天单独发
4. 两边评论区第一条都自己发：仓库链接 + Release 免安装包链接
