from campaign import Campaign, Weapon, WEAPONS


def test_shop_spends_wallet_not_score_and_rejects_duplicate():
    run = Campaign()
    run.wallet = 100
    run.score = 80
    assert run.buy("smg")[0]
    assert run.wallet == 100 - WEAPONS["smg"].price and run.score == 80
    previous = run.wallet
    assert not run.buy("smg")[0] and run.wallet == previous
    assert run.equipped == "smg"


def test_insufficient_and_full_health_purchase_are_atomic():
    run = Campaign()
    run.wallet = 0
    assert not run.buy("knives")[0] and run.knives == 0
    run.wallet = 100
    assert not run.buy("heal")[0] and run.wallet == 100
    run.health = 3
    assert run.buy("heal")[0] and run.health == 5


def test_knife_stock_and_cooldown():
    run = Campaign()
    run.wallet = 50
    assert not run.throw_knife()
    assert run.buy("knives")[0]
    assert run.knives == 5 and run.throw_knife() and run.knives == 4
    assert not run.throw_knife()
    run.update(0.6)
    assert run.throw_knife() and run.knives == 3


def test_weapon_profiles_and_upgrades_are_real_and_capped():
    assert WEAPONS["shotgun"].pellets == 5
    assert WEAPONS["rifle"].damage > WEAPONS["ak"].damage
    assert WEAPONS["smg"].interval < WEAPONS["ak"].interval
    run = Campaign()
    run.wallet = 1000
    for _ in range(3):
        assert run.buy("damage")[0]
    previous = run.wallet
    assert not run.buy("damage")[0] and run.wallet == previous
    assert run.damage_level == 3


def test_inventory_and_wallet_survive_stage_transition():
    run = Campaign()
    run.wallet = 100
    run.buy("shotgun")
    run.buy("knives")
    gun = run.weapons["shotgun"]
    gun.fire()
    run.advance()
    assert run.weapons["shotgun"] is gun and run.equipped == "shotgun"
    assert run.knives == 5
