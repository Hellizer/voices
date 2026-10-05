# voices/sim/actions.py
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple
import math
import random

from sim.voices import Voice, apply_delta, clamp
from sim.traces import (
    Traces,
    has_habit,
    habit_strength,
    register_repeat,
    register_threshold,
    create_debt,
    create_attachment,
    create_project,
    create_ritual,
    register_reputation,
)


def always(state: dict) -> bool:
    return True


def at_location(*locs: str) -> Callable[[dict], bool]:
    def pred(state: dict) -> bool:
        return state.get("location") in locs
    return pred


def has_resource(name: str, minimum: float = 0.0) -> Callable[[dict], bool]:
    def pred(state: dict) -> bool:
        return state.get("resources", {}).get(name, 0.0) >= minimum
    return pred


def voice_above(name: str, threshold: float) -> Callable[[dict], bool]:
    def pred(state: dict) -> bool:
        voices = state.get("voices", {})
        v = voices.get(name)
        if v is None:
            return False
        return v.weight >= threshold
    return pred


def voice_below(name: str, threshold: float) -> Callable[[dict], bool]:
    def pred(state: dict) -> bool:
        voices = state.get("voices", {})
        v = voices.get(name)
        if v is None:
            return False
        return v.weight < threshold
    return pred


def and_(*preds: Callable[[dict], bool]) -> Callable[[dict], bool]:
    def pred(state: dict) -> bool:
        return all(p(state) for p in preds)
    return pred


def or_(*preds: Callable[[dict], bool]) -> Callable[[dict], bool]:
    def pred(state: dict) -> bool:
        return any(p(state) for p in preds)
    return pred


def not_(pred: Callable[[dict], bool]) -> Callable[[dict], bool]:
    def inner(state: dict) -> bool:
        return not pred(state)
    return inner


@dataclass
class Action:
    id: str
    group: str
    costs: Dict[str, float]
    satisfies: Dict[str, float]
    raises: Dict[str, float]
    duration: int
    conditions: Callable[[dict], bool]
    traces: List[str]
    cooldown: int


