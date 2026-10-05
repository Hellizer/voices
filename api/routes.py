from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from sim.player import INTERVENTION_TYPES, ENVIRONMENT_TYPES

router = APIRouter()


class InterveneBody(BaseModel):
    type: str
    target: str
    intensity: Optional[float] = None


class EnvironmentBody(BaseModel):
    type: str
    payload: dict = {}


@router.get("/state")
async def get_state(request: Request):
    runtime = request.app.state.runtime
    return runtime.snapshot()


@router.get("/events")
async def get_events(request: Request, since: int = 0):
    runtime = request.app.state.runtime
    return {"events": runtime.events_since(since)}


@router.post("/intervene")
async def post_intervene(request: Request, body: InterveneBody):
    if body.type not in INTERVENTION_TYPES:
        raise HTTPException(status_code=400, detail="unknown intervention type")
    runtime = request.app.state.runtime
    result = await runtime.intervene(body.type, body.target, body.intensity)
    return {"ok": True, **result}


@router.post("/environment")
async def post_environment(request: Request, body: EnvironmentBody):
    if body.type not in ENVIRONMENT_TYPES:
        raise HTTPException(status_code=400, detail="unknown environment type")
    runtime = request.app.state.runtime
    await runtime.environment(body.type, body.payload)
    return {"ok": True}


@router.post("/tick")
async def post_tick(request: Request):
    runtime = request.app.state.runtime
    result = await runtime.do_tick()
    return {
        "ok": True,
        "tick": result.tick,
        "action_id": result.action_id,
        "action_group": result.action_group,
        "crisis": result.crisis,
    }


@router.get("/backups")
async def get_backups(request: Request):
    runtime = request.app.state.runtime
    return {"backups": runtime.backups()}


@router.post("/backup")
async def post_backup(request: Request):
    runtime = request.app.state.runtime
    path = await runtime.make_backup_now()
    return {"ok": True, "path": path}
