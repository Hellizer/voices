import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.runtime import Runtime
from api.routes import router
from api.ws import ws_router

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"

runtime = Runtime(str(CONFIG_PATH))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = runtime
    await runtime.start()
    yield
    await runtime.stop()


class StaticFilesNoCache(StaticFiles):
    MIME_MAP = {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }

    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        ext = os.path.splitext(str(full_path))[1].lower()
        if ext in self.MIME_MAP:
            response.headers["content-type"] = self.MIME_MAP[ext]
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.include_router(ws_router)

app.mount(
    "/",
    StaticFilesNoCache(directory=BASE_DIR / "frontend", html=True),
    name="frontend",
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
