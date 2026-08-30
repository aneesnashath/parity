# Parity — behavioural equivalence verification for agentic code migration

**IBM TechXchange 2026 Pre-conference Dev Day Hackathon**
Workflow addressed: application maintenance / legacy modernisation

---

## Results

| Variant | JUnit result | Parity divergences | Divergence rate | Financial drift |
|---|---|---|---|---|
| Bob's translation (unmodified) | 24/24 pass | **0** / 2000 | 0% | £0.00 |
| Mutation A: `HALF_UP` → `HALF_EVEN` | 5 failed | 376 | 18.80% | £3.76 |
| Mutation B: overflow guard removed | 2 failed | 286 | 14.30% | £2,860,000,000 |

**The test suite ranked a £3.76 defect as more than twice as serious as a £2.86 billion one.**

Five red tests against two. A test suite reports *that* something broke. It cannot
report *how much*, *which accounts*, or *what share of traffic*. Parity does.

Cost: **5.39 Bobcoins** for the full build, of which the three parallel
classification subagents accounted for **0.071**.

Raw JUnit output for all three variants is in `evidence/junit/`.

---

## The problem

Behavioural equivalence between a legacy program and its rewrite is the unsolved
blocker in mainframe modernisation. An LLM can now translate COBOL to Java faster
than a team can verify the result — so the bottleneck has moved from *writing* the
code to *trusting* it.

Existing verification does not close the gap:

- **Test suites** encode what the author thought to check. When the tests are
  generated from the same source as the translation, a misreading of the COBOL
  is asserted rather than caught.
- **Byte diffs** cannot distinguish a padding change from a rounding change.
- **Manual review** does not scale to a 200k-line migration.

## The approach

The legacy program is the specification. Parity makes that specification
executable.

1. **Capture** — run the COBOL binary over a generated input corpus; store the
   outputs as a golden trace. Deterministic, zero LLM cost.
2. **Translate** — IBM Bob (Plan mode → Agent mode) produces the Java and a
   JUnit suite.
3. **Replay** — run the Java over the same corpus.
4. **Diff semantically** — compare values, not bytes. Formatting differences are
   classified benign; value differences are divergences.
5. **Condense** — group divergences by signature and embed the relevant COBOL
   `PIC` clauses. 82,798 bytes → 2,674 bytes (3.2%).
6. **Classify** — three Bob subagents in parallel: severity classification, root
   cause traced to a COBOL line, and a minimal remediation patch.
7. **Package** — the whole sequence ships as a Bob Skill
   (`.bob/skills/parity/`) with a porting guide covering GnuCOBOL vs IBM
   Enterprise COBOL, adaptation for PL/I and RPG, and the five most common
   migration failure modes.

## What Bob got right unprompted

The translation prompt made no mention of rounding, packed decimal, or field
widths. Bob independently reproduced two mainframe semantics that commonly
break migrations:

- **`RoundingMode.HALF_UP`** matching COBOL's `ROUNDED`
  (nearest-away-from-zero), covering 376 half-cent boundary records.
- **A `truncateToPic9_7V99` helper** reproducing `PIC S9(7)V99` field-width
  overflow, where COBOL silently drops the eighth integer digit. 286 records.

The subagent classifier further recognised that the divergence reports were
mutation-testing artifacts rather than live defects, and declined to patch
already-correct source.

## Input corpus design

2,000 fixed-width records, fixed seed (`20260829`), deliberately weighted toward
the boundaries where exact decimal arithmetic and binary floating point diverge:
half-cent results at a flat 5.000% rate, zero and near-zero principals,
upper-range values that overflow `PIC S9(7)V99`, and zero-rate records.

## Reproducing

Verified from a clean clone with no manual steps.

```bash
sudo apt install -y gnucobol openjdk-21-jdk-headless

python3 generate_inputs.py          # 2000 records, fixed seed
cobc -x interest.cbl -o interest
./interest                          # writes output.dat
cp output.dat golden_traces.dat     # freeze the oracle

javac InterestAccrual.java && java InterestAccrual
python3 compare.py golden_traces.dat java_output.dat
python3 condense.py evidence/mutation_no_overflow_guard.json interest.cbl
```

JUnit is run separately. The console-standalone jar is deliberately not
vendored — download it from Maven Central and place it in the repository root:

```bash
java -jar junit-platform-console-standalone-1.10.3.jar \
  --class-path . --select-class InterestAccrualTest
```

Mutation A: change `RoundingMode.HALF_UP` to `HALF_EVEN` on line 71.
Mutation B: remove the `truncateToPic9_7V99` calls on lines 77–78.

## Repository

```
interest.cbl              legacy COBOL program (the specification)
generate_inputs.py        boundary-weighted corpus generator
InterestAccrual.java      Bob's translation
InterestAccrualTest.java  Bob's generated JUnit suite
compare.py                semantic comparator
condense.py               divergence condenser
golden_traces.dat         frozen COBOL oracle
evidence/                 divergence reports, condensed summaries,
                          JUnit output, subagent classification report
bob_sessions/             Bob task session consumption summaries
.bob/skills/parity/       reusable Bob Skill: SKILL.md + porting guide
```

## Limitations

Parity verifies only the behaviours present in the captured corpus — trace
coverage is the ceiling on what it can certify. It detects divergence from the
legacy system, which is not the same as detecting incorrectness: where the
legacy program is itself wrong, Parity will correctly flag a *fixed* rewrite as
divergent. That is the intended semantics for migration work, where downstream
reconciliation depends on the legacy behaviour rather than the ideal one.

The £2.86bn figure is the arithmetic sum of divergences across a 2,000-record
synthetic corpus, not a projection of real-world exposure. It represents 286
records disagreeing by £10,000,000 each; actual exposure scales with how many
accounts sit near the `PIC S9(7)V99` field limit.

Demonstrated on a single COBOL batch program. Extending to file-based and
VSAM-backed programs requires capture at the I/O boundary rather than stdout.
