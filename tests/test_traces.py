from sim.traces import (
    create_traces,
    upsert,
    get,
    register_repeat,
    register_threshold,
    create_scar,
    create_narrative,
    decay_all,
    has_habit,
    habit_strength,
    snapshot,
    active_traces,
    make_id,
    HABIT_THRESHOLD,
    THRESHOLD_TRIGGER,
)


def test_create_traces_empty():
    traces = create_traces()
    assert traces.items == {}
    assert traces.repeat_counts == {}
    assert traces.threshold_window == {}


def test_upsert_creates_and_increases():
    traces = create_traces()
    t1 = upsert(traces, "habit", "x", tick=1, strength_delta=0.2)
    assert t1.strength == 0.2
    assert get(traces, "habit", "x") is t1
    t2 = upsert(traces, "habit", "x", tick=2, strength_delta=0.3)
    assert t2 is t1
    assert abs(t2.strength - 0.5) < 1e-9
    assert t2.updated_at == 2


def test_register_repeat_creates_habit_after_threshold():
    traces = create_traces()
    result = None
    for i in range(HABIT_THRESHOLD):
        result = register_repeat(traces, "eat", tick=i)
    assert result is not None
    assert result.type == "habit"
    assert result.payload.get("action_id") == "eat"


def test_register_threshold_creates_after_triggers():
    traces = create_traces()
    result = None
    for i in range(THRESHOLD_TRIGGER):
        result = register_threshold(traces, "voice_high:body", tick=i)
    assert result is not None
    assert result.type == "threshold"


def test_create_scar_no_duplicate_keeps_strength():
    traces = create_traces()
    s1 = create_scar(traces, "k", tick=1)
    s2 = create_scar(traces, "k", tick=5, payload={"x": 1})
    assert s1 is s2
    assert s2.updated_at == 5
    assert s2.strength == s1.strength
    assert s2.payload.get("x") == 1


def test_decay_all_skips_scar_and_narrative():
    traces = create_traces()
    habit = upsert(traces, "habit", "h", tick=1, strength_delta=0.5)
    scar = create_scar(traces, "s", tick=1)
    narr = create_narrative(traces, "n", tick=1)
    scar_str = scar.strength
    narr_str = narr.strength
    habit_str = habit.strength
    for _ in range(100):
        decay_all(traces, rate=0.01)
    assert scar.strength == scar_str
    assert narr.strength == narr_str
    assert habit.strength < habit_str


def test_has_habit_and_habit_strength():
    traces = create_traces()
    for i in range(HABIT_THRESHOLD):
        register_repeat(traces, "eat", tick=i)
    assert has_habit(traces, "eat") is True
    assert habit_strength(traces, "eat") > 0.0
    assert has_habit(traces, "sleep") is False
    assert habit_strength(traces, "sleep") == 0.0


def test_snapshot_only_active():
    traces = create_traces()
    t1 = upsert(traces, "habit", "a", tick=1, strength_delta=0.3)
    t2 = upsert(traces, "habit", "b", tick=1, strength_delta=0.3)
    t2.active = False
    snap = snapshot(traces)
    ids = {s["id"] for s in snap}
    assert make_id("habit", "a") in ids
    assert make_id("habit", "b") not in ids
