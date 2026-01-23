"""Markdown parsing utilities for diary-md."""

import re
from datetime import datetime
from pathlib import Path
from typing import TextIO

from diary_md.exceptions import DiaryParseError
from diary_md.models import DATE_FORMAT, VALID_WEEKDAYS, WEEKDAY_TO_INDEX, WEEKDAYS_EN, ExpenseLine


def markdown_to_dict(file: TextIO, level: int = 1) -> dict:
    """Parse a markdown file into a hierarchical dict structure using markdown-it-py.

    This is a refactored version that uses the markdown-it-py library for parsing.
    It maintains backward compatibility with the original markdown_to_dict output format.

    Takes a markdown file, finds all section headers and subsection headers.
    Creates a hierarchical dict structure where section headers are keys
    and values are dicts containing subsection headers, etc.

    Special keys:
        __content__: Text content within a section (paragraphs + list items)
        __paragraphs__: List of paragraph strings (new in v2)
        __list_items__: List of list item dicts (new in v2)
        __file_name__: Name of the source file

    Args:
        file: Open file handle to read from
        level: Starting header level (1 = #, 2 = ##, etc.) - for compatibility, currently ignored

    Returns:
        Nested dict structure representing the markdown hierarchy
    """
    from diary_md import md_adapter

    # Handle non-seekable streams by reading into memory
    file_name = getattr(file, 'name', '<stream>')
    content = file.read()

    # Parse using markdown-it-py
    sections = md_adapter.parse_markdown_string(content)

    def section_to_dict(section: md_adapter.MarkdownSection) -> dict:
        """Convert a MarkdownSection to the expected dict format."""
        result: dict = {}

        # Add content in the original format for backward compatibility
        content_parts = []
        for para in section.paragraphs:
            content_parts.append(para)
            content_parts.append('')

        for item in section.list_items:
            content_parts.append(f"* {item['text']}")
            for nested in item.get('nested', []):
                content_parts.append(f"  * {nested['text']}")

        content_str = '\n'.join(content_parts)
        if content_str:
            result['__content__'] = content_str

        # Add new structured data for v2 consumers
        if section.paragraphs:
            result['__paragraphs__'] = section.paragraphs
        if section.list_items:
            result['__list_items__'] = section.list_items

        result['__file_name__'] = file_name

        # Process subsections recursively
        for subsection in section.subsections:
            result[subsection.heading] = section_to_dict(subsection)

        return result

    # Build the top-level result dict
    ret_dict: dict = {}
    for section in sections:
        ret_dict[section.heading] = section_to_dict(section)

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


def _looks_like_date_header(key: str) -> bool:
    """Check if a key looks like a date header (Weekday YYYY-MM-DD)."""
    return bool(re.match(r'^[A-Za-zæøåÆØÅ]+ 20\d\d-\d\d-\d\d', key))


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

    # Check if top-level keys are date headers (no trip wrapper)
    non_meta_keys = [k for k in md_dict if not k.startswith('__')]
    if non_meta_keys and all(_looks_like_date_header(k) for k in non_meta_keys):
        # Direct date headers at top level - wrap in synthetic trip
        defaults = {'trip': '__default__'}
        entries = _parse_subdict_to_list(md_dict, defaults, start, end)
        ret_list.extend(entries)
    else:
        # Normal structure: trip headers containing date headers
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

        # Check weekday matches date (compare by index to support multiple languages)
        expected_index = dt.weekday()  # Monday=0, Sunday=6
        actual_index = WEEKDAY_TO_INDEX.get(dow)
        if actual_index != expected_index:
            expected_name = WEEKDAYS_EN[expected_index]
            raise DiaryParseError(
                f"Weekday mismatch: '{dow}' is not the correct day for {date_str} "
                f"(should be {expected_name})",
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

        # Check chronological order
        if dt < last_dt:
            raise DiaryParseError(
                "Entries not in chronological order",
                file_name=fn,
                file_position=fp,
                section=section,
                date=dt,
                content=f"Previous: {last_section} ({last_dt})"
            )

        # Check for duplicate entries (same date, same file, same position)
        if dt == last_dt and fn == last_fn and fp == last_fp:
            raise DiaryParseError(
                "Duplicate date entry",
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
