from pathlib import Path


def get_dir_size(path: Path) -> int:
    total_size = 0
    try:
        if path.is_file():
            return path.stat().st_size

        if path.is_dir():
            for item in path.iterdir():
                total_size += get_dir_size(item)
    except (PermissionError, OSError):
        return total_size

    return total_size


def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"

    value = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"

