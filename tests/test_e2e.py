"""端到端：样例 → 判定 → 对账 → 导出，页面与接口一致。"""

from __future__ import annotations

import csv
import io

from tests.fixtures import expected

PAGES = [
    ("/", "规格单"),
    ("/types", "类型与兼容"),
    ("/mapping", "字段映射"),
    ("/impact", "影响面"),
    ("/batches", "版本历史"),
    ("/spec", "迁移单"),
]


def test_health_and_home(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["runs"] == 1
    assert body["window_semantics"] == "[start, end)"

    home = client.get("/")
    assert home.status_code == 200
    assert "规格单" in home.text


def test_all_pages_render(client):
    for path, marker in PAGES:
        response = client.get(path)
        assert response.status_code == 200, path
        assert marker in response.text, path
        assert "/static/theme.css" in response.text
        assert "http://" not in response.text.split("<main")[0]


def test_full_flow_matches_ledger(client):
    reconcile = client.get("/api/reconcile").json()
    fields = reconcile["fields"]
    assert fields["old_total"] == expected.OLD_TOTAL
    assert fields["new_total"] == expected.NEW_TOTAL
    assert fields["old_gap"] == 0 and fields["new_gap"] == 0
    assert reconcile["refs"]["balanced"] is True
    assert reconcile["balanced"]["all"] is True

    rows = list(csv.DictReader(io.StringIO(client.get("/api/export/evidence.csv").text)))
    assert len(rows) == expected.OLD_TOTAL + 4
    assert sum(1 for row in rows if row["verdict"] == "BREAKING") == 6


def test_quarantine_csv_export(client):
    response = client.get("/api/schemas/quarantine.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == expected.QUARANTINE_BLOCKED + expected.QUARANTINE_WARNINGS
    reasons = {row["reason"] for row in rows}
    assert {"LINE_MALFORMED", "DUPLICATE_COLUMN", "BOM_STRIPPED"} <= reasons
    assert sum(1 for row in rows if row["blocking"] == "Y") == expected.QUARANTINE_BLOCKED


def test_home_renders_field_rows(client):
    home = client.get("/")
    assert "order_code" in home.text
    assert "pay_channel" in home.text
    assert "破坏" in home.text


def test_mapping_page_shows_rename_chain(client):
    page = client.get("/mapping")
    assert "改名链" in page.text
    assert "ord_no → order_no → order_code" in page.text
    assert "v2026_03 → v2026_09" in page.text


def test_impact_page_shows_alias_paths(client):
    page = client.get("/impact")
    assert "经别名读取" in page.text
    assert "ord_no → order_no → order_code" in page.text


def test_pages_and_exports_share_version(client):
    """页面与导出对应同一版本：回看哪一批，页头、导航与导出都钉在那批。"""
    from app import store

    first = store.latest_run()["run_id"]
    client.post("/api/runs", json={"params": {"wave": "next"}})
    second = store.latest_run()["run_id"]
    assert second != first

    # 回看第一版：页头、导航与导出链接都带 run_id
    page = client.get(f"/spec?run_id={first}")
    assert page.status_code == 200
    assert first in page.text
    assert f"/api/export/spec.md?run_id={first}" in page.text
    assert f"/api/export/refs.csv?run_id={first}" in page.text
    assert f'href="/impact?run_id={first}"' in page.text

    # 缺省取最新批次
    latest = client.get("/spec")
    assert second in latest.text
    assert "/api/export/spec.md?run_id=" not in latest.text

    # 影响面与版本历史同样可回看
    impact = client.get(f"/impact?run_id={first}")
    assert impact.status_code == 200
    assert first in impact.text
    batches = client.get("/batches")
    assert f"/impact?run_id={first}" in batches.text
    assert f"/spec?run_id={first}" in batches.text

    # 接口同样认 run_id
    assert client.get(f"/api/impact?run_id={first}").json()["run_id"] == first
    assert client.get("/api/impact").json()["run_id"] == second
    assert client.get(f"/api/mapping?run_id={first}").json()["run_id"] == first
    assert client.get(f"/api/reconcile?run_id={first}").json()["run_id"] == first

    # 未知批次一律 404
    assert client.get("/spec?run_id=fm-000000000000").status_code == 404
    assert client.get("/impact?run_id=fm-000000000000").status_code == 404
    assert client.get("/api/impact?run_id=fm-000000000000").status_code == 404
