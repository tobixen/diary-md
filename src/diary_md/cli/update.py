"""diary-update: Add entries to diary files."""

import sys
from datetime import datetime
from pathlib import Path

import click

from diary_md.git import git_commit, git_push
from diary_md.parser import find_or_create_date_section, find_section_end, find_section_in_date


def get_diary_file() -> Path:
    """Get the diary file path for current year."""
    year = datetime.now().year
    return Path.home() / "solveig" / f"diary-{year}.md"


def format_date_header(dt: datetime) -> str:
    """Format date for diary header (## Weekday YYYY-MM-DD)."""
    return f"## {dt.strftime('%A %Y-%m-%d')}"


def format_expense_line(amount: float, currency: str, expense_type: str, description: str) -> str:
    """Format an expense line."""
    return f"* {currency} {amount:.2f} - {expense_type} - {description}"


def update_diary(
    diary_file: Path,
    target_date: datetime,
    section: str,
    line: str,
    dry_run: bool = False
) -> None:
    """Update the diary with a new entry."""
    if not diary_file.exists():
        click.echo(f"Error: Diary file not found: {diary_file}", err=True)
        sys.exit(1)

    with open(diary_file) as f:
        content = f.read()

    lines = content.split("\n")
    date_line, date_exists = find_or_create_date_section(content, target_date)

    if not date_exists:
        # Create new date section with the entry
        date_header = format_date_header(target_date)
        section_header = f"### {section.title()}"
        new_block = [
            "",
            date_header,
            "",
            section_header,
            "",
            line,
        ]
        lines = lines[:date_line] + new_block + lines[date_line:]
        action = f"Created new date section for {target_date.strftime('%Y-%m-%d')}"
    else:
        # Date exists, find or create section
        section_line = find_section_in_date(lines, date_line, section)

        if section_line is None:
            # Create section at end of date entry
            section_end = find_section_end(lines, date_line)
            section_header = f"### {section.title()}"
            new_block = [
                "",
                section_header,
                "",
                line,
            ]
            lines = lines[:section_end] + new_block + lines[section_end:]
            action = f"Created new '{section}' section"
        else:
            # Section exists, add line at end of section
            section_end = find_section_end(lines, section_line)
            # Insert before section_end, skip empty lines at end
            insert_at = section_end
            while insert_at > section_line and lines[insert_at - 1].strip() == "":
                insert_at -= 1
            lines.insert(insert_at, line)
            action = f"Added to existing '{section}' section"

    new_content = "\n".join(lines)

    if dry_run:
        click.echo("=== DRY RUN ===")
        click.echo(f"Would update: {diary_file}")
        click.echo(f"Action: {action}")
        click.echo(f"Line: {line}")
        click.echo()
        # Show context
        for i, current_line in enumerate(lines):
            if line in current_line or format_date_header(target_date) in current_line:
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                click.echo("Context:")
                for j in range(start, end):
                    marker = ">>>" if lines[j] == line else "   "
                    click.echo(f"{marker} {j}: {lines[j]}")
                break
    else:
        with open(diary_file, "w") as f:
            f.write(new_content)
        click.echo(f"Updated {diary_file}")
        click.echo(action)
        click.echo(f"Added: {line}")


def ensure_section_exists(
    diary_file: Path,
    target_date: datetime,
    section: str,
    dry_run: bool = False
) -> bool:
    """Ensure date and section exist in diary, but don't add any content.

    Returns True if file was modified.
    """
    if not diary_file.exists():
        click.echo(f"Error: Diary file not found: {diary_file}", err=True)
        sys.exit(1)

    with open(diary_file) as f:
        content = f.read()

    lines = content.split("\n")
    date_line, date_exists = find_or_create_date_section(content, target_date)
    modified = False

    if not date_exists:
        # Create new date section
        date_header = format_date_header(target_date)
        section_header = f"### {section.title()}"
        new_block = [
            "",
            date_header,
            "",
            section_header,
            "",
        ]
        lines = lines[:date_line] + new_block + lines[date_line:]
        modified = True
        action = f"Created date section for {target_date.strftime('%Y-%m-%d')} with {section} subsection"
    else:
        # Date exists, check if section exists
        section_line = find_section_in_date(lines, date_line, section)
        if section_line is None:
            # Create section at end of date entry
            section_end = find_section_end(lines, date_line)
            section_header = f"### {section.title()}"
            new_block = [
                "",
                section_header,
                "",
            ]
            lines = lines[:section_end] + new_block + lines[section_end:]
            modified = True
            action = f"Created '{section}' section for {target_date.strftime('%Y-%m-%d')}"
        else:
            action = f"Section '{section}' already exists for {target_date.strftime('%Y-%m-%d')}"

    if dry_run:
        click.echo("=== DRY RUN ===")
        click.echo(f"Action: {action}")
        if modified:
            click.echo("Would modify file")
    else:
        if modified:
            new_content = "\n".join(lines)
            with open(diary_file, "w") as f:
                f.write(new_content)
            click.echo(f"Updated {diary_file}")
        click.echo(action)

    return modified


@click.command()
@click.option('--section', '-s', default='expenses', help='Section name (default: expenses)')
@click.option('--date', '-d', default=datetime.now().strftime("%Y-%m-%d"), help='Date (YYYY-MM-DD, default: today)')
@click.option('--line', '-l', help="Full line to add (e.g., 'EUR 7.10 - groceries - Lidl')")
@click.option('--amount', '-a', type=float, help='Amount (used with --currency, --type, --description)')
@click.option('--currency', '-c', default='EUR', help='Currency (default: EUR)')
@click.option('--type', '-t', 'expense_type', default='groceries', help='Expense type (default: groceries)')
@click.option('--description', help="Description (e.g., 'Lidl (milk, bread)')")
@click.option('--commit', is_flag=True, help='Git commit after updating')
@click.option('--push', is_flag=True, help='Git push after committing (implies --commit)')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be done without modifying files')
def update(section, date, line, amount, currency, expense_type, description, commit, push, dry_run):
    """Add an entry to the diary."""
    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError as e:
        raise click.BadParameter(f"Invalid date format: {date} (expected YYYY-MM-DD)") from e

    diary_file = get_diary_file()

    # Determine the line to add (if any)
    entry_line = None
    if line:
        entry_line = f"* {line}"
    elif amount is not None and description:
        entry_line = format_expense_line(amount, currency, expense_type, description)
    elif description:
        raise click.UsageError("--description requires --amount for expense entries. Use --line for non-expense entries.")

    # Update diary
    if entry_line:
        update_diary(diary_file, target_date, section, entry_line, dry_run)
    else:
        # Just ensure section exists
        ensure_section_exists(diary_file, target_date, section, dry_run)

    # Git operations
    if dry_run:
        if commit or push:
            click.echo("Would commit changes")
        if push:
            click.echo("Would push to remote")
    else:
        if push:
            commit = True  # --push implies --commit

        if commit:
            message = f"Add {target_date.strftime('%Y-%m-%d')} {section}"
            if git_commit(diary_file.parent, [diary_file], message):
                if push:
                    git_push(diary_file.parent)


def main():
    """Entry point for diary-update command."""
    update()


if __name__ == "__main__":
    main()
