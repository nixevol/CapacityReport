"""Metrix 平台集成：API 客户端 + 储存下载器。

当 source_type/warehouse_type 选 "metrix" 时，源数据走平台储存模块、数据仓库走平台数据库模块。
连接信息(地址/token/storage_id/database_conn_id/target_database)来自 Configure.json 的 Metrix 段。
储存下载器与 RemoteDataDownloader 接口一致，可被源工厂直接替换。
"""
from __future__ import annotations

import time
from datetime import date
from pathlib import Path
from typing import Iterable

import requests

from app.config import AppConfig, MetrixConfig
from app.services.remote_download import RemoteDownloadResult, RemoteFileInfo
from app.utils.file_dates import parse_file_date_range, select_recent_items_by_directory


class PlatformClient:
    """平台储存 + 数据库模块的最小 API 封装（Bearer Token 鉴权）。"""

    def __init__(self, base_url: str, token: str, timeout: int = 60):
        if not base_url:
            raise ValueError("缺少平台地址，请在系统设置的 Metrix 连接中填写")
        if not token:
            raise ValueError("缺少平台 API Token，请在系统设置的 Metrix 连接中填写")
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    # --- 储存模块 --------------------------------------------------------
    def list_storage_files(self, storage_id: str, path: str = "/", recursive: bool = True) -> list[dict]:
        resp = self.session.get(
            f"{self.base}/api/storages/{storage_id}/files",
            params={"path": path, "recursive": "true" if recursive else "false"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("entries", [])

    def download_storage_file(self, storage_id: str, path: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(
            f"{self.base}/api/storages/{storage_id}/download",
            params={"path": path},
            stream=True,
            timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        handle.write(chunk)

    def batch_delete_storage(self, storage_id: str, paths: list[str]) -> int:
        deleted = 0
        for start in range(0, len(paths), 100):
            chunk = [p for p in paths[start:start + 100] if p]
            if not chunk:
                continue
            resp = self.session.post(
                f"{self.base}/api/storages/{storage_id}/batch-delete",
                json={"paths": chunk},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            deleted += len(chunk)
        return deleted

    # --- 数据库模块 ------------------------------------------------------
    def import_csv(self, conn_id: str, table: str, csv_path: Path, mode: str = "overwrite",
                   database: str = "", create_table: bool = True, upload_timeout: int = 1800) -> str:
        with csv_path.open("rb") as handle:
            resp = self.session.post(
                f"{self.base}/api/databases/{conn_id}/import",
                files={"file": (csv_path.name, handle, "text/csv")},
                data={
                    "format": "csv",
                    "target_table": table,
                    "mode": mode,
                    "database": database,
                    "mapping": "{}",
                    "create_table": "true" if create_table else "false",
                },
                timeout=upload_timeout,
            )
        resp.raise_for_status()
        return resp.json()["job_id"]

    def wait_job(self, job_id: str, interval: int = 2, max_wait: int = 7200) -> dict:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            resp = self.session.get(
                f"{self.base}/api/database-transfer-jobs/{job_id}", timeout=self.timeout
            )
            resp.raise_for_status()
            job = resp.json()
            if job.get("status") in ("success", "failed"):
                return job
            time.sleep(interval)
        raise TimeoutError(f"导入任务 {job_id} 超过 {max_wait}s 仍未完成")

    def run_script(self, conn_id: str, script_id: int | None = None, content: str = "",
                   database: str = "", single_session: bool = False, run_timeout: int = 7200) -> dict:
        body: dict = {"database": database, "stop_on_error": True, "single_session": single_session}
        if content:
            body["content"] = content
        if script_id is not None:
            body["script_id"] = int(script_id)
        resp = self.session.post(
            f"{self.base}/api/databases/{conn_id}/run-script",
            json=body,
            timeout=run_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # --- 数据库读 / 导出（供仓库代理使用）-------------------------------
    def list_tables(self, conn_id: str, database: str = "") -> list[str]:
        resp = self.session.get(
            f"{self.base}/api/databases/{conn_id}/tables",
            params={"database": database},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return [str(item.get("name")) for item in resp.json() if item.get("name")]

    def table_columns(self, conn_id: str, table: str, database: str = "") -> list[dict]:
        resp = self.session.get(
            f"{self.base}/api/databases/{conn_id}/tables/{table}",
            params={"database": database},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("columns", [])

    def table_data(self, conn_id: str, table: str, database: str = "", page: int = 1, page_size: int = 50,
                   order_by: str = "", order_dir: str = "asc") -> dict:
        params = {"database": database, "table": table, "page": page, "page_size": page_size}
        if order_by:
            params["order_by"] = order_by
            params["order_dir"] = "desc" if str(order_dir).lower().startswith("desc") else "asc"
        resp = self.session.get(
            f"{self.base}/api/databases/{conn_id}/table-data", params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def submit_export(self, conn_id: str, tables: list[str], fmt: str, database: str = "") -> str:
        resp = self.session.post(
            f"{self.base}/api/databases/{conn_id}/export",
            json={"format": fmt, "database": database, "tables": tables},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["job_id"]

    def download_job_file(self, job_id: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(
            f"{self.base}/api/database-transfer-jobs/{job_id}/download", stream=True, timeout=self.timeout
        ) as resp:
            resp.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        handle.write(chunk)


def make_client(metrix: MetrixConfig) -> PlatformClient:
    metrix = metrix.normalized()
    return PlatformClient(metrix.base_url, metrix.token)


def make_source_downloader(app_config: AppConfig, logger=None):
    """Return a file-source downloader matching app_config.source_type. FTP/SFTP use the
    original RemoteDataDownloader; 'metrix' uses PlatformStorageDownloader. Both share the
    interface test_connection / list_remote_zip_files / download_to / delete_source_files."""
    if app_config.source_type == "metrix":
        return PlatformStorageDownloader(app_config, logger)
    from app.services.remote_download import RemoteDataDownloader

    return RemoteDataDownloader(app_config.remote_data, logger)


class PlatformStorageDownloader:
    """平台储存版下载器，接口与 RemoteDataDownloader 对齐，可被源工厂直接替换。"""

    def __init__(self, app_config: AppConfig, logger=None):
        self.metrix = app_config.metrix.normalized()
        self.remote_dir = (app_config.remote_data.remote_dir or "/").strip() or "/"
        self.logger = logger
        self.client = make_client(self.metrix)

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger(message)

    def test_connection(self) -> None:
        if not self.metrix.storage_id:
            raise ValueError("缺少储存连接 ID，请在系统设置的 Metrix 连接中填写")
        self.client.list_storage_files(self.metrix.storage_id, self.remote_dir, recursive=False)

    def list_remote_zip_files(self, directory: str | None = None) -> list[RemoteFileInfo]:
        path = self._join(self.remote_dir, directory.strip("/")) if directory else self.remote_dir
        entries = self.client.list_storage_files(self.metrix.storage_id, path, recursive=True)
        files: list[RemoteFileInfo] = []
        for entry in entries:
            if entry.get("is_dir"):
                continue
            name = str(entry.get("name", ""))
            if not name.lower().endswith(".zip"):
                continue
            files.append(self._info(str(entry.get("path", "")), int(entry.get("size", 0) or 0)))
        return files

    def download_to(self, destination: Path, target_dates: Iterable[date] | None = None) -> RemoteDownloadResult:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        zip_files = self.list_remote_zip_files()
        date_filter = set(target_dates or [])

        if date_filter:
            selected = self._select_by_dates(zip_files, date_filter)
        elif zip_files:
            selected, summaries = select_recent_items_by_directory(
                zip_files,
                parent_key=lambda item: item.parent,
                name_key=lambda item: item.name,
            )
            for summary in summaries:
                if summary.skipped_count and summary.start_date and summary.max_date:
                    self._log(
                        f"储存目录 {summary.directory or '.'}: 仅下载 "
                        f"{summary.start_date.isoformat()} 至 {summary.max_date.isoformat()} 的 "
                        f"{summary.selected_count}/{summary.total_count} 个 ZIP，跳过 {summary.skipped_count} 个旧文件"
                    )
        else:
            selected = []

        result = RemoteDownloadResult()
        for remote_file in selected:
            dest = destination / remote_file.relative_path
            self._log(f"下载: {remote_file.relative_path}")
            self.client.download_storage_file(self.metrix.storage_id, remote_file.path, dest)
            result.file_count += 1
            result.total_bytes += remote_file.size or (dest.stat().st_size if dest.exists() else 0)
            result.remote_files.append(remote_file.path)
        return result

    def delete_source_files(self, remote_files: Iterable[str] | None = None) -> int:
        files = [path for path in (remote_files or []) if path]
        if not files:
            return 0
        self._log(f"清理储存源文件，共 {len(files)} 个")
        return self.client.batch_delete_storage(self.metrix.storage_id, files)

    # --- helpers ---------------------------------------------------------
    def _select_by_dates(self, zip_files: list[RemoteFileInfo], target_dates: set[date]) -> list[RemoteFileInfo]:
        grouped: dict[str, list[RemoteFileInfo]] = {}
        for remote_file in zip_files:
            grouped.setdefault(remote_file.parent, []).append(remote_file)

        selected: list[RemoteFileInfo] = []
        for parent, files in sorted(grouped.items(), key=lambda item: item[0]):
            picked = [
                remote_file
                for remote_file in files
                if (date_range := parse_file_date_range(remote_file.name))
                and (
                    date_range.covers_all(target_dates)
                    if date_range.span_days > 1
                    else date_range.covers_any(target_dates)
                )
            ]
            selected.extend(picked)
            skipped = len(files) - len(picked)
            if skipped:
                self._log(
                    f"储存目录 {parent or '.'}: 仅下载目标日期 "
                    f"{min(target_dates).isoformat()} 至 {max(target_dates).isoformat()} 的 "
                    f"{len(picked)}/{len(files)} 个 ZIP，跳过 {skipped} 个非目标文件"
                )
        return selected

    @staticmethod
    def _join(parent: str, child: str) -> str:
        parent = (parent or "").replace("\\", "/").rstrip("/")
        if not parent:
            return child
        if parent == "/":
            return f"/{child}"
        return f"{parent}/{child}"

    def _info(self, remote_path: str, size: int = 0) -> RemoteFileInfo:
        normalized_root = self.remote_dir.replace("\\", "/").rstrip("/")
        normalized_path = remote_path.replace("\\", "/")
        if normalized_root and normalized_root != "/" and normalized_path.startswith(f"{normalized_root}/"):
            relative_path = normalized_path[len(normalized_root) + 1:]
        else:
            relative_path = normalized_path.lstrip("/")
        relative = Path(relative_path)
        parent = str(relative.parent).replace("\\", "/")
        if parent == ".":
            parent = ""
        return RemoteFileInfo(
            path=remote_path,
            relative_path=relative_path,
            parent=parent,
            name=relative.name,
            size=size,
        )
