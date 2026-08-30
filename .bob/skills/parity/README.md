# Parity Skill — Adapting to a Different COBOL Program

This guide explains every substitution needed to point the **parity** skill at
a program other than `InterestAccrual`.

---

## What the skill does (one paragraph)

Parity runs a six-phase verification loop: generate a deterministic input
corpus → run the legacy binary to freeze a golden trace → run the rewrite
over the same corpus → diff the two outputs semantically (values, not bytes) →
condense divergences into a classifier-friendly summary → classify root cause,
severity, and minimal fix using three parallel subagents. The legacy output is
always the ground truth.

---

## File inventory

The four files below are program-specific. Everything else (`compare.py`,
`condense.py`, the skill itself) is reusable unchanged.

| File | Role | What to replace it with |
|---|---|---|
| `generate_inputs.py` | Corpus generator | A generator that writes fixed-width (or line-delimited) records matching your program's input layout |
| `interest.cbl` | Legacy source (the specification) | Your COBOL source file |
| `interest` | Compiled legacy binary | Your compiled COBOL executable |
| `InterestAccrual.java` | The rewrite under test | Your rewrite in any language |

---

## Step-by-step substitution

### 1. Understand the legacy record layout

Open the COBOL source and locate the `FD` / `01` entries in the `FILE SECTION`
and the `PIC` clauses in `WORKING-STORAGE`. These define:

- **Input record width** — the total bytes per record in `input.dat`
- **Field offsets and types** — which byte ranges carry which values
- **Arithmetic semantics** — `ROUNDED`, `COMP-3`, implied decimal points

Write these down; you will need them for step 2.

### 2. Write a new `generate_inputs.py`

The generator must:

1. Produce records that match the byte layout your COBOL program expects.
2. Use a **fixed random seed** so the corpus is reproducible.
3. Weight the distribution toward the boundaries most likely to expose
   semantic divergence — half-cent boundaries for financial programs,
   overflow thresholds for programs with bounded field widths, zero and
   near-zero values for programs with guards.

Template (adapt field widths and encoding):

```python
#!/usr/bin/env python3
import random
from decimal import Decimal

N_RECORDS = 2000
SEED = 20260829          # keep this fixed
OUTFILE = "input.dat"

random.seed(SEED)

def encode(acct, field_a, field_b):
    # pack each field according to the COBOL PIC layout
    a = int((field_a * 100).to_integral_value())   # PIC 9(7)V99 example
    b = int((field_b * 1000).to_integral_value())  # PIC 9(2)V999 example
    return f"{acct:<10}{a:09d}{b:05d}"

records = []
for i in range(N_RECORDS):
    acct = f"ACCT{i:06d}"
    # add boundary-weighted buckets here
    records.append(encode(acct, ...))

with open(OUTFILE, "w") as fh:
    fh.write("\n".join(records) + "\n")
```

### 3. Compile the legacy binary

```bash
# GnuCOBOL
cobc -x <your-program>.cbl -o <your-program>

# IBM Enterprise COBOL (z/OS, if available)
cob2 -o <your-program> <your-program>.cbl
```

### 4. Run the legacy binary to produce the golden trace

```bash
./<your-program>                    # reads input.dat, writes output.dat
cp output.dat golden_traces.dat     # freeze — do not overwrite after this point
```

The golden trace is immutable once frozen. Re-running the legacy with the same
`input.dat` should produce identical output (determinism is assumed). If the
legacy program is non-deterministic (timestamps, random seeds, etc.) you must
seed or stub those sources before freezing.

### 5. Adapt `compare.py` if the output format differs

`compare.py` tolerates arbitrary spacing and does not require fixed column
positions — it takes the last two decimal numbers on each line as `interest`
and `total`. If your program produces more than two numeric fields per line,
or uses a different separator, edit the `parse()` function:

```python
# compare.py  ─  parse() function
# Change: how the account token is extracted and which numeric columns are used
rows[acct] = {
    "interest": Decimal(nums[-2].replace(",", "")),   # second-to-last number
    "total":    Decimal(nums[-1].replace(",", "")),   # last number
    ...
}
```

For programs with a single output value (no interest+total pair), rename the
fields to match what your program computes.

### 6. Adapt `condense.py` for your legacy source

`condense.py` uses two regexes to pull specification context out of the COBOL
source:

```python
# PIC clauses — the field type declarations
re.search(r'\bPIC\b', line)

# Arithmetic statements — where rounding and overflow live
re.search(r'\b(COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|ROUNDED)\b', line)
```

These work for standard COBOL. If your source uses a non-standard dialect or
a different language (e.g. PL/I, RPG), replace these patterns with ones that
match your data-description and arithmetic constructs.

Also update the output path if you want per-program evidence directories:

```python
# condense.py  ─  main()
with open("evidence/parity_summary.json", "w") as fh:   # ← change filename
```

### 7. Tell the skill the new paths

When you invoke the skill, the opening prompt should specify:

- the legacy binary name (e.g. `./payroll` instead of `./interest`)
- the legacy source file (e.g. `payroll.cbl`)
- the rewrite compile and run commands
- the output file name the rewrite produces (if not `java_output.dat`)

Example prompt:

```
Run parity on the payroll program. Legacy binary is ./payroll (compiled from
payroll.cbl). The Java rewrite is PayrollBatch.java, which writes
payroll_output.dat. The corpus generator is generate_payroll_inputs.py.
```

The skill will substitute these names into each phase automatically.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `compare.py` reports 0 records compared | Account column not in column 0, or delimiter differs | Edit `parse()` in `compare.py` |
| `condense.py` produces empty `pic_clauses` | COBOL source uses a non-standard `PIC` keyword spelling | Update the regex in `extract_pic_clauses()` |
| Golden trace and rewrite line counts differ | Rewrite skips blank lines or adds a header | Align blank-line handling; check the rewrite's output loop |
| All records show value divergence of exactly 0.01 | Rounding mode mismatch — rewrite uses HALF_EVEN, COBOL uses HALF_UP | Change `RoundingMode.HALF_EVEN` → `RoundingMode.HALF_UP` in the `.divide()` call |
| ~14% of records show a large constant delta | Field-width overflow not modelled — COBOL silently drops high-order digits | Implement a `truncateToPicS9_7V99`-style helper in the rewrite |
| Legacy binary is non-deterministic | Timestamps, sequence numbers, or random state | Stub or seed the non-deterministic sources before freezing the golden trace |

---

## What stays the same

- `compare.py` — reusable unchanged for any two line-oriented output files
- `condense.py` — reusable unchanged for any standard COBOL source
- `evidence/` directory structure — classification reports land here
- The three-subagent classification prompt structure in the skill
- The core rule: **legacy = specification; value differences = divergences**

# IBM Bob task session summaries

| File | Task | Bobcoins |
|---|---|---|
| parity_task01_cobol_to_java_translation.png | COBOL to Java translation + JUnit generation (Plan then Agent mode) | 4.60 |
| parity_task02_divergence_classification.png | Divergence classification via three parallel subagents | included above |
| parity_task03_skill_packaging.png | Packaging the workflow as a reusable Bob Skill | 0.794 |

Total: 5.39 of 40 Bobcoins.