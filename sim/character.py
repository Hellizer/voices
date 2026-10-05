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

SELF_NAME_TEMPLATES = {
    "male": {
        "body": "тот, кто слушает тело",
        "safety": "тот, кто бережёт себя",
        "connection": "тот, кто рядом",
        "recognition": "тот, кого видно",
        "interest": "тот, кто ищет",
        "control": "тот, кто держит",
    },
    "female": {
        "body": "та, кто слушает тело",
        "safety": "та, кто бережёт себя",
        "connection": "та, кто рядом",
        "recognition": "та, кого видно",
        "interest": "та, кто ищет",
        "control": "та, кто держит",
    },
}


def derive_self_name(gender: str, chosen_voice: str) -> str:
    table = SELF_NAME_TEMPLATES.get(gender) or SELF_NAME_TEMPLATES["female"]
    return table.get(chosen_voice, "")


@dataclass
class Character:
    id: str = "default"
    name: str = ""
    gender: str = "female"
    self_name: str = ""
    tick: int = 0
    voices: Dict[str, Voice] = field(default_factory=dict)
    traces: Traces = field(default_factory=create_traces)
    journal: Journal = field(default_factory=create_journal)
    influence: MemoryInfluence = field(default_factory=create_influence)
    player: PlayerState = field(default_factory=create_player)
    temperature: float = 0.4
    choice_delta: float = 0.08
    resources: Dict[str, float] = field(
        default_factory=lambda: {"energy": 0.7, "money": 0.5, "social": 0.5}
    )
    cooldowns: Dict[str, int] = field(default_factory=dict)
    location: str = "home"


def create_character(
    character_id: str = "default",
    temperature: float = 0.4,
    choice_delta: float = 0.08,
) -> Character:
    return Character(
        id=character_id,
        name="",
        gender="female",
        self_name="",
        tick=0,
        voices=create_voices(),
        traces=create_traces(),
        journal=create_journal(),
        influence=create_influence(),
        player=create_player(),
        temperature=temperature,
        choice_delta=choice_delta,
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
        "choice_delta": character.choice_delta,
    }


def sync_from_state(character: Character, state: dict) -> None:
    character.resources = state.get("resources", character.resources)
    character.cooldowns = state.get("cooldowns", character.cooldowns)
    character.location = state.get("location", character.location)


def snapshot(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "gender": character.gender,
        "self_name": character.self_name,
        "tick": character.tick,
        "temperature": character.temperature,
        "choice_delta": character.choice_delta,
        "location": character.location,
        "resources": dict(character.resources),
        "cooldowns": dict(character.cooldowns),
        "voices": voices_snapshot(character.voices),
        "traces": traces_snapshot(character.traces),
        "journal": journal_snapshot(character.journal),
        "player": player_snapshot(character.player),
    }
