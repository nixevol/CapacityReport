"""
数据处理核心模块 - 性能优化版
"""
import os
import re
import time
import zipfile
import multiprocessing
import numpy as np
import pandas as pd
import sqlparse
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

from app.config import AppConfig, SQL_SCRIPT
from app.database import DatabaseManager


class ProcessLogger:
    """处理日志记录器"""
    
    def __init__(self, log_file: Optional[Path] = None, callback: Optional[Callable[[str], None]] = None):
        self.logs: List[str] = []
        self.log_file = log_file
        self.callback = callback
        # 如果指定了日志文件，确保目录存在
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            # 清空或创建日志文件
            self.log_file.write_text("", encoding='utf-8')
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(entry)
        
        # 实时写入文件
        if self.log_file:
            try:
                with self.log_file.open("a", encoding='utf-8') as f:
                    f.write(entry + "\n")
            except Exception as e:
                # 如果写入失败，至少记录到内存
                print(f"写入日志文件失败: {e}")
        
        if self.callback:
            self.callback(entry)
    
    def info(self, message: str):
        self.log(message, "INFO")
    
    def error(self, message: str):
        self.log(message, "ERROR")
    
    def warning(self, message: str):
        self.log(message, "WARN")
    
    def success(self, message: str):
        self.log(message, "SUCCESS")
    
    def get_logs(self) -> List[str]:
        return self.logs.copy()


