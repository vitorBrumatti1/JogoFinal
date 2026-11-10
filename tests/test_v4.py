import os, math

os.environ["ARCADE_HEADLESS"] = "1"
os.environ["ALSOFT_DRIVERS"] = "null"
import arcade, pytest
from game import GameWindow, TelaJogo, Bullet, Enemy, Bloco
from campaign import Weapon


@pytest.fixture(scope="module")
def window():
    w = GameWindow(visible=False)
    w.audio.muted = True
    yield w
    w.close()


def scene(window):
    v = TelaJogo()
    window.show_view(v)
    v.enemies.clear()
    v.barrels.clear()
    v.hazards.clear()
    v.grenades.clear()
    v.player.position = (110, 130)
    v.run.invulnerable = 100
    return v


def test_rounds_cross_support_platforms_but_physics_remains(window):
    v = scene(window)
    b = Bloco(210, 210)
    v.blocks.append(b)
    bullet = Bullet(180, 185, 80, 0)
    v.bullets.append(bullet)
    v.on_update(1 / 60)
    assert bullet in v.bullets and bullet.center_x == 260
    assert b in v.blocks and b not in v.ballistic
    assert isinstance(v.physics_engine, arcade.PhysicsEnginePlatformer)


def test_explicit_cover_stops_friendly_hostile_and_line_of_sight(window):
    from combat import Cover

    v = scene(window)
    v.ballistic.clear()
    cover = Cover(250, 96)
    v.ballistic.append(cover)
    v.blocks.append(cover)
    friendly = Bullet(180, 120, 150, 0)
    hostile = Bullet(350, 120, -150, 0, True)
    v.bullets.append(friendly)
    v.hostile.append(hostile)
    v.on_update(1 / 60)
    assert friendly not in v.bullets and hostile not in v.hostile
    e = Enemy(360, 130, "guard", 0)
    e.direction = -1
    assert not e.can_aim(v.player, v.ballistic)


def test_sweep_orders_thin_targets_and_cover_without_duplicate_damage(window):
    from combat import Cover

    v = scene(window)
    v.ballistic.clear()
    a = Enemy(210, 220, "boss", 0)
    b = Enemy(280, 220, "boss", 0)
    a.width = b.width = 10
    a.speed = b.speed = 0
    v.enemies.extend([b, a])
    cover = Cover(320, 190)
    v.ballistic.append(cover)
    shot = Bullet(140, 220, 280, 0, damage=4, pierce=3)
    v.bullets.append(shot)
    v.on_update(1 / 60)
    assert a.hp == 126 and b.hp == 126 and shot not in v.bullets
    assert len(shot.hit_ids) == 2


def test_sweep_handles_barrel_grenade_and_expiration(window):
    from combat import Grenade
    from world_fx import Barrel

    v = scene(window)
    v.ballistic.clear()
    barrel = Barrel(230, 230)
    v.barrels.append(barrel)
    shot = Bullet(140, 230, 200, 0)
    v.bullets.append(shot)
    v.on_update(1 / 60)
    assert barrel not in v.barrels and shot not in v.bullets
    grenade = Grenade(240, 300)
    v.grenades.append(grenade)
    shot = Bullet(140, 300, 200, 0)
    v.bullets.append(shot)
    v.on_update(1 / 60)
    assert grenade not in v.grenades
    expired = Bullet(140, 230, 0, 0)
    expired.life = 0.001
    v.bullets.append(expired)
    v.on_update(1 / 60)
    assert expired not in v.bullets


@pytest.mark.parametrize("kind", ["ak", "smg", "shotgun", "rifle"])
@pytest.mark.parametrize("angle", [0, 0.8, 2.9, -1.2])
def test_all_guns_share_true_muzzle_and_rotation(window, kind, angle):
    v = scene(window)
    v.player.position = (110, 250)
    v.run.weapons[kind] = Weapon(kind)
    v.run.equipped = kind
    v.mouse_aim = True
    v.on_mouse_motion(
        v.player.center_x + math.cos(angle) * 300,
        v.player.center_y + 3 + math.sin(angle) * 300,
        0,
        0,
    )
    v.fire()
    pose = v.gun_pose()
    assert tuple(v.bullets)[0].origin == pytest.approx(pose.muzzle)
    assert v.last_shot_origin == pytest.approx(pose.muzzle)
    assert len(v.bullets) == v.weapon.spec.pellets


