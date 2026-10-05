# voices/sim/loop.py
from dataclasses import dataclass, field
from typing import List, Optional

from sim.character import Character, build_state, sync_from_state
from sim.voices import step, normalize, clamp
from sim.actions import choose_action, apply_action
from sim.traces import decay_all, register_missed_window
from sim.memory import (
    update_influence,
    apply_memory,
    log,
    KIND_ACTION,
    KIND_CRISIS,
    KIND_WORLD,
)
from sim.world import (
    World,
    Window,
    update_time,
    register_location_tick,
    spawn_window,
    close_expired_windows,
    apply_window_reward,
    apply_window_miss_penalty,
    apply_npc_expectations,
    register_npc_memory,
    move_to,
    npcs_at,
    active_windows,
    mark_used,
)
from sim.mutate import (
    check_thresholds,
    apply_mutation,
    check_crisis,
    apply_crisis,
    snapshot_mutation,
)
from sim.player import apply_voice_bias, register_presence

WINDOWS_PER_DAY = 3
DAY_LENGTH = 24

_WINDOW_PLAN = [
    ("work", "work_place", {"recognition": 0.1}),
    ("invite", "cafe", {"connection": 0.15}),
    ("learn", "home", {"interest": 0.15}),
]


@dataclass
class TickResult:
    tick: int
    action_id: str
    action_group: str
    crisis: bool
    mutations: List[dict] = field(default_factory=list)
    expired_windows: List[str] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)


def maybe_spawn_windows(
    world: World,
    tick: int,
    per_day: int = WINDOWS_PER_DAY,
    day_length: int = DAY_LENGTH,
) -> List[Window]:
    created: List[Window] = []
    if tick % day_length != 0:
        return created
    existing_ids = {w.id for w in world.windows}
    for i in range(per_day):
        window_id = f"w_{tick}_{i}"
        if window_id in existing_ids:
            continue
        action_id, location, reward = _WINDOW_PLAN[i % len(_WINDOW_PLAN)]
        opens_at = tick + i * 4
        closes_at = opens_at + 6
        w = spawn_window(
            world,
            window_id,
            action_id,
            location,
            opens_at,
            closes_at,
            reward=reward,
            miss_penalty={"safety": -0.05},
        )
        created.append(w)
    return created


def pick_location(character: Character, world: World, action_id: str) -> Optional[str]:
    current = world.locations.get(character.location)
    if current is not None and action_id in current.actions_available:
        return current.id
    for loc_id, loc in world.locations.items():
        if action_id in loc.actions_available:
            return loc_id
    return None


def simulation_tick(character: Character, world: World, player_present: bool = False) -> TickResult:
    character.tick += 1
    update_time(world, character.tick)
    register_location_tick(world)

    register_presence(
        character.player,
        character.voices,
        character.tick,
        player_present,
        character.influence,
    )

    update_influence(character.influence, character.journal, character.tick)
    step(character.voices)
    apply_memory(character.voices, character.influence)
    apply_voice_bias(character.player, character.voices)
    decay_all(character.traces, rate=0.01)

    events_before = len(character.journal.events)

    maybe_spawn_windows(world, character.tick)

    expired = close_expired_windows(world)
    for w in expired:
        register_missed_window(
            character.traces,
            w.id,
            character.tick,
            payload={"action_id": w.action_id},
        )
        apply_window_miss_penalty(character.voices, w)

    state = build_state(character)
    chosen = choose_action(state)
    if chosen is None:
        chosen = ("idle", "idle")
    action_id, action_group = chosen

    if action_id != "idle":
        current_loc = world.locations.get(character.location)
        action_here = current_loc is not None and action_id in current_loc.actions_available
        moved = False

        if not action_here:
            target_location = pick_location(character, world, action_id)
            if target_location is not None and target_location != character.location:
                move_to(world, target_location)
                character.location = target_location
                state["location"] = target_location
                resources = state["resources"]
                resources["energy"] = clamp(resources.get("energy", 0.0) - 0.02)
                sync_from_state(character, state)
                action_id = "move"
                action_group = "movement"
                moved = True
                log(
                    character.journal,
                    character.tick,
                    KIND_ACTION,
                    {"action_id": "move", "group": "movement", "to": target_location},
                )

        if not moved:
            apply_action(action_id, state)
            sync_from_state(character, state)

            active = active_windows(world, character.location)
            for w in list(active):
                if w.action_id == action_id:
                    mark_used(world, w.id)
                    apply_window_reward(character.voices, w)
                    log(
                        character.journal,
                        character.tick,
                        KIND_WORLD,
                        {"window_used": w.id, "action_id": action_id},
                    )
                    break

            apply_npc_expectations(world, character.voices, action_id)
            for npc in npcs_at(world, world.current_location):
                register_npc_memory(world, npc.id, character.tick, action_id, outcome="ok")

            log(
                character.journal,
                character.tick,
                KIND_ACTION,
                {"action_id": action_id, "group": action_group},
            )
    else:
        apply_action("idle", state)
        sync_from_state(character, state)
        log(
            character.journal,
            character.tick,
            KIND_ACTION,
            {"action_id": "idle", "group": "idle"},
        )

    mutations = check_thresholds(character.traces, character.voices, character.tick)
    for m in mutations:
        apply_mutation(character.voices, character.traces, m)

    crisis = check_crisis(character.voices, character.traces, character.tick)
    if crisis is not None:
        crisis_mutation = apply_crisis(character.voices, character.traces, crisis)
        mutations.append(crisis_mutation)
        log(
            character.journal,
            character.tick,
            KIND_CRISIS,
            {
                "voices": list(crisis.voices),
                "severity": crisis.severity,
                "chosen": crisis_mutation.payload.get("chosen"),
            },
        )

    normalize(character.voices)

    events_after = len(character.journal.events)
    new_events = character.journal.events[events_before:events_after]

    return TickResult(
        tick=character.tick,
        action_id=action_id,
        action_group=action_group,
        crisis=crisis is not None,
        mutations=[snapshot_mutation(m) for m in mutations],
        expired_windows=[w.id for w in expired],
        events=[
            {"tick": e.tick, "kind": e.kind, "payload": dict(e.payload)}
            for e in new_events
        ],
    )
