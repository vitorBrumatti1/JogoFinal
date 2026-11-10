"""Campanha arcade: física fixa, câmera de mundo e HUD independente."""

import math
import random
from pathlib import Path
import arcade
from actors import Jogador, Pontuacao, inicializar_banco
from campaign import Campaign, Weapon, STAGES, WEAPONS
from ui_fx import ScreenMotion
from world_fx import Hazard, Barrel, draw_gun
from effects import Particula, TextoFlutuante
from sound import Audio
from combat import Grenade, Impact, draw_projectile, muzzle_flash
from arcade_style import cabinet_overlay, pixel_text, ArcadeMenuScene

WIDTH, HEIGHT = 960, 640
BASE = Path(__file__).resolve().parent
GOLD = (255, 218, 101)
INK = (18, 33, 38)
WHITE = (237, 242, 218)
RED = (240, 92, 65)


def asset(name):
    return str(BASE / "assets" / name)


def rect(x, y, w, h, color):
    arcade.draw_rect_filled(arcade.LBWH(x, y, w, h), color)


def text(message, x, y, size=16, color=WHITE, **kwargs):
    arcade.draw_text(message, x, y, color, size, font_name="DejaVu Sans", **kwargs)


def center(message, y, size=20, color=WHITE):
    text(message, WIDTH / 2, y, size, color, anchor_x="center", bold=True)


class Bloco(arcade.Sprite):
    def __init__(self, x, y, bridge=False, wall=False):
        super().__init__(
            asset("bridge.png" if bridge else ("wall.png" if wall else "stone.png"))
        )
        self.width = 48
        self.height = 24 if bridge else 48
        self.left = x
        self.top = y


class Enemy(arcade.Sprite):
    def __init__(self, x, y, kind, level, left=0, right=0):
        super().__init__(
            asset(
                {
                    "guard": "guard.png",
                    "charger": "guard.png",
                    "shooter": "guard.png",
                    "drone": "drone.png",
                    "boss": "boss.png",
                }[kind]
            ),
            scale=0.55 if kind in ("guard", "shooter", "charger") else 1.0,
        )
        self.kind = kind
        self.position = x, y
        self.hp = 130 if kind == "boss" else 2 + level
        if kind == "charger":
            self.hp += 2
        self.max_hp = self.hp
        self.speed = 1.7 + level * 0.3
        self.direction = -1
        self.low = left or x - 100
        self.high = right or x + 100
        self.shot_clock = 1.6 + random.random() * 1.2
        self.aim_time = 0.0
        self.level = level
        self.alert = 0.0
        self.phase = random.random() * 6.28
        self.base_y = y
        self.original = self.texture
        self.flipped = self.texture.flip_left_right()
        if kind == "shooter":
            self.color = (255, 190, 160)

    def tick(self, dt, player):
        self.shot_clock = max(0.0, self.shot_clock - dt)
        self.phase += dt * 3
        self.alert = 0.0
        if self.kind == "drone":
            self.center_x += max(
                -self.speed, min(self.speed, (player.center_x - self.center_x) * 0.01)
            )
            self.center_y = self.base_y + math.sin(self.phase) * 22
        elif self.kind != "boss":
            if self.kind == "charger" and abs(player.center_x - self.center_x) < 320:
                self.direction = 1 if player.center_x > self.center_x else -1
            self.center_x += (
                self.direction * self.speed * (1.8 if self.kind == "charger" else 1)
            )
            if self.left < self.low:
                self.left = self.low
                self.direction = 1
            if self.right > self.high:
                self.right = self.high
                self.direction = -1
            self.texture = self.original if self.direction == 1 else self.flipped
        else:
            facing = 1 if player.center_x > self.center_x else -1
            if facing != self.direction:
                self.direction = facing
                self.aim_time = 0.0
                self.shot_clock = max(self.shot_clock, 0.8)
            self.texture = self.original if self.direction == -1 else self.flipped
            self.center_x += math.sin(self.phase * 0.3) * 0.45

    def can_aim(self, player, walls):
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        if self.direction * dx <= 0 or abs(dx) > 620 or abs(dy) > abs(dx) * 0.85 + 35:
            return False
        return arcade.has_line_of_sight(
            self.position, player.position, walls, max_distance=650, check_resolution=12
        )


class Bullet(arcade.SpriteSolidColor):
    def __init__(self, x, y, vx, vy=0, hostile=False, damage=1, pierce=1, knife=False):
        super().__init__(
            24 if knife else (14 if not hostile else 10),
            4 if knife else 5,
            color=(216, 233, 235) if knife else (GOLD if not hostile else RED),
        )
        self.position = x, y
        self.change_x = vx
        self.change_y = vy
        self.life = 1.8
        self.hostile = hostile
        self.damage = damage
        self.pierce = pierce
        self.knife = knife
        self.hit_ids = set()
        self.angle = math.degrees(math.atan2(vy, vx))

    def tick(self, dt):
        self.center_x += self.change_x
        self.center_y += self.change_y
        self.life -= dt
        if self.knife:
            self.angle -= dt * 950


