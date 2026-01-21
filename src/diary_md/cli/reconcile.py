"""diary-reconcile: Reconcile bank expenses with diary entries."""

import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import click

from diary_md.git import git_commit_multiple_repos
from diary_md.models import SUPPORTED_CURRENCIES


@dataclass
class Expense:
    """An expense from bank statement."""
    date: datetime
    amount: float  # Always positive for expenses, original currency
    currency: str
    description: str
    bank: str
    bank_currency: str
    deducted_amount: float  # Amount in bank's account currency
    source_file: str
    line_num: int
    merchant_category: str = ''


@dataclass
class DiaryExpense:
    """An expense from diary."""
    date: datetime
    amount: float
    currency: str
    expense_type: str
    description: str
    source_file: str
    line_num: int
    original_line: str
    split_marker: str | None = None


# Default diary files to check
DEFAULT_DIARIES = [
    Path.home() / "solveig" / "diary-2026.md",
    Path.home() / "solveig" / "diary-202401.md",
    Path.home() / "solveig" / "diary-202312.md",
    Path.home() / "solveig" / "diary-202310.md",
    Path.home() / "solveig" / "diary-2023.md",
    Path.home() / "furusetalle9" / "diary-oslo-202512.md",
]

DEFAULT_ALIAS_FILE = Path.home() / ".config" / "reconcile-expenses" / "aliases.json"
DEFAULT_OUTPUT_FILE = Path.home() / "regnskap" / "non-reconciled.csv"
NON_RECONCILED_HEADER = ['date', 'currency', 'amount', 'description', 'bank', 'bank_currency', 'deducted_amount', 'merchant_category', 'source_file']


def load_aliases(filepath: Path | None) -> dict[str, set[str]]:
    """Load shop name aliases from JSON file."""
    aliases = {}

    if filepath is None:
        filepath = DEFAULT_ALIAS_FILE

    if not filepath.exists():
        return aliases

    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)

        for canonical, alias_list in data.items():
            canonical_lower = canonical.lower()
            aliases.setdefault(canonical_lower, set()).add(canonical_lower)
            for alias in alias_list:
                alias_lower = alias.lower()
                aliases.setdefault(alias_lower, set()).add(canonical_lower)

    except (OSError, json.JSONDecodeError) as e:
        click.echo(f"Warning: Could not load aliases from {filepath}: {e}", err=True)

    return aliases


def parse_n26_csv(filepath: Path, bank_currency: str = 'EUR') -> list[Expense]:
    """Parse N26 CSV export file."""
    expenses = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):
            try:
                deducted_amount = None
                for col in ['Amount (EUR)', 'Amount', 'Beloep', 'Summa']:
                    if col in row and row[col]:
                        try:
                            deducted_amount = float(row[col].replace(',', '.'))
                            break
                        except ValueError:
                            continue

                if deducted_amount is None or deducted_amount >= 0:
                    continue

                deducted_amount = abs(deducted_amount)

                date_str = None
                for col in ['Value Date', 'Booking Date', 'Date', 'Dato', 'Datum']:
                    if col in row and row[col]:
                        date_str = row[col]
                        break

                if not date_str:
                    continue
                date = datetime.strptime(date_str, '%Y-%m-%d')

                description = ''
                for col in ['Partner Name', 'Description', 'Beskrivelse', 'Payment Reference']:
                    if col in row and row[col]:
                        description = row[col]
                        break

                original_amount = row.get('Original Amount', '').strip()
                original_currency = row.get('Original Currency', '').strip()

                if original_amount and original_currency:
                    amount = abs(float(original_amount.replace(',', '.')))
                    currency = original_currency
                else:
                    amount = deducted_amount
                    currency = bank_currency

                expenses.append(Expense(
                    date=date,
                    amount=amount,
                    currency=currency,
                    description=description,
                    bank='N26',
                    bank_currency=bank_currency,
                    deducted_amount=deducted_amount,
                    source_file=str(filepath),
                    line_num=line_num
                ))
            except (ValueError, KeyError) as e:
                click.echo(f"Warning: Could not parse line {line_num}: {e}", err=True)
                continue

    return expenses


