"""Phase 2 script-factory runner: plan -> compile -> (write -> QA) with a revision cap.

Each sub-job is idempotent over its input statuses, so the pipeline is just an ordered
sequence with the write/QA pair repeated up to `revisions` extra times (the revise loop).
"""

from __future__ import annotations

from typing import Any

from .context import AgentContext
from .editorial_planner import run_editorial_planner
from .qa import run_qa
from .research_compiler import run_research_compiler
from .script_writer import run_script_writer


def run_script_pipeline(
    ctx: AgentContext, *, limit: int = 50, revisions: int = 2
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "editorial_planner": run_editorial_planner(ctx, limit=limit),
        "research_compiler": run_research_compiler(ctx, limit=limit),
        "rounds": [],
    }
    for _ in range(revisions + 1):  # initial draft + N revisions
        writer = run_script_writer(ctx, limit=limit)
        qa = run_qa(ctx, limit=limit)
        out["rounds"].append({"writer": writer, "qa": qa})
        if writer["scripts_written"] == 0:  # nothing left to draft or revise
            break
    return out