class TelaJogo(arcade.View):
    def __init__(self, campaign=None):
        super().__init__()
        self.run = campaign or Campaign()
        self.held = set()
        self.firing = False
        self.mouse_firing = False
        self.paused = False
        self.accumulator = 0.0
        self.transition = 0.0
        self.ended = False
        self.particles = []
        self.impacts = []
        self.labels = []
        self.shake = 0.0
        self.flash = 0.0
        self.muzzle = 0.0
        self.hitstop = 0.0
        self.world_camera = arcade.Camera2D()
        self.ui_camera = arcade.Camera2D()
        self.camera_x = WIDTH / 2
        self.mouse = (WIDTH / 2, HEIGHT / 2)
        self.mouse_aim = False
        self.aim_angle = 0.0
        self.camera_shake = (0.0, 0.0)
        self.pause_ui = ScreenMotion(self)
        self.pause_ui.add(
            "resume", "ESC / P / CONTINUAR", (290, 280, 380, 48), self.resume_pause
        )
        self.pause_ui.add(
            "menu",
            "M / MENU PRINCIPAL",
            (290, 218, 380, 48),
            lambda: self.window.show_view(TelaMenu()),
        )
        self.combo = 0
        self.combo_time = 0.0
        self.dash_direction = 1
        self.entrance = 0.4
        self.load_stage()

    @property
    def weapon(self):
        return self.run.weapon

    @property
    def audio(self):
        return self.window.audio

    def camera_center(self):
        return max(
            WIDTH / 2, min(self.stage.length - WIDTH / 2, self.player.center_x + 130)
        )

    def aim(self):
        if not self.mouse_aim:
            self.aim_angle = 0 if self.player.virado_para == 1 else math.pi
        else:
            world_x = (
                self.mouse[0] + self.camera_center() + self.camera_shake[0] - WIDTH / 2
            )
            self.aim_angle = math.atan2(
                self.mouse[1] + self.camera_shake[1] - self.player.center_y - 3,
                world_x - self.player.center_x,
            )
        return math.cos(self.aim_angle), math.sin(self.aim_angle)

    def on_show_view(self):
        self.clear_input()
        self.accumulator = 0.0
        self.entrance = 0.35
        self.window.set_mouse_visible(False)

    def clear_input(self):
        self.held.clear()
        self.firing = False
        self.mouse_firing = False

    def load_stage(self):
        self.stage = STAGES[self.run.stage]
        self.background = arcade.load_texture(asset(self.stage.background))
        self.blocks = arcade.SpriteList(use_spatial_hash=True)
        self.decor = arcade.SpriteList()
        self.coins = arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.bullets = arcade.SpriteList()
        self.hostile = arcade.SpriteList()
        self.grenades = arcade.SpriteList()
        self.players = arcade.SpriteList()
        self.barrels = arcade.SpriteList()
        self.hazards = arcade.SpriteList()
        self.player = Jogador()
        self.player.position = (90, 150)
        self.players.append(self.player)
        for x in range(0, self.stage.length + 48, 48):
            self.blocks.append(Bloco(x, 96))
            self.decor.append(Bloco(x, 48, wall=True))
        for idx, (x, y, w) in enumerate(self.stage.platforms):
            for bx in range(int(x - w / 2), int(x + w / 2), 48):
                self.blocks.append(Bloco(bx, y, bridge=idx % 3 == 1))
                if idx % 3 != 1:
                    self.decor.append(Bloco(bx, y - 48, wall=True))
            for offset in (-50, 0, 50):
                self.add_coin(
                    x + offset,
                    y + 32,
                    special=idx == len(self.stage.platforms) - 1 and offset == 0,
                )
            if idx % 3 == 0:
                self.barrels.append(Barrel(x + 68, y + 17))
        for x in range(180, self.stage.length - 180, 260):
            if not any(
                y < 200 and px - pw / 2 - 30 < x < px + pw / 2 + 30
                for px, y, pw in self.stage.platforms
            ):
                self.add_coin(x, 128)
        terrain = {
            "jungle": (255, 255, 255),
            "desert": (240, 184, 131),
            "foundry": (130, 156, 182),
            "snow": (176, 219, 247),
        }[self.stage.theme]
        for b in self.blocks:
            b.color = terrain
        for b in self.decor:
            b.color = terrain
        self.total_coins = len(self.coins)
        self.collected = 0
        self.coin_goal = math.ceil(self.total_coins * 0.7)
        for x, kind in self.stage.hazards:
            self.hazards.append(Hazard(x, kind))
        for i in range(self.stage.enemies):
            kind = "shooter" if i % 3 == 1 else "guard"
            if self.run.stage >= 1 and i % 4 == 2:
                kind = "drone"
            elif self.run.stage >= 1 and i % 5 == 4:
                kind = "charger"
            x = 470 + i * (self.stage.length - 700) / self.stage.enemies
            if kind == "drone":
                y = 240 + (i % 3) * 70
                left, right = x - 100, x + 100
            elif i % 2 == 0:
                px, py, pw = self.stage.platforms[(i // 2) % len(self.stage.platforms)]
                x = px
                y = py + 34
                left, right = px - pw / 2, px + pw / 2
            else:
                y = 130
                left, right = max(300, x - 90), min(self.stage.length - 180, x + 90)
            self.enemies.append(Enemy(x, y, kind, self.run.stage, left, right))
        self.boss = None
        if self.run.stage == 3:
            self.boss = Enemy(self.stage.length - 350, 168, "boss", 3)
            self.enemies.append(self.boss)
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player, walls=self.blocks, gravity_constant=0.5
        )
        self.banner = 2.3
        self.camera_x = WIDTH / 2
        self.particles.clear()
        self.impacts.clear()
        self.labels.clear()
        self.ambushes = set()
        self.combo = 0
        self.combo_time = 0.0

    def add_coin(self, x, y, special=False):
        coin = arcade.Sprite(asset("coin.png"), scale=1.2 if special else 0.85)
        coin.position = x, y
        coin.special = special
        coin.base_y = y
        coin.phase = x * 0.02
        self.coins.append(coin)

    def burst(self, x, y, color, count=12):
        count = min(count, max(0, 250 - len(self.particles)))
        self.particles.extend(Particula(x, y, color) for _ in range(count))

    def label(self, message, x, y, color=GOLD):
        if len(self.labels) < 35:
            self.labels.append(TextoFlutuante(message, x, y, color))

    def fire(self):
        if self.weapon.ammo == 0 and not self.weapon.reloading:
            if self.weapon.reload():
                self.audio.play("reload")
        if not self.weapon.fire():
            return
        ux, uy = self.aim()
        spec = self.weapon.spec
        x = self.player.center_x + ux * 22
        y = self.player.center_y + 3 + uy * 22
        for i in range(spec.pellets):
            spread = (
                (i - (spec.pellets - 1) / 2) * spec.spread
                if spec.pellets > 1
                else random.uniform(-spec.spread, spec.spread)
            )
            a = self.aim_angle + spread
            self.bullets.append(
                Bullet(
                    x,
                    y,
                    math.cos(a) * spec.speed,
                    math.sin(a) * spec.speed,
                    damage=spec.damage + self.run.damage_level,
                    pierce=spec.pierce,
                )
            )
        self.muzzle = 0.055
        self.audio.play("shot")
        self.burst(x - ux * 12, y - uy * 12, (210, 164, 67), 2)

    def throw_knife(self):
        if not self.run.throw_knife():
            self.label(
                "COMPRE FACAS NA LOJA" if not self.run.knives else "AGUARDE",
                self.player.center_x,
                self.player.top + 12,
            )
            return
        ux, uy = self.aim()
        self.bullets.append(
            Bullet(
                self.player.center_x + ux * 18,
                self.player.center_y + uy * 18,
                ux * 13,
                uy * 13,
                damage=6,
                pierce=3,
                knife=True,
            )
        )
        self.audio.play("jump")

    def impact(self, x, y, explosion=False):
        if len(self.impacts) < 35:
            self.impacts.append(Impact(x, y, explosion))

    def damage(self):
        if not self.run.damage():
            return
        self.audio.play("hit")
        self.player.receber_dano()
        self.shake = 0.23
        self.flash = 0.28
        self.combo = 0
        self.burst(*self.player.position, RED, 16)
        self.label("-1 VIDA", self.player.center_x, self.player.top + 18, RED)

    def defeat(self, enemy):
        if enemy not in self.enemies:
            return
        self.combo = self.combo + 1 if self.combo_time else 1
        self.combo_time = 3.0
        multiplier = min(4, 1 + self.combo // 3)
        gain = (50 if enemy.kind == "boss" else 3) * multiplier
        self.run.score += gain
        self.run.wallet += 25 if enemy.kind == "boss" else 4 + self.run.stage
        self.audio.play("boom")
        self.burst(*enemy.position, (255, 151, 57), 24)
        self.label(f"+{gain} / {multiplier}x", enemy.center_x, enemy.top)
        self.shake = 0.17
        self.hitstop = 0.025
        enemy.remove_from_sprite_lists()

    def explode(self, x, y, radius=110):
        self.audio.play("boom")
        self.impact(x, y, True)
        self.burst(x, y, (255, 148, 46), 38)
        self.shake = 0.3
        for enemy in list(self.enemies):
            if math.hypot(enemy.center_x - x, enemy.center_y - y) < radius:
                enemy.hp -= 9
                if enemy.hp <= 0:
                    self.defeat(enemy)
        if (
            math.hypot(self.player.center_x - x, self.player.center_y - y)
            < radius * 0.7
        ):
            self.damage()
        for barrel in list(self.barrels):
            if math.hypot(barrel.center_x - x, barrel.center_y - y) < radius:
                barrel.remove_from_sprite_lists()
                self.burst(*barrel.position, (255, 120, 40), 12)

    def open_shop(self):
        if self.transition or self.ended:
            return
        self.clear_input()
        self.accumulator = 0.0
        self.window.show_view(TelaLoja(self))

    def on_update(self, delta_time):
        if self.ended or self.window.current_view is not self:
            return
        if self.paused:
            self.pause_ui.update(delta_time)
            return
        self.accumulator += min(delta_time, 0.25)
        while self.accumulator >= 1 / 60:
            self.accumulator -= 1 / 60
            self.step(1 / 60)
            if self.ended or self.window.current_view is not self:
                return

    def step(self, dt):
        self.banner = max(0, self.banner - dt)
        self.entrance = max(0, self.entrance - dt)
        self.flash = max(0, self.flash - dt)
        self.shake = max(0, self.shake - dt)
        self.muzzle = max(0, self.muzzle - dt)
        self.combo_time = max(0, self.combo_time - dt)
        if not self.combo_time:
            self.combo = 0
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.vida > 0]
        for effect in self.impacts:
            effect.update(dt)
        self.impacts = [effect for effect in self.impacts if effect.life > 0]
        for p in self.labels:
            p.update(dt)
        self.labels = [p for p in self.labels if p.vida > 0]
        if self.transition:
            self.transition = max(0, self.transition - dt)
            if self.transition == 0:
                if self.run.advance():
                    self.load_stage()
                    self.window.show_view(TelaLoja(self, between=True))
                else:
                    self.finish(True)
            return
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        self.run.update(dt)
        for gun in self.run.weapons.values():
            gun.update(dt)
        left = bool(self.held & {arcade.key.A, arcade.key.LEFT})
        right = bool(self.held & {arcade.key.D, arcade.key.RIGHT})
        self.player.change_x = (
            self.dash_direction * 11
            if self.run.dash_time
            else (int(right) - int(left)) * 4.6
        )
        self.physics_engine.update()
        self.player.update(dt)
        self.aim()
        if self.mouse_aim:
            self.player.virado_para = 1 if math.cos(self.aim_angle) >= 0 else -1
            # Visual facing follows aim, while animation priority remains in Jogador.update.
            change_x = self.player.change_x
            self.player.change_x = self.player.virado_para * 0.001 if change_x else 0
            self.player.update(0)
            self.player.change_x = change_x
        self.player.left = max(0, self.player.left)
        self.player.right = min(self.stage.length, self.player.right)
        if self.player.top < 0:
            self.damage()
            self.player.position = (max(90, self.player.center_x - 70), 150)
        if self.firing:
            self.fire()
        for coin in self.coins:
            coin.phase += dt * 3
            coin.center_y = coin.base_y + math.sin(coin.phase) * 4
        for coin in arcade.check_for_collision_with_list(self.player, self.coins):
            value = 5 if coin.special else 1
            self.run.score += value
            self.run.wallet += value * 2
            self.collected += 1
            self.audio.play("coin")
            self.burst(*coin.position, GOLD, 10)
            self.label(f"+{value*2} $", coin.center_x, coin.top + 10)
            coin.remove_from_sprite_lists()
        # Each ambush is finite and drones arrive above the route, never on top of the player.
        for marker in (int(self.stage.length * 0.4), int(self.stage.length * 0.72)):
            if self.player.center_x > marker and marker not in self.ambushes:
                self.ambushes.add(marker)
                for n in range(2 + self.run.stage // 2):
                    x = min(
                        self.stage.length - 150, self.player.center_x + 380 + n * 90
                    )
                    self.enemies.append(Enemy(x, 410 + n * 18, "drone", self.run.stage))
                self.label(
                    "EMBOSCADA!", self.player.center_x, self.player.top + 35, RED
                )
        self.update_enemy_attacks(dt)
        for bullet in list(self.bullets):
            bullet.tick(dt)
            if bullet.life <= 0 or arcade.check_for_collision_with_list(
                bullet, self.blocks
            ):
                self.impact(*bullet.position)
                self.burst(*bullet.position, (210, 205, 161), 3)
                bullet.remove_from_sprite_lists()
                continue
            grenade_hits = arcade.check_for_collision_with_list(bullet, self.grenades)
            if grenade_hits:
                grenade = grenade_hits[0]
                grenade.remove_from_sprite_lists()
                bullet.remove_from_sprite_lists()
                self.explode(*grenade.position, radius=90)
                continue
            barrels = arcade.check_for_collision_with_list(bullet, self.barrels)
            if barrels:
                barrel = barrels[0]
                barrel.remove_from_sprite_lists()
                bullet.remove_from_sprite_lists()
                self.explode(*barrel.position)
                continue
            for enemy in arcade.check_for_collision_with_list(bullet, self.enemies):
                if id(enemy) in bullet.hit_ids:
                    continue
                bullet.hit_ids.add(id(enemy))
                enemy.hp -= bullet.damage
                bullet.pierce -= 1
                self.impact(*bullet.position)
                self.burst(*bullet.position, GOLD, 5)
                if enemy.hp <= 0:
                    self.defeat(enemy)
                if bullet.pierce <= 0:
                    bullet.remove_from_sprite_lists()
                    break
        for bullet in list(self.hostile):
            bullet.tick(dt)
            if arcade.check_for_collision(bullet, self.player):
                self.damage()
                bullet.remove_from_sprite_lists()
            elif bullet.life <= 0 or arcade.check_for_collision_with_list(
                bullet, self.blocks
            ):
                bullet.remove_from_sprite_lists()
        for grenade in list(self.grenades):
            if grenade.tick(dt, self.blocks):
                grenade.remove_from_sprite_lists()
                self.explode(*grenade.position, radius=90)
        for hazard in self.hazards:
            if hazard.tick(dt, self.run.time, self.player):
                self.explode(hazard.center_x, 115, 90)
            if hazard.active and arcade.check_for_collision(hazard, self.player):
                self.damage()
        if arcade.check_for_collision_with_list(self.player, self.enemies):
            self.damage()
        if self.run.health <= 0:
            self.finish(False)
            return
        if self.player.center_x > self.stage.length - 115:
            if len(self.coins) > self.total_coins - self.coin_goal:
                if int(self.run.time * 60) % 120 == 0:
                    self.label(
                        "COLETE 70% DAS MOEDAS",
                        self.player.center_x,
                        self.player.top + 20,
                    )
            elif self.boss and self.boss.hp > 0:
                if int(self.run.time * 60) % 120 == 0:
                    self.label(
                        "DERROTE O GUARDIÃO",
                        self.player.center_x,
                        self.player.top + 20,
                        RED,
                    )
            else:
                self.audio.play("clear")
                self.transition = 1.4
                self.clear_input()

    def update_enemy_attacks(self, dt):
        for enemy in list(self.enemies):
            if abs(enemy.center_x - self.player.center_x) > 760:
                continue
            enemy.tick(dt, self.player)
            if enemy.kind == "drone":
                eligible = (
                    abs(enemy.center_x - self.player.center_x) < 330
                    and enemy.bottom > self.player.top + 35
                )
                enemy.alert = eligible and enemy.shot_clock < 0.65
                if eligible and enemy.shot_clock <= 0 and len(self.grenades) < 8:
                    drift = max(
                        -1.2, min(1.2, (self.player.center_x - enemy.center_x) * 0.006)
                    )
                    self.grenades.append(
                        Grenade(enemy.center_x, enemy.bottom - 12, drift)
                    )
                    enemy.shot_clock = max(3.5, 4.8 - self.run.stage * 0.35)
                continue
            eligible = enemy.kind != "charger" and enemy.can_aim(
                self.player, self.blocks
            )
            enemy.aim_time = min(0.65, enemy.aim_time + dt) if eligible else 0.0
            enemy.alert = eligible and enemy.shot_clock < 0.65
            if not eligible or enemy.shot_clock > 0 or enemy.aim_time < 0.6:
                continue
            a = math.atan2(
                self.player.center_y - enemy.center_y,
                self.player.center_x - enemy.center_x,
            )
            enraged = enemy.kind == "boss" and enemy.hp < enemy.max_hp * 0.5
            speed = 3.0 + self.run.stage * 0.25
            for spread in ((-0.14, 0, 0.14) if enemy.kind == "boss" else (0,)):
                self.hostile.append(
                    Bullet(
                        enemy.center_x + enemy.direction * 24,
                        enemy.center_y,
                        math.cos(a + spread) * speed,
                        math.sin(a + spread) * speed,
                        True,
                    )
                )
            enemy.shot_clock = (
                (1.35 if enraged else 1.9)
                if enemy.kind == "boss"
                else max(2.1, 3.0 - self.run.stage * 0.3)
            )
            enemy.aim_time = 0.0

    def finish(self, victory):
        if self.ended:
            return
        self.ended = True
        self.clear_input()
        self.window.show_view(TelaGameOver(self.run.score, self.run.time, victory))

    def on_draw(self):
        self.clear(INK)
        self.ui_camera.use()
        self.camera_x = self.camera_center()
        offset = (self.camera_x - WIDTH / 2) * 0.12
        for i in (-1, 0, 1):
            arcade.draw_texture_rect(
                self.background,
                arcade.LBWH(i * WIDTH - offset, 0, WIDTH, HEIGHT),
                pixelated=True,
            )
        shake = 0 if self.window.reduced_effects else self.shake * 24
        self.camera_shake = (
            random.uniform(-shake, shake),
            random.uniform(-shake, shake),
        )
        self.world_camera.position = (
            self.camera_x + self.camera_shake[0],
            HEIGHT / 2 + self.camera_shake[1],
        )
        self.world_camera.use()
        self.decor.draw(pixelated=True)
        self.blocks.draw(pixelated=True)
        self.draw_terrain_caps()
        for i, (x, y, w) in enumerate(self.stage.platforms):
            if i % 3 == 1:
                for px in (x - w / 2, x + w / 2):
                    rect(px, y, 5, 36, (109, 86, 54))
                arcade.draw_line(x - w / 2, y + 30, x, y + 16, (206, 186, 128), 2)
                arcade.draw_line(x, y + 16, x + w / 2, y + 30, (206, 186, 128), 2)
        for hazard in self.hazards:
            hazard.draw_fx(self.run.time)
        self.barrels.draw()
        for barrel in self.barrels:
            barrel.draw_fx()
        self.draw_supply()
        self.draw_exit()
        self.coins.draw(pixelated=True)
        self.enemies.draw(pixelated=True)
        if self.run.dash_time:
            for offset in (15, 30, 45):
                arcade.draw_circle_filled(
                    self.player.center_x - offset * self.dash_direction,
                    self.player.center_y,
                    14,
                    (104, 222, 238, 45),
                )
        self.players.draw(pixelated=True)
        self.aim()
        draw_gun(
            self.player.center_x,
            self.player.center_y + 3,
            self.aim_angle,
            self.weapon.kind,
            3 if self.muzzle else 0,
        )
        for bullet in self.bullets:
            draw_projectile(bullet)
        for bullet in self.hostile:
            draw_projectile(bullet)
        for grenade in self.grenades:
            grenade.draw_fx()
        if self.muzzle:
            x = self.player.center_x + math.cos(self.aim_angle) * 35
            y = self.player.center_y + 3 + math.sin(self.aim_angle) * 35
            muzzle_flash(x, y, self.aim_angle)
        for effect in self.impacts:
            effect.draw()
        for p in self.particles:
            p.draw()
        for p in self.labels:
            p.draw()
        for enemy in self.enemies:
            if enemy.alert and enemy.kind != "charger":
                text("!", enemy.center_x, enemy.top + 5, 14, RED, bold=True)
            if enemy.kind == "boss":
                rect(enemy.left, enemy.top + 12, enemy.width, 6, INK)
                rect(
                    enemy.left,
                    enemy.top + 12,
                    enemy.width * max(0, enemy.hp) / enemy.max_hp,
                    6,
                    RED,
                )
                text(
                    "FÚRIA" if enemy.hp < enemy.max_hp * 0.5 else "GUARDIÃO",
                    enemy.left,
                    enemy.top + 24,
                    11,
                    RED,
                )
        self.ui_camera.use()
        self.weather()
        self.draw_hud()
        if self.mouse_aim and not self.paused:
            x, y = self.mouse
            arcade.draw_circle_outline(x, y, 9, GOLD, 1)
            for dx, dy in ((-15, 0), (15, 0), (0, -15), (0, 15)):
                arcade.draw_line(x + dx * 0.6, y + dy * 0.6, x + dx, y + dy, GOLD, 2)
        if self.flash and not self.window.reduced_effects:
            rect(0, 0, WIDTH, HEIGHT, (235, 67, 40, int(self.flash * 230)))
        if self.banner:
            rect(180, HEIGHT / 2 - 15, 600, 96, (18, 33, 38, 225))
            center(self.stage.name, HEIGHT / 2 + 39, 24, GOLD)
            center(self.stage.subtitle, HEIGHT / 2 + 5, 12)
        if self.transition:
            rect(0, 0, WIDTH, HEIGHT, (18, 33, 38, 175))
            center("SETOR CONCLUÍDO", 340, 34, GOLD)
            center("+1 VIDA / LOJA DE SUPRIMENTOS", 296, 16)
        if self.paused:
            rect(0, 0, WIDTH, HEIGHT, (18, 33, 38, 220))
            center("PAUSA", 385, 42, GOLD)
            if not self.window.reduced_effects:
                self.pause_ui.atmosphere()
            center("F8 som    F9 reduzir efeitos", 175, 13)
            self.pause_ui.draw()
        if self.entrance:
            rect(0, 0, WIDTH, HEIGHT, (9, 21, 28, int(255 * self.entrance / 0.4)))
        cabinet_overlay(self.window, WIDTH, HEIGHT)

    def draw_terrain_caps(self):
        if self.stage.theme == "jungle":
            return
        for b in self.blocks:
            if abs(b.center_x - self.camera_x) > WIDTH / 2 + 60:
                continue
            if self.stage.theme == "foundry":
                rect(b.left, b.bottom, b.width, b.height, (52, 68, 82, 245))
                rect(b.left, b.top - 5, b.width, 5, (117, 139, 149))
                arcade.draw_line(
                    b.left + 4, b.bottom + 4, b.right - 4, b.top - 9, (87, 108, 119), 2
                )
                for x in (b.left + 5, b.right - 5):
                    arcade.draw_circle_filled(x, b.top - 11, 1.5, (164, 174, 168))
            elif self.stage.theme == "snow":
                rect(b.left, b.top - 6, b.width, 6, (216, 237, 248))
                for x in (b.left + 8, b.left + 29):
                    rect(x, b.top - 9, 8, 6, (194, 224, 241))
            else:
                rect(b.left, b.top - 5, b.width, 5, (201, 152, 91))

    def resume_pause(self):
        self.paused = False
        self.clear_input()
        self.accumulator = 0.0
        self.window.set_mouse_visible(False)

    def weather(self):
        if self.window.reduced_effects:
            return
        if self.stage.theme == "snow":
            for i in range(38):
                x = (i * 137 - self.run.time * 28) % WIDTH
                y = (i * 83 - self.run.time * (25 + i % 8)) % HEIGHT
                arcade.draw_circle_filled(x, y, 1 + (i % 2), (220, 237, 250, 135))
        elif self.stage.theme == "foundry":
            for i in range(18):
                arcade.draw_circle_filled(
                    (i * 131 + math.sin(self.run.time + i) * 9) % WIDTH,
                    (i * 73 + self.run.time * 27) % HEIGHT,
                    1.5,
                    (255, 164, 71, 90),
                )

    def draw_supply(self):
        rect(117, 96, 42, 32, (39, 91, 75))
        rect(120, 123, 36, 4, GOLD)
        text("[ B ] LOJA", 108, 148, 11, GOLD, bold=True)

    def draw_exit(self):
        x = self.stage.length - 80
        ready = len(self.coins) <= self.total_coins - self.coin_goal
        rect(x, 96, 6, 144, (220, 212, 162))
        arcade.draw_triangle_filled(
            x + 6, 235, x + 66, 218, x + 6, 201, GOLD if ready else (111, 142, 111)
        )
        text("SAÍDA", x - 24, 77, 12, GOLD, bold=True)

    def draw_hud(self):
        rect(0, HEIGHT - 86, WIDTH, 86, (18, 33, 38, 240))
        rect(0, HEIGHT - 89, WIDTH, 3, GOLD)
        text("COIN COMMANDO / V3", 18, HEIGHT - 25, 11, GOLD, bold=True)
        text(f"{self.run.score:06d}", 18, HEIGHT - 56, 23, WHITE, bold=True)
        text(f"$ {self.run.wallet:03d}", 18, HEIGHT - 76, 11, GOLD)
        text("VIDAS", 215, HEIGHT - 24, 10, (161, 183, 164))
        for i in range(5):
            rect(
                215 + i * 19,
                HEIGHT - 49,
                14,
                14,
                RED if i < self.run.health else (52, 67, 65),
            )
        text(
            (
                "DASH PRONTO"
                if not self.run.dash_cooldown
                else f"DASH {self.run.dash_cooldown:.1f}s"
            ),
            215,
            HEIGHT - 73,
            10,
        )
        text(self.weapon.spec.name, 360, HEIGHT - 24, 11, GOLD)
        text(
            "RECARGA" if self.weapon.reloading else f"{self.weapon.ammo:02d} / ∞",
            360,
            HEIGHT - 53,
            19,
        )
        text(
            f"T: FACAS {self.run.knives:02d}   DANO +{self.run.damage_level}",
            360,
            HEIGHT - 74,
            10,
        )
        text(
            f"MOEDAS {self.collected:02d}/{self.total_coins:02d}", 595, HEIGHT - 26, 12
        )
        text(f"META {self.coin_goal} / 70%", 595, HEIGHT - 49, 10, GOLD)
        text(f"{self.run.time:06.1f}s", 595, HEIGHT - 74, 12)
        text(f"SETOR {self.run.stage+1:02d} / 04", 795, HEIGHT - 25, 12, GOLD)
        text(
            (
                f"COMBO {self.combo} / {min(4,1+self.combo//3)}x"
                if self.combo
                else ("SEM SOM" if self.audio.muted else "SOM ON")
            ),
            795,
            HEIGHT - 49,
            11,
        )
        text("B: LOJA NO SUPRIMENTO", 795, HEIGHT - 74, 8)
        rect(15, 12, WIDTH - 30, 30, (18, 33, 38, 225))
        text(
            "A/D mover  ESPAÇO pular  MOUSE mirar/atirar  T faca  SHIFT dash  1–4 armas  R recarga",
            26,
            23,
            10,
        )
        rect(710, 48, 225, 4, (38, 60, 58))
        rect(710, 48, 225 * self.player.center_x / self.stage.length, 4, GOLD)

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.P, arcade.key.ESCAPE):
            self.paused = not self.paused
            self.pause_ui.time = 0.0
            self.window.set_mouse_visible(self.paused)
            self.clear_input()
            self.accumulator = 0
            return
        if self.paused:
            if key == arcade.key.M:
                self.pause_ui.trigger("menu")
            self.settings(key)
            return
        if self.transition:
            return
        self.settings(key)
        self.held.add(key)
        if key in (arcade.key.W, arcade.key.UP, arcade.key.SPACE):
            if self.physics_engine.can_jump():
                self.player.change_y = 15
                self.audio.play("jump")
        elif key in (arcade.key.J, arcade.key.X):
            self.firing = True
        elif key == arcade.key.R:
            if self.weapon.reload():
                self.audio.play("reload")
        elif key == arcade.key.T:
            self.throw_knife()
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            if self.run.dash():
                self.dash_direction = (
                    -1
                    if self.held & {arcade.key.A, arcade.key.LEFT}
                    else (
                        1
                        if self.held & {arcade.key.D, arcade.key.RIGHT}
                        else self.player.virado_para
                    )
                )
                self.audio.play("jump")
        elif key == arcade.key.B:
            if (
                self.player.center_x < 260
                or self.player.center_x > self.stage.length - 260
            ):
                self.open_shop()
            else:
                self.label(
                    "LOJA NO INÍCIO / SAÍDA", self.player.center_x, self.player.top + 15
                )
        elif key in (
            arcade.key.KEY_1,
            arcade.key.KEY_2,
            arcade.key.KEY_3,
            arcade.key.KEY_4,
        ):
            self.run.equip(("ak", "smg", "shotgun", "rifle")[key - arcade.key.KEY_1])

    def settings(self, key):
        if key == arcade.key.F8:
            self.audio.toggle()
        if key == arcade.key.F9:
            self.window.reduced_effects = not self.window.reduced_effects

    def on_key_release(self, key, modifiers):
        self.held.discard(key)
        if key in (arcade.key.J, arcade.key.X):
            self.firing = (
                bool(self.held & {arcade.key.J, arcade.key.X}) or self.mouse_firing
            )

    def on_mouse_motion(self, x, y, dx, dy):
        if self.paused:
            self.pause_ui.pointer = (x, y)
            return
        self.mouse = (x, y)
        self.mouse_aim = True

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.on_mouse_motion(x, y, dx, dy)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.paused:
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.pause_ui.click(x, y)
            return
        if button == arcade.MOUSE_BUTTON_LEFT and not self.paused:
            self.on_mouse_motion(x, y, 0, 0)
            self.mouse_firing = True
            self.firing = True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_firing = False
            self.firing = bool(self.held & {arcade.key.J, arcade.key.X})

    def on_hide_view(self):
        self.clear_input()
        self.window.set_mouse_visible(True)


class Backdrop(arcade.View):
    def __init__(self):
        super().__init__()
        self.background = arcade.load_texture(asset("ruins.png"))
        self.camera = arcade.Camera2D()
        self.ui = ScreenMotion(self)
        self.ui.add(
            "back",
            "M / ESC / VOLTAR",
            (340, 74, 280, 36),
            lambda: self.window.show_view(TelaMenu()),
        )

    def begin(self):
        self.clear()
        self.camera.use()
        t = self.ui.time
        drift = 0 if self.window.reduced_effects else math.sin(t * 0.18) * 12
        arcade.draw_texture_rect(
            self.background,
            arcade.LBWH(-24 + drift, -12, WIDTH + 48, HEIGHT + 24),
            pixelated=True,
        )
        rect(0, 0, WIDTH, HEIGHT, (12, 31, 31, 120))
        if not self.window.reduced_effects:
            self.ui.atmosphere()
            beam_x = WIDTH * 0.64 + math.sin(t * 0.22) * 140
            arcade.draw_triangle_filled(
                beam_x - 160,
                0,
                beam_x + 180,
                0,
                beam_x + 200,
                HEIGHT,
                (233, 227, 163, 12),
            )

    def on_update(self, dt):
        self.ui.update(dt)

    def on_mouse_motion(self, x, y, dx, dy):
        self.ui.pointer = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.ui.click(x, y)

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.ESCAPE, arcade.key.M):
            self.ui.trigger("back")
        elif key == arcade.key.F8:
            self.window.audio.toggle()
        elif key == arcade.key.F9:
            self.window.reduced_effects = not self.window.reduced_effects


