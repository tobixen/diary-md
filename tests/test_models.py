"""Tests for diary_md.models module."""

from datetime import datetime

import pytest

from diary_md.models import DateHeader, ExpenseLine


class TestDateHeader:
    """Tests for DateHeader class."""

    def test_parse_simple_date(self):
        """Parse a simple date header."""
        header = DateHeader.parse("## Monday 2026-01-20")
        assert header is not None
        assert header.date == datetime(2026, 1, 20)
        assert header.weekday == "Monday"
        assert header.itinerary is None

    def test_parse_date_with_itinerary(self):
        """Parse date header with itinerary."""
        header = DateHeader.parse("## Monday 2026-01-20 - Oslo - Bergen")
        assert header is not None
        assert header.date == datetime(2026, 1, 20)
        assert header.weekday == "Monday"
        assert header.itinerary == "- Oslo - Bergen"

    def test_parse_norwegian_weekday(self):
        """Parse Norwegian weekday names."""
        header = DateHeader.parse("## Mandag 2026-01-20")
        assert header is not None
        assert header.weekday == "Mandag"

    def test_parse_invalid_weekday(self):
        """Invalid weekday returns None."""
        header = DateHeader.parse("## Funday 2026-01-20")
        assert header is None

    def test_parse_invalid_date(self):
        """Invalid date returns None."""
        header = DateHeader.parse("## Monday 2026-13-40")
        assert header is None

    def test_parse_non_header(self):
        """Non-header line returns None."""
        assert DateHeader.parse("Some random text") is None
        assert DateHeader.parse("# Top level header") is None
        assert DateHeader.parse("### Subsection") is None

    def test_format_simple(self):
        """Format a simple date header."""
        header = DateHeader(
            date=datetime(2026, 1, 20),
            weekday="Monday"
        )
        assert header.format() == "## Monday 2026-01-20"

    def test_format_with_itinerary(self):
        """Format date header with itinerary."""
        header = DateHeader(
            date=datetime(2026, 1, 20),
            weekday="Monday",
            itinerary="- Oslo - Bergen"
        )
        assert header.format() == "## Monday 2026-01-20 - Oslo - Bergen"

    def test_format_minimal(self):
        """Format without itinerary."""
        header = DateHeader(
            date=datetime(2026, 1, 20),
            weekday="Monday",
            itinerary="- Oslo - Bergen"
        )
        assert header.format_minimal() == "## Monday 2026-01-20"


class TestExpenseLine:
    """Tests for ExpenseLine class."""

    def test_parse_simple_expense(self):
        """Parse a simple expense line."""
        expense = ExpenseLine.parse("* EUR 15.72 - groceries - Lidl")
        assert expense is not None
        assert expense.currency == "EUR"
        assert expense.amount == 15.72
        assert expense.expense_type == "groceries"
        assert expense.description == "Lidl"
        assert expense.reconciliation_marker is None
        assert not expense.is_reconciled

    def test_parse_expense_with_description(self):
        """Parse expense with detailed description."""
        expense = ExpenseLine.parse("* EUR 15.72 - groceries - Lidl (milk, bread)")
        assert expense is not None
        assert expense.description == "Lidl (milk, bread)"

    def test_parse_expense_with_reconciliation(self):
        """Parse expense with reconciliation marker."""
        expense = ExpenseLine.parse(
            "* EUR 15.72 - groceries - Lidl (reconciled: N26 - 2026-01-20 - EUR:15.72)"
        )
        assert expense is not None
        assert expense.currency == "EUR"
        assert expense.amount == 15.72
        assert expense.description == "Lidl"
        assert expense.reconciliation_marker == "(reconciled: N26 - 2026-01-20 - EUR:15.72)"
        assert expense.is_reconciled

    def test_parse_different_currencies(self):
        """Parse expenses in different currencies."""
        currencies = ['EUR', 'BGN', 'NOK', 'USD', 'GBP', 'SEK', 'TRY', 'PLN']
        for currency in currencies:
            expense = ExpenseLine.parse(f"* {currency} 10.00 - test - description")
            assert expense is not None
            assert expense.currency == currency

    def test_parse_multiword_expense_type(self):
        """Parse expense with multi-word type."""
        expense = ExpenseLine.parse("* EUR 50.00 - harbour due - Marina Oslo")
        assert expense is not None
        assert expense.expense_type == "harbour due"
        assert expense.description == "Marina Oslo"

    def test_parse_negative_amount(self):
        """Parse expense with negative amount (refund)."""
        expense = ExpenseLine.parse("* EUR -10.00 - refund - Store return")
        assert expense is not None
        assert expense.amount == -10.00

    def test_parse_integer_amount(self):
        """Parse expense with integer amount."""
        expense = ExpenseLine.parse("* EUR 100 - hotel - Grand Hotel")
        assert expense is not None
        assert expense.amount == 100.0

    def test_parse_invalid_line(self):
        """Invalid lines return None."""
        assert ExpenseLine.parse("Some random text") is None
        assert ExpenseLine.parse("* Not an expense") is None
        assert ExpenseLine.parse("* XXX 10.00 - invalid currency - desc") is None

    def test_format_simple(self):
        """Format a simple expense line."""
        expense = ExpenseLine(
            currency="EUR",
            amount=15.72,
            expense_type="groceries",
            description="Lidl"
        )
        assert expense.format() == "* EUR 15.72 - groceries - Lidl"

    def test_format_with_reconciliation(self):
        """Format expense with reconciliation marker."""
        expense = ExpenseLine(
            currency="EUR",
            amount=15.72,
            expense_type="groceries",
            description="Lidl",
            reconciliation_marker="(reconciled: N26 - 2026-01-20 - EUR:15.72)"
        )
        formatted = expense.format()
        assert "(reconciled: N26 - 2026-01-20 - EUR:15.72)" in formatted

    def test_format_without_reconciliation(self):
        """Format expense excluding reconciliation marker."""
        expense = ExpenseLine(
            currency="EUR",
            amount=15.72,
            expense_type="groceries",
            description="Lidl",
            reconciliation_marker="(reconciled: N26 - 2026-01-20 - EUR:15.72)"
        )
        formatted = expense.format(include_reconciliation=False)
        assert "(reconciled:" not in formatted
