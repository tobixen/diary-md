"""Exchange rate lookup for diary-md."""

# Exchange rates to EUR by time period
# Format: { 'CUR': [('YYYY-MM-DD', rate), ...] }
# Rates are looked up by finding the most recent date <= expense date
# Last entry with None date is the fallback/current rate
EXCHANGE_RATES_TO_EUR: dict[str, list[tuple[str, float | None]]] = {
    'BGN': [  # Bulgarian Lev - pegged to EUR
        ('2000-01-01', 0.5113),
    ],
    'NOK': [  # Norwegian Krone - relatively stable
        ('2023-01-01', 0.092),
        ('2024-01-01', 0.087),
        ('2025-01-01', 0.082),
        ('2026-01-01', 0.085),
    ],
    'TRY': [  # Turkish Lira - significant depreciation
        ('2023-01-01', 0.050),  # ~20 TRY/EUR
        ('2023-07-01', 0.037),  # ~27 TRY/EUR
        ('2024-01-01', 0.030),  # ~33 TRY/EUR
        ('2024-07-01', 0.027),  # ~37 TRY/EUR
        ('2025-01-01', 0.026),  # ~38 TRY/EUR
        ('2025-07-01', 0.025),  # ~40 TRY/EUR
        ('2026-01-01', 0.024),  # ~42 TRY/EUR
    ],
    'USD': [
        ('2023-01-01', 0.93),
        ('2024-01-01', 0.91),
        ('2025-01-01', 0.96),
        ('2026-01-01', 0.94),
    ],
    'GBP': [
        ('2023-01-01', 1.13),
        ('2024-01-01', 1.15),
        ('2025-01-01', 1.19),
        ('2026-01-01', 1.16),
    ],
    'BAM': [  # Bosnia-Herzegovina Mark - pegged to EUR
        ('2000-01-01', 0.5113),
    ],
    'RON': [  # Romanian Leu
        ('2023-01-01', 0.203),
        ('2024-01-01', 0.201),
        ('2025-01-01', 0.200),
        ('2026-01-01', 0.200),
    ],
    'HRK': [  # Croatian Kuna (replaced by EUR 2023-01-01)
        ('2020-01-01', 0.132),
        ('2023-01-01', None),  # No longer valid
    ],
    'RSD': [  # Serbian Dinar
        ('2023-01-01', 0.0085),
        ('2024-01-01', 0.0085),
    ],
    'ALL': [  # Albanian Lek
        ('2023-01-01', 0.0093),
        ('2024-01-01', 0.0095),
    ],
    'MKD': [  # Macedonian Denar
        ('2023-01-01', 0.0162),
        ('2024-01-01', 0.0162),
    ],
    'SEK': [  # Swedish Krona
        ('2023-01-01', 0.089),
        ('2024-01-01', 0.087),
        ('2025-01-01', 0.086),
    ],
    'DKK': [  # Danish Krone - pegged to EUR
        ('2000-01-01', 0.134),
    ],
    'PLN': [  # Polish Zloty
        ('2023-01-01', 0.213),
        ('2024-01-01', 0.230),
        ('2025-01-01', 0.233),
    ],
    'CHF': [  # Swiss Franc
        ('2023-01-01', 1.00),
        ('2024-01-01', 1.05),
        ('2025-01-01', 1.06),
    ],
}


def get_exchange_rate(currency: str, date_str: str) -> float | None:
    """Get exchange rate to EUR for a currency on a given date.

    Args:
        currency: ISO 4217 currency code (e.g., 'USD', 'BGN')
        date_str: Date in YYYY-MM-DD format

    Returns:
        Exchange rate to EUR, or None if currency not found or discontinued.
    """
    if currency == 'EUR':
        return 1.0

    if currency not in EXCHANGE_RATES_TO_EUR:
        return None

    rates = EXCHANGE_RATES_TO_EUR[currency]
    # Find the most recent rate <= date
    applicable_rate = None
    for rate_date, rate in rates:
        if rate_date <= date_str:
            applicable_rate = rate
        else:
            break

    return applicable_rate


def convert_to_eur(amount: float, currency: str, date_str: str) -> float | None:
    """Convert an amount to EUR.

    Args:
        amount: The amount in the source currency
        currency: ISO 4217 currency code
        date_str: Date in YYYY-MM-DD format

    Returns:
        Amount in EUR, or None if conversion is not possible.
    """
    rate = get_exchange_rate(currency, date_str)
    if rate is None:
        return None
    return amount * rate
