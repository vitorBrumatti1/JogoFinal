"""Pixel lettering and CRT cabinet treatment; UI stays fully interactive."""

from pathlib import Path
from functools import lru_cache
import math
import unicodedata
from PIL import Image, ImageDraw
import arcade
from world_fx import draw_gun

# Exact bitmap alphabet: native UI assets, no system font dependency.
ROWS = {
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01111/10000/10000/10000/10000/10000/01111",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01111/10000/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "11111/00100/00100/00100/00100/00100/11111",
    "J": "00111/00010/00010/00010/10010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/10101/01010",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00010/00100/01000/11111",
    "3": "11110/00001/00001/01110/00001/00001/11110",
    "4": "00010/00110/01010/10010/11111/00010/00010",
    "5": "11111/10000/10000/11110/00001/00001/11110",
    "6": "01111/10000/10000/11110/10001/10001/01110",
    "7": "11111/00001/00010/00100/01000/01000/01000",
    "8": "01110/10001/10001/01110/10001/10001/01110",
    "9": "01110/10001/10001/01111/00001/00001/11110",
    ":": "00000/00100/00100/00000/00100/00100/00000",
    "/": "00001/00010/00010/00100/01000/01000/10000",
    "-": "00000/00000/00000/11111/00000/00000/00000",
    "!": "00100/00100/00100/00100/00100/00000/00100",
    ".": "00000/00000/00000/00000/00000/00100/00100",
    "+": "00000/00100/00100/11111/00100/00100/00000",
}


@lru_cache(maxsize=256)
def lettering(message, scale, color, style):
    message = "".join(
        c
        for c in unicodedata.normalize("NFD", message.upper())
        if not unicodedata.combining(c)
    )
    mask = Image.new("L", (len(message) * 6 + 4, 11))
    d = ImageDraw.Draw(mask)
    for i, char in enumerate(message):
        for y, row in enumerate(ROWS.get(char, "00000/" * 6 + "00000").split("/")):
            for x, value in enumerate(row):
                if value == "1":
                    d.point((i * 6 + x + 2, y + 1), 255)
    im = Image.new("RGBA", mask.size)
    draw = ImageDraw.Draw(im)
    # One-pixel outline and extrusion before nearest-neighbour scaling.
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
        im.paste((5, 8, 24, 255), (dx, dy), mask)
    fill = Image.new("RGBA", mask.size)
    fd = ImageDraw.Draw(fill)
    for y in range(fill.height):
        if style == "metal":
            c = (
                (246, 247, 255, 255)
                if y < 4
                else ((165, 161, 210, 255) if y < 6 else (218, 219, 245, 255))
            )
        elif style == "gold":
            c = (
                (255, 247, 103, 255)
                if y < 4
                else ((255, 175, 34, 255) if y < 6 else (243, 88, 31, 255))
            )
        else:
            c = (*color[:3], 255)
        fd.line((0, y, fill.width, y), fill=c)
    im.paste(fill, (0, 0), mask)
    return arcade.Texture(
        im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    )


def pixel_text(
    message, x, y, scale=3, color=(244, 245, 255), center=False, style="plain"
):
    tex = lettering(message, scale, tuple(color), style)
    arcade.draw_texture_rect(
        tex,
        arcade.LBWH(x - tex.width / 2 if center else x, y, tex.width, tex.height),
        pixelated=True,
    )


@lru_cache(maxsize=4)
def scanline_texture(width, height):
    im = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(im)
    for y in range(0, height, 4):
        draw.line((7, y, width - 7, y), fill=(6, 6, 25, 17))
    return arcade.Texture(im)


def cabinet_overlay(window, width=960, height=640):
    if not getattr(window, "arcade_filter", False):
        return
    if not window.reduced_effects:
        tex = scanline_texture(width, height)
        arcade.draw_texture_rect(tex, arcade.LBWH(0, 0, width, height), pixelated=True)
    for left in (0, width - 7):
        arcade.draw_rect_filled(arcade.LBWH(left, 0, 7, height), (6, 5, 19, 245))
    for y in (0, height - 7):
        arcade.draw_rect_filled(arcade.LBWH(0, y, width, 7), (6, 5, 19, 245))
    for x in (8, width - 10):
        arcade.draw_rect_filled(arcade.LBWH(x, 14, 2, height - 28), (71, 91, 207, 100))
    for x in (0, width):
        for y in (0, height):
            sx = 1 if x == 0 else -1
            sy = 1 if y == 0 else -1
            arcade.draw_triangle_filled(
                x, y, x + sx * 19, y, x, y + sy * 19, (4, 4, 14)
            )


