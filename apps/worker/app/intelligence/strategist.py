"""Growth Strategist: a weekly, evidence-linked report + recommendations.

Deterministic by default (aggregates the week's data + learned priors + insights) so it runs
at $0 and needs no LLM quota; the report markdown is written under /media/reports and the
recommendations land in the recommendations board.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..production.media import media_dir, rel_path
from .learning import category_priors

COMPONENT = "service:growth_strategist"


def _gather() -> dict[str, Any]:
    since = (date.today() - timedelta(days=7)).isoformat()
    with cursor() as cur:
        cur.execute("select count(*) as n from youtube_videos where published_at >= %s", (since,))
        published = cur.fetchone()["n"]
        cur.execute(
            """
            select ci.working_title, m.views, m.avg_pct_viewed::float8 as avg_pct
            from youtube_videos yv
            join content_items ci on ci.id = yv.content_item_id
            left join lateral (
                select views, avg_pct_viewed from video_metrics_daily d
                where d.youtube_video_id = yv.youtube_video_id order by date desc limit 1
            ) m on true
            order by m.views desc nulls last limit 5
            """
        )
        top = cur.fetchall()
        cur.execute(
            "select insight from insights where actionable = true order by created_at desc limit 8"
        )
        insights = [r["insight"] for r in cur.fetchall()]
    return {"published": published, "top": top, "insights": insights, "priors": category_priors()}


def _report_md(data: dict[str, Any]) -> str:
    today = date.today().isoformat()
    lines = [f"# PhoneWala Gyan — Weekly Report ({today})", ""]
    lines.append(f"**Videos published (7d):** {data['published']}")
    lines.append("")
    if data["top"]:
        lines.append("## Top performers")
        for t in data["top"]:
            v = t["views"] or 0
            ap = f"{round(t['avg_pct'])}%" if t["avg_pct"] is not None else "—"
            lines.append(f"- {t['working_title']} — {v} views, {ap} avg viewed")
        lines.append("")
    if data["priors"]:
        lines.append("## Category performance (learned priors)")
        for cat, score in sorted(data["priors"].items(), key=lambda kv: -kv[1]):
            lines.append(f"- **{cat}**: {score:.0%}")
        lines.append("")
    if data["insights"]:
        lines.append("## Insights")
        lines += [f"- {i}" for i in data["insights"]]
        lines.append("")
    return "\n".join(lines)


def _recommendations(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    recs: list[tuple[str, str, str]] = []
    priors = data["priors"]
    if priors:
        best = max(priors, key=priors.get)
        worst = min(priors, key=priors.get)
        recs.append(("topic", f"Double down on '{best}' content",
                     f"'{best}' has the highest learned performance ({priors[best]:.0%}). Schedule more of it next week."))
        if priors[worst] < 0.4:
            recs.append(("topic", f"Cut back on '{worst}' content",
                         f"'{worst}' underperforms ({priors[worst]:.0%}); reallocate slots to stronger categories."))
    recs.append(("format", "Derive shorts from every long video",
                 "Shorts feed reach is cheap to capture; auto-derive 9:16 cuts from each long upload."))
    return recs


def run_growth_strategist(*, limit: int = 0) -> dict[str, Any]:
    data = _gather()
    md = _report_md(data)
    reports_dir = os.path.join(media_dir(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, f"weekly_{date.today().isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)

    recs = _recommendations(data)
    with cursor() as cur:
        for rtype, title, detail in recs:
            cur.execute(
                "insert into recommendations (type, title, detail, status) values (%s, %s, %s, 'proposed')",
                (rtype, title, detail),
            )
    summary = {"report": rel_path(path), "recommendations": len(recs),
               "published_7d": data["published"]}
    log_system_event(severity="info", component=COMPONENT, message="growth strategist run complete",
                     detail=summary)
    return summary
