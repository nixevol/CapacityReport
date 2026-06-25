"""
配置管理模块
"""
import json
import os
import sys
from copy import deepcopy
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


def _resolve_base_dir() -> Path:
    env_base_dir = os.environ.get("CAPAREPORT_BASE_DIR")
    if env_base_dir:
        return Path(env_base_dir).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _resolve_base_dir()
CACHE_DIR = BASE_DIR / "cache"
CONFIG_FILE = BASE_DIR / "Configure.json"
SQL_SCRIPT = BASE_DIR / "ReportScript.sql"
CELLDATA_SCRIPT = BASE_DIR / "CellDataScript.sql"


@dataclass
class MySQLConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    passwd: str = ""
    dbname: str = "CapacityReport"

    def normalized(self) -> "MySQLConfig":
        try:
            port = int(self.port or 3306)
        except (TypeError, ValueError):
            port = 3306
        return MySQLConfig(
            host=str(self.host or "").strip() or "localhost",
            port=port,
            user=str(self.user or "").strip(),
            passwd=self.passwd or "",
            dbname=str(self.dbname or "").strip(),
        )

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        normalized = self.normalized()
        data = {
            "host": normalized.host,
            "port": normalized.port,
            "user": normalized.user,
            "dbname": normalized.dbname,
        }
        if include_password:
            data["passwd"] = normalized.passwd
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None, default_dbname: str = "CapacityReport") -> "MySQLConfig":
        data = data or {}
        return cls(
            host=str(data.get("host", "localhost")),
            port=data.get("port", 3306),
            user=str(data.get("user", "root")),
            passwd=str(data.get("passwd", "")),
            dbname=str(data.get("dbname", default_dbname)),
        ).normalized()


# Source backends: direct FTP/SFTP, or Metrix storage platform.
SOURCE_TYPES = ("ftp", "sftp", "metrix")
# Warehouse backends: direct MySQL, or Metrix database platform.
WAREHOUSE_TYPES = ("mysql", "metrix")

DEFAULT_CELL_DATA_SCAN_PATHS = [
    "/网优日常优化数据文档/日常性能报表/{maxyear}年/300表",
]
DEFAULT_CELL_DATA_YEAR_DIR_REGEX = r"(?P<year>\d{4})年"
DEFAULT_CELL_DATA_MONTH_DIR_REGEX = r"(?P<month>\d{1,2})月"
DEFAULT_CELL_DATA_DAY_DIR_REGEX = r"(?P<day>\d{1,2})日"
DEFAULT_CELL_DATA_FILE_NAME_REGEX = r"^Result_300_.*\.zip$"
DEFAULT_CELL_DATA_FILE_TIME_REGEX = r"(?P<timestamp>\d{14})(?=\.zip$)"
DEFAULT_CELL_DATA_MAPPING: Dict[str, Any] = {
    "target_table": "cellinfo",
    "key": {"field": "CGI", "expr": "{PLMN}-{eNodeBID}-{CellID}"},
    "sources": [
        {
            "band": "2.6G",
            "file_prefix": "LTE_ITBBU_CellInfo",
            "fields": {
                "eNodeBID": "eNBId",
                "CellID": "cellLocalId",
                "PLMN": "plmn",
                "基站名称": "eNBName",
                "小区名称": "CellName",
                "频点": "frequency",
                "带宽": "bandWidth",
                "制式": "radioMode",
                "功率": "cpSpeRefSigPwr",
                "网络": {"value": "4G"},
            },
        },
        {
            "band": "2.6G",
            "file_prefix": "LTE_SDR_CellInfo",
            "fields": {
                "eNodeBID": "eNBId",
                "CellID": "cellLocalId",
                "PLMN": "plmn",
                "基站名称": "eNBName",
                "小区名称": "cellName",
                "频点": "frequency",
                "带宽": "bandWidth",
                "制式": "radioMode",
                "功率": "cpSpeRefSigPwr",
                "网络": {"value": "4G"},
            },
        },
        {
            "band": "2.6G",
            "file_prefix": "NR_CellInfo",
            "fields": {
                "eNodeBID": "gNBId",
                "CellID": "cellLocalId",
                "PLMN": "plmn",
                "基站名称": "gNBName",
                "小区名称": "CellName",
                "频点": "ssbFrequency",
                "带宽": "carrierBandwidth",
                "制式": {"value": "2.6G"},
                "功率": "powerPerRERef",
                "网络": {"value": "5G"},
            },
        },
        {
            "band": "700M",
            "file_prefix": "LTE_ITBBU_CellInfo",
            "fields": {
                "eNodeBID": "eNBId",
                "CellID": "cellLocalId",
                "PLMN": "plmn",
                "基站名称": "eNBName",
                "小区名称": "CellName",
                "频点": "frequency",
                "带宽": "bandWidth",
                "制式": "radioMode",
                "功率": "cpSpeRefSigPwr",
                "网络": {"value": "4G"},
            },
        },
        {
            "band": "700M",
            "file_prefix": "NR_CellInfo",
            "fields": {
                "eNodeBID": "gNBId",
                "CellID": "cellLocalId",
                "PLMN": "plmn",
                "基站名称": "gNBName",
                "小区名称": "CellName",
                "频点": "ssbFrequency",
                "带宽": "carrierBandwidth",
                "制式": {"value": "700M"},
                "功率": "powerPerRERef",
                "网络": {"value": "5G"},
            },
        },
    ],
}


