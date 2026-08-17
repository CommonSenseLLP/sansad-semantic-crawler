# SCOPE — commoner-analyse

Canonical scope doc, per the organisation's canonical-project-docs rule.

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

The organisation already routes prose this way for other threads. The
publication layer lives in a writing repo, never in a hybrid pipeline repo.

This repo drifted from that. A finished op-ed and its primary sources sat in
the repo's local research area for months, because that is where the probing
happened. On **2026-08-04** they moved to the publication surface.

**The rule going forward:** research notes, probe output, hypotheses and
verification ledgers belong here. A draft written for a reader outside the org
does not — it moves to the surface that will publish it, and it takes its
citations and primary sources with it. Analysis that feeds a piece stays;
the piece goes.

Working research on the same subjects correctly stays. Research is not
publication. If a piece of it becomes a draft for outside readers, it moves
under the same rule.

## Current active scope

- Maintaining the analysis surface against `commoner-probe` releases (pinned
  `==`, currently `0.14.3`).
- Keeping the discourse taxonomy and its consumers in sync — the export path
  exists now; drift is a test failure downstream, not a manual check.
- **`REJECTED`: adjudicated 2026-08-17. See the section below.**
- NeVA state coverage remains 1 (Gujarat). Acquisition for more states is
  `commoner-probe state-assembly` work, not this repo's.

## Public package discipline

This is a published package with downstream consumers (`theright2read`,
`academiaindia`, `zero-hour`, `public-finance`).

Versioning, release and pinning rules are set organisation-wide, not here.

This repo's own data contract:

- `session` is `"ls"` | `"rs"` only. `year` is the YYYY-YY financial year.
  `probed_at` is the source-of-truth timestamp; `crawled_at` is a
  backwards-compatibility alias and both should be present.
- Changelog entry lands in the same commit as any version bump.

## `REJECTED` — the adjudication (2026-08-17)

`zero-hour` counts `REJECTED` as a dodge. This repo counts it as substantive.
`theright2read` had copied the dodge reading and inflated its evasion rate
(REQ-0009). REQ-0057 blocks on the verdict.

**Verdict: `REJECTED` stays substantive. The label is nonetheless wrong, and
the wrongness is narrower than either repo's reading.**

A refusal is an answer. When a ministry says it "does not agree", or that a
measure is "not feasible", the government has taken a position on the record.
That position is contestable in public. An evasion is not. Counting refusals
as evasions destroys the distinction the taxonomy exists to draw. It also
flatters the ministry that refuses openly over the one that says nothing.

The defect is that `_REJECTED` in `discourse.py` carries two different speech
acts under one label:

1. **Refusal with a stated position** — `does not agree`, `does not concur`,
   `not feasible`, `constraints of resources`, `govt. has not approved`. The
   ministry answered. The answer is no. **Substantive.**
2. **Premise denial** — `does not arise`, and the sub-part form
   `(b) and (c) Do not arise`. This answers nothing. It dissolves the question
   instead of replying to it, and it is one of the most common non-answers in
   Indian parliamentary practice. **Evasive.**

The tree already carries the evidence. `_CONFIDENCE["REJECTED"] = 0.90` is
justified in its own comment as "near-impossible to misread 'does not agree'".
The confidence was set on act 1 and then applied to act 2.

**What must happen before the split ships:**

1. Measure the share of `REJECTED` rows that fire only on the `does not arise`
   patterns. **Not measured.** `data/` is down under the m1-storage incident,
   so no count exists in this repo today.
2. Read the 20 records where `zero-hour` says `FACTUAL_DISCLOSURE` and this
   repo says `SUBSTITUTED` (REQ-0057). Nobody has read them.
3. Ship the split as a **minor** release with a changelog entry. It moves a
   published rate for `theright2read` and `academiaindia`.

**Until step 1 runs, do not change the classification.** A rate that moves for
an unmeasured reason is not an improvement.

**What `zero-hour` may do now:** stop treating the whole label as a dodge. It
is right about `does not arise` and wrong about the rest.

## Non-negotiable

**No claim without a source read in the turn that made it.** This repo feeds
litigation-adjacent and press-adjacent work. A confident wrong number costs
more than no number. Verified facts are logged to the repo's verification
ledger as they are verified, not later.
