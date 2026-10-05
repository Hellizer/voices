import argparse
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.repository import (
    init_db,
    load_character,
    load_world,
    load_traces,
    load_events,
)

VOICE_ORDER = ["body", "safety", "connection", "recognition", "interest", "control"]


def print_character(character) -> None:
    if character is None:
        print("character: none")
        return
    print(f"character: id={character.id} tick={character.tick} location={character.location}")
    res = character.resources or {}
    energy = round(float(res.get("energy", 0.0)), 3)
    money = round(float(res.get("money", 0.0)), 3)
    social = round(float(res.get("social", 0.0)), 3)
    print(f"resources: energy={energy} money={money} social={social}")
    print("voices:")
    voices = character.voices or {}
    for name in VOICE_ORDER:
        v = voices.get(name)
        w = round(float(v.weight), 3) if v is not None else 0.0
        print(f"  {name}={w}")


def print_traces(traces) -> None:
    if traces is None:
        print("traces: active=0 total=0")
        return
    items = list(traces.items.values())
    active = [t for t in items if t.active]
    print(f"traces: active={len(active)} total={len(items)}")
    active.sort(key=lambda t: t.strength, reverse=True)
    for t in active:
        s = round(float(t.strength), 3)
        print(
            f"  {t.type} | {t.key} | strength={s} | "
            f"created={t.created_at} | updated={t.updated_at}"
        )


def print_events(events, limit: int = 30) -> None:
    if events is None:
        events = []
    print(f"events: {len(events)} total, last {limit}:")
    tail = events[-limit:] if limit > 0 else []
    for e in reversed(tail):
        try:
            payload_str = json.dumps(e.payload, ensure_ascii=False)
        except Exception:
            payload_str = ""
        if len(payload_str) > 120:
            payload_str = payload_str[:120]
        print(f"  tick={e.tick} {e.kind} {payload_str}")


def print_world(world) -> None:
    if world is None:
        print("world: none")
        return
    print(f"world: tick={world.tick} location={world.current_location}")
    print("npcs:")
    for npc_id, npc in (world.npcs or {}).items():
        rel = round(float(npc.relation), 3)
        print(f"  {npc_id} relation={rel}")
    windows = world.windows or []
    print(f"windows: {len(windows)}")
    for w in windows:
        print(
            f"  {w.id} action={w.action_id} loc={w.location} "
            f"opens={w.opens_at} closes={w.closes_at} "
            f"used={w.used} missed={w.missed}"
        )


def run(db_path: str, events_limit: int) -> None:
    conn = init_db(db_path)
    character = load_character(conn)
    world = load_world(conn)
    traces = load_traces(conn)
    events = load_events(conn, 0)

    print_character(character)
    print_traces(traces)
    print_world(world)
    print_events(events, events_limit)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="./state.db")
    parser.add_argument("--events", type=int, default=30)
    args = parser.parse_args()
    run(args.db, args.events)


if __name__ == "__main__":
    main()
