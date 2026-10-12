# -*- mode: python ; coding: utf-8 -*-
"""CinderWing打包配置（onedir，无控制台窗口）。

构建：.venv\\Scripts\\python.exe -m PyInstaller --clean -y pet.spec
产物：dist\\CinderWing\\CinderWing.exe
"""
from PyInstaller.utils.hooks import collect_all

# 运行时只读资源（注意：config.json 不打包，它是可写的位置记忆，
# 打包后写到 %APPDATA%\\CinderWing）
datas = [
    ('assets/frames', 'assets/frames'),
    ('assets/sfx', 'assets/sfx'),
    ('skills', 'skills'),  # M6：一键导入的「桌宠形象工坊」技能包
]
binaries = []
hiddenimports = ['PySide6.QtMultimedia']

# ccl_chromium_reader 是 M2 读 IndexedDB 的依赖，且在函数内懒加载，
# 必须显式收集，否则打包后 ImportError
for pkg in ('ccl_chromium_reader',):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# 这些只在美术构建/离线工具里用，运行时不需要，排掉减小体积
excludes = ['rembg', 'onnxruntime', 'scipy', 'matplotlib', 'pytest',
            'IPython', 'notebook']

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CinderWing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='CinderWing',
)
