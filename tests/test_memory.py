from sim.voices import create_voices
from sim.memory import (
    create_journal,
    log,
    since,
    by_kind,
    create_influence,
    update_influence,
    register_presence,
    apply_memory,
    KIND_ACTION,
    KIND_CRISIS,
    KIND_INTERVENTION,
)


def test_log_adds_and_caps():
    journal = create_journal(max_events=3)
    for i in range(5):
        log(journal, i, KIND_ACTION, {"action_id": f"a{i}"})
    assert len(journal.events) == 3
    assert journal.events[0].payload["action_id"] == "a2"
    assert journal.events[-1].payload["action_id"] == "a4"


def test_since_filters_by_tick():
    journal = create_journal()
    for i in range(5):
        log(journal, i, KIND_ACTION)
    result = since(journal, 3)
    assert len(result) == 2
    assert all(e.tick >= 3 for e in result)


def test_by_kind_filters():
    journal = create_journal()
    log(journal, 1, KIND_ACTION)
    log(journal, 2, KIND_CRISIS)
    log(journal, 3, KIND_ACTION)
    actions = by_kind(journal, KIND_ACTION)
    assert len(actions) == 2
    crises = by_kind(journal, KIND_CRISIS)
    assert len(crises) == 1


def test_update_influence_collects():
    journal = create_journal()
    log(journal, 10, KIND_ACTION, {"action_id": "eat"})
    log(journal, 10, KIND_ACTION, {"action_id": "eat"})
    log(journal, 11, KIND_CRISIS, {})
    log(journal, 12, KIND_INTERVENTION, {"target_voice": "body", "delta": 0.3})
    inf = create_influence()
    update_influence(inf, journal, current_tick=12, window=20)
    assert inf.recent_actions.get("eat") == 2
    assert inf.recent_crises == 1
    assert abs(inf.recent_voices.get("body", 0.0) - 0.3) < 1e-9


def test_apply_memory_recent_voices():
    voices = create_voices()
    inf = create_influence()
    inf.recent_voices = {"body": 0.5}
    before = voices["body"].weight
    apply_memory(voices, inf)
    assert voices["body"].weight > before
