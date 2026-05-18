from __future__ import annotations

import stat
from dataclasses import dataclass
from ftplib import FTP
from pathlib import Path
from typing import Callable

from app.config import RemoteDataConfig


LogFn = Callable[[str], None]


@dataclass
class RemoteDownloadResult:
    file_count: int = 0
    total_bytes: int = 0


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

    def download_to(self, destination: Path) -> RemoteDownloadResult:
        self._validate_config()
        destination.mkdir(parents=True, exist_ok=True)
        if self.config.protocol == "ftp":
            return self._download_ftp(destination)
        return self._download_sftp(destination)

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

        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._log(f"下载: {remote_path}")
        sftp.get(remote_path, str(local_path))
        result.file_count += 1
        result.total_bytes += int(getattr(attrs, "st_size", 0) or local_path.stat().st_size)

    @staticmethod
    def _join_remote_path(parent: str, child: str) -> str:
        parent = parent.replace("\\", "/").rstrip("/")
        if not parent:
            return child
        if parent == "/":
            return f"/{child}"
        return f"{parent}/{child}"
