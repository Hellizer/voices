import json
from pathlib import Path

from sim.character import create_character
from sim.world import create_world
from storage.backups import (
    STATE_A,
    STATE_B,
    alternate_backup,
    create_config,
    list_all,
    load_best_backup,
)
from storage.repository import backup_to_json


def test_alternate_creates_two_files(tmp_path):
    config = create_config(str(tmp_path))
    character = create_character("t")
    world = create_world(0)
    p1 = alternate_backup(character, world, config)
    assert Path(p1).name == STATE_A
    p2 = alternate_backup(character, world, config)
    assert Path(p2).name == STATE_B
    assert (tmp_path / STATE_A).exists()
    assert (tmp_path / STATE_B).exists()


def test_load_best_picks_freshest(tmp_path):
    config = create_config(str(tmp_path))
    character = create_character("t")
    world = create_world(0)
    alternate_backup(character, world, config)
    character.tick = 5
    world.tick = 5
    alternate_backup(character, world, config)
    result = load_best_backup(config)
    assert result is not None
    assert result[0].tick == 5


def test_load_best_handles_corrupt(tmp_path):
    config = create_config(str(tmp_path))
    (tmp_path / STATE_A).write_text("not json", encoding="utf-8")
    character = create_character("t")
    world = create_world(0)
    character.tick = 7
    world.tick = 7
    backup_to_json(character, world, str(tmp_path / STATE_B))
    result = load_best_backup(config)
    assert result is not None
    assert result[0].tick == 7


def test_load_best_empty(tmp_path):
    config = create_config(str(tmp_path))
    assert load_best_backup(config) is None


def test_list_all(tmp_path):
    config = create_config(str(tmp_path))
    character = create_character("t")
    world = create_world(0)
    alternate_backup(character, world, config)
    info = list_all(config)
    assert len(info) == 1
    assert info[0]["name"] == STATE_A
