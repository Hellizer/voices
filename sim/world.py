# voices/sim/world.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sim.voices import Voice, clamp


@dataclass
class Window:
    id: str
    action_id: str
    location: str
    opens_at: int
    closes_at: int
    reward: Dict[str, float] = field(default_factory=dict)
    miss_penalty: Dict[str, float] = field(default_factory=dict)
    used: bool = False
    missed: bool = False


@dataclass
class NPC:
    id: str
    name: str
    location: str
    relation: float = 0.5
    expectations: List[str] = field(default_factory=list)
    memory: List[dict] = field(default_factory=list)


@dataclass
class Location:
    id: str
    name: str
    actions_available: List[str] = field(default_factory=list)
    npcs: List[str] = field(default_factory=list)


@dataclass
class World:
    tick: int = 0
    locations: Dict[str, Location] = field(default_factory=dict)
    npcs: Dict[str, NPC] = field(default_factory=dict)
    windows: List[Window] = field(default_factory=list)
    current_location: str = "home"
    location_streak: Dict[str, int] = field(default_factory=dict)


def create_world(tick: int = 0) -> World:
    locations = {
        "home": Location(
            id="home",
            name="дом",
            actions_available=[
                "eat", "sleep", "drink", "wash", "clean", "fix", "cook",
                "arrange", "save_up", "throw_away", "invest", "write",
                "invite", "read", "learn", "plan", "forbid_self", "ritual",
                "zone_out",
            ],
            npcs=[],
        ),
        "street": Location(
            id="street",
            name="улица",
            actions_available=[
                "drink", "go_outside", "move", "side_gig", "trade",
                "borrow", "help", "do", "show", "brag", "try", "collect",
            ],
            npcs=["stranger"],
        ),
        "cafe": Location(
            id="cafe",
            name="кафе",
            actions_available=[
                "eat", "drink", "write", "invite", "borrow", "show",
                "brag", "read", "try", "spend_on_self",
            ],
            npcs=["barista"],
        ),
        "work_place": Location(
            id="work_place",
            name="работа",
            actions_available=[
                "save_up", "work", "side_gig", "invest", "help", "do",
                "learn", "humiliate",
            ],
            npcs=["boss"],
        ),
        "gym": Location(
            id="gym",
            name="спортзал",
            actions_available=["move"],
            npcs=[],
        ),
        "park": Location(
            id="park",
            name="парк",
            actions_available=["go_outside", "try"],
            npcs=[],
        ),
        "shop": Location(
            id="shop",
            name="магазин",
            actions_available=["trade", "spend_on_self", "collect"],
            npcs=["shopkeeper"],
        ),
        "nowhere": Location(
            id="nowhere",
            name="нигде",
            actions_available=["zone_out"],
            npcs=[],
        ),
    }

    npcs = {
        "stranger": NPC(
            id="stranger",
            name="прохожий",
            location="street",
            relation=0.4,
            expectations=["help"],
            memory=[],
        ),
        "barista": NPC(
            id="barista",
            name="бариста",
            location="cafe",
            relation=0.5,
            expectations=["write", "invite"],
            memory=[],
        ),
        "boss": NPC(
            id="boss",
            name="начальник",
            location="work_place",
            relation=0.5,
            expectations=["work", "do"],
            memory=[],
        ),
        "shopkeeper": NPC(
            id="shopkeeper",
            name="продавец",
            location="shop",
            relation=0.5,
            expectations=["trade", "collect"],
            memory=[],
        ),
    }

    return World(
        tick=tick,
        locations=locations,
        npcs=npcs,
        windows=[],
        current_location="home",
        location_streak={},
    )


def get_location(world: World, location_id: str) -> Optional[Location]:
    return world.locations.get(location_id)


def get_npc(world: World, npc_id: str) -> Optional[NPC]:
    return world.npcs.get(npc_id)


def npcs_at(world: World, location_id: str) -> List[NPC]:
    location = world.locations.get(location_id)
    if location is None:
        return []
    result = []
    for npc_id in location.npcs:
        npc = world.npcs.get(npc_id)
        if npc is not None:
            result.append(npc)
    return result


