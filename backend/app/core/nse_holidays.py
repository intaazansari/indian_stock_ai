"""
NSE Capital Market Segment trading holiday calendar.

Source: NSE circulars ("Trading Holidays for the Calendar Year <YYYY>"),
published every December for the following year, e.g.:
  https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf (2026 list)

NSE is closed Saturdays and Sundays plus the fixed list of holidays below
(national holidays + religious festivals whose dates shift year to year).
Special one-off "Muhurat Trading" sessions (a short window on Diwali,
which sometimes falls on a weekend) are NOT trading days for our purposes —
they're an auspicious ceremonial session, not a normal full trading day.

Maintenance: add next year's list here every December once NSE publishes its
circular. If the current year is missing from NSE_HOLIDAYS, `is_nse_holiday`
safely returns False (weekday-only check still applies) rather than silently
skipping an unknown number of valid trading days.
"""
from __future__ import annotations

from datetime import date

# Verified against the official NSE Capital Market Segment circular.
NSE_HOLIDAYS: dict[int, dict[date, str]] = {
    2026: {
        date(2026, 1, 26): "Republic Day",
        date(2026, 3, 3): "Holi",
        date(2026, 3, 26): "Shri Ram Navami",
        date(2026, 3, 31): "Shri Mahavir Jayanti",
        date(2026, 4, 3): "Good Friday",
        date(2026, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
        date(2026, 5, 1): "Maharashtra Day",
        date(2026, 5, 28): "Bakri Id",
        date(2026, 6, 26): "Muharram",
        date(2026, 9, 14): "Ganesh Chaturthi",
        date(2026, 10, 2): "Mahatma Gandhi Jayanti",
        date(2026, 10, 20): "Dussehra",
        date(2026, 11, 10): "Diwali-Balipratipada",
        date(2026, 11, 24): "Prakash Gurpurb Sri Guru Nanak Dev",
        date(2026, 12, 25): "Christmas",
    },
}


def is_nse_holiday(d: date) -> bool:
    """True if `d` is a declared NSE trading holiday (excludes weekends)."""
    return d in NSE_HOLIDAYS.get(d.year, {})


def is_trading_day(d: date) -> bool:
    """
    True if NSE is open for regular trading on `d`.

    False for Saturdays, Sundays, and declared NSE holidays.
    """
    if d.weekday() >= 5:   # Saturday=5, Sunday=6
        return False
    return not is_nse_holiday(d)


def holiday_name(d: date) -> str | None:
    """Return the holiday name for `d`, or None if it's not a holiday."""
    return NSE_HOLIDAYS.get(d.year, {}).get(d)
