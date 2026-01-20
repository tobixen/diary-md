"""Data models for diary-md."""

import re
from dataclasses import dataclass
from datetime import datetime


DATE_FORMAT = "%Y-%m-%d"

# Valid weekday names (English and Norwegian)
WEEKDAYS_EN = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
WEEKDAYS_NO = ('Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag')
VALID_WEEKDAYS = WEEKDAYS_EN + WEEKDAYS_NO

# Supported currencies
SUPPORTED_CURRENCIES = (
    'EUR', 'BGN', 'NOK', 'USD', 'GBP', 'SEK', 'DKK', 'PLN', 'TRY', 'CHF',
    'HRK', 'RON', 'RSD', 'ALL', 'MKD', 'BAM',
)


@dataclass
class DateHeader:
    """Represents a date header in the diary (## Monday 2026-01-20 - Location)."""

    date: datetime
    weekday: str
    itinerary: str | None = None

    @classmethod
    def parse(cls, line: str) -> 'DateHeader | None':
        """Parse a date header line.

        Returns DateHeader if line matches, None otherwise.

        Example lines:
            ## Monday 2026-01-20
            ## Monday 2026-01-20 - Oslo
            ## Monday 2026-01-20 - Oslo - Bergen
        """
        pattern = r'^##\s+(\w+)\s+(\d{4}-\d{2}-\d{2})(.*)$'
        match = re.match(pattern, line.strip())
        if not match:
            return None

        weekday, date_str, rest = match.groups()

        # Validate weekday
        if weekday not in VALID_WEEKDAYS:
            return None

        try:
            date = datetime.strptime(date_str, DATE_FORMAT)
        except ValueError:
            return None

        # Parse itinerary (everything after the date)
        itinerary = rest.strip() if rest.strip() else None

        return cls(date=date, weekday=weekday, itinerary=itinerary)

    def format(self, include_itinerary: bool = True) -> str:
        """Format as markdown header line."""
        date_str = self.date.strftime(DATE_FORMAT)
        line = f"## {self.weekday} {date_str}"
        if include_itinerary and self.itinerary:
            line += f" {self.itinerary}"
        return line

    def format_minimal(self) -> str:
        """Format without itinerary."""
        return self.format(include_itinerary=False)


@dataclass
class ExpenseLine:
    """Represents an expense line in the diary.

    Example: * EUR 15.72 - groceries - Lidl (milk, bread)
    """

    currency: str
    amount: float
    expense_type: str
    description: str
    reconciliation_marker: str | None = None

    # Pattern for parsing expense lines
    # Note: expense type can be multi-word like "harbour due", "taxi fare"
    _PATTERN = re.compile(
        r'^\*\s+(' + '|'.join(SUPPORTED_CURRENCIES) + r')\s+'
        r'(-?\d+(?:\.\d+)?)\s+-\s+'
        r'([\w\s]+?)\s+-\s+'
        r'(.+)$'
    )

    # Pattern for reconciliation markers
    _RECONCILED_PATTERN = re.compile(r'\(reconciled:[^)]+\)')

    @classmethod
    def parse(cls, line: str) -> 'ExpenseLine | None':
        """Parse an expense line.

        Returns ExpenseLine if line matches, None otherwise.
        """
        line = line.strip()
        match = cls._PATTERN.match(line)
        if not match:
            return None

        currency, amount_str, expense_type, description = match.groups()

        try:
            amount = float(amount_str)
        except ValueError:
            return None

        # Extract reconciliation marker if present
        reconciliation_marker = None
        marker_match = cls._RECONCILED_PATTERN.search(description)
        if marker_match:
            reconciliation_marker = marker_match.group(0)
            # Remove marker from description for clean parsing
            description = description[:marker_match.start()].strip()

        return cls(
            currency=currency,
            amount=amount,
            expense_type=expense_type.strip(),
            description=description.strip(),
            reconciliation_marker=reconciliation_marker,
        )

    def format(self, include_reconciliation: bool = True) -> str:
        """Format as markdown list item."""
        line = f"* {self.currency} {self.amount:.2f} - {self.expense_type} - {self.description}"
        if include_reconciliation and self.reconciliation_marker:
            line += f" {self.reconciliation_marker}"
        return line

    @property
    def is_reconciled(self) -> bool:
        """Check if this expense has been reconciled."""
        return self.reconciliation_marker is not None
