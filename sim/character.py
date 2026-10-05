# voices/sim/character.py
from dataclasses import dataclass, field
from typing import Dict

from sim.voices import Voice, create_voices, snapshot as voices_snapshot
from sim.traces import Traces, create_traces, snapshot as traces_snapshot
from sim.memory import (
    Journal,
    MemoryInfluence,
    create_journal,
    create_influence,
    snapshot as journal_snapshot,
)
from sim.player import PlayerState, create_player, snapshot as player_snapshot


@dataclass
class Character:
    id: str = "default"
    tick: int = 0
    voices: Dict[str, Voice] = field(default_factory=dict)
    traces: Traces = field(default_factory=create_traces)
    journal: Journal = field(default_factory=create_journal)
    influence: MemoryInfluence = field(default_factory=create_influence)
    player: PlayerState = field(default_factory=create_player)
    temperature: float = 0.4
    resources: Dict[str, float] = field(
        default_factory=lambda: {"energy": 0.7, "money": 0.5, "social": 0.5}
    )
    cooldowns: Dict[str, int] = field(default_factory=dict)
    location: str = "home"


def create_character(character_id: str = "default", temperature: float = 0.4) -> Character:
    return Character(
        id=character_id,
        tick=0,
        voices=create_voices(),
        traces=create_traces(),
        journal=create_journal(),
        influence=create_influence(),
        player=create_player(),
        temperature=temperature,
        resources={"energy": 0.7, "money": 0.5, "social": 0.5},
        cooldowns={},
        location="home",
    )


def build_state(character: Character) -> dict:
    return {
        "voices": character.voices,
        "traces": character.traces,
        "tick": character.tick,
        "location": character.location,
        "resources": character.resources,
        "cooldowns": character.cooldowns,
        "temperature": character.temperature,
    }


def sync_from_state(character: Character, state: dict) -> None:
    character.resources = state.get("resources", character.resources)
    character.cooldowns = state.get("cooldowns", character.cooldowns)
    character.location = state.get("location", character.location)


def snapshot(character: Character) -> dict:
    return {
        "id": character.id,
        "tick": character.tick,
        "temperature": character.temperature,
        "location": character.location,
        "resources": dict(character.resources),
        "cooldowns": dict(character.cooldowns),
        "voices": voices_snapshot(character.voices),
        "traces": traces_snapshot(character.traces),
        "journal": journal_snapshot(character.journal),
        "player": player_snapshot(character.player),
    }
