import pathlib
from contextlib import asynccontextmanager

import orjson
import uvicorn
from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import RUNTIME_DIR, BUILD_LOGS_DIR, DIST_BUILD_DIR
from .db import get_db
from .models import Build

state = {}

LAST_COMMIT_JSON = RUNTIME_DIR / "last-commit.json"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if LAST_COMMIT_JSON.exists():
        state["commit"] = orjson.loads(LAST_COMMIT_JSON.read_text())
    else:
        state["commit"] = {}

    with next(get_db()) as session:
        rows = session.execute(
            select(
                Build.attrpath,
                Build.hydra_id,
                Build.tag,
                Build.error_line_number,
                Build.last_success_rev,
                Build.last_success_date,
            ).where(Build.tag != "success")
        ).all()

    state["builds"] = []
    state["search"] = {}

    for b in rows:
        logfile = pathlib.Path(RUNTIME_DIR / "build-logs") / f"{b.attrpath}.log"

        state["search"][b.attrpath] = logfile.read_bytes().decode(
            errors="ignore"
        )

        state["builds"].append(
            {
                "attrpath": b.attrpath,
                "hydra_id": b.hydra_id,
                "tag": b.tag,
                "error_line_number": b.error_line_number,
                "last_success_rev": b.last_success_rev,
                "last_success_date": b.last_success_date,
            }
        )

    print("Loaded", len(state["builds"]), "builds into the state")

    yield
    state.clear()


app = FastAPI(lifespan=lifespan)
app.mount("/build-logs", StaticFiles(directory=BUILD_LOGS_DIR))


@app.get("/api/builds")
async def list_builds() -> Response:
    return Response(
        orjson.dumps({"commit": state["commit"], "builds": state["builds"]}),
        media_type="application/json",
    )


@app.get("/api/search")
def search_logs(q: str = Query(..., min_length=3, max_length=100)):
    return [
        attrpath
        for attrpath, content in state["search"].items()
        if q in content
    ]


def main():
    app.mount("/", StaticFiles(directory=DIST_BUILD_DIR, html=True))

    uvicorn.run(app, host="0.0.0.0", port=8080)
