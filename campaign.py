"""Regras de campanha, arsenal e loja independentes da interface gráfica."""

from dataclasses import dataclass, replace
from level_design import LAYOUTS


@dataclass(frozen=True)
class WeaponSpec:
    name: str
    price: int
    capacity: int
    interval: float
    reload_time: float
    damage: int
    speed: float
    pellets: int = 1
    spread: float = 0
    pierce: int = 1
    color: tuple = (240, 197, 83)


WEAPONS = {
    "ak": WeaponSpec("AK-47", 0, 30, 0.105, 1.4, 1, 16, color=(188, 122, 67)),
    "smg": WeaponSpec(
        "VESPA / SMG", 32, 40, 0.065, 1.15, 1, 15, spread=0.025, color=(89, 200, 192)
    ),
    "shotgun": WeaponSpec(
        "ESCOPETA", 46, 7, 0.48, 1.7, 1, 14, 5, 0.18, color=(243, 166, 81)
    ),
    "rifle": WeaponSpec(
        "RIFLE DE PRECISÃO", 68, 10, 0.32, 1.8, 4, 22, pierce=2, color=(151, 176, 238)
    ),
}


@dataclass(frozen=True)
class Stage:
    name: str
    length: int
    enemies: int
    platforms: tuple
    tint: tuple
    subtitle: str
    theme: str = "jungle"
    background: str = "ruins.png"
    hazards: tuple = ()


ROUTE = tuple(
    (x, y, 192)
    for x, y in [
        (340, 192),
        (620, 288),
        (900, 192),
        (1180, 288),
        (1460, 384),
        (1740, 288),
        (2020, 192),
        (2300, 288),
        (2580, 192),
    ]
)


def route(points):
    return tuple((x, y, 192) for x, y in points)


STAGES = (
    Stage(
        "01 / SELVA EM ALERTA",
        3000,
        12,
        ROUTE,
        (255, 255, 255),
        "Patrulhas armadas. Barris podem virar o combate.",
        "jungle",
        "ruins.png",
        ((770, "mine"), (1580, "mine"), (2420, "mine")),
    ),
    Stage(
        "02 / ROTA DO DESERTO",
        3400,
        17,
        route(
            [
                (320, 192),
                (600, 288),
                (880, 384),
                (1160, 240),
                (1440, 336),
                (1720, 240),
                (2000, 336),
                (2280, 192),
                (2560, 288),
                (2840, 384),
                (3100, 288),
            ]
        ),
        (255, 255, 255),
        "Atravesse o posto industrial e sobreviva às emboscadas.",
        "desert",
        "desert.png",
        ((750, "spikes"), (1500, "mine"), (2180, "spikes"), (2900, "mine")),
    ),
    Stage(
        "03 / FUNDIÇÃO VERMELHA",
        3700,
        23,
        route(
            [
                (340, 240),
                (620, 336),
                (900, 240),
                (1180, 384),
                (1460, 288),
                (1740, 432),
                (2020, 288),
                (2300, 384),
                (2580, 240),
                (2860, 336),
                (3140, 432),
                (3420, 288),
            ]
        ),
        (255, 255, 255),
        "Os lasers avisam antes de disparar. Use o dash.",
        "foundry",
        "foundry.png",
        ((760, "laser"), (1570, "laser"), (2420, "laser"), (3250, "laser")),
    ),
    Stage(
        "04 / CÓDIGO GLACIAL",
        4000,
        28,
        route(
            [
                (340, 240),
                (620, 336),
                (900, 432),
                (1180, 288),
                (1460, 384),
                (1740, 288),
                (2020, 432),
                (2300, 288),
                (2580, 384),
                (2860, 240),
                (3140, 336),
                (3420, 240),
            ]
        ),
        (255, 255, 255),
        "Tempestade, esquadrões e um guardião em duas fases.",
        "snow",
        "snow.png",
        ((780, "mine"), (1540, "spikes"), (2120, "laser"), (3000, "mine")),
    ),
)

