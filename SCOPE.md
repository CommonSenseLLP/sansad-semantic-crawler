# SCOPE — commoner-analyse

Canonical scope doc (per `_org/architecture.md` → Canonical Project Documents).

**Doc conflict priority:** `SCOPE.md` → `ARCHITECTURE.md` → `CHANGELOG.md` →
`README.md`. If two disagree, reconcile here first; do not silently pick the
convenient one. `ARCHITECTURE.md` is canonical for the pipeline map and the
per-layer contracts; this file is canonical for the boundary.

---

## What this repo is

The **domain-analysis layer** over public records that `commoner-probe`
acquires. It reads a manifest and PDFs; it emits classification, discourse
labels, aggregations, dossiers, and a graph. It is published as a package
(PolyForm-Noncommercial-1.0.0) and consumed by other CommonerLLP repos.

The record is not the finding. Turning an acquired corpus into a claim someone
can act on is this repo's whole job.

## What it owns

1. **Topic classification** — `parse` (regex / embeddings / llm tiers). The
   regex tier is the audit-grade path and stays deterministic.
2. **Discourse analysis** — `analyse-discourse`, and the label taxonomy in
   `discourse.py::DISCOURSE_LABEL_DESCRIPTIONS`. **This repo is the single
   source of that vocabulary for the whole org.** Consumers read it as data
   via `export-glossary`; nobody hand-copies it (see REQ-0010).
3. **Answer / ATR extraction** — `extract-answers`, `extract-atr-linkage`.
4. **Aggregation** — `mp-summary`, `analyse-ministry`, `analyse-weights`, and
   the substantive/evasive split in `aggregations.py`. That split must stay in
   sync with the taxonomy above; they have drifted before.
5. **Dossiers and graph** — `mp-dossier`, `ministry-dossier`, `build-graph`.
6. **The public contracts** — the JSONL manifest schema, the `export` /
   `export-glossary` output shape, and the CLI surface. Every field is an
   interface; see "Public package discipline" below.

## What it does not own

| not this repo | whose | why |
|---|---|---|
| Acquisition — HTTP, crawling, scraping, provenance manifests | `commoner-probe` (hard dependency) | This repo holds **zero** acquisition code. A missing capability is a commoner-probe issue; check its CHANGELOG before assuming a gap, then file a cross-repo REQ. |
| Chunking, embeddings, FTS/vector search, MCP retrieval serving | `partial-recall` | Do not build a second search stack. The org paid for that lesson once. |
| Budget, RBI, fiscal, NHA/OOPE tooling | `public-finance` | — |
| Member-facing products — question kits, briefs, dossiers delivered to MPs/MLAs | `zero-hour` | This repo produces the analysis those products consume. |
| Public static surfaces / campaign sites | `theright2read`, `academiaindia`, `sevent4` | They consume generated data. |
| **Publication — op-eds, articles, pamphlets, public prose** | the relevant publication surface | See below. |

## Publication is not this repo's job

The org rule already exists for other threads: governmentality prose lives in
`writing/governmentality/`, the senior-bureaucracy op-ed layer in
`writing/opeds/meritless/` — "publication layer lives in writing, not a
hybrid repo" (`_org/architecture.md`).

This repo drifted from that. The NeVA/Bihar hollowtech op-ed and its primary
sources sat in `notes/` for months because that is where the probing happened.
On **2026-08-04** they moved to `~/Developer/writing/opeds/hollowtech/`.

**The rule going forward:** research notes, probe output, hypotheses and
verification ledgers belong here. A draft written for a reader outside the org
does not — it moves to the surface that will publish it, and it takes its
citations and primary sources with it. Analysis that feeds a piece stays;
the piece goes.

Still here, correctly: `notes/blog-neva-institutional-memory.md`,
`notes/bihar-assembly-records-tragedy.md`, `notes/neva-api*.md`,
`notes/NEVA_EXPANSION_STRATEGY.md` — research, not publication. If any becomes
a draft for outside readers, it moves under the same rule.

## Current active scope

- Maintaining the analysis surface against `commoner-probe` releases (pinned
  `==`, currently `0.13.0`).
- Keeping the discourse taxonomy and its consumers in sync — the export path
  exists now; drift is a test failure downstream, not a manual check.
- **Open:** whether `REJECTED` is substantive (this repo) or a dodge
  (`zero-hour`). Unadjudicated. Until it is settled, evasion rates from the two
  repos are not comparable.
- NeVA state coverage remains 1 (Gujarat). Acquisition for more states is
  `commoner-probe state-assembly` work, not this repo's.

## Public package discipline

This is a published package with downstream consumers (`theright2read`,
`academiaindia`, `zero-hour`, `public-finance`).

- **Patch** — fixes and docs, no API change. **Minor** — backwards-compatible
  additions, deprecation warnings before removal. **Major** — breaking change,
  explicit user decision.
- Do not rename CLI flags, change output schema fields, or alter the JSONL
  manifest structure in a patch or minor release.
- `session` is `"ls"` | `"rs"` only. `year` is the YYYY-YY financial year.
  `probed_at` is the source-of-truth timestamp; `crawled_at` is a
  backwards-compatibility alias and both should be present.
- Changelog entry lands in the same commit as any version bump.

## Non-negotiable

**No claim without a source read in the turn that made it.** This repo feeds
litigation-adjacent and press-adjacent work; a confident wrong number costs
more than no number. Verified facts are logged to `memory/verified_facts.md`
as they are verified, not later.
