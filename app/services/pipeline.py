"""Metrix 仓库模式的处理流水线：CSV 处理 → 平台导入暂存表 → run-script(single_session) 跑报表 SQL。

仅当 warehouse_type == "metrix" 时使用；直连 MySQL 模式走原版 DataProcessor。
"""
from __future__ import annotations

from pathlib import Path

from app.config import SQL_SCRIPT, AppConfig, MetrixConfig
from app.processor import ProcessLogger
from app.services.csv_processor import CsvProcessor
from app.services.platform import make_client

RJ_DIR_TO_TABLE = {
    "2.6RJGD": "2_6GRJGD",
    "2.6RJYD": "2_6GRJYD",
    "700RJGD": "700MRJGD",
    "700RJYD": "700MRJYD",
}
RESULT_TABLES = ["4G_结果表", "5G_结果表"]


def validate_metrix(metrix: MetrixConfig) -> None:
    missing = []
    if not metrix.base_url:
        missing.append("平台地址")
    if not metrix.token:
        missing.append("API Token")
    if not metrix.database_conn_id:
        missing.append("数据库连接 ID")
    if missing:
        raise RuntimeError("Metrix 连接配置不完整: " + ", ".join(missing))


def build_processor_config(app_config: AppConfig) -> dict:
    metrix = app_config.metrix.normalized()
    rj = app_config.rj_data.normalized()
    return {
        "recent_days": metrix.recent_days,
        "sheet_filter": list(app_config.sheet_filter),
        "data_dir_to_table": dict(metrix.data_dir_to_table),
        "extract_fields": app_config.extract_fields,
        "rj": {
            "enabled": rj.enabled,
            "weekly_directories": rj.weekly_directories,
            "dir_to_table": RJ_DIR_TO_TABLE,
            "table_field_mappings": rj.table_field_mappings,
        },
    }


def read_report_sql() -> str:
    if not SQL_SCRIPT.exists():
        return ""
    return SQL_SCRIPT.read_text(encoding="utf-8").strip()


def run_report_sql(app_config: AppConfig, logger: ProcessLogger) -> list[dict]:
    metrix = app_config.metrix.normalized()
    validate_metrix(metrix)
    report_sql = read_report_sql()
    if not report_sql:
        raise RuntimeError("报表 SQL（ReportScript.sql）为空或不存在")
    client = make_client(metrix)
    logger.info("执行报表 SQL（single_session）...")
    result = client.run_script(
        metrix.database_conn_id,
        content=report_sql,
        database=metrix.target_database,
        single_session=True,
        run_timeout=7200,
    )
    statements = result.get("results", [])
    failed = [item for item in statements if not item.get("ok")]
    if result.get("stopped") or failed:
        for item in failed[:5]:
            logger.error(f"[SQL] 第 {item.get('index')} 条失败: {item.get('message')}")
        raise RuntimeError("报表 SQL 执行失败")
    logger.success(f"报表 SQL 执行完成，共 {len(statements)} 条语句")
    return statements


def run_import_and_report(work_dir: Path, app_config: AppConfig, logger: ProcessLogger) -> dict:
    """处理工作目录数据 → 平台导入暂存表 → 跑报表 SQL。失败抛 RuntimeError。"""
    metrix = app_config.metrix.normalized()
    validate_metrix(metrix)

    logger.set_stage("converting")
    tables = CsvProcessor(work_dir, build_processor_config(app_config), logger.info).process()
    if not tables:
        raise RuntimeError("处理后没有产出任何暂存表数据")

    client = make_client(metrix)
    conn_id = metrix.database_conn_id
    target_db = metrix.target_database

    # 导入前 DROP 旧暂存表，让自动建表按当周实际列重建。
    logger.set_stage("importing")
    drop_sql = "".join(f"DROP TABLE IF EXISTS `{table}`;\n" for table in tables)
    drop_result = client.run_script(conn_id, content=drop_sql, database=target_db, run_timeout=600)
    if drop_result.get("stopped"):
        raise RuntimeError("清理旧暂存表失败")

    for table, csv_path in tables.items():
        logger.info(f"导入暂存表 {table} ...")
        job_id = client.import_csv(conn_id, table, csv_path, mode="overwrite", database=target_db, create_table=True)
        job = client.wait_job(job_id)
        if job.get("status") != "success":
            raise RuntimeError(f"暂存表 {table} 导入失败: {job.get('error_code') or job.get('status')}")
        logger.success(f"暂存表 {table} 导入完成")

    logger.set_stage("scripting")
    statements = run_report_sql(app_config, logger)
    return {"tables": list(tables.keys()), "statements": len(statements)}
