"""
数据库连接与操作模块
"""
import csv
import pymysql
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from app.config import AppConfig, MySQLConfig


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: AppConfig, mysql_config: MySQLConfig | None = None):
        self.config = config
        self.mysql_config = (mysql_config or config.mysql).normalized()
    
    @contextmanager
    def get_connection(self):
        """
        获取 PyMySQL 连接（上下文管理器）
        
        注意：此方法创建的是独立连接（非连接池），适用于：
        - 需要在整个操作过程中保持同一 session 的场景
        - 使用临时表（TEMPORARY TABLE）的场景（临时表是 session 级别的）
        - 需要事务一致性的长时间操作
        
        如果需要高性能的短连接操作，请使用 engine 属性（连接池）
        """
        mysql = self.mysql_config
        conn = pymysql.connect(
            host=mysql.host,
            port=mysql.port,
            user=mysql.user,
            password=mysql.passwd,
            database=mysql.dbname,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            local_infile=True,          # 允许 LOAD DATA LOCAL
            autocommit=False
        )
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def get_fast_connection(self):
        """获取高性能 PyMySQL 连接（用于批量插入）"""
        mysql = self.mysql_config
        conn = pymysql.connect(
            host=mysql.host,
            port=mysql.port,
            user=mysql.user,
            password=mysql.passwd,
            database=mysql.dbname,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor,  # 使用普通游标更快
            local_infile=True,
            autocommit=False,
            read_timeout=300,
            write_timeout=300
        )
        try:
            yield conn
        finally:
            conn.close()
    
    def test_connection(self) -> Tuple[bool, str]:
        """测试数据库连接"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return True, "连接成功"
        except Exception as e:
            return False, str(e)
    
    def check_load_data_support(self) -> Tuple[bool, str]:
        """
        检测数据库是否支持 LOAD DATA LOCAL INFILE
        
        Returns:
            (是否支持, 详细信息)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查服务器端 local_infile 变量
                    cursor.execute("SHOW VARIABLES LIKE 'local_infile'")
                    result = cursor.fetchone()
                    
                    if result:
                        value = result.get('Value', '').upper()
                        if value == 'ON':
                            return True, "服务器已启用 local_infile"
                        else:
                            return False, f"服务器 local_infile={value}，需要设置为 ON"
                    else:
                        return False, "无法获取 local_infile 变量"
        except Exception as e:
            return False, f"检测失败: {str(e)}"
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取数据库服务器信息"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取版本
                    cursor.execute("SELECT VERSION() as version")
                    version = cursor.fetchone().get('version', 'Unknown')
                    
                    # 检查 LOAD DATA 支持
                    load_data_supported, load_data_msg = self.check_load_data_support()
                    
                    return {
                        "version": version,
                        "load_data_infile": load_data_supported,
                        "load_data_message": load_data_msg
                    }
        except Exception as e:
            return {
                "version": "Unknown",
                "load_data_infile": False,
                "load_data_message": str(e)
            }
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                return [list(row.values())[0] for row in cursor.fetchall()]
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 获取列信息
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                
                # 获取行数
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                count = cursor.fetchone()['count']
                
                return {
                    "name": table_name,
                    "columns": columns,
                    "row_count": count
                }
    
    def query_table(
        self, 
        table_name: str, 
        page: int = 1, 
        page_size: int = 50,
        filters: Optional[Dict[str, str]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "ASC"
    ) -> Dict[str, Any]:
        """分页查询表数据"""
        offset = (page - 1) * page_size
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 构建 WHERE 条件
                where_clause = ""
                params = []
                if filters:
                    conditions = []
                    for col, val in filters.items():
                        if val:
                            conditions.append(f"`{col}` LIKE %s")
                            params.append(f"%{val}%")
                    if conditions:
                        where_clause = "WHERE " + " AND ".join(conditions)
                
                # 获取总数
                count_sql = f"SELECT COUNT(*) as count FROM `{table_name}` {where_clause}"
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['count']
                
                # 构建排序
                order_clause = ""
                if order_by:
                    order_clause = f"ORDER BY `{order_by}` {order_dir}"
                
                # 查询数据
                query_sql = f"SELECT * FROM `{table_name}` {where_clause} {order_clause} LIMIT %s OFFSET %s"
                cursor.execute(query_sql, params + [page_size, offset])
                rows = cursor.fetchall()
                
                return {
                    "data": rows,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
    
    def _row_conditions(self, identifier: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """按整行原值构造 WHERE：NULL 用 IS NULL；调用方再加 LIMIT 1 只影响单行。"""
        parts: List[str] = []
        params: List[Any] = []
        for col, val in identifier.items():
            if val is None:
                parts.append(f"`{col}` IS NULL")
            else:
                parts.append(f"`{col}` = %s")
                params.append(val)
        return (" AND ".join(parts) if parts else "1 = 0"), params

    def update_row(self, table_name: str, identifier: Dict[str, Any], values: Dict[str, Any]) -> int:
        """更新单行：按 identifier(原始整行) 定位、LIMIT 1，避免影响重复行。返回影响行数。"""
        if not values:
            return 0
        set_clause = ", ".join(f"`{col}` = %s" for col in values)
        set_params = list(values.values())
        where_clause, where_params = self._row_conditions(identifier)
        sql = f"UPDATE `{table_name}` SET {set_clause} WHERE {where_clause} LIMIT 1"
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, set_params + where_params)
                conn.commit()
                return cursor.rowcount

    def delete_row(self, table_name: str, identifier: Dict[str, Any]) -> int:
        """删除单行：按 identifier(原始整行) 定位、LIMIT 1。返回影响行数。"""
        where_clause, where_params = self._row_conditions(identifier)
        sql = f"DELETE FROM `{table_name}` WHERE {where_clause} LIMIT 1"
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, where_params)
                conn.commit()
                return cursor.rowcount

    def import_csv(self, file_path: str, table_name: str) -> int:
        """按 CSV 表头列追加导入（列须与表字段一致，由调用方校验）。返回导入行数。"""
        with open(file_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                return 0
            columns = [str(name).strip() for name in header]
            width = len(columns)
            data: List[Tuple] = []
            for row in reader:
                if not any(str(cell).strip() for cell in row):
                    continue
                cells = list(row[:width]) + [""] * (width - len(row))
                data.append(tuple(cells))
        if not data:
            return 0
        return self.bulk_insert(table_name, columns, data)

    def truncate_table(self, table_name: str) -> bool:
        """清空表"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE `{table_name}`")
                conn.commit()
                return True
    
    def drop_table(self, table_name: str) -> bool:
        """删除表"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                conn.commit()
                return True
    
    def drop_all_tables(self) -> Dict[str, Any]:
        """删除所有表"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 获取所有表名
                cursor.execute("SHOW TABLES")
                tables = [list(row.values())[0] for row in cursor.fetchall()]
                
                if not tables:
                    return {"success": True, "dropped_count": 0, "tables": []}
                
                # 删除所有表
                dropped_tables = []
                for table in tables:
                    try:
                        cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
                        dropped_tables.append(table)
                    except Exception:
                        # 记录错误但继续删除其他表
                        pass
                
                conn.commit()
                return {
                    "success": True,
                    "dropped_count": len(dropped_tables),
                    "tables": dropped_tables
                }
    
    def execute_sql(self, sql: str) -> Tuple[bool, Any]:
        """执行自定义 SQL"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    if sql.strip().upper().startswith("SELECT"):
                        return True, cursor.fetchall()
                    else:
                        conn.commit()
                        return True, {"affected_rows": cursor.rowcount}
                except Exception as e:
                    return False, str(e)
    
    def bulk_insert(self, table_name: str, columns: List[str], data: List[Tuple], 
                    batch_size: int = 5000, conn=None) -> int:
        """
        高性能批量插入
        使用 executemany + 批量提交，比 to_sql 快 5-10 倍
        
        Args:
            conn: 可选，复用已有连接
        """
        if not data:
            return 0
        
        total_inserted = 0
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join([f'`{col}`' for col in columns])
        sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
        
        def do_insert(connection):
            nonlocal total_inserted
            with connection.cursor() as cursor:
                # 优化插入性能的设置
                cursor.execute("SET autocommit=0")
                cursor.execute("SET unique_checks=0")
                cursor.execute("SET foreign_key_checks=0")
                
                # 分批插入
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    cursor.executemany(sql, batch)
                    total_inserted += len(batch)
                
                # 提交并恢复设置
                connection.commit()
                cursor.execute("SET unique_checks=1")
                cursor.execute("SET foreign_key_checks=1")
                cursor.execute("SET autocommit=1")
        
        if conn:
            do_insert(conn)
        else:
            with self.get_fast_connection() as connection:
                do_insert(connection)
        
        return total_inserted
    
    def load_data_infile(self, table_name: str, columns: List[str], 
                         temp_file: str, conn=None) -> int:
        """
        使用 LOAD DATA LOCAL INFILE 高速导入 CSV 文件
        比 executemany 快 10-50 倍
        
        Args:
            table_name: 目标表名
            columns: 列名列表
            temp_file: 临时 CSV 文件路径
            conn: 可选，复用已有连接
            
        Returns:
            导入的行数
        """
        column_names = ', '.join([f'`{col}`' for col in columns])
        
        # 使用正斜杠路径（MySQL 兼容）
        file_path = temp_file.replace('\\', '/')
        
        sql = f"""
            LOAD DATA LOCAL INFILE '{file_path}'
            INTO TABLE `{table_name}`
            CHARACTER SET utf8mb4
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            LINES TERMINATED BY '\\n'
            IGNORE 1 LINES
            ({column_names})
        """
        
        def do_load(connection):
            with connection.cursor() as cursor:
                # 优化导入性能的设置
                cursor.execute("SET autocommit=0")
                cursor.execute("SET unique_checks=0")
                cursor.execute("SET foreign_key_checks=0")
                
                # 执行 LOAD DATA
                cursor.execute(sql)
                row_count = cursor.rowcount
                
                # 提交并恢复设置
                connection.commit()
                cursor.execute("SET unique_checks=1")
                cursor.execute("SET foreign_key_checks=1")
                cursor.execute("SET autocommit=1")
                
                return row_count
        
        if conn:
            return do_load(conn)
        else:
            with self.get_fast_connection() as connection:
                return do_load(connection)
    
    # 字段类型到 MySQL 类型的映射
    TYPE_MAPPING = {
        'string': 'VARCHAR(255)',
        'datetime': 'DATETIME',
        'int': 'INT',
        'float': 'DOUBLE',
        'text': 'TEXT',
    }
    
    def create_table_from_columns(self, table_name: str, columns: List[str], 
                                   column_types: Optional[Dict[str, str]] = None):
        """
        根据列名和类型创建表
        
        Args:
            table_name: 表名
            columns: 列名列表
            column_types: 列名到类型的映射 {列名: 类型}，类型可选: string, datetime, int, float, text
        """
        column_defs = []
        for col in columns:
            # 获取类型，默认为 string
            col_type = 'string'
            if column_types and col in column_types:
                col_type = column_types[col]
            
            # 转换为 MySQL 类型
            mysql_type = self.TYPE_MAPPING.get(col_type, 'VARCHAR(255)')
            column_defs.append(f'`{col}` {mysql_type}')
        
        sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(column_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                conn.commit()
