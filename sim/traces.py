# voices/sim/traces.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sim.voices import clamp

TRACE_TYPES = [
    "habit", "threshold", "scar", "self_narrative",
    "debt", "attachment", "project", "ritual",
    "missed_window", "reputation",
]

HABIT_THRESHOLD = 5
THRESHOLD_WINDOW = 20
THRESHOLD_TRIGGER = 3
SCAR_MIN_STRENGTH = 0.6
RITUAL_MIN_STRENGTH = 0.5


@dataclass
class Trace:
    id: str
    type: str
    key: str
    strength: float
    created_at: int
    updated_at: int
    active: bool
    payload: dict


@dataclass
class Traces:
    items: Dict[str, Trace] = field(default_factory=dict)
    repeat_counts: Dict[str, int] = field(default_factory=dict)
    threshold_window: Dict[str, List[int]] = field(default_factory=dict)


def make_id(trace_type: str, key: str) -> str:
    return f"{trace_type}:{key}"


def create_traces() -> Traces:
    return Traces()


def get(traces: Traces, trace_type: str, key: str) -> Optional[Trace]:
    return traces.items.get(make_id(trace_type, key))


def upsert(
    traces: Traces,
    trace_type: str,
    key: str,
    tick: int,
    strength_delta: float = 0.1,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id(trace_type, key)
    existing = traces.items.get(tid)
    if existing is None:
        strength = clamp(strength_delta)
        trace = Trace(
            id=tid,
            type=trace_type,
            key=key,
            strength=strength,
            created_at=tick,
            updated_at=tick,
            active=True,
            payload=dict(payload) if payload else {},
        )
        traces.items[tid] = trace
        return trace
    existing.strength = clamp(existing.strength + strength_delta)
    existing.updated_at = tick
    if payload:
        existing.payload.update(payload)
    return existing


def deactivate(traces: Traces, trace_type: str, key: str) -> None:
    tid = make_id(trace_type, key)
    trace = traces.items.get(tid)
    if trace is not None:
        trace.active = False


def register_repeat(
    traces: Traces,
    action_id: str,
    tick: int,
    habit_threshold: int = HABIT_THRESHOLD,
) -> Optional[Trace]:
    cnt_key = f"habit:{action_id}"
    count = traces.repeat_counts.get(cnt_key, 0) + 1
    traces.repeat_counts[cnt_key] = count

    existing = get(traces, "habit", action_id)
    if existing is None:
        if count >= habit_threshold:
            return upsert(
                traces,
                "habit",
                action_id,
                tick,
                strength_delta=0.3,
                payload={"action_id": action_id, "count": count},
            )
        return None
    return upsert(
        traces,
        "habit",
        action_id,
        tick,
        strength_delta=0.1,
        payload={"count": count},
    )


def register_threshold(
    traces: Traces,
    key: str,
    tick: int,
    window: int = THRESHOLD_WINDOW,
    trigger: int = THRESHOLD_TRIGGER,
) -> Optional[Trace]:
    wkey = f"threshold:{key}"
    lst = traces.threshold_window.setdefault(wkey, [])
    lst.append(tick)
    cutoff = tick - window
    traces.threshold_window[wkey] = [x for x in lst if x >= cutoff]
    lst = traces.threshold_window[wkey]

    existing = get(traces, "threshold", key)
    if existing is not None:
        upsert(
            traces,
            "threshold",
            key,
            tick,
            strength_delta=0.1,
            payload={"events": list(lst)},
        )
        return None
    if len(lst) >= trigger:
        return upsert(
            traces,
            "threshold",
            key,
            tick,
            strength_delta=0.4,
            payload={"key": key, "events": list(lst)},
        )
    return None


def create_scar(
    traces: Traces,
    key: str,
    tick: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("scar", key)
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        if payload:
            existing.payload.update(payload)
        return existing
    trace = Trace(
        id=tid,
        type="scar",
        key=key,
        strength=SCAR_MIN_STRENGTH,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=dict(payload) if payload else {},
    )
    traces.items[tid] = trace
    return trace


def create_narrative(
    traces: Traces,
    key: str,
    tick: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("self_narrative", key)
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        existing.strength = clamp(existing.strength + 0.1)
        if payload:
            existing.payload.update(payload)
        return existing
    trace = Trace(
        id=tid,
        type="self_narrative",
        key=key,
        strength=0.5,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=dict(payload) if payload else {},
    )
    traces.items[tid] = trace
    return trace


def create_debt(
    traces: Traces,
    key: str,
    tick: int,
    due_at: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("debt", key)
    p = dict(payload) if payload else {}
    p["due_at"] = due_at
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        existing.payload.update(p)
        return existing
    trace = Trace(
        id=tid,
        type="debt",
        key=key,
        strength=0.5,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=p,
    )
    traces.items[tid] = trace
    return trace


def create_attachment(
    traces: Traces,
    key: str,
    tick: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("attachment", key)
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        if payload:
            existing.payload.update(payload)
        return existing
    trace = Trace(
        id=tid,
        type="attachment",
        key=key,
        strength=0.3,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=dict(payload) if payload else {},
    )
    traces.items[tid] = trace
    return trace


def create_project(
    traces: Traces,
    key: str,
    tick: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("project", key)
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        if payload:
            existing.payload.update(payload)
        return existing
    trace = Trace(
        id=tid,
        type="project",
        key=key,
        strength=0.4,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=dict(payload) if payload else {},
    )
    traces.items[tid] = trace
    return trace


def create_ritual(
    traces: Traces,
    key: str,
    tick: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("ritual", key)
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        if payload:
            existing.payload.update(payload)
        return existing
    trace = Trace(
        id=tid,
        type="ritual",
        key=key,
        strength=RITUAL_MIN_STRENGTH,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=dict(payload) if payload else {},
    )
    traces.items[tid] = trace
    return trace


def register_missed_window(
    traces: Traces,
    window_id: str,
    tick: int,
    payload: Optional[dict] = None,
) -> Trace:
    tid = make_id("missed_window", window_id)
    existing = traces.items.get(tid)
    if existing is not None:
        existing.updated_at = tick
        existing.strength = clamp(existing.strength + 0.1)
        if payload:
            existing.payload.update(payload)
        return existing
    trace = Trace(
        id=tid,
        type="missed_window",
        key=window_id,
        strength=0.2,
        created_at=tick,
        updated_at=tick,
        active=True,
        payload=dict(payload) if payload else {},
    )
    traces.items[tid] = trace
    return trace


def register_reputation(
    traces: Traces,
    key: str,
    tick: int,
    delta: float,
    payload: Optional[dict] = None,
) -> Trace:
    return upsert(
        traces,
        "reputation",
        key,
        tick,
        strength_delta=delta,
        payload=payload,
    )


def decay_all(traces: Traces, rate: float = 0.01) -> None:
    for trace in traces.items.values():
        if not trace.active:
            continue
        if trace.type in ("scar", "self_narrative"):
            continue
        trace.strength = clamp(trace.strength - rate)
        if trace.strength <= 0.0:
            trace.active = False


def active_traces(traces: Traces) -> List[Trace]:
    return [t for t in traces.items.values() if t.active]


def by_type(traces: Traces, trace_type: str) -> List[Trace]:
    return [t for t in traces.items.values() if t.type == trace_type]


def has_habit(traces: Traces, action_id: str) -> bool:
    for trace in traces.items.values():
        if (
            trace.type == "habit"
            and trace.active
            and trace.payload.get("action_id") == action_id
        ):
            return True
    return False


def habit_strength(traces: Traces, action_id: str) -> float:
    for trace in traces.items.values():
        if (
            trace.type == "habit"
            and trace.active
            and trace.payload.get("action_id") == action_id
        ):
            return trace.strength
    return 0.0


def snapshot(traces: Traces) -> List[dict]:
    result = []
    for trace in traces.items.values():
        if not trace.active:
            continue
        result.append(
            {
                "id": trace.id,
                "type": trace.type,
                "key": trace.key,
                "strength": trace.strength,
                "created_at": trace.created_at,
                "updated_at": trace.updated_at,
                "active": trace.active,
                "payload": dict(trace.payload),
            }
        )
    return result
