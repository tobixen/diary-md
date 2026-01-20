"""Tests for diary_md.parser module."""

from datetime import datetime
from io import StringIO

import pytest

from diary_md.parser import (
    markdown_to_dict,
    find_or_create_date_section,
    find_section_in_date,
    find_section_end,
    parse_diary_to_list,
    parse_diary_expenses,
)
from diary_md.exceptions import DiaryParseError


class TestMarkdownToDict:
    """Tests for markdown_to_dict function."""

    def test_simple_structure(self):
        """Parse simple markdown structure."""
        content = """\
# Header 1

Content under header 1.

## Section 1.1

Content under section 1.1.

## Section 1.2

Content under section 1.2.
"""
        result = markdown_to_dict(StringIO(content))
        assert 'Header 1' in result
        assert 'Section 1.1' in result['Header 1']
        assert 'Section 1.2' in result['Header 1']

    def test_nested_content(self):
        """Parse nested markdown content."""
        content = """\
# Trip

## Monday 2026-01-20

### Expenses

* EUR 15.00 - groceries - Lidl

### Maintenance

Fixed the thing.
"""
        result = markdown_to_dict(StringIO(content))
        assert 'Trip' in result
        assert 'Monday 2026-01-20' in result['Trip']
        assert 'Expenses' in result['Trip']['Monday 2026-01-20']
        assert '* EUR 15.00' in result['Trip']['Monday 2026-01-20']['Expenses']['__content__']

    def test_content_key(self):
        """Content is stored under __content__ key."""
        content = """\
# Header

Some content here.
More content.
"""
        result = markdown_to_dict(StringIO(content))
        assert '__content__' in result['Header']
        assert 'Some content here.' in result['Header']['__content__']

    def test_invalid_header_jump(self):
        """Invalid header level jump raises error."""
        content = """\
# Header

#### Invalid jump
"""
        with pytest.raises(DiaryParseError) as exc_info:
            markdown_to_dict(StringIO(content))
        assert "Invalid header level jump" in str(exc_info.value)


class TestFindOrCreateDateSection:
    """Tests for find_or_create_date_section function."""

    def test_find_existing_date(self):
        """Find existing date section."""
        content = """\
# Trip

## Tuesday 2026-01-20

Content
"""
        line_num, exists = find_or_create_date_section(content, datetime(2026, 1, 20))
        assert exists is True
        assert line_num == 2

    def test_find_nonexistent_date(self):
        """Determine insertion point for new date."""
        content = """\
# Trip

## Monday 2026-01-20

Content

## Wednesday 2026-01-22

Content
"""
        # Tuesday should be inserted between Monday and Wednesday
        line_num, exists = find_or_create_date_section(content, datetime(2026, 1, 21))
        assert exists is False
        assert line_num == 6  # After Monday's content

    def test_append_at_end(self):
        """New date after all existing dates appends at end."""
        content = """\
# Trip

## Monday 2026-01-20

Content
"""
        line_num, exists = find_or_create_date_section(content, datetime(2026, 1, 25))
        assert exists is False
        assert line_num == 6  # At end (content has 6 lines including trailing newline)


class TestFindSectionInDate:
    """Tests for find_section_in_date function."""

    def test_find_existing_section(self):
        """Find existing section within date."""
        lines = [
            "# Trip",
            "",
            "## Monday 2026-01-20",
            "",
            "### Expenses",
            "",
            "* EUR 15.00",
        ]
        result = find_section_in_date(lines, 2, "expenses")
        assert result == 4

    def test_section_not_found(self):
        """Return None when section doesn't exist."""
        lines = [
            "# Trip",
            "",
            "## Monday 2026-01-20",
            "",
            "### Maintenance",
            "",
        ]
        result = find_section_in_date(lines, 2, "expenses")
        assert result is None

    def test_stops_at_next_date(self):
        """Stop searching at next date header."""
        lines = [
            "## Monday 2026-01-20",
            "",
            "### Maintenance",
            "",
            "## Tuesday 2026-01-21",
            "",
            "### Expenses",
        ]
        result = find_section_in_date(lines, 0, "expenses")
        assert result is None  # Expenses is in Tuesday, not Monday


class TestFindSectionEnd:
    """Tests for find_section_end function."""

    def test_find_section_end_at_next_section(self):
        """Section ends at next section header."""
        lines = [
            "### Expenses",
            "",
            "* EUR 15.00",
            "",
            "### Maintenance",
        ]
        result = find_section_end(lines, 0)
        assert result == 4

    def test_find_section_end_at_date(self):
        """Section ends at next date header."""
        lines = [
            "### Expenses",
            "",
            "* EUR 15.00",
            "",
            "## Tuesday 2026-01-21",
        ]
        result = find_section_end(lines, 0)
        assert result == 4

    def test_find_section_end_at_eof(self):
        """Section ends at end of file."""
        lines = [
            "### Expenses",
            "",
            "* EUR 15.00",
        ]
        result = find_section_end(lines, 0)
        assert result == 3


class TestParseDiaryExpenses:
    """Tests for parse_diary_expenses function."""

    def test_parse_expenses(self, sample_diary_file):
        """Parse expenses from diary file."""
        expenses = parse_diary_expenses(sample_diary_file)

        # Should find unreconciled expenses
        assert len(expenses) > 0

        # Check a specific expense
        lidl_expense = [e for e in expenses if 'Lidl' in e['description']]
        assert len(lidl_expense) == 1
        assert lidl_expense[0]['currency'] == 'EUR'
        assert lidl_expense[0]['amount'] == 15.72

    def test_skip_reconciled(self, sample_diary_file):
        """Skip already reconciled expenses."""
        expenses = parse_diary_expenses(sample_diary_file)

        # The Billa expense is already reconciled
        billa_expense = [e for e in expenses if 'Billa' in e['description']]
        assert len(billa_expense) == 0

    def test_nonexistent_file(self, tmp_path):
        """Return empty list for nonexistent file."""
        expenses = parse_diary_expenses(tmp_path / "nonexistent.md")
        assert expenses == []
