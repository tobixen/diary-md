"""Tests for diary_md.cli.digest module."""

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

    def test_find_all_subsections(self, sample_diary_file):
        """Find all subsection titles in diary."""
        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(sample_diary_file), 'find-all-subsections'])

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

        runner = CliRunner()
        result = runner.invoke(digest, ['--diary', str(diary_file), 'find-all-subsections'])

        assert result.exit_code == 0
        assert 'Not allowed: Custom Section' in result.output


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
