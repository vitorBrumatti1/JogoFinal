import os

os.environ["ARCADE_HEADLESS"] = "1"
os.environ["ALSOFT_DRIVERS"] = "null"
import arcade
import pytest
from game import GameWindow, TelaJogo, Enemy


@pytest.fixture(scope="module")
def window():
    w = GameWindow(visible=False)
    w.audio.muted = True
    yield w
    w.close()


def test_guard_cannot_shoot_backwards_and_has_slow_cadence(window):
    v = TelaJogo()
    window.show_view(v)
    v.enemies.clear()
    v.barrels.clear()
    # Isolate orientation from the new authored cover at x500.
    v.ballistic.clear()
    e = Enemy(520, 130, "guard", 0, 100, 1000)
    e.direction = 1
    e.shot_clock = 0
    v.enemies.append(e)
    v.player.position = (140, 130)
    for _ in range(45):
        v.on_update(1 / 60)
    assert len(v.hostile) == 0
    e.direction = -1
    for _ in range(45):
        v.on_update(1 / 60)
    assert len(v.hostile) == 1
    assert e.shot_clock > 2
    assert max(abs(b.change_x) for b in v.hostile) <= 4


def test_drone_drops_grenades_instead_of_bullets(window):
    v = TelaJogo()
    window.show_view(v)
    v.enemies.clear()
    v.barrels.clear()
    e = Enemy(180, 410, "drone", 0)
    e.shot_clock = 0
    v.enemies.append(e)
    v.player.position = (140, 130)
    for _ in range(60):
        v.on_update(1 / 60)
    assert len(v.hostile) == 0
    assert len(v.grenades) == 1
    g = v.grenades[0]
    assert g.center_y < e.center_y and g.fuse > 0


def test_grenade_lands_warns_and_explodes_only_once(window):
    from combat import Grenade

    v = TelaJogo()
    window.show_view(v)
    g = Grenade(160, 220)
    for _ in range(120):
        if g.grounded:
            break
        assert not g.tick(1 / 60, v.blocks)
    assert g.grounded and g.bottom >= 95 and g.fuse >= 0.8
    explosions = 0
    for _ in range(150):
        explosions += int(g.tick(1 / 60, v.blocks))
    assert explosions == 1


def test_enemy_wont_shoot_through_cover(window):
    # V4: support platforms are transparent to bullets; cover is explicit.
    from combat import Cover

    v = TelaJogo()
    window.show_view(v)
    v.ballistic.append(Cover(270, 96))
    e = Enemy(170, 130, "guard", 0, 100, 240)
    e.direction = 1
    v.player.position = (470, 130)
    assert not e.can_aim(v.player, v.ballistic)


def test_menu_has_reference_structure_and_real_options(window):
    from game import TelaMenu, TelaOpcoes

    m = TelaMenu()
    window.show_view(m)
    assert [b.id for b in m.ui.buttons] == ["play", "shop", "options", "about", "exit"]
    m.ui.trigger("options")
    for _ in range(20):
        m.on_update(1 / 60)
    assert isinstance(window.current_view, TelaOpcoes)
    options = window.current_view
    old = window.arcade_filter
    options.ui.trigger("crt")
    for _ in range(20):
        options.on_update(1 / 60)
    assert window.arcade_filter != old


def test_all_combat_effects_render_with_live_projectiles(window):
    from game import Bullet
    from combat import Grenade

    v = TelaJogo()
    window.show_view(v)
    v.bullets.append(Bullet(210, 180, 12, 3))
    v.bullets.append(Bullet(280, 200, 10, 0, knife=True))
    v.hostile.append(Bullet(480, 210, -3, 0, True))
    v.grenades.append(Grenade(400, 260))
    v.muzzle = 0.05
    v.impact(360, 190)
    v.impact(540, 190, True)
    v.on_draw()
    assert arcade.get_image().size == (960, 640)
