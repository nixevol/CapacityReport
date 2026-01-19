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
        self._field_map, self._type_map = self._build_field_map()
        
        # LOAD DATA INFILE 支持状态（在首次使用时检测）
        self._load_data_supported: Optional[bool] = None
        self._load_data_checked = False
    
    def _build_field_map(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        预构建字段映射表和类型映射表，提高查找效率
        
        Returns:
            field_map: {源字段名: 目标字段名}
            type_map: {目标字段名: 字段类型}
        """
        field_map = {}
        type_map = {}
        for field_def in self.config.extract_fields:
            db_field = field_def.get("Field")
            field_type = field_def.get("Type", "string")  # 默认类型为 string
            
            # 记录目标字段的类型
            type_map[db_field] = field_type
            
            # 记录源字段到目标字段的映射
            for extract_name in field_def.get("Extract", []):
                field_map[extract_name] = db_field
        
        return field_map, type_map
    
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
            # 清理临时目录
            self._cleanup_temp_dir()
            # 释放数据库连接
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
    
    def _process_csv_file_fast(self, csv_file: Path, table_name: str, 
                                conn=None, table_created: bool = False) -> Tuple[int, bool]:
        """
        高性能处理单个 CSV 文件
        使用 LOAD DATA LOCAL INFILE，比 executemany 快 10-50 倍
        
        Args:
            csv_file: CSV 文件路径
            table_name: 目标表名
            conn: 数据库连接（复用）
            table_created: 表是否已创建
            
        Returns:
            (导入行数, 表是否已创建)
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
                return 0, table_created
            raise ValueError(f"字段匹配不足: {rel_path}")
        
        # 选择需要的列并重命名
        source_cols = list(col_mapping.keys())
        target_cols = list(col_mapping.values())
        
        # 创建结果 DataFrame，使用目标列名
        df_result = df[source_cols].copy()
        df_result.columns = target_cols
        
        # 替换 NA 为默认值
        df_result = df_result.fillna('')
        
        # 构建目标字段的类型映射
        column_types = {col: self._type_map.get(col, 'string') for col in target_cols}
        
        # 根据类型处理每列数据
        for col in target_cols:
            col_type = column_types.get(col, 'string')
            
            if col_type == 'datetime':
                # 日期时间类型处理
                df_result[col] = self._convert_datetime_column(df_result[col])
            
            elif col_type == 'int':
                # 整数类型处理
                df_result[col] = self._convert_int_column(df_result[col])
            
            elif col_type == 'float':
                # 浮点数类型处理
                df_result[col] = self._convert_float_column(df_result[col])
            
            elif col_type == 'text':
                # 长文本类型，截断到 65535 字符
                mask = df_result[col].str.len() > 65535
                if mask.any():
                    df_result.loc[mask, col] = df_result.loc[mask, col].str[:65535]
            
            else:  # string 或其他
                # 字符串类型：去除百分号、截断长度
                df_result[col] = df_result[col].str.replace('%', '', regex=False)
                mask = df_result[col].str.len() > 255
                if mask.any():
                    df_result.loc[mask, col] = df_result.loc[mask, col].str[:255]
        
        # 确保表存在（只在第一次创建）
        if not table_created:
            self.db.create_table_from_columns(table_name, target_cols, column_types)
            table_created = True
        
        # 使用 LOAD DATA INFILE 导入
        inserted = self._load_data_infile(df_result, table_name, target_cols, conn)
        
        return inserted, table_created
    
    def _get_temp_dir(self) -> Path:
        """获取临时目录（使用工作目录下的 .temp 子目录）"""
        temp_dir = self.work_dir / '.temp'
        temp_dir.mkdir(exist_ok=True)
        return temp_dir
    
    def _cleanup_temp_dir(self):
        """清理临时目录"""
        temp_dir = self.work_dir / '.temp'
        if temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    def _check_load_data_support(self) -> bool:
        """检测是否支持 LOAD DATA INFILE（只检测一次）"""
        if self._load_data_checked:
            return self._load_data_supported or False
        
        self._load_data_checked = True
        supported, message = self.db.check_load_data_support()
        self._load_data_supported = supported
        
        if supported:
            self.logger.info(f"LOAD DATA INFILE: 已启用 ({message})")
        else:
            self.logger.warning(f"LOAD DATA INFILE: 不可用 ({message})，将使用批量插入模式")
        
        return supported
    
    def _load_data_infile(self, df: pd.DataFrame, table_name: str, 
                          columns: List[str], conn=None) -> int:
        """
        使用 LOAD DATA LOCAL INFILE 导入数据
        如果失败则自动回退到 bulk_insert 方式
        临时文件放在工作目录的 .temp 子目录中
        """
        import tempfile
        
        # 检测是否支持 LOAD DATA INFILE
        if not self._check_load_data_support():
            # 不支持，直接使用 bulk_insert
            return self._bulk_insert_fallback(df, table_name, columns, conn)
        
        # 获取临时目录
        temp_dir = self._get_temp_dir()
        temp_file = None
        
        try:
            # 写入临时 CSV 文件
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.csv', 
                delete=False, 
                encoding='utf-8',
                newline='',
                dir=str(temp_dir)  # 使用指定的临时目录
            ) as f:
                temp_file = f.name
                # 写入 CSV（带表头，用于 IGNORE 1 LINES）
                df.to_csv(f, index=False, header=True, na_rep='\\N')
            
            # 使用 LOAD DATA LOCAL INFILE 导入
            inserted = self.db.load_data_infile(table_name, columns, temp_file, conn)
            return inserted
            
        except Exception as e:
            # LOAD DATA 失败，标记为不支持并回退
            self.logger.warning(f"LOAD DATA INFILE 执行失败: {e}，回退到批量插入模式")
            self._load_data_supported = False
            return self._bulk_insert_fallback(df, table_name, columns, conn)
            
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
    
    def _bulk_insert_fallback(self, df: pd.DataFrame, table_name: str,
                               columns: List[str], conn=None) -> int:
        """批量插入回退方案"""
        # 转换为元组列表
        data_tuples = [tuple(row) for row in df.values]
        # 使用批量插入
        return self.db.bulk_insert(table_name, columns, data_tuples, self.BATCH_SIZE, conn)
    
    # 支持的日期时间格式列表
    DATETIME_FORMATS = [
        'ISO8601',                    # 2026-01-06T00:00:00+08:00
        '%Y-%m-%d %H:%M:%S',          # 2026-01-06 00:00:00
        '%Y-%m-%d %H:%M',             # 2026-01-06 00:00
        '%Y/%m/%d %H:%M:%S',          # 2026/01/06 00:00:00
        '%Y/%m/%d %H:%M',             # 2026/01/06 00:00
        '%Y-%m-%d',                   # 2026-01-06
        '%Y/%m/%d',                   # 2026/01/06
        '%Y年%m月%d日 %H:%M:%S',       # 2026年01月06日 00:00:00
        '%Y年%m月%d日',                # 2026年01月06日
        '%Y%m%d%H%M%S',               # 20260106000000
        '%Y%m%d',                     # 20260106
    ]
    
    def _detect_datetime_format(self, series: pd.Series, sample_size: int = 100) -> list:
        """
        采样检测时间格式，返回检测到的格式列表（按匹配数量排序）
        """
        # 获取非空样本
        valid = series[series.notna() & (series != '') & (series.astype(str).str.strip() != '')]
        if len(valid) == 0:
            return self.DATETIME_FORMATS
        
        # 采样
        sample = valid.head(sample_size) if len(valid) > sample_size else valid
        
        # 检测每种格式的匹配率
        format_matches = {}
        for fmt in self.DATETIME_FORMATS:
            try:
                if fmt == 'ISO8601':
                    parsed = pd.to_datetime(sample, errors='coerce', format='ISO8601')
                else:
                    parsed = pd.to_datetime(sample, errors='coerce', format=fmt)
                match_count = parsed.notna().sum()
                if match_count > 0:
                    format_matches[fmt] = match_count
            except Exception:
                continue
        
        # 按匹配数量降序排序，只返回有匹配的格式
        if format_matches:
            sorted_formats = sorted(format_matches.keys(), key=lambda x: format_matches[x], reverse=True)
            return sorted_formats
        
        # 没有检测到格式，返回默认列表
        return self.DATETIME_FORMATS
    
    def _convert_datetime_column(self, series: pd.Series) -> pd.Series:
        """
        转换日期时间列，支持多种常见格式
        使用采样检测优化性能：先检测主要格式，再批量处理
        """
        try:
            valid_mask = series.notna() & (series != '') & (series.astype(str).str.strip() != '')
            if not valid_mask.any():
                return pd.Series([None] * len(series), index=series.index)
            
            # 采样检测格式（只用前 100 条数据检测）
            detected_formats = self._detect_datetime_format(series, sample_size=100)
            
            # 初始化结果
            parsed = pd.Series([pd.NaT] * len(series), index=series.index)
            remaining = valid_mask.copy()
            
            # 按检测到的格式顺序处理
            for fmt in detected_formats:
                if not remaining.any():
                    break
                
                try:
                    if fmt == 'ISO8601':
                        temp_parsed = pd.to_datetime(series[remaining], errors='coerce', format='ISO8601')
                    else:
                        temp_parsed = pd.to_datetime(series[remaining], errors='coerce', format=fmt)
                    
                    success_mask = temp_parsed.notna()
                    if success_mask.any():
                        success_indices = remaining[remaining].index[success_mask]
                        parsed.loc[success_indices] = temp_parsed[success_mask].values
                        remaining.loc[success_indices] = False
                except Exception:
                    continue
            
            # 兜底：用 mixed 模式处理剩余的
            if remaining.any():
                try:
                    temp_parsed = pd.to_datetime(series[remaining], errors='coerce', format='mixed', dayfirst=False)
                    success_mask = temp_parsed.notna()
                    if success_mask.any():
                        success_indices = remaining[remaining].index[success_mask]
                        parsed.loc[success_indices] = temp_parsed[success_mask].values
                except Exception:
                    pass
            
            # 格式化输出
            return parsed.dt.strftime('%Y-%m-%d %H:%M:%S').fillna(None)
        except Exception:
            return series
    
    def _convert_int_column(self, series: pd.Series) -> pd.Series:
        """转换整数列"""
        try:
            # 检测是否包含百分号
            has_percent = series.astype(str).str.contains('%', regex=False, na=False)
            
            # 去除百分号和逗号
            cleaned = series.str.replace('%', '', regex=False).str.replace(',', '', regex=False)
            # 转换为数值
            numeric = pd.to_numeric(cleaned, errors='coerce')
            
            # 如果有百分号，除以100转换为小数
            numeric[has_percent] = numeric[has_percent] / 100
            
            # 四舍五入并转为整数字符串，空值保留为 None
            return numeric.round().fillna(0).astype(int).astype(str).replace('0', None, regex=False)
        except Exception:
            return series
    
    def _convert_float_column(self, series: pd.Series) -> pd.Series:
        """转换浮点数列"""
        try:
            # 检测是否包含百分号
            has_percent = series.astype(str).str.contains('%', regex=False, na=False)
            
            # 去除百分号和逗号
            cleaned = series.str.replace('%', '', regex=False).str.replace(',', '', regex=False)
            # 转换为数值
            numeric = pd.to_numeric(cleaned, errors='coerce')
            
            # 如果有百分号，除以100转换为小数（例如：95% → 0.95）
            numeric[has_percent] = numeric[has_percent] / 100
            
            # 保留小数，空值为 None
            return numeric.fillna(0).astype(str).replace('0.0', None, regex=False).replace('0', None, regex=False)
        except Exception:
            return series
    
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
        """处理所有 CSV 文件（高性能版 - 使用 LOAD DATA INFILE + 连接复用）"""
        self.logger.info("正在处理 CSV 文件并上传到数据库...")
        
        # 查找数据目录
        data_dirs = self._find_data_directories()
        
        if not data_dirs:
            self.logger.warning("未找到任何数据目录")
            return
        
        # 按目录分组处理，使用连接复用
        for table_name, subdir in data_dirs.items():
            self.logger.info(f"处理目录: {subdir.relative_to(self.work_dir)} -> 表: {table_name}")
            
            # 删除旧表
            self.db.drop_table(table_name)
            
            # 处理该目录下的所有 CSV
            csv_files = list(self._scan_files(subdir, ['.csv']))
            self.logger.info(f"找到 {len(csv_files)} 个 CSV 文件")
            
            total_rows = 0
            start_time = time.time()
            table_created = False
            
            # 使用连接复用：一个表的所有 CSV 文件共用一个连接
            with self.db.get_fast_connection() as conn:
                for i, csv_file in enumerate(csv_files, 1):
                    try:
                        rows, table_created = self._process_csv_file_fast(
                            csv_file, table_name, conn, table_created
                        )
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
    
    @staticmethod
    def parse_sql_script(sql_text: str) -> List[str]:
        """
        解析 SQL 脚本，提取有效的 SQL 语句
        
        改进的SQL分割逻辑：直接按分号分割，更可靠
        这样可以确保所有以分号结尾的语句都被正确识别
        
        Args:
            sql_text: SQL 脚本文本内容
            
        Returns:
            有效的 SQL 语句列表
        """
        if not sql_text or not sql_text.strip():
            return []
        
        # 改进的SQL分割逻辑：直接按分号分割，更可靠
        # 这样可以确保所有以分号结尾的语句都被正确识别
        parts = sql_text.split(';')
        valid_sqls = []
        
        for part in parts:
            # 处理多行语句：移除以#开头的注释行，但保留SQL语句
            lines = []
            for line in part.split('\n'):
                line = line.strip()
                # 跳过空行和整行注释
                if line and not line.startswith('#'):
                    lines.append(line)
            
            if lines:
                # 合并多行语句，保留换行符（MySQL支持多行SQL）
                cleaned_sql = '\n'.join(lines)
                cleaned_sql = cleaned_sql.strip()
                # 跳过空语句（可能只剩下注释）
                if cleaned_sql:
                    valid_sqls.append(cleaned_sql)
        
        return valid_sqls
    
    def _execute_sql_script(self):
        """
        执行 SQL 脚本
        
        重要说明：
        - 使用 get_connection() 获取独立连接（非连接池），确保整个脚本在同一 session 中执行
        - 临时表（TEMPORARY TABLE）是 session 级别的，必须在同一连接中创建和使用
        - 如果使用连接池，不同 SQL 语句可能分配到不同连接，导致临时表不可见
        - 因此整个脚本必须在同一个连接中顺序执行，不能使用连接池
        """
        if not SQL_SCRIPT.exists():
            self.logger.warning("SQL 脚本文件不存在，跳过")
            return
        
        self.logger.info("正在执行 SQL 脚本...")
        
        with open(SQL_SCRIPT, 'r', encoding='utf-8') as f:
            sql_text = f.read()
        
        if not sql_text or not sql_text.strip():
            self.logger.warning("SQL 脚本文件为空，跳过执行")
            return
        
        # 使用抽离的解析函数
        valid_sqls = self.parse_sql_script(sql_text)
        
        if not valid_sqls:
            self.logger.warning("SQL 脚本中没有有效的 SQL 语句（可能全是注释或空行）")
            return
        
        total = len(valid_sqls)
        self.logger.info(f"共找到 {total} 条有效的 SQL 语句")
        
        executed_count = 0
        # 使用独立连接（非连接池），确保整个脚本在同一 session 中执行
        # 这对于临时表（TEMPORARY TABLE）至关重要，因为临时表是 session 级别的
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                for i, sql in enumerate(valid_sqls, 1):
                    start_time = time.time()
                    preview = sql[:80].replace('\n', ' ')
                    self.logger.info(f"执行 SQL ({i}/{total}): {preview}...")
                    
                    try:
                        cursor.execute(sql)
                        executed_count += 1
                        elapsed = round(time.time() - start_time, 2)
                        affected_rows = cursor.rowcount if cursor.rowcount >= 0 else 0
                        if affected_rows > 0:
                            self.logger.info(f"完成，耗时 {elapsed} 秒，影响 {affected_rows} 行")
                        else:
                            self.logger.info(f"完成，耗时 {elapsed} 秒")
                    except Exception as e:
                        self.logger.error(f"SQL 执行失败: {e}")
                        # 继续执行下一条 SQL，不中断
                
                conn.commit()
        
        self.logger.success(f"SQL 脚本执行完成，共执行 {executed_count}/{total} 条语句")
