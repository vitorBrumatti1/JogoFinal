"""Botões animados, mira e seleção por disparo reutilizados em todas as Views."""

from dataclasses import dataclass
import math
import random
import arcade


@dataclass
class Button:
    id: str
    label: str
    box: tuple
    action: object
    subtitle: str = ""
    hover: float = 0.0

    def contains(self, x, y):
        bx, by, w, h = self.box
        return bx <= x <= bx + w and by <= y <= by + h


class ScreenMotion:
    def __init__(self, view):
        self.view = view
        self.time = 0.0
        self.pointer = (-100, -100)
        self.buttons = []
        self.pending = None
        self.shot = None
        rng = random.Random(19)
        self.motes = [
            (rng.randrange(960), rng.randrange(640), rng.uniform(7, 24))
            for _ in range(28)
        ]

    def add(self, id, label, box, action, subtitle=""):
        button = Button(id, label, box, action, subtitle)
        self.buttons.append(button)
        return button

    def trigger(self, id):
        if self.pending:
            return False
        button = next((b for b in self.buttons if b.id == id), None)
        if not button:
            return False
        x, y, w, h = button.box
        target = (
            self.pointer
            if button.contains(*self.pointer)
            else (x + w * 0.65, y + h * 0.5)
        )
        self.pending = [0.22, button.action]
        self.shot = [target, 0.22]
        if self.view.window:
            self.view.window.audio.play("menu")
        return True

    def click(self, x, y):
        self.pointer = (x, y)
        for b in self.buttons:
            if b.contains(x, y):
                return self.trigger(b.id)
        return False

    def update(self, dt):
        dt = min(dt, 0.1)
        self.time += dt
        for b in self.buttons:
            target = 1.0 if b.contains(*self.pointer) else 0.0
            b.hover += (target - b.hover) * min(1, dt * 14)
        if self.shot:
            self.shot[1] -= dt
            if self.shot[1] <= 0:
                self.shot = None
        if self.pending:
            self.pending[0] -= dt
            if self.pending[0] <= 0:
                action = self.pending[1]
                self.pending = None
                action()

    def atmosphere(self):
        for x, y, speed in self.motes:
            px = (x + math.sin(self.time * 0.2 + y) * 13) % 960
            py = (y + self.time * speed) % 640
            arcade.draw_circle_filled(px, py, 1.5, (255, 219, 140, 40))

    def draw(self):
        if getattr(self, "arcade_menu", False):
            from arcade_style import draw_menu_buttons

            draw_menu_buttons(self)
        else:
            for b in self.buttons:
                x, y, w, h = b.box
                shift = b.hover * 8
                arcade.draw_rect_filled(
                    arcade.LBWH(x + shift, y, w, h),
                    (
                        (23, 27, 35, 235)
                        if getattr(b, "unavailable", False)
                        else (17 + int(b.hover * 17), 35 + int(b.hover * 13), 40, 235)
                    ),
                )
                arcade.draw_rect_filled(
                    arcade.LBWH(x + shift, y, 3 + b.hover * 3, h),
                    (255, 218, 101, int(130 + 125 * b.hover)),
                )
                arcade.draw_rect_outline(
                    arcade.LBWH(x + shift, y, w, h),
                    (255, 218, 101, int(35 + 180 * b.hover)),
                    1,
                )
                arcade.draw_text(
                    b.label,
                    x + 18 + shift,
                    y + h - 20 if getattr(b, "card", False) else y + h * 0.53,
                    (255, 226, 137) if b.hover > 0.25 else (237, 242, 218),
                    15,
                    bold=True,
                    anchor_y="center",
                )
                if getattr(b, "render_extra", None):
                    b.render_extra()
                if b.subtitle:
                    arcade.draw_text(
                        b.subtitle, x + 18 + shift, y + 8, (153, 185, 177), 10
                    )
                if b.hover > 0.05:
                    arcade.draw_line(
                        x + w - 36 + shift,
                        y + h / 2,
                        x + w - 18 + shift,
                        y + h / 2,
                        (255, 218, 101, int(255 * b.hover)),
                        2,
                    )
        if self.shot:
            (tx, ty), remaining = self.shot
            t = 1 - remaining / 0.22
            if not self.view.window.reduced_effects:
                arcade.draw_line(
                    920, 50, tx, ty, (255, 230, 150, int(230 * (1 - t))), 3
                )
                for i in range(8):
                    a = i * math.pi / 4
                    r = 10 + t * 34
                    arcade.draw_line(
                        tx + math.cos(a) * r * 0.5,
                        ty + math.sin(a) * r * 0.5,
                        tx + math.cos(a) * r,
                        ty + math.sin(a) * r,
                        (255, 195, 85, int(255 * (1 - t))),
                        2,
                    )
                arcade.draw_circle_filled(
                    tx, ty, 12 * (1 - t), (255, 238, 188, int(220 * (1 - t)))
                )
            arcade.draw_circle_filled(tx, ty, 4, (8, 16, 20))
            arcade.draw_circle_outline(tx, ty, 6, (255, 218, 101), 1)
        alpha = max(0, int(255 * (1 - self.time / 0.35)))
        if alpha:
            arcade.draw_rect_filled(arcade.LBWH(0, 0, 960, 640), (9, 21, 28, alpha))
        from arcade_style import cabinet_overlay

        cabinet_overlay(self.view.window)
