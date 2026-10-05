import random

from sim.character import create_character
from sim.world import create_world
from sim.loop import simulation_tick


def test_simulation_tick_increments_tick():
    character = create_character("t")
    world = create_world(0)
    assert character.tick == 0
    result = simulation_tick(character, world)
    assert character.tick == 1
    assert result.tick == 1


def test_simulation_50_ticks_no_crash():
    random.seed(42)
    character = create_character("t")
    world = create_world(0)
    for _ in range(50):
        result = simulation_tick(character, world)
        assert result is not None
    assert character.tick == 50


def test_simulation_multiple_actions():
    random.seed(42)
    character = create_character("t")
    world = create_world(0)
    actions = set()
    for _ in range(100):
        result = simulation_tick(character, world)
        actions.add(result.action_id)
    assert len(actions) >= 3
