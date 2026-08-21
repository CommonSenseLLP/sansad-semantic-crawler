"""Tier capability and the outcome-rate guard.

A classification tier can be structurally incapable of reaching one of the
label families. Average such a tier together with a tier that reads the whole
answer, and the one-sided tier's share moves the rate by however many rows it
contributed. The rate stays plausible. Nothing raises.

Measured in a sibling repo, which found the defect and filed REQ-0058: pooling a
table-detector tier with a reading tier under-reported dodging by 11.3 points,
12.0% against 23.2%. A cockpit, a PM profile and a report all carried the wrong
number at once.

**This repo does not have that bias today, and this module says so out loud.**
Both tiers registered below reach both families, so ``outcome_rate`` drops no
row for one-sidedness on a current corpus. The guard is here because the repo
publishes a rate over a ``classifier`` field it never reads, and the third tier
is the one that costs.

What this module does NOT do: classify, re-label, or change an existing count.
It decides which rows may be averaged, and it answers whether a rate is
publishable instead of leaving a consumer to assume it.

Capability is asserted against the taxonomy, not merely declared. See
``tests/test_tiers.py``: a tier registered as two-sided whose reachable labels
sit in one family fails the suite. A declaration nobody checks is the same
defect one level up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

BOTH_FAMILIES = frozenset({"substantive", "evasive"})

# What each tier is CAPABLE of emitting — not what it happened to emit on one
# corpus. An absent tier is refused, never assumed two-sided: assuming
# capability is how the original bias entered.
#
# The v1 keys are not historical clutter. `analysis_discourse.jsonl` files
# written before the v2 taxonomy carry them, and a corpus is read years after
# it is written. Both tiers reached both families in v1 as well.
TIER_CAPABILITY: dict[str, frozenset[str]] = {
    "regex_v1": BOTH_FAMILIES,
    "regex_v2": BOTH_FAMILIES,
    "llm_discourse_v1": BOTH_FAMILIES,
    "llm_discourse_v2": BOTH_FAMILIES,
}

ONE_SIDED_TIERS = frozenset(t for t, f in TIER_CAPABILITY.items() if f != BOTH_FAMILIES)

# A pass may name itself one thing and be stored under another. The mapping
# lives here rather than as a second registry entry, because two names both
# registered is precisely the drift REQ-0058 warns about.
TIER_ALIASES: dict[str, str] = {}


def canonical_tier(classifier: str) -> str:
    """The registry key for a tier, whatever a manifest happens to call it."""
    return TIER_ALIASES.get(classifier, classifier)


def tier_families(classifier: str) -> frozenset[str]:
    """Which label families ``classifier`` can reach. Empty means unregistered."""
    return TIER_CAPABILITY.get(canonical_tier(classifier), frozenset())


def two_sided(classifier: str) -> bool:
    """True only for a tier that could have returned either family."""
    return tier_families(classifier) == BOTH_FAMILIES


def rate_publishable(classifiers: Iterable[str]) -> bool:
    """True when every tier that fed a rate could have gone either way.

    The question a consumer of ``analyse-discourse`` should be able to ask
    before quoting a number. False on an unregistered tier as well as a
    one-sided one — an unknown tier is refused, not assumed benign.
    """
    seen = list(classifiers)
    return bool(seen) and all(two_sided(c) for c in seen)


@dataclass(frozen=True)
class DiscourseRow:
    """One discourse row, as stored in ``analysis_discourse.jsonl``.

    ``label`` and ``confidence`` are both optional, because the file carries
    rows where they are null. A ``dfg_recommendation_passthrough`` row is a
    committee ask with no response yet: it holds a real ``classifier`` and a
    null label. Such a row must not raise when a caller builds ``DiscourseRow(**row)``
    straight from the file, so ``outcome_rate`` treats a null confidence as
    below any floor.
    """

    key: str
    label: str | None
    confidence: float | None
    classifier: str


@dataclass(frozen=True)
class OutcomeRate:
    """A substantive/evasive split, its denominator, and what it dropped.

    ``excluded`` mixes two units, and it must. ``one_sided_tier``,
    ``unregistered_tier`` and ``below_confidence`` count ROWS.
    ``tied_conflict`` and ``top_unclassified`` count RECORDS. A record can also
    lose a row to the first group and still reach ``n`` through another tier.
    So ``excluded`` does not reconcile against ``n`` in either direction. It
    says what was refused and why, not what the denominator would have been.
    """

    n: int
    substantive: int
    evasive: int
    excluded: dict[str, int] = field(default_factory=dict)
    min_n: int = 30

    @property
    def citable(self) -> bool:
        return self.n >= self.min_n

    @property
    def substantive_share(self) -> float | None:
        return self.substantive / self.n if self.n else None

    @property
    def evasion_rate(self) -> float | None:
        return self.evasive / self.n if self.n else None

    def summary(self) -> str:
        if not self.n:
            head = "no eligible labels — no rate"
        else:
            head = (f"n={self.n} substantive={self.substantive_share:.1%} "
                    f"evasive={self.evasion_rate:.1%}")
        verdict = "citable" if self.citable else f"NOT citable (min_n={self.min_n})"
        drops = " ".join(f"{k}={v}" for k, v in sorted(self.excluded.items()))
        return f"{head} — {verdict}" + (f" | excluded: {drops}" if drops else "")


def outcome_rate(
    rows: Iterable[DiscourseRow],
    *,
    min_confidence: float = 0.7,
    min_n: int = 30,
) -> OutcomeRate:
    """Substantive/evasive split over labels that could have gone either way.

    One row per record key — the highest-confidence eligible one. A record a
    one-sided tier also labelled still counts when a two-sided tier reached it.
    Dropping the record would lose coverage rather than remove bias.

    ``unclassified`` is judged at the top confidence, never filtered out first.
    Filtering it first lets a record the strongest tier REFUSED to call be
    decided by a weaker tier that did call it. Every such override lands on the
    benign side, which is the failure the guard exists to prevent.

    See ``OutcomeRate.excluded`` for how to read the drop counts.
    """
    # Deferred: aggregations.py owns the split and imports this module for the
    # guard, so a module-level import here would close the cycle.
    from .aggregations import label_function

    excluded: dict[str, int] = {}
    eligible: dict[str, list[DiscourseRow]] = {}

    def drop(reason: str) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1

    for row in rows:
        if not two_sided(row.classifier):
            drop("one_sided_tier" if canonical_tier(row.classifier) in ONE_SIDED_TIERS
                 else "unregistered_tier")
            continue
        if row.confidence is None or row.confidence < min_confidence:
            drop("below_confidence")
            continue
        eligible.setdefault(row.key, []).append(row)

    # Take the top confidence per record. When two tiers tie there and disagree
    # on the family, iteration order would decide the rate, so refuse the record
    # — the same reason an unregistered tier is refused. A tie that agrees on
    # the family has nothing for order to change, so it counts.
    families: list[str] = []
    for candidates in eligible.values():
        top = max(r.confidence for r in candidates)
        tied = {label_function(r.label) for r in candidates if r.confidence == top}
        if len(tied) > 1:
            drop("tied_conflict")
            continue
        fam = tied.pop()
        if fam == "unclassified":
            drop("top_unclassified")
            continue
        families.append(fam)

    return OutcomeRate(
        n=len(families),
        substantive=families.count("substantive"),
        evasive=families.count("evasive"),
        excluded=excluded,
        min_n=min_n,
    )