class TelaMenu(Backdrop):
    def __init__(self):
        super().__init__()
        self.scene = ArcadeMenuScene()
        self.ui.buttons.clear()
        self.ui.arcade_menu = True
        self.ui.selection = "play"
        entries = [
            ("play", "JOGAR", lambda: self.window.show_view(TelaLoja(TelaJogo()))),
            ("shop", "LOJA", lambda: self.window.show_view(TelaLoja(TelaJogo()))),
            ("options", "OPCOES", lambda: self.window.show_view(TelaOpcoes())),
            ("about", "CREDITOS", lambda: self.window.show_view(TelaSobre())),
            ("exit", "SAIR", lambda: self.window.close()),
        ]
        for i, (id, label, action) in enumerate(entries):
            self.ui.add(id, label, (52, 345 - i * 73, 278, 64), action)

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.scene.draw(self.ui.time)
        self.ui.draw()

    def on_key_press(self, key, modifiers):
        mapping = {
            arcade.key.J: "play",
            arcade.key.ENTER: "play",
            arcade.key.B: "shop",
            arcade.key.O: "options",
            arcade.key.S: "about",
            arcade.key.ESCAPE: "exit",
        }
        if key in (arcade.key.UP, arcade.key.DOWN):
            ids = [b.id for b in self.ui.buttons]
            i = ids.index(self.ui.selection)
            self.ui.selection = ids[
                (i + (-1 if key == arcade.key.UP else 1)) % len(ids)
            ]
            self.ui.pointer = (-100, -100)
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            self.ui.trigger(self.ui.selection)
        elif key in mapping:
            self.ui.trigger(mapping[key])
        elif key == arcade.key.R:
            self.window.show_view(TelaRanking())
        elif key == arcade.key.I:
            self.window.show_view(TelaInstrucoes())
        else:
            super().on_key_press(key, modifiers)


