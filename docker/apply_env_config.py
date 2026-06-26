# -*- coding: utf-8 -*-
"""首次播种 Configure.json 后，按容器环境变量改写「数据库 / SFTP 连接」。

仅在 entrypoint 首次创建 /data/Configure.json 时调用一次；用户之后在界面里的修改不会被覆盖。
保留数据格式相关配置（DataMappings / ExtractField / CellData.mapping 等）不变。
"""
import json
import os

BASE_DIR = os.environ.get("CAPAREPORT_BASE_DIR", "/data")
CONFIG_PATH = os.path.join(BASE_DIR, "Configure.json")


def set_str(target: dict, key: str, env: str) -> None:
    val = os.environ.get(env)
    if val not in (None, ""):
        target[key] = val


def set_int(target: dict, key: str, env: str) -> None:
    val = os.environ.get(env)
    if val not in (None, ""):
        try:
            target[key] = int(val)
        except ValueError:
            pass


def main() -> None:
    if not os.path.exists(CONFIG_PATH):
        return
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 主仓库 MySQL
    main_db = cfg.setdefault("MySQL_DBInfo", {})
    set_str(main_db, "host", "DB_HOST")
    set_int(main_db, "port", "DB_PORT")
    set_str(main_db, "user", "DB_USER")
    set_str(main_db, "passwd", "DB_PASSWD")
    set_str(main_db, "dbname", "MAIN_DB_NAME")

    cell = cfg.setdefault("CellData", {})
    # CellData MySQL
    cell_db = cell.setdefault("mysql", {})
    set_str(cell_db, "host", "DB_HOST")
    set_int(cell_db, "port", "DB_PORT")
    set_str(cell_db, "user", "DB_USER")
    set_str(cell_db, "passwd", "DB_PASSWD")
    set_str(cell_db, "dbname", "CELLDATA_DB_NAME")

    # 容量数据源 SFTP
    remote = cfg.setdefault("RemoteData", {})
    set_str(remote, "host", "SFTP_HOST")
    set_int(remote, "port", "SFTP_PORT")
    set_str(remote, "user", "SFTP_USER")
    set_str(remote, "passwd", "SFTP_PASSWD")

    # CellData 数据源 SFTP
    cell_remote = cell.setdefault("remote_data", {})
    set_str(cell_remote, "host", "SFTP_HOST")
    set_int(cell_remote, "port", "SFTP_PORT")
    set_str(cell_remote, "user", "SFTP_USER")
    set_str(cell_remote, "passwd", "SFTP_PASSWD")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("[entrypoint] 已按容器环境变量初始化 Configure.json 的数据库/SFTP 连接")


if __name__ == "__main__":
    main()
