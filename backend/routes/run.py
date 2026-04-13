"""Pipeline run endpoints: POST /api/run, SSE stream, downloads, status."""

from __future__ import annotations

import asyncio
import json
import queue
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..jobs import RUNS, RunState, run_output_dir
from ..pipeline_wrapper import execute, make_emitter

router = APIRouter(prefix="/api", tags=["run"])

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    mode: Literal["csv_only", "api_discovery", "csv_plus_api"]
    dry_run: bool = True
    enrich: bool = False
    use_master_persona: bool = True
    master_persona_path: str = "MASTER.md"
    voice_profile_path: str = "data/voice_profile.json"
    few_shot_k: int = 3
    min_qualification_score: int = 60
    min_fit_score_for_enrich: int = 65
    referral_advocates_only: bool = True
    state: str = "CO"
    prospect_sources: list[str] = Field(default_factory=lambda: ["hunter"])
    prospect_limit: int = 25
    hunter_domains: list[str] = Field(default_factory=list)
    min_ebitda: int = 0
    csv_file_ids: list[str] = Field(default_factory=list)
    icp_overrides: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------


@router.post("/uploads")
async def upload_files(files: list[UploadFile] = File(...)) -> dict[str, list[str]]:
    file_ids: list[str] = []
    for upload in files:
        file_id = uuid.uuid4().hex[:12]
        dest = UPLOAD_DIR / f"{file_id}.csv"
        with dest.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        file_ids.append(file_id)
    return {"file_ids": file_ids}


def _paths_for_ids(file_ids: list[str]) -> list[str]:
    paths: list[str] = []
    for file_id in file_ids:
        if file_id == "sample":
            sample = Path("data/sample_contacts.csv")
            if sample.exists():
                paths.append(str(sample))
            continue
        p = UPLOAD_DIR / f"{file_id}.csv"
        if p.exists():
            paths.append(str(p))
    return paths


# ---------------------------------------------------------------------------
# Run execution
# ---------------------------------------------------------------------------


def _run_in_thread(state: RunState, payload: RunRequest) -> None:
    out_dir = run_output_dir(state.run_id)
    output_csv = out_dir / "campaign_ready.csv"
    instantly_csv = out_dir / "instantly_campaign.csv"
    emit = make_emitter(state.event_queue)
    state.status = "running"

    try:
        csv_paths = _paths_for_ids(payload.csv_file_ids)
        _count, report = execute(
            run_id=state.run_id,
            mode=payload.mode,
            csv_paths=csv_paths,
            output_path=str(output_csv),
            instantly_path=str(instantly_csv),
            dry_run=payload.dry_run,
            enrich=payload.enrich,
            use_master_persona=payload.use_master_persona,
            master_persona_path=payload.master_persona_path,
            voice_profile_path=payload.voice_profile_path,
            few_shot_k=payload.few_shot_k,
            min_qualification_score=payload.min_qualification_score,
            min_fit_score_for_enrich=payload.min_fit_score_for_enrich,
            referral_advocates_only=payload.referral_advocates_only,
            state=payload.state,
            prospect_sources=payload.prospect_sources,
            prospect_limit=payload.prospect_limit,
            hunter_domains=payload.hunter_domains,
            min_ebitda=payload.min_ebitda,
            icp_overrides=payload.icp_overrides,
            emit=emit,
        )
        state.report = report.to_dict()
        state.output_csv = str(output_csv)
        state.instantly_csv = str(instantly_csv)
        state.status = "done"
        emit(
            "done",
            {
                "run_id": state.run_id,
                "report": state.report,
                "output_csv": f"/api/runs/{state.run_id}/csv",
                "instantly_csv": f"/api/runs/{state.run_id}/instantly",
            },
        )
    except Exception as e:
        state.status = "error"
        state.error = str(e)
        emit("error", {"message": str(e)})
    finally:
        state.finished_at = time.time()
        # Sentinel so the SSE consumer stops draining.
        state.event_queue.put(None)


@router.post("/run")
def start_run(payload: RunRequest) -> dict[str, str]:
    state = RUNS.create()
    thread = threading.Thread(target=_run_in_thread, args=(state, payload), daemon=True)
    thread.start()
    return {
        "run_id": state.run_id,
        "stream_url": f"/api/runs/{state.run_id}/stream",
    }


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------


async def _event_generator(state: RunState):
    loop = asyncio.get_event_loop()
    q: queue.Queue = state.event_queue
    while True:
        item = await loop.run_in_executor(None, q.get)
        if item is None:
            break
        yield {
            "event": item["event"],
            "data": json.dumps(item["data"]),
        }
        if item["event"] in ("done", "error"):
            # Drain any residual events in case more arrive before sentinel.
            continue


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    state = RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    return EventSourceResponse(_event_generator(state))


# ---------------------------------------------------------------------------
# Downloads + status
# ---------------------------------------------------------------------------


@router.get("/runs/{run_id}/csv")
def download_csv(run_id: str) -> FileResponse:
    state = RUNS.get(run_id)
    if state is None or not state.output_csv:
        raise HTTPException(status_code=404, detail="csv not ready")
    path = Path(state.output_csv)
    if not path.exists():
        raise HTTPException(status_code=404, detail="csv file missing")
    return FileResponse(str(path), media_type="text/csv", filename="campaign_ready.csv")


@router.get("/runs/{run_id}/instantly")
def download_instantly(run_id: str) -> FileResponse:
    state = RUNS.get(run_id)
    if state is None or not state.instantly_csv:
        raise HTTPException(status_code=404, detail="instantly csv not ready")
    path = Path(state.instantly_csv)
    if not path.exists():
        raise HTTPException(status_code=404, detail="instantly csv missing")
    return FileResponse(
        str(path), media_type="text/csv", filename="instantly_campaign.csv"
    )


@router.get("/runs/{run_id}/report")
def get_report(run_id: str) -> dict[str, Any]:
    state = RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    if state.report is None:
        raise HTTPException(
            status_code=409, detail=f"report not available (status={state.status})"
        )
    return state.report


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    state = RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": state.run_id,
        "status": state.status,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
        "error": state.error,
        "report": state.report,
        "output_csv": (f"/api/runs/{state.run_id}/csv" if state.output_csv else None),
        "instantly_csv": (
            f"/api/runs/{state.run_id}/instantly" if state.instantly_csv else None
        ),
    }