class TelaOpcoes(Backdrop):
    def __init__(self):
        super().__init__()
        self.background = arcade.load_texture(asset("arcade-menu.png"))
        self.ui.buttons.clear()
        self.ui.add(
            "sound", "SOM", (235, 415, 490, 50), lambda: self.window.audio.toggle()
        )
        self.ui.add("crt", "FILTRO DE FLIPERAMA", (235, 345, 490, 50), self.toggle_crt)
        self.ui.add(
            "reduced", "EFEITOS REDUZIDOS", (235, 275, 490, 50), self.toggle_reduced
        )
        self.ui.add(
            "help",
            "CONTROLES E MANUAL",
            (235, 205, 490, 50),
            lambda: self.window.show_view(TelaInstrucoes()),
        )
        self.ui.add(
            "back",
            "VOLTAR AO MENU",
            (300, 105, 360, 45),
            lambda: self.window.show_view(TelaMenu()),
        )

    def toggle_crt(self):
        self.window.arcade_filter = not self.window.arcade_filter

    def toggle_reduced(self):
        self.window.reduced_effects = not self.window.reduced_effects

    def on_draw(self):
        self.begin()
        rect(170, 70, 620, 495, (8, 12, 43, 230))
        pixel_text("OPCOES", 480, 505, 5, center=True)
        for b in self.ui.buttons:
            state = {
                "sound": not self.window.audio.muted,
                "crt": self.window.arcade_filter,
                "reduced": self.window.reduced_effects,
            }.get(b.id)
            if state is not None:
                b.subtitle = "LIGADO" if state else "DESLIGADO"
        self.ui.draw()


