# Generalising the analytical units

> **Status: proposal.** No code changes with it. `SCOPE.md` stays canonical for
> what this repo owns today. `ARCHITECTURE.md` stays canonical for how the
> pipeline works today. Read this as a direction, not a decision.
>
> Written 2026-08-21, from an audit of how sibling repos use this package.

## The problem, measured

`commoner-probe` reaches 16 repos in the org. This package reaches 6.

The ten repos that use probe and not this package write their own analytics.
Counting files that define a `classify`, `analyse`, `aggregate` or `summarise`
function, the five heaviest hold 21, 19, 7, 7 and 4 such files. That is 58
files of hand-rolled analysis across five repos.

Of the 18 CLI commands here, sibling repos call 6. Those 6 reach 9 of 34
modules, about 26% of the package.

## The cause is the unit each package names

**Probe's unit is a source.** `sansad`, `census`, `mospi`, `cag`, `courts`,
`budget`, `shrug`, `myneta`, and about 40 more. A repo picks the sources its
subject needs. Nothing about a source assumes a domain.

**This package's unit is a parliamentary artefact.** `mp-dossier`,
`ministry-dossier`, `analyse-ministry`, `mp-summary`, `extract-atr-linkage`. A
repo studying transit, budgets or land records can use none of them.

That is why the ten probe-only repos hand-roll. The capability they need lives
here. The name on the door says it is not for them.

## The machinery is already general. The vocabulary is not.

`discourse.py` is 997 lines. About 215 are the label vocabulary. The other 782
are engine: pattern tiers, confidence scoring, channel selection, voice and
agency detection.

None of that engine knows what a ministry is. It matches patterns, ranks by
confidence, and assigns a label from a set. A different label set makes it read
RTI replies, court orders, or municipal responses.

**The repo already solved this once, for topic classification.** Topic profiles
live in JSON. The README states the reason: other projects add subjects without
editing analysis code. `topics.py` loads a profile from disk.

The discourse taxonomy did not get the same treatment. It is hardcoded as
`_LabelDef` blocks. `export-glossary` publishes it as data, but only outward.
Nothing can supply a different taxonomy inward.

## The proposal

Do for the discourse taxonomy what topic profiles already do. Make the
vocabulary an input.

Parliament then becomes one profile among several rather than the hardcoded
case. The engine stays here and serves every corpus.

The same inversion applies to the artefact commands.

| today | generalised | the key becomes |
|---|---|---|
| `analyse-ministry` | `aggregate --by <field>` | any grouping field |
| `mp-summary` | `summarise --by <field>` | any actor field |
| `mp-dossier` | `dossier --for <entity>` | any entity |
| `ministry-dossier` | `dossier --for <entity>` | any entity |
| `extract-atr-linkage` | link a follow-up to its source by citation | any document pair |

Each parliament command survives as a thin wrapper that supplies the key. The
capability underneath serves any corpus.

## What this is NOT

**It is not a proposal to move the parliament code to a consuming repo.** That
was considered and set aside. A move makes the destination bigger and this
package smaller. It reaches no new repo. Generalising reaches the ten that
already hand-roll.

**It is not a rewrite.** Four modules are already domain-free and need only a
CLI surface: `inference_gates`, `staging`, `fragment_merge`, `tiers`. None of
them appears in `cli.py` today, so no consumer can reach them without importing
the package. Exactly one Python import of this package exists across the whole
org.

**It does not need a major version.** Add the general form beside the specific
one. Deprecate in place. Remove nothing until a major, and a major needs an
explicit decision.

## Open questions

**Two of the three closed on 2026-08-21, the day this note landed.** A sibling
repo already built the same design independently, for a different domain.

1. ~~**Does a second taxonomy exist to prove the design?**~~ **Yes.** A sibling
   repo classifies officers into four categories with an `Unknown` fifth. It
   groups them into a family the way this package groups labels into evasive
   and substantive. It then gates publication on that grouping. See below.
2. **What is the artefact contract?** Still open. `aggregate --by` needs a
   defined input row shape. Today that shape is `analysis_discourse.jsonl`,
   which carries parliamentary fields.
3. ~~**Who is the first non-parliament caller?**~~ **The same repo.** It is not
   waiting for the capability. It wrote its own.

## The second taxonomy, and what it proves

The parallel is structural rather than superficial.

| this package | the sibling repo |
|---|---|
| labels grouped into evasive and substantive | categories grouped into one family |
| `rate_publishable` refuses a rate a one-sided tier fed | a gate holds every aggregate unpublishable until all checks pass |
| `outcome_rate` reports each drop by reason | the gate returns a verdict plus a list of reasons |
| `UNCLASSIFIED` stays out of the denominator | a coverage floor, so an abstention rate cannot be headlined |
| gate 2, pooled against stratified | a per-category bias bound |

Its own comment states the thesis this package states in `tiers.py`. Aggregates
stay unpublishable until every check passes.

**It also goes further than this package does.** It carries a precision
harness. That harness holds a macro F1 across categories. It holds a recall
floor for the group whose erasure it guards against. It holds a minimum
gold-set size. REQ-0058 deliberately did not port a precision harness here,
because this repo holds no adjudicated tier. That repo built one.

**What this changes.** The generalisation is no longer speculative. Two repos
reached the same design from different domains, and neither can use the other's
code. That is the case for a shared implementation, and it is also the strongest
argument that the unit is the artefact rather than the domain.

## Sequence, if it proceeds

1. Give the four domain-free modules a CLI surface. Smallest step, no contract
   change, immediately usable.
2. Load the discourse taxonomy from a profile, with the current vocabulary as
   the default profile. No consumer sees a change.
3. Add `aggregate --by` and `summarise --by` beside the parliament commands.
4. Reduce the parliament commands to wrappers over the general form.

Steps 1 and 2 stand on their own. Steps 3 and 4 want a second consumer first.
