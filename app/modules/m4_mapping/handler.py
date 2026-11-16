"""M4 入口：字段映射页与映射接口。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app import web
from app.modules.m4_mapping import rename

router = APIRouter()


@router.get("/mapping", response_class=HTMLResponse)
def mapping_page(request: Request, run_id: str | None = None):
    run = web.pick_run(run_id)
    payload = (run or {}).get("mapping") or {}
    chain = (run or {}).get("rename_chain") or []
    return web.page_or_404(
        request,
        "mapping.html",
        "mapping",
        run,
        run_id=run_id,
        mapping=payload,
        stats=payload.get("stats") or {},
        aliases=payload.get("aliases") or [],
        chain_hops=chain,
        chain_paths=rename.chain_paths(chain),
    )


@router.get("/api/mapping")
def mapping_api(run_id: str | None = None):
    run = web.pick_run(run_id)
    if not run:
        return {"run_id": None, "rows": [], "stats": {}, "aliases": [],
                "rename_chain": []}
    payload = run.get("mapping") or {}
    return {
        "run_id": run["run_id"],
        "stats": payload.get("stats") or {},
        "rows": payload.get("rows") or [],
        "aliases": payload.get("aliases") or [],
        "conflicts": payload.get("conflicts") or [],
        "added": payload.get("added") or [],
        "deleted": payload.get("deleted") or [],
        "rename_chain": run.get("rename_chain") or [],
    }
