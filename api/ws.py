import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    runtime = websocket.app.state.runtime
    runtime.on_ws_connect()

    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(payload: dict) -> None:
        await queue.put(payload)

    runtime.subscribe(on_event)

    await websocket.send_json({"type": "hello", "tick": runtime.character.tick})

    async def sender() -> None:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)

    sender_task = asyncio.create_task(sender())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        runtime.on_ws_disconnect()
        runtime.unsubscribe(on_event)
        sender_task.cancel()
        try:
            await sender_task
        except asyncio.CancelledError:
            pass