@dataclass
class MetrixConfig:
    """Connection to a Metrix platform, used when source_type/warehouse_type is 'metrix'.

    Metrix appears in the UI as two connection types ("存储平台"/"数据库平台") that share the
    same base_url + token; storage_id is the file source, database_conn_id + target_database
    are the warehouse.
    """
    base_url: str = "http://host.docker.internal:8000"
    token: str = ""
    storage_id: str = ""
    database_conn_id: str = ""
    target_database: str = ""
    recent_days: int = 7

    def normalized(self) -> "MetrixConfig":
        try:
            recent_days = max(int(self.recent_days), 1)
        except (TypeError, ValueError):
            recent_days = 7
        return MetrixConfig(
            base_url=str(self.base_url or "").strip(),
            token=str(self.token or "").strip(),
            storage_id=str(self.storage_id or "").strip(),
            database_conn_id=str(self.database_conn_id or "").strip(),
            target_database=str(self.target_database or "").strip(),
            recent_days=recent_days,
        )

    def to_dict(self, include_token: bool = False) -> Dict[str, Any]:
        n = self.normalized()
        data = {
            "base_url": n.base_url,
            "storage_id": n.storage_id,
            "database_conn_id": n.database_conn_id,
            "target_database": n.target_database,
            "recent_days": n.recent_days,
        }
        if include_token:
            data["token"] = n.token
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "MetrixConfig":
        data = data or {}
        return cls(
            base_url=str(data.get("base_url", "http://host.docker.internal:8000")),
            token=str(data.get("token", "")),
            storage_id=str(data.get("storage_id", "")),
            database_conn_id=str(data.get("database_conn_id", "")),
            target_database=str(data.get("target_database", "")),
            recent_days=data.get("recent_days", 7),
        ).normalized()


