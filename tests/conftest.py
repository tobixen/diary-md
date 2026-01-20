"""Pytest fixtures for diary-md tests."""

import pytest
from io import StringIO
from pathlib import Path


@pytest.fixture
def sample_diary_content():
    """Sample diary content for testing."""
    return """\
# Summer Trip 2026

## Monday 2026-01-20 - Oslo - Bergen

Some notes about the day.

### Expenses

* EUR 15.72 - groceries - Lidl (milk, bread)
* NOK 250.00 - fuel - Shell
* EUR 7.50 - lunch - Kafe Oslo

### Maintenance

Fixed the rudder bearing.

## Tuesday 2026-01-21 - Bergen

Another day in Bergen.

### Expenses

* EUR 25.00 - dinner - Restaurant
* BGN 50.00 - groceries - Billa (reconciled: N26 - 2026-01-21 - BGN:50.00)

# Winter Trip 2026

## Wednesday 2026-01-22 - Trondheim

### Expenses

* EUR 100.00 - hotel - Grand Hotel
"""


@pytest.fixture
def sample_diary_file(tmp_path, sample_diary_content):
    """Create a temporary diary file."""
    diary_file = tmp_path / "diary-2026.md"
    diary_file.write_text(sample_diary_content)
    return diary_file


@pytest.fixture
def sample_diary_io(sample_diary_content):
    """Create a StringIO for diary content."""
    return StringIO(sample_diary_content)


@pytest.fixture
def sample_n26_csv(tmp_path):
    """Create a sample N26 CSV file."""
    csv_content = """\
Booking Date,Value Date,Partner Name,Partner Iban,Type,Payment Reference,Account Name,Amount (EUR),Original Amount,Original Currency,Exchange Rate
2026-01-20,2026-01-20,Lidl,,,Card Payment,My Account,-15.72,,,
2026-01-20,2026-01-20,Shell,,,Card Payment,My Account,-23.50,-250.00,NOK,0.094
2026-01-21,2026-01-21,Restaurant,,,Card Payment,My Account,-25.00,,,
2026-01-21,2026-01-21,Billa,,,Card Payment,My Account,-25.57,-50.00,BGN,0.5113
"""
    csv_file = tmp_path / "n26.csv"
    csv_file.write_text(csv_content)
    return csv_file
