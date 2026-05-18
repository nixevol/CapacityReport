"""
配置管理模块
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


BASE_DIR = Path(__file__).resolve().parent.parent
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

    def normalized(self) -> "RemoteDataConfig":
        protocol = self.protocol.lower().strip()
        if protocol not in {"ftp", "sftp"}:
            protocol = "sftp"

        port = self.port or (22 if protocol == "sftp" else 21)
        return RemoteDataConfig(
            enabled=bool(self.enabled),
            protocol=protocol,
            host=self.host.strip(),
            port=port,
            user=self.user.strip(),
            passwd=self.passwd,
            remote_dir=(self.remote_dir or "/").strip() or "/",
            passive=bool(self.passive),
            timeout=max(int(self.timeout or 30), 1),
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
        ).normalized()


@dataclass
class AppConfig:
    update: str = ""
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
    remote_data: RemoteDataConfig = field(default_factory=RemoteDataConfig)
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
        
        return cls(
            update=data.get("Update", ""),
            mysql=mysql_config,
            remote_data=remote_config,
            sheet_filter=data.get("SheetFilter", []),
            extract_fields=data.get("ExtractField", [])
        )
    
    def save(self):
        """保存配置到 Configure.json，并自动更新 Update 时间"""
        self.update = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        
        data = {
            "Update": self.update,
            "MySQL_DBInfo": {
                "host": self.mysql.host,
                "port": self.mysql.port,
                "user": self.mysql.user,
                "passwd": self.mysql.passwd,
                "dbname": self.mysql.dbname
            },
            "RemoteData": self.remote_data.normalized().to_dict(include_password=True),
            "SheetFilter": self.sheet_filter,
            "ExtractField": self.extract_fields
        }
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于返回给前端，隐藏密码）"""
        return {
            "update": self.update,
            "mysql": {
                "host": self.mysql.host,
                "port": self.mysql.port,
                "user": self.mysql.user,
                "dbname": self.mysql.dbname
            },
            "remote_data": self.remote_data.normalized().to_dict(),
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }
    
    def to_dict_full(self) -> Dict[str, Any]:
        """转换为完整字典（包含密码，用于编辑时回显）"""
        return {
            "update": self.update,
            "mysql": {
                "host": self.mysql.host,
                "port": self.mysql.port,
                "user": self.mysql.user,
                "passwd": self.mysql.passwd,
                "dbname": self.mysql.dbname
            },
            "remote_data": self.remote_data.normalized().to_dict(include_password=True),
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }


# 确保缓存目录存在
CACHE_DIR.mkdir(exist_ok=True)
