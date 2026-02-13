"""Tests for diary_md.cli.update module."""

from datetime import datetime

from diary_md.cli.update import (
    detect_diary_language,
    format_date_header,
    format_section_header,
    update_diary,
)
from diary_md.parser import find_or_create_date_section, find_section_in_date

NORWEGIAN_DIARY = """\
# Oslo-stay February

## Tirsdag 2026-02-03

Ankomst Oslo.

### Tidsbruk

* Pauser (mat, soving, underholding, etc)   -      10.4h

## Onsdag 2026-02-04

Enda en dag.

### Tidsbruk

* Pauser (mat, soving, underholding, etc)   -       8.2h

## Fredag 2026-02-06

Endelig fredag.

### Kostnader

* NOK 100 - mat - Rema 1000
"""

ENGLISH_DIARY = """\
# Summer Trip

## Monday 2026-01-20

Some content.

### Expenses

* EUR 15.00 - groceries - Lidl

## Wednesday 2026-01-22

More content.
"""


class TestDetectDiaryLanguage:
    """Tests for detect_diary_language."""

    def test_norwegian_diary(self):
        assert detect_diary_language(NORWEGIAN_DIARY) == 'no'

    def test_english_diary(self):
        assert detect_diary_language(ENGLISH_DIARY) == 'en'

    def test_empty_content(self):
        assert detect_diary_language("") == 'en'

    def test_no_date_headers(self):
        assert detect_diary_language("# Just a title\n\nSome text.") == 'en'


class TestFormatDateHeader:
    """Tests for format_date_header."""

    def test_english(self):
        dt = datetime(2026, 2, 6)  # Friday
        assert format_date_header(dt, 'en') == "## Friday 2026-02-06"

    def test_norwegian(self):
        dt = datetime(2026, 2, 6)  # Fredag
        assert format_date_header(dt, 'no') == "## Fredag 2026-02-06"

    def test_norwegian_monday(self):
        dt = datetime(2026, 2, 9)  # Mandag
        assert format_date_header(dt, 'no') == "## Mandag 2026-02-09"

    def test_default_is_english(self):
        dt = datetime(2026, 2, 6)
        assert format_date_header(dt) == "## Friday 2026-02-06"


class TestFormatSectionHeader:
    """Tests for format_section_header."""

    def test_english(self):
        assert format_section_header("expenses", "en") == "### Expenses"

    def test_norwegian_expenses(self):
        assert format_section_header("expenses", "no") == "### Kostnader"

    def test_norwegian_maintenance(self):
        assert format_section_header("maintenance", "no") == "### Vedlikehold"

    def test_unknown_section_norwegian(self):
        """Unknown sections fall back to title-cased English name."""
        assert format_section_header("custom stuff", "no") == "### Custom Stuff"


class TestFindOrCreateDateSectionNorwegian:
    """Tests for find_or_create_date_section with Norwegian content."""

    def test_find_existing_norwegian_date(self):
        line_num, exists = find_or_create_date_section(
            NORWEGIAN_DIARY, datetime(2026, 2, 6)
        )
        assert exists is True
        assert "Fredag 2026-02-06" in NORWEGIAN_DIARY.split("\n")[line_num]

    def test_find_nonexistent_date_in_norwegian(self):
        line_num, exists = find_or_create_date_section(
            NORWEGIAN_DIARY, datetime(2026, 2, 5)
        )
        assert exists is False
        # Should be inserted between 2026-02-04 and 2026-02-06
        lines = NORWEGIAN_DIARY.split("\n")
        # The insertion point should be after Onsdag content, before Fredag
        assert line_num > 0
        assert line_num <= len(lines)


