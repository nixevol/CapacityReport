"""数据库前置检查：确保各库「必须存在的结构表」已建好，缺表则按 db_init/ 下的初始化 SQL 自动创建。

约定（见 db_init/README.md）：
- 初始化 SQL 放在 BASE_DIR/db_init/，文件名形如 ``<库标识>.<表名>.sql``。
- 库标识 -> 实际连接（库名以用户配置为准，不写死）：
    celldata        -> AppConfig.cell_data.mysql（CellData 库，始终直连 MySQL）
    capacityreport  -> AppConfig.mysql（主仓库，仅当 warehouse_type == 'mysql' 直连时检查）
- 仅当目标表「不存在」时执行对应 SQL；已存在则跳过整文件，
  因此 sector_band_ref 这类带预设数据的表只在首次创建时写入，绝不覆盖用户自定义。
- 全过程 best-effort：单个库/单张表失败只记录日志并继续，不阻断启动或处理流程。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pymysql

from app.config import BASE_DIR, AppConfig, MySQLConfig

DB_INIT_DIR = BASE_DIR / "db_init"


def _log(logger, message: str) -> None:
    if logger is not None:
        try:
            logger.info(message)
            return
        except Exception:
            pass
    print(message)


def _target_mysql(app_config: AppConfig, db_key: str) -> Optional[MySQLConfig]:
    """库标识 -> MySQL 连接配置；不适用（如主库走 Metrix）时返回 None。"""
    if db_key == "celldata":
        return app_config.cell_data.mysql.normalized()
    if db_key == "capacityreport":
        if app_config.warehouse_type != "mysql":
            return None
        return app_config.mysql.normalized()
    return None


def _connect(mysql: MySQLConfig):
    return pymysql.connect(
        host=mysql.host,
        port=mysql.port,
        user=mysql.user,
        password=mysql.passwd,
        database=mysql.dbname,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        autocommit=False,
    )


def _existing_tables(conn) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        return {str(row[0]).lower() for row in cursor.fetchall()}


def _run_sql_file(conn, path: Path) -> None:
    from app.processor import DataProcessor

    statements = DataProcessor.parse_sql_script(path.read_text(encoding="utf-8"))
    with conn.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
    conn.commit()


def _discover() -> dict[str, list[tuple[str, Path]]]:
    """收集 db_init 下的初始化 SQL，按库标识分组：{库标识: [(表名, 路径), ...]}。"""
    groups: dict[str, list[tuple[str, Path]]] = {}
    if not DB_INIT_DIR.exists():
        return groups
    for path in sorted(DB_INIT_DIR.glob("*.sql")):
        stem = path.stem  # 例如 celldata.sector_band_ref
        if "." not in stem:
            continue
        db_key, table = stem.split(".", 1)
        groups.setdefault(db_key, []).append((table, path))
    return groups


def ensure_required_tables(app_config: AppConfig, logger=None) -> None:
    """检查各库必须存在的表，缺则按初始化 SQL 建好。失败不抛出（仅记录日志）。"""
    groups = _discover()
    for db_key, items in groups.items():
        mysql = _target_mysql(app_config, db_key)
        if mysql is None or not mysql.dbname:
            continue
        try:
            conn = _connect(mysql)
        except Exception as exc:  # noqa: BLE001
            _log(logger, f"[前置检查] 连接库 {db_key}({mysql.dbname}@{mysql.host}:{mysql.port}) 失败，跳过：{exc}")
            continue
        try:
            existing = _existing_tables(conn)
            for table, path in items:
                if table.lower() in existing:
                    continue
                try:
                    _run_sql_file(conn, path)
                    _log(logger, f"[前置检查] {db_key}.{table} 不存在，已按 {path.name} 初始化建表")
                except Exception as exc:  # noqa: BLE001
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    _log(logger, f"[前置检查] 初始化 {db_key}.{table} 失败：{exc}")
        finally:
            conn.close()
