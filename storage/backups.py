# voices/storage/backups.py
import json
from pathlib import Path
from typing import List, Optional, Tuple

from sim.character import Character
from sim.world import World
from storage.repository import backup_to_json, load_backup

STATE_A = "state-a.json"
STATE_B = "state-b.json"


class BackupConfig:
    def __init__(self, backup_dir: str) -> None:
        self.backup_dir = backup_dir


def create_config(backup_dir: str) -> BackupConfig:
    return BackupConfig(backup_dir=backup_dir)


def _state_paths(config: BackupConfig) -> List[Path]:
    base = Path(config.backup_dir)
    return [base / STATE_A, base / STATE_B]


def _pick_target(config: BackupConfig) -> Path:
    paths = _state_paths(config)
    missing = [p for p in paths if not p.exists()]
    if missing:
        return missing[0]
    return min(paths, key=lambda p: p.stat().st_mtime)


def alternate_backup(character: Character, world: World, config: BackupConfig) -> str:
    base = Path(config.backup_dir)
    base.mkdir(parents=True, exist_ok=True)
    target = _pick_target(config)
    tmp = target.with_name(target.name + ".tmp")
    backup_to_json(character, world, str(tmp))
    tmp.replace(target)
    return str(target)


def load_best_backup(config: BackupConfig) -> Optional[Tuple[Character, World]]:
    best: Optional[Tuple[Character, World]] = None
    for path in _state_paths(config):
        if not path.exists():
            continue
        try:
            character, world = load_backup(str(path))
        except (ValueError, OSError, json.JSONDecodeError):
            continue
        if best is None or character.tick > best[0].tick:
            best = (character, world)
    return best


def list_all(config: BackupConfig) -> List[dict]:
    result = []
    for path in _state_paths(config):
        if not path.exists():
            continue
        info = {
            "name": path.name,
            "size": path.stat().st_size,
            "mtime": path.stat().st_mtime,
            "tick": None,
            "created_at": None,
        }
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            info["tick"] = data.get("character", {}).get("tick")
            info["created_at"] = data.get("created_at")
        except Exception:
            pass
        result.append(info)
    return result