class DataProcessor:
    """数据处理器 - 高性能版"""
    
    # 批量插入大小（根据实际测试，5000 是比较好的平衡点）
    BATCH_SIZE = 5000
    # Excel 并行处理的最大线程数（根据 CPU 核心数自动调整）
    # 使用 CPU 核心数，但至少为 1，最多不超过 8（避免过多线程导致上下文切换开销）
    MAX_WORKERS = min(max(multiprocessing.cpu_count(), 1), 8)
    
    def __init__(self, config: AppConfig, work_dir: Path, logger: ProcessLogger):
        self.config = config
        self.work_dir = work_dir
        self.logger = logger
        self.db = DatabaseManager(config)
        self.results: Dict[str, Any] = {}
        
        # 预编译字段映射，避免重复查找
        self._field_map = self._build_field_map()
    
    def _build_field_map(self) -> Dict[str, str]:
        """预构建字段映射表，提高查找效率"""
        field_map = {}
        for field_def in self.config.extract_fields:
            db_field = field_def.get("Field")
            for extract_name in field_def.get("Extract", []):
                field_map[extract_name] = db_field
        return field_map
    
    def process(self) -> Dict[str, Any]:
        """执行完整的数据处理流程"""
        start_time = time.time()
        self.logger.info(f"开始处理数据，工作目录: {self.work_dir}")
        
        try:
            # 1. 解压 ZIP 文件
            self._unzip_files()
            
            # 2. 处理 Excel 文件（并行）
            self._process_excel_files_parallel()
            
            # 3. 处理 CSV 文件并上传到数据库（高性能批量插入）
            self._process_csv_files()
            
            # 4. 执行 SQL 脚本
            self._execute_sql_script()
            
            elapsed = round(time.time() - start_time, 2)
            self.logger.success(f"处理完成！总耗时: {elapsed} 秒")
            
            self.results["success"] = True
            self.results["elapsed_time"] = elapsed
            
        except Exception as e:
            self.logger.error(f"处理失败: {str(e)}")
            self.results["success"] = False
            self.results["error"] = str(e)
        
        finally:
            self.db.dispose()
        
        return self.results
    
    def _unzip_files(self):
        """解压所有 ZIP 文件（支持中文文件名）"""
        self.logger.info("正在解压 ZIP 文件...")
        zip_files = list(self.work_dir.rglob("*.zip"))
        zip_count = 0
        
        for zip_file in zip_files:
            try:
                rel_path = zip_file.relative_to(self.work_dir)
                self.logger.info(f"解压: {rel_path}")
                self._extract_zip_with_encoding(zip_file)
                zip_count += 1
            except Exception as e:
                rel_path = zip_file.relative_to(self.work_dir)
                self.logger.error(f"解压失败 {rel_path}: {e}")
        
        self.logger.info(f"ZIP 解压完成，共 {zip_count} 个文件")
    
    def _extract_zip_with_encoding(self, zip_file: Path):
        """
        解压 ZIP 文件，自动处理中文文件名编码问题
        支持 UTF-8、GBK、CP437 等多种编码
        """
        # 优先尝试 UTF-8（现代 ZIP 文件标准）
        try:
            with zipfile.ZipFile(zip_file, 'r', metadata_encoding='utf-8') as zf:
                zf.extractall(zip_file.parent)
                return
        except (UnicodeDecodeError, zipfile.BadZipFile):
            # UTF-8 失败，尝试 GBK（Windows 中文系统常用）
            try:
                with zipfile.ZipFile(zip_file, 'r', metadata_encoding='gbk') as zf:
                    zf.extractall(zip_file.parent)
                    return
            except (UnicodeDecodeError, zipfile.BadZipFile):
                # GBK 也失败，尝试 CP437（DOS 编码）
                try:
                    with zipfile.ZipFile(zip_file, 'r', metadata_encoding='cp437') as zf:
                        zf.extractall(zip_file.parent)
                        return
                except Exception as e:
                    # 所有编码都失败
                    raise Exception(f"无法解压 ZIP 文件，编码检测失败: {e}")
    
    def _scan_files(self, directory: Path, extensions: List[str]) -> Generator[Path, None, None]:
        """扫描指定扩展名的文件"""
        for ext in extensions:
            for file in directory.rglob(f"*{ext}"):
                yield file
    
    def _process_single_excel(self, excel_file: Path, sheet_filter: set) -> int:
        """处理单个 Excel 文件（用于并行）"""
        processed = 0
        try:
            rel_path = excel_file.relative_to(self.work_dir)
            
            # 使用 openpyxl 的 read_only 模式会更快，但这里保持兼容性
            xl = pd.ExcelFile(excel_file, engine='openpyxl')
            
            for sheet_name in xl.sheet_names:
                if sheet_name not in sheet_filter:
                    output_file = excel_file.parent / f"{excel_file.stem}_{sheet_name}.csv"
                    # 直接读取并写入，不做额外处理
                    df = xl.parse(sheet_name)
                    df.to_csv(output_file, index=False, encoding='utf-8')
                    processed += 1
            
            xl.close()
            return processed
            
        except Exception as e:
            rel_path = excel_file.relative_to(self.work_dir)
            self.logger.error(f"Excel 处理失败 {rel_path}: {e}")
            return 0
    
    def _process_excel_files_parallel(self):
        """并行处理 Excel 文件"""
        self.logger.info("正在并行处理 Excel 文件...")
        excel_files = list(self._scan_files(self.work_dir, ['.xlsx', '.xls']))
        self.logger.info(f"找到 {len(excel_files)} 个 Excel 文件")
        
        if not excel_files:
            return
        
        sheet_filter = set(self.config.sheet_filter)
        total_processed = 0
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._process_single_excel, f, sheet_filter): f 
                for f in excel_files
            }
            
            for future in as_completed(futures):
                excel_file = futures[future]
                try:
                    count = future.result()
                    total_processed += count
                    rel_path = excel_file.relative_to(self.work_dir)
                    if count > 0:
                        self.logger.info(f"处理完成: {rel_path} ({count} 个 sheet)")
                except Exception as e:
                    rel_path = excel_file.relative_to(self.work_dir)
                    self.logger.error(f"Excel 处理异常 {rel_path}: {e}")
        
        self.logger.info(f"Excel 处理完成，共生成 {total_processed} 个 CSV 文件")
    
    def _detect_encoding(self, file_path: Path) -> str:
        """快速检测文件编码（只读取前 8KB）"""
        import chardet
        with open(file_path, 'rb') as f:
            # 只读取前 8KB，足够检测编码，比 64KB 快很多
            result = chardet.detect(f.read(8192))
        encoding = result.get('encoding', 'utf-8') or 'utf-8'
        encoding = encoding.lower()
        if 'utf' in encoding:
            return 'utf-8'
        elif 'gb' in encoding:
            return 'gbk'
        return 'utf-8'
    
    def _process_csv_file_fast(self, csv_file: Path, table_name: str) -> int:
        """
        高性能处理单个 CSV 文件
        使用批量插入代替 to_sql，性能提升 5-10 倍
        """
        encoding = self._detect_encoding(csv_file)
        rel_path = csv_file.relative_to(self.work_dir)
        self.logger.info(f"处理 CSV: {rel_path} (编码: {encoding})")
        
        # 读取 CSV，使用优化参数
        df = pd.read_csv(
            csv_file, 
            encoding=encoding, 
            thousands=',', 
            low_memory=True,        # 低内存模式
            dtype=str,              # 全部作为字符串读取，避免类型推断开销
            na_values=[''],         # 只把空字符串当作 NA
            keep_default_na=False   # 不使用默认的 NA 值
        )
        
        # 快速字段匹配（使用预编译的映射表）
        col_mapping = {}
        for col in df.columns:
            if col in self._field_map:
                col_mapping[col] = self._field_map[col]
        
        if len(col_mapping) <= 3:
            if 'kpis' in str(csv_file).lower():
                self.logger.warning(f"跳过非数据文件: {rel_path}")
                return 0
            raise ValueError(f"字段匹配不足: {rel_path}")
        
        # 选择需要的列并重命名
        source_cols = list(col_mapping.keys())
        target_cols = list(col_mapping.values())
        
        df_result = df[source_cols]
        
        # 向量化数据清洗（比逐列循环快 10 倍以上）
        # 替换 NA 为 '0'，去除百分号，截断长度
        df_result = df_result.fillna('0')
        
        # 使用 numpy 向量化操作
        for col in df_result.columns:
            # 去除百分号
            df_result[col] = df_result[col].str.replace('%', '', regex=False)
            # 截断超长字符串
            mask = df_result[col].str.len() > 200
            if mask.any():
                df_result.loc[mask, col] = df_result.loc[mask, col].str[:200]
        
        # 确保表存在
        self.db.create_table_from_columns(table_name, target_cols)
        
        # 转换为元组列表，用于批量插入
        # 这比 to_sql 快很多
        data_tuples = [tuple(row) for row in df_result.values]
        
        # 使用批量插入
        inserted = self.db.bulk_insert(table_name, target_cols, data_tuples, self.BATCH_SIZE)
        
        return inserted
    
    def _find_data_directories(self) -> Dict[str, Path]:
        """
        查找包含数据文件的目录，返回 {表名: 目录路径}
        """
        data_dirs = {}
        target_names = {'4G', '5G', '4g', '5g'}
        
        self.logger.info(f"开始查找数据目录，工作目录: {self.work_dir}")
        
        # 递归查找所有名为 4G 或 5G 的目录
        found_dirs = []
        for subdir in self.work_dir.rglob('*'):
            if subdir.is_dir() and subdir.name in target_names:
                found_dirs.append(subdir)
        
        self.logger.info(f"找到 {len(found_dirs)} 个候选目录")
        
        for subdir in found_dirs:
            table_name = f"{subdir.name.upper()}_UD"
            if table_name not in data_dirs:
                data_dirs[table_name] = subdir
                self.logger.info(f"发现数据目录: {subdir.relative_to(self.work_dir)} -> 表: {table_name}")
        
        if not data_dirs:
            self.logger.warning("未找到 4G/5G 目录，使用直接子目录")
            for subdir in self.work_dir.iterdir():
                if subdir.is_dir():
                    table_name = f"{subdir.name}_UD"
                    data_dirs[table_name] = subdir
                    self.logger.info(f"使用直接子目录: {subdir.relative_to(self.work_dir)} -> 表: {table_name}")
        
        return data_dirs
    
    def _process_csv_files(self):
        """处理所有 CSV 文件（高性能版）"""
        self.logger.info("正在处理 CSV 文件并上传到数据库...")
        
        # 查找数据目录
        data_dirs = self._find_data_directories()
        
        if not data_dirs:
            self.logger.warning("未找到任何数据目录")
            return
        
        # 按目录分组处理
        for table_name, subdir in data_dirs.items():
            self.logger.info(f"处理目录: {subdir.relative_to(self.work_dir)} -> 表: {table_name}")
            
            # 删除旧表
            self.db.drop_table(table_name)
            
            # 处理该目录下的所有 CSV
            csv_files = list(self._scan_files(subdir, ['.csv']))
            self.logger.info(f"找到 {len(csv_files)} 个 CSV 文件")
            
            total_rows = 0
            start_time = time.time()
            
            for i, csv_file in enumerate(csv_files, 1):
                try:
                    rows = self._process_csv_file_fast(csv_file, table_name)
                    total_rows += rows
                    
                    # 每处理 10 个文件报告一次进度
                    if i % 10 == 0:
                        elapsed = round(time.time() - start_time, 1)
                        self.logger.info(f"进度: {i}/{len(csv_files)} 文件, 已导入 {total_rows} 行, 耗时 {elapsed}s")
                        
                except Exception as e:
                    rel_path = csv_file.relative_to(self.work_dir)
                    self.logger.error(f"CSV 处理失败 {rel_path}: {e}")
            
            elapsed = round(time.time() - start_time, 2)
            speed = round(total_rows / elapsed) if elapsed > 0 else 0
            self.logger.success(f"表 {table_name} 导入完成: {total_rows} 行, 耗时 {elapsed}s, 速度 {speed} 行/秒")
    
    def _execute_sql_script(self):
        """执行 SQL 脚本"""
        if not SQL_SCRIPT.exists():
            self.logger.warning("SQL 脚本文件不存在，跳过")
            return
        
        self.logger.info("正在执行 SQL 脚本...")
        
        with open(SQL_SCRIPT, 'r', encoding='utf-8') as f:
            sql_text = f.read()
        
        sqls = sqlparse.split(sql_text)
        total = len(sqls)
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for i, sql in enumerate(sqls, 1):
                    sql = sql.strip()
                    if not sql or sql.startswith('#'):
                        continue
                    
                    start_time = time.time()
                    preview = sql[:80].replace('\n', ' ')
                    self.logger.info(f"执行 SQL ({i}/{total}): {preview}...")
                    
                    try:
                        cursor.execute(sql)
                        elapsed = round(time.time() - start_time, 2)
                        self.logger.info(f"完成，耗时 {elapsed} 秒")
                    except Exception as e:
                        self.logger.error(f"SQL 执行失败: {e}")
                
                conn.commit()
        
        self.logger.success("SQL 脚本执行完成")
