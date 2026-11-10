"""Assets pixel-perfect e áudio original reproduzíveis; não exige rede."""

from pathlib import Path
from PIL import Image, ImageDraw
import math, random, wave, struct

OUT = Path(__file__).resolve().parents[1] / "assets"
OUT.mkdir(exist_ok=True)
rng = random.Random(83)


def save(im, name, scale=3):
    im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST).save(
        OUT / name
    )


def soldier(frame, enemy=False):
    im = Image.new("RGBA", (32, 42))
    d = ImageDraw.Draw(im)
    ink = "#202b2d"
    skin = "#e5af73"
    light = "#ffcf95"
    uniform = "#657c40" if not enemy else "#ae8850"
    dy = 1 if frame in (3, 5, 7, 9) else 0
    # silhouette, neck, head, headband and rear ribbons
    d.rectangle((10, 8 + dy, 17, 15 + dy), fill=ink)
    d.rectangle((11, 8 + dy, 17, 13 + dy), fill=skin)
    d.rectangle((14, 9 + dy, 18, 11 + dy), fill=light)
    d.rectangle((16, 9 + dy, 17, 10 + dy), fill=ink)
    d.rectangle((10, 6 + dy, 17, 8 + dy), fill="#412c26" if not enemy else "#657345")
    d.rectangle((10, 8 + dy, 16, 9 + dy), fill="#b63f3a" if not enemy else "#8b9b57")
    d.line((10, 9 + dy, 6, 13 + dy), fill="#b63f3a", width=2)
    # torso / vest
    d.polygon([(10, 14 + dy), (17, 14 + dy), (20, 25), (9, 25), (8, 19)], fill=ink)
    d.rectangle((10, 15 + dy, 16, 23), fill=uniform)
    d.line((11, 15 + dy, 11, 23), fill="#c3bd7e", width=2)
    d.rectangle((13, 18, 16, 21), fill="#39462e")
    d.rectangle((9, 24, 19, 26), fill="#483d2e")
    d.rectangle((14, 24, 15, 25), fill="#e0bf58")
    # eight distinct leg poses
    offsets = [0, -3, -4, -2, 0, 3, 4, 2]
    step = offsets[(frame - 2) % 8] if frame >= 2 else 0
    if frame == 1:
        legs = [(11, 26, 8, 30, 13, 32), (17, 26, 21, 29, 23, 32)]
    else:
        legs = [
            (11, 26, 11 + step, 31, 10 + step, 36),
            (17, 26, 17 - step, 31, 18 - step, 36),
        ]
    for x, y, kx, ky, fx, fy in legs:
        d.line((x, y, kx, ky, fx, fy), fill=ink, width=5)
        d.line((x, y, kx, ky, fx, fy - 1), fill=uniform, width=3)
        d.rectangle((fx - 2, fy - 1, fx + 3, fy + 1), fill="#242b2c")
    # AK silhouette: wooden stock, receiver, curved magazine, barrel
    d.rectangle((14, 18 + dy, 28, 20 + dy), fill=ink)
    d.rectangle((13, 19 + dy, 17, 21 + dy), fill="#a16234")
    d.rectangle((23, 18 + dy, 27, 19 + dy), fill="#a16b3e")
    d.rectangle((20, 20 + dy, 22, 24 + dy), fill="#344047")
    d.point((21, 25 + dy), fill=ink)
    d.line((27, 19 + dy, 31, 19 + dy), fill=ink, width=2)
    d.point((29, 17 + dy), fill=ink)
    d.rectangle((17, 17 + dy, 20, 19 + dy), fill=skin)
    d.line((9, 16 + dy, 10, 20 + dy, 16, 21 + dy), fill=skin, width=3)
    return im


sheet = Image.new("RGBA", (960, 128))
for f in range(10):
    sheet.paste(soldier(f).resize((96, 126), Image.Resampling.NEAREST), (f * 96, 2))
sheet.save(OUT / "player.png")
save(soldier(0, True), "guard.png")
# compact drone / armored guardian
for boss in (False, True):
    im = Image.new("RGBA", (64 if boss else 24, 48 if boss else 20))
    d = ImageDraw.Draw(im)
    if boss:
        d.rectangle((5, 18, 58, 42), fill="#26343c")
        d.rectangle((9, 16, 54, 34), fill="#758178")
        d.rectangle((13, 18, 50, 21), fill="#b8b68e")
        d.rectangle((20, 6, 44, 20), fill="#374b51")
        d.rectangle((23, 8, 41, 11), fill="#ed6f3c")
        d.rectangle((38, 13, 63, 17), fill="#273238")
        for x in range(9, 55, 9):
            d.rectangle((x, 35, x + 6, 42), fill="#151f29")
            d.rectangle((x + 1, 36, x + 5, 39), fill="#747e78")
        for x in (10, 48):
            d.rectangle((x, 23, x + 5, 27), fill="#e5b856")
    else:
        d.polygon([(3, 7), (8, 4), (17, 4), (21, 7), (18, 14), (6, 14)], fill="#263a46")
        d.rectangle((7, 6, 17, 10), fill="#81999b")
        d.rectangle((10, 8, 14, 11), fill="#fa6b43")
        d.line((0, 3, 8, 3), fill="#253c4b", width=2)
        d.line((16, 3, 23, 3), fill="#253c4b", width=2)
    save(im, "boss.png" if boss else "drone.png")
