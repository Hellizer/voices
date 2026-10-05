from sim.voices import (
    VOICES,
    create_voices,
    apply_delta,
    normalize,
    top_voices,
    step,
    clamp,
)


def test_create_voices_count_and_names():
    voices = create_voices()
    assert len(voices) == 6
    for name in VOICES:
        assert name in voices


def test_create_voices_weight_equals_baseline():
    voices = create_voices()
    for name, v in voices.items():
        assert v.weight == v.baseline


def test_apply_delta_respects_sensitivity_and_caps():
    voices = create_voices()
    v = voices["body"]
    before = v.weight
    apply_delta(v, 0.5)
    assert v.weight > before
    assert v.weight <= 1.0
    for _ in range(20):
        apply_delta(v, 1.0)
    assert v.weight == 1.0


def test_normalize_sums_to_one():
    voices = create_voices()
    for v in voices.values():
        v.weight = 2.0
    normalize(voices)
    total = sum(v.weight for v in voices.values())
    assert abs(total - 1.0) < 1e-9


def test_top_voices_descending():
    voices = create_voices()
    voices["body"].weight = 0.9
    voices["safety"].weight = 0.8
    voices["connection"].weight = 0.1
    top = top_voices(voices, n=2)
    assert top[0][0] == "body"
    assert top[1][0] == "safety"
    assert top[0][1] >= top[1][1]


def test_step_keeps_count():
    voices = create_voices()
    step(voices)
    assert len(voices) == 6
    for v in voices.values():
        assert 0.0 <= v.weight <= 1.0
