#!/usr/bin/env python3
"""Generate web logo / favicon / Open Graph assets from images/logo-original.png.

Usage: python3 scripts/build_logo_assets.py   (run from repo root; needs Pillow)
The 1.8 MB master is not committed (gitignored); copy it to images/logo-original.png locally first.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"
SRC = IMG / "logo-original.png"

CREAM = (245, 237, 220)        # #F5EDDC brand cream
LOGO_BG = (252, 238, 217)      # cream sampled from the logo artwork itself
NAVY = (27, 42, 74)            # #1B2A4A
AMBER = (216, 155, 61)         # #D89B3D (accent only)

src = Image.open(SRC).convert("RGB")
W = src.width  # 1254

# The ears poke outside the navy ring (content reaches ~675px from centre on a
# 1254px canvas), so pad onto a larger logo-cream canvas before cropping to a
# circle -- otherwise border-radius:50% would clip the ear tips.
PAD = 1420
padded = Image.new("RGB", (PAD, PAD), LOGO_BG)
padded.paste(src, ((PAD - W) // 2, (PAD - W) // 2))


def circle_logo(size: int) -> Image.Image:
    """Circular RGBA badge (transparent outside the disc), anti-aliased."""
    ss = 4
    big = padded.resize((size * ss, size * ss), Image.LANCZOS)
    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big.width - 1, big.height - 1), fill=255)
    big.putalpha(mask)
    return big.resize((size, size), Image.LANCZOS)


def save_png(im: Image.Image, path: Path, colors: int | None = None):
    if colors:
        im = im.quantize(colors=colors, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG)
    im.save(path, optimize=True)


for size in (512, 256):
    im = circle_logo(size)
    save_png(im, IMG / f"logo-{size}.png", colors=256)
    im.save(IMG / f"logo-{size}.webp", quality=86, method=6)

# Favicons: tighter square crop (ring fills the icon) on logo cream, opaque.
inset = 40
tight = src.crop((inset, inset, W - inset, W - inset))
tight.resize((32, 32), Image.LANCZOS).save(ROOT / "favicon-32.png", optimize=True)
# 16px: ring is unreadable at that size, so use a face-only crop.
face = src.crop((215, 40, 1040, 865)).resize((16, 16), Image.LANCZOS)
ico32 = tight.resize((32, 32), Image.LANCZOS)
ico48 = tight.resize((48, 48), Image.LANCZOS)
ico48.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
           append_images=[face, ico32])

# Apple touch icon: opaque 180x180 (iOS fills transparency with black).
apple = Image.new("RGB", (W + 80, W + 80), LOGO_BG)
apple.paste(src, (40, 40))
apple.resize((180, 180), Image.LANCZOS).save(ROOT / "apple-touch-icon.png", optimize=True)

# Open Graph 1200x630: cream bg, logo centred-left, navy wordmark + amber underline.
OW, OH = 1200, 630
og = Image.new("RGB", (OW, OH), CREAM)
d = ImageDraw.Draw(og)
LS = 460
logo = circle_logo(LS)
lx, ly = 90, (OH - LS) // 2
# soft shadow + navy hairline around the badge
shadow = Image.new("L", (OW, OH), 0)
ImageDraw.Draw(shadow).ellipse((lx + 4, ly + 14, lx + LS + 4, ly + LS + 14), fill=70)
shadow = shadow.filter(ImageFilter.GaussianBlur(18))
og.paste(Image.new("RGB", (OW, OH), (190, 175, 150)), (0, 0), shadow)
d = ImageDraw.Draw(og)
d.ellipse((lx - 3, ly - 3, lx + LS + 2, ly + LS + 2), fill=NAVY)
og.paste(logo, (lx, ly), logo)


def font(cands, size, axes=None):
    """First font that loads; `axes` = {axis name: value} for variable fonts."""
    for c in cands:
        try:
            f = ImageFont.truetype(c, size)
        except OSError:
            continue
        if axes:
            try:
                cur = {a["name"].decode() if isinstance(a["name"], bytes) else a["name"]: a
                       for a in f.get_variation_axes()}
                f.set_variation_by_axes([axes.get(n, a["default"]) for n, a in cur.items()])
            except Exception:
                pass
        return f
    return ImageFont.load_default(size)


GF = "/usr/share/fonts/truetype/sand-box/google"
display = [f"{GF}/Fraunces/Fraunces-VariableFont_SOFT,WONK,opsz,wght.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
sans = [f"{GF}/Nunito/Nunito-VariableFont_wght.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

tx = lx + LS + 70
f1 = font(display, 92, {"Weight": 700, "Optical Size": 60, "Wonky": 0})
f_tag = font(sans, 32, {"Weight": 600})
lines = ["DOG", "UNPACKED"]
y = 175
for ln in lines:
    d.text((tx, y), ln, font=f1, fill=NAVY)
    y += 98
bbox = d.textbbox((tx, 175 + 98), "UNPACKED", font=f1)
uy = bbox[3] + 22
d.rounded_rectangle((tx + 2, uy, tx + 2 + 150, uy + 8), radius=4, fill=AMBER)
d.text((tx, uy + 34), "He\u2019s not broken.\nHe\u2019s bred that way.", font=f_tag, fill=NAVY, spacing=8)
save_png(og, IMG / "og-image.png", colors=256)

for p in sorted([*IMG.glob("logo-*"), IMG / "og-image.png", ROOT / "favicon.ico",
                 ROOT / "favicon-32.png", ROOT / "apple-touch-icon.png"]):
    print(f"{p.relative_to(ROOT)}: {p.stat().st_size/1024:.1f} KB")
