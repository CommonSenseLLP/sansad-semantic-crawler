"""Checks that decide whether an aggregate is entitled to exist.

``aggregations.py`` computes numbers. Nothing here computes one. Each gate
answers a prior question: may this number be quoted at all?

The defect class is not a crash and not a null. It is **a plausible figure that
passes every consistency check and is wrong**. Both gates below were specified
against real failures of that kind, in which a pooled rate and a distance
measure each came back confident and inverted.

Two of the seven gates in REQ-0055 ship here. They are pure functions over a
frame and need no corpus, no reference layer and no vintage metadata:

* **Gate 2, pooled versus stratified.** If the pooled statistic falls outside
  the range of the stratum statistics, the pooling is invalid.
* **Gate 4, the unit is not the row.** A row is not the thing you are counting
  until you have checked that it is.

Gates 1, 3, 5 and 6 need dataset context this repo does not hold: completeness
strata, a join's dropped rows, a variable inventory per year, a vintage on each
frame. They are not stubbed here. A stub that always passes is worse than an
absent gate, because a caller reads it as a check that ran.

**Gate 7, the same-frame control, is a study design and has no callable.** It
belongs beside the gates rather than in them, so it is written here instead.
When an instrument is known to under-collect, do not look for a better
instrument first. Look for two groups the biased source names *in the same
document, in the same place, on the same day*. Both then carry identical
extraction bias, so the absolute rate of either is meaningless while the
difference between them is readable. A biased instrument plus a controlled
contrast beats waiting for a clean instrument.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


class InferenceGateError(AssertionError):
    """A gate refused. The message carries the reason, not a stack trace."""


@dataclass(frozen=True)
class Verdict:
    """Whether a number may be quoted, and why not when it may not.

    ``detail`` carries the counts a caller needs to write the caveat, so a
    failing gate does not force a second pass over the same frame.
    """

    ok: bool
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.ok


def build_pooling_verdict(
    pooled: float,
    strata: Sequence[float],
    *,
    tolerance: float = 0.0,
) -> Verdict:
    """Gate 2 — a pooled statistic must lie inside its stratum range.

    Simpson's paradox needs no explanation to be caught. When completeness
    varies by stratum and the compared groups are spread unevenly across
    strata, the pooled figure can land outside every stratum it pools. That is
    not a weak signal. It can point the opposite way from every stratum.

    ``tolerance`` widens the range on both sides, for the rounding a caller
    applied before calling. It does not license a pooled figure that sits
    outside by more than rounding.
    """
    if not strata:
        return Verdict(False, "no strata to check the pooled figure against")
    if any(value is None for value in strata):
        return Verdict(False, "a stratum has no value; compute it or drop the stratum")

    low = min(strata) - tolerance
    high = max(strata) + tolerance
    detail = {
        "pooled": pooled,
        "stratum_low": min(strata),
        "stratum_high": max(strata),
        "stratum_total": len(strata),
    }
    if pooled < low or pooled > high:
        return Verdict(
            False,
            f"pooled {pooled} falls outside the stratum range "
            f"{min(strata)} to {max(strata)}; the pooling is invalid",
            detail,
        )
    return Verdict(True, "pooled figure lies inside the stratum range", detail)


def assert_pooling_valid(
    pooled: float,
    strata: Sequence[float],
    *,
    tolerance: float = 0.0,
) -> None:
    """Gate 2, at a boundary. Raises ``InferenceGateError`` on refusal."""
    verdict = build_pooling_verdict(pooled, strata, tolerance=tolerance)
    if not verdict.ok:
        raise InferenceGateError(verdict.reason)


def build_unit_verdict(rows: Iterable[Mapping[str, Any]], *, unit_key: str) -> Verdict:
    """Gate 4 — one row is one unit, or the rate is per row and says so.

    A spatial unit can hold several administrative ones. A boundary layer can
    carry more polygons than distinct area codes, because an area is
    multi-part. A record listed in two source workspaces is one thing. Every
    per-unit rate computed on rows counts such units more than once, and
    reports a rate over a denominator nobody chose.

    A row missing ``unit_key`` fails the gate rather than forming its own unit.
    An absent key is not a distinct unit; it is a row that cannot be attributed.
    """
    rows_by_unit: Counter[Any] = Counter()
    row_total = 0
    unattributed_total = 0
    for row in rows:
        row_total += 1
        value = row.get(unit_key)
        if value is None:
            unattributed_total += 1
            continue
        rows_by_unit[value] += 1

    multi_part = {unit: n for unit, n in rows_by_unit.items() if n > 1}
    detail = {
        "row_total": row_total,
        "unit_total": len(rows_by_unit),
        "multi_part_total": len(multi_part),
        "unattributed_total": unattributed_total,
        "rows_by_multi_part_unit": dict(sorted(multi_part.items(), key=lambda kv: -kv[1])),
    }
    if unattributed_total:
        return Verdict(
            False,
            f"{unattributed_total} of {row_total} rows carry no {unit_key!r}; "
            "they cannot be attributed to a unit",
            detail,
        )
    if multi_part:
        return Verdict(
            False,
            f"{row_total} rows cover {len(rows_by_unit)} units: "
            f"{len(multi_part)} units hold more than one row; a per-row rate is "
            "not a per-unit rate",
            detail,
        )
    return Verdict(True, f"{row_total} rows over {row_total} distinct units", detail)


def assert_one_row_per_unit(rows: Iterable[Mapping[str, Any]], *, unit_key: str) -> None:
    """Gate 4, at a boundary. Raises ``InferenceGateError`` on refusal."""
    verdict = build_unit_verdict(rows, unit_key=unit_key)
    if not verdict.ok:
        raise InferenceGateError(verdict.reason)
