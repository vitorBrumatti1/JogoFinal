import math
import random
import arcade


class Particula:
    def __init__(self, x, y, cor):
        angulo = random.uniform(0, 2 * math.pi)
        velocidade = random.uniform(70, 190)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angulo) * velocidade, math.sin(angulo) * velocidade
        self.vida = random.uniform(0.3, 0.65)
        self.max_vida = self.vida
        self.raio = random.uniform(2.5, 5)
        self.cor = cor

    def update(self, dt):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= 220 * dt

    def draw(self):
        if self.vida > 0:
            alpha = int(255 * max(0, self.vida / self.max_vida))
            size = max(2, round(self.raio))
            arcade.draw_rect_filled(
                arcade.LBWH(round(self.x), round(self.y), size, size),
                (*self.cor, alpha),
            )
            if self.vida / self.max_vida > 0.4:
                arcade.draw_line(
                    self.x,
                    self.y,
                    self.x - self.vx * 0.022,
                    self.y - self.vy * 0.022,
                    (*self.cor, alpha // 2),
                    2,
                )


class TextoFlutuante:
    def __init__(self, mensagem, x, y, cor):
        self.mensagem, self.x, self.y, self.cor = mensagem, x, y, cor
        self.vida, self.max_vida = 0.85, 0.85

    def update(self, dt):
        self.y += 55 * dt
        self.vida -= dt

    def draw(self):
        if self.vida > 0:
            alpha = int(255 * self.vida / self.max_vida)
            arcade.draw_text(
                self.mensagem,
                self.x,
                self.y,
                (*self.cor, alpha),
                17,
                bold=True,
                anchor_x="center",
            )


class Casing:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.vx = -direction * random.uniform(35, 65)
        self.vy = random.uniform(65, 105)
        self.life = 0.4

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= 330 * dt

    def draw(self):
        arcade.draw_rect_filled(
            arcade.LBWH(round(self.x), round(self.y), 3, 2),
            (221, 177, 77, int(255 * max(0, self.life) / 0.4)),
        )


class SpriteEcho:
    def __init__(self, sprite, death=False):
        self.texture = sprite.texture
        self.x, self.y = sprite.position
        self.w = sprite.width
        self.h = sprite.height
        self.death = death
        self.age = 0.0
        self.life = 0.28 if death else 0.15
        self.duration = self.life
        self.direction = getattr(sprite, "direction", 1)

    def update(self, dt):
        self.life -= dt
        self.age += dt
        if self.death:
            self.x += self.direction * 24 * dt
            self.y -= 60 * self.age * dt

    def draw(self):
        alpha = int((210 if self.death else 70) * max(0, self.life) / self.duration)
        arcade.draw_texture_rect(
            self.texture,
            arcade.LBWH(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h),
            angle=self.age * 95 * self.direction if self.death else 0,
            alpha=alpha,
            pixelated=True,
        )