class TelaLoja(Backdrop):
    catalog = (
        ("smg", "02 / VESPA SMG", "40 tiros • cadência alta"),
        ("shotgun", "03 / ESCOPETA", "5 projéteis • curta distância"),
        ("rifle", "04 / PRECISÃO", "4 de dano • perfura 2 alvos"),
        ("knives", "FACAS / PACOTE DE 5", "T lança na direção da mira"),
        ("damage", "MELHORIA DE DANO", "+1 por projétil • máximo 3"),
        ("rate", "MELHORIA DE CADÊNCIA", "+13% de ritmo • máximo 2"),
        ("heal", "KIT MÉDICO", "Recupera 2 vidas • máximo 5"),
    )

    def __init__(self, game, between=False):
        super().__init__()
        self.game = game
        self.between = between
        self.message = "Escolha seu arsenal. A pontuação do ranking não é gasta."
        self.background = arcade.load_texture(asset(game.stage.background))
        self.ui.buttons.clear()
        for i, (key, label, subtitle) in enumerate(self.catalog):
            col = i % 2
            row = i // 2
            box = (55 + col * 435, 406 - row * 79, 415, 66)
            self.ui.add(key, label, box, lambda item=key: self.purchase(item), subtitle)
        self.ui.add(
            "resume",
            (
                "ENTER / INICIAR SETOR"
                if between or game.run.time == 0
                else "ENTER / VOLTAR AO COMBATE"
            ),
            (490, 169, 415, 66),
            self.resume,
            "As compras duram esta campanha",
        )
        self.ui.add(
            "menu",
            "M / ENCERRAR CAMPANHA",
            (55, 62, 300, 35),
            lambda: self.window.show_view(TelaMenu()),
        )

    def on_show_view(self):
        self.game.clear_input()
        self.window.set_mouse_visible(True)

    def purchase(self, key):
        ok, self.message = self.game.run.buy(key)
        self.window.audio.play("coin" if ok else "hit")

    def resume(self):
        self.game.paused = False
        self.game.accumulator = 0.0
        self.window.show_view(self.game)

    def on_draw(self):
        self.begin()
        rect(25, 30, 910, 568, (12, 26, 34, 220))
        text("ARSENAL / SUPRIMENTOS", 55, 550, 23, GOLD, bold=True)
        text(f"CRÉDITOS $ {self.game.run.wallet:03d}", 620, 553, 23, GOLD, bold=True)
        text(
            f"{self.game.stage.name}     VIDA {self.game.run.health}/5     FACAS {self.game.run.knives}",
            57,
            512,
            12,
        )
        text(
            "1 AK-47   2 SMG   3 ESCOPETA   4 RIFLE • troque durante a partida",
            57,
            488,
            10,
            (164, 191, 180),
        )
        for b in self.ui.buttons:
            item = next((entry for entry in self.catalog if entry[0] == b.id), None)
            if item:
                owned = b.id in self.game.run.weapons
                value = "COMPRADA" if owned else f"$ {self.game.run.price(b.id)}"
                b.label = f"{item[1]} / {value}"
        text(self.message, 57, 122, 12, GOLD)
        self.ui.draw()

    def on_key_press(self, key, modifiers):
        if key in (
            arcade.key.ENTER,
            arcade.key.RETURN,
            arcade.key.ESCAPE,
            arcade.key.B,
        ):
            self.ui.trigger("resume")
        elif key == arcade.key.M:
            self.ui.trigger("menu")
        else:
            super().on_key_press(key, modifiers)


