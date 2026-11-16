"""改名链：跨多个版本的旧名 → 新名，带环检测。

一个字段可能被改过两次名，下游还写着最早的名字，所以要顺着链一路解析到底。
"""

from __future__ import annotations

MAX_HOPS = 12


def edge_key(table: str, name: str) -> str:
    return f"{table.lower()}|{name.lower()}"


def build_edges(fields_old: list[dict], fields_new: list[dict],
                allowed_ids: set[str] | None = None) -> dict[str, set[str]]:
    """同一个 field_id 在两个版本里名字不同 → 一条改名边。"""
    by_id = {field["field_id"]: field for field in fields_new}
    edges: dict[str, set[str]] = {}
    for old in fields_old:
        new = by_id.get(old["field_id"])
        if not new or new["name"] == old["name"]:
            continue
        if allowed_ids is not None and old["field_id"] not in allowed_ids:
            continue
        edges.setdefault(edge_key(old["table"], old["name"]), set()).add(new["name"])
    return edges


def merge_edges(*graphs: dict[str, set[str]]) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = {}
    for graph in graphs:
        for key, targets in graph.items():
            merged.setdefault(key, set()).update(targets)
    return merged


def resolve(edges: dict[str, set[str]], table: str, name: str) -> dict:
    """顺着改名链走到最后一个名字；遇到环就停下并标出来。"""
    key = edge_key(table, name)
    path = [name]
    seen = {key}
    cycle = False
    ambiguous = False
    hops = 0
    while hops < MAX_HOPS:
        targets = edges.get(key)
        if not targets:
            break
        if len(targets) > 1:
            ambiguous = True
            break
        target = next(iter(targets))
        next_key = edge_key(table, target)
        path.append(target)
        if next_key in seen:
            cycle = True
            break
        seen.add(next_key)
        key = next_key
        hops += 1
    return {
        "canonical": path[-1],
        "path": path,
        "cycle": cycle,
        "ambiguous": ambiguous,
        "hops": hops,
        "reason": "ALIAS_CYCLE" if cycle else ("MAPPING_CONFLICT" if ambiguous else None),
    }


def alias_map(fields_old: list[dict], fields_new: list[dict]) -> dict[tuple[str, str], str]:
    """(表, 旧列名) -> 新列名，供引用解析使用。"""
    by_id = {field["field_id"]: field for field in fields_new}
    out: dict[tuple[str, str], str] = {}
    for old in fields_old:
        new = by_id.get(old["field_id"])
        if not new:
            continue
        out[(old["table"].lower(), old["name"].lower())] = new["name"]
    return out


def chain_paths(hops: list[dict]) -> list[dict]:
    """把逐跳改名记录连成最长链，供页面与导出展示。

    hops 里每条是 {"table", "old_name", "new_name", ...}；同一字段跨多个版本
    改过多次名时，这里把散落的跳接成 ord_no → order_no → order_code，
    并带上首跳与末跳所在的版本区间。
    """
    by_table: dict[str, dict[str, str]] = {}
    versions: dict[tuple[str, str], dict] = {}
    for hop in hops:
        table = str(hop.get("table") or "")
        old_name = str(hop.get("old_name") or "")
        new_name = str(hop.get("new_name") or "")
        if not table or not old_name or not new_name or old_name == new_name:
            continue
        by_table.setdefault(table, {})[old_name] = new_name
        versions[(table, old_name)] = hop

    paths: list[dict] = []
    for table in sorted(by_table):
        edges = by_table[table]
        starts = [name for name in edges if name not in edges.values()]
        for start in sorted(starts, key=str.lower):
            path = [start]
            seen = {start.lower()}
            node = start
            while node in edges:
                nxt = edges[node]
                path.append(nxt)
                if nxt.lower() in seen:
                    break
                seen.add(nxt.lower())
                node = nxt
            if len(path) > 1:
                first = versions.get((table, path[0])) or {}
                last = versions.get((table, path[-2])) or {}
                paths.append({
                    "table": table,
                    "path": path,
                    "from_version": first.get("from_version"),
                    "to_version": last.get("to_version"),
                })
    return paths
