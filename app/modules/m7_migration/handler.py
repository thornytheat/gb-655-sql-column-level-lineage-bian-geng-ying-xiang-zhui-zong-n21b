"""M7 入口：迁移单页与导出物。

页面与导出都认 run_id：回看哪一批，页面、Markdown、CSV、清单就都是那一版。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app import errors, web
from app.modules.m7_migration import service

router = APIRouter()


def _run_or_404(run_id: str | None) -> dict:
    run = web.pick_run(run_id)
    if run is None:
        raise errors.NotFound("还没有批次，先在版本历史页跑一次")
    return run


def _download(body: str, media_type: str, filename: str) -> Response:
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv(body: str, filename: str) -> Response:
    return _download(body, "text/csv; charset=utf-8", filename)


@router.get("/spec", response_class=HTMLResponse)
def spec_page(request: Request, run_id: str | None = None):
    run = web.pick_run(run_id)
    return web.page_or_404(
        request,
        "spec.html",
        "spec",
        run,
        run_id=run_id,
        clauses=service.clauses(run) if run else [],
        ledger=(run or {}).get("ledger") or {},
        aliases=((run or {}).get("mapping") or {}).get("aliases") or [],
        warnings=(run or {}).get("warnings") or [],
    )


@router.get("/api/export/evidence.csv")
def export_evidence(run_id: str | None = None):
    run = _run_or_404(run_id)
    return _csv(service.fields_csv_text(run),
                f"lineageguard-evidence-{run['run_id']}.csv")


@router.get("/api/export/spec.md")
def export_spec_md(run_id: str | None = None):
    run = _run_or_404(run_id)
    return _download(service.spec_markdown(run), "text/markdown; charset=utf-8",
                     f"lineageguard-spec-{run['run_id']}.md")


@router.get("/api/export/fields.csv")
def export_fields_csv(run_id: str | None = None):
    run = _run_or_404(run_id)
    return _csv(service.fields_csv_text(run),
                f"lineageguard-fields-{run['run_id']}.csv")


@router.get("/api/export/refs.csv")
def export_refs_csv(run_id: str | None = None):
    run = _run_or_404(run_id)
    return _csv(service.refs_csv_text(run),
                f"lineageguard-refs-{run['run_id']}.csv")


@router.get("/api/export/ledger.csv")
def export_ledger_csv(run_id: str | None = None):
    run = _run_or_404(run_id)
    return _csv(service.ledger_csv_text(run),
                f"lineageguard-ledger-{run['run_id']}.csv")


@router.get("/api/export/manifest.json")
def export_manifest_json(run_id: str | None = None):
    run = _run_or_404(run_id)
    return _download(service.manifest_json_text(run),
                     "application/json; charset=utf-8",
                     f"lineageguard-manifest-{run['run_id']}.json")
