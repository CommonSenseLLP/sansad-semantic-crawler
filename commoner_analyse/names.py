"""Canonical forms for a personal name, so two spellings of one person match.

This module knows nothing about any domain. It matches names.

**The part that matters is the token sort.** Indian records write a name in
whatever order the clerk chose. "P V Joshi" and "Joshi P V" are one person, and
a normaliser that only lowercases and strips punctuation returns two different
keys for them. Sorting the tokens collapses both to one key, so a join finds
the match instead of dropping the row.

Four separate implementations of this function exist across sibling repos, and
one repo carries it twice. Three of the four lowercase and strip punctuation and
stop there. That is why this lives here now.

The honorific list is South Asian. It is not parliamentary. Extend it with the
``extra_honorifics`` argument rather than copying the function.
"""

from __future__ import annotations

import re
from typing import Iterable

HONORIFICS: tuple[str, ...] = (
    "Shri", "Smt", "Dr", "Prof", "Babu", "Ven'ble", "Kumari", "Sushri",
    "Sardar", "Adv", "Hon'ble", "Mr", "Mrs", "Ms",
)

_HONORIFIC_RE = re.compile(
    rf"\b({'|'.join(re.escape(h) for h in HONORIFICS)})\b\.?\s*", re.IGNORECASE
)


def _honorific_pattern(extra: Iterable[str] | None) -> re.Pattern[str]:
    if not extra:
        return _HONORIFIC_RE
    words = [*HONORIFICS, *extra]
    return re.compile(
        rf"\b({'|'.join(re.escape(w) for w in words)})\b\.?\s*", re.IGNORECASE
    )


def _strip(name: str, extra: Iterable[str] | None) -> str:
    """Lowercase, drop honorifics and punctuation, leaving space-separated words."""
    text = _honorific_pattern(extra).sub("", name)
    text = text.lower().replace(".", " ")
    return re.sub(r"[^a-z0-9\s]", " ", text)


def normalize_name(name: str, *, extra_honorifics: Iterable[str] | None = None) -> str:
    """Stable canonical form for matching.

    1. Comma-reversal: ``Joshi, Shri P.V.`` becomes ``Shri P.V. Joshi``.
    2. Strip honorifics.
    3. Lowercase, drop punctuation, collapse whitespace.
    4. Sort tokens alphabetically. The result is order-independent, so
       ``P V Joshi`` and ``Joshi P V`` collapse to the same key.

    Step 4 is the whole point. Drop it and a join misses every name the source
    wrote in the other order.
    """
    if not name:
        return ""
    text = name
    if "," in text:
        parts = [part.strip() for part in text.split(",", 1)]
        if len(parts) == 2:
            text = f"{parts[1]} {parts[0]}"
    return " ".join(sorted(word for word in _strip(text, extra_honorifics).split() if word))


def slugify(name: str, *, extra_honorifics: Iterable[str] | None = None) -> str:
    """URL-safe slug for an identifier suffix.

    Word order is preserved here, unlike ``normalize_name``. A slug is read by
    a person, so ``p_v_joshi`` beats the alphabetised ``joshi_p_v``.
    """
    return "_".join(word for word in _strip(name, extra_honorifics).split() if word)
