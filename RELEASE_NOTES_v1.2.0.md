# CinderWing v1.2.0

A chibi dragon desktop pet for Windows that watches your Doubao Work agents and
reports task start / progress / decisions / completion in speech bubbles with
progress bars — Codex Pets style, fully local and read-only.

## Highlights in v1.2.0

- **Skins & character packs** — every pet is a folder (`packs/<id>/`, 9 animation
  sets + `pack.json`); switch instantly from the right-click menu, missing
  animations fall back to the built-in dragon.
- **Asset Forge skill** — one click installs an AI skill into Doubao Work;
  upload one concept image and get all 9 cyan-screen animation sheets, then
  `tools/pack_build.py` cuts out, aligns, QA-checks (magenta contact sheet) and
  packages a switchable skin.
- **Open-source release** — renamed to the original character CinderWing (小烬翼),
  code under MIT, art/audio under CC BY-NC 4.0, English README, privacy scrubbed.

## Also included (v1.0–v1.1)

- 52-frame 2D animation: belly breathing, eye-only blinks, scratches, fire
  breath, lunge, cheer, drag sway, sleep with breathing
- Read-only IndexedDB polling (3 s), task state machine, blob fallback parsing
- Speech bubbles with progress bars, multi-task panel, clickable decision
  option buttons, deep-link jump into the conversation
- Right-click menu, tray icon, single instance, optional auto-start
- PyInstaller one-folder build — no Python install required

## Download

- **CinderWing_v1.2.0.zip** — unpack and double-click `CinderWing.exe`
  (Windows 10/11). Run `开机自启-安装.bat` once to enable auto-start.
- Or clone and run from source — see [README.en.md](README.en.md).

## Privacy

No server, no telemetry. The app only takes read-only snapshots of the local
Doubao Work IndexedDB and never writes to it. Not affiliated with or endorsed
by ByteDance / Doubao Work.

**Full Changelog**: https://github.com/momoheal/CinderWing/compare/v1.1.0...v1.2.0
