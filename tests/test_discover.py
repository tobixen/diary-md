"""Tests for diary file discovery."""

from datetime import datetime

from diary_md.discover import (
    find_diary_files,
    get_current_diary_file,
    get_diary_file_for_date,
    parse_diary_filename,
)


class TestParseDiaryFilename:
    """Test diary filename parsing."""

    def test_year_only(self):
        """Parse diary-YYYY.md format."""
        start, end = parse_diary_filename("diary-2026.md")
        assert start == datetime(2026, 1, 1)
        assert end is None

    def test_year_month(self):
        """Parse diary-YYYYMM.md format."""
        start, end = parse_diary_filename("diary-202401.md")
        assert start == datetime(2024, 1, 1)
        assert end is None

    def test_year_month_december(self):
        """Parse diary-YYYYMM.md format with December."""
        start, end = parse_diary_filename("diary-202312.md")
        assert start == datetime(2023, 12, 1)
        assert end is None

    def test_with_prefix(self):
        """Parse diary-prefix-YYYYMM.md format."""
        start, end = parse_diary_filename("diary-oslo-202512.md")
        assert start == datetime(2025, 12, 1)
        assert end is None

    def test_unrecognized_format(self):
        """Return None for unrecognized formats."""
        start, end = parse_diary_filename("notes.md")
        assert start is None
        assert end is None

    def test_old_txt_format(self):
        """Return None for old .txt format."""
        start, end = parse_diary_filename("diary-2023.txt")
        assert start is None
        assert end is None


class TestFindDiaryFiles:
    """Test diary file discovery."""

    def test_finds_files(self, tmp_path):
        """Find diary files in directory."""
        (tmp_path / "diary-2026.md").touch()
        (tmp_path / "diary-202401.md").touch()
        (tmp_path / "notes.md").touch()

        files = find_diary_files(tmp_path)
        names = [f.name for f in files]

        assert "diary-2026.md" in names
        assert "diary-202401.md" in names
        assert "notes.md" not in names

    def test_sorted_newest_first(self, tmp_path):
        """Files are sorted with newest first."""
        (tmp_path / "diary-2023.md").touch()
        (tmp_path / "diary-2026.md").touch()
        (tmp_path / "diary-202401.md").touch()

        files = find_diary_files(tmp_path)
        names = [f.name for f in files]

        assert names[0] == "diary-2026.md"
        assert names[1] == "diary-202401.md"
        assert names[2] == "diary-2023.md"

    def test_filter_by_date(self, tmp_path):
        """Filter files by date."""
        (tmp_path / "diary-2023.md").touch()
        (tmp_path / "diary-2026.md").touch()

        # Date in 2024 - only 2023 file starts before it
        files = find_diary_files(tmp_path, for_date=datetime(2024, 6, 15))
        names = [f.name for f in files]

        assert "diary-2023.md" in names
        assert "diary-2026.md" not in names


class TestGetCurrentDiaryFile:
    """Test getting current diary file path."""

    def test_returns_path_in_directory(self, tmp_path):
        """Returns path to diary-YYYY.md in directory."""
        result = get_current_diary_file(tmp_path)
        year = datetime.now().year
        assert result == tmp_path / f"diary-{year}.md"

    def test_default_directory(self):
        """Default directory is current working directory."""
        result = get_current_diary_file()
        year = datetime.now().year
        assert result.name == f"diary-{year}.md"


class TestGetDiaryFileForDate:
    """Test getting diary file for specific date."""

    def test_finds_correct_file(self, tmp_path):
        """Find file that covers the date."""
        (tmp_path / "diary-2023.md").touch()
        (tmp_path / "diary-2026.md").touch()

        result = get_diary_file_for_date(datetime(2024, 6, 15), tmp_path)
        assert result.name == "diary-2023.md"

    def test_returns_none_if_no_match(self, tmp_path):
        """Return None if no file covers the date."""
        (tmp_path / "diary-2026.md").touch()

        result = get_diary_file_for_date(datetime(2020, 1, 1), tmp_path)
        assert result is None