def parse_wise_csv(filepath: Path, default_currency: str = 'EUR') -> list[Expense]:
    """Parse Wise (TransferWise) CSV export file."""
    expenses = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):
            try:
                if row.get('Status') != 'COMPLETED':
                    continue
                if row.get('Direction') != 'OUT':
                    continue

                date_str = row.get('Finished on') or row.get('Created on')
                if not date_str:
                    continue
                date = datetime.strptime(date_str.split()[0], '%Y-%m-%d')

                source_amount_str = row.get('Source amount (after fees)', '').strip()
                source_currency = row.get('Source currency', '').strip() or default_currency
                deducted_amount = abs(float(source_amount_str.replace(',', '.'))) if source_amount_str else 0

                target_amount = row.get('Target amount (after fees)', '').strip()
                target_currency = row.get('Target currency', '').strip()

                if target_amount and target_currency:
                    amount = abs(float(target_amount.replace(',', '.')))
                    currency = target_currency
                else:
                    if source_amount_str:
                        amount = deducted_amount
                        currency = source_currency
                    else:
                        continue

                target_name = row.get('Target name', '').strip()
                note = row.get('Note', '').strip()
                description = target_name
                if note:
                    description = f"{target_name} ({note})"

                expenses.append(Expense(
                    date=date,
                    amount=amount,
                    currency=currency,
                    description=description,
                    bank='Wise',
                    bank_currency=source_currency,
                    deducted_amount=deducted_amount,
                    source_file=str(filepath),
                    line_num=line_num
                ))
            except (ValueError, KeyError) as e:
                click.echo(f"Warning: Could not parse line {line_num}: {e}", err=True)
                continue

    return expenses


def parse_banknorwegian_xlsx(filepath: Path) -> list[Expense]:
    """Parse Bank Norwegian XLSX export file."""
    import xml.etree.ElementTree as ET
    import zipfile

    expenses = []
    excel_epoch = datetime(1899, 12, 30)

    def excel_date_to_datetime(serial: float) -> datetime:
        return excel_epoch + timedelta(days=serial)

    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            shared_strings = []
            try:
                with zf.open('xl/sharedStrings.xml') as f:
                    tree = ET.parse(f)
                    ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    for si in tree.findall('.//x:si', ns):
                        texts = [t.text or '' for t in si.findall('.//x:t', ns)]
                        shared_strings.append(''.join(texts))
            except KeyError:
                pass

            with zf.open('xl/worksheets/sheet1.xml') as f:
                tree = ET.parse(f)
                ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

                rows = tree.findall('.//x:row', ns)

                for row in rows[1:]:
                    try:
                        cells = {c.attrib.get('r', '')[0]: c for c in row.findall('x:c', ns)}

                        def get_value(col: str, cells=cells) -> str:
                            cell = cells.get(col)
                            if cell is None:
                                return ''
                            v_elem = cell.find('x:v', ns)
                            if v_elem is None or v_elem.text is None:
                                return ''
                            if cell.attrib.get('t') == 's':
                                idx = int(v_elem.text)
                                return shared_strings[idx] if idx < len(shared_strings) else ''
                            return v_elem.text

                        date_val = get_value('A')
                        if not date_val:
                            continue
                        date = excel_date_to_datetime(float(date_val))

                        description = get_value('B').strip()
                        tx_type = get_value('C')
                        if tx_type in ['Innbetaling', 'Interest', 'Rente']:
                            continue

                        amount_str = get_value('D')
                        if not amount_str:
                            continue
                        original_amount = float(amount_str)
                        if original_amount >= 0:
                            continue
                        original_amount = abs(original_amount)

                        currency = get_value('F') or 'NOK'
                        deducted_str = get_value('G')
                        deducted_amount = abs(float(deducted_str)) if deducted_str else original_amount

                        area = get_value('H').strip()
                        if area and area not in description:
                            description = f"{description} ({area})"

                        category = get_value('I').strip()

                        if tx_type == 'Kontantuttak' or 'ATM' in category:
                            description = f"ATM: {description}"

                        expenses.append(Expense(
                            date=date,
                            amount=original_amount,
                            currency=currency,
                            description=description,
                            bank='BankNorwegian',
                            bank_currency='NOK',
                            deducted_amount=deducted_amount,
                            source_file=str(filepath),
                            line_num=int(row.attrib.get('r', 0)),
                            merchant_category=category
                        ))
                    except (ValueError, KeyError, IndexError):
                        continue
    except (OSError, zipfile.BadZipFile) as e:
        click.echo(f"Error reading {filepath}: {e}", err=True)

    return expenses