ACTIONS: List[Action] = [
    # Bodily
    Action(
        id="eat", group="bodily",
        costs={"energy": 0.05, "money": 0.02},
        satisfies={"body": 0.3}, raises={},
        duration=1, conditions=at_location("home", "cafe"),
        traces=["habit"], cooldown=2,
    ),
    Action(
        id="sleep", group="bodily",
        costs={},
        satisfies={"body": 0.4}, raises={"interest": 0.05},
        duration=3, conditions=at_location("home"),
        traces=["habit"], cooldown=8,
    ),
    Action(
        id="drink", group="bodily",
        costs={"money": 0.03},
        satisfies={"body": 0.1}, raises={"body": 0.05},
        duration=1, conditions=at_location("home", "street", "cafe"),
        traces=["habit"], cooldown=1,
    ),
    Action(
        id="wash", group="bodily",
        costs={"energy": 0.05},
        satisfies={"body": 0.15}, raises={},
        duration=1, conditions=at_location("home"),
        traces=["habit"], cooldown=4,
    ),
    Action(
        id="go_outside", group="bodily",
        costs={"energy": 0.05},
        satisfies={"body": 0.2}, raises={"connection": 0.1},
        duration=1, conditions=at_location("street", "park"),
        traces=["habit"], cooldown=2,
    ),
    Action(
        id="move", group="bodily",
        costs={"energy": 0.15},
        satisfies={"body": 0.3}, raises={"recognition": 0.05},
        duration=1, conditions=at_location("gym", "street"),
        traces=["habit"], cooldown=3,
    ),
    Action(
        id="zone_out", group="bodily",
        costs={"energy": 0.02},
        satisfies={"body": 0.1}, raises={"safety": 0.1},
        duration=1, conditions=at_location("home", "nowhere"),
        traces=["habit", "threshold"], cooldown=3,
    ),

    # Domestic
    Action(
        id="clean", group="domestic",
        costs={"energy": 0.1},
        satisfies={"safety": 0.15}, raises={"control": 0.1},
        duration=1, conditions=at_location("home"),
        traces=["habit"], cooldown=4,
    ),
    Action(
        id="fix", group="domestic",
        costs={"energy": 0.15, "money": 0.05},
        satisfies={"control": 0.2}, raises={"interest": 0.05},
        duration=1, conditions=at_location("home"),
        traces=["habit"], cooldown=5,
    ),
    Action(
        id="cook", group="domestic",
        costs={"energy": 0.1, "money": 0.05},
        satisfies={"body": 0.2}, raises={"connection": 0.05},
        duration=1, conditions=at_location("home"),
        traces=["habit"], cooldown=3,
    ),
    Action(
        id="arrange", group="domestic",
        costs={"energy": 0.08},
        satisfies={"control": 0.15}, raises={},
        duration=1, conditions=at_location("home"),
        traces=["habit", "ritual"], cooldown=4,
    ),
    Action(
        id="save_up", group="domestic",
        costs={"energy": 0.05},
        satisfies={"safety": 0.2}, raises={"control": 0.1},
        duration=1, conditions=at_location("home", "work_place"),
        traces=["project"], cooldown=5,
    ),
    Action(
        id="throw_away", group="domestic",
        costs={"energy": 0.05},
        satisfies={"control": 0.1}, raises={"safety": 0.05},
        duration=1, conditions=at_location("home"),
        traces=["ritual"], cooldown=6,
    ),

    # Money
    Action(
        id="work", group="money",
        costs={"energy": 0.2},
        satisfies={"safety": 0.2}, raises={"recognition": 0.1},
        duration=1, conditions=at_location("work_place"),
        traces=["habit", "project"], cooldown=3,
    ),
    Action(
        id="side_gig", group="money",
        costs={"energy": 0.15, "social": 0.05},
        satisfies={"safety": 0.15}, raises={"recognition": 0.05},
        duration=1, conditions=at_location("street", "work_place"),
        traces=["project"], cooldown=4,
    ),
    Action(
        id="trade", group="money",
        costs={"money": 0.1, "social": 0.1},
        satisfies={"recognition": 0.15}, raises={"safety": 0.05},
        duration=1, conditions=at_location("shop", "street"),
        traces=["reputation"], cooldown=5,
    ),
    Action(
        id="invest", group="money",
        costs={"money": 0.2},
        satisfies={"safety": 0.1}, raises={"control": 0.15},
        duration=1, conditions=at_location("home", "work_place"),
        traces=["project"], cooldown=8,
    ),
    Action(
        id="borrow", group="money",
        costs={"social": 0.15},
        satisfies={"safety": 0.15}, raises={"connection": 0.05},
        duration=1, conditions=at_location("street", "cafe"),
        traces=["debt"], cooldown=8,
    ),
    Action(
        id="spend_on_self", group="money",
        costs={"money": 0.15},
        satisfies={"body": 0.15}, raises={"recognition": 0.1},
        duration=1, conditions=at_location("shop", "cafe"),
        traces=["habit"], cooldown=4,
    ),

    # Connection
    Action(
        id="write", group="connection",
        costs={"energy": 0.05, "social": 0.05},
        satisfies={"connection": 0.25}, raises={"interest": 0.05},
        duration=1, conditions=at_location("home", "cafe"),
        traces=["habit"], cooldown=2,
    ),
    Action(
        id="invite", group="connection",
        costs={"energy": 0.1, "social": 0.1, "money": 0.05},
        satisfies={"connection": 0.3}, raises={"recognition": 0.1},
        duration=1, conditions=at_location("home", "cafe"),
        traces=["attachment"], cooldown=4,
    ),
    Action(
        id="help", group="connection",
        costs={"energy": 0.15, "social": 0.1},
        satisfies={"connection": 0.2}, raises={"recognition": 0.15},
        duration=1, conditions=at_location("street", "work_place"),
        traces=["reputation", "attachment"], cooldown=4,
    ),
    Action(
        id="refuse", group="connection",
        costs={"social": 0.15},
        satisfies={"control": 0.2}, raises={"safety": 0.1},
        duration=1, conditions=always,
        traces=["reputation", "scar"], cooldown=5,
    ),
    Action(
        id="lie", group="connection",
        costs={"social": 0.05},
        satisfies={"safety": 0.2}, raises={"control": 0.1},
        duration=1, conditions=always,
        traces=["scar", "threshold"], cooldown=4,
    ),
    Action(
        id="break_off", group="connection",
        costs={"social": 0.2},
        satisfies={"control": 0.25}, raises={"safety": 0.1},
        duration=1, conditions=always,
        traces=["scar"], cooldown=10,
    ),
    Action(
        id="come_back", group="connection",
        costs={"energy": 0.05},
        satisfies={"connection": 0.2}, raises={"safety": 0.05},
        duration=1, conditions=always,
        traces=["attachment"], cooldown=6,
    ),

    # Recognition
    Action(
        id="do", group="recognition",
        costs={"energy": 0.15},
        satisfies={"recognition": 0.25}, raises={"control": 0.05},
        duration=1, conditions=at_location("work_place", "street"),
        traces=["habit", "project"], cooldown=3,
    ),
    Action(
        id="show", group="recognition",
        costs={"social": 0.1},
        satisfies={"recognition": 0.3}, raises={"connection": 0.05},
        duration=1, conditions=at_location("street", "cafe"),
        traces=["reputation"], cooldown=4,
    ),
    Action(
        id="stay_silent", group="recognition",
        costs={"social": 0.05},
        satisfies={"safety": 0.15}, raises={"control": 0.15},
        duration=1, conditions=always,
        traces=["threshold", "scar"], cooldown=2,
    ),
    Action(
        id="brag", group="recognition",
        costs={"social": 0.1},
        satisfies={"recognition": 0.25}, raises={"control": 0.05},
        duration=1, conditions=at_location("cafe", "street"),
        traces=["reputation"], cooldown=4,
    ),
    Action(
        id="humiliate", group="recognition",
        costs={"social": 0.15},
        satisfies={"recognition": 0.2}, raises={"control": 0.1},
        duration=1, conditions=at_location("cafe", "work_place"),
        traces=["scar", "reputation"], cooldown=8,
    ),
    Action(
        id="revenge", group="recognition",
        costs={"energy": 0.2},
        satisfies={"recognition": 0.3}, raises={"control": 0.15},
        duration=1, conditions=always,
        traces=["scar", "project"], cooldown=12,
    ),

    # Interest
    Action(
        id="read", group="interest",
        costs={"energy": 0.05},
        satisfies={"interest": 0.25}, raises={"safety": 0.05},
        duration=1, conditions=at_location("home", "cafe"),
        traces=["habit", "project"], cooldown=2,
    ),
    Action(
        id="learn", group="interest",
        costs={"energy": 0.15, "money": 0.05},
        satisfies={"interest": 0.3}, raises={"recognition": 0.1},
        duration=1, conditions=at_location("home", "work_place"),
        traces=["project"], cooldown=4,
    ),
    Action(
        id="try", group="interest",
        costs={"energy": 0.1},
        satisfies={"interest": 0.25}, raises={"connection": 0.05},
        duration=1, conditions=at_location("street", "park", "cafe"),
        traces=["habit", "project"], cooldown=3,
    ),
    Action(
        id="abandon", group="interest",
        costs={"energy": 0.05},
        satisfies={"safety": 0.15}, raises={"control": 0.1},
        duration=1, conditions=always,
        traces=["missed_window"], cooldown=6,
    ),
    Action(
        id="collect", group="interest",
        costs={"money": 0.1},
        satisfies={"interest": 0.2}, raises={"safety": 0.05},
        duration=1, conditions=at_location("shop", "street"),
        traces=["attachment"], cooldown=3,
    ),

    # Control
    Action(
        id="plan", group="control",
        costs={"energy": 0.05},
        satisfies={"control": 0.25}, raises={"safety": 0.1},
        duration=1, conditions=at_location("home"),
        traces=["project", "ritual"], cooldown=3,
    ),
    Action(
        id="forbid_self", group="control",
        costs={"energy": 0.1},
        satisfies={"control": 0.3}, raises={"safety": 0.1},
        duration=1, conditions=at_location("home"),
        traces=["threshold", "ritual"], cooldown=4,
    ),
    Action(
        id="ritual", group="control",
        costs={"energy": 0.05},
        satisfies={"control": 0.2}, raises={"body": 0.05},
        duration=1, conditions=at_location("home"),
        traces=["ritual", "habit"], cooldown=2,
    ),
    Action(
        id="break_down", group="control",
        costs={"energy": 0.25},
        satisfies={"body": 0.2}, raises={"recognition": 0.15},
        duration=1, conditions=always,
        traces=["scar", "threshold"], cooldown=10,
    ),
]


