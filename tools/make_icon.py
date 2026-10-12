"""把核心形象图转成 Windows 多尺寸 .ico（打包用图标）。"""
from PIL import Image

src = "assets/core/core-dragon.png"
dst = "assets/app.ico"

img = Image.open(src).convert("RGBA")
# core 图角色基本占满，轻微内缩一点避免图标里贴边
canvas = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
canvas.alpha_comductor = None
canvas.alpha_composite(img.resize((1900, 1900)), (74, 74))
canvas.save(dst, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                        (64, 64), (128, 128), (256, 256)])
print("saved", dst)
