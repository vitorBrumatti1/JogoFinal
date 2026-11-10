"""Campanha arcade: física fixa, câmera de mundo e HUD independente."""

import math
import random
from pathlib import Path
import arcade
from actors import Jogador, Pontuacao, inicializar_banco
from campaign import Campaign, Weapon, STAGES, WEAPONS
from ui_fx import ScreenMotion
from world_fx import Hazard, Barrel, draw_gun
from effects import Particula, TextoFlutuante, Casing, SpriteEcho
from polish import TextPool, enemy_role
from level_design import COVER_POSITIONS, ground_lane
from sound import Audio
from weapon_art import GunPose, RECOIL, FLASH_TIME, draw_weapon
from combat import Grenade, Impact, Cover, swept_contacts, draw_projectile, muzzle_flash
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
    def __init__(self, x, y, bridge=False, wall=False, ballistic=False):
        super().__init__(
            asset("bridge.png" if bridge else ("wall.png" if wall else "stone.png"))
        )
        self.ballistic = ballistic
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
        self.hurt = 0.0
        self.knockback = 0.0
        self.volley = 0
        self.target_x = x
        self.base_color = (
            (255, 255, 255)
            if kind == "guard"
            else (
                (166, 199, 255)
                if kind == "shooter"
                else (255, 153, 127) if kind == "charger" else (255, 255, 255)
            )
        )
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
        self.color = self.base_color

    def receive_hit(self, damage, direction, kind="ak"):
        self.hp -= damage
        self.hurt = 0.09
        self.knockback = direction * (
            0.7 if self.kind == "boss" else 4 if kind in ("shotgun", "rifle") else 2
        )

    def tick(self, dt, player):
        self.hurt = max(0.0, self.hurt - dt)
        self.color = (255, 135, 116) if self.hurt else self.base_color
        self.center_x += self.knockback
        self.knockback *= 0.75
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
                self.direction
                * self.speed
                * (
                    (1.8 if 0.35 < self.phase % 2.4 < 1.35 else 0.55)
                    if self.kind == "charger"
                    else 1
                )
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
    def __init__(
        self, x, y, vx, vy=0, hostile=False, damage=1, pierce=1, knife=False, kind="ak"
    ):
        super().__init__(
            24 if knife else (14 if not hostile else 10),
            4 if knife else 5,
            color=(216, 233, 235) if knife else (GOLD if not hostile else RED),
        )
        self.position = x, y
        self.change_x = vx
        self.change_y = vy
        self.life = 1.8
        self.kind = kind
        self.origin = (x, y)
        self.previous_position = (x, y)
        self.hostile = hostile
        self.damage = damage
        self.pierce = pierce
        self.knife = knife
        self.hit_ids = set()
        self.angle = math.degrees(math.atan2(vy, vx))

    def tick(self, dt):
        self.previous_position = self.position
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
        self.casings = []
        self.echoes = []
        self._dash_echo = 0.0
        self._grounded_before = False
        self.hud = TextPool()
        self.currency_pulse = 0.0
        self.weapon_banner = 0.0
        self.labels = []
        self.shake = 0.0
        self.flash = 0.0
        self.muzzle = 0.0
        self.recoil = 0.0
        self.last_shot_origin = None
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
        self.ballistic = arcade.SpriteList(use_spatial_hash=True)
        self.covers = arcade.SpriteList()
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
            floor = Bloco(x, 96, ballistic=True)
            self.blocks.append(floor)
            self.ballistic.append(floor)
            self.decor.append(Bloco(x, 48, wall=True))
        for idx, (x, y, w) in enumerate(self.stage.platforms):
            for bx in range(int(x - w / 2), int(x + w / 2), 48):
                self.blocks.append(Bloco(bx, y, bridge=idx % 3 == 1))
                if idx % 3 != 1:
                    self.decor.append(Bloco(bx, y - 48, wall=True))
            offsets = (
                (-28, 28)
                if w == 144
                else (-72, -24, 24, 72) if w == 240 else (-50, 0, 50)
            )
            for offset in offsets:
                self.add_coin(
                    x + offset,
                    y + 32,
                    special=idx == len(self.stage.platforms) - 1 and offset == 0,
                )
            if idx == len(self.stage.platforms) - 1 and 0 not in offsets:
                self.add_coin(x, y + 32, special=True)
            if idx % 3 == 0:
                self.barrels.append(Barrel(x + 68, y + 17))
        for x in range(180, self.stage.length - 180, 260):
            if not any(
                y < 200 and px - pw / 2 - 30 < x < px + pw / 2 + 30
                for px, y, pw in self.stage.platforms
            ) and not any(
                cx - 30 < x < cx + 66 for cx in COVER_POSITIONS[self.run.stage]
            ):
                self.add_coin(x, 128)
        for x in COVER_POSITIONS[self.run.stage]:
            cover = Cover(x)
            self.covers.append(cover)
            self.blocks.append(cover)
            self.ballistic.append(cover)
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
            kind = (
                "shooter" if i % 3 == 1 and (self.run.stage > 0 or i > 2) else "guard"
            )
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
                x, left, right = ground_lane(
                    self.stage, x, COVER_POSITIONS[self.run.stage]
                )
            self.enemies.append(Enemy(x, y, kind, self.run.stage, left, right))
        self.boss = None
        self.boss_introduced = False
        self.boss_intro = 0.0
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
        self.casings.clear()
        self.echoes.clear()
        self._grounded_before = False
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

    def gun_pose(self):
        return GunPose(
            (self.player.center_x, self.player.center_y + 3),
            self.aim_angle,
            self.weapon.kind,
            self.recoil,
        )

    def fire(self):
        if self.weapon.ammo == 0 and not self.weapon.reloading:
            if self.weapon.reload():
                self.audio.play("reload_v4")
        if not self.weapon.fire():
            return
        self.aim()
        self.recoil = RECOIL[self.weapon.kind]
        pose = self.gun_pose()
        x, y = pose.muzzle
        self.last_shot_origin = (x, y)
        self.muzzle = FLASH_TIME[self.weapon.kind]
        spec = self.weapon.spec
        for i in range(spec.pellets):
            spread = (
                (i - (spec.pellets - 1) / 2) * spec.spread
                if spec.pellets > 1
                else random.uniform(-spec.spread, spec.spread)
            )
            a = self.aim_angle + spread
            bullet = Bullet(
                x,
                y,
                math.cos(a) * spec.speed,
                math.sin(a) * spec.speed,
                damage=spec.damage + self.run.damage_level,
                pierce=spec.pierce,
                kind=self.weapon.kind,
            )
            bullet.prefix_start = pose.pivot
            self.bullets.append(bullet)
        self.audio.play("shot_" + self.weapon.kind)
        if len(self.casings) < 24:
            self.casings.append(
                Casing(*pose.point(1, 4), 1 if math.cos(self.aim_angle) > 0 else -1)
            )
        if self.weapon.kind in ("shotgun", "rifle"):
            self.shake = max(
                self.shake, 0.08 if self.weapon.kind == "shotgun" else 0.06
            )

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
        self.audio.play("damage")
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
        self.audio.play("impact")
        if len(self.echoes) < 20:
            self.echoes.append(SpriteEcho(enemy, death=True))
        self.burst(*enemy.position, (255, 151, 57), 24)
        self.label(f"+{gain} / {multiplier}x", enemy.center_x, enemy.top)
        self.shake = 0.17
        self.hitstop = 0.025
        enemy.remove_from_sprite_lists()

    def explode(self, x, y, radius=110):
        self.audio.play("boom_v4")
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
        self.boss_intro = max(0.0, self.boss_intro - dt)
        if (
            self.boss
            and not self.boss_introduced
            and self.player.center_x > self.stage.length - 900
        ):
            self.boss_introduced = True
            self.boss_intro = 1.8
            self.run.invulnerable = max(self.run.invulnerable, 1.8)
            self.audio.play("menu")
        self.currency_pulse = max(0.0, self.currency_pulse - dt)
        self.weapon_banner = max(0.0, self.weapon_banner - dt)
        self._dash_echo = max(0.0, self._dash_echo - dt)
        for item in self.casings + self.echoes:
            item.update(dt)
        self.casings = [item for item in self.casings if item.life > 0]
        self.echoes = [item for item in self.echoes if item.life > 0]
        self.muzzle = max(0, self.muzzle - dt)
        self.recoil = max(0.0, self.recoil - dt * 34)
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
        self.aim()
        self.player.grounded = self.physics_engine.can_jump()
        self.player.aim_facing = (
            (1 if math.cos(self.aim_angle) >= 0 else -1) if self.mouse_aim else None
        )
        self.player.update(dt)
        if (
            self.player.grounded
            and not self._grounded_before
            and self.player.tempo_total > 0.15
        ):
            self.burst(self.player.center_x, self.player.bottom, (176, 171, 141), 5)
            self.audio.play("land")
        self._grounded_before = self.player.grounded
        if self.run.dash_time and not self._dash_echo and len(self.echoes) < 20:
            self.echoes.append(SpriteEcho(self.player))
            self._dash_echo = 0.04
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
            self.currency_pulse = 0.3
            self.collected += 1
            self.audio.play("coin_v4")
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
        self.update_projectiles(dt)
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

    def update_projectiles(self, dt):
        friendly_groups = [
            ("cover", self.ballistic),
            ("grenade", self.grenades),
            ("barrel", self.barrels),
            ("enemy", self.enemies),
        ]
        hostile_groups = [("cover", self.ballistic), ("player", self.players)]
        for projectiles, groups in (
            (self.bullets, friendly_groups),
            (self.hostile, hostile_groups),
        ):
            for bullet in list(projectiles):
                prefix_start = getattr(bullet, "prefix_start", None)
                if prefix_start is not None:
                    del bullet.prefix_start
                bullet.tick(dt)
                if (
                    bullet.life <= 0
                    or bullet.center_x < -100
                    or bullet.center_x > self.stage.length + 100
                    or not -100 < bullet.center_y < 900
                ):
                    bullet.remove_from_sprite_lists()
                    continue
                for _, _, category, target, point in swept_contacts(
                    prefix_start or bullet.previous_position,
                    bullet.position,
                    groups,
                    radius=2.0,
                ):
                    if category == "enemy":
                        if target not in self.enemies or id(target) in bullet.hit_ids:
                            continue
                        bullet.hit_ids.add(id(target))
                        target.receive_hit(
                            bullet.damage,
                            1 if bullet.change_x >= 0 else -1,
                            bullet.kind,
                        )
                        self.audio.play("impact")
                        bullet.pierce -= 1
                        self.impact(*point)
                        self.burst(*point, GOLD, 4)
                        if target.hp <= 0:
                            self.defeat(target)
                        if bullet.pierce > 0:
                            continue
                    elif category == "grenade":
                        if target not in self.grenades:
                            continue
                        target.remove_from_sprite_lists()
                        self.explode(*target.position, radius=90)
                    elif category == "barrel":
                        if target not in self.barrels:
                            continue
                        target.remove_from_sprite_lists()
                        self.explode(*target.position)
                    elif category == "player":
                        self.damage()
                    else:
                        self.impact(*point)
                    bullet.position = point
                    bullet.remove_from_sprite_lists()
                    break

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
                self.player, self.ballistic
            )
            enemy.aim_time = min(0.65, enemy.aim_time + dt) if eligible else 0.0
            if eligible and enemy.shot_clock < 0.65 and not enemy.alert:
                enemy.target_x = self.player.center_x
            enemy.alert = eligible and enemy.shot_clock < 0.65
            if not eligible or enemy.shot_clock > 0 or enemy.aim_time < 0.6:
                continue
            a = math.atan2(
                self.player.center_y - enemy.center_y,
                self.player.center_x - enemy.center_x,
            )
            enraged = enemy.kind == "boss" and enemy.hp < enemy.max_hp * 0.5
            speed = 3.0 + self.run.stage * 0.25
            enemy.volley += 1
            mortar = enemy.kind == "boss" and enemy.volley % 3 == 0
            if mortar:
                for drift in (-0.5, 0.5):
                    grenade = Grenade(
                        enemy.center_x,
                        enemy.top + 12,
                        max(-4, min(4, (enemy.target_x - enemy.center_x) / 85)) + drift,
                    )
                    grenade.change_y = 3.0
                    if len(self.grenades) < 8:
                        self.grenades.append(grenade)
            else:
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
        self.audio.play("victory" if victory else "defeat")
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
        shake = 0 if self.window.reduced_effects else min(4, self.shake * 20)
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
        for cover in self.covers:
            cover.draw_fx(self.stage.theme)
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
        self.draw_environment_details()
        self.draw_supply()
        self.draw_exit()
        self.coins.draw(pixelated=True)
        self.enemies.draw(pixelated=True)
        for echo in self.echoes:
            echo.draw()
        self.players.draw(pixelated=True)
        self.aim()
        draw_weapon(self.gun_pose())
        for bullet in self.bullets:
            draw_projectile(bullet)
        for bullet in self.hostile:
            draw_projectile(bullet)
        for grenade in self.grenades:
            grenade.draw_fx()
        if self.muzzle:
            x, y = self.gun_pose().muzzle
            muzzle_flash(x, y, self.aim_angle, self.weapon.kind)
        for casing in self.casings:
            casing.draw()
        for effect in self.impacts:
            effect.draw()
        for p in self.particles:
            p.draw()
        for p in self.labels:
            p.draw()
        for enemy in self.enemies:
            enemy_role(enemy)
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
        if self.boss_intro:
            rect(180, 88, 600, 72, (18, 31, 47, 220))
            center("GUARDIÃO GLACIAL", 127, 24, GOLD)
            center("Observe a mira. Rajadas e morteiros alternados.", 101, 12)
        if self.boss and self.boss.hp > 0 and self.boss_introduced:
            rect(295, HEIGHT - 85, 370, 7, (41, 51, 61))
            rect(295, HEIGHT - 85, 370 * self.boss.hp / self.boss.max_hp, 7, RED)
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
            if getattr(b, "is_cover", False):
                continue
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

    def draw_environment_details(self):
        if self.window.reduced_effects:
            return
        if self.stage.theme == "jungle":
            for x, y, w in self.stage.platforms:
                if abs(x - self.camera_x) > 600:
                    continue
                for dx in (-w / 2 + 9, w / 2 - 12):
                    sway = math.sin(self.run.time * 1.8 + x) * 2
                    arcade.draw_line(
                        x + dx, y, x + dx + sway, y + 12, (100, 155, 74), 2
                    )
                    arcade.draw_line(
                        x + dx, y + 4, x + dx + sway + 5, y + 9, (128, 182, 78), 2
                    )
        elif self.stage.theme == "foundry":
            alpha = int(38 + math.sin(self.run.time * 3) * 15)
            rect(self.camera_x - WIDTH / 2, 96, WIDTH, 5, (255, 137, 52, alpha))

    def weather(self):
        if self.window.reduced_effects:
            return
        if self.stage.theme == "snow":
            for i in range(38):
                x = (i * 137 - self.run.time * 28) % WIDTH
                y = (i * 83 - self.run.time * (25 + i % 8)) % HEIGHT
                arcade.draw_circle_filled(x, y, 1 + (i % 2), (220, 237, 250, 135))
        elif self.stage.theme == "desert":
            for i in range(15):
                x = (i * 173 + self.run.time * 31) % WIDTH
                y = 130 + (i * 67) % 300
                arcade.draw_rect_filled(arcade.LBWH(x, y, 4, 1), (231, 188, 128, 95))
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
        rect(8, HEIGHT - 64, WIDTH - 16, 57, (12, 24, 34, 238))
        rect(8, HEIGHT - 65, WIDTH - 16, 2, (122, 174, 173))
        label = self.hud.draw
        label("score", f"{self.run.score:06d}", 20, HEIGHT - 30, 20, WHITE, True)
        label("scoretag", "PTS", 133, HEIGHT - 25, 8, (153, 176, 171))
        label(
            "wallet",
            f"$ {self.run.wallet:03d}",
            20,
            HEIGHT - 50,
            12,
            WHITE if self.currency_pulse else GOLD,
            True,
        )
        for i in range(5):
            x = 180 + i * 19
            y = HEIGHT - 25
            color = RED if i < self.run.health else (50, 65, 70)
            arcade.draw_polygon_filled(
                [
                    (x - 6, y + 4),
                    (x - 2, y + 7),
                    (x + 1, y + 4),
                    (x + 4, y + 7),
                    (x + 8, y + 4),
                    (x + 8, y),
                    (x + 1, y - 8),
                    (x - 6, y),
                ],
                color,
            )
        label("dash", "DASH", 176, HEIGHT - 51, 8, (160, 198, 211))
        rect(210, HEIGHT - 49, 42, 4, (42, 61, 70))
        rect(
            210,
            HEIGHT - 49,
            42 * (1 - self.run.dash_cooldown / 1.8),
            4,
            (127, 218, 235),
        )
        label("knives", f"T {self.run.knives:02d}", 264, HEIGHT - 51, 11, WHITE)
        label(
            "gun",
            self.weapon.spec.name,
            330,
            HEIGHT - 23,
            10,
            GOLD if self.weapon_banner else WHITE,
        )
        draw_weapon(GunPose((350, HEIGHT - 47), 0, self.weapon.kind), hands=False)
        label(
            "ammo",
            (
                "RECARGA"
                if self.weapon.reloading
                else f"{self.weapon.ammo:02d} / {self.weapon.capacity}"
            ),
            405,
            HEIGHT - 52,
            18,
            GOLD,
            True,
        )
        if self.weapon.reloading:
            rect(
                403,
                HEIGHT - 59,
                106 * (1 - self.weapon.reloading / self.weapon.spec.reload_time),
                2,
                GOLD,
            )
        label(
            "coins",
            f"MOEDAS {self.collected:02d}/{self.total_coins:02d}",
            575,
            HEIGHT - 25,
            11,
            WHITE,
        )
        label("goal", f"META {self.coin_goal}", 699, HEIGHT - 24, 8, GOLD)
        rect(575, HEIGHT - 48, 145, 5, (45, 65, 66))
        rect(
            575,
            HEIGHT - 48,
            145 * min(1, self.collected / max(1, self.coin_goal)),
            5,
            (244, 202, 94),
        )
        label(
            "stage", f"SETOR {self.run.stage+1:02d} / 04", 789, HEIGHT - 24, 11, WHITE
        )
        label("timer", f"{self.run.time:05.1f}s", 790, HEIGHT - 50, 12, (162, 195, 199))
        if self.combo:
            label(
                "combo",
                f"{min(4,1+self.combo//3)}x / COMBO {self.combo}",
                775,
                HEIGHT - 87,
                13,
                GOLD,
                True,
            )
            rect(774, HEIGHT - 94, 134 * self.combo_time / 3, 2, GOLD)
        if self.player.center_x < 260 and self.run.time < 12:
            rect(18, 15, 620, 28, (14, 29, 36, 215))
            label(
                "help",
                "A/D mover • ESPAÇO pular • MOUSE mirar • SHIFT dash • T faca • B loja",
                28,
                24,
                10,
                WHITE,
            )
        elif self.player.center_x > self.stage.length - 260:
            label(
                "exithelp", "B: suprimentos   /   Alcance a bandeira", 24, 22, 11, GOLD
            )
        if self.weapon_banner:
            label(
                "swap",
                self.weapon.spec.name,
                self.player.center_x - self.camera_center() + WIDTH / 2 - 35,
                self.player.top + 17,
                11,
                GOLD,
            )

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
                self.audio.play("reload_v4")
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
                self.audio.play("dash")
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
            if self.run.equip(
                ("ak", "smg", "shotgun", "rifle")[key - arcade.key.KEY_1]
            ):
                self.weapon_banner = 0.8

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
        self.message = "Compare as barras com a marca branca da arma equipada."
        self.success = True
        self.purchase_time = 0.0
        self.stats = TextPool()
        self.background = arcade.load_texture(asset(game.stage.background))
        self.ui.buttons.clear()
        for i, (key, label, subtitle) in enumerate(self.catalog):
            if i < 3:
                button = self.ui.add(
                    key,
                    WEAPONS[key].name,
                    (42 + i * 301, 318, 274, 165),
                    lambda item=key: self.purchase(item),
                    subtitle,
                )
                button.card = True
                button.render_extra = lambda b=button, item=key: self.weapon_card(
                    b, item
                )
            else:
                short = {
                    "knives": "5 FACAS",
                    "damage": "DANO +1",
                    "rate": "CADENCIA +13%",
                    "heal": "KIT MEDICO",
                }[key]
                self.ui.add(
                    key,
                    short,
                    (42 + (i - 3) * 224, 224, 204, 70),
                    lambda item=key: self.purchase(item),
                    subtitle,
                )
        self.ui.add(
            "resume",
            (
                "ENTER / INICIAR SETOR"
                if between or game.run.time == 0
                else "ENTER / VOLTAR AO COMBATE"
            ),
            (520, 112, 398, 52),
            self.resume,
            "Equipamentos acompanham a campanha",
        )
        self.ui.add(
            "menu",
            "M / ENCERRAR CAMPANHA",
            (42, 65, 320, 35),
            lambda: self.window.show_view(TelaMenu()),
        )

    def on_show_view(self):
        self.game.clear_input()
        self.window.set_mouse_visible(True)

    def on_update(self, dt):
        super().on_update(dt)
        self.purchase_time = max(0.0, self.purchase_time - dt)

    def purchase(self, key):
        if key in self.game.run.weapons:
            self.game.run.equip(key)
            self.success = True
            self.message = "Arma equipada. Nenhum crédito descontado."
        else:
            self.success, self.message = self.game.run.buy(key)
        self.purchase_time = 0.45
        self.game.currency_pulse = 0.3
        self.game.weapon_banner = 0.8
        self.window.audio.play("coin_v4" if self.success else "damage")

    def resume(self):
        self.game.paused = False
        self.game.accumulator = 0.0
        self.window.show_view(self.game)

    def weapon_card(self, button, key):
        x, y, w, h = button.box
        spec = WEAPONS[key]
        run = self.game.run
        draw_weapon(GunPose((x + 62, y + 101), 0, key), hands=False)
        owned = key in run.weapons
        badge = (
            "EQUIPADA"
            if run.equipped == key
            else "ADQUIRIDA" if owned else f"$ {spec.price}"
        )
        tint = (121, 224, 207) if owned else GOLD if run.wallet >= spec.price else RED
        self.stats.draw(key + "badge", badge, x + 153, y + 101, 10, tint, True)
        values = (
            ("DANO", spec.damage / 4, run.weapon.spec.damage / 4),
            (
                "RITMO",
                min(1, 0.065 / spec.interval),
                min(1, 0.065 / run.weapon.spec.interval),
            ),
            ("PENTE", spec.capacity / 40, run.weapon.spec.capacity / 40),
        )
        for i, (name, value, comparison) in enumerate(values):
            by = y + 72 - i * 15
            self.stats.draw(key + name, name, x + 18, by, 8, (166, 189, 189))
            rect(x + 81, by + 2, 166, 4, (42, 61, 68))
            rect(x + 81, by + 2, 166 * min(1, value), 4, tint)
            marker = x + 81 + 166 * min(1, comparison)
            rect(marker, by, 2, 8, WHITE)
        if owned:
            arcade.draw_rect_outline(
                arcade.LBWH(x + 1, y + 1, w - 2, h - 2), (70, 167, 159), 1
            )

    def on_draw(self):
        self.begin()
        rect(25, 30, 910, 568, (12, 26, 34, 232))
        text("ARSENAL / SUPRIMENTOS", 42, 550, 23, GOLD, bold=True)
        text(f"$ {self.game.run.wallet:03d}", 767, 549, 25, GOLD, bold=True)
        text(
            f"{self.game.stage.name}    VIDA {self.game.run.health}/5    FACAS {self.game.run.knives}",
            44,
            515,
            12,
        )
        text(
            f"ATUAL: {self.game.weapon.spec.name}  /  CLIQUE EM UMA ARMA ADQUIRIDA PARA EQUIPAR",
            44,
            494,
            9,
            (157, 188, 183),
        )
        for b in self.ui.buttons:
            if b.id in WEAPONS:
                spec = WEAPONS[b.id]
                b.label = spec.name.replace("RIFLE DE PRECISÃO", "RIFLE PRECISAO")
                b.subtitle = (
                    "5 projéteis / disparo"
                    if b.id == "shotgun"
                    else (
                        "Perfura dois alvos"
                        if b.id == "rifle"
                        else "Leve / recarga rápida"
                    )
                )
                b.unavailable = (
                    b.id not in self.game.run.weapons
                    and self.game.run.wallet < spec.price
                )
            elif b.id in ("knives", "damage", "rate", "heal"):
                b.subtitle = (
                    f"$ {self.game.run.price(b.id)}  / "
                    + {
                        "knives": f"ESTOQUE {self.game.run.knives}/30",
                        "damage": f"NIVEL {self.game.run.damage_level}/3",
                        "rate": f"NIVEL {self.game.run.rate_level}/2",
                        "heal": "+2 VIDAS",
                    }[b.id]
                )
                b.unavailable = self.game.run.wallet < self.game.run.price(b.id)
        text(self.message, 44, 191, 11, (132, 225, 190) if self.success else RED)
        self.ui.draw()
        if self.purchase_time:
            rect(42, 184, 876, 2, (121, 224, 207) if self.success else RED)

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