def get_action(action_id: str) -> Optional[Action]:
    for action in ACTIONS:
        if action.id == action_id:
            return action
    return None


def is_available(action: Action, state: dict) -> bool:
    if not action.conditions(state):
        return False
    tick = state.get("tick", 0)
    cooldowns = state.get("cooldowns", {})
    return cooldowns.get(action.id, 0) <= tick


def score(action: Action, state: dict) -> float:
    s = 0.0
    voices = state.get("voices", {})
    for voice_name, coef in action.satisfies.items():
        v = voices.get(voice_name)
        if v is not None:
            s += v.weight * coef
    for voice_name, coef in action.raises.items():
        v = voices.get(voice_name)
        if v is not None:
            s -= v.weight * coef * 0.5
    for _res, amount in action.costs.items():
        s -= amount
    traces = state.get("traces")
    if traces is not None and has_habit(traces, action.id):
        s += habit_strength(traces, action.id) * 0.04
    return clamp(s, -1.0, 1.0)


def softmax(scores: Dict[str, float], temperature: float = 0.4) -> Dict[str, float]:
    if not scores:
        return {}
    if temperature <= 0:
        best = max(scores, key=lambda k: scores[k])
        return {k: (1.0 if k == best else 0.0) for k in scores}
    m = max(scores.values())
    exps = {k: math.exp((v - m) / temperature) for k, v in scores.items()}
    total = sum(exps.values())
    if total <= 0.0:
        return {k: 0.0 for k in scores}
    return {k: v / total for k, v in exps.items()}


