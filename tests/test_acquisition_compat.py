from __future__ import annotations

import argparse

from commoner_analyse.acquisition_compat import (
    build_commoner_probe_command,
    deprecation_message,
)


def test_crawl_replacement_maps_to_commoner_probe_sansad_without_classifier():
    args = argparse.Namespace(
        topic="topics/libraries.json",
        out="data/libraries",
        house="ls",
        from_date="2024-01-01",
        to_date=None,
        qtype="starred",
        sessions="250-267",
        limit=10,
        max_buckets=2,
        max_records=5,
        sleep=0.1,
        no_download=True,
        reset=True,
        with_entities=True,
        classifier="regex",
    )

    command = build_commoner_probe_command("crawl", args)

    assert command == [
        "commoner-probe",
        "sansad",
        "--topic",
        "topics/libraries.json",
        "--out",
        "data/libraries",
        "--house",
        "ls",
        "--from-date",
        "2024-01-01",
        "--qtype",
        "starred",
        "--sessions",
        "250-267",
        "--limit",
        "10",
        "--max-buckets",
        "2",
        "--max-records",
        "5",
        "--sleep",
        "0.1",
        "--no-download",
        "--reset",
        "--with-entities",
    ]
    assert "--classifier" not in command


def test_committees_replacement_omits_classifier_and_composition_flags():
    args = argparse.Namespace(
        topic="topics/libraries.json",
        out="data/libraries",
        house="rs",
        committees="health,education",
        lok_sabha_no=18,
        from_date=None,
        to_date="2026-01-01",
        max_records=4,
        sleep=0.2,
        no_download=False,
        reset=False,
        classifier="regex",
        crawl_composition=True,
    )

    command = build_commoner_probe_command("crawl-committees", args)

    assert command == [
        "commoner-probe",
        "committees",
        "--topic",
        "topics/libraries.json",
        "--out",
        "data/libraries",
        "--house",
        "rs",
        "--committees",
        "health,education",
        "--lok-sabha-no",
        "18",
        "--to-date",
        "2026-01-01",
        "--max-records",
        "4",
        "--sleep",
        "0.2",
    ]
    assert "--classifier" not in command
    assert "--crawl-composition" not in command


def test_neva_replacement_renames_state_code_to_state_assembly():
    args = argparse.Namespace(
        portal="gujarat",
        state_code="GJ",
        out="data/neva/gujarat",
        assemblies="14,15",
        sleep=0.5,
        no_download=True,
        no_member_details=True,
        sessions_limit=2,
    )

    command = build_commoner_probe_command("neva-crawl", args)

    assert command == [
        "commoner-probe",
        "state-assembly",
        "--portal",
        "gujarat",
        "--state",
        "GJ",
        "--out",
        "data/neva/gujarat",
        "--assemblies",
        "14,15",
        "--sleep",
        "0.5",
        "--no-download",
        "--no-member-details",
        "--sessions-limit",
        "2",
    ]


def test_deprecation_message_names_local_compatibility_and_commoner_probe():
    args = argparse.Namespace(
        topic="topic.json",
        out="data/out",
        house="both",
        from_date=None,
        to_date=None,
        qtype="both",
        sessions="1-267",
        limit=None,
        max_buckets=None,
        max_records=None,
        sleep=0.25,
        no_download=False,
        reset=False,
        with_entities=False,
    )

    message = deprecation_message("crawl", args)

    assert "deprecated acquisition command" in message
    assert "commoner-probe sansad" in message
    assert "local compatibility crawler" in message


def test_bills_and_debates_warn_like_the_other_acquisition_commands():
    """`crawl-bills` and `crawl-debates` shipped without a deprecation notice.

    The other three acquisition commands have warned since the delegation
    landed. These two did not, so they were the only path that told a caller
    nothing about where acquisition belongs.
    """
    bills = deprecation_message(
        "crawl-bills",
        argparse.Namespace(
            out="data/out", house="ls", bill_type=None, max_records=50,
            sleep=1.0, api_url=None, dry_run=False, reset=False,
        ),
    )
    assert "deprecated acquisition command" in bills
    assert "commoner-probe bills" in bills

    debates = deprecation_message(
        "crawl-debates",
        argparse.Namespace(
            out="data/out", loksabhas="18", sessions=None,
            max_records=None, sleep=0.5, reset=False,
        ),
    )
    assert "commoner-probe debates" in debates


def test_reset_is_not_offered_where_commoner_probe_has_no_such_flag():
    """A replacement command a caller cannot run is worse than no advice.

    `commoner-probe sansad` takes `--reset`. Its `bills` and `debates`
    subcommands do not. The message therefore drops the flag for those two and
    says what to do instead.
    """
    args = argparse.Namespace(
        out="data/out", house="ls", bill_type=None, max_records=None,
        sleep=None, api_url=None, dry_run=False, reset=True,
    )
    command = build_commoner_probe_command("crawl-bills", args)
    assert "--reset" not in command

    message = deprecation_message("crawl-bills", args)
    assert "--reset has no commoner-probe equivalent" in message


