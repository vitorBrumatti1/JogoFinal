"""Apresentação em slots de texto reutilizáveis e sinais visuais dos inimigos."""

import math
import arcade


class TextPool:
    def __init__(self):
        self.slots = {}

    def draw(self, key, value, x, y, size=12, color=(237, 242, 218), bold=False):
        label = self.slots.get(key)
        if label is None:
            label = arcade.Text(
                str(value), x, y, color, size, font_name="DejaVu Sans", bold=bold
            )
            self.slots[key] = label
        else:
            if label.text != str(value):
                label.text = str(value)
            label.x = x
            label.y = y
            label.color = color
        label.draw()


def enemy_role(enemy):
    x, y = enemy.position
    direction = enemy.direction
    if enemy.kind == "shooter":
        # Blue optics and a radio silhouette identify the ranged class.
        rear = x - direction * 17
        arcade.draw_rect_filled(arcade.LBWH(rear - 4, y - 8, 8, 19), (40, 62, 87))
        arcade.draw_line(rear, y + 8, rear, y + 30, (148, 179, 211), 2)
        arcade.draw_rect_filled(
            arcade.LBWH(x + direction * 4 - 3, y + 22, 8, 3), (98, 226, 238)
        )
    elif enemy.kind == "charger":
        arcade.draw_line(
            x - direction * 7, y + 17, x - direction * 23, y + 10, (224, 67, 62), 4
        )
        if enemy.phase % 2.4 < 0.35:
            arcade.draw_line(
                x + direction * 15,
                y - 15,
                x + direction * 34,
                y - 15,
                (248, 116, 80, 160),
                2,
            )
    elif enemy.kind == "drone":
        width = 17 if int(enemy.phase * 6) % 2 else 27
        arcade.draw_line(x - width, y + 25, x + width, y + 25, (130, 160, 169), 2)
        color = (255, 218, 110) if enemy.alert else (225, 89, 64)
        arcade.draw_rect_filled(arcade.LBWH(x - 4, y - 17, 8, 5), color)
        if enemy.alert:
            arcade.draw_circle_outline(
                x, y - 18, 10 + math.sin(enemy.phase * 10) * 2, (255, 209, 91), 1
            )
    elif enemy.kind == "boss" and enemy.alert:
        tx = getattr(enemy, "target_x", x - 220)
        arcade.draw_line(x, y + 12, tx, 110, (255, 139, 99, 90), 1)
        arcade.draw_circle_outline(tx, 110, 27, (255, 163, 94, 150), 2)
    if getattr(enemy, "hurt", 0) > 0:
        arcade.draw_rect_outline(
            arcade.LBWH(enemy.left, enemy.bottom, enemy.width, enemy.height),
            (255, 228, 199, 180),
            1,
        )
