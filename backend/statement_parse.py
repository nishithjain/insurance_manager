"""Parse 'NAME AND ADDRESS' CSV cells into name + address.

Rules:
- Multiline cells: after handling the first physical line (see below), remaining lines are address.
- First physical line: many exports pad with long runs of spaces between **name** and **address**
  (e.g. ``SRINIVASA REDDY K                                                  SRI SRINIVASA...``). Split that
  line on **3+ whitespace characters** so only the name stays in the name field.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Split "NAME<3+ spaces>START OF ADDRESS" (fixed-width / Excel padding)
_PADDING_SPLIT = re.compile(r"\s{3,}")


def split_name_address(raw: Optional[str]) -> Tuple[str, Optional[str]]:
    if raw is None or not str(raw).strip():
        return "Unknown", None
    text = str(raw).strip()
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    if not lines:
        return "Unknown", None

    first = lines[0]
    tail = "\n".join(lines[1:]) if len(lines) > 1 else ""

    parts = _PADDING_SPLIT.split(first, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        name = parts[0].strip()[:200]
        addr_first = parts[1].strip()
        if tail:
            addr = addr_first + "\n" + tail
        else:
            addr = addr_first
        return name, addr

    # No wide padding on line 1: treat whole first line as name (legacy multiline layout)
    name = (first[:200] or "Unknown")
    if tail:
        return name, tail
    return name, None
