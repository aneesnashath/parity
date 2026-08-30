# Create a Bob Skill called parity that packages the verification workflow in this repo: capture a golden trace from a legacy binary, replay a rewrite over the same corpus, diff semantically with compare.py, condense with condense.py, and classify divergences using parallel subagents.

The core rule: the legacy program is the authoritative specification. Where legacy and rewrite disagree, the legacy defines correct behaviour. Formatting differences are benign; value differences are divergences.

Include the skill definition and a short README explaining how to point it at a different COBOL program.

---

**Status:** active  **Date:** 2026-08-29

---

### 👤 User

Create a Bob Skill called parity that packages the verification workflow in this repo: capture a golden trace from a legacy binary, replay a rewrite over the same corpus, diff semantically with compare.py, condense with condense.py, and classify divergences using parallel subagents.

The core rule: the legacy program is the authoritative specification. Where legacy and rewrite disagree, the legacy defines correct behaviour. Formatting differences are benign; value differences are divergences.

Include the skill definition and a short README explaining how to point it at a different COBOL program.

---

### 🤖 Assistant

> 🔧 called: list_files, read_file, read_file, read_file, read_file, read_file, read_file



> 🔧 **list_files** — .

> 🔧 **read_file** — README.md

> 🔧 **read_file** — compare.py

> 🔧 **read_file** — condense.py

> 🔧 **read_file** — generate_inputs.py

> 🔧 **read_file** — interest.cbl

> 🔧 **read_file** — evidence/classification_report.md

### 🤖 Assistant

> 🔧 called: read_file, read_file, use_skill

Now let me read the evidence files and the Java source to fully understand the workflow before writing the skill:

> 🔧 **read_file** — InterestAccrual.java

> 🔧 **read_file** — evidence/parity_summary.json

> 🔧 **use_skill** — create-skill

### 🤖 Assistant

> 🔧 called: glob, glob

Now I have a complete picture of the repo. Let me check the existing `.bob` or `.agents` directory structure:

> 🔧 **glob** — .bob/**/*

> 🔧 **glob** — .agents/**/*

### 🤖 Assistant

> 🔧 called: update_todo_list, write_file, update_todo_list, write_file, update_todo_list

No existing `.bob` or `.agents` directories. I'll use `.bob/skills/parity/`. Now I have everything I need to write both files.

> 🔧 **update_todo_list** — [-] Write .bob/skills/parity/SKILL.md
[ ] Write .bob/skills/parity/README.md


> 🔧 **write_file** — .bob/skills/parity/SKILL.md

> 🔧 **update_todo_list** — [x] Write .bob/skills/parity/SKILL.md
[-] Write .bob/skills/parity/README.md


> 🔧 **write_file** — # Parity Skill — Adapting to a Different COBOL Program

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


> 🔧 **update_todo_list** — [x] Write .bob/skills/parity/SKILL.md
[x] Write .bob/skills/parity/README.md


### 🤖 Assistant

> 🔧 called: execute_command

Let me do a quick sanity-check on both files:

> 🔧 **execute_command** — Get-Content .bob/skills/parity/SKILL.md | Select-Object -First 10; Write-Host "---"; Get-ChildItem .bob/skills/parity/

### 🤖 Assistant

> 🔧 called: search_and_replace

The em-dash in the YAML description multi-line string is harmless (it's in a prose continuation line, not a YAML key), but let me replace it with a plain hyphen to keep the frontmatter clean:

> 🔧 **search_and_replace** — .bob/skills/parity/SKILL.md

### 🤖 Assistant

Both files are written and valid. Here is what was created:

---

## What was built

### [`.bob/skills/parity/SKILL.md`](.bob/skills/parity/SKILL.md)

The skill definition. It registers under the name `parity`, auto-activates on phrases like "run parity", "check parity", "compare legacy to rewrite", and "divergence analysis", and walks Bob through eight phases:

| Phase | What happens |
|---|---|
| **0** Prerequisites | Confirms all required files exist before doing anything |
| **1** Corpus | Runs `generate_inputs.py` (or skips if `input.dat` is current) |
| **2** Golden trace | Compiles + runs the legacy binary; freezes `golden_traces.dat` as the immutable oracle |
| **3** Rewrite | Compiles + runs the Java rewrite over the same corpus |
| **4** Semantic diff | Calls `compare.py`; stops here with a pass if VALUE divergences = 0 |
| **5** Condense | Calls `condense.py` to group divergences by signature and embed PIC clauses |
| **6** Classify | Spawns three `spawn_subagent` calls **in parallel** — severity, root cause, minimal patch — each with its exact prompt and mandate |
| **7** Report | Merges the three subagent outputs into `evidence/classification_report.md` |
| **8** Summary | Prints a final table including cumulative financial drift |

The core invariant is baked into the skill's preamble: *formatting differences are benign; value differences are divergences*.

---

### [`.bob/skills/parity/README.md`](.bob/skills/parity/README.md)

A step-by-step guide for pointing the skill at any other COBOL program. Covers:

- The four program-specific files and exactly what to replace each with
- A `generate_inputs.py` template with boundary-weighted bucket comments
- How to compile under GnuCOBOL vs IBM Enterprise COBOL
- How to adapt `compare.py`'s `parse()` function if the output layout differs
- How to adapt `condense.py`'s regexes for non-standard dialects (PL/I, RPG)
- What to tell Bob when invoking the skill (example prompt included)
- A table of the five most common failure modes with exact fixes (HALF_EVEN → HALF_UP, overflow truncation, non-deterministic legacy, etc.)

---

The skill will be available in the **next task/conversation**. If it doesn't auto-activate, type `/parity` to invoke it explicitly.