"""
配置管理模块
"""
import json
import os
import sys
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


@dataclass
class MySQLConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    passwd: str = ""
    dbname: str = "CapacityReport"


# Source backends: direct FTP/SFTP, or Metrix storage platform.
SOURCE_TYPES = ("ftp", "sftp", "metrix")
# Warehouse backends: direct MySQL, or Metrix database platform.
WAREHOUSE_TYPES = ("mysql", "metrix")


@dataclass
class MetrixConfig:
    """Connection to a Metrix platform, used when source_type/warehouse_type is 'metrix'.

    Metrix appears in the UI as two connection types ("存储平台"/"数据库平台") that share the
    same base_url + token; storage_id is the file source, database_conn_id + target_database
    are the warehouse. data_dir_to_table maps data sub-dirs to staging tables (Metrix mode only).
    """
    base_url: str = "http://host.docker.internal:8000"
    token: str = ""
    storage_id: str = ""
    database_conn_id: str = ""
    target_database: str = ""
    recent_days: int = 7
    data_dir_to_table: Dict[str, str] = field(default_factory=lambda: {"4G": "4G_UD", "5G": "5G_UD"})

    def normalized(self) -> "MetrixConfig":
        try:
            recent_days = max(int(self.recent_days), 1)
        except (TypeError, ValueError):
            recent_days = 7
        mapping = {
            str(k).strip(): str(v).strip()
            for k, v in (self.data_dir_to_table or {}).items()
            if str(k).strip() and str(v).strip()
        }
        return MetrixConfig(
            base_url=str(self.base_url or "").strip(),
            token=str(self.token or "").strip(),
            storage_id=str(self.storage_id or "").strip(),
            database_conn_id=str(self.database_conn_id or "").strip(),
            target_database=str(self.target_database or "").strip(),
            recent_days=recent_days,
            data_dir_to_table=mapping or {"4G": "4G_UD", "5G": "5G_UD"},
        )

    def to_dict(self, include_token: bool = False) -> Dict[str, Any]:
        n = self.normalized()
        data = {
            "base_url": n.base_url,
            "storage_id": n.storage_id,
            "database_conn_id": n.database_conn_id,
            "target_database": n.target_database,
            "recent_days": n.recent_days,
            "data_dir_to_table": n.data_dir_to_table,
        }
        if include_token:
            data["token"] = n.token
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "MetrixConfig":
        data = data or {}
        mapping = data.get("data_dir_to_table")
        return cls(
            base_url=str(data.get("base_url", "http://host.docker.internal:8000")),
            token=str(data.get("token", "")),
            storage_id=str(data.get("storage_id", "")),
            database_conn_id=str(data.get("database_conn_id", "")),
            target_database=str(data.get("target_database", "")),
            recent_days=data.get("recent_days", 7),
            data_dir_to_table=mapping if isinstance(mapping, dict) else {"4G": "4G_UD", "5G": "5G_UD"},
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
class RJDataConfig:
    """RJ数据配置 - 周数据处理"""
    enabled: bool = False
    weekly_directories: List[str] = field(default_factory=list)
    # 字段映射: {表名: [{Source, Target, Type}, ...]}
    table_field_mappings: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def normalized(self) -> "RJDataConfig":
        directories = []
        seen = set()
        for d in self.weekly_directories or []:
            normalized = str(d).replace("\\", "/").strip().strip("/")
            if normalized and normalized not in seen:
                directories.append(normalized)
                seen.add(normalized)

        # 标准化字段映射
        mappings = {}
        for table_name, fields in (self.table_field_mappings or {}).items():
            if isinstance(fields, list):
                mappings[table_name] = [
                    {k: v for k, v in f.items() if k in ("Source", "Target", "Type")}
                    for f in fields
                    if isinstance(f, dict) and "Source" in f and "Target" in f
                ]

        return RJDataConfig(
            enabled=bool(self.enabled),
            weekly_directories=directories,
            table_field_mappings=mappings,
        )

    def to_dict(self) -> Dict[str, Any]:
        normalized = self.normalized()
        return {
            "enabled": normalized.enabled,
            "weekly_directories": normalized.weekly_directories,
            "table_field_mappings": normalized.table_field_mappings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "RJDataConfig":
        data = data or {}
        return cls(
            enabled=bool(data.get("enabled", False)),
            weekly_directories=data.get("weekly_directories", []) if isinstance(data.get("weekly_directories"), list) else [],
            table_field_mappings=data.get("table_field_mappings", {}) if isinstance(data.get("table_field_mappings"), dict) else {},
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
    remote_data: RemoteDataConfig = field(default_factory=RemoteDataConfig)
    history_retention: HistoryRetentionConfig = field(default_factory=HistoryRetentionConfig)
    rj_data: RJDataConfig = field(default_factory=RJDataConfig)
    sheet_filter: List[str] = field(default_factory=list)
    extract_fields: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls) -> "AppConfig":
        """从 Configure.json 加载配置"""
        if not CONFIG_FILE.exists():
            return cls()

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        mysql_data = data.get("MySQL_DBInfo", {})
        mysql_config = MySQLConfig(
            host=mysql_data.get("host", "localhost"),
            port=mysql_data.get("port", 3306),
            user=mysql_data.get("user", "root"),
            passwd=mysql_data.get("passwd", ""),
            dbname=mysql_data.get("dbname", "CapacityReport")
        )
        remote_config = RemoteDataConfig.from_dict(data.get("RemoteData"))
        metrix_config = MetrixConfig.from_dict(data.get("Metrix"))
        history_retention = HistoryRetentionConfig.from_dict(data.get("HistoryRetention"))
        rj_data = RJDataConfig.from_dict(data.get("RJData"))

        return cls(
            update=data.get("Update", ""),
            source_type=_normalize_source_type(data.get("SourceType"), remote_config.protocol),
            warehouse_type=_normalize_warehouse_type(data.get("WarehouseType")),
            mysql=mysql_config,
            metrix=metrix_config,
            remote_data=remote_config,
            history_retention=history_retention,
            rj_data=rj_data,
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
            "MySQL_DBInfo": {
                "host": self.mysql.host,
                "port": self.mysql.port,
                "user": self.mysql.user,
                "passwd": self.mysql.passwd,
                "dbname": self.mysql.dbname
            },
            "Metrix": self.metrix.normalized().to_dict(include_token=True),
            "RemoteData": self.remote_data.normalized().to_dict(include_password=True),
            "HistoryRetention": self.history_retention.normalized().to_dict(),
            "RJData": self.rj_data.normalized().to_dict(),
            "SheetFilter": self.sheet_filter,
            "ExtractField": self.extract_fields
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于返回给前端，隐藏密码）"""
        return {
            "update": self.update,
            "source_type": self.source_type,
            "warehouse_type": self.warehouse_type,
            "mysql": {
                "host": self.mysql.host,
                "port": self.mysql.port,
                "user": self.mysql.user,
                "dbname": self.mysql.dbname
            },
            "metrix": self.metrix.normalized().to_dict(),
            "remote_data": self.remote_data.normalized().to_dict(),
            "history_retention": self.history_retention.normalized().to_dict(),
            "rj_data": self.rj_data.normalized().to_dict(),
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }
    
    def to_dict_full(self) -> Dict[str, Any]:
        """转换为完整字典（包含密码，用于编辑时回显）"""
        return {
            "update": self.update,
            "source_type": self.source_type,
            "warehouse_type": self.warehouse_type,
            "mysql": {
                "host": self.mysql.host,
                "port": self.mysql.port,
                "user": self.mysql.user,
                "passwd": self.mysql.passwd,
                "dbname": self.mysql.dbname
            },
            "metrix": self.metrix.normalized().to_dict(include_token=True),
            "remote_data": self.remote_data.normalized().to_dict(include_password=True),
            "history_retention": self.history_retention.normalized().to_dict(),
            "rj_data": self.rj_data.normalized().to_dict(),
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }


# 确保缓存目录存在
CACHE_DIR.mkdir(exist_ok=True)
