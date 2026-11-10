import os

os.environ["ARCADE_HEADLESS"] = "1"
os.environ["ALSOFT_DRIVERS"] = "null"
import arcade
import pytest
from game import GameWindow, TelaJogo, TelaMenu, TelaRanking, TelaGameOver
from actors import banco, Pontuacao


@pytest.fixture(scope="module")
def window():
    w = GameWindow(visible=False)
    w.audio.muted = True
    yield w
    w.close()


def test_real_render_and_physics(window):
    v = TelaJogo()
    window.show_view(v)
    for _ in range(120):
        v.on_update(1 / 60)
    assert v.physics_engine.can_jump()
    v.on_key_press(arcade.key.SPACE, 0)
    first = v.player.change_y
    v.on_update(1 / 60)
    v.on_key_press(arcade.key.SPACE, 0)
    assert v.player.change_y < first
    v.on_draw()


def test_combat_damages_enemy_and_blocks_bullets(window):
    v = TelaJogo()
    window.show_view(v)
    v.enemies.clear()
    from game import Enemy

    enemy = Enemy(250, 130, "guard", 0, 200, 300)
    v.enemies.append(enemy)
    v.player.position = (130, 131)
    v.firing = True
    for _ in range(100):
        v.on_update(1 / 60)
    assert enemy.hp <= 0
    assert len(v.enemies) == 0
    assert v.run.score >= 3


def test_all_stages_transition_and_victory(window):
    v = TelaJogo()
    window.show_view(v)
    for stage in range(4):
        assert v.run.stage == stage
        v.coins.clear()
        if v.boss:
            v.boss.hp = 0
            v.boss.remove_from_sprite_lists()
        v.player.position = (v.stage.length - 90, 150)
        v.on_update(1 / 60)
        assert v.transition > 0
        for _ in range(90):
            v.on_update(1 / 60)
        from game import TelaLoja

        if isinstance(window.current_view, TelaLoja):
            window.current_view.resume()
    assert isinstance(window.current_view, TelaGameOver)
    assert window.current_view.victory


def test_text_save_once_and_ranking_snapshot(window, tmp_path):
    original = banco.database
    banco.close()
    banco.init(str(tmp_path / "ranking.db"))
    banco.connect()
    banco.create_tables([Pontuacao])
    try:
        v = TelaGameOver(123, 9.5)
        window.show_view(v)
        v.on_key_press(arcade.key.ENTER, 0)
        assert Pontuacao.select().count() == 0
        v.on_text("Vitor")
        v.on_key_press(arcade.key.ENTER, 0)
        v.on_key_press(arcade.key.ENTER, 0)
        assert Pontuacao.select().count() == 1
        for i in range(15):
            Pontuacao.create(nome_jogador=str(i), pontos=i, tempo_partida=10)
        rank = TelaRanking()
        window.show_view(rank)
        assert len(rank.melhores) == 10 and rank.melhores[0].pontos == 123
        banco.close()
        # Drawing the snapshot must never query the database.
        rank.on_draw()
        assert banco.is_closed()
    finally:
        if not banco.is_closed():
            banco.close()
        banco.init(original)


def test_pause_and_focus_clear_held_input(window):
    v = TelaJogo()
    window.show_view(v)
    v.on_key_press(arcade.key.D, 0)
    v.firing = True
    window.on_deactivate()
    assert v.paused and not v.held and not v.firing
    before = v.run.time
    v.on_update(0.2)
    assert v.run.time == before


def test_ground_pickups_never_inside_low_overhang(window):
    from campaign import Campaign

    for level in range(4):
        run = Campaign()
        run.stage = level
        v = TelaJogo(run)
        window.show_view(v)
        for coin in v.coins:
            if coin.base_y != 128:
                continue
            for block in v.blocks:
                if 96 < block.top < 200:
                    assert not (block.left - 30 < coin.center_x < block.right + 30)


def test_mixed_fire_inputs_do_not_cancel_each_other(window):
    v = TelaJogo()
    window.show_view(v)
    v.on_key_press(arcade.key.J, 0)
    v.on_mouse_press(0, 0, arcade.MOUSE_BUTTON_LEFT, 0)
    v.on_key_release(arcade.key.J, 0)
    assert v.firing
    v.on_key_press(arcade.key.X, 0)
    v.on_mouse_release(0, 0, arcade.MOUSE_BUTTON_LEFT, 0)
    assert v.firing
    v.on_key_release(arcade.key.X, 0)
    assert not v.firing


def test_fixed_step_is_independent_of_frame_rate(window):
    positions = []
    for rate in (30, 60, 120):
        v = TelaJogo()
        window.show_view(v)
        v.enemies.clear()
        v.on_key_press(arcade.key.D, 0)
        for _ in range(rate):
            v.on_update(1 / rate)
        positions.append(v.player.position)
    assert positions[0] == positions[1] == positions[2]


