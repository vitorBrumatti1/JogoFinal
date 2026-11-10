"""Perigos com aviso visual e desenho de armas rotacionadas no mundo."""

import math
import arcade


class Hazard(arcade.SpriteSolidColor):
    def __init__(self, x, kind):
        super().__init__(
            14 if kind == "laser" else 42,
            410 if kind == "laser" else 15,
            color=(235, 75, 52),
        )
        self.kind = kind
        self.center_x = x
        self.bottom = 96
        self.fuse = None
        self.phase = 0.0
        self.exploded = False

    @property
    def warning(self):
        return self.kind == "laser" and 2 < self.phase < 2.9

    @property
    def active(self):
        return self.kind == "spikes" or (self.kind == "laser" and self.phase >= 2.9)

    def tick(self, dt, clock, player):
        self.phase = (clock + self.center_x * 0.001) % 4
        if self.kind == "mine" and not self.exploded:
            if (
                self.fuse is None
                and abs(player.center_x - self.center_x) < 100
                and player.bottom < 165
            ):
                self.fuse = 0.75
            if self.fuse is not None:
                self.fuse -= dt
                if self.fuse <= 0:
                    self.exploded = True
                    return True
        return False

    def draw_fx(self, clock):
        x = self.center_x
        if self.kind == "laser":
            arcade.draw_rect_filled(arcade.LBWH(x - 17, 495, 34, 16), (59, 78, 91))
            if self.warning or self.active:
                color = (255, 79, 60, 240) if self.active else (255, 209, 104, 120)
                arcade.draw_line(x, 96, x, 497, color, 9 if self.active else 2)
                if self.active:
                    arcade.draw_line(x, 96, x, 497, (255, 242, 199), 3)
        elif self.kind == "mine" and not self.exploded:
            arcade.draw_rect_filled(arcade.LBWH(x - 16, 96, 32, 9), (49, 56, 46))
            color = (
                (255, 72, 53)
                if self.fuse is not None and int(clock * 15) % 2
                else (255, 207, 89)
            )
            arcade.draw_circle_filled(x, 108, 4, color)
            if self.fuse is not None:
                arcade.draw_circle_outline(x, 105, 72, (255, 100, 60, 130), 2)
        elif self.kind == "spikes":
            for px in range(int(x - 21), int(x + 21), 9):
                arcade.draw_triangle_filled(
                    px, 96, px + 4, 115, px + 9, 96, (204, 220, 225)
                )


class Barrel(arcade.SpriteSolidColor):
    def __init__(self, x, y):
        super().__init__(24, 34, color=(177, 63, 39))
        self.position = x, y
        self.hp = 1

    def draw_fx(self):
        x = self.left
        y = self.bottom
        for dy in (5, 26):
            arcade.draw_rect_filled(arcade.LBWH(x - 2, y + dy, 28, 3), (71, 57, 48))
        arcade.draw_triangle_filled(
            x + 7, y + 11, x + 12, y + 23, x + 17, y + 11, (255, 209, 90)
        )


def draw_gun(x, y, angle, kind, recoil=0):
    """As peças giram juntas ao redor da mão; o corpo continua na máquina de estados."""
    c, s = math.cos(angle), math.sin(angle)
    flip = -1 if c < 0 else 1

    def part(points, color):
        pts = [
            (x + (a - recoil) * c - b * flip * s, y + (a - recoil) * s + b * flip * c)
            for a, b in points
        ]
        arcade.draw_polygon_filled(pts, color)

    def box(a, b, w, h, color):
        part([(a, b), (a + w, b), (a + w, b + h), (a, b + h)], color)

    dark = (23, 35, 42)
    steel = (88, 111, 120)
    length = {"ak": 31, "smg": 24, "shotgun": 36, "rifle": 43}[kind]
    box(-9, -4, 18, 8, dark)
    box(-8, 0, 17, 3, steel)
    box(-17, -3, 10, 6, (158, 96, 53) if kind in ("ak", "shotgun") else dark)
    box(7, -2, length - 7, 4, dark)
    box(10, -1, 9, 4, (165, 109, 59) if kind in ("ak", "shotgun") else steel)
    box(length - 2, -1, 5, 3, (151, 165, 157))
    if kind != "shotgun":
        part([(1, -3), (8, -3), (6, -13), (1, -11)], dark)
    if kind == "rifle":
        box(-1, 5, 16, 4, dark)
        box(2, 7, 8, 3, (97, 137, 161))
    box(-8, -7, 8, 5, (234, 181, 121))
