"""Granadas balísticas e efeitos legíveis sem alterar as colisões dos tiros."""

import math
import arcade
from weapon_art import TRAILS, COLORS


class Grenade(arcade.SpriteSolidColor):
    def __init__(self, x, y, vx=0):
        super().__init__(14, 16, color=(139, 211, 86))
        self.position = x, y
        self.change_x = vx
        self.change_y = -0.8
        self.fuse = 3.0
        self.grounded = False
        self.exploded = False
        self.age = 0.0

    def tick(self, dt, walls):
        if self.exploded:
            return False
        self.age += dt
        if not self.grounded:
            previous = self.bottom
            self.change_y = max(-8, self.change_y - 0.12)
            self.center_x += self.change_x
            self.center_y += self.change_y
            supports = [
                b
                for b in arcade.check_for_collision_with_list(self, walls)
                if previous >= b.top - 9
            ]
            if supports:
                self.bottom = max(b.top for b in supports)
                self.change_x = 0
                self.change_y = 0
                self.grounded = True
                self.fuse = min(self.fuse, 0.95)
        self.fuse -= dt
        if self.fuse <= 0:
            self.exploded = True
            return True
        return False

    def draw_fx(self):
        x, y = self.position
        for radius, alpha in ((14, 45), (10, 80)):
            arcade.draw_circle_filled(x, y, radius, (255, 174, 46, alpha))
        arcade.draw_rect_filled(arcade.LBWH(x - 9, y - 9, 18, 18), (11, 19, 30))
        arcade.draw_rect_filled(arcade.LBWH(x - 6, y - 7, 12, 14), (114, 181, 73))
        arcade.draw_rect_filled(arcade.LBWH(x - 4, y + 6, 8, 4), (194, 205, 189))
        arcade.draw_line(x - 3, y - 6, x - 3, y + 4, (201, 236, 141), 2)
        blink = int(self.age * (15 if self.grounded else 7)) % 2
        arcade.draw_rect_filled(
            arcade.LBWH(x - 2, y, 4, 4), (255, 73, 68) if blink else (255, 234, 125)
        )
        if self.grounded:
            radius = 72 + math.sin(self.age * 18) * 3
            arcade.draw_circle_outline(x, y, radius, (255, 126, 58, 200), 2)
            arcade.draw_text(
                "!", x, y + 25, (255, 212, 96), 17, bold=True, anchor_x="center"
            )


