"""
数据库连接与操作模块 - 性能优化版
"""
import pymysql
import sqlalchemy
from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import QueuePool
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

from app.config import AppConfig


class DatabaseManager:
    """数据库管理器 - 高性能版"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self._engine: Optional[sqlalchemy.Engine] = None
    
    @property
    def engine(self) -> sqlalchemy.Engine:
        """获取 SQLAlchemy 引擎（带连接池）- 优化配置"""
        if self._engine is None:
            mysql = self.config.mysql
            self._engine = create_engine(
                f'mysql+pymysql://'
                f'{quote(mysql.user)}:'
                f'{quote(mysql.passwd)}@'
                f'{quote(mysql.host)}:'
                f'{mysql.port}/'
                f'{quote(mysql.dbname)}?charset=utf8mb4',
                poolclass=QueuePool,
                pool_size=10,           # 增大连接池
                max_overflow=20,        # 增大溢出连接
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
                # 性能优化参数
                connect_args={
                    'local_infile': True,   # 允许 LOAD DATA LOCAL
                    'autocommit': False,
                }
            )
        return self._engine
    
    @contextmanager
    def get_connection(self):
        """获取 PyMySQL 连接（上下文管理器）"""
        mysql = self.config.mysql
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
        mysql = self.config.mysql
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
    
    def delete_rows(self, table_name: str, condition: str, params: List[Any]) -> int:
        """删除符合条件的行"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = f"DELETE FROM `{table_name}` WHERE {condition}"
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount
    
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
                    batch_size: int = 5000) -> int:
        """
        高性能批量插入
        使用 executemany + 批量提交，比 to_sql 快 5-10 倍
        """
        if not data:
            return 0
        
        total_inserted = 0
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join([f'`{col}`' for col in columns])
        sql = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
        
        with self.get_fast_connection() as conn:
            with conn.cursor() as cursor:
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
                conn.commit()
                cursor.execute("SET unique_checks=1")
                cursor.execute("SET foreign_key_checks=1")
                cursor.execute("SET autocommit=1")
        
        return total_inserted
    
    def create_table_from_columns(self, table_name: str, columns: List[str]):
        """根据列名创建表（所有列都是 VARCHAR(255)）"""
        column_defs = ', '.join([f'`{col}` VARCHAR(255)' for col in columns])
        sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({column_defs}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                conn.commit()
    
    def dispose(self):
        """释放连接池"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
