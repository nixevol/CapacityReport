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
class AppConfig:
    update: str = ""
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
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
        
        return cls(
            update=data.get("Update", ""),
            mysql=mysql_config,
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
            "sheet_filter": self.sheet_filter,
            "extract_fields": self.extract_fields
        }


# 确保缓存目录存在
CACHE_DIR.mkdir(exist_ok=True)
