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
        self.month_dir_re = re.compile(self.config.month_dir_regex)
        self.day_dir_re = re.compile(self.config.day_dir_regex)
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

    def run_local(self, upload_root: Path) -> CellDataResult:
        self._set_stage("locating")
        local_files = self._select_local_zip_files(upload_root)
        if not local_files:
            raise RuntimeError("未找到可处理的 CellData ZIP 文件")
        self._log(f"已选择 {len(local_files)} 个 CellData ZIP 文件")

        self._set_stage("parsing")
        result = CellDataResult(selected_files=len(local_files))
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
        parts = [part for part in path.split("/") if part]
        replacements = [
            ("{maxyear}", "year", self.year_dir_re, "年份"),
            ("{maxmonth}", "month", self.month_dir_re, "月份"),
            ("{maxday}", "day", self.day_dir_re, "日期"),
        ]
        for token, group_name, pattern, label in replacements:
            token_index = next((index for index, part in enumerate(parts) if token in part), -1)
            if token_index < 0:
                continue
            parent = "/" + "/".join(parts[:token_index]) if token_index else "/"
            values: list[int] = []
            for entry in self._list_dir(parent):
                if entry["type"] != "directory":
                    continue
                match = pattern.search(str(entry["name"]))
                if match:
                    values.append(int(match.group(group_name)))
            if not values:
                raise RuntimeError(f"未找到{label}目录: {parent}")
            parts[token_index] = parts[token_index].replace(token, str(max(values)))
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

    def _select_local_zip_files(self, upload_root: Path) -> list[tuple[SelectedZip, Path]]:
        grouped: dict[str, list[Path]] = {}
        for path in upload_root.rglob("*.zip"):
            if not self.file_name_re.search(path.name):
                continue
            try:
                parent = str(path.parent.relative_to(upload_root)).replace("\\", "/")
            except ValueError:
                parent = ""
            grouped.setdefault("" if parent == "." else parent, []).append(path)

        selected: list[tuple[SelectedZip, Path]] = []
        for parent, paths in sorted(grouped.items(), key=lambda item: item[0]):
            candidates = []
            for path in paths:
                match = self.file_time_re.search(path.name)
                if match:
                    candidates.append((match.group("timestamp"), path))
            if not candidates:
                continue
            timestamp, path = max(candidates, key=lambda item: item[0])
            band = Path(parent).name if parent else ""
            selected_zip = SelectedZip(
                scan_path=str(upload_root),
                band=band,
                remote_file=RemoteFileInfo(
                    path=str(path),
                    relative_path=str(path.relative_to(upload_root)).replace("\\", "/"),
                    parent=parent,
                    name=path.name,
                    size=path.stat().st_size,
                ),
                timestamp=timestamp,
            )
            if not band:
                self._log(f"未从目录名识别频段: {path.name}")
            else:
                self._log(f"{band}: {path.name}")
            selected.append((selected_zip, path))
        return selected

    @staticmethod
    def _download_result():
        from app.services.remote_download import RemoteDownloadResult

        return RemoteDownloadResult()

    def _parse_zip_files(self, local_files: list[tuple[SelectedZip, Path]], result: CellDataResult) -> list[dict[str, str]]:
        mapping = self.config.mapping
        key_config = mapping["key"]
        key_field = str(key_config["field"])
        rows_by_key: dict[str, dict[str, str]] = {}
        self._log(f"开始解压并解析 {len(local_files)} 个 ZIP 文件...")
        for selected, local_path in local_files:
            band_label = selected.band or "未识别频段"
            size_kb = local_path.stat().st_size / 1024 if local_path.exists() else 0
            self._log(f"[{band_label}] 解压 {local_path.name}（{size_kb:.0f} KB）...")
            zip_parsed_before = result.parsed_rows
            zip_skipped_before = result.skipped_rows
            with zipfile.ZipFile(local_path) as zf:
                sources = list(mapping["sources"])
                csv_entries = [info for info in zf.infolist() if Path(info.filename).name.lower().endswith(".csv")]
                self._log(f"  压缩包内含 {len(csv_entries)} 个 CSV 文件")
                for info in csv_entries:
                    name = Path(info.filename).name
                    matching_sources = [
                        source
                        for source in sources
                        if name.startswith(source["file_prefix"]) and (not selected.band or source["band"] == selected.band)
                    ]
                    if not matching_sources:
                        self._log(f"  跳过未匹配规则的文件: {name}")
                        continue
                    if not selected.band and len(matching_sources) > 1:
                        self._log(f"  跳过无法识别频段的文件: {name}")
                        continue
                    for source in matching_sources:
                        raw = zf.read(info.filename)
                        text = self._decode_csv(raw)
                        reader = csv.DictReader(text.splitlines())
                        added = 0
                        skipped = 0
                        for csv_row in reader:
                            row = self._map_row(source["fields"], csv_row)
                            key = self._render_expr(str(key_config["expr"]), row)
                            if not key or "--" in key:
                                result.skipped_rows += 1
                                skipped += 1
                                continue
                            row[key_field] = key
                            rows_by_key[key] = {column: row.get(column, "") for column in CELLINFO_COLUMNS}
                            result.parsed_rows += 1
                            added += 1
                        self._log(f"  解析 {name}（频段 {source.get('band', '') or '通用'}）：有效 {added} 行，跳过 {skipped} 行")
            self._log(
                f"[{band_label}] {local_path.name} 解析完成："
                f"本包有效 {result.parsed_rows - zip_parsed_before} 行，跳过 {result.skipped_rows - zip_skipped_before} 行"
            )
        self._log(
            f"全部解析完成：累计有效 {result.parsed_rows} 行，按 {key_field} 去重后 {len(rows_by_key)} 行，"
            f"累计跳过 {result.skipped_rows} 行"
        )
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
        self._log(f"准备写入表 `{table}`（库 {mysql.dbname}@{mysql.host}:{mysql.port}），共 {len(rows)} 行")
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
        self._log("已连接 CellData 数据库")
        try:
            with conn.cursor() as cursor:
                self._ensure_cellinfo_table(cursor, table)
                self._log(f"已确认表结构 `{table}`")
                cursor.execute(f"TRUNCATE TABLE `{table}`")
                self._log(f"已清空表 `{table}`（TRUNCATE）")
                placeholders = ", ".join(["%s"] * len(CELLINFO_COLUMNS))
                columns = ", ".join(f"`{column}`" for column in CELLINFO_COLUMNS)
                values = [tuple(row.get(column, "") for column in CELLINFO_COLUMNS) for row in rows]
                total = len(values)
                for start in range(0, total, 1000):
                    cursor.executemany(
                        f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})",
                        values[start:start + 1000],
                    )
                    self._log(f"写入中 {min(start + 1000, total)}/{total} 行...")
            conn.commit()
            self._log(f"已提交，成功写入 {len(rows)} 行到 `{table}`")
            return len(rows)
        except Exception as exc:
            conn.rollback()
            self._log(f"写入失败，已回滚: {exc}")
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