class TestFindSectionInDateWithAliases:
    """Tests for find_section_in_date with alias matching."""

    def test_find_kostnader_with_expenses(self):
        """Searching for 'expenses' should find '### Kostnader'."""
        lines = NORWEGIAN_DIARY.split("\n")
        # Find Fredag 2026-02-06
        date_line = next(
            i for i, line in enumerate(lines) if "Fredag 2026-02-06" in line
        )
        result = find_section_in_date(lines, date_line, "expenses")
        assert result is not None
        assert "Kostnader" in lines[result]

    def test_find_tidsbruk_with_time_tracking(self):
        """Searching for 'time tracking' should find '### Tidsbruk'."""
        lines = NORWEGIAN_DIARY.split("\n")
        date_line = next(
            i for i, line in enumerate(lines) if "Tirsdag 2026-02-03" in line
        )
        result = find_section_in_date(lines, date_line, "time tracking")
        assert result is not None
        assert "Tidsbruk" in lines[result]

    def test_find_english_section_directly(self):
        """Searching for 'expenses' should find '### Expenses' in English diary."""
        lines = ENGLISH_DIARY.split("\n")
        date_line = next(
            i for i, line in enumerate(lines) if "Monday 2026-01-20" in line
        )
        result = find_section_in_date(lines, date_line, "expenses")
        assert result is not None
        assert "Expenses" in lines[result]


class TestUpdateDiaryNorwegian:
    """Tests for update_diary with Norwegian diary content."""

    def test_add_to_existing_kostnader_section(self, tmp_path):
        """Adding expenses to a Norwegian diary with existing Kostnader section."""
        diary_file = tmp_path / "diary-oslo-2026.md"
        diary_file.write_text(NORWEGIAN_DIARY)

        update_diary(
            diary_file,
            datetime(2026, 2, 6),
            "expenses",
            "* NOK 318 - mat - Coop Prix",
        )

        content = diary_file.read_text()
        lines = content.split("\n")

        # Find the Kostnader section under Fredag
        in_fredag = False
        in_kostnader = False
        found_new_entry = False
        found_existing_entry = False
        for line in lines:
            if "Fredag 2026-02-06" in line:
                in_fredag = True
            elif line.startswith("## ") and in_fredag:
                break
            if in_fredag and "### Kostnader" in line:
                in_kostnader = True
            if in_kostnader and "NOK 318" in line:
                found_new_entry = True
            if in_kostnader and "NOK 100" in line:
                found_existing_entry = True

        assert found_new_entry, "New expense entry not found under Kostnader"
        assert found_existing_entry, "Existing expense entry disappeared"

    def test_create_new_section_in_norwegian(self, tmp_path):
        """Creating a new section in Norwegian diary uses Norwegian name."""
        diary_file = tmp_path / "diary-oslo-2026.md"
        diary_file.write_text(NORWEGIAN_DIARY)

        update_diary(
            diary_file,
            datetime(2026, 2, 3),
            "expenses",
            "* NOK 50 - mat - Kiwi",
        )

        content = diary_file.read_text()
        # New section should use Norwegian name
        assert "### Kostnader" in content
        # Should be under Tirsdag 2026-02-03
        lines = content.split("\n")
        tirsdag_line = next(i for i, line in enumerate(lines) if "Tirsdag 2026-02-03" in line)
        onsdag_line = next(i for i, line in enumerate(lines) if "Onsdag 2026-02-04" in line)
        kostnader_lines = [
            i for i, line in enumerate(lines)
            if "### Kostnader" in line and tirsdag_line < i < onsdag_line
        ]
        assert len(kostnader_lines) == 1

    def test_create_new_date_in_norwegian(self, tmp_path):
        """Creating a new date section in Norwegian diary uses Norwegian weekday."""
        diary_file = tmp_path / "diary-oslo-2026.md"
        diary_file.write_text(NORWEGIAN_DIARY)

        update_diary(
            diary_file,
            datetime(2026, 2, 5),  # Torsdag
            "expenses",
            "* NOK 200 - mat - Meny",
        )

        content = diary_file.read_text()
        assert "## Torsdag 2026-02-05" in content
        assert "### Kostnader" in content
