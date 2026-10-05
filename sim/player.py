# voices/sim/player.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from sim.voices import Voice, clamp
from sim.traces import Traces, by_type
from sim.memory import (
    Journal,
    MemoryInfluence,
    log,
    KIND_INTERVENTION,
    register_presence as register_presence_memory,
)
from sim.actions import get_action

INTERVENTION_TYPES = ["request", "forbid", "support", "distract", "insist", "leave"]
ENVIRONMENT_TYPES = ["teach", "connect", "value", "open_door", "close_door"]
DEFAULT_INTENSITY = 0.2
OBEDIENCE_BASE = 0.5
OBEDIENCE_VOICE_BONUS = 0.15
OBEDIENCE_NARRATIVE_PENALTY = 0.25
ABSENCE_THRESHOLD = 20


@dataclass
class Intervention:
    type: str
    target: str
    intensity: float


@dataclass
class EnvironmentChange:
    type: str
    payload: dict


@dataclass
class PlayerState:
    interventions: List[dict] = field(default_factory=list)
    obedience_history: List[bool] = field(default_factory=list)
    presence_ticks: int = 0
    absences: int = 0
    last_seen_tick: int = 0
    action_cost_modifiers: Dict[str, float] = field(default_factory=dict)
    voice_bias: Dict[str, float] = field(default_factory=dict)


def create_player() -> PlayerState:
    return PlayerState()


def compute_delta(
    player: PlayerState,
    voices: Dict[str, Voice],
    traces: Traces,
    intervention: Intervention,
) -> Tuple[float, bool]:
    target_voice: Optional[str] = None
    if intervention.target in voices:
        target_voice = intervention.target
    else:
        action = get_action(intervention.target)
        if action is not None and action.satisfies:
            target_voice = next(iter(action.satisfies))

    if target_voice is None:
        return (0.0, False)

    p = OBEDIENCE_BASE

    v = voices.get(target_voice)
    if v is not None and v.weight >= 0.5:
        p += OBEDIENCE_VOICE_BONUS

    for t in by_type(traces, "self_narrative"):
        if not t.active:
            continue
        chosen = t.payload.get("chosen")
        key = t.payload.get("key")
        if chosen == target_voice or key == target_voice or chosen == intervention.target or key == intervention.target:
            p -= OBEDIENCE_NARRATIVE_PENALTY
            break

    last5 = player.obedience_history[-5:]
    if last5:
        true_count = sum(1 for x in last5 if x)
        false_count = len(last5) - true_count
        if true_count > len(last5) / 2:
            p += 0.1
        elif false_count > len(last5) / 2:
            p -= 0.1

    p = clamp(p, 0.0, 1.0)

    obeyed = random.random() < p
    base = intervention.intensity if obeyed else -intervention.intensity * 0.3

    if intervention.type == "request":
        delta = base
    elif intervention.type == "forbid":
        delta = -base
    elif intervention.type == "support":
        delta = base * 1.2
    elif intervention.type == "distract":
        delta = -base
    elif intervention.type == "insist":
        delta = base * 1.5
    elif intervention.type == "leave":
        delta = base
    else:
        delta = 0.0

    return (delta, obeyed)


def apply_intervention(
    player: PlayerState,
    voices: Dict[str, Voice],
    traces: Traces,
    journal: Journal,
    intervention: Intervention,
    tick: int,
) -> dict:
    delta, obeyed = compute_delta(player, voices, traces, intervention)

    target_voice: Optional[str] = None
    if intervention.target in voices:
        target_voice = intervention.target
    else:
        action = get_action(intervention.target)
        if action is not None and action.satisfies:
            target_voice = next(iter(action.satisfies))

    if intervention.type == "leave":
        if "connection" in voices:
            voices["connection"].weight = clamp(voices["connection"].weight - delta * 0.5)
        if "safety" in voices:
            voices["safety"].weight = clamp(voices["safety"].weight + delta * 0.3)
    else:
        if target_voice is not None and target_voice in voices:
            voices[target_voice].weight = clamp(voices[target_voice].weight + delta)
        if intervention.type == "distract":
            if "safety" in voices:
                voices["safety"].weight = clamp(voices["safety"].weight - delta * 0.5)

    if obeyed:
        message_key = "heard"
    elif intervention.intensity > 0.5:
        message_key = "wrong"
    else:
        message_key = "ignored"

    log(
        journal,
        tick,
        KIND_INTERVENTION,
        {
            "type": intervention.type,
            "target": intervention.target,
            "target_voice": target_voice,
            "delta": delta,
            "obeyed": obeyed,
            "message_key": message_key,
        },
    )

    player.interventions.append(
        {
            "tick": tick,
            "type": intervention.type,
            "target": intervention.target,
            "intensity": intervention.intensity,
            "obeyed": obeyed,
        }
    )
    player.obedience_history.append(obeyed)
    while len(player.obedience_history) > 50:
        player.obedience_history.pop(0)
    player.last_seen_tick = tick

    return {
        "obeyed": obeyed,
        "delta": delta,
        "target_voice": target_voice,
        "message_key": message_key,
    }


def apply_environment(
    player: PlayerState,
    voices: Dict[str, Voice],
    env: EnvironmentChange,
    tick: int,
) -> None:
    if env.type == "teach":
        action_id = env.payload.get("action_id")
        if action_id is not None:
            player.action_cost_modifiers[action_id] = (
                player.action_cost_modifiers.get(action_id, 0.0) - 0.05
            )
    elif env.type == "connect":
        pass
    elif env.type == "value":
        voice = env.payload.get("voice")
        delta = env.payload.get("delta")
        if voice is not None and delta is not None:
            player.voice_bias[voice] = player.voice_bias.get(voice, 0.0) + delta
    elif env.type == "open_door":
        pass
    elif env.type == "close_door":
        pass

    player.last_seen_tick = tick


def apply_voice_bias(player: PlayerState, voices: Dict[str, Voice]) -> None:
    for voice_name, delta in player.voice_bias.items():
        v = voices.get(voice_name)
        if v is not None:
            v.weight = clamp(v.weight + delta * 0.1)


def get_action_cost_modifier(player: PlayerState, action_id: str) -> float:
    return player.action_cost_modifiers.get(action_id, 0.0)


def register_presence(
    player: PlayerState,
    voices: Dict[str, Voice],
    tick: int,
    present: bool,
    influence: Optional[MemoryInfluence] = None,
) -> None:
    if present:
        if player.last_seen_tick > 0 and tick - player.last_seen_tick > ABSENCE_THRESHOLD:
            player.absences += 1
            conn = voices.get("connection")
            if conn is not None:
                conn.weight = clamp(conn.weight + 0.05)
            rec = voices.get("recognition")
            if rec is not None:
                rec.weight = clamp(rec.weight + 0.05)
        player.presence_ticks += 1
        player.last_seen_tick = tick
    if influence is not None:
        register_presence_memory(influence, present)


def snapshot(player: PlayerState) -> dict:
    return {
        "presence_ticks": player.presence_ticks,
        "absences": player.absences,
        "last_seen_tick": player.last_seen_tick,
        "voice_bias": dict(player.voice_bias),
        "action_cost_modifiers": dict(player.action_cost_modifiers),
    }
