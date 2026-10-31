"""Account statements: date ranges in Turkish time and the CSV export."""

import csv
import io
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone

from app.models import Transaction

# Turkey has kept UTC+3 all year since 2016; a fixed offset avoids needing a tz database
# (Windows has none for zoneinfo).
TR_TZ = timezone(timedelta(hours=3), "TRT")

MAX_STATEMENT_DAYS = 366
MAX_STATEMENT_ROWS = 5000

HEADER = ["Tarih", "Açıklama", "Karşı taraf", "Tutar (TL)", "Bakiye (TL)"]


def day_bounds(
    from_date: date | None, to_date: date | None
) -> tuple[datetime | None, datetime | None]:
    """[start, end) of whole Turkish days as aware datetimes; either side may be open."""
    start = datetime.combine(from_date, time(), TR_TZ) if from_date else None
    end = datetime.combine(to_date + timedelta(days=1), time(), TR_TZ) if to_date else None
    return start, end


def format_tl(kurus: int) -> str:
    """1250,50 / -1250,50: no thousands separator, so spreadsheets read it as a number."""
    sign = "-" if kurus < 0 else ""
    whole, cents = divmod(abs(kurus), 100)
    return f"{sign}{whole},{cents:02d}"


def safe_cell(text: str) -> str:
    """Descriptions and names come from other customers. A leading =, +, -, @, tab or CR makes a
    spreadsheet run the cell as a formula, so such text is prefixed with an apostrophe."""
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def statement_csv(rows: Iterable[Transaction]) -> str:
    """Semicolon-separated with a BOM: what Excel opens correctly with Turkish settings."""
    out = io.StringIO()
    out.write("﻿")
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADER)
    for t in rows:
        writer.writerow(
            [
                t.created_at.astimezone(TR_TZ).strftime("%d.%m.%Y %H:%M"),
                safe_cell(t.description),
                safe_cell(t.counterparty or ""),
                format_tl(t.amount_kurus),
                "" if t.balance_after_kurus is None else format_tl(t.balance_after_kurus),
            ]
        )
    return out.getvalue()