class Impact:
    def __init__(self, x, y, explosion=False):
        self.x = x
        self.y = y
        self.explosion = explosion
        self.age = 0.0
        self.life = 0.5 if explosion else 0.2

    def update(self, dt):
        self.age += dt
        self.life -= dt

    def draw(self):
        t = self.age / (0.5 if self.explosion else 0.2)
        alpha = max(0, int(220 * (1 - t)))
        if self.explosion:
            radius = 15 + t * 95
            arcade.draw_circle_outline(
                self.x, self.y, radius, (255, 183, 77, alpha), max(1, 5 * (1 - t))
            )
            arcade.draw_circle_outline(
                self.x, self.y, radius * 0.7, (255, 242, 176, alpha // 2), 2
            )
            for i in range(7):
                a = i * math.tau / 7
                x = self.x + math.cos(a) * t * 45
                y = self.y + math.sin(a) * t * 35 + t * 28
                size = 10 + t * 15
                arcade.draw_rect_filled(
                    arcade.LBWH(x - size / 2, y - size / 2, size, size),
                    (49, 34, 49, int(100 * (1 - t))),
                )
        else:
            for i in range(6):
                a = i * math.tau / 6
                length = 6 + t * 21
                arcade.draw_line(
                    self.x + math.cos(a) * 4,
                    self.y + math.sin(a) * 4,
                    self.x + math.cos(a) * length,
                    self.y + math.sin(a) * length,
                    (255, 226, 132, alpha),
                    2,
                )


def draw_projectile(bullet):
    x, y = bullet.position
    if bullet.knife:
        a = math.radians(bullet.angle)
        c, s = math.cos(a), math.sin(a)
        arcade.draw_line(x - c * 13, y - s * 13, x + c * 13, y + s * 13, (9, 17, 27), 7)
        arcade.draw_line(
            x - c * 11, y - s * 11, x - c * 3, y - s * 3, (159, 105, 55), 4
        )
        arcade.draw_triangle_filled(
            x - c * 3 - s * 3,
            y - s * 3 + c * 3,
            x + c * 15,
            y + s * 15,
            x - c * 3 + s * 3,
            y - s * 3 - c * 3,
            (230, 251, 255),
        )
        return
    vx, vy = bullet.change_x, bullet.change_y
    speed = max(0.01, math.hypot(vx, vy))
    ux, uy = vx / speed, vy / speed
    kind = "hostile" if bullet.hostile else getattr(bullet, "kind", "ak")
    trail = TRAILS[kind]
    color = COLORS[kind]
    # Compact silhouette; visual width is independent of the collision radius.
    arcade.draw_line(
        x - ux * trail, y - uy * trail, x + ux * 2, y + uy * 2, (14, 18, 28), 4
    )
    arcade.draw_line(
        x - ux * (trail - 2), y - uy * (trail - 2), x + ux * 1, y + uy * 1, color, 2
    )
    arcade.draw_line(x - ux * 3, y - uy * 3, x + ux * 1, y + uy * 1, (255, 251, 228), 1)


def muzzle_flash(x, y, angle, kind="ak"):
    size = {"ak": 0.52, "smg": 0.36, "shotgun": 0.8, "rifle": 0.6}[kind]
    c, s = math.cos(angle), math.sin(angle)
    points = [
        (-4, 0),
        (4, 5),
        (9, 3),
        (18, 8),
        (14, 1),
        (26, 0),
        (14, -2),
        (18, -8),
        (8, -3),
        (3, -5),
    ]
    arcade.draw_polygon_filled(
        [(x + (a * c - b * s) * size, y + (a * s + b * c) * size) for a, b in points],
        (255, 156, 37),
    )
    points = [(-2, 0), (6, 4), (13, 0), (7, -4)]
    arcade.draw_polygon_filled(
        [(x + (a * c - b * s) * size, y + (a * s + b * c) * size) for a, b in points],
        (255, 250, 181),
    )


class Cover(arcade.SpriteSolidColor):
    """Explicit ballistic cover; also a small jumpable physical obstacle."""

    def __init__(self, x, floor=96):
        super().__init__(36, 48, color=(67, 86, 96))
        self.left = x
        self.bottom = floor
        self.ballistic = True
        self.is_cover = True

    def draw_fx(self, theme="jungle"):
        x, y = self.left, self.bottom
        base = (
            (96, 112, 91)
            if theme == "jungle"
            else (107, 101, 85) if theme == "desert" else (77, 101, 124)
        )
        arcade.draw_rect_filled(arcade.LBWH(x, y, self.width, self.height), base)
        arcade.draw_rect_outline(
            arcade.LBWH(x + 2, y + 2, self.width - 4, self.height - 4), (23, 39, 49), 3
        )
        for dx in (6, self.width - 8):
            for dy in (7, self.height - 9):
                arcade.draw_rect_filled(
                    arcade.LBWH(x + dx, y + dy, 3, 3), (190, 197, 168)
                )
        arcade.draw_line(
            x + 8, y + 12, x + self.width - 8, y + self.height - 12, (190, 165, 87), 3
        )


def segment_box(start, end, bounds, radius=2.0):
    """Slab intersection, returning first time along segment (0..1)."""
    left, bottom, right, top = bounds
    lo, hi = 0.0, 1.0
    for origin, delta, minimum, maximum in (
        (start[0], end[0] - start[0], left - radius, right + radius),
        (start[1], end[1] - start[1], bottom - radius, top + radius),
    ):
        if abs(delta) < 1e-10:
            if origin < minimum or origin > maximum:
                return None
            continue
        a, b = (minimum - origin) / delta, (maximum - origin) / delta
        if a > b:
            a, b = b, a
        lo = max(lo, a)
        hi = min(hi, b)
        if lo > hi:
            return None
    return lo


def swept_contacts(start, end, groups, radius=2.0):
    contacts = []
    for category, sprites in groups:
        for sprite in sprites:
            hb = sprite.hit_box
            t = segment_box(start, end, (hb.left, hb.bottom, hb.right, hb.top), radius)
            if t is not None:
                point = (
                    start[0] + (end[0] - start[0]) * t,
                    start[1] + (end[1] - start[1]) * t,
                )
                contacts.append(
                    (t, 0 if category == "cover" else 1, category, sprite, point)
                )
    contacts.sort(key=lambda item: (item[0], item[1]))
    return contacts