# V4 changes composition only; names, enemy counts, economy and objectives are retained.
STAGES = tuple(replace(stage, platforms=LAYOUTS[i]) for i, stage in enumerate(STAGES))


class Weapon:
    def __init__(self, kind="ak"):
        self.kind = kind
        self.spec = WEAPONS[kind]
        self.capacity = self.spec.capacity
        self.ammo = self.capacity
        self.cooldown = 0.0
        self.reloading = 0.0
        self.rate_level = 0

    def update(self, dt):
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.reloading:
            self.reloading = max(0.0, self.reloading - dt)
            if self.reloading == 0:
                self.ammo = self.capacity

    def reload(self):
        if self.ammo < self.capacity and not self.reloading:
            self.reloading = self.spec.reload_time
            return True
        return False

    def fire(self):
        if self.cooldown > 0 or self.reloading or self.ammo == 0:
            return False
        self.ammo -= 1
        self.cooldown = self.spec.interval / (1 + 0.13 * self.rate_level)
        return True


class Campaign:
    def __init__(self):
        self.stage = 0
        self.health = 5
        self.score = 0
        self.time = 0.0
        self.invulnerable = 0.0
        self.finished = False
        self.wallet = 16
        self.weapons = {"ak": Weapon()}
        self.equipped = "ak"
        self.knives = 0
        self.damage_level = 0
        self.rate_level = 0
        self.knife_cooldown = 0.0
        self.dash_time = 0.0
        self.dash_cooldown = 0.0

    @property
    def weapon(self):
        return self.weapons[self.equipped]

    def update(self, dt):
        self.time += dt
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.knife_cooldown = max(0.0, self.knife_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.dash_time = max(0.0, self.dash_time - dt)

    def damage(self):
        if self.health <= 0 or self.invulnerable:
            return False
        self.health = max(0, self.health - 1)
        self.invulnerable = 0.75
        self.score = max(0, self.score - 1)
        return True

    def dash(self):
        if self.dash_cooldown:
            return False
        self.dash_time = 0.16
        self.dash_cooldown = 1.8
        self.invulnerable = max(self.invulnerable, 0.16)
        return True

    def throw_knife(self):
        if not self.knives or self.knife_cooldown:
            return False
        self.knives -= 1
        self.knife_cooldown = 0.45
        return True

    def equip(self, kind):
        if kind not in self.weapons:
            return False
        self.equipped = kind
        return True

    def price(self, item):
        if item in WEAPONS:
            return WEAPONS[item].price
        return {
            "knives": 8,
            "heal": 16,
            "damage": 24 + self.damage_level * 14,
            "rate": 22 + self.rate_level * 15,
        }.get(item, 0)

    def buy(self, item):
        if item in WEAPONS and item in self.weapons:
            return False, "Arma já adquirida. Use 1–4 para equipar."
        if item not in WEAPONS and item not in ("knives", "heal", "damage", "rate"):
            return False, "Item indisponível."
        if item == "heal" and self.health == 5:
            return False, "Vida já está completa."
        if item == "damage" and self.damage_level >= 3:
            return False, "Dano no nível máximo."
        if item == "rate" and self.rate_level >= 2:
            return False, "Cadência no nível máximo."
        if item == "knives" and self.knives > 25:
            return False, "Limite de 30 facas."
        price = self.price(item)
        if self.wallet < price:
            return False, "Créditos insuficientes."
        self.wallet -= price
        if item in WEAPONS:
            self.weapons[item] = Weapon(item)
            self.equipped = item
        elif item == "knives":
            self.knives += 5
        elif item == "heal":
            self.health = min(5, self.health + 2)
        elif item == "damage":
            self.damage_level += 1
        elif item == "rate":
            self.rate_level += 1
        for gun in self.weapons.values():
            gun.rate_level = self.rate_level
        return True, "Compra concluída."

    def advance(self):
        if self.finished:
            return False
        if self.stage == len(STAGES) - 1:
            self.finished = True
            return False
        self.stage += 1
        self.health = min(5, self.health + 1)
        return True