@dataclass
class DataMappingsConfig:
    """Source directories mapped to staging tables."""
    directories: List[Dict[str, str]] = field(
        default_factory=lambda: [
            {"path": "4G", "table": "4G_UD", "ready_rule": "daily"},
            {"path": "5G", "table": "5G_UD", "ready_rule": "daily"},
        ]
    )
    table_field_mappings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def normalized(self) -> "DataMappingsConfig":
        directories = []
        seen = set()
        for item in self.directories or []:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).replace("\\", "/").strip().strip("/")
            table = str(item.get("table", "")).strip()
            ready_rule = str(item.get("ready_rule", "daily")).strip().lower()
            if ready_rule not in {"daily", "auto"}:
                ready_rule = "daily"
            if not path or not table:
                continue
            key = (path, table, ready_rule)
            if key in seen:
                continue
            seen.add(key)
            directories.append({"path": path, "table": table, "ready_rule": ready_rule})

        if not directories:
            directories = [
                {"path": "4G", "table": "4G_UD", "ready_rule": "daily"},
                {"path": "5G", "table": "5G_UD", "ready_rule": "daily"},
            ]

        mappings = {}
        for table_name, fields in (self.table_field_mappings or {}).items():
            if isinstance(fields, list):
                mappings[table_name] = [
                    {k: v for k, v in f.items() if k in ("Source", "Target", "Type")}
                    for f in fields
                    if isinstance(f, dict) and "Source" in f and "Target" in f
                ]

        return DataMappingsConfig(directories=directories, table_field_mappings=mappings)

    def to_dict(self) -> Dict[str, Any]:
        normalized = self.normalized()
        return {
            "directories": normalized.directories,
            "table_field_mappings": normalized.table_field_mappings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "DataMappingsConfig":
        data = data or {}
        directories = data.get("directories", [])
        return cls(
            directories=directories if isinstance(directories, list) else [],
            table_field_mappings=data.get("table_field_mappings", {}) if isinstance(data.get("table_field_mappings"), dict) else {},
        ).normalized()


@dataclass
class AutoSchedulerConfig:
    enabled: bool = False
    check_interval_hours: int = 1
    expected_directories: List[str] = field(default_factory=list)
    week_offset: int = 0

    def normalized(self) -> "AutoSchedulerConfig":
        try:
            check_interval_hours = int(self.check_interval_hours)
        except (TypeError, ValueError):
            check_interval_hours = 1
        try:
            week_offset = int(self.week_offset)
        except (TypeError, ValueError):
            week_offset = 0

        directories = []
        seen = set()
        for directory in self.expected_directories or []:
            normalized = str(directory).replace("\\", "/").strip().strip("/")
            if normalized and normalized not in seen:
                directories.append(normalized)
                seen.add(normalized)

        return AutoSchedulerConfig(
            enabled=bool(self.enabled),
            check_interval_hours=max(check_interval_hours, 1),
            expected_directories=directories,
            week_offset=week_offset,
        )

    def to_dict(self) -> Dict[str, Any]:
        normalized = self.normalized()
        return {
            "enabled": normalized.enabled,
            "check_interval_hours": normalized.check_interval_hours,
            "expected_directories": normalized.expected_directories,
            "week_offset": normalized.week_offset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "AutoSchedulerConfig":
        data = data or {}
        directories = data.get("expected_directories", [])
        return cls(
            enabled=bool(data.get("enabled", False)),
            check_interval_hours=data.get("check_interval_hours", 1),
            expected_directories=directories if isinstance(directories, list) else [],
            week_offset=data.get("week_offset", 0),
        ).normalized()


@dataclass
class RemoteDataConfig:
    enabled: bool = False
    protocol: str = "sftp"
    host: str = ""
    port: int = 22
    user: str = ""
    passwd: str = ""
    remote_dir: str = "/"
    passive: bool = True
    timeout: int = 30
    auto_delete_source: bool = False
    auto_scheduler: AutoSchedulerConfig = field(default_factory=AutoSchedulerConfig)

    def normalized(self) -> "RemoteDataConfig":
        protocol = self.protocol.lower().strip()
        if protocol not in {"ftp", "sftp"}:
            protocol = "sftp"

        port = self.port or (22 if protocol == "sftp" else 21)
        scheduler = self.auto_scheduler.normalized()
        return RemoteDataConfig(
            enabled=bool(self.enabled) or scheduler.enabled,
            protocol=protocol,
            host=self.host.strip(),
            port=port,
            user=self.user.strip(),
            passwd=self.passwd,
            remote_dir=(self.remote_dir or "/").strip() or "/",
            passive=bool(self.passive),
            timeout=max(int(self.timeout or 30), 1),
            auto_delete_source=bool(self.auto_delete_source) or scheduler.enabled,
            auto_scheduler=scheduler,
        )

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        data = {
            "enabled": self.enabled,
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "remote_dir": self.remote_dir,
            "passive": self.passive,
            "timeout": self.timeout,
            "auto_delete_source": self.auto_delete_source,
            "auto_scheduler": self.auto_scheduler.normalized().to_dict(),
        }
        if include_password:
            data["passwd"] = self.passwd
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "RemoteDataConfig":
        data = data or {}
        protocol = str(data.get("protocol", "sftp")).lower()
        default_port = 22 if protocol == "sftp" else 21
        try:
            port = int(data.get("port") or default_port)
        except (TypeError, ValueError):
            port = default_port
        try:
            timeout = int(data.get("timeout") or 30)
        except (TypeError, ValueError):
            timeout = 30
        return cls(
            enabled=bool(data.get("enabled", False)),
            protocol=protocol,
            host=str(data.get("host", "")),
            port=port,
            user=str(data.get("user", "")),
            passwd=str(data.get("passwd", "")),
            remote_dir=str(data.get("remote_dir", "/")),
            passive=bool(data.get("passive", True)),
            timeout=timeout,
            auto_delete_source=bool(data.get("auto_delete_source", False)),
            auto_scheduler=AutoSchedulerConfig.from_dict(data.get("auto_scheduler")),
        ).normalized()


@dataclass
class CellDataConfig:
    """CellData side data source and database connection used by later processing steps."""
    remote_data: RemoteDataConfig = field(
        default_factory=lambda: RemoteDataConfig(
            enabled=False,
            protocol="sftp",
            remote_dir="/",
        )
    )
    mysql: MySQLConfig = field(default_factory=lambda: MySQLConfig(dbname="celldata"))
    scan_paths: List[str] = field(default_factory=lambda: list(DEFAULT_CELL_DATA_SCAN_PATHS))
    year_dir_regex: str = DEFAULT_CELL_DATA_YEAR_DIR_REGEX
    month_dir_regex: str = DEFAULT_CELL_DATA_MONTH_DIR_REGEX
    day_dir_regex: str = DEFAULT_CELL_DATA_DAY_DIR_REGEX
    file_name_regex: str = DEFAULT_CELL_DATA_FILE_NAME_REGEX
    file_time_regex: str = DEFAULT_CELL_DATA_FILE_TIME_REGEX
    mapping: Dict[str, Any] = field(default_factory=lambda: deepcopy(DEFAULT_CELL_DATA_MAPPING))

    def normalized(self) -> "CellDataConfig":
        scan_paths = []
        seen = set()
        for path in self.scan_paths or []:
            normalized = str(path).replace("\\", "/").strip()
            if normalized and normalized not in seen:
                scan_paths.append(normalized)
                seen.add(normalized)
        if not scan_paths:
            scan_paths = list(DEFAULT_CELL_DATA_SCAN_PATHS)

        mapping = self.mapping if isinstance(self.mapping, dict) and self.mapping else deepcopy(DEFAULT_CELL_DATA_MAPPING)
        return CellDataConfig(
            remote_data=self.remote_data.normalized(),
            mysql=self.mysql.normalized(),
            scan_paths=scan_paths,
            year_dir_regex=str(self.year_dir_regex or DEFAULT_CELL_DATA_YEAR_DIR_REGEX).strip() or DEFAULT_CELL_DATA_YEAR_DIR_REGEX,
            month_dir_regex=str(self.month_dir_regex or DEFAULT_CELL_DATA_MONTH_DIR_REGEX).strip() or DEFAULT_CELL_DATA_MONTH_DIR_REGEX,
            day_dir_regex=str(self.day_dir_regex or DEFAULT_CELL_DATA_DAY_DIR_REGEX).strip() or DEFAULT_CELL_DATA_DAY_DIR_REGEX,
            file_name_regex=str(self.file_name_regex or DEFAULT_CELL_DATA_FILE_NAME_REGEX).strip() or DEFAULT_CELL_DATA_FILE_NAME_REGEX,
            file_time_regex=str(self.file_time_regex or DEFAULT_CELL_DATA_FILE_TIME_REGEX).strip() or DEFAULT_CELL_DATA_FILE_TIME_REGEX,
            mapping=mapping,
        )

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        normalized = self.normalized()
        return {
            "remote_data": normalized.remote_data.to_dict(include_password=include_password),
            "mysql": normalized.mysql.to_dict(include_password=include_password),
            "scan_paths": normalized.scan_paths,
            "year_dir_regex": normalized.year_dir_regex,
            "month_dir_regex": normalized.month_dir_regex,
            "day_dir_regex": normalized.day_dir_regex,
            "file_name_regex": normalized.file_name_regex,
            "file_time_regex": normalized.file_time_regex,
            "mapping": normalized.mapping,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "CellDataConfig":
        data = data or {}
        default = cls()
        remote_data = data.get("RemoteData") or data.get("remote_data")
        mysql_data = data.get("MySQL_DBInfo") or data.get("mysql")
        return cls(
            remote_data=RemoteDataConfig.from_dict(remote_data) if isinstance(remote_data, dict) else default.remote_data,
            mysql=MySQLConfig.from_dict(mysql_data, default_dbname="celldata") if isinstance(mysql_data, dict) else default.mysql,
            scan_paths=data.get("scan_paths", default.scan_paths) if isinstance(data.get("scan_paths", default.scan_paths), list) else default.scan_paths,
            year_dir_regex=str(data.get("year_dir_regex", default.year_dir_regex)),
            month_dir_regex=str(data.get("month_dir_regex", default.month_dir_regex)),
            day_dir_regex=str(data.get("day_dir_regex", default.day_dir_regex)),
            file_name_regex=str(data.get("file_name_regex", default.file_name_regex)),
            file_time_regex=str(data.get("file_time_regex", default.file_time_regex)),
            mapping=data.get("mapping", default.mapping) if isinstance(data.get("mapping", default.mapping), dict) else default.mapping,
        ).normalized()


@dataclass
class HistoryRetentionConfig:
    enabled: bool = False
    keep_count: int = 20

    def normalized(self) -> "HistoryRetentionConfig":
        try:
            keep_count = int(self.keep_count)
        except (TypeError, ValueError):
            keep_count = 20

        return HistoryRetentionConfig(
            enabled=bool(self.enabled),
            keep_count=max(keep_count, 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        normalized = self.normalized()
        return {
            "enabled": normalized.enabled,
            "keep_count": normalized.keep_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "HistoryRetentionConfig":
        data = data or {}
        return cls(
            enabled=bool(data.get("enabled", False)),
            keep_count=data.get("keep_count", 20),
        ).normalized()


def _normalize_source_type(value: Any, protocol: str = "sftp") -> str:
    text = str(value or "").strip().lower()
    if text in SOURCE_TYPES:
        return text
    # Back-compat: no explicit source type means direct remote, pick its protocol.
    return "ftp" if str(protocol).strip().lower() == "ftp" else "sftp"


def _normalize_warehouse_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in WAREHOUSE_TYPES else "mysql"


@dataclass
class AppConfig:
    update: str = ""
    source_type: str = "sftp"
    warehouse_type: str = "mysql"
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
    metrix: MetrixConfig = field(default_factory=MetrixConfig)
    data_mappings: DataMappingsConfig = field(default_factory=DataMappingsConfig)
    remote_data: RemoteDataConfig = field(default_factory=RemoteDataConfig)
    cell_data: CellDataConfig = field(default_factory=CellDataConfig)
    history_retention: HistoryRetentionConfig = field(default_factory=HistoryRetentionConfig)
    sheet_filter: List[str] = field(default_factory=list)
    extract_fields: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls) -> "AppConfig":
        """从 Configure.json 加载配置"""
        if not CONFIG_FILE.exists():
            return cls()

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        mysql_config = MySQLConfig.from_dict(data.get("MySQL_DBInfo"))
        remote_config = RemoteDataConfig.from_dict(data.get("RemoteData"))
        metrix_config = MetrixConfig.from_dict(data.get("Metrix"))
        data_mappings = DataMappingsConfig.from_dict(data.get("DataMappings"))
        cell_data = CellDataConfig.from_dict(data.get("CellData"))
        history_retention = HistoryRetentionConfig.from_dict(data.get("HistoryRetention"))

        return cls(
            update=data.get("Update", ""),
            source_type=_normalize_source_type(data.get("SourceType"), remote_config.protocol),
            warehouse_type=_normalize_warehouse_type(data.get("WarehouseType")),
            mysql=mysql_config,
            metrix=metrix_config,
            data_mappings=data_mappings,
            remote_data=remote_config,
            cell_data=cell_data,
            history_retention=history_retention,
            sheet_filter=data.get("SheetFilter", []),
            extract_fields=data.get("ExtractField", [])
        )

    def save(self):
        """保存配置到 Configure.json，并自动更新 Update 时间"""
        self.update = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        data = self.to_file_dict()

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def to_file_dict(self) -> Dict[str, Any]:
        """转换为配置文件结构（包含敏感字段，用于保存和下载）"""
        return {
            "Update": self.update,
            "SourceType": self.source_type,
            "WarehouseType": self.warehouse_type,
            "MySQL_DBInfo": self.mysql.normalized().to_dict(include_password=True),
            "Metrix": self.metrix.normalized().to_dict(include_token=True),
            "DataMappings": self.data_mappings.normalized().to_dict(),
            "RemoteData": self.remote_data.normalized().to_dict(include_password=True),
            "CellData": self.cell_data.normalized().to_dict(include_password=True),
            "HistoryRetention": self.history_retention.normalized().to_dict(),
            "SheetFilter": self.sheet_filter,
            "ExtractField": self.extract_fields
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于返回给前端，隐藏密码）"""
        return {
            "update": self.update,
            "source_type": self.source_type,
            "warehouse_type": self.warehouse_type,
            "mysql": self.mysql.normalized().to_dict(),
            "metrix": self.metrix.normalized().to_dict(),
            "data_mappings": self.data_mappings.normalized().to_dict(),
            "remote_data": self.remote_data.normalized().to_dict(),
            "cell_data": self.cell_data.normalized().to_dict(),
            "history_retention": self.history_retention.normalized().to_dict(),
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }
    
    def to_dict_full(self) -> Dict[str, Any]:
        """转换为完整字典（包含密码，用于编辑时回显）"""
        return {
            "update": self.update,
            "source_type": self.source_type,
            "warehouse_type": self.warehouse_type,
            "mysql": self.mysql.normalized().to_dict(include_password=True),
            "metrix": self.metrix.normalized().to_dict(include_token=True),
            "data_mappings": self.data_mappings.normalized().to_dict(),
            "remote_data": self.remote_data.normalized().to_dict(include_password=True),
            "cell_data": self.cell_data.normalized().to_dict(include_password=True),
            "history_retention": self.history_retention.normalized().to_dict(),
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }


# 确保缓存目录存在
CACHE_DIR.mkdir(exist_ok=True)
