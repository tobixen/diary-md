"""Markdown parsing utilities for diary-md."""

import re
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import TextIO

from diary_md.exceptions import DiaryParseError
from diary_md.models import DateHeader, ExpenseLine, DATE_FORMAT, VALID_WEEKDAYS


def markdown_to_dict(file: TextIO, level: int = 1) -> dict:
    """Parse a markdown file into a hierarchical dict structure.

    Takes a markdown file, finds all section headers and subsection headers.
    Creates a hierarchical dict structure where section headers are keys
    and values are dicts containing subsection headers, etc.

    Special keys:
        __content__: Text content within a section
        __file_position__: File position after the section
        __file_name__: Name of the source file

    Args:
        file: Open file handle to read from
        level: Starting header level (1 = #, 2 = ##, etc.)

    Returns:
        Nested dict structure representing the markdown hierarchy
    """
    # Handle non-seekable streams (like piped stdin) by reading into memory
    if not file.seekable():
        file_name = getattr(file, 'name', '<stream>')
        content = file.read()
        file = StringIO(content)
        file.name = file_name  # Preserve original name

    ret_dict: dict = {}
    content = ""

    while True:
        file_position = file.tell()
        line = file.readline()

        if not line:
            if content:
                ret_dict['__content__'] = content
            return ret_dict

        header_level = 0
        while header_level < len(line) and line[header_level] == '#':
            header_level += 1

        if not header_level:
            content += line
            continue

        if content:
            ret_dict['__content__'] = content
            content = ""

        # Special hack for files without a top-level header
        if header_level == level + 1 and level == 1:
            ret_dict['__top__'] = {}
            ret_dict = ret_dict['__top__']
            level = 2

        if header_level < level:
            file.seek(file_position)
            return ret_dict

        if header_level == level:
            section_name = line[header_level:].strip()
            ret_dict[section_name] = markdown_to_dict(file, header_level + 1)
            ret_dict[section_name]['__file_position__'] = file.tell()
            ret_dict[section_name]['__file_name__'] = getattr(file, 'name', '<stream>')
        else:
            raise DiaryParseError(
                f"Invalid header level jump: expected level {level} ({'#'*level}), "
                f"got level {header_level} ({'#'*header_level})",
                file_name=getattr(file, 'name', '<stream>'),
                file_position=file_position,
                section=line.strip(),
                content=line
            )

    return ret_dict


def find_or_create_date_section(content: str, target_date: datetime) -> tuple[int, bool]:
    """Find existing date section or determine where to insert a new one.

    Args:
        content: Full file content
        target_date: The date to find or insert

    Returns:
        Tuple of (line_number, section_exists)
    """
    date_header = f"## {target_date.strftime('%A %Y-%m-%d')}"
    lines = content.split("\n")

    # Check if date already exists (may have itinerary after date)
    for i, line in enumerate(lines):
        if line.strip().startswith(date_header):
            return i, True

    # Find insertion point (chronological order)
    # Pattern allows optional itinerary after date
    date_pattern = re.compile(r"^## \w+ (\d{4}-\d{2}-\d{2})")

    for i, line in enumerate(lines):
        match = date_pattern.match(line.strip())
        if match:
            entry_date = datetime.strptime(match.group(1), DATE_FORMAT)
            if entry_date.date() > target_date.date():
                return i, False

    # Append at end
    return len(lines), False


def find_section_in_date(lines: list[str], start_line: int, section_name: str) -> int | None:
    """Find a section (### Section) within a date entry.

    Args:
        lines: List of file lines
        start_line: Line number where the date entry starts
        section_name: Name of the section to find (case-insensitive)

    Returns:
        Line number of section header, or None if not found
    """
    section_header = f"### {section_name.title()}"
    date_pattern = re.compile(r"^## \w+ \d{4}-\d{2}-\d{2}")

    for i in range(start_line + 1, len(lines)):
        line = lines[i].strip()
        # Stop if we hit the next date
        if date_pattern.match(line):
            return None
        if line.lower() == section_header.lower():
            return i

    return None


def find_section_end(lines: list[str], section_line: int) -> int:
    """Find where a section ends (next ### or ## or end of file).

    Args:
        lines: List of file lines
        section_line: Line number where the section starts

    Returns:
        Line number where the section ends
    """
    for i in range(section_line + 1, len(lines)):
        line = lines[i].strip()
        if line.startswith("## ") or line.startswith("### "):
            return i
    return len(lines)


def parse_diary_to_list(
    md_dict: dict,
    start: datetime | None = None,
    end: datetime | None = None
) -> list[dict]:
    """Convert parsed markdown dict to a list of diary entries.

    Args:
        md_dict: Dict from markdown_to_dict()
        start: Only include dates at or after this date
        end: Only include dates up to and including this date

    Returns:
        List of entry dicts, sorted by date
    """
    ret_list = []
    for header in md_dict:
        if header.startswith('__'):
            continue
        defaults = {'trip': header}
        entries = _parse_subdict_to_list(md_dict[header], defaults, start, end)
        ret_list.extend(entries)
    return ret_list


