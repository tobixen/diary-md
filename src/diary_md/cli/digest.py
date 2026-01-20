"""diary-digest: Analyze and extract information from diary files."""

import json
import re
import sys
from collections import defaultdict

import click

from diary_md.exceptions import DiaryParseError
from diary_md.exchange import get_exchange_rate
from diary_md.parser import markdown_to_dict, parse_diary_to_list

DATE_FORMAT = "%Y-%m-%d"


@click.group()
@click.option('--start', help='Only show dates at or after this date', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--begin', 'start', help='alias for start', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--since', 'start', help='alias for start', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--from', 'start', help='alias for start', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--end', help='Only show dates up until and including this date', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--to', 'end', help='alias for end', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--until', 'end', help='alias for end', type=click.DateTime(formats=[DATE_FORMAT]))
@click.option('--diary', type=click.File('r'), default=(sys.stdin,), multiple=True)
@click.pass_context
def digest(ctx, diary, start, end):
    """Analyze and extract information from markdown diary files."""
    ctx.ensure_object(dict)
    ctx.obj['md_dict'] = {}
    for d in diary:
        ctx.obj['md_dict'].update(markdown_to_dict(d))
    ctx.obj['diary_list'] = parse_diary_to_list(ctx.obj['md_dict'], start=start, end=end)


@digest.command()
@click.pass_context
@click.option('--section', multiple=True, help='Section(s) to extract')
def select_subsection(ctx, section):
    """Extract specific subsections from diary entries."""
    header = ""
    for x in ctx.obj['diary_list']:
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
    """Export diary as JSON."""
    click.echo(json.dumps(ctx.obj['diary_list']))


@digest.command()
@click.pass_context
def find_all_subsections(ctx):
    """Find all subsection titles used in the diary."""
    md_dict = ctx.obj['md_dict']
    allowable_subsection_titles = {
        '__content__',
        'Time accounting',
        'Expenses',
        'Mistakes and incidents',
        'Maintenance',
        'Equipment bought',
        'Embarkments and disembarkments',
        'Times and positions'
    }
    subsection_titles = set()
    for headline in md_dict:
        for day in md_dict[headline]:
            if day.startswith('__'):
                continue
            for subtitle in md_dict[headline][day]:
                if subtitle.startswith('__'):
                    continue
                subsection_titles.add(subtitle)
                if subtitle not in allowable_subsection_titles:
                    click.echo(f"Not allowed: {subtitle} in {headline}->{day}")
    click.echo(f"Allowable, but missing: {allowable_subsection_titles - subsection_titles!r}")
    click.echo(f"Not allowable, but found: {subsection_titles - allowable_subsection_titles!r}")


@digest.command()
@click.pass_context
def expenses(ctx):
    """Summarize expenses from diary entries."""
    unaccounted_content = []
    accounted = []

    for entry in ctx.obj['diary_list']:
        if 'Expenses' not in entry:
            continue

        unaccounted = ""
        if '__content__' not in entry['Expenses']:
            raise DiaryParseError(
                "Expenses section has no content",
                file_name=entry.get('__file_name__'),
                file_position=entry.get('__file_position__'),
                section=f"{entry['dow']} {entry['date']} {entry.get('itenary', '')}",
                date=entry['date']
            )

        expense_date = entry['date']  # YYYY-MM-DD format
        expenses_text = entry['Expenses']['__content__'].strip().split('\n')

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