def draw_menu_buttons(ui):
    hovered = next((b.id for b in ui.buttons if b.contains(*ui.pointer)), None)
    for b in ui.buttons:
        x, y, w, h = b.box
        active = b.id == (hovered or getattr(ui, "selection", "play"))
        border = (255, 230, 58) if active else (34, 188, 248)
        fill = (157, 8, 40) if active else (6, 22, 76)
        if active and not ui.view.window.reduced_effects:
            for pad, alpha in ((8, 28), (5, 60)):
                arcade.draw_rect_outline(
                    arcade.LBWH(x - pad, y - pad, w + 2 * pad, h + 2 * pad),
                    (255, 70, 35, alpha),
                    3,
                )
        outline = [
            (x + 7, y),
            (x + w - 7, y),
            (x + w, y + 7),
            (x + w, y + h - 7),
            (x + w - 7, y + h),
            (x + 7, y + h),
            (x, y + h - 7),
            (x, y + 7),
        ]
        arcade.draw_polygon_filled([(px + 3, py - 4) for px, py in outline], (3, 4, 19))
        arcade.draw_polygon_filled(outline, border)
        arcade.draw_rect_filled(arcade.LBWH(x + 5, y + 5, w - 10, h - 10), fill)
        arcade.draw_line(
            x + 9,
            y + h - 8,
            x + w - 9,
            y + h - 8,
            (255, 146, 98) if active else (58, 122, 220),
            2,
        )
        if active:
            offset = math.sin(ui.time * 7) * 3
            arcade.draw_triangle_filled(
                x - 20 + offset,
                y + h / 2,
                x - 31 + offset,
                y + h / 2 + 10,
                x - 31 + offset,
                y + h / 2 - 10,
                (255, 224, 46),
            )
        icon = b.id
        cx = x + 29
        cy = y + h / 2
        white = (255, 232, 77) if active else (225, 241, 255)
        if icon == "play":
            arcade.draw_triangle_filled(
                cx - 9, cy - 13, cx - 9, cy + 13, cx + 12, cy, white
            )
        elif icon == "shop":
            arcade.draw_line(cx - 12, cy + 9, cx + 11, cy + 9, white, 4)
            arcade.draw_line(cx - 8, cy + 9, cx - 4, cy - 4, white, 3)
            arcade.draw_line(cx + 11, cy + 9, cx + 6, cy - 4, white, 3)
            arcade.draw_line(cx - 4, cy - 4, cx + 6, cy - 4, white, 3)
            for px in (cx - 3, cx + 7):
                arcade.draw_rect_filled(arcade.LBWH(px - 2, cy - 12, 5, 5), white)
        elif icon == "options":
            arcade.draw_circle_outline(cx, cy, 10, white, 5)
            for a in range(0, 360, 60):
                a = math.radians(a)
                arcade.draw_rect_filled(
                    arcade.LBWH(
                        cx + math.cos(a) * 12 - 3, cy + math.sin(a) * 12 - 3, 6, 6
                    ),
                    white,
                )
        elif icon == "about":
            for dx in (-8, 8):
                arcade.draw_rect_filled(arcade.LBWH(cx + dx - 4, cy + 2, 8, 9), white)
                arcade.draw_rect_filled(
                    arcade.LBWH(cx + dx - 7, cy - 12, 14, 10), white
                )
        else:
            arcade.draw_circle_outline(cx, cy, 12, white, 4)
            arcade.draw_rect_filled(arcade.LBWH(cx - 3, cy + 2, 6, 15), white)
        pixel_text(b.label, x + 66, y + 13, 4 if len(b.label) < 8 else 3)


