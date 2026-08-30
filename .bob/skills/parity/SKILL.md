---
name: parity
description: >
  Use when the user wants to verify behavioural equivalence between a legacy
  binary (COBOL or otherwise) and a rewritten program - captures a golden trace
  from the legacy, replays the rewrite over the same corpus, diffs semantically,
  condenses divergences, and classifies them with parallel subagents.
  Also activates for phrases like "run parity", "check parity", "parity check",
  "compare legacy to rewrite", "golden trace verification", "divergence analysis".
---

# Parity — Behavioural Equivalence Verification

## Core rule

The legacy binary is the authoritative specification. Where legacy and rewrite
disagree, the legacy defines correct behaviour. **Formatting differences are
benign; value differences are divergences.**

---

## Prerequisites

Confirm these exist in the workspace before starting. If any are missing, tell
the user exactly what is needed and stop.

| Item | Expected path / description |
|---|---|
| Legacy binary | compiled and executable (e.g. `./interest` for COBOL, a JAR, etc.) |
| Rewrite source | compilable source file (e.g. `InterestAccrual.java`) |
| Input corpus | `input.dat` — fixed-width records, or equivalent |
| `generate_inputs.py` | corpus generator (if corpus must be (re)generated) |
| `compare.py` | semantic comparator script |
| `condense.py` | divergence condenser script |
| COBOL/legacy source | e.g. `interest.cbl` — used by `condense.py` for PIC clause extraction |

---

## Phase 1 — Corpus generation (skip if `input.dat` already exists and is current)

Run the corpus generator to produce a reproducible, boundary-weighted input
set. The generator must use a fixed seed so every run over the same source
produces the same trace.

```
python3 generate_inputs.py
```

Report the record count and the first 3 lines of `input.dat`.

---

## Phase 2 — Capture golden trace from the legacy binary

Run the legacy program to produce `output.dat`, then freeze it as
`golden_traces.dat`. This is the oracle; do not overwrite it once frozen.

```
./interest                         # or the equivalent legacy invocation
cp output.dat golden_traces.dat
```

If the legacy binary is not yet compiled, compile it first:
```
cobc -x interest.cbl -o interest   # GnuCOBOL; adjust for the target toolchain
```

Confirm `golden_traces.dat` exists and report its line count.

---

## Phase 3 — Compile and run the rewrite

Compile the rewrite if it is not already compiled:
```
javac InterestAccrual.java          # adjust for the target language
```

Run it over the same input corpus:
```
java InterestAccrual               # writes java_output.dat (or equivalent)
```

Confirm the output file exists and report its line count. Check that it matches
the line count of `golden_traces.dat`.

---

## Phase 4 — Semantic diff with `compare.py`

```
python3 compare.py golden_traces.dat java_output.dat
```

`compare.py` writes `divergences.json`. Read its stdout output and report:
- records compared
- VALUE divergences (non-zero = actionable)
- formatting-only differences (benign — skip)
- missing / extra records

**If VALUE divergences = 0:** report "Behavioural equivalence holds" and stop.
No further phases are needed.

**If VALUE divergences > 0:** continue to Phase 5.

---

## Phase 5 — Condense with `condense.py`

Condense the raw divergence list into a classifier-friendly summary that
groups by signature and embeds the relevant source PIC clauses. Replace
`interest.cbl` with the actual legacy source path for this program.

```
python3 condense.py divergences.json interest.cbl
```

This writes `evidence/parity_summary.json`. Report:
- number of distinct divergence classes
- each class: signature, occurrence count, share of records
- compression ratio (original bytes → summary bytes)

---

## Phase 6 — Parallel classification by three subagents

Spawn **three subagents in parallel** using `spawn_subagent`. Each receives
the condensed summary (`evidence/parity_summary.json`), the legacy source
(e.g. `interest.cbl`), and its specific mandate. Do not wait for one before
launching the others.

### Subagent A — Severity classification

> You are a migration-verification auditor. The legacy program is the
> authoritative specification. Read `evidence/parity_summary.json` and
> `interest.cbl` (or the provided legacy source).
>
> For each divergence class, classify severity as one of:
> - **REGRESSION** — a value difference that contradicts the legacy spec
> - **BENIGN** — a formatting-only difference (no numeric change)
> - **INTENTIONAL** — a documented, authorised deviation from legacy behaviour
>
> Support every classification with a specific reference to the legacy source
> (file name + line number). Output a markdown table: class | severity | evidence.

### Subagent B — Root cause

> You are a COBOL-to-Java migration specialist. Read `evidence/parity_summary.json`
> and `interest.cbl` (or the provided legacy source).
>
> For each divergence class, identify the exact COBOL construct responsible
> (verb, PIC clause, or compiler option) and the corresponding Java code that
> diverges. Cite specific line numbers in both sources. Explain the mechanism
> that produces the observed delta.

### Subagent C — Minimal remediation

> You are a Java engineer performing a correctness fix for a COBOL migration.
> Read `evidence/parity_summary.json` and `interest.cbl` (or the provided
> legacy source).
>
> For each divergence class that is a REGRESSION: propose the minimal code
> change (unified diff, single-method scope where possible) that restores
> behavioural equivalence with the legacy. If the current source is already
> correct (e.g. the divergence file is from a deliberate mutation test), state
> that explicitly and do not propose changes.
>
> For BENIGN or INTENTIONAL classes: no patch needed — state why.

---

## Phase 7 — Synthesise and write the classification report

Collect the three subagent outputs. Write a combined report to
`evidence/classification_report.md` with sections:

1. **Divergence Classification** (severity per class, from Subagent A)
2. **COBOL Construct and Root Cause** (from Subagent B)
3. **Minimal Patch** (from Subagent C)
4. **Appendix: Evidence File Summary** (table of all evidence files with
   record counts and divergence counts)

Use the existing `evidence/classification_report.md` as a style reference if
it is present.

---

## Phase 8 — Summary

Print a final summary table:

| Phase | Result |
|---|---|
| Corpus | N records, fixed seed |
| Golden trace | N lines captured from legacy |
| Rewrite output | N lines produced |
| VALUE divergences | N (0 = pass) |
| Divergence rate | N% |
| Distinct classes | N |
| Severity breakdown | e.g. 1 REGRESSION, 0 BENIGN, 0 INTENTIONAL |
| Report | `evidence/classification_report.md` |

If divergences > 0, state the cumulative absolute drift (financial exposure).

---

## Adapting to a different program

See `README.md` in this skill directory for a step-by-step guide on pointing
the workflow at a different COBOL program.
