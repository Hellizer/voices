# voices/sim/memory.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sim.voices import Voice, clamp

KIND_TICK = "tick"
KIND_ACTION = "action"
KIND_TRACE = "trace"
KIND_CRISIS = "crisis"
KIND_INTERVENTION = "intervention"
KIND_WORLD = "world"
KIND_PRESENCE = "presence"


@dataclass
class Event:
    tick: int
    kind: str
    payload: dict = field(default_factory=dict)


@dataclass
class Journal:
    events: List[Event] = field(default_factory=list)
    max_events: int = 2000


@dataclass
class MemoryInfluence:
    recent_actions: Dict[str, int] = field(default_factory=dict)
    recent_voices: Dict[str, float] = field(default_factory=dict)
    recent_crises: int = 0
    silence_ticks: int = 0


def create_journal(max_events: int = 2000) -> Journal:
    return Journal(events=[], max_events=max_events)


def log(journal: Journal, tick: int, kind: str, payload: Optional[dict] = None) -> Event:
    event = Event(tick=tick, kind=kind, payload=dict(payload) if payload else {})
    journal.events.append(event)
    while len(journal.events) > journal.max_events:
        journal.events.pop(0)
    return event


def since(journal: Journal, tick: int) -> List[Event]:
    return [e for e in journal.events if e.tick >= tick]


def by_kind(journal: Journal, kind: str) -> List[Event]:
    return [e for e in journal.events if e.kind == kind]


def last_n(journal: Journal, n: int) -> List[Event]:
    if n <= 0:
        return []
    return journal.events[-n:]


def create_influence() -> MemoryInfluence:
    return MemoryInfluence()


def update_influence(
    influence: MemoryInfluence,
    journal: Journal,
    current_tick: int,
    window: int = 20,
) -> None:
    influence.recent_actions = {}
    influence.recent_voices = {}
    influence.recent_crises = 0

    cutoff = current_tick - window
    for event in journal.events:
        if event.tick < cutoff:
            continue
        if event.kind == KIND_ACTION:
            aid = event.payload.get("action_id")
            if aid is not None:
                influence.recent_actions[aid] = influence.recent_actions.get(aid, 0) + 1
        elif event.kind == KIND_CRISIS:
            influence.recent_crises += 1
        elif event.kind == KIND_INTERVENTION:
            target = event.payload.get("target_voice")
            delta = event.payload.get("delta")
            if target is not None and delta is not None:
                influence.recent_voices[target] = (
                    influence.recent_voices.get(target, 0.0) + delta
                )


def register_presence(influence: MemoryInfluence, present: bool) -> None:
    if present:
        influence.silence_ticks = 0
    else:
        influence.silence_ticks += 1


def apply_memory(voices: Dict[str, Voice], influence: MemoryInfluence) -> None:
    for voice_name, delta in influence.recent_voices.items():
        v = voices.get(voice_name)
        if v is not None:
            v.weight = clamp(v.weight + delta * 0.5)


def snapshot(journal: Journal) -> List[dict]:
    return [
        {"tick": e.tick, "kind": e.kind, "payload": dict(e.payload)}
        for e in journal.events
    ]
