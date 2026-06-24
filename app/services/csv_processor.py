"""纯数据处理流水线（容器版，无数据库代码）。

输入：包含已下载周 ZIP/CSV/Excel 的工作目录。
输出：每张暂存表一个规范化 CSV（{表名: csv 路径}）；由平台数据库导入 API 建表入库，
      再由平台 run-script 跑报表 SQL 生成结果表。这里不含任何数据库/LOAD DATA 代码。
"""
from __future__ import annotations

import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import chardet
import pandas as pd

from app.utils.file_dates import select_recent_items_by_directory

ZERO_TEXTS = {"", "-", "--", "—", "–", "NA", "N/A", "NULL", "NONE", "NAN", "\\N"}
DATETIME_FORMATS = [
    "ISO8601",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y年%m月%d日 %H:%M:%S",
    "%Y年%m月%d日",
    "%Y%m%d%H%M%S",
    "%Y%m%d",
]
MAX_WORKERS = 8


class CsvProcessor:
    def __init__(self, work_dir: Path, config: dict, log: Callable[[str], None]):
        self.work_dir = Path(work_dir)
        self.config = config
        self.log = log
        self.recent_days = int(config.get("recent_days", 7))
        self.sheet_filter = set(config.get("sheet_filter", []))
        self.directories = _build_directory_mappings(config.get("directories") or [])
        self.field_map, self.type_map = _build_global_map(config.get("extract_fields", []))
        self.table_maps = _build_table_maps(config.get("table_field_mappings") or {})
        self.out_dir = self.work_dir / ".out"

    def process(self) -> dict[str, Path]:
        self._unzip_files()
        self._excel_to_csv()
        return self._build_table_csvs()

    # --- step 1: unzip ---------------------------------------------------
    def _unzip_files(self) -> None:
        zips = self._filter_recent(list(self.work_dir.rglob("*.zip")), "ZIP")
        self.log(f"解压 ZIP: {len(zips)} 个")
        for zip_file in zips:
            try:
                _extract_zip(zip_file, self.log)
            except Exception as exc:  # noqa: BLE001 - keep going on a bad archive
                self.log(f"[WARN] 解压失败 {zip_file.name}: {exc}")

    # --- step 2: excel -> csv -------------------------------------------
    def _excel_to_csv(self) -> None:
        excels = self._filter_recent(list(self._scan(self.work_dir, (".xlsx", ".xls"))), "Excel")
        if not excels:
            return
        self.log(f"Excel 转 CSV: {len(excels)} 个文件")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._one_excel, f): f for f in excels}
            for future in as_completed(futures):
                excel = futures[future]
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    self.log(f"[WARN] Excel 处理失败 {excel.name}: {exc}")

    def _one_excel(self, excel_file: Path) -> None:
        xl = pd.ExcelFile(excel_file, engine="openpyxl")
        try:
            for sheet in xl.sheet_names:
                if sheet in self.sheet_filter:
                    continue
                out = excel_file.parent / f"{excel_file.stem}_{sheet}.csv"
                xl.parse(sheet).to_csv(out, index=False, encoding="utf-8")
        finally:
            xl.close()

    # --- step 3: build one normalized CSV per staging table -------------
    def _build_table_csvs(self) -> dict[str, Path]:
        data_dirs = self._find_data_dirs()
        if not data_dirs:
            self.log("[WARN] 未找到任何数据目录")
            return {}
        self.out_dir.mkdir(parents=True, exist_ok=True)
        result: dict[str, Path] = {}
        for table, directories in data_dirs.items():
            csv_files: list[Path] = []
            for directory in directories:
                csv_files.extend(self._filter_recent(list(self._scan(directory, (".csv",))), "CSV", root=directory))
            if not csv_files:
                continue
            field_map, type_map = self._maps_for_table(table)
            out_path = self.out_dir / f"{table}.csv"
            rows = self._write_table_csv(table, csv_files, field_map, type_map, out_path)
            if rows > 0:
                result[table] = out_path
                self.log(f"暂存表 {table}: {rows} 行 -> {out_path.name}")
        return result

    def _write_table_csv(self, table, csv_files, field_map, type_map, out_path: Path) -> int:
        # First pass: union of target columns across this table's CSV files.
        union: list[str] = []
        seen: set[str] = set()
        frames: list[tuple[Path, list[str]]] = []
        for csv_file in csv_files:
            headers = _read_headers(csv_file)
            targets = _ordered_targets(headers, field_map)
            if not targets:
                continue
            frames.append((csv_file, headers))
            for target in targets:
                if target not in seen:
                    seen.add(target)
                    union.append(target)
        if not union:
            return 0

        total = 0
        header_written = False
        for csv_file, _headers in frames:
            df = self._normalize(csv_file, field_map, type_map, union)
            if df is None or df.empty:
                continue
            df.to_csv(out_path, index=False, header=not header_written, mode="w" if not header_written else "a", encoding="utf-8")
            header_written = True
            total += len(df)
        return total

    def _normalize(self, csv_file: Path, field_map, type_map, union: list[str]):
        try:
            df = pd.read_csv(
                csv_file,
                encoding=_detect_encoding(csv_file),
                dtype=str,
                na_values=[""],
                keep_default_na=False,
                low_memory=True,
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"[WARN] 读取 CSV 失败 {csv_file.name}: {exc}")
            return None

        col_map: dict[str, str] = {}
        mapped: set[str] = set()
        for col in df.columns:
            target = field_map.get(col)
            if target and target not in mapped:
                col_map[col] = target
                mapped.add(target)
        if not col_map:
            return None

        out = df[list(col_map.keys())].copy()
        out.columns = list(col_map.values())
        out = out.fillna("")
        for col in out.columns:
            col_type = type_map.get(col, "string")
            if col_type == "datetime":
                out[col] = _convert_datetime(out[col])
            elif col_type == "int":
                out[col] = _convert_int(out[col])
            elif col_type == "float":
                out[col] = _convert_float(out[col])
            else:
                out[col] = out[col].astype("string").str.replace("%", "", regex=False).str.slice(0, 255)
        # Reindex to the shared union columns; fill missing per type so numeric
        # staging columns never carry '' (the report SQL re-types them later).
        for col in union:
            if col not in out.columns:
                out[col] = "0" if type_map.get(col) in ("int", "float") else ""
        return out[union]

    # --- directory detection --------------------------------------------
    def _find_data_dirs(self) -> dict[str, list[Path]]:
        data_dirs: dict[str, list[Path]] = {}
        for item in self.directories:
            directory = self.work_dir / item["path"]
            if directory.exists() and directory.is_dir():
                _add_data_dir(data_dirs, item["table"], directory)
        return data_dirs

    def _maps_for_table(self, table: str):
        if table in self.table_maps:
            return self.table_maps[table]
        return self.field_map, self.type_map

    # --- helpers ---------------------------------------------------------
    def _scan(self, directory: Path, extensions: tuple[str, ...]):
        for ext in extensions:
            yield from directory.rglob(f"*{ext}")

    def _filter_recent(self, files: list[Path], label: str, root: Path | None = None) -> list[Path]:
        if not files:
            return files
        base = (root or self.work_dir).resolve()

        def parent_key(file_path: Path) -> str:
            try:
                parent = file_path.parent.resolve().relative_to(base)
            except ValueError:
                parent = file_path.parent
            text = str(parent).replace("\\", "/")
            return "" if text == "." else text

        selected, summaries = select_recent_items_by_directory(
            files,
            parent_key=parent_key,
            name_key=lambda f: f.name,
            days=self.recent_days,
        )
        for summary in summaries:
            if summary.skipped_count and summary.start_date and summary.max_date:
                self.log(
                    f"{label} {summary.directory or '.'}: 取 {summary.start_date}~{summary.max_date} "
                    f"{summary.selected_count}/{summary.total_count}，跳过 {summary.skipped_count} 个旧文件"
                )
        return sorted(selected)


