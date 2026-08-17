# TODO — commoner-analyse

## Current

- [ ] Fix FDA: System Settings → Privacy & Security → Full Disk Access → add Claude Code binary
- [ ] Wait for partial-recall corpus filter fix before using `corpus="folder"` in MCP queries
- [ ] Adjudicate `REJECTED`: substantive here, dodge in zero-hour — decides
      whether a cross-repo evasion rate is comparable (flagged in zero-hour PR #29)
- [ ] Search sansad.in written answers for NeVA year-wise expenditure by state

## Future

### NeVA / state assemblies
- [ ] Assam crawl — 14 sessions, only other state with question data — run via
      `commoner-probe state-assembly` (acquisition delegated there as of 2026-07-06)
- [ ] Semantic/intelligence layer: OCR pipeline (two-path Shruti/Shree), translation, embeddings, answer extraction
- [ ] Test H1-H6 hypotheses against PDF answers (`notes/gujarat-assembly15-hypotheses.md`)
- [ ] Expand to UP (`upvs.neva.gov.in`) — largest state, highest volume — via `commoner-probe state-assembly`
- [ ] Expand to Haryana (`hrla.neva.gov.in`) — via `commoner-probe state-assembly`
- [ ] Run `commoner-probe state-assembly-probe --include-councils` across all 37 portals for a
      real coverage report (supersedes the old "move recon script to neva_probe.py" plan — that
      coverage-probe capability now ships natively in commoner-probe, no local script needed)
- [ ] File RTI: MoPA — year-wise funds released per state under NeVA CSS 2019-26
- [ ] File RTI: Bihar Vidhan Sabha — status of pre-2022 paper records, digitization plan
- [ ] File RTI: NIC — status of vidhansabha.bih.nic.in data (migrating or abandoned?)
- [ ] Check Wayback Machine: vidhansabha.bih.nic.in snapshots 2010–2019
- [ ] Publish `notes/neva-api-public-draft.md` once ≥10 states verified

### Central parliament (pre-existing)
- [ ] regex_v2 coverage audit (reference corpora, measure delta from ~28%) — needs
      reference corpora not available in a code-only pass
- [ ] CPR Accountability Initiative adapter (JS-rendered, RSS route preferred) —
      **architecture flag:** this is new acquisition/scraping code; per
      `_org/architecture.md`'s Layer 0/2 split, this repo owns zero acquisition
      code. Belongs in `commoner-probe`, not here — check its CHANGELOG/README
      first, then scope there.
- [ ] TECHDEBT: topic_hash propagation into analysis_discourse.jsonl — `analyse_discourse()`
      currently has no topic-profile parameter at all (unlike mp_summary/ministry_summary),
      so this is a signature/CLI-flag addition, not a one-line fix; scope as its own task
- [ ] TECHDEBT: Channel enum (`CHANNEL_QA`/`CHANNEL_COMMITTEE` are string constants in
      discourse.py; a real enum would give type-checking over the channel value at both
      classify and aggregate call sites — not yet started)

## Archive

- [x] Op-ed + its sources MOVED OUT (2026-08-04) to
      `~/Developer/writing/opeds/hollowtech/`, per the org rule that public
      prose lives in `writing/`, not a pipeline repo. The .ris import and the
      remaining verify checklist went with it. (Routed via zero-hour first;
      that was the wrong surface — it is a member-facing product layer.)
- [x] Bihar 1937 claims verified (2026-08-04): Ram Dayalu Singh as Speaker
      CONFIRMED (no election date established); "first sat 22 July 1937"
      REFUTED — that is the first joint session of the two houses. Source and
      quotes in memory/verified_facts.md.

- [x] Fixed all 6 outstanding Codex findings (2026-07-08): `graph.py` classifications/
      atr_linkages unique constraints + clear-before-reload (PR#34); `dossier.py`
      `_resolve_display_identity` co-asker pollution (PR#30); `cli.py` `analyse-ministry`
      fail-fast on missing `analysis_discourse.jsonl` (PR#25); `aggregations.py`
      `write_ministry_summary` records_total/label_distribution unit mismatch via
      discourse-row dedup (PR#25); `discourse.py` `_VOICE_ACTIVE_RE` bare-auxiliary
      passive over-match + ministry-span IGNORECASE bug (PR#43); `CONTRIBUTING.md`
      Python-version mismatch (PR#15). Regression tests added for each.
- [x] Entity resolver: `_membership_score` now scores `context["date"]` against each
      membership's start/end window — Article 101(1) house+term disambiguation, fixing
      a documented-but-unimplemented `date` context key (2026-07-08)
- [x] TECHDEBT: duplicate HTTP layer resolved — `discourse.py`'s and `dossier.py`'s
      SSRF-guarded LLM endpoint validation, API-key resolution, chat-completions POST,
      and tolerant JSON parsing consolidated into new `llm_client.py` (2026-07-08)
- [x] Renamed sansad-semantic-crawler → commoner-analyse; released v2.1.0 (2026-07-06)
- [x] NeVA acquisition delegated to commoner-probe>=0.7.0's native `state-assembly`;
      local fallback crawler removed (2026-07-06)
- [x] Reconciled duplicated commoner-probe-delegation refactor with origin/main;
      fixed pre-existing RS-filter test bug (2026-07-06)
- [x] `export` now merges `discourseSummary`/`ministryDiscourse`; added
      `export-glossary` command; fixed evasion-rate undercounting for 4
      Instrumented Discourse Tier v2 labels (2026-07-06)
- [x] Filed REQ-0009 (theright2read) / REQ-0010 (zero-hour) for downstream
      consumption of the new export fields (2026-07-06)
- [x] Downstream pins updated: theright2read, academiaindia, zero-hour docs (2026-07-06)
- [x] Gujarat assembly 15 full crawl started (all 8 sessions, with PDFs) (2026-05-21)
- [x] Analytical hypotheses written + typeset as PDF (`notes/gujarat-assembly15-hypotheses.pdf`) (2026-05-21)
- [x] SESSION_LOG.md + WORKING.md maintained (2026-05-21)
- [x] Two mistakes logged to `_org/mistakes.md` (2026-05-21)
- [x] v1.1.0 released — changelog aligned, README updated (2026-05-20)
- [x] NeVA recon: reverse-engineered full Gujarat API surface (2026-05-20)
- [x] NeVA scraper written: neva.py + neva-crawl CLI command (2026-05-21)
- [x] Gujarat assembly 15 smoke test: 2,122 Q + 145 papers + 181 members (2026-05-21)
- [x] v1.0.0 released: ATR linkage, constitutional audit, mp/ministry dossier (2026-05-13)
- [x] CI workflow added (Python 3.10-3.13 matrix) (2026-05-13)
- [x] Security hardening PRs #19, #21 (2026-05-10)
- [x] mp-dossier + ministry-dossier feature v0.6.6 (2026-05-09)
- [ ] OCR pipeline for Session 8 answers (Tesseract 5.5.2 + guj)
- [ ] Analysis: Test H1-H7 against extracted Session 8 text
- [ ] Re-index partial-recall (awaiting corpus="folder" filter fix)
- [ ] Verify NeVA uniformity on Haryana (hrla.neva.gov.in)
- [ ] Verify NeVA uniformity on Tamil Nadu (tnla.neva.gov.in)
- [ ] Comparison: Map "Ghetto" ministries in TN vs GJ (Revenue vs Social Justice)
