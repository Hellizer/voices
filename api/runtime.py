# voices/api/runtime.py
import asyncio
import datetime
import json
import random
import sqlite3
from pathlib import Path
from typing import Callable, Awaitable, Optional, Any

import yaml

from sim.character import Character, create_character, snapshot as character_snapshot
from sim.world import World, create_world, snapshot as world_snapshot
from sim.loop import simulation_tick, TickResult
from sim.player import (
    Intervention,
    EnvironmentChange,
    apply_intervention,
    apply_environment,
)
from storage.repository import (
    init_db,
    load_character,
    load_world,
    load_traces,
    load_events,
    save_character,
    save_world,
    save_traces,
    save_events,
)
from storage.backups import (
    BackupConfig,
    create_config,
    alternate_backup,
    load_best_backup,
    list_all as backups_list_all,
)

BroadcastFn = Callable[[dict], Awaitable[None]]


def _tick_result_to_dict(result: Optional[TickResult]) -> Optional[dict]:
    if result is None:
        return None
    return {
        "tick": result.tick,
        "action_id": result.action_id,
        "action_group": result.action_group,
        "crisis": result.crisis,
        "mutations": list(result.mutations),
        "expired_windows": list(result.expired_windows),
        "events": list(result.events),
    }


class Runtime:
    def __init__(self, config_path: str) -> None:
        self.config_path = str(config_path)
        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        self.cfg = {
            "tick": raw.get("tick", {}) or {},
            "simulation": raw.get("simulation", {}) or {},
            "storage": raw.get("storage", {}) or {},
            "player": raw.get("player", {}) or {},
            "world": raw.get("world", {}) or {},
        }

        seed = self.cfg["simulation"].get("seed")
        if seed is not None:
            random.seed(int(seed))

        self.base_dir = Path(self.config_path).resolve().parent

        self.temperature = float(self.cfg["simulation"].get("temperature", 0.4))
        self.choice_delta = float(self.cfg["simulation"].get("choice_delta", 0.08))

        storage_cfg = self.cfg["storage"]
        db_path = storage_cfg.get("db_path", "./state.db")
        backup_dir = storage_cfg.get("backup_dir", "./backups")

        db_path_p = Path(db_path)
        if not db_path_p.is_absolute():
            db_path_p = self.base_dir / db_path_p
        self.db_path = str(db_path_p)

        backup_dir_p = Path(backup_dir)
        if not backup_dir_p.is_absolute():
            backup_dir_p = self.base_dir / backup_dir_p
        self.backup_dir = str(backup_dir_p)

        self.backup_config: BackupConfig = create_config(self.backup_dir)

        self.conn = None
        self.character = None
        self.world = None

        if not self._try_load_from_db():
            if not self._restore_from_backup():
                try:
                    if Path(self.db_path).exists():
                        Path(self.db_path).unlink()
                except OSError:
                    pass
                self.conn = init_db(self.db_path)
                self.character = create_character(
                    "default", self.temperature, self.choice_delta
                )
                self.world = create_world(0)

        self.subscribers: list[BroadcastFn] = []
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()
        self.last_result: Optional[TickResult] = None
        self.ws_count: int = 0

    def _try_load_from_db(self):
        """Пытается загрузить из БД. Возвращает True при успехе."""
        try:
            self.conn = init_db(self.db_path)
            loaded_character = load_character(self.conn, "default")
            loaded_world = load_world(self.conn, "default")
            loaded_traces = load_traces(self.conn)
            loaded_events = load_events(self.conn, 0)
        except (sqlite3.DatabaseError, sqlite3.OperationalError, ValueError, OSError):
            return False
        self.character = loaded_character or create_character(
            "default", self.temperature, self.choice_delta
        )
        self.world = loaded_world or create_world(0)
        self.character.traces = loaded_traces
        self.character.journal.events = loaded_events
        return True

    def _restore_from_backup(self) -> bool:
        result = load_best_backup(self.backup_config)
        if result is None:
            return False
        character, world = result
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        db_file = Path(self.db_path)
        if db_file.exists():
            broken_path = db_file.with_suffix(db_file.suffix + ".broken")
            try:
                if broken_path.exists():
                    broken_path.unlink()
            except OSError:
                pass
            try:
                db_file.rename(broken_path)
            except OSError:
                try:
                    db_file.unlink()
                except OSError:
                    pass
        self.conn = init_db(self.db_path)
        self.character = character
        self.world = world
        return True

    def subscribe(self, fn: BroadcastFn) -> None:
        self.subscribers.append(fn)

    def unsubscribe(self, fn: BroadcastFn) -> None:
        try:
            self.subscribers.remove(fn)
        except ValueError:
            pass

    def _format_message(self, key: str) -> str:
        g = getattr(self.character, "gender", "female")
        if g == "male":
            return {
                "heard": "он услышал",
                "ignored": "он проигнорировал",
                "wrong": "он ответил не то, что ты просил",
            }.get(key, "")
        return {
            "heard": "она услышала",
            "ignored": "она проигнорировала",
            "wrong": "она ответила не то, что ты просил",
        }.get(key, "")

    def on_ws_connect(self) -> None:
        self.ws_count += 1

    def on_ws_disconnect(self) -> None:
        if self.ws_count > 0:
            self.ws_count -= 1

    async def _broadcast(self, payload: dict) -> None:
        for fn in list(self.subscribers):
            try:
                await fn(payload)
            except Exception:
                continue

    def tick_interval_seconds(self) -> float:
        minutes = float(self.cfg["tick"].get("real_minutes_per_game_hour", 10))
        return minutes * 60.0

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.tick_interval_seconds()
                )
                break
            except asyncio.TimeoutError:
                pass
            try:
                await self.do_tick()
            except Exception:
                continue

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._persist)

    async def do_tick(self) -> TickResult:
        async with self._lock:
            result = simulation_tick(
                self.character,
                self.world,
                player_present=(self.ws_count > 0),
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._persist)
            await loop.run_in_executor(None, self._backup)
            self.last_result = result

            await self._broadcast(
                {
                    "type": "tick",
                    "tick": result.tick,
                    "action_id": result.action_id,
                    "action_group": result.action_group,
                }
            )
            if result.crisis:
                await self._broadcast(
                    {
                        "type": "crisis",
                        "tick": result.tick,
                        "mutations": result.mutations,
                    }
                )
            if result.mutations:
                await self._broadcast(
                    {
                        "type": "trace",
                        "tick": result.tick,
                        "mutations": result.mutations,
                    }
                )
            if result.expired_windows:
                await self._broadcast(
                    {
                        "type": "world_change",
                        "tick": result.tick,
                        "expired_windows": result.expired_windows,
                    }
                )
            return result

    def _persist(self) -> None:
        save_character(self.conn, self.character)
        save_world(self.conn, self.world)
        save_traces(self.conn, self.character.traces)
        save_events(self.conn, self.character.journal, self.character.tick)

    def _backup(self) -> None:
        try:
            alternate_backup(self.character, self.world, self.backup_config)
        except Exception:
            pass

    def snapshot(self) -> dict:
        return {
            "character": character_snapshot(self.character),
            "world": world_snapshot(self.world),
            "last_result": _tick_result_to_dict(self.last_result),
        }

    async def intervene(
        self,
        intervention_type: str,
        target: str,
        intensity: Optional[float] = None,
    ) -> dict:
        async with self._lock:
            if intensity is None:
                intensity = float(
                    self.cfg["player"].get("default_intensity", 0.2)
                )
            intervention = Intervention(
                type=intervention_type,
                target=target,
                intensity=float(intensity),
            )
            result = apply_intervention(
                self.character.player,
                self.character.voices,
                self.character.traces,
                self.character.journal,
                intervention,
                self.character.tick,
            )
            result["message"] = self._format_message(result.get("message_key", ""))
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._persist)
            await self._broadcast(
                {
                    "type": "intervention_result",
                    "tick": self.character.tick,
                    "intervention_type": intervention.type,
                    "target": target,
                    **result,
                }
            )
            return result

    async def environment(self, env_type: str, payload: dict) -> dict:
        async with self._lock:
            env = EnvironmentChange(type=env_type, payload=dict(payload))
            apply_environment(
                self.character.player,
                self.character.voices,
                env,
                self.character.tick,
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._persist)
            return {"ok": True}

    async def character_init(self, name: str, gender: str) -> dict:
        async with self._lock:
            self.character.name = name.strip()
            self.character.gender = gender
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._persist)
            return {
                "ok": True,
                "name": self.character.name,
                "gender": self.character.gender,
            }

    async def make_backup_now(self) -> str:
        async with self._lock:
            loop = asyncio.get_event_loop()
            path = await loop.run_in_executor(
                None,
                lambda: alternate_backup(self.character, self.world, self.backup_config),
            )
            return path

    def backups(self) -> list:
        return backups_list_all(self.backup_config)

    def events_since(self, tick: int) -> list[dict]:
        result = []
        for event in self.character.journal.events:
            if event.tick >= tick:
                result.append(
                    {
                        "tick": event.tick,
                        "kind": event.kind,
                        "payload": dict(event.payload),
                    }
                )
        return result