def _build_global_map(extract_fields: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    field_map: dict[str, str] = {}
    type_map: dict[str, str] = {}
    for field in extract_fields:
        target = field.get("Field")
        if not target:
            continue
        type_map[target] = field.get("Type", "string")
        for source in field.get("Extract", []):
            field_map[source] = target
    return field_map, type_map


def _build_directory_mappings(items: list[dict]) -> list[dict[str, str]]:
    mappings: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).replace("\\", "/").strip().strip("/")
        table = str(item.get("table", "")).strip()
        if not path or not table:
            continue
        key = (path, table)
        if key in seen:
            continue
        seen.add(key)
        mappings.append({"path": path, "table": table})
    return mappings


def _add_data_dir(data_dirs: dict[str, list[Path]], table: str, directory: Path) -> None:
    existing = data_dirs.setdefault(table, [])
    resolved = directory.resolve()
    if all(path.resolve() != resolved for path in existing):
        existing.append(directory)


def _build_table_maps(table_field_mappings: dict) -> dict[str, tuple[dict[str, str], dict[str, str]]]:
    maps: dict[str, tuple[dict[str, str], dict[str, str]]] = {}
    for table, fields in table_field_mappings.items():
        field_map: dict[str, str] = {}
        type_map: dict[str, str] = {}
        for field in fields:
            source = field.get("Source")
            target = field.get("Target")
            if source and target:
                field_map[source] = target
                type_map[target] = field.get("Type", "string")
        maps[table] = (field_map, type_map)
    return maps


