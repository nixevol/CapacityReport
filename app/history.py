"""
处理历史记录管理模块
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from app.config import CACHE_DIR


HISTORY_FILE = CACHE_DIR / "history.json"


@dataclass
class HistoryRecord:
    """历史记录"""
    id: str
    timestamp: str
    status: str  # pending, processing, completed, failed
    work_dir: str
    file_count: int = 0
    elapsed_time: float = 0.0
    error: Optional[str] = None
    result_tables: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_log_file(self) -> Path:
        """获取日志文件路径"""
        return Path(self.work_dir) / "log.txt"


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self):
        self._ensure_file()
    
    def _ensure_file(self):
        """确保历史文件存在"""
        if not HISTORY_FILE.exists():
            HISTORY_FILE.write_text("[]", encoding='utf-8')
    
    def _load(self) -> List[Dict[str, Any]]:
        """加载历史记录"""
        try:
            return json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except:
            return []
    
    def _save(self, records: List[Dict[str, Any]]):
        """保存历史记录"""
        HISTORY_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    
    def create(self, work_dir: Path, file_count: int, record_id: Optional[str] = None) -> HistoryRecord:
        """创建新的历史记录"""
        # 如果提供了 record_id，使用它；否则生成新的
        if record_id is None:
            record_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        record = HistoryRecord(
            id=record_id,
            timestamp=datetime.now().isoformat(),
            status="pending",
            work_dir=str(work_dir),
            file_count=file_count
        )
        
        records = self._load()
        records.insert(0, record.to_dict())
        
        # 只保留最近 100 条记录
        records = records[:100]
        self._save(records)
        
        return record
    
    def _clean_record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """清理记录，移除不存在的字段（如旧的 logs 字段）"""
        cleaned = {
            'id': rec.get('id'),
            'timestamp': rec.get('timestamp'),
            'status': rec.get('status'),
            'work_dir': rec.get('work_dir'),
            'file_count': rec.get('file_count', 0),
            'elapsed_time': rec.get('elapsed_time', 0.0),
            'error': rec.get('error'),
            'result_tables': rec.get('result_tables', [])
        }
        return cleaned
    
    def update(self, record_id: str, **kwargs) -> Optional[HistoryRecord]:
        """更新历史记录"""
        records = self._load()
        
        for i, rec in enumerate(records):
            if rec['id'] == record_id:
                rec.update(kwargs)
                self._save(records)
                cleaned = self._clean_record(rec)
                return HistoryRecord(**cleaned)
        
        return None
    
    def get(self, record_id: str) -> Optional[HistoryRecord]:
        """获取单条记录"""
        records = self._load()
        for rec in records:
            if rec['id'] == record_id:
                cleaned = self._clean_record(rec)
                return HistoryRecord(**cleaned)
        return None
    
    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取历史记录列表"""
        records = self._load()
        # 返回简化的列表（不包含日志）
        result = []
        for rec in records[:limit]:
            item = rec.copy()
            item.pop('logs', None)  # 列表不返回日志（兼容旧数据）
            result.append(item)
        return result
    
    def get_logs(self, record_id: str) -> List[str]:
        """从 log.txt 文件读取日志"""
        record = self.get(record_id)
        if not record:
            return []
        
        log_file = record.get_log_file()
        if not log_file.exists():
            return []
        
        try:
            content = log_file.read_text(encoding='utf-8')
            # 按行分割，过滤空行
            logs = [line.strip() for line in content.split('\n') if line.strip()]
            return logs
        except Exception as e:
            print(f"读取日志文件失败: {log_file}, 错误: {e}")
            return []
    
    def delete(self, record_id: str) -> bool:
        """删除历史记录，同时删除对应的文件目录"""
        records = self._load()
        
        # 找到要删除的记录，获取其工作目录
        work_dir = None
        for rec in records:
            if rec['id'] == record_id:
                work_dir = rec.get('work_dir')
                break
        
        # 删除记录
        new_records = [r for r in records if r['id'] != record_id]
        
        if len(new_records) < len(records):
            self._save(new_records)
            
            # 删除对应的文件目录（安全检查：确保路径在cache目录内）
            if work_dir:
                try:
                    work_path = Path(work_dir).resolve()
                    cache_path = CACHE_DIR.resolve()
                    
                    # 安全检查：确保要删除的目录在cache目录内
                    if work_path.exists() and work_path.is_dir():
                        # 检查路径是否在cache目录内
                        try:
                            work_path.relative_to(cache_path)
                            # 路径安全，可以删除
                            shutil.rmtree(work_path)
                        except ValueError:
                            # 路径不在cache目录内，跳过删除（安全保护）
                            print(f"警告: 尝试删除cache目录外的文件: {work_dir}")
                except Exception as e:
                    # 记录错误但不影响删除历史记录的操作
                    print(f"删除文件目录失败: {work_dir}, 错误: {e}")
            
            return True
        return False
    
    def clear(self) -> int:
        """清空所有历史记录，同时清空cache目录（保留history.json）"""
        records = self._load()
        count = len(records)
        
        # 清空历史记录
        self._save([])
        
        # 清空cache目录（保留history.json文件）
        try:
            cache_path = CACHE_DIR.resolve()
            for item in CACHE_DIR.iterdir():
                try:
                    item_path = item.resolve()
                    # 安全检查：确保路径在cache目录内
                    item_path.relative_to(cache_path)
                    
                    if item.is_dir():
                        # 删除所有子目录
                        shutil.rmtree(item_path)
                    elif item.is_file() and item.name != "history.json":
                        # 删除所有文件，但保留history.json
                        item_path.unlink()
                except ValueError:
                    # 路径不在cache目录内，跳过（安全保护）
                    print(f"警告: 跳过cache目录外的文件: {item}")
                except Exception as e:
                    # 单个文件/目录删除失败，继续处理其他文件
                    print(f"删除失败: {item}, 错误: {e}")
        except Exception as e:
            # 记录错误但不影响清空历史记录的操作
            print(f"清空cache目录失败: {e}")
        
        return count
