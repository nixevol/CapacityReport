from __future__ import annotations

import stat
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from ftplib import FTP
from pathlib import Path
from typing import Callable, Iterable

from app.config import RemoteDataConfig
from app.utils.file_dates import extract_file_date, select_recent_items_by_directory


LogFn = Callable[[str], None]


@dataclass
class RemoteDownloadResult:
    file_count: int = 0
    total_bytes: int = 0
    remote_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RemoteFileInfo:
    path: str
    relative_path: str
    parent: str
    name: str
    size: int = 0


class RemoteDownloadError(RuntimeError):
    pass


class RemoteDataDownloader:
    def __init__(self, config: RemoteDataConfig, logger: LogFn | None = None):
        self.config = config.normalized()
        self.logger = logger

    def test_connection(self) -> None:
        self._validate_config()
        if self.config.protocol == "ftp":
            with self._ftp_client() as ftp:
                ftp.cwd(self.config.remote_dir)
            return

        ssh = self._sftp_ssh_client()
        try:
            with ssh.open_sftp() as sftp:
                sftp.stat(self.config.remote_dir)
        finally:
            ssh.close()

    def download_to(self, destination: Path, target_dates: Iterable[date] | None = None) -> RemoteDownloadResult:
        self._validate_config()
        destination.mkdir(parents=True, exist_ok=True)
        zip_files = self.list_remote_zip_files()
        date_filter = set(target_dates or [])
        if date_filter:
            selected_files = self._select_files_by_dates(zip_files, date_filter)
            return self._download_selected_files(destination, selected_files)

        if zip_files:
            selected_files, summaries = select_recent_items_by_directory(
                zip_files,
                parent_key=lambda item: item.parent,
                name_key=lambda item: item.name,
            )
            for summary in summaries:
                if summary.max_date and summary.start_date and summary.skipped_count:
                    self._log(
                        f"远程目录 {summary.directory or '.'}: 仅下载 "
                        f"{summary.start_date.isoformat()} 至 {summary.max_date.isoformat()} "
                        f"的 {summary.selected_count}/{summary.total_count} 个 ZIP 文件，"
                        f"跳过 {summary.skipped_count} 个旧文件"
                    )
            return self._download_selected_files(destination, selected_files)

        if self.config.protocol == "ftp":
            return self._download_ftp(destination)
        return self._download_sftp(destination)

    def _select_files_by_dates(self, zip_files: list[RemoteFileInfo], target_dates: set[date]) -> list[RemoteFileInfo]:
        selected_files: list[RemoteFileInfo] = []
        grouped: dict[str, list[RemoteFileInfo]] = defaultdict(list)
        for remote_file in zip_files:
            grouped[remote_file.parent].append(remote_file)

        for parent, files in sorted(grouped.items(), key=lambda item: item[0]):
            selected = [
                remote_file
                for remote_file in files
                if extract_file_date(remote_file.name) in target_dates
            ]
            selected_files.extend(selected)
            skipped_count = len(files) - len(selected)
            if skipped_count:
                first_day = min(target_dates).isoformat()
                last_day = max(target_dates).isoformat()
                self._log(
                    f"远程目录 {parent or '.'}: 仅下载调度目标日期 "
                    f"{first_day} 至 {last_day} 的 {len(selected)}/{len(files)} 个 ZIP 文件，"
                    f"跳过 {skipped_count} 个非目标日期文件"
                )

        return selected_files

    def list_remote_zip_files(self, directory: str | None = None) -> list[RemoteFileInfo]:
        self._validate_config()
        remote_dir = (
            self._join_remote_path(self.config.remote_dir, directory.strip("/"))
            if directory
            else self.config.remote_dir
        )
        if self.config.protocol == "ftp":
            return self._list_ftp_zip_files(remote_dir)
        return self._list_sftp_zip_files(remote_dir)

    def delete_source_files(self, remote_files: Iterable[str] | None = None) -> int:
        self._validate_config()
        source_files = list(remote_files or [])
        if source_files:
            if self.config.protocol == "ftp":
                return self._delete_ftp_file_paths(source_files)
            return self._delete_sftp_file_paths(source_files)

        if self.config.protocol == "ftp":
            return self._delete_ftp_source_files()
        return self._delete_sftp_source_files()

    def _validate_config(self) -> None:
        if self.config.protocol not in {"ftp", "sftp"}:
            raise RemoteDownloadError("远程协议只支持 FTP 或 SFTP")
        if not self.config.host:
            raise RemoteDownloadError("请填写远程服务器地址")
        if not self.config.user:
            raise RemoteDownloadError("请填写远程服务器用户名")
        if not self.config.remote_dir:
            raise RemoteDownloadError("请填写远程数据目录")

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger(message)

    def _ftp_client(self) -> FTP:
        ftp = FTP()
        ftp.connect(self.config.host, self.config.port, timeout=self.config.timeout)
        ftp.login(self.config.user, self.config.passwd)
        ftp.set_pasv(self.config.passive)
        return ftp

    def _download_ftp(self, destination: Path) -> RemoteDownloadResult:
        result = RemoteDownloadResult()
        with self._ftp_client() as ftp:
            self._log(f"已连接 FTP: {self.config.host}:{self.config.port}")
            self._download_ftp_dir(ftp, self.config.remote_dir, destination, result)
        return result

    def _download_ftp_dir(
        self,
        ftp: FTP,
        remote_dir: str,
        local_dir: Path,
        result: RemoteDownloadResult,
    ) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)
        entries = self._list_ftp_entries(ftp, remote_dir)

        for name, entry_type, size in entries:
            if name in {".", ".."}:
                continue

            remote_path = self._join_remote_path(remote_dir, name)
            local_path = local_dir / name

            if entry_type == "dir":
                self._download_ftp_dir(ftp, remote_path, local_path, result)
                continue

            if entry_type == "unknown" and self._ftp_is_dir(ftp, remote_path):
                self._download_ftp_dir(ftp, remote_path, local_path, result)
                continue

            self._download_ftp_file(ftp, remote_path, local_path, result, size)

    def _list_ftp_entries(self, ftp: FTP, remote_dir: str) -> list[tuple[str, str, int]]:
        try:
            return [
                (
                    name,
                    facts.get("type", "unknown"),
                    int(facts.get("size", "0") or 0),
                )
                for name, facts in ftp.mlsd(remote_dir)
            ]
        except Exception:
            names = ftp.nlst(remote_dir)
            entries = []
            for name in names:
                clean_name = Path(name.replace("\\", "/")).name
                if clean_name:
                    entries.append((clean_name, "unknown", 0))
            return entries

    def _ftp_is_dir(self, ftp: FTP, remote_path: str) -> bool:
        current = ftp.pwd()
        try:
            ftp.cwd(remote_path)
            return True
        except Exception:
            return False
        finally:
            try:
                ftp.cwd(current)
            except Exception:
                pass

    def _download_ftp_file(
        self,
        ftp: FTP,
        remote_path: str,
        local_path: Path,
        result: RemoteDownloadResult,
        expected_size: int = 0,
    ) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._log(f"下载: {remote_path}")
        with local_path.open("wb") as file:
            ftp.retrbinary(f"RETR {remote_path}", file.write)
        result.file_count += 1
        result.total_bytes += expected_size or local_path.stat().st_size
        result.remote_files.append(remote_path)

    def _download_selected_files(self, destination: Path, remote_files: list[RemoteFileInfo]) -> RemoteDownloadResult:
        result = RemoteDownloadResult()
        if not remote_files:
            return result

        if self.config.protocol == "ftp":
            with self._ftp_client() as ftp:
                self._log(f"已连接 FTP: {self.config.host}:{self.config.port}")
                for remote_file in remote_files:
                    self._download_ftp_file(
                        ftp,
                        remote_file.path,
                        destination / remote_file.relative_path,
                        result,
                        remote_file.size,
                    )
            return result

        ssh = self._sftp_ssh_client()
        try:
            with ssh.open_sftp() as sftp:
                self._log(f"已连接 SFTP: {self.config.host}:{self.config.port}")
                for remote_file in remote_files:
                    self._download_sftp_file(
                        sftp,
                        remote_file.path,
                        destination / remote_file.relative_path,
                        result,
                        remote_file.size,
                    )
        finally:
            ssh.close()
        return result

    def _list_ftp_zip_files(self, remote_dir: str) -> list[RemoteFileInfo]:
        with self._ftp_client() as ftp:
            return self._collect_ftp_zip_files(ftp, remote_dir)

    def _collect_ftp_zip_files(self, ftp: FTP, remote_dir: str) -> list[RemoteFileInfo]:
        files: list[RemoteFileInfo] = []
        for name, entry_type, size in self._list_ftp_entries(ftp, remote_dir):
            if name in {".", ".."}:
                continue

            remote_path = self._join_remote_path(remote_dir, name)
            if entry_type == "dir" or (entry_type == "unknown" and self._ftp_is_dir(ftp, remote_path)):
                files.extend(self._collect_ftp_zip_files(ftp, remote_path))
                continue

            if name.lower().endswith(".zip"):
                files.append(self._remote_file_info(remote_path, size))
        return files

    def _delete_ftp_source_files(self) -> int:
        with self._ftp_client() as ftp:
            self._log(f"开始清理 FTP 源文件: {self.config.remote_dir}")
            return self._delete_ftp_files(ftp, self.config.remote_dir)

    def _delete_ftp_files(self, ftp: FTP, remote_dir: str) -> int:
        deleted_count = 0
        for name, entry_type, _ in self._list_ftp_entries(ftp, remote_dir):
            if name in {".", ".."}:
                continue

            remote_path = self._join_remote_path(remote_dir, name)
            if entry_type == "dir" or (entry_type == "unknown" and self._ftp_is_dir(ftp, remote_path)):
                deleted_count += self._delete_ftp_files(ftp, remote_path)
                continue

            self._log(f"删除远程文件: {remote_path}")
            ftp.delete(remote_path)
            deleted_count += 1
        return deleted_count

    def _delete_ftp_file_paths(self, remote_files: list[str]) -> int:
        deleted_count = 0
        with self._ftp_client() as ftp:
            self._log(f"开始清理 FTP 源文件，共 {len(remote_files)} 个")
            for remote_path in remote_files:
                self._log(f"删除远程文件: {remote_path}")
                ftp.delete(remote_path)
                deleted_count += 1
        return deleted_count

    def _sftp_ssh_client(self):
        try:
            import paramiko
        except ImportError as exc:
            raise RemoteDownloadError("SFTP 功能需要安装 paramiko，请执行 uv pip install -r requirements.txt") from exc

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.user,
            password=self.config.passwd,
            timeout=self.config.timeout,
            banner_timeout=self.config.timeout,
            auth_timeout=self.config.timeout,
        )
        return ssh

    def _download_sftp(self, destination: Path) -> RemoteDownloadResult:
        result = RemoteDownloadResult()
        ssh = self._sftp_ssh_client()
        try:
            with ssh.open_sftp() as sftp:
                self._log(f"已连接 SFTP: {self.config.host}:{self.config.port}")
                self._download_sftp_path(sftp, self.config.remote_dir, destination, result)
        finally:
            ssh.close()
        return result

    def _download_sftp_path(
        self,
        sftp,
        remote_path: str,
        local_path: Path,
        result: RemoteDownloadResult,
    ) -> None:
        attrs = sftp.stat(remote_path)
        if stat.S_ISDIR(attrs.st_mode):
            local_path.mkdir(parents=True, exist_ok=True)
            for item in sftp.listdir_attr(remote_path):
                if item.filename in {".", ".."}:
                    continue
                self._download_sftp_path(
                    sftp,
                    self._join_remote_path(remote_path, item.filename),
                    local_path / item.filename,
                    result,
                )
            return

        self._download_sftp_file(sftp, remote_path, local_path, result, int(getattr(attrs, "st_size", 0) or 0))

    def _download_sftp_file(
        self,
        sftp,
        remote_path: str,
        local_path: Path,
        result: RemoteDownloadResult,
        expected_size: int = 0,
    ) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._log(f"下载: {remote_path}")
        sftp.get(remote_path, str(local_path))
        result.file_count += 1
        result.total_bytes += expected_size or local_path.stat().st_size
        result.remote_files.append(remote_path)

    def _list_sftp_zip_files(self, remote_dir: str) -> list[RemoteFileInfo]:
        ssh = self._sftp_ssh_client()
        try:
            with ssh.open_sftp() as sftp:
                return self._collect_sftp_zip_files(sftp, remote_dir)
        finally:
            ssh.close()

    def _collect_sftp_zip_files(self, sftp, remote_path: str) -> list[RemoteFileInfo]:
        attrs = sftp.stat(remote_path)
        if not stat.S_ISDIR(attrs.st_mode):
            name = Path(remote_path.replace("\\", "/")).name
            if name.lower().endswith(".zip"):
                return [self._remote_file_info(remote_path, int(getattr(attrs, "st_size", 0) or 0))]
            return []

        files: list[RemoteFileInfo] = []
        for item in sftp.listdir_attr(remote_path):
            if item.filename in {".", ".."}:
                continue
            child_path = self._join_remote_path(remote_path, item.filename)
            if stat.S_ISDIR(item.st_mode):
                files.extend(self._collect_sftp_zip_files(sftp, child_path))
            elif item.filename.lower().endswith(".zip"):
                files.append(self._remote_file_info(child_path, int(getattr(item, "st_size", 0) or 0)))
        return files

    def _delete_sftp_source_files(self) -> int:
        ssh = self._sftp_ssh_client()
        try:
            with ssh.open_sftp() as sftp:
                self._log(f"开始清理 SFTP 源文件: {self.config.remote_dir}")
                return self._delete_sftp_files(sftp, self.config.remote_dir)
        finally:
            ssh.close()

    def _delete_sftp_files(self, sftp, remote_path: str) -> int:
        attrs = sftp.stat(remote_path)
        if stat.S_ISDIR(attrs.st_mode):
            deleted_count = 0
            for item in sftp.listdir_attr(remote_path):
                if item.filename in {".", ".."}:
                    continue
                deleted_count += self._delete_sftp_files(
                    sftp,
                    self._join_remote_path(remote_path, item.filename),
                )
            return deleted_count

        self._log(f"删除远程文件: {remote_path}")
        sftp.remove(remote_path)
        return 1

    def _delete_sftp_file_paths(self, remote_files: list[str]) -> int:
        deleted_count = 0
        ssh = self._sftp_ssh_client()
        try:
            with ssh.open_sftp() as sftp:
                self._log(f"开始清理 SFTP 源文件，共 {len(remote_files)} 个")
                for remote_path in remote_files:
                    self._log(f"删除远程文件: {remote_path}")
                    sftp.remove(remote_path)
                    deleted_count += 1
        finally:
            ssh.close()
        return deleted_count

    @staticmethod
    def _join_remote_path(parent: str, child: str) -> str:
        parent = parent.replace("\\", "/").rstrip("/")
        if not parent:
            return child
        if parent == "/":
            return f"/{child}"
        return f"{parent}/{child}"

    def _remote_file_info(self, remote_path: str, size: int = 0) -> RemoteFileInfo:
        normalized_root = self.config.remote_dir.replace("\\", "/").rstrip("/")
        normalized_path = remote_path.replace("\\", "/")
        if normalized_root and normalized_root != "/" and normalized_path.startswith(f"{normalized_root}/"):
            relative_path = normalized_path[len(normalized_root) + 1 :]
        else:
            relative_path = normalized_path.lstrip("/")
        relative = Path(relative_path)
        parent = str(relative.parent).replace("\\", "/")
        if parent == ".":
            parent = ""
        return RemoteFileInfo(
            path=remote_path,
            relative_path=relative_path,
            parent=parent,
            name=relative.name,
            size=size,
        )
