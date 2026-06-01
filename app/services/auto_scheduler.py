from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app import state
from app.config import CACHE_DIR, AutoSchedulerConfig
from app.services.remote_download import RemoteDataDownloader, RemoteFileInfo
from app.utils.file_dates import parse_file_date_range, required_week_days


READY_DIR = CACHE_DIR / "auto_scheduler"
READY_FLAG = READY_DIR / "ready.flag"
DISABLED_CHECK_SECONDS = 60
STARTUP_CHECK_SECONDS = 5
FAILURE_RESULTS = {"scan_failed", "trigger_failed", "source_cleanup_failed", "failed", "invalid_flag"}


@dataclass(frozen=True)
class RJDirectoryReadyStatus:
    """RJ 数据目录就绪状态，按最新文件自动识别日粒度或周粒度。"""
    directory: str
    ready: bool
    granularity: str | None = None
    found_days: list[date] | None = None
    missing_days: list[date] | None = None
    file_name: str | None = None
    file_count: int = 0
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        found_days = self.found_days or []
        missing_days = self.missing_days or []
        return {
            "ready": self.ready,
            "granularity": self.granularity,
            "found_days": [item.isoformat() for item in found_days],
            "missing_days": [item.isoformat() for item in missing_days],
            "found_count": len(found_days),
            "required_count": len(found_days) + len(missing_days),
            "file_name": self.file_name,
            "file_count": self.file_count,
            "error": self.error,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


@dataclass(frozen=True)
class DirectoryReadyStatus:
    directory: str
    ready: bool
    found_days: list[date]
    missing_days: list[date]
    file_count: int
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "found_days": [item.isoformat() for item in self.found_days],
            "missing_days": [item.isoformat() for item in self.missing_days],
            "found_count": len(self.found_days),
            "required_count": len(self.found_days) + len(self.missing_days),
            "file_count": self.file_count,
            "error": self.error,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


class AutoScheduler:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._check_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_check_at: datetime | None = None
        self._next_check_at: datetime | None = None
        self._last_result = "not_started"
        self._last_message = "自动调度器尚未检查"
        self._directory_status: dict[str, dict[str, Any]] = {}
        self._task_running = False
        self._task_id: str | None = None
        self._failure_count = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._stop_event.clear()
        self._set_next_check(datetime.now() + timedelta(seconds=STARTUP_CHECK_SECONDS))
        self._thread = threading.Thread(target=self._run_loop, name="auto-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def get_status(self) -> dict[str, Any]:
        app_config = state.current_config()
        config = app_config.remote_data.normalized()
        scheduler = config.auto_scheduler.normalized()
        rj_config = app_config.rj_data.normalized()
        target_days = required_week_days(scheduler.week_offset)
        ready_flag = self._read_ready_flag()

        with self._status_lock:
            return {
                "enabled": scheduler.enabled,
                "running": self._running,
                "check_interval_hours": scheduler.check_interval_hours,
                "expected_directories": scheduler.expected_directories,
                "week_offset": scheduler.week_offset,
                "auto_delete_source": config.auto_delete_source,
                "rj_data_enabled": rj_config.enabled,
                "rj_directories": rj_config.weekly_directories,
                "rj_weekly_directories": rj_config.weekly_directories,
                "next_check_at": self._format_dt(self._next_check_at),
                "last_check_at": self._format_dt(self._last_check_at),
                "last_result": self._last_result,
                "last_message": self._last_message,
                "failure_count": self._failure_count,
                "task_running": self._task_running,
                "task_id": self._task_id,
                "ready_flag": ready_flag,
                "target_week": {
                    "start": target_days[0].isoformat(),
                    "end": target_days[-1].isoformat(),
                    "days": [item.isoformat() for item in target_days],
                },
                "directory_status": self._directory_status,
            }

    def check_and_run(self, manual: bool = False) -> dict[str, Any]:
        if not self._check_lock.acquire(blocking=False):
            return self._finish_check("busy", "自动调度器正在检查中", manual)

        try:
            return self._check_and_run_locked(manual)
        finally:
            self._check_lock.release()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._seconds_until_next_check()):
            self.check_and_run(manual=False)

    def _check_and_run_locked(self, manual: bool) -> dict[str, Any]:
        now = datetime.now()
        app_config = state.current_config()
        remote_config = app_config.remote_data.normalized()
        scheduler = remote_config.auto_scheduler.normalized()
        self._last_check_at = now

        if not scheduler.enabled:
            self._set_next_check(now + timedelta(seconds=DISABLED_CHECK_SECONDS))
            return self._finish_check("disabled", "自动调度未启用", manual)

        self._set_next_check(now + timedelta(hours=scheduler.check_interval_hours))

        if not remote_config.enabled:
            return self._finish_check("remote_disabled", "远程数据源未启用", manual)

        if state.global_task_lock["locked"]:
            return self._finish_check("task_running", "已有任务在运行，本轮自动调度跳过", manual)

        ready_flag = self._read_ready_flag()
        if ready_flag["exists"]:
            if ready_flag.get("invalid"):
                self._clear_ready_flag()
                return self._finish_check("invalid_flag", "就绪标识格式错误，已清除，本轮不触发处理", manual)
            target_dates = self._target_dates_from_flag(ready_flag, scheduler)
            return self._trigger_processing(target_dates, ready_flag, manual)

        target_days = required_week_days(scheduler.week_offset)
        downloader = RemoteDataDownloader(remote_config)
        rj_config = app_config.rj_data.normalized()
        rj_directories = set(rj_config.weekly_directories) if rj_config.enabled else set()

        # 检查现有7天目录（4G/5G数据），RJ 目录单独按粒度判断，避免被普通7天规则误拦。
        directory_status = self._check_remote_ready(
            downloader,
            scheduler,
            target_days,
            excluded_directories=rj_directories,
        )

        error_count = sum(1 for item in directory_status.values() if item.error)
        if error_count:
            self._set_combined_directory_status(directory_status, {})
            return self._finish_check(
                "scan_failed",
                f"远程目录扫描失败，{error_count}/{len(directory_status)} 个目录无法访问或扫描失败",
                manual,
            )

        active_status = [item for item in directory_status.values() if not item.skipped]
        skipped_count = len(directory_status) - len(active_status)
        daily_ready = bool(active_status) and all(item.ready for item in active_status)

        # 检查 RJ 数据目录，按最新文件自动判断日粒度或周粒度。
        rj_status = self._check_rj_ready(downloader, target_days)
        rj_error_count = sum(1 for item in rj_status.values() if item.error)
        self._set_combined_directory_status(directory_status, rj_status)
        if rj_error_count:
            return self._finish_check(
                "scan_failed",
                f"RJ 远程目录扫描失败，{rj_error_count}/{len(rj_status)} 个目录无法访问或扫描失败",
                manual,
            )

        active_rj_status = [item for item in rj_status.values() if not item.skipped]
        rj_ready = all(item.ready for item in active_rj_status)
        rj_status_text = ""

        if active_rj_status:
            rj_ready_count = sum(1 for item in active_rj_status if item.ready)
            rj_total = len(active_rj_status)
            if not rj_ready:
                rj_status_text = f"，RJ 数据 {rj_ready_count}/{rj_total} 个有效目录就绪"

        # 两个条件都满足才触发
        if daily_ready and rj_ready:
            self._mark_ready(target_days, directory_status, rj_status)
            skipped_text = f"，已跳过 {skipped_count} 个停推目录" if skipped_count else ""
            rj_text = "，RJ 数据已就绪" if active_rj_status else ""
            return self._finish_check(
                "marked_ready",
                f"远程数据已满足目标周 7 天{skipped_text}{rj_text}，已写入就绪标识，下次检查将自动处理",
                manual,
            )

        if not active_status and directory_status:
            return self._finish_check(
                "waiting",
                f"远程数据未就绪，{len(directory_status)} 个目录均为空，已视为停推但不会触发处理",
                manual,
            )

        if not active_status:
            return self._finish_check(
                "waiting",
                f"远程普通日数据未发现有效目录，无法触发处理{rj_status_text}",
                manual,
            )

        ready_count = sum(1 for item in active_status if item.ready)
        skipped_text = f"，跳过 {skipped_count} 个停推目录" if skipped_count else ""
        return self._finish_check(
            "waiting",
            f"远程数据未就绪，{ready_count}/{len(active_status)} 个有效目录满足目标周 7 天{skipped_text}{rj_status_text}",
            manual,
        )

    def _check_remote_ready(
        self,
        downloader: RemoteDataDownloader,
        scheduler: AutoSchedulerConfig,
        target_days: list[date],
        excluded_directories: set[str] | None = None,
    ) -> dict[str, DirectoryReadyStatus]:
        excluded = {self._normalize_directory_name(item) for item in (excluded_directories or set())}
        expected_directories = scheduler.expected_directories
        if expected_directories:
            return {
                directory: self._directory_ready_status(
                    directory,
                    self._safe_list_remote_zip_files(downloader, directory),
                    target_days,
                )
                for directory in expected_directories
                if not self._is_excluded_directory(directory, excluded)
            }

        files = self._safe_list_remote_zip_files(downloader, None)
        if files is None:
            return {
                ".": DirectoryReadyStatus(
                    directory=".",
                    ready=False,
                    found_days=[],
                    missing_days=target_days,
                    file_count=0,
                    error="远程目录扫描失败",
                )
            }

        if not files:
            return {
                ".": DirectoryReadyStatus(
                    directory=".",
                    ready=False,
                    found_days=[],
                    missing_days=target_days,
                    file_count=0,
                    error="远程目录未找到 ZIP 文件",
                )
            }

        grouped: dict[str, list[RemoteFileInfo]] = defaultdict(list)
        for remote_file in files:
            parent = remote_file.parent or "."
            if self._is_excluded_directory(parent, excluded):
                continue
            grouped[parent].append(remote_file)

        if not grouped:
            return {}

        return {
            directory: self._directory_ready_status(directory, directory_files, target_days)
            for directory, directory_files in sorted(grouped.items(), key=lambda item: item[0])
        }

    def _safe_list_remote_zip_files(
        self,
        downloader: RemoteDataDownloader,
        directory: str | None,
    ) -> list[RemoteFileInfo] | None:
        try:
            return downloader.list_remote_zip_files(directory)
        except Exception:
            return None

    def _directory_ready_status(
        self,
        directory: str,
        files: list[RemoteFileInfo] | None,
        target_days: list[date],
    ) -> DirectoryReadyStatus:
        if files is None:
            return DirectoryReadyStatus(
                directory=directory,
                ready=False,
                found_days=[],
                missing_days=target_days,
                file_count=0,
                error="远程目录不存在或无法访问",
            )

        if not files:
            return DirectoryReadyStatus(
                directory=directory,
                ready=True,
                found_days=[],
                missing_days=[],
                file_count=0,
                skipped=True,
                skip_reason="目录为空，视为已停推并跳过",
            )

        required = set(target_days)
        found = {
            target_day
            for remote_file in files
            if (date_range := parse_file_date_range(remote_file.name))
            for target_day in date_range.covered_days()
            if target_day in required
        }
        missing = [item for item in target_days if item not in found]
        return DirectoryReadyStatus(
            directory=directory,
            ready=not missing,
            found_days=sorted(found),
            missing_days=missing,
            file_count=len(files),
        )

    def _check_rj_ready(
        self,
        downloader: RemoteDataDownloader,
        target_days: list[date],
    ) -> dict[str, RJDirectoryReadyStatus]:
        """检查 RJ 数据目录是否就绪，自动识别目录最新文件是日粒度还是周粒度。"""
        rj_config = state.current_config().rj_data.normalized()
        if not rj_config.enabled:
            return {}

        result: dict[str, RJDirectoryReadyStatus] = {}

        for directory in rj_config.weekly_directories:
            result[directory] = self._check_single_rj_directory(downloader, directory, target_days)

        return result

    def _check_single_rj_directory(
        self,
        downloader: RemoteDataDownloader,
        directory: str,
        target_days: list[date],
    ) -> RJDirectoryReadyStatus:
        """检查单个 RJ 目录是否包含目标周数据。"""
        files = self._safe_list_remote_zip_files(downloader, directory)
        if files is None:
            return RJDirectoryReadyStatus(
                directory=directory,
                ready=False,
                error="远程目录不存在或无法访问",
            )

        if not files:
            return RJDirectoryReadyStatus(
                directory=directory,
                ready=True,
                file_count=0,
                skipped=True,
                skip_reason="目录为空，视为已停推并跳过",
            )

        parsed_files = [
            (remote_file, date_range)
            for remote_file in files
            if (date_range := parse_file_date_range(remote_file.name))
        ]
        if not parsed_files:
            return RJDirectoryReadyStatus(
                directory=directory,
                ready=False,
                found_days=[],
                missing_days=target_days,
                file_count=len(files),
                error="目录中未找到可识别日期的 ZIP 文件",
            )

        latest_file, latest_range = max(
            parsed_files,
            key=lambda item: (item[1].start, item[1].end_exclusive, item[0].name),
        )
        granularity = "daily" if latest_range.span_days <= 1 else "weekly"
        required = set(target_days)

        found = {
            target_day
            for _, date_range in parsed_files
            for target_day in date_range.covered_days()
            if target_day in required
        }
        missing = [item for item in target_days if item not in found]

        if granularity == "daily":
            return RJDirectoryReadyStatus(
                directory=directory,
                ready=not missing,
                granularity=granularity,
                found_days=sorted(found),
                missing_days=missing,
                file_name=latest_file.name,
                file_count=len(files),
            )

        for remote_file in files:
            date_range = parse_file_date_range(remote_file.name)
            if date_range and date_range.covers_all(required):
                return RJDirectoryReadyStatus(
                    directory=directory,
                    ready=True,
                    granularity=granularity,
                    found_days=target_days,
                    missing_days=[],
                    file_name=remote_file.name,
                    file_count=len(files),
                )

        return RJDirectoryReadyStatus(
            directory=directory,
            ready=False,
            granularity=granularity,
            found_days=sorted(found),
            missing_days=missing,
            file_name=latest_file.name,
            file_count=len(files),
        )

    def _trigger_processing(
        self,
        target_dates: list[date],
        ready_flag: dict[str, Any],
        manual: bool,
    ) -> dict[str, Any]:
        from app.api.routers.remote import start_remote_processing_job

        try:
            result = start_remote_processing_job(
                source="scheduler",
                on_finish=self._on_processing_finish,
                target_dates=target_dates,
            )
        except HTTPException as exc:
            return self._finish_check("trigger_failed", str(exc.detail), manual)
        except Exception as exc:
            return self._finish_check("trigger_failed", f"自动调度触发失败: {exc}", manual)

        task_id = result.get("task_id")
        with self._status_lock:
            self._task_running = True
            self._task_id = str(task_id) if task_id else None
            self._last_result = "triggered"
            self._last_message = "已根据就绪标识触发远程下载并处理"
        return {
            "success": True,
            "result": "triggered",
            "message": "已根据就绪标识触发远程下载并处理",
            "task_id": task_id,
            "ready_flag": ready_flag,
            "status": self.get_status(),
        }

    def _mark_ready(
        self,
        target_days: list[date],
        directory_status: dict[str, DirectoryReadyStatus],
        rj_status: dict[str, RJDirectoryReadyStatus] | None = None,
    ) -> None:
        READY_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "ready_at": datetime.now().isoformat(timespec="seconds"),
            "week_start": target_days[0].isoformat(),
            "week_end": target_days[-1].isoformat(),
            "target_dates": [item.isoformat() for item in target_days],
            "directories": {
                name: item.to_dict()
                for name, item in directory_status.items()
            },
        }
        if rj_status:
            payload["rj_directories"] = {
                name: item.to_dict()
                for name, item in rj_status.items()
            }
            payload["rj_weekly_directories"] = {
                name: item.to_dict()
                for name, item in rj_status.items()
            }
        READY_FLAG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _clear_ready_flag(self) -> None:
        try:
            READY_FLAG.unlink(missing_ok=True)
        except OSError:
            pass

    def _read_ready_flag(self) -> dict[str, Any]:
        if not READY_FLAG.exists():
            return {"exists": False}
        try:
            data = json.loads(READY_FLAG.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {"exists": True, **data}
        except Exception as exc:
            return {"exists": True, "invalid": True, "error": str(exc)}
        return {"exists": True, "invalid": True, "error": "ready.flag 格式错误"}

    def _target_dates_from_flag(
        self,
        ready_flag: dict[str, Any],
        scheduler: AutoSchedulerConfig,
    ) -> list[date]:
        raw_dates = ready_flag.get("target_dates")
        if isinstance(raw_dates, list):
            dates: list[date] = []
            for raw_date in raw_dates:
                try:
                    dates.append(date.fromisoformat(str(raw_date)))
                except ValueError:
                    continue
            if dates:
                return sorted(dates)
        return required_week_days(scheduler.week_offset)

    def _on_processing_finish(self, task_id: str, status: str) -> None:
        if status == "completed":
            self._clear_ready_flag()
            message = "自动调度任务处理成功，已清除就绪标识"
            result = "completed"
        else:
            message = "自动调度任务未完成，就绪标识已保留，下次检查会重试"
            result = status or "failed"

        with self._status_lock:
            self._task_running = False
            self._task_id = task_id
            self._last_result = result
            self._last_message = message
            self._failure_count = 0 if result == "completed" else self._failure_count + 1

    def _finish_check(self, result: str, message: str, manual: bool) -> dict[str, Any]:
        with self._status_lock:
            self._last_result = result
            self._last_message = message
            if result in FAILURE_RESULTS:
                self._failure_count += 1
            elif result not in {"busy", "task_running"}:
                self._failure_count = 0
            if result not in {"triggered", "task_running"}:
                self._task_running = False

        return {
            "success": result not in FAILURE_RESULTS,
            "manual": manual,
            "result": result,
            "message": message,
            "status": self.get_status(),
        }

    def _set_combined_directory_status(
        self,
        directory_status: dict[str, DirectoryReadyStatus],
        rj_status: dict[str, RJDirectoryReadyStatus],
    ) -> None:
        with self._status_lock:
            combined = {
                name: item.to_dict()
                for name, item in directory_status.items()
            }
            combined.update(
                {
                    name: item.to_dict()
                    for name, item in rj_status.items()
                }
            )
            self._directory_status = combined

    @staticmethod
    def _normalize_directory_name(directory: str) -> str:
        normalized = str(directory or "").replace("\\", "/").strip().strip("/")
        return "." if normalized in {"", "."} else normalized

    @classmethod
    def _is_excluded_directory(cls, directory: str, excluded: set[str]) -> bool:
        if not excluded:
            return False
        normalized = cls._normalize_directory_name(directory)
        return any(
            normalized == item or normalized.startswith(f"{item}/")
            for item in excluded
            if item != "."
        )

    def _set_next_check(self, value: datetime) -> None:
        with self._status_lock:
            self._next_check_at = value

    def _seconds_until_next_check(self) -> float:
        with self._status_lock:
            next_check_at = self._next_check_at
        if not next_check_at:
            return STARTUP_CHECK_SECONDS
        return max((next_check_at - datetime.now()).total_seconds(), 0)

    @staticmethod
    def _format_dt(value: datetime | None) -> str | None:
        return value.isoformat(timespec="seconds") if value else None