def choose_action(state: dict) -> Optional[Tuple[str, str]]:
    available = [a for a in ACTIONS if is_available(a, state)]
    if not available:
        return ("idle", "idle")
    scores = {a.id: score(a, state) for a in available}
    max_score = max(scores.values())
    if max_score < 0.0:
        return ("idle", "idle")
    delta = state.get("choice_delta", 0.08)
    cutoff = max_score - delta
    filtered = {aid: s for aid, s in scores.items() if s >= cutoff}
    probs = softmax(filtered, state.get("temperature", 0.4))
    r = random.random()
    cum = 0.0
    last_id: Optional[str] = None
    for aid, p in probs.items():
        last_id = aid
        cum += p
        if r <= cum:
            a = get_action(aid)
            return (aid, a.group) if a is not None else ("idle", "idle")
    if last_id is not None:
        a = get_action(last_id)
        if a is not None:
            return (last_id, a.group)
    return ("idle", "idle")


def apply_action(action_id: str, state: dict) -> None:
    if action_id == "idle":
        resources = state.get("resources", {})
        energy = resources.get("energy", 0.0)
        resources["energy"] = clamp(energy - 0.01)
        return

    action = get_action(action_id)
    if action is None:
        return

    resources = state["resources"]
    for res, amount in action.costs.items():
        current = resources.get(res, 0.0)
        if res == "money":
            resources[res] = max(0.0, current - amount)
        else:
            resources[res] = clamp(current - amount, 0.0, 1.0)

    voices = state["voices"]
    for voice_name, coef in action.satisfies.items():
        v = voices.get(voice_name)
        if v is not None:
            apply_delta(v, -coef * 0.02)
    for voice_name, coef in action.raises.items():
        v = voices.get(voice_name)
        if v is not None:
            apply_delta(v, coef * 0.01)

    cooldowns = state["cooldowns"]
    tick = state["tick"]
    cooldowns[action.id] = tick + action.cooldown
    register_repeat(state["traces"], action.id, tick)

    traces = state["traces"]
    for trace_type in action.traces:
        if trace_type == "habit":
            continue
        if trace_type == "threshold":
            register_threshold(traces, f"action:{action.id}", tick)
        elif trace_type == "debt":
            create_debt(
                traces,
                action.id,
                tick,
                due_at=tick + 10,
                payload={"action_id": action.id},
            )
        elif trace_type == "attachment":
            create_attachment(
                traces,
                action.id,
                tick,
                payload={"action_id": action.id},
            )
        elif trace_type == "project":
            create_project(
                traces,
                action.id,
                tick,
                payload={"action_id": action.id},
            )
        elif trace_type == "ritual":
            if has_habit(traces, action.id):
                create_ritual(
                    traces,
                    action.id,
                    tick,
                    payload={"action_id": action.id},
                )
        elif trace_type == "reputation":
            register_reputation(
                traces,
                action.id,
                tick,
                delta=0.05,
                payload={"action_id": action.id},
            )
        elif trace_type == "scar":
            continue
        elif trace_type == "self_narrative":
            continue
        elif trace_type == "missed_window":
            continue
