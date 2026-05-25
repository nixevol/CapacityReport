"""Filename date parsing and per-directory date filtering."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, TypeVar


FILENAME_DATE_RE = re.compile(r"(?<!\d)(20\d{10}(?:\d{2})?)(?!\d)")
T = TypeVar("T")


@dataclass(frozen=True)
class DirectoryDateSelection:
    directory: str
    total_count: int
    selected_count: int
    skipped_count: int
    undated_count: int
    max_date: date | None = None
    start_date: date | None = None


def extract_file_date(filename: str | Path) -> date | None:
    """Extract the first timestamp date from a filename."""
    match = FILENAME_DATE_RE.search(Path(str(filename)).name)
    if not match:
        return None
    return parse_file_timestamp(match.group(1))


def parse_file_timestamp(value: str) -> date | None:
    fmt = "%Y%m%d%H%M%S" if len(value) == 14 else "%Y%m%d%H%M"
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def required_week_days(week_offset: int = 0, today: date | None = None) -> list[date]:
    """Return Monday-Sunday dates for the target natural week.

    week_offset=0 means last week, -1 means the week before last.
    """
    base_day = today or date.today()
    this_monday = base_day - timedelta(days=base_day.weekday())
    target_monday = this_monday - timedelta(days=7 * (1 - week_offset))
    return [target_monday + timedelta(days=offset) for offset in range(7)]


def select_recent_items_by_directory(
    items: Iterable[T],
    *,
    parent_key: Callable[[T], str],
    name_key: Callable[[T], str],
    days: int = 7,
) -> tuple[list[T], list[DirectoryDateSelection]]:
    """Select the latest N natural days of dated files in each directory.

    If a directory has no dated files at all, all files in that directory are
    kept to preserve compatibility with legacy/manual data.
    """
    safe_days = max(int(days), 1)
    groups: dict[str, list[T]] = {}
    for item in items:
        groups.setdefault(parent_key(item), []).append(item)

    selected: list[T] = []
    summaries: list[DirectoryDateSelection] = []
    for directory, group_items in sorted(groups.items(), key=lambda pair: pair[0]):
        dated_items = [(item, extract_file_date(name_key(item))) for item in group_items]
        valid_dates = [file_date for _, file_date in dated_items if file_date]
        if not valid_dates:
            selected.extend(group_items)
            summaries.append(
                DirectoryDateSelection(
                    directory=directory,
                    total_count=len(group_items),
                    selected_count=len(group_items),
                    skipped_count=0,
                    undated_count=len(group_items),
                )
            )
            continue

        max_date = max(valid_dates)
        start_date = max_date - timedelta(days=safe_days - 1)
        group_selected = [
            item
            for item, file_date in dated_items
            if file_date is not None and start_date <= file_date <= max_date
        ]
        selected.extend(group_selected)
        summaries.append(
            DirectoryDateSelection(
                directory=directory,
                total_count=len(group_items),
                selected_count=len(group_selected),
                skipped_count=len(group_items) - len(group_selected),
                undated_count=sum(1 for _, file_date in dated_items if file_date is None),
                max_date=max_date,
                start_date=start_date,
            )
        )

    return selected, summaries
