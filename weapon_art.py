"""Geometria única e sprites pixelados do arsenal, sem alterar balanceamento."""

from dataclasses import dataclass
from functools import lru_cache
import math
from PIL import Image, ImageDraw
import arcade

MUZZLES = {"ak": 34, "smg": 27, "shotgun": 39, "rifle": 46}
RECOIL = {"ak": 2.0, "smg": 1.1, "shotgun": 4.3, "rifle": 3.5}
FLASH_TIME = {"ak": 0.035, "smg": 0.025, "shotgun": 0.055, "rifle": 0.04}
TRAILS = {"ak": 11, "smg": 8, "shotgun": 8, "rifle": 16, "hostile": 9}
COLORS = {
    "ak": (255, 211, 89),
    "smg": (162, 236, 224),
    "shotgun": (255, 177, 108),
    "rifle": (189, 215, 255),
    "hostile": (255, 123, 164),
}


@dataclass(frozen=True)
class GunPose:
    pivot: tuple
    angle: float
    kind: str
    recoil: float = 0.0

    def point(self, x, y=0):
        c, s = math.cos(self.angle), math.sin(self.angle)
        flip = -1 if c < 0 else 1
        return (
            self.pivot[0] + (x - self.recoil) * c - y * flip * s,
            self.pivot[1] + (x - self.recoil) * s + y * flip * c,
        )

    @property
    def muzzle(self):
        return self.point(MUZZLES[self.kind])

    @property
    def grip(self):
        return self.point(-5, -5)

    @property
    def support(self):
        return self.point(12, -3)


@lru_cache(maxsize=8)
def gun_texture(kind, flip=False):
    length = MUZZLES[kind]
    im = Image.new("RGBA", (length + 20, 27))
    d = ImageDraw.Draw(im)

    # Coords are local to grip, so muzzle pixels match GunPose exactly.
    def box(x, y, w, h, color):
        d.rectangle((x + 18, 12 - y - h, x + 18 + w - 1, 12 - y), fill=color)

    ink = "#101b28"
    steel = "#5d7481"
    light = "#a3b6bb"
    wood = "#a46d3f"
    box(-18, -4, 12, 8, ink)
    box(-17, -2, 10, 5, wood if kind in ("ak", "shotgun") else "#45566c")
    box(-8, -5, 20, 9, ink)
    box(-7, 0, 20, 3, steel)
    box(-5, 3, 10, 1, light)
    box(10, -2, length - 10, 4, ink)
    box(10, -1, 10, 4, wood if kind in ("ak", "shotgun") else steel)
    box(length - 3, -1, 4, 3, light)
    box(length - 2, 1, 2, 2, ink)
    if kind == "ak":
        box(0, -12, 5, 8, ink)
        box(3, -13, 4, 4, ink)
        box(1, -10, 2, 5, steel)
    elif kind == "smg":
        box(3, -13, 5, 9, ink)
        box(4, -10, 2, 5, steel)
    elif kind == "shotgun":
        box(14, -4, 12, 2, steel)
        box(9, -3, 10, 4, wood)
    else:
        box(-1, 5, 17, 4, ink)
        box(2, 6, 10, 2, "#81abbc")
        box(26, -2, 3, 4, steel)
    if flip:
        im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return arcade.Texture(im)


def draw_weapon(pose, hands=True):
    tex = gun_texture(pose.kind, math.cos(pose.angle) < 0)
    center = pose.point((MUZZLES[pose.kind] - 18) / 2, -1)
    arcade.draw_texture_rect(
        tex,
        arcade.LBWH(
            center[0] - tex.width / 2, center[1] - tex.height / 2, tex.width, tex.height
        ),
        angle=-math.degrees(pose.angle),
        pixelated=True,
    )
    if hands:
        for x, y in (pose.grip, pose.support):
            arcade.draw_rect_filled(
                arcade.LBWH(round(x) - 3, round(y) - 2, 6, 5), (38, 31, 31)
            )
            arcade.draw_rect_filled(
                arcade.LBWH(round(x) - 2, round(y) - 1, 4, 3), (235, 181, 120)
            )
