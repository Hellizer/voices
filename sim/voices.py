import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

VOICES = ["body", "safety", "connection", "recognition", "interest", "control"]

DEFAULT_BASELINE = {
    "body": 0.15,
    "safety": 0.20,
    "connection": 0.20,
    "recognition": 0.15,
    "interest": 0.15,
    "control": 0.15,
}

DEFAULT_SENSITIVITY = {
    "body": 0.5,
    "safety": 0.6,
    "connection": 0.5,
    "recognition": 0.7,
    "interest": 0.5,
    "control": 0.4,
}

LINKS = {
    "body":        {"safety": 0.0,  "connection": 0.0,  "recognition": 0.0,  "interest": -0.2, "control": 0.0},
    "safety":      {"body": 0.0,    "connection": 0.0,  "recognition": 0.0,  "interest": -0.3, "control": 0.0},
    "connection":  {"body": -0.2,   "safety": 0.0,      "recognition": 0.0,  "interest": 0.0,  "control": 0.0},
    "recognition": {"body": 0.0,    "safety": 0.2,      "connection": 0.0,  "interest": 0.0,  "control": 0.3},
    "interest":    {"body": 0.0,    "safety": 0.0,      "connection": 0.0,  "recognition": 0.0, "control": -0.2},
    "control":     {"body": 0.0,    "safety": 0.0,      "connection": -0.3, "recognition": -0.2, "interest": 0.0},
}

MEMORY_ALPHA = 0.2
LINK_RATE = 0.01
DECAY_RATE = 0.02
RESISTANCE_SHARPNESS = 6.0


@dataclass
class Voice:
    name: str
    weight: float
    baseline: float
    sensitivity: float
    memory: float
    links: Dict[str, float] = field(default_factory=dict)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def weight_resistance(w: float) -> float:
    distance = abs(w - 0.5)
    if distance <= 0.3:
        return 1.0
    extra = (distance - 0.3) / 0.5
    return 1.0 - 0.6 * extra


def create_voices() -> Dict[str, Voice]:
    voices: Dict[str, Voice] = {}
    for name in VOICES:
        baseline = DEFAULT_BASELINE[name]
        voices[name] = Voice(
            name=name,
            weight=baseline,
            baseline=baseline,
            sensitivity=DEFAULT_SENSITIVITY[name],
            memory=baseline,
            links=dict(LINKS[name]),
        )
    return voices


def decay(voice: Voice, rate: float = DECAY_RATE) -> None:
    voice.weight = clamp(voice.weight + (voice.baseline - voice.weight) * rate)


def update_memory(voice: Voice, alpha: float = MEMORY_ALPHA) -> None:
    voice.memory = clamp(voice.memory * (1 - alpha) + voice.weight * alpha)


def apply_delta(voice: Voice, delta: float) -> None:
    r = weight_resistance(voice.weight)
    voice.weight = clamp(voice.weight + delta * voice.sensitivity * r)


def normalize(voices: Dict[str, Voice]) -> None:
    total = sum(v.weight for v in voices.values())
    if total > 0:
        for voice in voices.values():
            voice.weight = voice.weight / total


def apply_links(voices: Dict[str, Voice]) -> None:
    for src_name, targets in LINKS.items():
        if src_name not in voices:
            continue
        src = voices[src_name]
        for dst_name, coeff in targets.items():
            if coeff == 0.0:
                continue
            if dst_name not in voices:
                continue
            dst = voices[dst_name]
            delta = src.weight * coeff * LINK_RATE
            dst.weight = clamp(dst.weight + delta)


def step(voices: Dict[str, Voice]) -> None:
    apply_links(voices)
    for voice in voices.values():
        decay(voice)
    for voice in voices.values():
        update_memory(voice)
    normalize(voices)


def top_voices(voices: Dict[str, Voice], n: int = 2) -> List[Tuple[str, float]]:
    ordered = sorted(voices.items(), key=lambda item: item[1].weight, reverse=True)
    return [(name, voice.weight) for name, voice in ordered[:n]]


def snapshot(voices: Dict[str, Voice]) -> Dict[str, Dict[str, float]]:
    return {
        name: {
            "weight": voice.weight,
            "baseline": voice.baseline,
            "memory": voice.memory,
        }
        for name, voice in voices.items()
    }