def execute_celldata_script(script_path: Path, app_config: AppConfig, logger=None) -> None:
    if not script_path.exists():
        if logger:
            logger.info("CellData 脚本文件不存在，跳过")
        return
    sql_text = script_path.read_text(encoding="utf-8").strip()
    if not sql_text:
        if logger:
            logger.info("CellData 脚本为空，跳过")
        return

    from app.processor import DataProcessor

    statements = DataProcessor.parse_sql_script(sql_text)
    if not statements:
        if logger:
            logger.info("CellData 脚本中没有有效语句，跳过")
        return

    mysql = app_config.cell_data.mysql.normalized()
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
            for i, sql in enumerate(statements, 1):
                preview = sql[:80].replace("\n", " ")
                if logger:
                    logger.info(f"CellData SQL ({i}/{len(statements)}): {preview}...")
                cursor.execute(sql)
                affected = cursor.rowcount if cursor.rowcount >= 0 else 0
                if affected > 0 and logger:
                    logger.info(f"完成，影响 {affected} 行")
        conn.commit()
        if logger:
            logger.success(f"CellData 脚本执行完成，共 {len(statements)} 条语句")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def copy_celldata_tables_to_capacity(app_config: AppConfig, logger=None) -> int:
    cd_mysql = app_config.cell_data.mysql.normalized()
    cap_mysql = app_config.mysql.normalized()

    if (
        cd_mysql.host == cap_mysql.host
        and cd_mysql.port == cap_mysql.port
        and cd_mysql.dbname == cap_mysql.dbname
    ):
        if logger:
            logger.info("CellData 与容量数据库相同，跳过表复制")
        return 0

    cd_conn = pymysql.connect(
        host=cd_mysql.host, port=cd_mysql.port,
        user=cd_mysql.user, password=cd_mysql.passwd,
        database=cd_mysql.dbname, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    cap_conn = pymysql.connect(
        host=cap_mysql.host, port=cap_mysql.port,
        user=cap_mysql.user, password=cap_mysql.passwd,
        database=cap_mysql.dbname, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        local_infile=True, autocommit=False,
    )
    try:
        tables = _list_tables(cd_conn)
        if not tables:
            if logger:
                logger.info("CellData 数据库中没有表，跳过复制")
            return 0

        copied = 0
        for table in tables:
            rows = _copy_one_table(cd_conn, cap_conn, table, logger)
            if rows >= 0:
                copied += 1
        cap_conn.commit()
        if logger:
            logger.success(f"已将 {copied} 张表从 CellData 复制到容量数据库")
        return copied
    except Exception:
        cap_conn.rollback()
        raise
    finally:
        cd_conn.close()
        cap_conn.close()


def _list_tables(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        return [list(row.values())[0] for row in cur.fetchall()]


def _copy_one_table(src_conn, dst_conn, table: str, logger=None) -> int:
    with src_conn.cursor() as cur:
        cur.execute(f"SHOW CREATE TABLE `{table}`")
        row = cur.fetchone()
        create_sql = row.get("Create Table") or list(row.values())[1]

    with src_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS `cnt` FROM `{table}`")
        count = cur.fetchone()["cnt"]

    with dst_conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS `{table}`")
        cur.execute(create_sql)

    if count == 0:
        if logger:
            logger.info(f"复制表 {table}: 0 行（空表）")
        return 0

    with src_conn.cursor() as src_cur:
        src_cur.execute(f"SELECT * FROM `{table}`")
        columns = [desc[0] for desc in src_cur.description]
        col_list = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"

        batch: list[tuple] = []
        inserted = 0
        with dst_conn.cursor() as dst_cur:
            for row in src_cur:
                batch.append(tuple(row.values()))
                if len(batch) >= 5000:
                    dst_cur.executemany(insert_sql, batch)
                    inserted += len(batch)
                    batch.clear()
            if batch:
                dst_cur.executemany(insert_sql, batch)
                inserted += len(batch)

    if logger:
        logger.info(f"复制表 {table}: {inserted} 行")
    return inserted