def parse_remember_json(filepath: Path) -> list[Expense]:
    """Parse Remember credit card JSON export."""
    expenses = []
    seen_ids = set()

    if '*' in str(filepath):
        files = sorted(filepath.parent.glob(filepath.name))
    else:
        files = [filepath]

    for json_file in files:
        try:
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)

            transactions = data.get('transactions', [])

            for tx in transactions:
                try:
                    tx_id = tx.get('id')
                    if tx_id in seen_ids:
                        continue
                    seen_ids.add(tx_id)

                    tx_amount = tx.get('transactionAmount', 0)
                    billing_amount = tx.get('billingAmount', 0)

                    if tx_amount >= 0:
                        continue

                    tx_amount = abs(tx_amount)
                    billing_amount = abs(billing_amount)

                    date_str = tx.get('transactionDate', '')
                    if not date_str:
                        continue
                    date = datetime.strptime(date_str[:10], '%Y-%m-%d')

                    currency = tx.get('transactionCurrency', 'NOK')
                    billing_currency = tx.get('billingCurrency', 'NOK')

                    description = tx.get('description', '').strip()
                    city = tx.get('city', '').strip()
                    if city and city.upper() not in description.upper():
                        description = f"{description} ({city})"

                    reason_code = tx.get('reasonCode') or ''
                    is_atm = (
                        reason_code == 'CASH' or
                        'kontantuttak' in description.lower() or
                        'gebyr kontantuttak' in description.lower()
                    )
                    if is_atm and not description.startswith('ATM:'):
                        description = f"ATM: {description}"

                    if reason_code == 'fee' or 'valutapaaslag' in description.lower():
                        continue

                    expenses.append(Expense(
                        date=date,
                        amount=tx_amount,
                        currency=currency,
                        description=description,
                        bank='Remember',
                        bank_currency=billing_currency,
                        deducted_amount=billing_amount,
                        source_file=str(json_file),
                        line_num=tx_id or 0,
                        merchant_category=''
                    ))
                except (ValueError, KeyError, TypeError):
                    continue

        except (OSError, json.JSONDecodeError) as e:
            click.echo(f"Error reading {json_file}: {e}", err=True)

    return expenses


def get_reconciled_markers(filepath: Path) -> set[tuple]:
    """Extract reconciliation markers from diary file."""
    markers = set()
    if not filepath.exists():
        return markers

    marker_pattern = re.compile(
        r'\(reconciled:\s*(\w+)\s*-\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\w+):(\d+\.?\d*)(?:/\d+|/\w+:\d+\.?\d*)?\)'
    )

    try:
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                for match in marker_pattern.finditer(line):
                    bank, date, currency, amount = match.groups()
                    markers.add((bank, date, currency, f"{float(amount):.2f}"))
    except OSError:
        pass

    return markers