def test_every_generated_command_uses_flags_commoner_probe_accepts():
    """The whole point of the message is that a caller can paste and run it.

    This walks each acquisition command, builds its replacement, and checks
    every emitted flag against the installed probe's own `--help`. It fails
    when probe renames or drops a flag, which is the drift no reader catches.
    """
    import re
    import shutil
    import subprocess
    import sys
    from pathlib import Path as _Path

    # Look beside the running interpreter first. A venv's console scripts sit
    # next to its python, and PATH often does not include that directory when
    # pytest runs as `.venv/bin/python -m pytest`. Falling straight to
    # shutil.which skipped this check on exactly the setup it is written for.
    candidate = _Path(sys.executable).parent / "commoner-probe"
    probe = str(candidate) if candidate.exists() else shutil.which("commoner-probe")
    if probe is None:
        import pytest
        pytest.skip("commoner-probe console script not found")

    cases = {
        "crawl": argparse.Namespace(
            topic="t", out="o", house="ls", from_date=None, to_date=None,
            qtype=None, sessions=None, limit=None, max_buckets=None,
            max_records=None, sleep=1.0, no_download=True, reset=True,
            with_entities=True,
        ),
        "neva-crawl": argparse.Namespace(
            portal="p", state_code="GJ", out="o", assemblies="15", sleep=1.0,
            no_download=True, no_member_details=True, sessions_limit=None,
        ),
        "crawl-bills": argparse.Namespace(
            out="o", house="ls", bill_type="government", max_records=5,
            sleep=1.0, api_url="http://x", dry_run=True, reset=True,
        ),
        "crawl-debates": argparse.Namespace(
            out="o", loksabhas="18", sessions="1", max_records=5, sleep=1.0,
            reset=True,
        ),
    }
    for name, args in cases.items():
        command = build_commoner_probe_command(name, args)
        helptext = subprocess.run(
            [probe, command[1], "--help"], capture_output=True, text=True
        ).stdout
        accepted = set(re.findall(r"--[a-z-]+", helptext))
        emitted = {token for token in command if token.startswith("--")}
        assert not emitted - accepted, (name, sorted(emitted - accepted))


# The replacement command must not quietly change the operation the caller
# asked for. Dropping --dry-run turns a planning run into a live acquisition.
# Codex found this on crawl-debates, where five flags went missing. The test
# below walks every deprecated command, so the next one cannot go missing.

# Each entry names a flag the builder deliberately does not emit, and why.
# deprecation_message() prints a note for each of these instead.
FLAGS_WITHOUT_A_PROBE_EQUIVALENT = {
    "crawl": {"classifier"},
    "crawl-committees": {"classifier", "crawl_composition"},
    "neva-crawl": {"state_code"},          # probe spells it --state
    "crawl-bills": {"reset"},
    "crawl-debates": {"reset"},
}


def test_no_deprecated_command_drops_a_flag_from_its_replacement():
    from commoner_analyse.cli import build_parser

    parser = build_parser()
    subparsers = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ][0]

    for name, exempt in FLAGS_WITHOUT_A_PROBE_EQUIVALENT.items():
        subparser = subparsers.choices[name]
        dests = {
            action.dest
            for action in subparser._actions
            if action.dest not in {"help", "func", "command"}
        }
        args = argparse.Namespace(**{dest: "X" for dest in dests})
        command = build_commoner_probe_command(name, args)
        emitted = {token for token in command if token.startswith("--")}
        wanted = {"--" + dest.replace("_", "-") for dest in dests - exempt}
        assert not wanted - emitted, (name, sorted(wanted - emitted))


def test_a_debate_dry_run_stays_a_dry_run_in_the_replacement():
    args = argparse.Namespace(
        out="o", loksabhas="18", sessions=None, from_date="2024-01-01",
        to_date="2024-03-01", max_records=5, download=True, api_url="http://x",
        sleep=1.0, reset=False, dry_run=True,
    )

    command = build_commoner_probe_command("crawl-debates", args)

    assert command == [
        "commoner-probe",
        "debates",
        "--out",
        "o",
        "--loksabhas",
        "18",
        "--from-date",
        "2024-01-01",
        "--to-date",
        "2024-03-01",
        "--max-records",
        "5",
        "--api-url",
        "http://x",
        "--sleep",
        "1.0",
        "--download",
        "--dry-run",
    ]


def test_a_debate_run_that_asks_for_nothing_extra_stays_short():
    args = argparse.Namespace(
        out="o", loksabhas="18", sessions=None, from_date=None, to_date=None,
        max_records=None, download=False, api_url=None, sleep=0.5,
        reset=False, dry_run=False,
    )

    command = build_commoner_probe_command("crawl-debates", args)

    assert command == ["commoner-probe", "debates", "--out", "o", "--loksabhas", "18", "--sleep", "0.5"]
