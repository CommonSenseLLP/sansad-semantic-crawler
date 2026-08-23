# Commoner Analyse

The domain-analysis layer over Indian parliamentary records.
[`commoner-probe`](https://github.com/CommonerLLP/commoner-probe) acquires
them. This package classifies, aggregates, and cross-references them.

It reads Lok Sabha and Rajya Sabha questions, standing-committee reports,
and NeVA state-assembly records. Topic profiles live in JSON, so a project
adds a subject without editing analysis code.

It is not a watchdog, a summariser, or a search engine. It builds corpora
and audits for researchers.

## Install

Not on PyPI yet. Install from a release tag:

```bash
pip install "commoner-analyse @ git+https://github.com/CommonerLLP/commoner-analyse.git@v2.7.1"
```

Extras are `[http]`, `[pdf]`, `[embeddings]`, `[llm]` and `[all]`. Add one
in the usual brackets:

```bash
pip install "commoner-analyse[pdf] @ git+https://github.com/CommonerLLP/commoner-analyse.git@v2.7.1"
```

Pin the same line in a project's `requirements.txt`:

```text
commoner-analyse[http,pdf] @ git+https://github.com/CommonerLLP/commoner-analyse.git@v2.7.1
```

`commoner-probe` is the one required third-party dependency. Beyond it the
package runs on a clean Python 3.11+ install. Without `[http]` it falls back
to `urllib`. Without `[pdf]` it falls back to the `pdftotext` system binary.

## Quick start

```bash
# Core pipeline
commoner-analyse crawl             # Fetch metadata and PDFs
commoner-analyse crawl-committees  # Crawl standing-committee reports
commoner-analyse parse             # Topic classification -> analysis.jsonl
commoner-analyse export            # Aggregate for sites
commoner-analyse export-glossary   # Discourse taxonomy as standalone JSON/JS
commoner-analyse build-graph       # Ingest outputs into SQLite

# Response / audit pipeline
commoner-analyse extract-answers      # Response extraction -> answers.jsonl
commoner-analyse analyse-discourse    # Discourse + voice/agency
commoner-analyse analyse-weights      # Per-person / per-party weights

# Research / audit subcommands
commoner-analyse extract-atr-linkage  # Map ATRs to original reports
commoner-analyse mp-dossier           # MP-level briefing
commoner-analyse ministry-dossier     # Ministry audit report
commoner-analyse analyse-ministry     # Aggregate evasion patterns
commoner-analyse mp-summary           # Aggregate MP assertion rates
```

## Commands that assume no legislature

These five work on any corpus. They exist because the capability sat here,
importable only, while other projects rebuilt it by hand.

```bash
# One canonical key per name. The token sort makes it order-independent, so
# "P V Joshi" and "Joshi P V" collapse and a join stops dropping rows.
commoner-analyse normalize-names --file names.txt
commoner-analyse normalize-names --file names.txt --slug

# Refuse a pooled statistic that falls outside its stratum range. Exits
# non-zero, so a pipeline stops instead of publishing.
commoner-analyse check-pooling --pooled 0.047 --strata 0.44,0.68

# Refuse a per-unit rate computed over rows that are not units.
commoner-analyse check-units rows.jsonl --unit-key shrid2

# Name any staged record whose split flag its own fields do not support.
commoner-analyse check-claims staging.jsonl

# Reconcile labelling fragments by key, never by position.
commoner-analyse merge-fragments f1.jsonl f2.jsonl --target target.jsonl
```

Each check exits non-zero on a refusal. A gate that only prints is a gate a
pipeline ignores.

## The three analytical layers

They stay separate because they answer different questions.

**1. Topic classification** writes `analysis.jsonl`. Does this record
belong in my corpus, and which tags fired? Four modes: `regex` (the
audit-grade deterministic path), `embeddings`, `llm`, and `ensemble`.

**2. Response discourse analysis** writes `analysis_discourse.jsonl`. What
is the political function of the ministry's response? It runs on extracted
response text through `extract-answers` then `analyse-discourse`.

The current discourse label set is:

- `CONSTITUTIONAL_DEFAULT` — category-wise representation data is omitted
  through aggregate totals or substitution
- `FEDERAL_DEFLECTION` — the response pushes responsibility away through
  a "State Subject" or federalism dodge
- `STRUCTURAL_REFUSAL` — blunt refusal; no scheme, no approval, or no
  willingness to act
- `REPRESENTATIONAL_SILENCE` — factual recitation that strategically
  ignores the representational core of the question
- `ACCEPTED` — concrete commitment with specifics, dates, approvals, or
  allocations
- `DEFLECTED` — indefinite deferral such as "under consideration" or
  "steps are being taken"
- `ABSORBED` — acknowledged without commitment; noted, appreciated, or
  absorbed into procedure
- `REJECTED` — flat disagreement, infeasibility, or rejection of the
  recommendation
- `SUBSTITUTED` — the question's metric is replaced with the ministry's
  preferred framing
- `DATA_WITHHELD` — the response says data is not maintained, not
  available, or still being collected
- `SCOPE_NARROWED` — the response narrows jurisdiction or says the matter
  lies outside the ministry's purview
- `CIRCULAR_REFERENCE` — the committee response points back to its own
  earlier non-answer
- `FACTUAL_DISCLOSURE` — direct factual answer without obvious evasion or
  new commitment
- `UNCLASSIFIED` — no current deterministic pattern matched

Channel matters. `qa` covers written question answers. `committee` covers
ATR and committee-response text. `dfg` passthrough rows carry null
discourse fields, because a recommendation exists before any response does.

An optional LLM second pass only touches rows the regex tier left
`UNCLASSIFIED`.

**3. Voice and agency** is additive on top of layer 2. Is the response
active, passive, or mixed, and does it name an actor? The fields are
`voice`, `passive_ratio`, `agent_named` and `agent_terms`. It is
deterministic and dependency-free, using conservative heuristics rather
than a full NLP parser.

Downstream commands compose these layers rather than recomputing them.
`analyse-ministry` rolls them up by ministry, `mp-summary` by asking MP,
`build-graph` indexes them in SQLite, and the dossier commands turn them
into Markdown.

## What "audit-grade" means here

Deterministic, traceable, and linked. The regex classifier returns the
same output for the same input. `_runs.jsonl` records which profile bytes
produced which records. The ATR Linkage Engine maps Action Taken Reports
back to the recommendations they answer.

**The labels are instrumented, not authoritative.** They are technical
hypotheses about linguistic patterns of institutional evasion. Treat them
as a triage signal, not a verdict.

## Output layout

```text
data/<topic>/
  manifest.jsonl       normalised crawl records (one per question or report)
  _runs.jsonl          one record per crawl invocation: profile hash,
                       classifier mode, scope, counts, errors. Read this
                       to know which apparatus produced which records.
  analysis.jsonl       topic-level semantic classification (after `parse`)
  answers.jsonl        extracted question/answer or recommendation/response
                       pairs (after `extract-answers`)
  analysis_discourse.jsonl
                       discourse labels + voice/agency analysis over
                       response text (after `analyse-discourse`)
  atr_linkage.jsonl    mapped bidirectional links (after `extract-atr-linkage`)
  mp_summary.jsonl     per-MP discourse summary (after `mp-summary`)
  ministry_summary_qa.jsonl
                       per-ministry Q/A discourse summary
  ministry_summary_committee.jsonl
                       per-committee ATR/committee discourse summary
  weights/
    person_topic.jsonl per-person weighted topic scores
    party_topic.jsonl  per-party weighted topic scores
  graph.db             SQLite read layer over outputs (after `build-graph`)
  summary.json         aggregate export (after `export`)
  pdfs/
    ls/*.pdf
    rs/*.pdf
  text/*.txt           extracted PDF text, one file per record
  ministry_dossiers/   Markdown audit reports (after `ministry-dossier`)
  mp_dossiers/         Markdown MP briefings (after `mp-dossier`)
```

Records carry a `run_id` that maps to a row in `_runs.jsonl`. To verify
which topic-profile bytes produced a record, look up its run.

## Design notes

- **Acquisition is delegated to `commoner-probe`.** It is the single source
  of truth for crawling and the one required dependency.
- **`pdftotext` is preferred over `pdfminer.six`.** Parliamentary PDFs lean
  on layout for tables. `pdfminer.six` is the fallback.
- **Stable keys.** A record's `key` comes from
  `(house, qtype, qno, answer-date)` for questions, and from
  `(house, committee, report_no[, lokSabha])` for committee reports.
- **Form is data, not metadata.** Where a committee report was laid
  (Speaker only, Lok Sabha only, both houses) is a political distinction.
  It surfaces as `presented_via` rather than hiding inside dates.
- Core schemas and the pipeline are stable as of v1.0.0.

## Status

The per-release timeline lives in [CHANGELOG.md](CHANGELOG.md). `main` may
carry additive work ahead of the newest tag. Check the changelog's
`Unreleased` section.

## Licence

[GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).

The package was PolyForm Noncommercial 1.0.0 until 2026-08-20. Commercial
use is now permitted. Anyone who runs a modified version as a network
service must publish their changes.

## Citation

`CITATION.cff` at the repository root carries machine-readable metadata.
GitHub renders a "Cite this repository" button against it.
