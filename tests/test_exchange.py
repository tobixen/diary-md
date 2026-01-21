"""Tests for diary_md.exchange module."""

import pytest

from diary_md.exchange import convert_to_eur, get_exchange_rate


class TestGetExchangeRate:
    """Tests for get_exchange_rate function."""

    def test_eur_rate_is_one(self):
        """EUR to EUR is always 1.0."""
        assert get_exchange_rate('EUR', '2026-01-20') == 1.0
        assert get_exchange_rate('EUR', '2020-01-01') == 1.0

    def test_bgn_pegged_rate(self):
        """BGN is pegged to EUR."""
        assert get_exchange_rate('BGN', '2026-01-20') == 0.5113
        assert get_exchange_rate('BGN', '2010-01-01') == 0.5113

    def test_nok_historical_rates(self):
        """NOK rates change over time."""
        # 2023 rate
        assert get_exchange_rate('NOK', '2023-06-15') == 0.092
        # 2024 rate
        assert get_exchange_rate('NOK', '2024-06-15') == 0.087
        # 2025 rate
        assert get_exchange_rate('NOK', '2025-06-15') == 0.082

    def test_try_depreciation(self):
        """TRY rates show depreciation."""
        rate_2023 = get_exchange_rate('TRY', '2023-03-01')
        rate_2025 = get_exchange_rate('TRY', '2025-03-01')
        # TRY has depreciated - lower rate means more TRY per EUR
        assert rate_2025 < rate_2023

    def test_hrk_discontinued(self):
        """HRK returns None after 2023 (replaced by EUR)."""
        # Before discontinuation
        assert get_exchange_rate('HRK', '2022-12-15') == 0.132
        # After discontinuation
        assert get_exchange_rate('HRK', '2023-06-15') is None

    def test_unknown_currency(self):
        """Unknown currency returns None."""
        assert get_exchange_rate('XYZ', '2026-01-20') is None
        assert get_exchange_rate('JPY', '2026-01-20') is None

    def test_date_before_any_rate(self):
        """Date before any rate returns None."""
        # NOK has rates starting from 2023-01-01
        assert get_exchange_rate('NOK', '1990-01-01') is None


class TestConvertToEur:
    """Tests for convert_to_eur function."""

    def test_convert_eur(self):
        """Converting EUR is a no-op."""
        assert convert_to_eur(100.0, 'EUR', '2026-01-20') == 100.0

    def test_convert_bgn(self):
        """Convert BGN to EUR."""
        result = convert_to_eur(100.0, 'BGN', '2026-01-20')
        assert result == pytest.approx(51.13, rel=0.01)

    def test_convert_nok(self):
        """Convert NOK to EUR."""
        result = convert_to_eur(1000.0, 'NOK', '2026-06-15')
        # 2026 rate is 0.085
        assert result == pytest.approx(85.0, rel=0.01)

    def test_convert_unknown_currency(self):
        """Unknown currency returns None."""
        assert convert_to_eur(100.0, 'XYZ', '2026-01-20') is None

    def test_convert_discontinued_currency(self):
        """Discontinued currency returns None."""
        assert convert_to_eur(100.0, 'HRK', '2023-06-15') is None
