# voices/sim/mutate.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sim.voices import Voice, clamp, top_voices, snapshot, DEFAULT_BASELINE
from sim.traces import (
    Traces,
    create_scar,
    create_narrative,
    register_threshold,
    by_type,
    get,
)

CRISIS_THRESHOLD = 0.20
NARRATIVE_SHIFT_THRESHOLD = 0.5

CONFLICT_PAIRS = [
    ("safety", "interest"),
    ("safety", "recognition"),
    ("connection", "control"),
    ("recognition", "control"),
    ("body", "control"),
    ("interest", "control"),
    ("recognition", "connection"),
    ("interest", "connection"),
    ("safety", "body"),
]


@dataclass
class Crisis:
    voices: Tuple[str, str]
    severity: float
    tick: int


@dataclass
class Mutation:
    kind: str
    key: str
    payload: dict


def conflict(top_pair: Tuple[str, str]) -> bool:
    a, b = top_pair
    for x, y in CONFLICT_PAIRS:
        if (a == x and b == y) or (a == y and b == x):
            return True
    return False


def both_above(voices: Dict[str, Voice], pair: Tuple[str, str], threshold: float = CRISIS_THRESHOLD) -> bool:
    a, b = pair
    va = voices.get(a)
    vb = voices.get(b)
    if va is None or vb is None:
        return False
    return va.weight >= threshold and vb.weight >= threshold


def check_crisis(voices: Dict[str, Voice], traces: Traces, tick: int) -> Optional[Crisis]:
    best: Optional[Crisis] = None
    for a, b in CONFLICT_PAIRS:
        va = voices.get(a)
        vb = voices.get(b)
        if va is None or vb is None:
            continue
        if va.weight < CRISIS_THRESHOLD or vb.weight < CRISIS_THRESHOLD:
            continue
        if get(traces, "scar", f"crisis:{a}_vs_{b}") is not None:
            continue
        severity = (va.weight + vb.weight) / 2.0
        if best is None or severity > best.severity:
            best = Crisis(voices=(a, b), severity=severity, tick=tick)
    return best


def narrative_shift_needed(voices: Dict[str, Voice], baseline: Dict[str, float]) -> bool:
    total = 0.0
    for name, v in voices.items():
        base = baseline.get(name)
        if base is None:
            continue
        total += abs(v.weight - base)
    return total > NARRATIVE_SHIFT_THRESHOLD


def resolve(voices: Dict[str, Voice], crisis: Crisis) -> str:
    a, b = crisis.voices
    wa = voices[a].weight if a in voices else 0.0
    wb = voices[b].weight if b in voices else 0.0
    if wa >= wb:
        return a
    return b


def apply_crisis(voices: Dict[str, Voice], traces: Traces, crisis: Crisis) -> Mutation:
    chosen = resolve(voices, crisis)
    a, b = crisis.voices
    loser = b if chosen == a else a

    create_scar(
        traces,
        f"crisis:{crisis.voices[0]}_vs_{crisis.voices[1]}",
        crisis.tick,
        payload={"chosen": chosen, "severity": crisis.severity},
    )
    create_narrative(
        traces,
        f"after:{chosen}",
        crisis.tick,
        payload={"chosen": chosen, "severity": crisis.severity},
    )

    if chosen in voices:
        v = voices[chosen]
        v.baseline = clamp(v.baseline + 0.05)
    if loser in voices:
        v = voices[loser]
        v.baseline = clamp(v.baseline - 0.05)

    return Mutation(
        kind="crisis",
        key=f"{crisis.voices[0]}_vs_{crisis.voices[1]}",
        payload={"chosen": chosen, "severity": crisis.severity},
    )


def check_thresholds(traces: Traces, voices: Dict[str, Voice], tick: int) -> List[Mutation]:
    mutations: List[Mutation] = []

    for name, v in voices.items():
        if v.weight >= CRISIS_THRESHOLD:
            trace = register_threshold(traces, f"voice_high:{name}", tick)
            if trace is not None:
                mutations.append(
                    Mutation(kind="threshold", key=f"voice_high:{name}", payload={})
                )
        if v.weight <= 0.02:
            trace = register_threshold(traces, f"voice_low:{name}", tick)
            if trace is not None:
                mutations.append(
                    Mutation(kind="threshold", key=f"voice_low:{name}", payload={})
                )

    if narrative_shift_needed(voices, DEFAULT_BASELINE):
        recent_shift = False
        for t in by_type(traces, "self_narrative"):
            if t.active and t.key.startswith("shift:") and tick - t.updated_at <= 20:
                recent_shift = True
                break
        if not recent_shift:
            create_narrative(
                traces,
                f"shift:{tick}",
                tick,
                payload={"voices": snapshot(voices)},
            )
            mutations.append(
                Mutation(kind="narrative_shift", key=f"shift:{tick}", payload={})
            )

    return mutations


def apply_mutation(voices: Dict[str, Voice], traces: Traces, mutation: Mutation) -> None:
    if mutation.kind == "crisis":
        return
    if mutation.kind == "threshold":
        if mutation.key.startswith("voice_high:"):
            name = mutation.key[len("voice_high:"):]
            v = voices.get(name)
            if v is not None:
                v.weight = clamp(v.weight + 0.03)
        elif mutation.key.startswith("voice_low:"):
            name = mutation.key[len("voice_low:"):]
            v = voices.get(name)
            if v is not None:
                v.weight = clamp(v.weight - 0.03)
        return
    if mutation.kind == "narrative_shift":
        return
    if mutation.kind == "scar_decay":
        pass
    return


def snapshot_mutation(mutation: Mutation) -> dict:
    return {
        "kind": mutation.kind,
        "key": mutation.key,
        "payload": dict(mutation.payload),
    }
