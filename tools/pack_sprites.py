"""Empacota arte gerada nos tamanhos exatos do motor e da atividade."""

from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "assets"


def pack():
    im = Image.open(
        OUT
        / (
            "player-body-source.png"
            if (OUT / "player-body-source.png").exists()
            else "player-source.png"
        )
    ).convert("RGBA")
    cells = []
    for row in range(2):
        for col in range(5):
            cell = im.crop(
                (
                    round(col * im.width / 5),
                    round(row * im.height / 2),
                    round((col + 1) * im.width / 5),
                    round((row + 1) * im.height / 2),
                )
            )
            bounds = (
                cell.getchannel("A").point(lambda a: 255 if a > 100 else 0).getbbox()
            )
            cells.append(cell.crop(bounds))
    scale = min(90 / max(c.width for c in cells), 120 / max(c.height for c in cells))
    result = Image.new("RGBA", (960, 128))
    for i, cell in enumerate(cells):
        cell = cell.resize(
            (round(cell.width * scale), round(cell.height * scale)),
            Image.Resampling.NEAREST,
        )
        result.paste(cell, (i * 96 + (96 - cell.width) // 2, 126 - cell.height), cell)
    result.save(OUT / "player.png")
    source = Image.open(OUT / "enemies-source.png").convert("RGBA")
    for name, box, size, flip in [
        ("guard.png", (0, 0, 500, source.height), (96, 128), True),
        ("drone.png", (500, 0, 1025, source.height), (78, 66), False),
        ("boss.png", (1025, 0, source.width, source.height), (240, 144), False),
    ]:
        cell = source.crop(box)
        cell = cell.crop(cell.getbbox())
        cell.thumbnail(size, Image.Resampling.NEAREST)
        if flip:
            cell = cell.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        final = Image.new("RGBA", size)
        final.paste(cell, ((size[0] - cell.width) // 2, size[1] - cell.height), cell)
        final.save(OUT / name)
    stone = Image.open(OUT / "stone-source.png").convert("RGBA")
    stone.resize((48, 48), Image.Resampling.NEAREST).save(OUT / "stone.png")
    stone.crop((0, round(stone.height * 0.22), stone.width, stone.height)).resize(
        (48, 48), Image.Resampling.NEAREST
    ).save(OUT / "wall.png")
    print("Sprites packed: player 960x128 / guard / drone / boss")


if __name__ == "__main__":
    pack()