class TelaInstrucoes(Backdrop):
    def on_draw(self):
        self.begin()
        rect(80, 56, 800, 540, (18, 33, 38, 240))
        center("MANUAL DE CAMPO", 541, 30, GOLD)
        lines = [
            "A / D ou ← / →  —  mover; ESPAÇO / W / ↑  —  pular",
            "MOUSE  —  mirar livremente; clique esquerdo / J / X  —  disparar",
            "T  —  lançar uma faca comprada; 1 / 2 / 3 / 4  —  trocar arma",
            "SHIFT  —  dash com breve proteção; R  —  recarregar",
            "B  —  loja no suprimento inicial ou perto da saída; pausa entre fases",
            "P / ESC  —  pausar; M na pausa volta ao menu",
            "F8  —  som; F9  —  reduzir flashes, clima e tremor",
            "",
            "Colete 70% das moedas e alcance a bandeira. As demais são bônus.",
            "Moedas e inimigos dão créditos para comprar equipamentos.",
            "Pontuação e créditos são separados. Compras duram esta campanha.",
            "Minas avisam antes de explodir; lasers amarelos vão ficar vermelhos.",
            "Barris explodem perto dos inimigos e também podem ferir você.",
            "Abates rápidos sobem o combo. O chefe fica furioso com meia vida.",
        ]
        for i, line in enumerate(lines):
            text(line, 104, 494 - i * 27, 12)
        self.ui.draw()


