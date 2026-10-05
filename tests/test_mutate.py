from sim.voices import create_voices, DEFAULT_BASELINE
from sim.traces import create_traces, get, create_scar
from sim.mutate import (
    check_crisis,
    resolve,
    apply_crisis,
    check_thresholds,
    Crisis,
    CRISIS_THRESHOLD,
)


def test_check_crisis_none_below_threshold():
    voices = create_voices()
    for v in voices.values():
        v.weight = 0.1
    assert check_crisis(voices, create_traces(), tick=1) is None


def test_check_crisis_returns_crisis():
    voices = create_voices()
    for v in voices.values():
        v.weight = 0.1
    voices["safety"].weight = 0.9
    voices["interest"].weight = 0.85
    c = check_crisis(voices, create_traces(), tick=5)
    assert c is not None
    assert c.tick == 5
    for name in c.voices:
        assert name in voices


def test_resolve_picks_higher():
    voices = create_voices()
    for v in voices.values():
        v.weight = 0.1
    voices["safety"].weight = 0.9
    voices["interest"].weight = 0.8
    c = Crisis(voices=("safety", "interest"), severity=0.85, tick=1)
    assert resolve(voices, c) == "safety"


def test_apply_crisis_creates_scar_and_narrative():
    voices = create_voices()
    for v in voices.values():
        v.weight = 0.1
    voices["safety"].weight = 0.9
    voices["interest"].weight = 0.85
    voices["safety"].baseline = 0.2
    voices["interest"].baseline = 0.2
    traces = create_traces()
    c = Crisis(voices=("safety", "interest"), severity=0.85, tick=10)
    m = apply_crisis(voices, traces, c)
    assert m.kind == "crisis"
    assert m.payload.get("chosen") == "safety"
    scar = get(traces, "scar", "crisis:safety_vs_interest")
    assert scar is not None
    narr = get(traces, "self_narrative", "after:safety")
    assert narr is not None
    assert voices["safety"].baseline > 0.2
    assert voices["interest"].baseline < 0.2


def test_check_crisis_skips_existing_scar():
    voices = create_voices()
    for v in voices.values():
        v.weight = 0.1
    voices["safety"].weight = 0.9
    voices["interest"].weight = 0.85
    traces = create_traces()
    create_scar(traces, "crisis:safety_vs_interest", tick=1)
    c = check_crisis(voices, traces, tick=5)
    if c is not None:
        assert set(c.voices) != {"safety", "interest"}


def test_check_thresholds_creates_mutations():
    voices = create_voices()
    for v in voices.values():
        v.weight = 0.1
    voices["body"].weight = 0.95
    voices["control"].weight = 0.01
    traces = create_traces()

    all_mutations = []
    for tick in (1, 2, 3):
        all_mutations.extend(check_thresholds(traces, voices, tick=tick))

    kinds = {m.key for m in all_mutations}
    assert "voice_high:body" in kinds
    assert "voice_low:control" in kinds
    assert any(m.kind == "narrative_shift" for m in all_mutations)
