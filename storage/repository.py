# voices/storage/repository.py
import sqlite3
import json
import os
import datetime
from pathlib import Path
from typing import Optional, List

from sim.character import Character, create_character
from sim.world import World, create_world, Window, NPC, Location
from sim.traces import Traces, Trace, create_traces
from sim.memory import Journal, Event, MemoryInfluence, create_journal, create_influence
from sim.player import PlayerState
from sim.voices import Voice, create_voices


def init_db(db_path: str) -> sqlite3.Connection:
    p = Path(db_path)
    parent = p.parent
    if str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS character (
                id TEXT PRIMARY KEY,
                state JSON,
                updated_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS voices (
                name TEXT PRIMARY KEY,
                weight REAL,
                baseline REAL,
                sensitivity REAL,
                memory REAL,
                links JSON
            );
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT UNIQUE,
                type TEXT,
                payload JSON,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                strength REAL,
                active BOOLEAN
            );
            CREATE TABLE IF NOT EXISTS world (
                id TEXT PRIMARY KEY,
                state JSON,
                updated_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick INTEGER,
                kind TEXT,
                payload JSON,
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS player_input (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                payload JSON,
                created_at TIMESTAMP,
                effect JSON
            );
            """
        )
        conn.commit()
    except sqlite3.DatabaseError:
        try:
            conn.close()
        except Exception:
            pass
        raise
    return conn


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def save_character(conn: sqlite3.Connection, character: Character) -> None:
    state_json = json.dumps(character_to_dict(character), ensure_ascii=False)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO character (id, state, updated_at) VALUES (?, ?, ?)",
        (character.id, state_json, _now()),
    )
    conn.commit()


def load_character(conn: sqlite3.Connection, character_id: str = "default") -> Optional[Character]:
    cur = conn.cursor()
    cur.execute("SELECT state FROM character WHERE id = ?", (character_id,))
    row = cur.fetchone()
    if row is None:
        return None
    data = json.loads(row["state"])
    return dict_to_character(data)


def save_world(conn: sqlite3.Connection, world: World, world_id: str = "default") -> None:
    state_json = json.dumps(world_to_dict(world), ensure_ascii=False)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO world (id, state, updated_at) VALUES (?, ?, ?)",
        (world_id, state_json, _now()),
    )
    conn.commit()


def load_world(conn: sqlite3.Connection, world_id: str = "default") -> Optional[World]:
    cur = conn.cursor()
    cur.execute("SELECT state FROM world WHERE id = ?", (world_id,))
    row = cur.fetchone()
    if row is None:
        return None
    data = json.loads(row["state"])
    return dict_to_world(data)


def save_traces(conn: sqlite3.Connection, traces: Traces) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM traces")
    for trace in traces.items.values():
        payload_json = json.dumps(
            {"key": trace.key, "payload": trace.payload},
            ensure_ascii=False,
        )
        cur.execute(
            "INSERT INTO traces (trace_id, type, payload, created_at, updated_at, strength, active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                trace.id,
                trace.type,
                payload_json,
                int(trace.created_at),
                int(trace.updated_at),
                float(trace.strength),
                1 if trace.active else 0,
            ),
        )
    conn.commit()


def load_traces(conn: sqlite3.Connection) -> Traces:
    traces = create_traces()
    cur = conn.cursor()
    cur.execute(
        "SELECT trace_id, type, payload, created_at, updated_at, strength, active FROM traces"
    )
    for row in cur.fetchall():
        payload_json = json.loads(row["payload"]) if row["payload"] else {}
        key = payload_json.get("key", "")
        payload = payload_json.get("payload", {})
        trace = Trace(
            id=row["trace_id"],
            type=row["type"],
            key=key,
            strength=float(row["strength"]) if row["strength"] is not None else 0.0,
            created_at=int(row["created_at"]) if row["created_at"] is not None else 0,
            updated_at=int(row["updated_at"]) if row["updated_at"] is not None else 0,
            active=bool(row["active"]),
            payload=payload,
        )
        traces.items[trace.id] = trace
    return traces


def traces_to_list(traces: Traces) -> list:
    return [
        {
            "id": t.id,
            "type": t.type,
            "key": t.key,
            "strength": t.strength,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "active": t.active,
            "payload": dict(t.payload),
        }
        for t in traces.items.values()
    ]


def traces_from_list(data: list) -> Traces:
    traces = create_traces()
    for item in data:
        trace = Trace(
            id=item["id"],
            type=item["type"],
            key=item["key"],
            strength=float(item.get("strength", 0.0)),
            created_at=int(item.get("created_at", 0)),
            updated_at=int(item.get("updated_at", 0)),
            active=bool(item.get("active", True)),
            payload=dict(item.get("payload", {})),
        )
        traces.items[trace.id] = trace
    return traces


def journal_to_list(journal: Journal) -> list:
    return [
        {"tick": e.tick, "kind": e.kind, "payload": dict(e.payload)}
        for e in journal.events
    ]


def journal_from_list(data: list) -> List[Event]:
    return [
        Event(tick=int(e["tick"]), kind=e["kind"], payload=dict(e.get("payload", {})))
        for e in data
    ]


def _validate_backup_dict(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("backup is not an object")
    character = data.get("character")
    world = data.get("world")
    if not isinstance(character, dict):
        raise ValueError("backup has no character")
    if not isinstance(world, dict):
        raise ValueError("backup has no world")
    for key in ("id", "tick", "voices", "resources"):
        if key not in character:
            raise ValueError(f"character missing {key}")
    for key in ("tick", "current_location", "locations", "npcs", "windows"):
        if key not in world:
            raise ValueError(f"world missing {key}")


def save_events(conn: sqlite3.Connection, journal: Journal, tick: int) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE tick = ?", (tick,))
    now = _now()
    for event in journal.events:
        if event.tick != tick:
            continue
        cur.execute(
            "INSERT INTO events (tick, kind, payload, created_at) VALUES (?, ?, ?, ?)",
            (
                int(event.tick),
                event.kind,
                json.dumps(event.payload, ensure_ascii=False),
                now,
            ),
        )
    conn.commit()


def load_events(conn: sqlite3.Connection, since_tick: int = 0) -> List[Event]:
    cur = conn.cursor()
    cur.execute(
        "SELECT tick, kind, payload FROM events WHERE tick >= ? ORDER BY tick",
        (int(since_tick),),
    )
    result: List[Event] = []
    for row in cur.fetchall():
        payload = json.loads(row["payload"]) if row["payload"] else {}
        result.append(Event(tick=int(row["tick"]), kind=row["kind"], payload=payload))
    return result


def save_player_input(conn: sqlite3.Connection, kind: str, payload: dict, effect: dict) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO player_input (kind, payload, created_at, effect) VALUES (?, ?, ?, ?)",
        (
            kind,
            json.dumps(payload, ensure_ascii=False),
            _now(),
            json.dumps(effect, ensure_ascii=False),
        ),
    )
    conn.commit()


def character_to_dict(character: Character) -> dict:
    return {
        "id": character.id,
        "tick": character.tick,
        "temperature": character.temperature,
        "location": character.location,
        "resources": dict(character.resources),
        "cooldowns": dict(character.cooldowns),
        "voices": {
            name: {
                "weight": v.weight,
                "baseline": v.baseline,
                "sensitivity": v.sensitivity,
                "memory": v.memory,
                "links": dict(v.links),
            }
            for name, v in character.voices.items()
        },
        "player": {
            "interventions": list(character.player.interventions),
            "obedience_history": list(character.player.obedience_history),
            "presence_ticks": character.player.presence_ticks,
            "absences": character.player.absences,
            "last_seen_tick": character.player.last_seen_tick,
            "action_cost_modifiers": dict(character.player.action_cost_modifiers),
            "voice_bias": dict(character.player.voice_bias),
        },
    }


def dict_to_character(data: dict) -> Character:
    character = create_character(
        data.get("id", "default"),
        data.get("temperature", 0.4),
    )
    character.tick = data.get("tick", 0)
    character.location = data.get("location", "home")
    character.resources = dict(data.get("resources", character.resources))
    character.cooldowns = dict(data.get("cooldowns", {}))

    voices_data = data.get("voices")
    if voices_data:
        character.voices = {}
        for name, vd in voices_data.items():
            character.voices[name] = Voice(
                name=name,
                weight=vd.get("weight", 0.0),
                baseline=vd.get("baseline", 0.0),
                sensitivity=vd.get("sensitivity", 0.5),
                memory=vd.get("memory", 0.0),
                links=dict(vd.get("links", {})),
            )

    player_data = data.get("player")
    if player_data:
        character.player = PlayerState(
            interventions=list(player_data.get("interventions", [])),
            obedience_history=list(player_data.get("obedience_history", [])),
            presence_ticks=player_data.get("presence_ticks", 0),
            absences=player_data.get("absences", 0),
            last_seen_tick=player_data.get("last_seen_tick", 0),
            action_cost_modifiers=dict(player_data.get("action_cost_modifiers", {})),
            voice_bias=dict(player_data.get("voice_bias", {})),
        )

    return character


def world_to_dict(world: World) -> dict:
    return {
        "tick": world.tick,
        "current_location": world.current_location,
        "locations": {
            loc_id: {
                "id": loc.id,
                "name": loc.name,
                "actions_available": list(loc.actions_available),
                "npcs": list(loc.npcs),
            }
            for loc_id, loc in world.locations.items()
        },
        "npcs": {
            npc_id: {
                "id": npc.id,
                "name": npc.name,
                "location": npc.location,
                "relation": npc.relation,
                "expectations": list(npc.expectations),
                "memory": list(npc.memory),
            }
            for npc_id, npc in world.npcs.items()
        },
        "windows": [
            {
                "id": w.id,
                "action_id": w.action_id,
                "location": w.location,
                "opens_at": w.opens_at,
                "closes_at": w.closes_at,
                "reward": dict(w.reward),
                "miss_penalty": dict(w.miss_penalty),
                "used": w.used,
                "missed": w.missed,
            }
            for w in world.windows
        ],
    }


def dict_to_world(data: dict) -> World:
    world = create_world(data.get("tick", 0))
    world.tick = data.get("tick", 0)
    world.current_location = data.get("current_location", "home")

    locations_data = data.get("locations")
    if locations_data:
        world.locations = {}
        for loc_id, ld in locations_data.items():
            world.locations[loc_id] = Location(
                id=ld.get("id", loc_id),
                name=ld.get("name", loc_id),
                actions_available=list(ld.get("actions_available", [])),
                npcs=list(ld.get("npcs", [])),
            )

    npcs_data = data.get("npcs")
    if npcs_data:
        world.npcs = {}
        for npc_id, nd in npcs_data.items():
            world.npcs[npc_id] = NPC(
                id=nd.get("id", npc_id),
                name=nd.get("name", npc_id),
                location=nd.get("location", ""),
                relation=nd.get("relation", 0.5),
                expectations=list(nd.get("expectations", [])),
                memory=list(nd.get("memory", [])),
            )

    windows_data = data.get("windows", [])
    world.windows = []
    for wd in windows_data:
        world.windows.append(
            Window(
                id=wd["id"],
                action_id=wd["action_id"],
                location=wd["location"],
                opens_at=wd["opens_at"],
                closes_at=wd["closes_at"],
                reward=dict(wd.get("reward", {})),
                miss_penalty=dict(wd.get("miss_penalty", {})),
                used=wd.get("used", False),
                missed=wd.get("missed", False),
            )
        )

    return world


def backup_to_json(character: Character, world: World, backup_path: str) -> None:
    p = Path(backup_path)
    parent = p.parent
    if str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    data = {
        "character": character_to_dict(character),
        "world": world_to_dict(world),
        "traces": traces_to_list(character.traces),
        "journal": journal_to_list(character.journal),
        "created_at": _now(),
    }
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_backup(path: str) -> tuple:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _validate_backup_dict(data)
    character = dict_to_character(data["character"])
    world = dict_to_world(data["world"])
    if "traces" in data:
        character.traces = traces_from_list(data["traces"])
    if "journal" in data:
        character.journal.events = journal_from_list(data["journal"])
    return character, world
