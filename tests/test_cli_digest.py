"""Tests for diary_md.cli.digest module."""

import json

import pytest
from click.testing import CliRunner

from diary_md.cli.digest import digest


class TestDigestExpenses:
    """Tests for diary-digest expenses command."""

    def test_expenses_basic(self, sample_diary_file):
        """Parse and summarize expenses from diary."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(sample_diary_file), 'expenses'])

        assert result.exit_code == 0
        assert 'Expenses by category' in result.output
        assert 'groceries' in result.output
        assert 'Total expenses' in result.output

    def test_expenses_currency_conversion(self, sample_diary_file):
        """Expenses in different currencies are converted to EUR."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(sample_diary_file), 'expenses'])

        assert result.exit_code == 0
        # NOK expenses should be converted
        assert 'EUR' in result.output

    def test_expenses_with_date_filter(self, sample_diary_file):
        """Filter expenses by date range."""
        runner = CliRunner()
        result = runner.invoke(digest, [
            '--diary', str(sample_diary_file),
            '--from', '2026-01-20',
            '--to', '2026-01-20',
            'expenses'
        ])

        assert result.exit_code == 0


class TestDigestFindAllSubsections:
    """Tests for diary-digest find-all-subsections command."""

    def test_find_all_subsections(self, sample_diary_file, tmp_path):
        """Find all subsection titles in diary."""
        # Create a config file with allowable_subsections
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "allowable_subsections": ["Expenses", "Notes", "Weather"]
        }))

        runner = CliRunner()
        result = runner.invoke(digest, [
            '--diary', str(sample_diary_file),
            'find-all-subsections', '--config', str(config_file)
        ])

        assert result.exit_code == 0
        assert 'Allowable, but missing' in result.output
        assert 'Not allowable, but found' in result.output

    def test_find_subsections_reports_non_standard(self, tmp_path):
        """Report non-standard subsection names."""
        diary_content = """\
# Trip

## Tuesday 2026-01-20

### Custom Section

Some content here.
"""
        diary_file = tmp_path / "diary.md"
        diary_file.write_text(diary_content)

        # Create a config file that doesn't allow "Custom Section"
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "allowable_subsections": ["Expenses", "Notes"]
        }))

        runner = CliRunner()
        result = runner.invoke(digest, [
            '--diary', str(diary_file),
            'find-all-subsections', '--config', str(config_file)
        ])

        assert result.exit_code == 0
        assert 'Not allowed: Custom Section' in result.output


class TestDigestMalformedDateHeader:
    """A malformed date header should not break commands that don't need dates."""

    @pytest.fixture
    def broken_diary_file(self, tmp_path):
        """Diary with a date header lacking the date part."""
        diary_file = tmp_path / "broken.md"
        diary_file.write_text("""\
# Trip

## Tuesday 2026-01-20

### Expenses

* EUR 15.72 - groceries - Lidl

## Tuesday

### Notes

Header above is missing its date.
""")
        return diary_file

    def test_find_all_subsections_ignores_date_parse_errors(self, broken_diary_file, tmp_path):
        """find-all-subsections only needs the section tree, not parsed dates."""
        # Explicit empty config, so the user's own config file is not picked up
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        runner = CliRunner()
        result = runner.invoke(digest, [
            '--diary', str(broken_diary_file),
            'find-all-subsections', '--config', str(config_file)
        ])

        assert result.exit_code == 0
        assert 'Expenses' in result.output
        assert 'Notes' in result.output

    def test_export_web_json_ignores_date_parse_errors(self, broken_diary_file):
        """export-web-json works off the raw dict as well."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(broken_diary_file), 'export-web-json'])

        assert result.exit_code == 0
        assert json.loads(result.output)['trips']

    def test_date_parse_error_is_reported_without_traceback(self, broken_diary_file):
        """Commands that do need dates fail cleanly, not with a stack trace."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(broken_diary_file), 'expenses'])

        assert result.exit_code != 0
        assert result.exception is None or isinstance(result.exception, SystemExit)
        assert "doesn't match expected format" in result.output
        assert 'Traceback' not in result.output


class TestDigestHelp:
    """The help text should explain where the diary comes from."""

    def test_help_mentions_stdin_default(self):
        """--diary defaults to stdin; the user needs to be told."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--help'])

        assert result.exit_code == 0
        assert 'stdin' in result.output.lower()


class TestDigestSelectSubsection:
    """Tests for diary-digest select-subsection command."""

    def test_select_expenses_section(self, sample_diary_file):
        """Extract Expenses sections from diary."""
        runner = CliRunner()
        result = runner.invoke(digest, [
            '--diary', str(sample_diary_file),
            'select-subsection', '--section', 'Expenses'
        ])

        assert result.exit_code == 0
        assert 'EUR' in result.output or 'NOK' in result.output

    def test_select_maintenance_section(self, sample_diary_file):
        """Extract Maintenance sections from diary."""
        runner = CliRunner()
        result = runner.invoke(digest, [
            '--diary', str(sample_diary_file),
            'select-subsection', '--section', 'Maintenance'
        ])

        assert result.exit_code == 0
        assert 'rudder' in result.output.lower()


class TestDigestExportJson:
    """Tests for diary-digest export-json command."""

    def test_export_json(self, sample_diary_file):
        """Export diary as JSON."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(sample_diary_file), 'export-json'])

        assert result.exit_code == 0
        # Should be valid JSON (list)
        assert result.output.strip().startswith('[')
        assert result.output.strip().endswith(']')
