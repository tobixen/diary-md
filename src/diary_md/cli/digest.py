"""diary-digest: Analyze and extract information from diary files."""

import fnmatch
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import click

from diary_md.exceptions import DiaryParseError
from diary_md.exchange import get_exchange_rate
from diary_md.models import find_section
from diary_md.parser import markdown_to_dict, parse_diary_to_list
from diary_md.redact import PublicPolicy, RedactionReport, public_text, redact_diary

DATE_FORMAT = "%Y-%m-%d"

# Default config file location
DEFAULT_CONFIG_FILE = Path.home() / ".config" / "diary-md" / "config.json"


def load_config(config_file: Path | None = None) -> dict:
    """Load configuration from JSON file.

    Config format (simple):
    {
        "allowable_subsections": ["Expenses", "Maintenance", ...]
    }

    Config format (with diary-specific patterns):
    {
        "diary_configs": {
            "**/boat-diary/*": {
                "allowable_subsections": ["Expenses", "Maintenance", ...]
            },
            "**/home-diary/*": {
                "allowable_subsections": ["Kostnader", "Tidsbruk", ...]
            }
        },
        "allowable_subsections": ["default", "sections", "..."]
    }
    """
    if config_file is None:
        config_file = DEFAULT_CONFIG_FILE

    if not config_file.exists():
        return {}

    try:
        with open(config_file, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def get_config_for_diary(cfg: dict, diary_path: str) -> dict:
    """Get the configuration for a specific diary file.

    Matches diary path against patterns in diary_configs.
    Falls back to top-level config if no pattern matches.
    """
    diary_configs = cfg.get('diary_configs', {})

    for pattern, diary_cfg in diary_configs.items():
        if fnmatch.fnmatch(diary_path, pattern):
            return diary_cfg

    # Return top-level config as default
    return cfg


class DiaryGroup(click.Group):
    """Group reporting diary parse errors as clean messages rather than tracebacks."""

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except DiaryParseError as e:
            raise click.ClickException(str(e)) from e


def get_diary_list(ctx) -> list[dict]:
    """Return the parsed list of diary entries, parsing on first use.

    Parsing validates date headers and chronology, so it is deferred until a
    command actually asks for it — commands working on the raw section tree
    (find-all-subsections, export-web-json) should not fail on a broken date
    header elsewhere in the diary.
    """
    if 'diary_list' not in ctx.obj:
        ctx.obj['diary_list'] = parse_diary_to_list(
            ctx.obj['md_dict'], start=ctx.obj['start'], end=ctx.obj['end']
        )
    return ctx.obj['diary_list']


@click.group(cls=DiaryGroup)
@click.option('--start', help='Only show dates at or after this date', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--begin', 'start', help='alias for start', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--since', 'start', help='alias for start', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--from', 'start', help='alias for start', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--end', help='Only show dates up until and including this date', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--to', 'end', help='alias for end', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--until', 'end', help='alias for end', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--diary', type=click.File('r'), default=(sys.stdin,), multiple=True,
              help='Diary file to read; repeat for several files. Defaults to stdin.')
@click.pass_context
def digest(ctx, diary, start, end):
    """Analyze and extract information from markdown diary files.

    Diary files are given with --diary, which may be repeated:

        diary-digest --diary diary-2025.md --diary diary-2026.md expenses

    With no --diary option the diary is read from stdin, so the command hangs
    waiting for input if nothing is piped in:

        cat diary-2026.md | diary-digest expenses

    Passing files with --diary is preferable to piping several of them in at
    once: concatenated files are seen as one stream, so error messages lose
    the file name and the entries must be in chronological order across the
    whole concatenation.
    """
    ctx.ensure_object(dict)
    ctx.obj['md_dict'] = {}
    ctx.obj['diary_paths'] = []
    ctx.obj['start'] = start
    ctx.obj['end'] = end
    ctx.obj['diary_texts'] = []
    for d in diary:
        # Kept raw for the public export, which strips private fences before parsing
        name = getattr(d, 'name', '<stream>')
        text = d.read()
        ctx.obj['diary_texts'].append((name, text))
        stream = io.StringIO(text)
        stream.name = name
        ctx.obj['md_dict'].update(markdown_to_dict(stream))
        # Track diary paths for config lookup
        if hasattr(d, 'name') and d.name != '<stdin>':
            ctx.obj['diary_paths'].append(d.name)


@digest.command()
@click.pass_context
@click.option('--section', multiple=True, help='Section(s) to extract')
def select_subsection(ctx, section):
    """Extract specific subsections from diary entries."""
    header = ""
    for x in get_diary_list(ctx):
        if x['trip'] != header:
            click.echo(f"# {x['trip']}")
            click.echo()
            header = x['trip']
        day_print = False
        for s in section:
            if s in x:
                if not day_print:
                    click.echo(f"## {x['dow']} {x['date']} {x['itenary']}")
                    click.echo()
                    day_print = True
                click.echo(f"### {s}")
                click.echo(x[s]['__content__'])


@digest.command()
@click.pass_context
def export_json(ctx):
    """Export diary as JSON (list format)."""
    click.echo(json.dumps(get_diary_list(ctx)))


def _web_day(day_header: str, day_data: dict) -> dict | None:
    """One day in the web viewer format, or None if it has no content."""
    date_match = re.search(r'20\d\d-\d\d-\d\d', day_header)
    sections = {}
    # Main day content (prose before any ### subsection)
    main_content = day_data.get('__content__', '').strip()
    if main_content:
        sections[''] = main_content
    for section_name in day_data:
        if not section_name.startswith('__'):
            sections[section_name] = day_data[section_name].get('__content__', '')
    if not sections:
        return None
    return {
        "date": date_match.group(0) if date_match else "",
        "dateString": day_header,
        "sections": sections,
    }


def _web_trip(title: str, days: dict) -> dict | None:
    dates = [
        d for header, data in days.items()
        if not header.startswith('__') and isinstance(data, dict)
        for d in [_web_day(header, data)] if d
    ]
    return {"title": title, "dates": dates} if dates else None


def web_json(md_dict: dict) -> dict:
    """The diary in the hierarchical trip/date/section format of diary-viewer.html."""
    def looks_like_date(key):
        return bool(re.match(r'^[A-Za-zæøåÆØÅ]+ 20\d\d-\d\d-\d\d', key))

    # Top-level keys may be date headers directly, with no trip wrapper
    non_meta_keys = [k for k in md_dict if not k.startswith('__')]
    if non_meta_keys and all(looks_like_date(k) for k in non_meta_keys):
        trips = [_web_trip("Diary", md_dict)]
    else:
        trips = [
            _web_trip(header, data) for header, data in md_dict.items()
            if not header.startswith('__') and isinstance(data, dict)
        ]
    return {"trips": [t for t in trips if t]}


def public_diary(ctx, policy_file: Path, places: Path | None) -> tuple[dict, RedactionReport]:
    """Parse the diaries again with private fences and comments stripped, and redact them."""
    try:
        policy = PublicPolicy.load(policy_file)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    md_dict: dict = {}
    for name, text in ctx.obj['diary_texts']:
        stream = io.StringIO(public_text(text))
        stream.name = name
        md_dict.update(markdown_to_dict(stream))
    known = set()
    if places:
        with open(places, encoding='utf-8') as f:
            for place, aliases in json.load(f).items():
                known |= {place, *aliases}
    try:
        return redact_diary(md_dict, policy, known_words=known)
    except ValueError as e:
        raise click.ClickException(f'{policy_file}: {e}') from e


POLICY_HELP = 'Public policy JSON: people registry, public/private sections, allowed words, reviewed_up_to'
PLACES_HELP = 'Place aliases JSON (as used by the viewer); its names count as known words'


@digest.command()
@click.pass_context
@click.option('--pretty', is_flag=True, help='Pretty-print JSON output')
@click.option('--public', 'policy', type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help=f'Export the public version. {POLICY_HELP}')
@click.option('--places', type=click.Path(exists=True, dir_okay=False, path_type=Path), help=PLACES_HELP)
@click.option('--allow-unknown', is_flag=True,
              help='With --public: export even if unknown capitalised words remain')
def export_web_json(ctx, pretty, policy, places, allow_unknown):
    """Export diary as JSON for web viewer.

    Outputs JSON in the format expected by diary-viewer.html with
    hierarchical trip/date/section structure.

    With --public, only the reviewed, whitelisted and name-redacted part of
    the diary is exported; see check-public.  The report goes to stderr, and
    unknown capitalised words make the export fail unless --allow-unknown.
    """
    if not policy and (places or allow_unknown):
        raise click.UsageError('--places and --allow-unknown only apply with --public')
    if policy:
        md_dict, report = public_diary(ctx, policy, places)
        if report.format():
            click.echo(report.format(), err=True)
        if report.unknown_tokens and not allow_unknown:
            raise click.ClickException('unknown capitalised words; add them to the policy or pass --allow-unknown')
    else:
        md_dict = ctx.obj['md_dict']
    output = web_json(md_dict)
    if pretty:
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        click.echo(json.dumps(output, ensure_ascii=False))


@digest.command()
@click.pass_context
@click.option('--policy', required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help=POLICY_HELP)
@click.option('--places', type=click.Path(exists=True, dir_okay=False, path_type=Path), help=PLACES_HELP)
def check_public(ctx, policy, places):
    """Report what the public export would leave for a human to classify.

    Exits 1 if there are unknown capitalised words — usable as a pre-commit
    hook.  Unclassified sections and days mentioning children are reported
    but do not fail: the former are left out anyway, the latter are a reminder.
    """
    _, report = public_diary(ctx, policy, places)
    if report.format():
        click.echo(report.format())
    if report.unknown_tokens:
        ctx.exit(1)

@digest.command()
@click.pass_context
@click.option('--config', type=click.Path(exists=True, path_type=Path),
              help=f'Config file (default: {DEFAULT_CONFIG_FILE})')
def find_all_subsections(ctx, config):
    """Find all subsection titles used in the diary.

    If a config file defines allowable_subsections, validates against that list.
    Otherwise, just reports all found subsections.

    Supports diary-specific configs with glob patterns in diary_configs section.
    """
    md_dict = ctx.obj['md_dict']
    diary_paths = ctx.obj.get('diary_paths', [])

    # Load config and get diary-specific settings
    cfg = load_config(config)

    # If we have diary paths, try to get diary-specific config
    allowable_from_config = []
    if diary_paths:
        # Use first diary's config (could be enhanced to merge configs)
        diary_cfg = get_config_for_diary(cfg, diary_paths[0])
        allowable_from_config = diary_cfg.get('allowable_subsections', [])
    else:
        allowable_from_config = cfg.get('allowable_subsections', [])

    # Always allow internal keys
    allowable_subsection_titles = {'__content__', '__file_position__', '__file_name__'}
    allowable_subsection_titles.update(allowable_from_config)

    subsection_titles = set()

    def _looks_like_date(key: str) -> bool:
        """Check if key looks like a date header."""
        import re
        return bool(re.match(r'^[A-Za-zæøåÆØÅ]+ 20\d\d-\d\d-\d\d', key))

    # Check if top-level keys are date headers (no trip wrapper)
    non_meta_keys = [k for k in md_dict if not k.startswith('__')]
    direct_dates = non_meta_keys and all(_looks_like_date(k) for k in non_meta_keys)

    if direct_dates:
        # Top-level is date headers directly
        for day in md_dict:
            if not isinstance(day, str) or day.startswith('__'):
                continue
            day_data = md_dict[day]
            if not isinstance(day_data, dict):
                continue
            for subtitle in day_data:
                if not isinstance(subtitle, str) or subtitle.startswith('__'):
                    continue
                subsection_titles.add(subtitle)
                if allowable_from_config and subtitle not in allowable_subsection_titles:
                    click.echo(f"Not allowed: {subtitle} in {day}")
    else:
        # Normal structure: trip headers containing date headers
        for headline in md_dict:
            if not isinstance(md_dict[headline], dict):
                continue
            for day in md_dict[headline]:
                if not isinstance(day, str) or day.startswith('__'):
                    continue
                day_data = md_dict[headline][day]
                if not isinstance(day_data, dict):
                    continue
                for subtitle in day_data:
                    if not isinstance(subtitle, str) or subtitle.startswith('__'):
                        continue
                    subsection_titles.add(subtitle)
                    if allowable_from_config and subtitle not in allowable_subsection_titles:
                        click.echo(f"Not allowed: {subtitle} in {headline}->{day}")

    if allowable_from_config:
        user_allowable = set(allowable_from_config)
        click.echo(f"Allowable, but missing: {user_allowable - subsection_titles!r}")
        click.echo(f"Not allowable, but found: {subsection_titles - user_allowable!r}")
    else:
        click.echo(f"Found subsections: {subsection_titles!r}")
        click.echo(f"(No config file found at {DEFAULT_CONFIG_FILE} - showing all found sections)")


@digest.command()
@click.pass_context
def expenses(ctx):
    """Summarize expenses from diary entries."""
    unaccounted_content = []
    accounted = []

    for entry in get_diary_list(ctx):
        expense_section = find_section(entry, 'Expenses')
        if expense_section is None:
            continue

        unaccounted = ""
        if '__content__' not in expense_section:
            raise DiaryParseError(
                "Expenses section has no content",
                file_name=entry.get('__file_name__'),
                file_position=entry.get('__file_position__'),
                section=f"{entry['dow']} {entry['date']} {entry.get('itenary', '')}",
                date=entry['date']
            )

        expense_date = entry['date']  # YYYY-MM-DD format
        expenses_text = expense_section['__content__'].strip().split('\n')

        for expense in expenses_text:
            if not unaccounted:
                expense = expense.strip()
                if not expense:
                    continue
            findings = re.match(r"^\* ([A-Z]{3}) (-?\d+(?:\.\d+)?) - (.*)$", expense)
            if findings:
                accounted.append((findings.group(1), findings.group(2), findings.group(3), expense_date))
            else:
                unaccounted += expense

        if unaccounted:
            unaccounted_content.append(f"## {entry['dow']} {entry['date']} {entry['itenary']}\n")
            unaccounted_content.append(unaccounted)

    base_currency = 'EUR'

    my_expenses = 0
    total_expenses = 0
    shared_expenses_per_head = 0
    paid_by = defaultdict(float)
    expenses_by_category = defaultdict(float)
    conversion_warnings = []

    for expense in accounted:
        (currency, amount, details, expense_date) = expense
        amount = float(amount)

        if currency != base_currency:
            rate = get_exchange_rate(currency, expense_date)
            if rate is None:
                conversion_warnings.append(f"Unknown currency {currency} on {expense_date}")
                continue
            amount = amount * rate
            currency = base_currency

        total_expenses += amount
        category = details.split(' - ')[0]
        if ' (' in category:
            category = category.split(' (')[0]

        paidbyf = re.search(r"- paid by ([^ ]*)", details)
        if paidbyf:
            paid_by[paidbyf.group(1)] += amount

        sharedf = re.search(r" - DIV(\d+)", details)
        if sharedf:
            divisor = int(sharedf.group(1))
            amount /= divisor
            shared_expenses_per_head += amount

        expenses_by_category[category] += amount
        my_expenses += amount

    click.echo("# Unaccounted text under expenses (look through)")
    click.echo()
    click.echo("\n".join(unaccounted_content))
    click.echo("# Expenses by payer")
    click.echo()
    for payer in paid_by:
        click.echo(f" * {base_currency} {paid_by[payer]:5.2f} - {payer}")
    click.echo()
    click.echo("# Expenses by category")
    click.echo()
    categories = list(expenses_by_category.keys())
    categories.sort(key=lambda x: expenses_by_category[x])
    for cat in categories:
        click.echo(f" * {base_currency} {expenses_by_category[cat]:5.2f} - {cat}")
    click.echo()

    if conversion_warnings:
        click.echo("# Currency conversion warnings")
        click.echo()
        for warning in conversion_warnings:
            click.echo(f" * {warning}")
        click.echo()

    click.echo("# Totals")
    click.echo()
    click.echo(f"Total expenses: {base_currency} {total_expenses:5.2f}")
    click.echo(f"Shared expenses per head: {base_currency} {shared_expenses_per_head:5.2f}")
    click.echo(f"My expenses: {base_currency} {my_expenses:5.2f}")


def main():
    """Entry point for diary-digest command."""
    digest()


if __name__ == '__main__':
    main()
