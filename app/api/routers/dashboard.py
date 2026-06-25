"""容量看板分析接口。

基于 4G/5G 结果表（含富集 + 高负荷判定 + 优化建议列）做聚合分析，供前端容量看板展示。
读经 `make_warehouse`（直连 MySQL 或 Metrix 平台），分析对象为“主仓库”里的结果表。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app import state
from app.warehouse import make_warehouse

router = APIRouter(tags=["dashboard"])

# 每个制式（结果表）的关键列映射
RAT = {
    "4g": {
        "table": "4G_结果表",
        "id": "CGI",
        "name": "小区名称",
        "ul": "上行PUSCH利用率",
        "dl": "下行PDSCH利用率",
        "ul_label": "上行PUSCH利用率",
        "dl_label": "下行PDSCH利用率",
        "users": "YY-RRC连接建立最大用户数",
    },
    "5g": {
        "table": "5G_结果表",
        "id": "NCGI",
        "name": "CU小区配置名称",
        "ul": "上行PRB平均利用率",
        "dl": "下行PRB平均利用率",
        "ul_label": "上行PRB利用率",
        "dl_label": "下行PRB利用率",
        "users": "RRC连接平均连接用户数",
    },
}
FLOW = "日均流量（GB）"
PROBLEMS = ["高负荷", "利用率预警", "高流量预警"]


def _db():
    return make_warehouse(state.current_config())


def _esc(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "''")


def _rows(db, sql: str) -> list[dict[str, Any]]:
    ok, result = db.execute_sql(sql)
    if not ok:
        raise HTTPException(status_code=500, detail=str(result))
    return result if isinstance(result, list) else []


def _num(value: Any, digits: int | None = None) -> float | int:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0
    if digits is None:
        return int(num)
    return round(num, digits)


def _rat(rat: str) -> dict[str, str]:
    cfg = RAT.get((rat or "").lower())
    if not cfg:
        raise HTTPException(status_code=400, detail="rat 仅支持 4g / 5g")
    return cfg


def _existing_tables(db) -> set[str]:
    try:
        return {str(t).lower() for t in db.get_tables()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取数据表失败: {exc}") from exc


@router.get("/api/dashboard/status")
def dashboard_status():
    tables = _existing_tables(_db())
    has_4g = RAT["4g"]["table"].lower() in tables
    has_5g = RAT["5g"]["table"].lower() in tables
    return {"has_4g": has_4g, "has_5g": has_5g, "ready": has_4g and has_5g}


@router.get("/api/dashboard/overview")
def dashboard_overview(rat: str = Query("4g")):
    cfg = _rat(rat)
    db = _db()
    if cfg["table"].lower() not in _existing_tables(db):
        raise HTTPException(status_code=404, detail=f"结果表 {cfg['table']} 不存在，请先进行数据处理")

    t = f"`{cfg['table']}`"
    ul, dl, flow, users = f"`{cfg['ul']}`", f"`{cfg['dl']}`", f"`{FLOW}`", f"`{cfg['users']}`"

    summary = _rows(db, (
        f"SELECT COUNT(*) total,"
        f" SUM(`高负荷问题`='高负荷') high_load,"
        f" SUM(`高负荷问题`='利用率预警') util_warn,"
        f" SUM(`高负荷问题`='高流量预警') flow_warn,"
        f" SUM(`高负荷问题` IS NULL) normal,"
        f" ROUND(AVG({dl})*100,1) avg_dl,"
        f" ROUND(MAX({dl})*100,1) max_dl,"
        f" ROUND(AVG({flow}),2) avg_flow,"
        f" ROUND(SUM({flow}),1) total_flow"
        f" FROM {t}"
    ))
    s = summary[0] if summary else {}
    summary_out = {
        "total": _num(s.get("total")),
        "high_load": _num(s.get("high_load")),
        "util_warn": _num(s.get("util_warn")),
        "flow_warn": _num(s.get("flow_warn")),
        "normal": _num(s.get("normal")),
        "avg_dl": _num(s.get("avg_dl"), 1),
        "max_dl": _num(s.get("max_dl"), 1),
        "avg_flow": _num(s.get("avg_flow"), 2),
        "total_flow": _num(s.get("total_flow"), 1),
    }

    problem_pie = [
        {"name": "高负荷", "value": summary_out["high_load"]},
        {"name": "利用率预警", "value": summary_out["util_warn"]},
        {"name": "高流量预警", "value": summary_out["flow_warn"]},
        {"name": "正常", "value": summary_out["normal"]},
    ]

    def group_by(col: str, limit: int = 0) -> list[dict[str, Any]]:
        limit_sql = f" LIMIT {int(limit)}" if limit else ""
        rows = _rows(db, (
            f"SELECT IFNULL(`{col}`,'未知') name, COUNT(*) total,"
            f" SUM(`是否高负荷小区`='是') high,"
            f" SUM(`高负荷问题` IS NOT NULL) flagged"
            f" FROM {t} GROUP BY `{col}` ORDER BY flagged DESC, total DESC{limit_sql}"
        ))
        return [
            {"name": str(r.get("name")), "total": _num(r.get("total")),
             "high": _num(r.get("high")), "flagged": _num(r.get("flagged"))}
            for r in rows
        ]

    # 下行利用率分布（0-10%...90-100%）
    hist_rows = _rows(db, (
        f"SELECT LEAST(FLOOR({dl}*10),9) b, COUNT(*) c FROM {t}"
        f" WHERE {dl} IS NOT NULL GROUP BY b ORDER BY b"
    ))
    hist_map = {int(_num(r.get("b"))): _num(r.get("c")) for r in hist_rows}
    util_hist = [
        {"bucket": f"{i*10}-{i*10+10}%", "value": hist_map.get(i, 0)} for i in range(10)
    ]

    top_rows = _rows(db, (
        f"SELECT `{cfg['id']}` id, IFNULL(`{cfg['name']}`,'') name, IFNULL(`制式`,'') `system`,"
        f" IFNULL(`带宽`,'') band, IFNULL(`站型`,'') station,"
        f" ROUND({ul}*100,1) ul, ROUND({dl}*100,1) dl, ROUND({flow},2) flow, ROUND({users},0) users,"
        f" IFNULL(`高负荷问题`,'') problem"
        f" FROM {t} WHERE `高负荷问题`='高负荷' ORDER BY {dl} DESC, {flow} DESC LIMIT 10"
    ))
    top_cells = [
        {"id": str(r.get("id")), "name": str(r.get("name")), "system": str(r.get("system")),
         "band": str(r.get("band")), "station": str(r.get("station")),
         "ul": _num(r.get("ul"), 1), "dl": _num(r.get("dl"), 1),
         "flow": _num(r.get("flow"), 2), "users": _num(r.get("users")), "problem": str(r.get("problem"))}
        for r in top_rows
    ]

    return {
        "rat": rat.lower(),
        "labels": {"ul": cfg["ul_label"], "dl": cfg["dl_label"]},
        "summary": summary_out,
        "problem_pie": problem_pie,
        "by_system": group_by("制式"),
        "by_band": group_by("带宽"),
        "by_station": group_by("站型"),
        "by_freq": group_by("频段", limit=12),
        "util_hist": util_hist,
        "top_cells": top_cells,
    }


@router.get("/api/dashboard/cells")
def dashboard_cells(
    rat: str = Query("4g"),
    problem: str = Query(""),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    cfg = _rat(rat)
    db = _db()
    if cfg["table"].lower() not in _existing_tables(db):
        raise HTTPException(status_code=404, detail=f"结果表 {cfg['table']} 不存在，请先进行数据处理")

    t = f"`{cfg['table']}`"
    ul, dl, flow, users = f"`{cfg['ul']}`", f"`{cfg['dl']}`", f"`{FLOW}`", f"`{cfg['users']}`"

    wheres = ["`高负荷问题` IS NOT NULL"]
    if problem in PROBLEMS:
        wheres = [f"`高负荷问题`='{problem}'"]
    if keyword.strip():
        kw = _esc(keyword.strip())
        wheres.append(f"(`{cfg['id']}` LIKE '%{kw}%' OR `{cfg['name']}` LIKE '%{kw}%')")
    where_sql = " WHERE " + " AND ".join(wheres)

    total = _num(_rows(db, f"SELECT COUNT(*) c FROM {t}{where_sql}")[0].get("c"))
    offset = (page - 1) * page_size
    rows = _rows(db, (
        f"SELECT `{cfg['id']}` id, IFNULL(`{cfg['name']}`,'') name, IFNULL(`制式`,'') `system`,"
        f" IFNULL(`带宽`,'') band, IFNULL(`站型`,'') station, IFNULL(`频段`,'') freq,"
        f" ROUND({ul}*100,1) ul, ROUND({dl}*100,1) dl, ROUND({flow},2) flow, ROUND({users},0) users,"
        f" IFNULL(`高负荷问题`,'') problem, IFNULL(`是否高负荷小区`,'否') is_high"
        f" FROM {t}{where_sql}"
        f" ORDER BY FIELD(`高负荷问题`,'高负荷','高流量预警','利用率预警'), {dl} DESC"
        f" LIMIT {int(page_size)} OFFSET {int(offset)}"
    ))
    items = [
        {"id": str(r.get("id")), "name": str(r.get("name")), "system": str(r.get("system")),
         "band": str(r.get("band")), "station": str(r.get("station")), "freq": str(r.get("freq")),
         "ul": _num(r.get("ul"), 1), "dl": _num(r.get("dl"), 1), "flow": _num(r.get("flow"), 2),
         "users": _num(r.get("users")), "problem": str(r.get("problem")), "is_high": str(r.get("is_high"))}
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/api/dashboard/cell")
def dashboard_cell(rat: str = Query("4g"), id: str = Query(...)):
    cfg = _rat(rat)
    db = _db()
    if cfg["table"].lower() not in _existing_tables(db):
        raise HTTPException(status_code=404, detail=f"结果表 {cfg['table']} 不存在")

    t = f"`{cfg['table']}`"
    cell_id = _esc(id)
    rows = _rows(db, f"SELECT * FROM {t} WHERE `{cfg['id']}`='{cell_id}' LIMIT 1")
    if not rows:
        raise HTTPException(status_code=404, detail="未找到该小区")
    row = rows[0]

    # 同扇区同 PLMN 的兄弟小区（用于详情页的均衡上下文）
    sector = str(row.get("扇区") or "")
    siblings: list[dict[str, Any]] = []
    if sector:
        plmn = _esc("-".join(str(id).split("-")[:2]))
        sector_e = _esc(sector)
        dl = f"`{cfg['dl']}`"
        sib_rows = _rows(db, (
            f"SELECT `{cfg['id']}` id, IFNULL(`{cfg['name']}`,'') name, IFNULL(`带宽`,'') band,"
            f" IFNULL(`频段`,'') freq, ROUND(`{cfg['ul']}`*100,1) ul, ROUND({dl}*100,1) dl,"
            f" ROUND(`{FLOW}`,2) flow, IFNULL(`高负荷问题`,'正常') problem"
            f" FROM {t} WHERE `扇区`='{sector_e}' AND SUBSTRING_INDEX(`{cfg['id']}`,'-',2)='{plmn}'"
            f" AND `{cfg['id']}`<>'{cell_id}' ORDER BY {dl} DESC LIMIT 30"
        ))
        siblings = [
            {"id": str(r.get("id")), "name": str(r.get("name")), "band": str(r.get("band")),
             "freq": str(r.get("freq")), "ul": _num(r.get("ul"), 1), "dl": _num(r.get("dl"), 1),
             "flow": _num(r.get("flow"), 2), "problem": str(r.get("problem"))}
            for r in sib_rows
        ]

    # 原始行转为字符串友好的 dict（数值保留，None→空）
    detail = {str(k): (v if v is not None else "") for k, v in row.items()}
    return {
        "rat": rat.lower(),
        "id": str(row.get(cfg["id"]) or id),
        "name": str(row.get(cfg["name"]) or ""),
        "labels": {"ul": cfg["ul_label"], "dl": cfg["dl_label"]},
        "id_field": cfg["id"],
        "name_field": cfg["name"],
        "ul_field": cfg["ul"],
        "dl_field": cfg["dl"],
        "users_field": cfg["users"],
        "flow_field": FLOW,
        "detail": detail,
        "siblings": siblings,
    }
