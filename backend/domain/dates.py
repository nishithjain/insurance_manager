"""
Unified date parsing helpers for the Insurance domain.

Before this module, the codebase had three separate parsers — ``server.py`` had both
``_parse_date_flexible_for_export`` and ``_parse_policy_end_date``, and
``statement_parse.py`` had its own ``_parse_iso_date_dd_mm_yyyy``. Different handlers
happened to agree on simple ISO inputs but disagreed on edge cases.

All three behaviors are now expressed here:

- :func:`parse_policy_end_date_strict` — strict ISO / ISO-datetime (used by renewal
  bucketing and anywhere policy end dates are expected to be clean).
- :func:`parse_date_flexible` — tolerant of ISO, ISO-datetime, and ``dd-mm-yyyy``
  (used by CSV export filtering where legacy rows may still have mixed formats).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

_DDMMYYYY = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")


def parse_policy_end_date_strict(val: Any) -> date:
    """
    Normalize an ISO date / datetime string to a :class:`date`. Raises on invalid input.

    Accepted shapes:
    - ``"YYYY-MM-DD"``
    - ``"YYYY-MM-DDTHH:MM:SS[...]"``
    - ``"YYYY-MM-DDTHH:MM:SSZ"``
    """
    s = str(val).strip()
    if "T" in s:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    return datetime.fromisoformat(s[:10]).date()


def parse_date_flexible(val: Any) -> Optional[date]:
    """
    Return a calendar date for ISO, ISO-datetime, or ``dd-mm-yyyy`` input, or None.

    Used by CSV exports where historical rows may have been imported from various
    statement formats.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None

    # ISO datetime ("T" separator) or " " separator followed by time.
    if "T" in s or (len(s) > 10 and s[10] == " "):
        try:
            if "T" in s:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(s[:19].replace(" ", "T", 1))
            return dt.date()
        except ValueError:
            pass

    # Plain ISO date prefix.
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            pass

    # Legacy "dd-mm-yyyy".
    m = _DDMMYYYY.match(s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            return None

    return None