def _ordered_targets(headers: list[str], field_map: dict[str, str]) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for col in headers:
        target = field_map.get(col)
        if target and target not in seen:
            seen.add(target)
            targets.append(target)
    return targets


def _read_headers(csv_file: Path) -> list[str]:
    try:
        df = pd.read_csv(csv_file, encoding=_detect_encoding(csv_file), nrows=0, dtype=str)
        return list(df.columns)
    except Exception:  # noqa: BLE001
        return []


def _detect_encoding(file_path: Path) -> str:
    with open(file_path, "rb") as handle:
        result = chardet.detect(handle.read(8192))
    encoding = (result.get("encoding") or "utf-8").lower()
    if "utf" in encoding:
        return "utf-8"
    if "gb" in encoding:
        return "gbk"
    return "utf-8"


def _extract_zip(zip_file: Path, log: Callable[[str], None]) -> None:
    for enc in ("utf-8", "gbk", "cp437"):
        try:
            with zipfile.ZipFile(zip_file, "r", metadata_encoding=enc) as zf:
                _extract_members(zf, zip_file.parent, log)
            return
        except (UnicodeDecodeError, zipfile.BadZipFile):
            continue
    raise RuntimeError("无法解压（编码检测失败）")


def _extract_members(zf: zipfile.ZipFile, target_dir: Path, log: Callable[[str], None]) -> None:
    root = target_dir.resolve()
    for member in zf.infolist():
        name = member.filename.replace("\\", "/")
        target = (root / name).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            log(f"[WARN] 跳过不安全的 ZIP 条目: {member.filename}")
            continue
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as source, target.open("wb") as out:
            shutil.copyfileobj(source, out)


def _clean_numeric_text(series: pd.Series) -> pd.Series:
    return (
        series.str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("，", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("％", "", regex=False)
        .str.replace("\t", "", regex=False)
        .str.replace(" ", "", regex=False)
    )


def _numeric_series(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    has_percent = text.str.contains(r"[%％]", regex=True, na=False)
    cleaned = _clean_numeric_text(text)
    zero_mask = cleaned.isna() | cleaned.str.upper().isin(ZERO_TEXTS)
    numeric = pd.to_numeric(cleaned.mask(zero_mask, "0"), errors="coerce").fillna(0)
    numeric[has_percent & numeric.notna()] = numeric[has_percent & numeric.notna()] / 100
    return numeric


def _convert_int(series: pd.Series) -> pd.Series:
    try:
        rounded = _numeric_series(series).round()
        return pd.Series([int(v) for v in rounded], index=series.index, dtype=object)
    except Exception:  # noqa: BLE001
        return series


def _convert_float(series: pd.Series) -> pd.Series:
    try:
        numeric = _numeric_series(series)
        return pd.Series([float(v) for v in numeric], index=series.index, dtype=object)
    except Exception:  # noqa: BLE001
        return series


def _convert_datetime(series: pd.Series) -> pd.Series:
    try:
        valid = series.notna() & (series != "") & (series.astype(str).str.strip() != "")
        if not valid.any():
            return pd.Series([None] * len(series), index=series.index)
        parsed = pd.Series([pd.NaT] * len(series), index=series.index)
        remaining = valid.copy()
        for fmt in DATETIME_FORMATS:
            if not remaining.any():
                break
            try:
                temp = pd.to_datetime(series[remaining], errors="coerce", format=fmt)
            except Exception:  # noqa: BLE001
                continue
            ok = temp.notna()
            if ok.any():
                idx = remaining[remaining].index[ok]
                parsed.loc[idx] = temp[ok].values
                remaining.loc[idx] = False
        if remaining.any():
            try:
                temp = pd.to_datetime(series[remaining], errors="coerce", format="mixed", dayfirst=False)
                ok = temp.notna()
                if ok.any():
                    idx = remaining[remaining].index[ok]
                    parsed.loc[idx] = temp[ok].values
            except Exception:  # noqa: BLE001
                pass
        return parsed.dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return series
