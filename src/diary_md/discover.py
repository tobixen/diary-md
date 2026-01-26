"""Discover diary files in a directory."""

import re
from datetime import datetime
from pathlib import Path


def parse_diary_filename(filename: str) -> tuple[datetime | None, datetime | None]:
    """Parse diary filename to extract date range.

    Supports formats:
    - diary-2026.md -> covers year 2026 (Jan 1 to Dec 31)
    - diary-202401.md -> covers from Jan 2024 onwards
    - diary-202312.md -> covers from Dec 2023 onwards

    Returns:
        Tuple of (start_date, end_date) where end_date may be None for open-ended files.
        Returns (None, None) if filename doesn't match expected pattern.
    """
    # Match diary-YYYY.md or diary-YYYYMM.md patterns
    match = re.match(r'^diary-?(\d{4})(\d{2})?\.md$', filename, re.IGNORECASE)
    if not match:
        # Also try with prefix like diary-oslo-202512.md
        match = re.match(r'^diary-[a-z]+-(\d{4})(\d{2})?\.md$', filename, re.IGNORECASE)

    if not match:
        return (None, None)

    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else 1

    start_date = datetime(year, month, 1)

    # End date is open-ended (None) - the file may still be actively used
    return (start_date, None)


def find_diary_files(
    directory: Path | None = None,
    pattern: str = "diary*.md",
    for_date: datetime | None = None,
) -> list[Path]:
    """Find diary files in directory.

    Args:
        directory: Directory to search (default: current directory)
        pattern: Glob pattern to match (default: diary*.md)
        for_date: If specified, filter to files that might contain this date

    Returns:
        List of diary file paths, sorted by start date (newest first)
    """
    if directory is None:
        directory = Path.cwd()

    files = list(directory.glob(pattern))

    # Parse dates and sort
    files_with_dates = []
    for f in files:
        start_date, end_date = parse_diary_filename(f.name)
        files_with_dates.append((f, start_date, end_date))

    # Sort by start date, newest first (files without dates go last)
    files_with_dates.sort(
        key=lambda x: x[1] if x[1] else datetime.min,
        reverse=True
    )

    # Filter by date if specified
    if for_date:
        filtered = []
        for f, start_date, end_date in files_with_dates:
            if start_date is None:
                # Include files we can't parse (might contain any date)
                filtered.append(f)
            elif start_date <= for_date:
                # File starts before or on the target date
                if end_date is None or end_date >= for_date:
                    filtered.append(f)
        return filtered

    return [f for f, _, _ in files_with_dates]


def get_default_diary_files(directory: Path | None = None) -> list[Path]:
    """Get default diary files for reconciliation/processing.

    Returns all diary*.md files in the directory, sorted newest first.
    """
    return find_diary_files(directory)


def get_diary_file_for_date(
    target_date: datetime,
    directory: Path | None = None,
) -> Path | None:
    """Get the diary file that should contain a specific date.

    Returns the most likely file based on filename parsing.
    Returns None if no suitable file found.
    """
    files = find_diary_files(directory, for_date=target_date)
    return files[0] if files else None


def get_current_diary_file(directory: Path | None = None) -> Path:
    """Get the diary file for current year, creating path if needed.

    Returns path to diary-YYYY.md in the specified directory.
    """
    if directory is None:
        directory = Path.cwd()

    year = datetime.now().year
    return directory / f"diary-{year}.md"
