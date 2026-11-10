"""Composição autoral sobre os quatro setores e corredores seguros de patrulha."""

# Widths are multiples of 48; max ascent144, gaps chosen for the retained jump.
LAYOUTS = (
    (
        (340, 192, 192),
        (610, 240, 144),
        (890, 192, 240),
        (1170, 288, 192),
        (1420, 384, 144),
        (1680, 288, 240),
        (2000, 192, 240),
        (2280, 240, 192),
        (2580, 192, 240),
    ),
    (
        (320, 192, 144),
        (600, 288, 192),
        (900, 384, 144),
        (1180, 240, 240),
        (1460, 336, 192),
        (1740, 288, 144),
        (2000, 384, 240),
        (2300, 240, 192),
        (2580, 336, 144),
        (2840, 384, 240),
        (3100, 288, 192),
    ),
    (
        (340, 240, 192),
        (640, 336, 240),
        (930, 240, 144),
        (1200, 384, 192),
        (1480, 288, 240),
        (1780, 432, 192),
        (2050, 288, 144),
        (2320, 384, 240),
        (2600, 240, 192),
        (2880, 336, 144),
        (3160, 432, 240),
        (3440, 288, 192),
    ),
    (
        (340, 240, 240),
        (640, 336, 144),
        (920, 432, 192),
        (1200, 288, 240),
        (1480, 384, 144),
        (1760, 288, 192),
        (2060, 432, 240),
        (2340, 288, 144),
        (2620, 384, 192),
        (2900, 240, 240),
        (3180, 336, 144),
        (3460, 240, 240),
    ),
)
COVER_POSITIONS = (
    (500, 1280, 2130),
    (500, 1390, 2480),
    (500, 1510, 2670),
    (500, 1650, 2800),
)


def ground_lane(stage, x, cover_positions):
    blocked = [
        (px - w / 2 - 4, px + w / 2 + 4) for px, y, w in stage.platforms if y - 48 < 166
    ]
    blocked.extend((cx - 4, cx + 40) for cx in cover_positions)
    free = []
    left = 285
    for a, b in sorted(blocked):
        if a > left and a - left >= 108:
            free.append((left, a))
        left = max(left, b)
    if stage.length - 180 - left >= 108:
        free.append((left, stage.length - 180))
    low, high = min(free, key=lambda p: abs((p[0] + p[1]) / 2 - x))
    center = max(low + 30, min(high - 30, x))
    return center, max(low, center - 95), min(high, center + 95)