class TelaSobre(Backdrop):
    def on_draw(self):
        self.begin()
        rect(140, 150, 680, 340, (18, 33, 38, 240))
        center("SOBRE O PROJETO", 429, 28, GOLD)
        center("Vitor Rufino Brumatti / 3º Info", 362, 20)
        center("IFPR • Programação Orientada a Objetos", 321, 16)
        center("Python Arcade • Física • Animação • Peewee / SQLite", 278, 14)
        center("V3 / ARCADE EDITION — arte e sons originais", 240, 12)
        self.ui.draw()


class TelaRanking(Backdrop):
    def __init__(self):
        super().__init__()
        self.melhores = list(
            Pontuacao.select()
            .order_by(Pontuacao.pontos.desc(), Pontuacao.tempo_partida.asc())
            .limit(10)
        )
        self.ui.buttons.clear()
        self.ui.add(
            "play",
            "J / NOVA MISSÃO",
            (190, 72, 270, 38),
            lambda: self.window.show_view(TelaLoja(TelaJogo())),
        )
        self.ui.add(
            "back",
            "M / ESC / MENU",
            (500, 72, 270, 38),
            lambda: self.window.show_view(TelaMenu()),
        )

    def on_draw(self):
        self.begin()
        rect(110, 56, 740, 534, (18, 33, 38, 240))
        center("TOP 10 / HALL DA FAMA", 535, 29, GOLD)
        for label, x in [
            ("POS", 145),
            ("JOGADOR", 220),
            ("PONTOS", 585),
            ("TEMPO", 725),
        ]:
            text(label, x, 485, 12, (164, 185, 169))
        if not self.melhores:
            center("Nenhuma pontuação registrada. Seja o primeiro!", 315, 17)
        for indice, registro in enumerate(self.melhores):
            y = 444 - indice * 32
            if indice % 2 == 0:
                rect(130, y - 5, 700, 30, (44, 61, 57))
            arcade.draw_text(f"{indice+1:02d}", 145, y, GOLD, 15)
            arcade.draw_text(registro.nome_jogador, 220, y, WHITE, 15)
            arcade.draw_text(str(registro.pontos), 595, y, GOLD, 15)
            arcade.draw_text(f"{registro.tempo_partida:.1f}s", 725, y, WHITE, 15)
        self.ui.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.J:
            self.ui.trigger("play")
        else:
            super().on_key_press(key, modifiers)


