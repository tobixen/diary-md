"""diary-md: Tools for managing markdown-based diary entries."""

from diary_md.exceptions import DiaryParseError
from diary_md.models import DateHeader, ExpenseLine
from diary_md.exchange import get_exchange_rate, EXCHANGE_RATES_TO_EUR
from diary_md.parser import (
    markdown_to_dict,
    find_or_create_date_section,
    find_section_in_date,
    find_section_end,
)

__version__ = "0.1.0"

__all__ = [
    "DiaryParseError",
    "DateHeader",
    "ExpenseLine",
    "get_exchange_rate",
    "EXCHANGE_RATES_TO_EUR",
    "markdown_to_dict",
    "find_or_create_date_section",
    "find_section_in_date",
    "find_section_end",
]
