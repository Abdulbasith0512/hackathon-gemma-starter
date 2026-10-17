"""Deterministic date windows. Relative phrases are resolved here, from the as-of date,
never by the language model. Both ends are inclusive and compared by date."""

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
UNITS = {"day": "days", "days": "days", "week": "weeks", "weeks": "weeks", "month": "months", "months": "months", "year": "years", "years": "years"}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}


@dataclass
class Period:
    start: date
    end: date
    label: str
    assumption: str | None = None

    def contains(self, iso_date: str) -> bool:
        return self.start.isoformat() <= iso_date[:10] <= self.end.isoformat()

    def as_dict(self) -> dict:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "label": self.label, "assumption": self.assumption}


def add_months(d: date, months: int) -> date:
    idx = d.year * 12 + (d.month - 1) + months
    year, month = divmod(idx, 12)
    return date(year, month + 1, min(d.day, calendar.monthrange(year, month + 1)[1]))


def _fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def _span(start: date, end: date, assumption: str | None = None) -> Period:
    return Period(start, end, f"{_fmt(start)} to {_fmt(end)}", assumption)


def resolve_period(text: str | None, as_of: date, start: str | None = None, end: str | None = None, data_min: date | None = None) -> Period:
    """Explicit start/end win; otherwise interpret a phrase such as 'last 4 months'."""
    if start or end:
        s = date.fromisoformat(start) if start else (data_min or date(1900, 1, 1))
        return _span(s, date.fromisoformat(end) if end else as_of)
    t = (text or "").strip().lower()
    if not t:
        raise ValueError("No time period given.")
    m = re.fullmatch(r"(?:in |over |during )?(?:the )?(?:past|trailing) (year|month|week|quarter)", t)
    if m:  # "the past year" is a rolling window ending today ("last year" is the previous calendar year)
        unit = m.group(1)
        t = {"year": "last 12 months", "month": "last 1 months", "week": "last 7 days", "quarter": "last 3 months"}[unit]
    t = re.sub(r"\b(in|during|over|within|the|for|of|past|previous|trailing)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if t in ("today", "now", "right now"):
        return _span(as_of, as_of)
    if t == "yesterday":
        return _span(as_of - timedelta(days=1), as_of - timedelta(days=1))
    m = re.fullmatch(r"(this|last) quarter", t)
    if m:
        q0 = (as_of.month - 1) // 3
        if m.group(1) == "last":
            q0 -= 1
        year = as_of.year + (q0 // 4 if q0 < 0 else 0)
        q0 %= 4
        first = date(year, q0 * 3 + 1, 1)
        last = date(year, q0 * 3 + 3, calendar.monthrange(year, q0 * 3 + 3)[1])
        return _span(first, min(last, as_of) if m.group(1) == "this" else last, "'Last quarter' is taken as the previous calendar quarter." if m.group(1) == "last" else None)
    m = re.fullmatch(r"q([1-4])(?: (\d{4}))?", t)
    if m:
        year = int(m.group(2)) if m.group(2) else as_of.year
        q = int(m.group(1))
        return _span(date(year, q * 3 - 2, 1), min(date(year, q * 3, calendar.monthrange(year, q * 3)[1]), as_of))
    m = re.fullmatch(r"since ([a-z]+)(?: (\d{4}))?", t)
    if m and m.group(1) in MONTHS:
        month = MONTHS[m.group(1)]
        year = int(m.group(2)) if m.group(2) else (as_of.year if month <= as_of.month else as_of.year - 1)
        return _span(date(year, month, 1), as_of)

    m = re.fullmatch(r"last (\w+) (days?|weeks?|months?|years?)", t)
    if m:
        n = NUMBER_WORDS.get(m.group(1)) or (int(m.group(1)) if m.group(1).isdigit() else None)
        if n is not None:
            unit = UNITS[m.group(2)]
            s = as_of - timedelta(days=n) if unit == "days" else as_of - timedelta(weeks=n) if unit == "weeks" else add_months(as_of, -n * (12 if unit == "years" else 1))
            return _span(s, as_of)
    m = re.fullmatch(r"(\d+|\w+) (days?|weeks?|months?|years?)", t)  # 'past 90 days' after filler removal
    if m and (m.group(1).isdigit() or m.group(1) in NUMBER_WORDS):
        n = int(m.group(1)) if m.group(1).isdigit() else NUMBER_WORDS[m.group(1)]
        unit = UNITS[m.group(2)]
        s = as_of - timedelta(days=n) if unit == "days" else as_of - timedelta(weeks=n) if unit == "weeks" else add_months(as_of, -n * (12 if unit == "years" else 1))
        return _span(s, as_of)
    if t in ("year to date", "ytd", "this year", "current year", "year"):
        return _span(date(as_of.year, 1, 1), as_of)
    if t in ("last year", "previous year"):
        return _span(date(as_of.year - 1, 1, 1), date(as_of.year - 1, 12, 31), f"'Last year' is taken as the calendar year {as_of.year - 1}.")
    if t == "this month":
        return _span(date(as_of.year, as_of.month, 1), as_of)
    if t == "last month":
        first = add_months(date(as_of.year, as_of.month, 1), -1)
        return _span(first, date(first.year, first.month, calendar.monthrange(first.year, first.month)[1]), "'Last month' is taken as the previous calendar month.")
    if t in ("this week", "week"):
        return _span(as_of - timedelta(days=as_of.weekday()), as_of)
    if t in ("all time", "ever", "since the start", "all", "history", "overall", "to date"):
        return _span(data_min or date(1900, 1, 1), as_of)
    if t in ("summer", "this summer", "last summer"):
        year = as_of.year if date(as_of.year, 6, 1) <= as_of or t != "last summer" and as_of.month >= 6 else as_of.year - 1
        if t == "last summer":
            year = as_of.year - 1 if as_of.month <= 8 else as_of.year
        s, e = date(year, 6, 1), min(date(year, 8, 31), as_of)
        return _span(s, e, "Summer is taken as 1 Jun to 31 Aug.")
    m = re.fullmatch(r"(\d{4})", t)
    if m:
        y = int(m.group(1))
        return _span(date(y, 1, 1), min(date(y, 12, 31), as_of) if y == as_of.year else date(y, 12, 31))
    m = re.fullmatch(r"([a-z]+)(?: (\d{4}))?", t)
    if m and m.group(1) in MONTHS:
        month = MONTHS[m.group(1)]
        year = int(m.group(2)) if m.group(2) else (as_of.year if month <= as_of.month else as_of.year - 1)
        last = calendar.monthrange(year, month)[1]
        return _span(date(year, month, 1), min(date(year, month, last), as_of) if (year, month) == (as_of.year, as_of.month) else date(year, month, last))
    raise ValueError(f"Cannot interpret the period '{text}'. Give explicit start and end dates (YYYY-MM-DD).")