# 48x48 mossy sandstone tile, handmade pixel clusters
im = Image.new("RGBA", (16, 16), "#555d48")
d = ImageDraw.Draw(im)
d.rectangle((1, 3, 14, 14), fill="#7b8060")
d.line((1, 14, 14, 14, 14, 3), fill="#343f3c", width=2)
d.line((2, 5, 12, 5, 12, 12, 4, 12, 4, 7, 10, 7, 10, 10, 7, 10), fill="#a3a27b")
d.rectangle((0, 0, 15, 2), fill="#528b40")
for _ in range(20):
    x, y = rng.randrange(16), rng.randrange(4)
    d.point((x, y), fill=rng.choice(["#a5cf59", "#75ae3e", "#2e663a"]))
save(im, "stone.png")
im = Image.new("RGBA", (16, 8))
d = ImageDraw.Draw(im)
d.rectangle((0, 0, 15, 2), fill="#c0a16c")
d.rectangle((0, 3, 15, 4), fill="#594d3c")
d.line((0, 4, 7, 7, 15, 4), fill="#67553b", width=2)
save(im, "bridge.png")
im = Image.new("RGBA", (9, 9))
d = ImageDraw.Draw(im)
d.ellipse((0, 0, 8, 8), fill="#724520")
d.ellipse((1, 0, 7, 7), fill="#ffe281")
d.ellipse((2, 1, 6, 6), fill="#e9a832")
d.line((4, 2, 4, 5), fill="#fff4ac")
save(im, "coin.png")
# blue sky fallback; detailed distant silhouettes
im = Image.new("RGB", (480, 270))
d = ImageDraw.Draw(im)
for y in range(270):
    d.line(
        (0, y, 480, y),
        fill=(104 + int(y * 0.12), 172 + int(y * 0.15), 234 - int(y * 0.09)),
    )
for x, y in [(25, 36), (160, 60), (330, 26), (420, 83)]:
    d.rectangle((x, y, x + 32, y + 3), fill="#a7d8ed")
    d.rectangle((x + 8, y - 4, x + 21, y), fill="#a7d8ed")
for layer, col, base in [(0, "#85b8bc", 214), (1, "#639c99", 244)]:
    for x in range(-20, 500, 30):
        h = rng.randrange(25, 85)
        d.polygon(
            [(x, 270), (x + 10, base - h), (x + 24, base - h - 7), (x + 43, 270)],
            fill=col,
        )
for x in range(20, 500, 89):
    h = rng.randrange(40, 90)
    d.rectangle((x, 270 - h, x + 24, 270), fill="#588a83")
    d.rectangle((x - 3, 270 - h, x + 27, 274 - h), fill="#719e8e")
save(im, "sky.png", 3)
# synthesized original mono PCM, small and independent of audio libraries
for name, dur, freq in [
    ("shot", 0.085, 130),
    ("hit", 0.12, 90),
    ("coin", 0.15, 950),
    ("jump", 0.14, 360),
    ("reload", 0.26, 180),
    ("boom", 0.44, 55),
    ("clear", 0.65, 660),
]:
    samples = []
    sr = 22050
    for i in range(int(dur * sr)):
        t = i / sr
        env = (1 - t / dur) ** 2
        tone = math.sin(
            2
            * math.pi
            * (
                freq * t
                + (220 * t * t if name in ("coin", "jump", "clear") else -30 * t * t)
            )
        )
        noise = rng.uniform(-1, 1)
        v = (
            (noise * 0.7 + tone * 0.3)
            if name in ("shot", "hit", "boom", "reload")
            else tone * 0.65
        )
        samples.append(struct.pack("<h", int(15000 * v * env)))
    with wave.open(str(OUT / (name + ".wav")), "wb") as w:
        w.setparams((1, 2, sr, 0, "NONE", "not compressed"))
        w.writeframes(b"".join(samples))
print("Assets written to", OUT)

# Restore production sprites from the preserved generated sources.
if (OUT / "player-source.png").exists() and (OUT / "enemies-source.png").exists():
    from pack_sprites import pack

    pack()