def parse_diary_expenses(filepath: Path) -> list[DiaryExpense]:
    """Parse expense entries from a diary file."""
    expenses = []

    if not filepath.exists():
        return expenses

    expense_pattern = re.compile(
        r'^\* (' + '|'.join(SUPPORTED_CURRENCIES) + r')\s+(\d+(?:\.\d+)?)\s+-\s+([\w\s]+?)\s+-\s+(.+)$'
    )
    date_pattern = re.compile(r'^## \w+ (\d{4}-\d{2}-\d{2})')
    reconciled_pattern = re.compile(r'\(reconciled:')
    cash_pattern = re.compile(r'\(cash\)', re.IGNORECASE)
    split_marker_pattern = re.compile(
        r'\((reconciled:\s*)?(\w+)\s*-\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\w+):(\d+\.?\d*)/(\d+)\)'
    )

    current_date = None

    with open(filepath, encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            original_line = line.rstrip('\n')
            line = line.strip()

            date_match = date_pattern.match(line)
            if date_match:
                current_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                continue

            if current_date:
                expense_match = expense_pattern.match(line)
                if expense_match:
                    split_match = split_marker_pattern.search(line)
                    split_marker = None
                    if split_match:
                        is_reconciled = split_match.group(1) is not None
                        if is_reconciled:
                            continue
                        split_marker = f"{split_match.group(2)} - {split_match.group(3)} - {split_match.group(4)}:{split_match.group(5)}/{split_match.group(6)}"
                    elif reconciled_pattern.search(line):
                        continue

                    if cash_pattern.search(line):
                        continue

                    currency = expense_match.group(1)
                    try:
                        amount = float(expense_match.group(2))
                    except ValueError:
                        continue
                    expense_type = expense_match.group(3)
                    description = expense_match.group(4)

                    expenses.append(DiaryExpense(
                        date=current_date,
                        amount=amount,
                        currency=currency,
                        expense_type=expense_type,
                        description=description,
                        source_file=str(filepath),
                        line_num=line_num,
                        original_line=original_line,
                        split_marker=split_marker
                    ))

    return expenses


def normalize_text(text: str) -> set[str]:
    """Extract words from text for matching."""
    text = text.lower()
    words = re.findall(r'[a-z0-9aouaoeae]+', text)
    noise = {'the', 'a', 'an', 'and', 'or', 'of', 'in', 'at', 'to', 'for', 'on', 'from'}
    return {w for w in words if len(w) > 2 and w not in noise}


def expand_with_aliases(words: set[str], aliases: dict[str, set[str]]) -> set[str]:
    """Expand word set with aliases."""
    expanded = set(words)
    for word in words:
        if word in aliases:
            expanded.update(aliases[word])
    return expanded


def text_matches_with_aliases(text1: str, text2: str, aliases: dict[str, set[str]]) -> bool:
    """Check if two texts match, considering aliases."""
    words1 = normalize_text(text1)
    words2 = normalize_text(text2)

    expanded1 = expand_with_aliases(words1, aliases)
    expanded2 = expand_with_aliases(words2, aliases)

    if expanded1 & expanded2:
        return True

    text1_lower = text1.lower().strip()
    text2_lower = text2.lower().strip()

    if text1_lower in aliases:
        canonical1 = aliases[text1_lower]
        if expanded2 & canonical1:
            return True

    if text2_lower in aliases:
        canonical2 = aliases[text2_lower]
        if expanded1 & canonical2:
            return True

    return False


def update_diary_with_reconciliation(
    matched: list[tuple[Expense, DiaryExpense]],
    dry_run: bool = False
) -> dict[str, int]:
    """Update diary files with reconciliation markers."""
    by_file: dict[str, list[tuple[Expense, DiaryExpense]]] = {}
    for expense, diary_exp in matched:
        by_file.setdefault(diary_exp.source_file, []).append((expense, diary_exp))

    updated_counts = {}

    for filepath, matches in by_file.items():
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()

        matches.sort(key=lambda x: x[1].line_num, reverse=True)

        for expense, diary_exp in matches:
            line_idx = diary_exp.line_num - 1

            if line_idx >= len(lines):
                continue

            line = lines[line_idx].rstrip('\n')

            if diary_exp.split_marker:
                old_marker = f"({diary_exp.split_marker})"
                new_marker = f"(reconciled: {diary_exp.split_marker})"
                line = line.replace(old_marker, new_marker)
            else:
                if expense.currency != expense.bank_currency:
                    marker = f" (reconciled: {expense.bank} - {expense.date.strftime('%Y-%m-%d')} - {expense.currency}:{expense.amount:.2f}/{expense.bank_currency}:{expense.deducted_amount:.2f})"
                else:
                    marker = f" (reconciled: {expense.bank} - {expense.date.strftime('%Y-%m-%d')} - {expense.currency}:{expense.amount:.2f})"
                line = line + marker

            lines[line_idx] = line + '\n'

        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        updated_counts[filepath] = len(matches)

    return updated_counts


def find_split_match(
    expense: Expense,
    diary_expenses: list[DiaryExpense],
    date_tolerance: int = 2
) -> list[DiaryExpense] | None:
    """Find diary expenses with split markers matching this bank expense."""
    by_marker: dict[str, list[DiaryExpense]] = {}
    for diary_exp in diary_expenses:
        if diary_exp.split_marker:
            by_marker.setdefault(diary_exp.split_marker, []).append(diary_exp)

    marker_pattern = re.compile(r'^(\w+)\s*-\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\w+):(\d+\.?\d*)/(\d+)$')

    for marker, diary_exps in by_marker.items():
        match = marker_pattern.match(marker)
        if not match:
            continue

        bank, date_str, currency, amount_str, count_str = match.groups()
        marker_date = datetime.strptime(date_str, '%Y-%m-%d')
        marker_amount = float(amount_str)
        expected_count = int(count_str)

        if expense.bank != bank:
            continue
        if expense.currency != currency:
            continue

        date_diff = abs((expense.date - marker_date).days)
        if date_diff > date_tolerance:
            continue

        if abs(expense.amount - marker_amount) > 0.10:
            continue

        if len(diary_exps) != expected_count:
            continue

        return diary_exps

    return None


def find_match(
    expense: Expense,
    diary_expenses: list[DiaryExpense],
    amount_tolerance: float = 2.0,
    date_tolerance: int = 2,
    aliases: dict[str, set[str]] | None = None
) -> DiaryExpense | None:
    """Find a matching diary expense (single entry, not split)."""
    if aliases is None:
        aliases = {}

    for diary_exp in diary_expenses:
        if diary_exp.split_marker:
            continue

        date_diff = abs((expense.date - diary_exp.date).days)
        if date_diff > date_tolerance:
            continue

        if expense.currency != diary_exp.currency:
            continue

        amount_diff = abs(expense.amount - diary_exp.amount)

        if amount_diff > amount_tolerance:
            continue

        if amount_diff < 0.10:
            return diary_exp

        if text_matches_with_aliases(expense.description, diary_exp.description, aliases):
            return diary_exp

    return None


def load_existing_non_reconciled(filepath: Path) -> tuple[set[tuple], list[dict]]:
    """Load existing entries from non-reconciled.csv for deduplication."""
    existing = set()
    commented_rows = []

    if not filepath.exists():
        return existing, commented_rows

    try:
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row.get('date', '')
                desc = row.get('description', '')
                if desc.startswith('ATM: '):
                    desc = desc[5:]
                key = (
                    date.lstrip('#'),
                    row.get('currency', ''),
                    row.get('amount', ''),
                    desc,
                    row.get('bank', '')
                )
                existing.add(key)

                if date.startswith('#'):
                    commented_rows.append(row)
    except (OSError, csv.Error) as e:
        click.echo(f"Warning: Could not read {filepath}: {e}", err=True)

    return existing, commented_rows


def expense_to_row(expense: Expense) -> dict:
    """Convert Expense to CSV row dict."""
    return {
        'date': expense.date.strftime('%Y-%m-%d'),
        'currency': expense.currency,
        'amount': f'{expense.amount:.2f}',
        'description': expense.description,
        'bank': expense.bank,
        'bank_currency': expense.bank_currency,
        'deducted_amount': f'{expense.deducted_amount:.2f}',
        'merchant_category': expense.merchant_category,
        'source_file': expense.source_file,
    }


def expense_key(expense: Expense) -> tuple:
    """Get deduplication key for an expense."""
    desc = expense.description
    if desc.startswith('ATM: '):
        desc = desc[5:]
    return (
        expense.date.strftime('%Y-%m-%d'),
        expense.currency,
        f'{expense.amount:.2f}',
        desc,
        expense.bank
    )


def row_to_expense(row: dict) -> Expense:
    """Convert CSV row dict back to Expense for matching."""
    return Expense(
        date=datetime.strptime(row['date'], '%Y-%m-%d'),
        amount=float(row['amount']),
        currency=row['currency'],
        description=row['description'],
        bank=row['bank'],
        bank_currency=row['bank_currency'],
        deducted_amount=float(row['deducted_amount']),
        source_file=row['source_file'],
        line_num=0,
        merchant_category=row.get('merchant_category', '')
    )


def update_non_reconciled(
    new_unmatched: list[Expense],
    output_file: Path,
    diary_expenses: list[DiaryExpense],
    amount_tolerance: float,
    date_tolerance: int,
    aliases: dict,
    dry_run: bool = False
) -> tuple[int, int, int]:
    """Update non-reconciled CSV file."""
    existing_keys, commented_rows = load_existing_non_reconciled(output_file)

    active_rows = []
    if output_file.exists() and output_file.stat().st_size > 0:
        with open(output_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row.get('date', '')
                if not date.startswith('#'):
                    active_rows.append(row)

    still_unmatched = []
    removed = 0
    for row in active_rows:
        try:
            expense = row_to_expense(row)
            match = find_match(expense, diary_expenses, amount_tolerance, date_tolerance, aliases)
            if match:
                removed += 1
            else:
                still_unmatched.append(row)
        except (ValueError, KeyError):
            still_unmatched.append(row)

    existing_keys = {
        (r['date'], r['currency'], r['amount'],
         r['description'][5:] if r['description'].startswith('ATM: ') else r['description'],
         r['bank'])
        for r in still_unmatched
    }

    new_rows = []
    duplicates = 0
    for expense in new_unmatched:
        key = expense_key(expense)
        if key in existing_keys:
            duplicates += 1
        else:
            new_rows.append(expense_to_row(expense))
            existing_keys.add(key)

    if dry_run:
        return len(new_rows), removed, duplicates

    commented_keys = {
        (r['date'].lstrip('#'), r['currency'], r['amount'],
         r['description'][5:] if r['description'].startswith('ATM: ') else r['description'],
         r['bank'])
        for r in commented_rows
    }

    all_active = [
        r for r in (still_unmatched + new_rows)
        if (r['date'], r['currency'], r['amount'],
            r['description'][5:] if r['description'].startswith('ATM: ') else r['description'],
            r['bank']) not in commented_keys
    ]
    all_active.sort(key=lambda r: r.get('date', ''))
    commented_rows.sort(key=lambda r: r.get('date', '').lstrip('#'))

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=NON_RECONCILED_HEADER)
        writer.writeheader()
        writer.writerows(all_active)
        writer.writerows(commented_rows)

    return len(new_rows), removed, duplicates


@click.command()
@click.argument('input_file', type=click.Path(exists=False, path_type=Path))
@click.option('--format', '-f', 'fmt', type=click.Choice(['n26', 'wise', 'banknorwegian', 'remember']),
              default='n26', help='Input format')
@click.option('--diary', '-d', type=click.Path(exists=True, path_type=Path), multiple=True,
              help='Diary file(s) to check')
@click.option('--output', '-o', type=click.Path(path_type=Path), default=DEFAULT_OUTPUT_FILE,
              help='Output file for unmatched expenses')
@click.option('--currency', default='EUR', help='Default currency when not specified')
@click.option('--tolerance', '-t', type=float, default=2.0, help='Amount tolerance')
@click.option('--date-tolerance', type=int, default=2, help='Date tolerance in days')
@click.option('--aliases', '-a', type=click.Path(exists=True, path_type=Path),
              help='Alias file for shop names')
@click.option('--dry-run', '-n', is_flag=True, help='Show matches without modifying files')
@click.option('--no-commit', is_flag=True, help="Don't commit changes to git")
@click.option('--verbose', '-v', is_flag=True, help='Show detailed matching info')
def reconcile(input_file, fmt, diary, output, currency, tolerance, date_tolerance, aliases, dry_run, no_commit, verbose):
    """Reconcile bank expenses with diary entries."""
    alias_dict = load_aliases(aliases)
    if alias_dict and verbose:
        click.echo(f"Loaded {len(alias_dict)} alias mappings")

    if fmt != 'remember' and not input_file.exists():
        click.echo(f"Error: File not found: {input_file}", err=True)
        sys.exit(1)

    diary_files = list(diary) if diary else DEFAULT_DIARIES

    click.echo(f"Reading {input_file}...")
    if fmt == 'n26':
        bank_expenses = parse_n26_csv(input_file, currency)
    elif fmt == 'wise':
        bank_expenses = parse_wise_csv(input_file, currency)
    elif fmt == 'banknorwegian':
        bank_expenses = parse_banknorwegian_xlsx(input_file)
    elif fmt == 'remember':
        bank_expenses = parse_remember_json(input_file)
    else:
        click.echo(f"Unknown format: {fmt}", err=True)
        sys.exit(1)

    click.echo(f"Found {len(bank_expenses)} expenses")

    all_diary_expenses = []
    for diary_file in diary_files:
        if diary_file.exists():
            diary_expenses_list = parse_diary_expenses(diary_file)
            all_diary_expenses.extend(diary_expenses_list)
            if verbose and diary_expenses_list:
                click.echo(f"Found {len(diary_expenses_list)} expenses in {diary_file}")

    click.echo(f"Found {len(all_diary_expenses)} total expenses in diaries")

    all_reconciled_markers = set()
    for diary_file in diary_files:
        all_reconciled_markers.update(get_reconciled_markers(diary_file))
    if verbose and all_reconciled_markers:
        click.echo(f"Found {len(all_reconciled_markers)} existing reconciliation markers")

    matched = []
    unmatched = []
    already_reconciled = 0

    for expense in bank_expenses:
        marker_key = (
            expense.bank,
            expense.date.strftime('%Y-%m-%d'),
            expense.currency,
            f"{expense.amount:.2f}"
        )
        if marker_key in all_reconciled_markers:
            already_reconciled += 1
            continue

        split_matches = find_split_match(expense, all_diary_expenses, date_tolerance=date_tolerance)
        if split_matches:
            for diary_exp in split_matches:
                matched.append((expense, diary_exp))
            continue

        match = find_match(expense, all_diary_expenses, amount_tolerance=tolerance,
                           date_tolerance=date_tolerance, aliases=alias_dict)
        if match:
            matched.append((expense, match))
        else:
            unmatched.append(expense)

    if already_reconciled and verbose:
        click.echo(f"Skipped {already_reconciled} already-reconciled entries")

    click.echo("\n=== Results ===")
    if already_reconciled:
        click.echo(f"Already reconciled: {already_reconciled}")
    click.echo(f"Matched: {len(matched)}")
    click.echo(f"Unmatched: {len(unmatched)}")

    if verbose or dry_run:
        if matched:
            click.echo("\n--- Matched expenses ---")
            for expense, diary_exp in matched:
                click.echo(f"  {expense.date.strftime('%Y-%m-%d')} {expense.currency} {expense.amount:.2f} "
                           f"'{expense.description}'")
                click.echo(f"    -> {diary_exp.currency} {diary_exp.amount:.2f} "
                           f"- {diary_exp.expense_type} - {diary_exp.description}")

        if unmatched:
            click.echo("\n--- Unmatched expenses (need manual review) ---")
            for expense in unmatched:
                click.echo(f"  {expense.date.strftime('%Y-%m-%d')} {expense.currency} {expense.amount:.2f} "
                           f"'{expense.description}'")

    diary_updates = {}
    if matched:
        diary_updates = update_diary_with_reconciliation(matched, dry_run=dry_run)
        if not dry_run:
            for filepath, count in diary_updates.items():
                click.echo(f"Marked {count} entries as reconciled in {filepath}")
        elif verbose:
            click.echo(f"\nWould mark {len(matched)} diary entries as reconciled")

    added, removed, duplicates = update_non_reconciled(
        unmatched, output, all_diary_expenses,
        tolerance, date_tolerance, alias_dict, dry_run=dry_run
    )

    if dry_run:
        if added or removed or duplicates:
            click.echo(f"\nNon-reconciled file ({output}):")
            if added:
                click.echo(f"  Would add {added} new entries")
            if removed:
                click.echo(f"  Would remove {removed} entries (now matched)")
            if duplicates:
                click.echo(f"  Would skip {duplicates} duplicates")
        click.echo("\n(Dry run - no files modified)")
    else:
        if added or removed:
            click.echo(f"\nUpdated {output}:")
            if added:
                click.echo(f"  Added {added} new entries")
            if removed:
                click.echo(f"  Removed {removed} entries (now matched)")
            if duplicates:
                click.echo(f"  Skipped {duplicates} duplicates")

    if not no_commit and not dry_run:
        modified_files = [Path(f) for f in diary_updates.keys()] + [output]
        if modified_files:
            commit_msg = f"reconcile-expenses: {input_file.name}"
            if matched:
                commit_msg += f" ({len(matched)} matched"
                if added:
                    commit_msg += f", {added} new unmatched"
                if removed:
                    commit_msg += f", {removed} cleaned up"
                commit_msg += ")"
            git_commit_multiple_repos(modified_files, commit_msg)


def main():
    """Entry point for diary-reconcile command."""
    reconcile()


if __name__ == "__main__":
    main()