def _parse_subdict_to_list(
    input_dict: dict,
    defaults: dict,
    start: datetime | None = None,
    end: datetime | None = None
) -> list[dict]:
    """Parse a section's subdict into diary entries.

    Internal helper for parse_diary_to_list.
    """
    ret_list = []

    for day in input_dict:
        if day == 'TODO' or day.startswith('__'):
            continue

        entry = defaults.copy()

        # Parse date header: "Weekday YYYY-MM-DD optional-itinerary"
        findings = re.match(r"^([^ ]*) (20\d\d-\d\d-\d\d)(.*)$", day)
        if not findings:
            raise DiaryParseError(
                "Section header doesn't match expected format 'Weekday YYYY-MM-DD ...'",
                file_name=input_dict[day].get('__file_name__'),
                file_position=input_dict[day].get('__file_position__'),
                section=day,
                content=input_dict[day].get('__content__', '')[:100]
            )

        dow, date_str, itinerary = findings.groups()

        # Validate weekday
        if dow not in VALID_WEEKDAYS:
            raise DiaryParseError(
                f"Unknown weekday '{dow}'",
                file_name=input_dict[day].get('__file_name__'),
                file_position=input_dict[day].get('__file_position__'),
                section=day,
                date=date_str
            )

        dt = datetime.strptime(date_str, DATE_FORMAT)

        # Check weekday matches date
        if dt.strftime('%A') != dow:
            raise DiaryParseError(
                f"Weekday mismatch: '{dow}' is not the correct day for {date_str} "
                f"(should be {dt.strftime('%A')})",
                file_name=input_dict[day].get('__file_name__'),
                file_position=input_dict[day].get('__file_position__'),
                section=day,
                date=date_str
            )

        # Apply date filters
        if start and dt < start:
            continue
        if end and dt > end:
            continue

        # Parse itinerary into list
        itinerary_list = []
        parts = itinerary.split(' - ')
        for part in parts:
            match = re.match(r"^([^(]*)(\(.*\))?$", part)
            if match:
                itinerary_list.append(match.group(1))
                if match.group(2):
                    itinerary_list.append(match.group(2))

        entry['dow'] = dow
        entry['date'] = date_str
        entry['itenary'] = itinerary
        entry['itenary_list'] = itinerary_list
        entry.update(input_dict[day])
        ret_list.append(entry)

    # Sort by date, then file position
    ret_list.sort(key=lambda x: f"{x['date']}{x.get('__file_name__', '')}{x.get('__file_position__', 0)}")

    # Validate chronological order
    _validate_chronological_order(ret_list)

    return ret_list


def _validate_chronological_order(entries: list[dict]) -> None:
    """Validate that entries are in chronological order."""
    last_fn = ''
    last_fp = 0
    last_dt = '1970-01-01'
    last_section = ''

    for entry in entries:
        fn = entry.get('__file_name__', '')
        fp = entry.get('__file_position__', 0)
        dt = entry['date']
        section = f"{entry['dow']} {entry['date']} {entry.get('itenary', '')}"

        if dt <= last_dt or (fn == last_fn and fp <= last_fp):
            raise DiaryParseError(
                "Entries not in chronological order or duplicate date",
                file_name=fn,
                file_position=fp,
                section=section,
                date=dt,
                content=f"Previous: {last_section} ({last_dt})"
            )

        last_fn = fn
        last_fp = fp
        last_dt = dt
        last_section = section


def parse_diary_expenses(filepath: Path) -> list[dict]:
    """Parse expense entries from a diary file.

    Args:
        filepath: Path to diary file

    Returns:
        List of dicts with expense info (date, amount, currency, etc.)
    """
    expenses = []

    if not filepath.exists():
        return expenses

    # Pattern for date headers
    date_pattern = re.compile(r'^## \w+ (\d{4}-\d{2}-\d{2})')

    # Pattern to detect already reconciled entries
    reconciled_pattern = re.compile(r'\(reconciled:')

    # Pattern to detect cash expenses
    cash_pattern = re.compile(r'\(cash\)', re.IGNORECASE)

    # Pattern for split markers
    split_marker_pattern = re.compile(
        r'\((reconciled:\s*)?(\w+)\s*-\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\w+):(\d+\.?\d*)/(\d+)\)'
    )

    current_date = None

    with open(filepath, encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            original_line = line.rstrip('\n')
            line_stripped = line.strip()

            # Check for date header
            date_match = date_pattern.match(line_stripped)
            if date_match:
                current_date = datetime.strptime(date_match.group(1), DATE_FORMAT)
                continue

            if current_date is None:
                continue

            # Try to parse as expense line
            expense = ExpenseLine.parse(line_stripped)
            if not expense:
                continue

            # Check for split marker
            split_match = split_marker_pattern.search(line_stripped)
            split_marker = None
            if split_match:
                is_reconciled = split_match.group(1) is not None
                if is_reconciled:
                    continue  # Already reconciled split
                split_marker = (
                    f"{split_match.group(2)} - {split_match.group(3)} - "
                    f"{split_match.group(4)}:{split_match.group(5)}/{split_match.group(6)}"
                )
            elif reconciled_pattern.search(line_stripped):
                continue  # Already reconciled

            # Skip cash expenses
            if cash_pattern.search(line_stripped):
                continue

            expenses.append({
                'date': current_date,
                'amount': expense.amount,
                'currency': expense.currency,
                'expense_type': expense.expense_type,
                'description': expense.description,
                'source_file': str(filepath),
                'line_num': line_num,
                'original_line': original_line,
                'split_marker': split_marker,
            })

    return expenses
