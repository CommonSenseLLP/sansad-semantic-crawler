"""Key-reconcile fragment files produced by a fleet of labelling agents.

A batch of agents each write one fragment; the parent assembles the canonical
file. The failure this module exists to stop is **positional** assembly. Rebuild
the input files mid-run — the target set grows, so the chunks are redistributed
— and an agent that finishes against the batch it was handed writes a fragment
whose row order still looks right. Rows get duplicated across fragments, rows
refer to keys no longer in any input, and target keys end up with no row at all.
Every such fragment passes its own line-count check.

So the merge is keyed, never positional, and the reconciliation is reported in
named buckets rather than resolved silently:

* **accepted** — every demanded letter labelled, exactly, no conflict.
* **partial** — a demanded letter has no label. The work is real but the answer
  is incomplete; relabel rather than record a gap as an outcome.
* **invented** — a letter the question never posed. The labeller was reading a
  different document. Accepting it would record a response to an unasked demand.
* **conflicted** — the same key labelled twice, differently. File order decided
  which won, so neither may be taken.
* **orphan** — a labelled key outside the target. Not garbage: real work filed
  against a stale key set, kept visible so it can be re-filed rather than lost.
* **unlabelled** — a target key no fragment reached.

The buckets are disjoint and, orphans aside, they partition the target.

Ported from a sibling repo under REQ-0059. Nothing here knows what a ministry is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


def _shape(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """The comparable content of a row: its (letter, label) pairs, in order."""
    return tuple(
        (str(limb.get("letter", "")), limb.get("label", ""))
        for limb in row.get("limbs", [])
    )


def collect(
    fragments: Iterable[Sequence[dict[str, Any]]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    """Merge fragments into one key->row view, marking disagreeing repeats.

    Returns the rows and a count of how many times each repeated key was seen.
    A repeat that agrees is harmless; a repeat that disagrees sets
    ``row["conflict"]``, because whichever file was read last would otherwise
    win. The repeat counts are returned rather than logged, so a caller cannot
    merge overlapping fragments without being handed the overlap.
    """
    rows: dict[str, dict[str, Any]] = {}
    seen: dict[str, int] = {}
    for fragment in fragments:
        for row in fragment:
            key = row["key"]
            if key not in rows:
                rows[key] = dict(row)
                seen[key] = 1
                continue
            seen[key] += 1
            if _shape(rows[key]) != _shape(row):
                rows[key]["conflict"] = True
    return rows, {key: n for key, n in seen.items() if n > 1}


@dataclass(frozen=True)
class Reconciliation:
    """What a merge may ingest, and what each refusal was."""

    target_total: int
    accepted: dict[str, dict[str, Any]] = field(default_factory=dict)
    unlabelled: tuple[str, ...] = ()
    partial: dict[str, tuple[str, ...]] = field(default_factory=dict)
    invented: dict[str, tuple[str, ...]] = field(default_factory=dict)
    conflicted: tuple[str, ...] = ()
    orphan: tuple[str, ...] = ()

    @property
    def redo(self) -> tuple[str, ...]:
        """Target keys still owed a pass — the input set for the next fleet."""
        return tuple(sorted(
            set(self.unlabelled)
            | set(self.partial)
            | set(self.invented)
            | set(self.conflicted)
        ))

    def summary(self) -> str:
        return (
            f"target={self.target_total} accepted={len(self.accepted)} "
            f"unlabelled={len(self.unlabelled)} partial={len(self.partial)} "
            f"invented={len(self.invented)} conflicted={len(self.conflicted)} "
            f"orphan={len(self.orphan)} redo={len(self.redo)}"
        )


def reconcile(
    target: dict[str, Sequence[str]],
    rows: dict[str, dict[str, Any]],
) -> Reconciliation:
    """Decide, per target key, whether its labelling may be ingested.

    ``target`` maps a question key to the letters the question actually demands
    — recomputed from the corpus at merge time, never inherited from whatever
    the agents were handed.
    """
    accepted: dict[str, dict[str, Any]] = {}
    unlabelled: list[str] = []
    partial: dict[str, tuple[str, ...]] = {}
    invented: dict[str, tuple[str, ...]] = {}
    conflicted: list[str] = []

    for key, letters in target.items():
        row = rows.get(key)
        if row is None:
            unlabelled.append(key)
            continue
        if row.get("conflict"):
            conflicted.append(key)
            continue
        got = {str(limb.get("letter", "")) for limb in row.get("limbs", [])}
        want = set(letters)
        extra = got - want
        if extra:
            invented[key] = tuple(sorted(extra))
            continue
        missing = want - got
        if missing:
            partial[key] = tuple(sorted(missing))
            continue
        accepted[key] = row

    return Reconciliation(
        target_total=len(target),
        accepted=accepted,
        unlabelled=tuple(sorted(unlabelled)),
        partial=partial,
        invented=invented,
        conflicted=tuple(sorted(conflicted)),
        orphan=tuple(sorted(set(rows) - set(target))),
    )
