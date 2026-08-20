"""Build the reading file for a labelling pass, without overclaiming.

A staged record carries a reply's full text and, where the document has a
recognisable boundary, the question and answer halves separately. The flag
saying the split worked is the part that matters: a reader who trusts it stops
looking for the demand in the full text, and a reply whose limbs are only in
``full`` then gets labelled on its answer alone.

One staging file claimed the split succeeded on every record. It carried no
question or answer field at all. The flag was true everywhere, so it meant
nothing anywhere. ``split_state`` exists so the
flag can only ever be as true as the fields under it.

Ported from ``zero-hour`` under REQ-0059. Nothing here knows what a ministry is.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Sequence

OK = "ok"
NO_BOUNDARY = "no_boundary"
NOT_ATTEMPTED = "not_attempted"

# Carried through to the reading file verbatim. `full` is added separately
# because it is the one field a record cannot be staged without.
CARRIED_FIELDS = ("key", "subject", "ministry", "qtype", "sitting_date")


def split_state(question: str | None, answer: str | None) -> str:
    """Whether a split actually produced both halves.

    A half that is present but blank counts as absent: an empty string is what a
    parser returns when its anchor was not found, and treating it as a
    successful split is how the flag came loose from the fields.
    """
    if question is None and answer is None:
        return NOT_ATTEMPTED
    if (question or "").strip() and (answer or "").strip():
        return OK
    return NO_BOUNDARY


def stage(
    record: Mapping[str, Any],
    full: str,
    splitter: Callable[[str], tuple[str, str] | None] | None = None,
    *,
    carried: Sequence[str] = CARRIED_FIELDS,
) -> dict[str, Any]:
    """One reading-file record, with the split reported as it happened.

    ``splitter`` returns the two halves or None when the document has no
    recognisable boundary. Pass None to stage the full text alone rather than
    silently recording a failed split. ``carried`` names the fields copied
    across; override it for a corpus whose records are shaped differently.
    """
    staged: dict[str, Any] = {name: record.get(name) for name in carried}
    staged["full"] = full

    # A splitter that ran and found no boundary is not the same fact as no
    # splitter having run: the first says the document resists splitting, the
    # second says nobody asked. Collapsing them loses the only signal that
    # would tell a later reader whether re-running the split is worth anything.
    if splitter is None:
        question = answer = None
        state = NOT_ATTEMPTED
    else:
        halves = splitter(full)
        question, answer = halves if halves else ("", "")
        state = split_state(question, answer)

    staged["reply_split"] = state
    staged["reply_split_ok"] = state == OK
    if state == OK:
        staged["question"] = question
        staged["answer"] = answer
    return staged


def unsupported_claims(records: Iterable[Mapping[str, Any]]) -> list[str]:
    """Keys whose split flag is not borne out by the fields on the record.

    Run against a staging file before reading it. A file that claims a split it
    cannot show is worse than one that admits it has only the full text.
    """
    unsupported = []
    for record in records:
        if not record.get("reply_split_ok"):
            continue
        if split_state(record.get("question"), record.get("answer")) != OK:
            unsupported.append(str(record.get("key")))
    return unsupported