def test_close_cover_between_hand_and_muzzle_cannot_be_skipped(window):
    from combat import Cover

    v = scene(window)
    v.ballistic.clear()
    v.player.position = (150, 150)
    cover = Cover(165, 135)
    cover.width = 5
    v.ballistic.append(cover)
    v.fire()
    v.update_projectiles(1 / 60)
    assert not v.bullets


def test_jump_apex_keeps_airborne_texture(window):
    v = scene(window)
    for _ in range(60):
        v.on_update(1 / 60)
    v.on_key_press(arcade.key.SPACE, 0)
    for _ in range(60):
        v.on_update(1 / 60)
        if v.player.change_y == 0 and not v.physics_engine.can_jump():
            assert v.player.texture == v.player.textura_pulo_direita
            break
    else:
        pytest.fail("apex not reached")


def test_enemy_attack_loop_ignores_support_platforms(window):
    v = scene(window)
    v.ballistic.clear()
    v.player.position = (470, 170)
    e = Enemy(170, 170, "guard", 0, 100, 1000)
    e.direction = 1
    e.shot_clock = 0
    e.speed = 0
    v.enemies.append(e)
    for _ in range(40):
        v.update_enemy_attacks(1 / 60)
    assert len(v.hostile) == 1


def test_ground_patrols_do_not_cross_physical_obstacles(window):
    from campaign import Campaign, STAGES

    for level, stage in enumerate(STAGES):
        run = Campaign()
        run.stage = level
        v = TelaJogo(run)
        window.show_view(v)
        for e in v.enemies:
            if e.kind in ("drone", "boss") or e.center_y > 150:
                continue
            for block in v.blocks:
                if block.top <= 96 or block.bottom >= e.top:
                    continue
                assert e.high <= block.left or e.low >= block.right


def test_shop_owned_weapon_click_equips_without_spending(window):
    from game import TelaLoja

    v = scene(window)
    v.run.wallet = 100
    v.run.buy("smg")
    v.run.equip("ak")
    shop = TelaLoja(v)
    window.show_view(shop)
    before = v.run.wallet
    shop.purchase("smg")
    assert v.run.equipped == "smg" and v.run.wallet == before


def test_projectile_visuals_compact_and_weapon_audio_distinct():
    from weapon_art import TRAILS, FLASH_TIME
    from pathlib import Path
    import hashlib, wave

    for kind in ("ak", "smg", "shotgun", "rifle"):
        assert 8 <= TRAILS[kind] <= 16 and FLASH_TIME[kind] < 0.06
    digests = []
    for kind in ("ak", "smg", "shotgun", "rifle"):
        path = Path(__file__).parents[1] / "assets" / f"shot_{kind}.wav"
        digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
        with wave.open(str(path), "rb") as audio:
            assert (
                audio.getnchannels() == 1
                and audio.getsampwidth() == 2
                and audio.getnframes() > 1000
            )
    assert len(set(digests)) == 4


def test_ranking_indirect_inheritance_and_view_contract(window):
    from game import TelaRanking

    assert issubclass(TelaRanking, arcade.View)


def test_enemy_between_grip_and_muzzle_is_hit(window):
    v = scene(window)
    v.ballistic.clear()
    v.player.position = (150, 250)
    v.run.weapons["rifle"] = Weapon("rifle")
    v.run.equipped = "rifle"
    v.on_mouse_motion(800, 253, 0, 0)
    enemy = Enemy(165, 253, "guard", 0)
    v.enemies.append(enemy)
    v.fire()
    v.update_projectiles(1 / 60)
    assert enemy.hp < enemy.max_hp
