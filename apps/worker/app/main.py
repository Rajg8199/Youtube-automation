"""FastAPI internal API for the PhoneWala Gyan worker.

Phase 0 surface:
  GET  /health         -> liveness + DB connectivity (acceptance criterion)
  POST /jobs/{agent}   -> contract stub for the n8n -> worker handoff (501 until wired)
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from . import __version__
from .config import get_settings
from .db import ping

app = FastAPI(title="PhoneWala Gyan Worker", version=__version__)

# Agents that will own /jobs/{agent} endpoints across Phases 1-5.
KNOWN_AGENTS: frozenset[str] = frozenset(
    {
        "trend_scout",
        "topic_scorer",
        "editorial_planner",
        "research_compiler",
        "script_writer",
        "qa",
        "voice_producer",
        "visual_director",
        "render_worker",
        "thumbnail_designer",
        "seo_optimizer",
        "publisher",
        "analytics_analyst",
        "growth_strategist",
        "orchestrator",
    }
)


@app.get("/health")
def health() -> JSONResponse:
    settings = get_settings()
    db_ok = False
    try:
        db_ok = ping()
    except Exception:  # noqa: BLE001 - report rather than crash the probe
        db_ok = False

    status = "ok" if db_ok else "degraded"
    code = 200 if db_ok else 503
    return JSONResponse(
        status_code=code,
        content={
            "status": status,
            "version": __version__,
            "stack_tier": settings.stack_tier,
            "db": "up" if db_ok else "down",
        },
    )


@app.post("/jobs/{agent}")
def run_job(agent: str, payload: dict[str, Any] | None = None) -> Any:
    if agent not in KNOWN_AGENTS:
        raise HTTPException(status_code=404, detail=f"unknown agent: {agent}")
    # Phase 0: contract exists, logic lands in later phases.
    raise HTTPException(
        status_code=501,
        detail=f"agent '{agent}' not implemented yet (Phase 0 stub)",
    )