def test_animation_priority_and_timing(window):
    from actors import Jogador

    p = Jogador()
    p.change_x = -4
    p.change_y = 2
    p.update(0.2)
    assert p.texture == p.textura_pulo_esquerda
    p.change_y = 0
    p.change_x = 0
    p.update(0.2)
    assert p.texture == p.textura_idle_esquerda
    p.change_x = 4
    p.update(0.099)
    assert p.frame_atual == 0
    p.update(0.0011)
    assert p.frame_atual == 1 and p.virado_para == 1


def test_mouse_menu_hover_and_delayed_shot_selection(window):
    from game import TelaLoja

    v = TelaMenu()
    window.show_view(v)
    b = next(b for b in v.ui.buttons if b.id == "play")
    x, y, w, h = b.box
    v.on_mouse_motion(x + 20, y + 20, 0, 0)
    v.on_update(0.1)
    assert b.hover > 0
    v.on_mouse_press(x + 20, y + 20, arcade.MOUSE_BUTTON_LEFT, 0)
    assert v.ui.shot and window.current_view is v
    for _ in range(20):
        v.on_update(1 / 60)
    assert isinstance(window.current_view, TelaLoja)


def test_mouse_aim_is_world_relative_and_knife_spends_stock(window):
    v = TelaJogo()
    window.show_view(v)
    v.player.position = (1600, 300)
    v.on_mouse_motion(500, 500, 0, 0)
    v.fire()
    bullet = list(v.bullets)[-1]
    assert bullet.change_y > 0
    assert bullet.change_x > 0
    v.run.wallet = 50
    v.run.buy("knives")
    v.on_key_press(arcade.key.T, 0)
    assert v.run.knives == 4
    assert any(b.knife for b in v.bullets)


def test_shop_freezes_game_and_preserves_inventory(window):
    from game import TelaLoja

    v = TelaJogo()
    window.show_view(v)
    v.run.wallet = 100
    v.held.add(arcade.key.D)
    v.firing = True
    v.open_shop()
    shop = window.current_view
    assert isinstance(shop, TelaLoja) and not v.held and not v.firing
    clock = v.run.time
    shop.purchase("shotgun")
    shop.on_update(0.1)
    assert v.run.time == clock and v.run.equipped == "shotgun"
    shop.resume()
    assert window.current_view is v and v.weapon.kind == "shotgun"


def test_hazards_warn_before_activation_and_mines_explode_once(window):
    from world_fx import Hazard

    v = TelaJogo()
    window.show_view(v)
    laser = Hazard(760, "laser")
    laser.tick(0.01, 2.4 - 0.76, v.player)
    assert laser.warning and not laser.active
    laser.tick(0.01, 3.2 - 0.76, v.player)
    assert laser.active and not laser.warning
    mine = Hazard(100, "mine")
    v.player.position = (100, 130)
    assert not mine.tick(0.3, 1, v.player)
    assert not mine.tick(0.3, 1.3, v.player)
    assert mine.tick(0.3, 1.6, v.player)
    assert not mine.tick(1, 2.6, v.player)


def test_piercing_damages_each_target_only_once(window):
    from game import Bullet, Enemy

    v = TelaJogo()
    window.show_view(v)
    v.enemies.clear()
    enemy = Enemy(220, 140, "boss", 0)
    v.enemies.append(enemy)
    v.bullets.append(Bullet(220, 140, 0, 0, damage=4, pierce=2))
    hp = enemy.hp
    for _ in range(12):
        v.on_update(1 / 60)
    assert enemy.hp == hp - 4


def test_authored_platforms_can_be_reached_with_real_physics(window):
    from campaign import Campaign, STAGES

    for level, stage in enumerate(STAGES):
        run = Campaign()
        run.stage = level
        v = TelaJogo(run)
        window.show_view(v)
        v.enemies.clear()
        v.hazards.clear()
        v.barrels.clear()
        previous_right = 150
        previous_top = 96
        for x, y, width in stage.platforms:
            v.player.center_x = previous_right - 28
            v.player.bottom = previous_top
            v.player.velocity = (0, 0)
            v.clear_input()
            for _ in range(12):
                v.on_update(1 / 60)
            assert v.physics_engine.can_jump(), (level, x, "takeoff")
            v.on_key_press(arcade.key.SPACE, 0)
            for _ in range(130):
                if v.player.center_x < x - 3:
                    v.held.add(arcade.key.D)
                else:
                    v.held.discard(arcade.key.D)
                v.on_update(1 / 60)
                if abs(v.player.center_x - x) < 8 and v.physics_engine.can_jump():
                    break
            assert abs(v.player.center_x - x) < 8 and abs(v.player.bottom - y) < 12, (
                level,
                x,
                y,
                v.player.position,
            )
            previous_right = x + width / 2
            previous_top = y


def test_pause_menu_click_animates_without_advancing_game(window):
    v = TelaJogo()
    window.show_view(v)
    v.on_key_press(arcade.key.P, 0)
    clock = v.run.time
    v.on_mouse_motion(400, 305, 0, 0)
    v.on_mouse_press(400, 305, arcade.MOUSE_BUTTON_LEFT, 0)
    assert v.pause_ui.shot
    for _ in range(20):
        v.on_update(1 / 60)
    assert not v.paused and v.run.time >= clock