class TelaGameOver(Backdrop):
    def __init__(self, pontos, tempo, victory=False):
        super().__init__()
        self.pontos = pontos
        self.tempo = tempo
        self.victory = victory
        self.nome_jogador = ""
        self.salvo = False
        self.mensagem = "Digite seu nome e pressione ENTER."
        self.ui.buttons.clear()
        self.ui.add(
            "save", "ENTER / REGISTRAR RESULTADO", (270, 150, 420, 45), self.save_result
        )
        self.ui.add(
            "back",
            "ESC / MENU SEM SALVAR",
            (325, 95, 310, 34),
            lambda: self.window.show_view(TelaMenu()),
        )

    def on_draw(self):
        self.begin()
        rect(140, 100, 680, 445, (18, 33, 38, 245))
        center(
            "MISSÃO CUMPRIDA" if self.victory else "FIM DE COMBATE",
            474,
            33,
            GOLD if self.victory else RED,
        )
        center(f"{self.pontos:06d} PONTOS", 401, 31)
        center(f"TEMPO {self.tempo:.1f}s", 360, 16)
        if not self.salvo:
            center("NOME DO JOGADOR", 295, 12, (164, 185, 169))
            rect(265, 225, 430, 48, (43, 60, 56))
            center(self.nome_jogador or "_", 240, 22, GOLD)
            center(self.mensagem, 210, 12)

        else:
            center("PONTUAÇÃO SALVA!", 273, 22, GOLD)

        self.ui.draw()

    def save_result(self):
        self.on_key_press(arcade.key.ENTER, 0)

    def on_text(self, value):
        if not self.salvo and value.isprintable():
            self.nome_jogador += value[: max(0, 20 - len(self.nome_jogador))]

    def on_key_press(self, key, modifiers):
        if not self.salvo:
            if key == arcade.key.BACKSPACE:
                self.nome_jogador = self.nome_jogador[:-1]
            elif key in (arcade.key.ENTER, arcade.key.RETURN):
                name = self.nome_jogador.strip()
                if not name:
                    self.mensagem = "Digite pelo menos um caractere."
                    return
                try:
                    Pontuacao.create(
                        nome_jogador=name, pontos=self.pontos, tempo_partida=self.tempo
                    )
                except Exception:
                    self.mensagem = (
                        "Não foi possível salvar. Verifique a pasta e tente novamente."
                    )
                    return
                self.salvo = True
                self.ui.buttons.clear()
                self.ui.add(
                    "rank",
                    "R / RANKING",
                    (165, 165, 220, 48),
                    lambda: self.window.show_view(TelaRanking()),
                )
                self.ui.add(
                    "play",
                    "J / NOVA MISSÃO",
                    (399, 165, 230, 48),
                    lambda: self.window.show_view(TelaLoja(TelaJogo())),
                )
                self.ui.add(
                    "back",
                    "M / MENU",
                    (643, 165, 150, 48),
                    lambda: self.window.show_view(TelaMenu()),
                )
            elif key == arcade.key.ESCAPE:
                self.ui.trigger("back")
            return
        if key == arcade.key.R:
            self.ui.trigger("rank")
        elif key == arcade.key.J:
            self.ui.trigger("play")
        elif key in (arcade.key.M, arcade.key.ESCAPE):
            self.ui.trigger("back")


class GameWindow(arcade.Window):
    def __init__(self, visible=True):
        super().__init__(
            WIDTH,
            HEIGHT,
            "Coin Commando / Projeto Moedas",
            visible=visible,
            update_rate=1 / 60,
            vsync=True,
        )
        self.audio = Audio()
        self.reduced_effects = False
        self.arcade_filter = True

    def on_deactivate(self):
        view = self.current_view
        if isinstance(view, TelaJogo):
            view.paused = True
            view.pause_ui.time = 0.0
            self.set_mouse_visible(True)
            view.held.clear()
            view.firing = False
            view.mouse_firing = False
