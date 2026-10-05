from sim.voices import create_voices
from sim.traces import create_traces
from sim.actions import (
    get_action,
    is_available,
    score,
    softmax,
    choose_action,
    apply_action,
)


def make_state():
    return {
        "voices": create_voices(),
        "traces": create_traces(),
        "tick": 100,
        "location": "home",
        "resources": {"energy": 0.9, "money": 0.9, "social": 0.9},
        "cooldowns": {},
        "temperature": 0.4,
    }


def test_get_action_eat_bodily():
    a = get_action("eat")
    assert a is not None
    assert a.group == "bodily"


def test_is_available_respects_cooldown():
    state = make_state()
    a = get_action("eat")
    assert is_available(a, state) is True
    state["cooldowns"]["eat"] = state["tick"] + 5
    assert is_available(a, state) is False


def test_score_higher_with_voice_weight():
    state = make_state()
    state["location"] = "home"
    a = get_action("eat")
    s_low = score(a, state)
    state["voices"]["body"].weight = 0.9
    s_high = score(a, state)
    assert s_high > s_low


def test_softmax_sums_to_one():
    probs = softmax({"a": 0.1, "b": 0.5, "c": -0.3}, temperature=0.4)
    total = sum(probs.values())
    assert abs(total - 1.0) < 1e-9


def test_choose_action_returns_valid_pair():
    state = make_state()
    result = choose_action(state)
    assert result is not None
    aid, group = result
    assert isinstance(aid, str)
    assert isinstance(group, str)


def test_apply_action_consumes_and_cooldown():
    state = make_state()
    a = get_action("eat")
    before_energy = state["resources"]["energy"]
    before_money = state["resources"]["money"]
    apply_action("eat", state)
    assert state["resources"]["energy"] < before_energy
    assert state["resources"]["money"] < before_money
    assert state["cooldowns"]["eat"] == state["tick"] + a.cooldown
