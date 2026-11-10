from campaign import Weapon, Campaign, STAGES


def test_magazine_cooldown_and_reload():
    gun = Weapon()
    assert gun.fire()
    assert not gun.fire()
    for _ in range(29):
        gun.update(0.11)
        assert gun.fire()
    assert gun.ammo == 0
    assert not gun.fire()
    gun.reload()
    gun.update(1)
    assert not gun.fire()
    gun.update(0.5)
    assert gun.ammo == 30 and gun.fire()


def test_progression_and_final_completion():
    run = Campaign()
    for i in range(4):
        assert run.stage == i
        assert run.advance() == (i < 3)
    assert run.finished
    assert not run.advance()
    assert run.stage == 3


def test_damage_has_invulnerability_and_floor():
    run = Campaign()
    assert run.damage()
    assert run.health == 4
    assert not run.damage()
    for _ in range(8):
        run.update(1.1)
        run.damage()
    assert run.health == 0


def test_authored_route_has_reachable_jumps_and_pickups():
    assert len(STAGES) == 4
    for stage in STAGES:
        previous = (100, 96)
        for x, y, width in stage.platforms:
            assert abs(y - previous[1]) <= 160
            assert x - width / 2 - previous[0] < 260
            previous = (x + width / 2, y)
        assert stage.length >= 2800
    assert [s.enemies for s in STAGES] == sorted(s.enemies for s in STAGES)
