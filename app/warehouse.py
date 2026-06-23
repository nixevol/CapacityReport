"""数据仓库抽象：直连 MySQL 或 Metrix 数据库平台。

`make_warehouse(config)` 按 warehouse_type 返回:
- 直连 MySQL: 原版 `DatabaseManager`（已具备下列方法）。
- Metrix: `MetrixWarehouse`，用平台数据库 API 实现相同方法，供查看/导出路由透明替换。

两者都提供: test_connection / get_server_info / get_tables / get_table_info /
query_table / truncate_table / drop_table / drop_all_tables / execute_sql。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.config import AppConfig
from app.database import DatabaseManager
from app.services.platform import make_client


def make_warehouse(config: AppConfig):
    if config.warehouse_type == "metrix":
        return MetrixWarehouse(config)
    return DatabaseManager(config)


def _quote_ident(name: str) -> str:
    return "`" + str(name).replace("`", "``") + "`"


def _quote_value(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


class MetrixWarehouse:
    """用 Metrix 数据库 API 实现 DatabaseManager 的只读/管理子集。"""

    def __init__(self, config: AppConfig):
        self.metrix = config.metrix.normalized()
        self.conn_id = self.metrix.database_conn_id
        self.database = self.metrix.target_database
        self.client = make_client(self.metrix)

    # --- 连接 / 诊断 -----------------------------------------------------
    def test_connection(self) -> Tuple[bool, str]:
        try:
            self.client.list_tables(self.conn_id, self.database)
            return True, "连接成功"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def get_server_info(self) -> Dict[str, Any]:
        version = "Metrix"
        try:
            res = self.client.run_script(self.conn_id, content="SELECT VERSION() AS v", database=self.database, run_timeout=30)
            rows = (res.get("results") or [{}])[0].get("rows") or []
            if rows:
                version = str(list(rows[0].values())[0])
        except Exception:  # noqa: BLE001
            pass
        return {"version": version, "load_data_infile": True, "load_data_message": "Metrix 平台导入"}

    # --- 表 / 数据 -------------------------------------------------------
    def get_tables(self) -> List[str]:
        return self.client.list_tables(self.conn_id, self.database)

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        columns = self.client.table_columns(self.conn_id, table_name, self.database)
        # Map Metrix column shape -> original DESCRIBE-like shape used by the frontend.
        mapped = [
            {
                "Field": col.get("name"),
                "Type": col.get("type", ""),
                "Null": "YES" if col.get("nullable", True) else "NO",
                "Key": "PRI" if col.get("primary_key") else "",
                "Default": col.get("default"),
                "Extra": "auto_increment" if col.get("autoincrement") else "",
            }
            for col in columns
        ]
        data = self.client.table_data(self.conn_id, table_name, self.database, page=1, page_size=1)
        return {"name": table_name, "columns": mapped, "row_count": int(data.get("total") or 0)}

    def query_table(
        self,
        table_name: str,
        page: int = 1,
        page_size: int = 50,
        filters: Optional[Dict[str, str]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "ASC",
    ) -> Dict[str, Any]:
        active_filters = {k: v for k, v in (filters or {}).items() if v}
        if active_filters:
            return self._query_with_filters(table_name, page, page_size, active_filters, order_by, order_dir)
        data = self.client.table_data(
            self.conn_id, table_name, self.database, page=page, page_size=page_size,
            order_by=order_by or "", order_dir=order_dir,
        )
        total = int(data.get("total") or 0)
        return {
            "data": data.get("rows", []),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        }

    def _query_with_filters(self, table_name, page, page_size, filters, order_by, order_dir) -> Dict[str, Any]:
        where = " AND ".join(f"{_quote_ident(col)} LIKE {_quote_value('%' + str(val) + '%')}" for col, val in filters.items())
        where_sql = f" WHERE {where}" if where else ""
        table_sql = _quote_ident(table_name)
        total_res = self.client.run_script(
            self.conn_id, content=f"SELECT COUNT(*) AS n FROM {table_sql}{where_sql}",
            database=self.database, run_timeout=120,
        )
        total = int(((total_res.get("results") or [{}])[0].get("rows") or [{}])[0].get("n") or 0)
        order_sql = ""
        if order_by:
            direction = "DESC" if str(order_dir).upper() == "DESC" else "ASC"
            order_sql = f" ORDER BY {_quote_ident(order_by)} {direction}"
        offset = max(page - 1, 0) * page_size
        data_res = self.client.run_script(
            self.conn_id,
            content=f"SELECT * FROM {table_sql}{where_sql}{order_sql} LIMIT {int(page_size)} OFFSET {int(offset)}",
            database=self.database, run_timeout=300,
        )
        rows = (data_res.get("results") or [{}])[0].get("rows") or []
        return {
            "data": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        }

    # --- 管理操作 --------------------------------------------------------
    def truncate_table(self, table_name: str) -> bool:
        self._run(f"TRUNCATE TABLE {_quote_ident(table_name)}")
        return True

    def drop_table(self, table_name: str) -> bool:
        self._run(f"DROP TABLE IF EXISTS {_quote_ident(table_name)}")
        return True

    def drop_all_tables(self) -> Dict[str, Any]:
        tables = self.get_tables()
        if not tables:
            return {"success": True, "dropped_count": 0, "tables": []}
        drop_sql = "".join(f"DROP TABLE IF EXISTS {_quote_ident(t)};\n" for t in tables)
        self._run(drop_sql)
        return {"success": True, "dropped_count": len(tables), "tables": tables}

    def execute_sql(self, sql: str) -> Tuple[bool, Any]:
        try:
            res = self.client.run_script(self.conn_id, content=sql, database=self.database, run_timeout=600)
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
        if res.get("stopped"):
            failed = [r for r in res.get("results", []) if not r.get("ok")]
            return False, (failed[0].get("message") if failed else "SQL 执行失败")
        results = res.get("results", [])
        last = results[-1] if results else {}
        if last.get("rows"):
            return True, last["rows"]
        return True, {"affected_rows": sum(int(r.get("affected_rows") or 0) for r in results)}

    def _run(self, content: str) -> None:
        res = self.client.run_script(self.conn_id, content=content, database=self.database, run_timeout=600)
        if res.get("stopped"):
            failed = [r for r in res.get("results", []) if not r.get("ok")]
            raise RuntimeError(failed[0].get("message") if failed else "SQL 执行失败")