def spawn_window(
    world: World,
    window_id: str,
    action_id: str,
    location: str,
    opens_at: int,
    closes_at: int,
    reward: Optional[dict] = None,
    miss_penalty: Optional[dict] = None,
) -> Window:
    window = Window(
        id=window_id,
        action_id=action_id,
        location=location,
        opens_at=opens_at,
        closes_at=closes_at,
        reward=dict(reward) if reward else {},
        miss_penalty=dict(miss_penalty) if miss_penalty else {},
        used=False,
        missed=False,
    )
    world.windows.append(window)
    return window


def active_windows(world: World, location: Optional[str] = None) -> List[Window]:
    result = []
    for w in world.windows:
        if w.used or w.missed:
            continue
        if not (w.opens_at <= world.tick < w.closes_at):
            continue
        if location is not None and w.location != location:
            continue
        result.append(w)
    return result


def close_expired_windows(world: World) -> List[Window]:
    expired = []
    for w in world.windows:
        if w.used or w.missed:
            continue
        if world.tick >= w.closes_at:
            w.missed = True
            expired.append(w)
    return expired


def mark_used(world: World, window_id: str) -> Optional[Window]:
    for w in world.windows:
        if w.id == window_id:
            if not w.used:
                w.used = True
                return w
            return None
    return None


def update_time(world: World, tick: int) -> None:
    world.tick = tick


def register_location_tick(world: World) -> None:
    loc = world.current_location
    world.location_streak[loc] = world.location_streak.get(loc, 0) + 1


def apply_window_reward(voices: Dict[str, Voice], window: Window) -> None:
    for voice_name, delta in window.reward.items():
        v = voices.get(voice_name)
        if v is not None:
            v.weight = clamp(v.weight + delta)


def apply_window_miss_penalty(voices: Dict[str, Voice], window: Window) -> None:
    for voice_name, delta in window.miss_penalty.items():
        v = voices.get(voice_name)
        if v is not None:
            v.weight = clamp(v.weight + delta)


def apply_npc_expectations(
    world: World, voices: Dict[str, Voice], action_id: str
) -> None:
    location_id = world.current_location
    location = world.locations.get(location_id)
    if location is None:
        return
    connection = voices.get("connection")
    streak = world.location_streak.get(location_id, 0)
    any_matched = False
    for npc_id in location.npcs:
        npc = world.npcs.get(npc_id)
        if npc is None:
            continue
        if action_id in npc.expectations:
            npc.relation = clamp(npc.relation + 0.05)
            if connection is not None:
                connection.weight = clamp(connection.weight + 0.02)
            any_matched = True
        else:
            if streak >= 3:
                npc.relation = clamp(npc.relation - 0.01)
    if any_matched:
        world.location_streak[location_id] = 0


def register_npc_memory(
    world: World,
    npc_id: str,
    tick: int,
    action_id: str,
    outcome: str,
) -> None:
    npc = world.npcs.get(npc_id)
    if npc is None:
        return
    npc.memory.append(
        {"tick": tick, "action_id": action_id, "outcome": outcome}
    )
    while len(npc.memory) > 50:
        npc.memory.pop(0)


def move_to(world: World, location_id: str) -> None:
    if location_id in world.locations:
        world.current_location = location_id


def snapshot(world: World) -> dict:
    locations_snap = {}
    for loc_id, loc in world.locations.items():
        locations_snap[loc_id] = {
            "name": loc.name,
            "actions_available": list(loc.actions_available),
            "npcs": list(loc.npcs),
        }

    npcs_snap = {}
    for npc_id, npc in world.npcs.items():
        npcs_snap[npc_id] = {
            "name": npc.name,
            "relation": npc.relation,
            "expectations": list(npc.expectations),
        }

    windows_snap = []
    for w in world.windows:
        windows_snap.append(
            {
                "id": w.id,
                "action_id": w.action_id,
                "location": w.location,
                "opens_at": w.opens_at,
                "closes_at": w.closes_at,
                "used": w.used,
                "missed": w.missed,
            }
        )

    return {
        "tick": world.tick,
        "current_location": world.current_location,
        "locations": locations_snap,
        "npcs": npcs_snap,
        "windows": windows_snap,
    }