class ArcadeMenuScene:
    def __init__(self):
        base = Path(__file__).parent / "assets"
        self.background = arcade.load_texture(str(base / "arcade-menu.png"))
        sheet = arcade.load_spritesheet(str(base / "player.png"))
        self.frames = sheet.get_texture_grid(size=(96, 128), columns=10, count=10)
        self.portrait = arcade.Texture(self.frames[0].image.crop((25, 4, 73, 56)))
        self.hero = arcade.Sprite(self.frames[0], scale=0.9)
        self.hero.position = (465, 200)
        self.enemy = arcade.Sprite(str(base / "guard.png"), scale=0.65)
        self.enemy.position = (835, 335)
        self.enemy.texture = self.enemy.texture.flip_left_right()
        self.sprites = arcade.SpriteList()
        self.sprites.extend([self.hero, self.enemy])
        self.coin = arcade.load_texture(str(base / "coin.png"))

    def draw(self, t):
        arcade.draw_texture_rect(
            self.background, arcade.LBWH(0, 0, 960, 640), pixelated=True
        )
        for i in range(14):
            x = (i * 137 + t * 6) % 960
            y = 220 + (i * 83) % 350
            arcade.draw_rect_filled(arcade.LBWH(x, y, 2, 2), (64, 133, 255, 100))
        # Original game name, in the two-tier metallic/gold composition of the reference.
        cx = 643
        cy = 548
        for i in range(8):
            a = i * math.pi / 4
            arcade.draw_rect_filled(
                arcade.LBWH(
                    cx + math.cos(a) * 31 - 9, cy + math.sin(a) * 31 - 9, 18, 18
                ),
                (162, 157, 205),
            )
        arcade.draw_circle_filled(cx, cy, 27, (115, 117, 164))
        arcade.draw_circle_filled(cx, cy, 14, (19, 24, 73))
        for i in range(4):
            arcade.draw_rect_filled(
                arcade.LBWH(374 + i * 14, 511 - i * 15, 470 - i * 28, 9), (181, 14, 48)
            )
        pixel_text("COIN", 643, 482, 9, center=True, style="metal")
        pixel_text("COMMANDO", 643, 412, 7, center=True, style="gold")
        # Real sprite animation and muzzle flashes, rather than a static image.
        self.hero.texture = self.frames[0 if int(t * 2) % 8 < 5 else 2 + int(t * 9) % 8]
        self.hero.center_y = 200 + (math.sin(t * 3) * 2)
        self.enemy.center_x = 830 + math.sin(t * 0.8) * 28
        self.sprites.draw(pixelated=True)
        draw_gun(self.hero.center_x, self.hero.center_y + 6, 0, "ak")
        if int(t * 9) % 9 in (0, 1):
            from combat import muzzle_flash

            muzzle_flash(self.hero.center_x + 31, self.hero.center_y + 6, 0)
            for i in range(3):
                x = 520 + (t * 370 + i * 49) % 295
                arcade.draw_line(x, 206, x + 19, 206, (255, 229, 87), 4)
        for i in range(3):
            arcade.draw_texture_rect(
                self.coin,
                arcade.LBWH(672 + i * 40, 155 + math.sin(t * 3 + i) * 3, 19, 23),
                pixelated=True,
            )
        # Header is an arcade display, not fake saved progress.
        arcade.draw_rect_filled(arcade.LBWH(20, 562, 63, 63), (5, 7, 28))
        arcade.draw_rect_outline(arcade.LBWH(20, 562, 63, 63), (180, 190, 244), 3)
        arcade.draw_texture_rect(
            self.portrait, arcade.LBWH(22, 564, 59, 59), pixelated=True
        )
        pixel_text("X 3", 87, 582, 3)
        for i in range(3):
            x = 190 + i * 33
            y = 594
            arcade.draw_polygon_filled(
                [
                    (x - 12, y),
                    (x - 12, y + 9),
                    (x - 4, y + 13),
                    (x, y + 8),
                    (x + 4, y + 13),
                    (x + 12, y + 9),
                    (x + 12, y),
                    (x, y - 14),
                ],
                (246, 39, 83),
            )
            arcade.draw_rect_filled(arcade.LBWH(x - 8, y + 5, 5, 4), (255, 177, 192))
        arcade.draw_texture_rect(
            self.coin, arcade.LBWH(595, 588, 20, 24), pixelated=True
        )
        pixel_text("ARCADE", 625, 582, 3)
        pixel_text("SCORE 000000", 760, 588, 2)
        pixel_text("R RANKING / I AJUDA", 475, 37, 2, color=(166, 187, 255))
        if int(t * 2) % 2:
            pixel_text("PRESS START", 650, 82, 2, center=True, color=(255, 222, 87))
