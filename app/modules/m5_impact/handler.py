"""M5 入口：影响面页与影响面接口。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app import web
from app.modules.m5_impact.sql_lineage import extract_edges, reverse_impact

router = APIRouter()


@router.get("/impact", response_class=HTMLResponse)
def impact_page(request: Request, run_id: str | None = None):
    run = web.pick_run(run_id)
    payload = (run or {}).get("impact") or {}
    resolution = (run or {}).get("resolution") or {}
    return web.page_or_404(
        request,
        "impact.html",
        "impact",
        run,
        run_id=run_id,
        graph=payload.get("impact") or {},
        cycles=payload.get("cycles") or {},
        one_sided=payload.get("one_sided") or [],
        broken=payload.get("broken") or [],
        aliased=resolution.get("aliased") or [],
        summary=payload.get("summary") or {},
    )


@router.get("/api/impact")
def impact_api(run_id: str | None = None):
    run = web.pick_run(run_id)
    if not run:
        return {"run_id": None, "impact": {}, "summary": {}}
    payload = run.get("impact") or {}
    resolution = run.get("resolution") or {}
    return {
        "run_id": run["run_id"],
        "impact": payload.get("impact") or {},
        "cycles": payload.get("cycles") or {},
        "one_sided": payload.get("one_sided") or [],
        "broken": payload.get("broken") or [],
        "aliased": resolution.get("aliased") or [],
        "summary": payload.get("summary") or {},
    }


@router.post("/api/lineage")
def lineage_api(payload: dict):
    result = extract_edges(payload.get("expressions") or [])
    result["affected"] = reverse_impact(result["edges"], payload.get("changed") or [])
    return result
