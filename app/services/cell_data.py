from __future__ import annotations

import csv
import re
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import chardet
import pymysql

from app.config import AppConfig, CellDataConfig
from app.services.remote_download import RemoteDataDownloader, RemoteFileInfo

LogFn = Callable[[str], None]

CELLINFO_COLUMNS = [
    "CGI",
    "eNodeBID",
    "CellID",
    "PLMN",
    "基站名称",
    "小区名称",
    "频点",
    "带宽",
    "制式",
    "功率",
    "网络",
]


@dataclass(frozen=True)
class SelectedZip:
    scan_path: str
    band: str
    remote_file: RemoteFileInfo
    timestamp: str


@dataclass
class CellDataResult:
    selected_files: int = 0
    parsed_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0


class CellDataProcessor:
    def __init__(self, app_config: AppConfig, work_dir: Path, logger=None):
        self.app_config = app_config
        self.config = app_config.cell_data.normalized()
        self.work_dir = work_dir
        self.logger = logger
        self.downloader = RemoteDataDownloader(self.config.remote_data, self._log)
        self.year_dir_re = re.compile(self.config.year_dir_regex)
        self.file_name_re = re.compile(self.config.file_name_regex)
        self.file_time_re = re.compile(self.config.file_time_regex)

    def run(self) -> CellDataResult:
        if not self.config.remote_data.enabled:
            self._log("CellData 数据源未启用，跳过")
            return CellDataResult()

        self._set_stage("locating")
        selected = self._select_latest_zip_files()
        if not selected:
            raise RuntimeError("未找到可处理的 CellData ZIP 文件")
        self._log(f"已选择 {len(selected)} 个 CellData ZIP 文件")

        self._set_stage("downloading")
        local_files = self._download_selected(selected)

        self._set_stage("parsing")
        result = CellDataResult(selected_files=len(selected))
        rows = self._parse_zip_files(local_files, result)
        if not rows:
            raise RuntimeError("CellData ZIP 中未解析到有效数据")

        self._set_stage("importing")
        result.imported_rows = self._replace_cellinfo(rows)
        self._log(f"CellData 导入完成，共 {result.imported_rows} 行")
        return result

    def _select_latest_zip_files(self) -> list[SelectedZip]:
        selected: list[SelectedZip] = []
        for template in self.config.scan_paths:
            scan_path = self._resolve_scan_path(template)
            band_dirs = [
                entry
                for entry in self._list_dir(scan_path)
                if entry["type"] == "directory"
            ]
            for band_dir in band_dirs:
                band = str(band_dir["name"])
                files = [
                    entry
                    for entry in self._list_dir(str(band_dir["path"]))
                    if entry["type"] == "file" and self.file_name_re.search(str(entry["name"]))
                ]
                latest = self._latest_file(files)
                if latest:
                    selected.append(
                        SelectedZip(
                            scan_path=scan_path,
                            band=band,
                            remote_file=self._remote_file_info(str(latest["path"]), int(latest.get("size") or 0)),
                            timestamp=str(latest["timestamp"]),
                        )
                    )
                    self._log(f"{band}: {latest['name']}")
        return selected

    def _resolve_scan_path(self, template: str) -> str:
        path = self._replace_date_placeholders(str(template).replace("\\", "/").strip())
        if not path.startswith("/"):
            path = self._join_remote_path(self.config.remote_data.remote_dir, path)
        if "{maxyear}" not in path:
            return path

        parts = [part for part in path.split("/") if part]
        maxyear_index = next((index for index, part in enumerate(parts) if "{maxyear}" in part), -1)
        if maxyear_index < 0:
            return path
        parent = "/" + "/".join(parts[:maxyear_index]) if maxyear_index else "/"
        year_segment = parts[maxyear_index]
        years: list[int] = []
        for entry in self._list_dir(parent):
            if entry["type"] != "directory":
                continue
            match = self.year_dir_re.search(str(entry["name"]))
            if match:
                years.append(int(match.group("year")))
        if not years:
            raise RuntimeError(f"未找到年份目录: {parent}")
        max_year = str(max(years))
        parts[maxyear_index] = year_segment.replace("{maxyear}", max_year)
        return "/" + "/".join(parts)

    def _replace_date_placeholders(self, path: str) -> str:
        now = datetime.now()
        return (
            path.replace("{yyyy}", now.strftime("%Y"))
            .replace("{yyyymm}", now.strftime("%Y%m"))
            .replace("{yyyymmdd}", now.strftime("%Y%m%d"))
        )

    def _latest_file(self, files: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates: list[dict[str, Any]] = []
        for item in files:
            match = self.file_time_re.search(str(item["name"]))
            if not match:
                continue
            timestamp = match.group("timestamp")
            candidates.append({**item, "timestamp": timestamp})
        if not candidates:
            return None
        return max(candidates, key=lambda item: str(item["timestamp"]))

    def _download_selected(self, selected: list[SelectedZip]) -> list[tuple[SelectedZip, Path]]:
        target_dir = self.work_dir / "cell_data"
        target_dir.mkdir(parents=True, exist_ok=True)
        local_files: list[tuple[SelectedZip, Path]] = []
        if self.config.remote_data.protocol == "ftp":
            with self.downloader._ftp_client() as ftp:  # noqa: SLF001 - reuse existing connection helpers
                for item in selected:
                    local_path = target_dir / item.band / item.remote_file.name
                    self.downloader._download_ftp_file(ftp, item.remote_file.path, local_path, self._download_result(), item.remote_file.size)  # noqa: SLF001
                    local_files.append((item, local_path))
            return local_files

        ssh = self.downloader._sftp_ssh_client()  # noqa: SLF001
        try:
            with ssh.open_sftp() as sftp:
                for item in selected:
                    local_path = target_dir / item.band / item.remote_file.name
                    self.downloader._download_sftp_file(sftp, item.remote_file.path, local_path, self._download_result(), item.remote_file.size)  # noqa: SLF001
                    local_files.append((item, local_path))
        finally:
            ssh.close()
        return local_files

    @staticmethod
    def _download_result():
        from app.services.remote_download import RemoteDownloadResult

        return RemoteDownloadResult()

    def _parse_zip_files(self, local_files: list[tuple[SelectedZip, Path]], result: CellDataResult) -> list[dict[str, str]]:
        mapping = self.config.mapping
        key_config = mapping["key"]
        rows_by_key: dict[str, dict[str, str]] = {}
        for selected, local_path in local_files:
            with zipfile.ZipFile(local_path) as zf:
                for source in mapping["sources"]:
                    if source["band"] != selected.band:
                        continue
                    for info in zf.infolist():
                        name = Path(info.filename).name
                        if not name.lower().endswith(".csv"):
                            continue
                        if not name.startswith(source["file_prefix"]):
                            continue
                        raw = zf.read(info.filename)
                        text = self._decode_csv(raw)
                        reader = csv.DictReader(text.splitlines())
                        for csv_row in reader:
                            row = self._map_row(source["fields"], csv_row)
                            key = self._render_expr(str(key_config["expr"]), row)
                            if not key or "--" in key:
                                result.skipped_rows += 1
                                continue
                            row[str(key_config["field"])] = key
                            rows_by_key[key] = {column: row.get(column, "") for column in CELLINFO_COLUMNS}
                            result.parsed_rows += 1
        return list(rows_by_key.values())

    def _map_row(self, fields: dict[str, Any], csv_row: dict[str, str]) -> dict[str, str]:
        row: dict[str, str] = {}
        for target, rule in fields.items():
            if isinstance(rule, str):
                row[target] = str(csv_row.get(rule, "") or "").strip()
            elif isinstance(rule, dict) and "value" in rule:
                row[target] = str(rule.get("value", "") or "").strip()
            else:
                row[target] = ""
        return row

    @staticmethod
    def _render_expr(expr: str, row: dict[str, str]) -> str:
        def replace(match):
            return row.get(match.group(1), "")

        return re.sub(r"\{([^{}]+)\}", replace, expr).strip()

    @staticmethod
    def _decode_csv(raw: bytes) -> str:
        candidates = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
        detected = (chardet.detect(raw).get("encoding") or "").lower()
        if detected and detected not in candidates:
            candidates.append(detected)
        for encoding in dict.fromkeys(candidates):
            try:
                return raw.decode(encoding).lstrip("\ufeff")
            except (LookupError, UnicodeDecodeError):
                pass
        return raw.decode("utf-8", errors="replace").lstrip("\ufeff")

    def _replace_cellinfo(self, rows: list[dict[str, str]]) -> int:
        mysql = self.config.mysql.normalized()
        table = str(self.config.mapping.get("target_table") or "cellinfo")
        conn = pymysql.connect(
            host=mysql.host,
            port=mysql.port,
            user=mysql.user,
            password=mysql.passwd,
            database=mysql.dbname,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        try:
            with conn.cursor() as cursor:
                self._ensure_cellinfo_table(cursor, table)
                cursor.execute(f"TRUNCATE TABLE `{table}`")
                placeholders = ", ".join(["%s"] * len(CELLINFO_COLUMNS))
                columns = ", ".join(f"`{column}`" for column in CELLINFO_COLUMNS)
                values = [tuple(row.get(column, "") for column in CELLINFO_COLUMNS) for row in rows]
                for start in range(0, len(values), 1000):
                    cursor.executemany(
                        f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})",
                        values[start:start + 1000],
                    )
            conn.commit()
            return len(rows)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _ensure_cellinfo_table(cursor, table: str) -> None:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{table}` (
              `CGI` varchar(120) DEFAULT NULL,
              `eNodeBID` int DEFAULT NULL,
              `CellID` int DEFAULT NULL,
              `PLMN` varchar(100) DEFAULT NULL,
              `基站名称` varchar(200) DEFAULT NULL,
              `小区名称` varchar(200) DEFAULT NULL,
              `频点` varchar(50) DEFAULT NULL,
              `带宽` varchar(20) DEFAULT NULL,
              `制式` varchar(50) DEFAULT NULL,
              `功率` varchar(100) DEFAULT NULL,
              `网络` varchar(20) DEFAULT NULL,
              KEY `CGI` (`CGI`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    def _list_dir(self, remote_path: str) -> list[dict[str, Any]]:
        if self.config.remote_data.protocol == "ftp":
            with self.downloader._ftp_client() as ftp:  # noqa: SLF001
                return [
                    {
                        "name": name,
                        "type": "directory" if entry_type == "dir" else "file",
                        "size": size,
                        "path": self._join_remote_path(remote_path, name),
                    }
                    for name, entry_type, size in self.downloader._list_ftp_entries(ftp, remote_path)  # noqa: SLF001
                    if name not in {".", ".."}
                ]

        ssh = self.downloader._sftp_ssh_client()  # noqa: SLF001
        try:
            with ssh.open_sftp() as sftp:
                return [
                    {
                        "name": item.filename,
                        "type": "directory" if stat.S_ISDIR(item.st_mode) else "file",
                        "size": int(getattr(item, "st_size", 0) or 0),
                        "path": self._join_remote_path(remote_path, item.filename),
                    }
                    for item in sftp.listdir_attr(remote_path)
                    if item.filename not in {".", ".."}
                ]
        finally:
            ssh.close()

    def _remote_file_info(self, remote_path: str, size: int) -> RemoteFileInfo:
        return self.downloader._remote_file_info(remote_path, size)  # noqa: SLF001

    @staticmethod
    def _join_remote_path(parent: str, child: str) -> str:
        parent = parent.replace("\\", "/").rstrip("/")
        child = child.replace("\\", "/").strip("/")
        if not parent:
            return child
        if parent == "/":
            return f"/{child}"
        return f"{parent}/{child}"

    def _set_stage(self, stage: str) -> None:
        if hasattr(self.logger, "set_stage"):
            self.logger.set_stage(stage)

    def _log(self, message: str) -> None:
        if self.logger:
            if hasattr(self.logger, "info"):
                self.logger.info(message)
            else:
                self.logger(message)


def refresh_cell_data(app_config: AppConfig, work_dir: Path, logger=None) -> CellDataResult:
    return CellDataProcessor(app_config, work_dir, logger).run()
