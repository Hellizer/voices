import random

from sim.voices import create_voices
from sim.traces import create_traces
from sim.memory import create_journal, KIND_INTERVENTION
from sim.player import (
    create_player,
    apply_intervention,
    apply_environment,
    register_presence,
    Intervention,
    EnvironmentChange,
)


def test_create_player_empty():
    p = create_player()
    assert p.interventions == []
    assert p.obedience_history == []
    assert p.presence_ticks == 0
    assert p.absences == 0
    assert p.last_seen_tick == 0
    assert p.action_cost_modifiers == {}
    assert p.voice_bias == {}


def test_apply_intervention_logs_and_history():
    random.seed(42)
    p = create_player()
    voices = create_voices()
    traces = create_traces()
    journal = create_journal()
    intervention = Intervention(type="request", target="body", intensity=0.3)
    result = apply_intervention(p, voices, traces, journal, intervention, tick=5)
    assert "obeyed" in result
    assert "message_key" in result
    assert result["message_key"] in ("heard", "ignored", "wrong")
    assert len(p.obedience_history) == 1
    assert len(p.interventions) == 1
    assert p.last_seen_tick == 5
    kinds = [e.kind for e in journal.events]
    assert KIND_INTERVENTION in kinds


def test_apply_environment_value_accumulates_bias():
    p = create_player()
    voices = create_voices()
    env = EnvironmentChange(type="value", payload={"voice": "interest", "delta": 0.2})
    apply_environment(p, voices, env, tick=3)
    assert abs(p.voice_bias.get("interest", 0.0) - 0.2) < 1e-9
    env2 = EnvironmentChange(type="value", payload={"voice": "interest", "delta": 0.1})
    apply_environment(p, voices, env2, tick=4)
    assert abs(p.voice_bias.get("interest", 0.0) - 0.3) < 1e-9


def test_register_presence_increments():
    from sim.voices import create_voices
    p = create_player()
    voices = create_voices()
    register_presence(p, voices, tick=1, present=True)
    register_presence(p, voices, tick=2, present=True)
    assert p.presence_ticks == 2
    assert p.last_seen_tick == 2
