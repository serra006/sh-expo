# -*- coding: utf-8 -*-
"""生成 App 图标：深青绿渐变底 + 白色「展」字 + 青绿下划线 + 琥珀圆点。

排版用固定坐标，不依赖文字墨迹测量，保证各尺寸缩放后位置一致。
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "app", "src", "main", "res")
FONT = "C:/Windows/Fonts/msyhbd.ttc"
SIZES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}

S = 512
C_TOP, C_BOT = (22, 74, 62), (6, 13, 11)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---- 底：垂直渐变 ----
base = Image.new("RGB", (S, S), C_BOT)
d = ImageDraw.Draw(base)
for y in range(S):
    d.line([(0, y), (S, y)], fill=lerp(C_TOP, C_BOT, (y / S) ** 0.8))

# ---- 左上柔光（RGBA 叠加，无硬边）----
glow = Image.new("L", (S, S), 0)
ImageDraw.Draw(glow).ellipse([-int(S * .30), -int(S * .55), int(S * .95), int(S * .55)], fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(S * .22)).point(lambda v: int(v * 0.38))
tint = Image.new("RGB", (S, S), (45, 212, 167))
base = Image.composite(tint, base, glow)

# ---- 文字与装饰：固定坐标 ----
img = base.convert("RGBA")
d = ImageDraw.Draw(img)

GLYPH_Y = int(S * 0.442)          # 字心
font = ImageFont.truetype(FONT, int(S * 0.46))
d.text((S // 2, GLYPH_Y), "展", font=font, fill=(240, 253, 249), anchor="mm")

BAR_Y = int(S * 0.780)            # 下划线中线
BAR_W, BAR_H = int(S * 0.255), int(S * 0.042)
BAR_X = int(S * 0.5 - BAR_W * 0.60)   # 略左移，给右侧圆点留位
d.rounded_rectangle([BAR_X, BAR_Y - BAR_H // 2, BAR_X + BAR_W, BAR_Y + BAR_H // 2],
                    radius=BAR_H // 2, fill=(45, 212, 167))

R = int(S * 0.030)
DOT_X = BAR_X + BAR_W + int(S * 0.055)
d.ellipse([DOT_X - R, BAR_Y - R, DOT_X + R, BAR_Y + R], fill=(245, 165, 36))

for name, px in SIZES.items():
    out_dir = os.path.join(RES, "mipmap-" + name)
    os.makedirs(out_dir, exist_ok=True)
    img.resize((px, px), Image.LANCZOS).convert("RGB").save(
        os.path.join(out_dir, "ic_launcher.png"))
    print("mipmap-%s/ic_launcher.png %dpx" % (name, px))

img.convert("RGB").save(os.path.join(BASE, "icon_512.png"))
print("icon_512.png")
