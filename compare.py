#!/usr/bin/env python3
"""
Parity comparator.

Diffs the Java rewrite's output against the COBOL golden trace.

The point is SEMANTIC equivalence, not byte equality. A rewrite that pads
differently or drops a leading space is not broken; a rewrite that computes
a different number is. Those two are separated here, because conflating
them is how you end up reporting 2000 false divergences.

Usage:
    python3 compare.py golden_traces.dat java_output.dat

Writes divergences.json for the classifier stage.
"""

import json
import re
import sys
from decimal import Decimal

NUM = re.compile(r"-?[\d,]+(?:\.\d+)?")


def parse(path):
    """
    Tolerantly pull (account, interest, total) from each line.

    Deliberately does not assume column positions: the Java rewrite is
    allowed to format differently. We take the account token and the last
    two decimal numbers on the line.
    """
    rows = {}
    with open(path) as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                rows[f"__UNPARSED_{lineno}"] = {"raw": line, "unparsed": True}
                continue
            acct, remainder = parts[0].strip(), parts[1]
            nums = NUM.findall(remainder)
            if len(nums) < 2:
                rows[f"__UNPARSED_{lineno}"] = {"raw": line, "unparsed": True}
                continue
            rows[acct] = {
                "interest": Decimal(nums[-2].replace(",", "")),
                "total": Decimal(nums[-1].replace(",", "")),
                "raw": line,
            }
    return rows


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: compare.py <golden_traces.dat> <java_output.dat>")

    golden = parse(sys.argv[1])
    actual = parse(sys.argv[2])

    value_divergences = []
    formatting_only = 0
    missing = sorted(set(golden) - set(actual))
    extra = sorted(set(actual) - set(golden))

    for acct in sorted(set(golden) & set(actual)):
        g, a = golden[acct], actual[acct]
        if g.get("unparsed") or a.get("unparsed"):
            continue

        di = a["interest"] - g["interest"]
        dt = a["total"] - g["total"]

        if di or dt:
            value_divergences.append({
                "account": acct,
                "field": "interest" if di else "total",
                "expected": str(g["interest"] if di else g["total"]),
                "actual": str(a["interest"] if di else a["total"]),
                "delta": str(di or dt),
                "golden_line": g["raw"],
                "actual_line": a["raw"],
            })
        elif g["raw"] != a["raw"]:
            formatting_only += 1

    compared = len(set(golden) & set(actual))
    n_div = len(value_divergences)

    print(f"records compared          : {compared}")
    print(f"VALUE divergences         : {n_div}")
    print(f"formatting-only (benign)  : {formatting_only}")
    print(f"missing from rewrite      : {len(missing)}")
    print(f"extra in rewrite          : {len(extra)}")

    if n_div:
        deltas = sorted({d["delta"] for d in value_divergences})
        print(f"\ndistinct deltas observed  : {deltas[:6]}")
        print(f"\nfirst {min(8, n_div)} divergences:")
        print(f"  {'ACCOUNT':<12}{'EXPECTED':>12}{'ACTUAL':>12}{'DELTA':>9}")
        for d in value_divergences[:8]:
            print(f"  {d['account']:<12}{d['expected']:>12}{d['actual']:>12}{d['delta']:>9}")

        total_drift = sum(abs(Decimal(d["delta"])) for d in value_divergences)
        print(f"\ncumulative absolute drift : {total_drift}")
        print(f"divergence rate           : {n_div / compared:.2%} of records")
    else:
        print("\nNo value divergences. Behavioural equivalence holds across "
              f"{compared} records.")

    with open("divergences.json", "w") as fh:
        json.dump({
            "records_compared": compared,
            "value_divergences": n_div,
            "formatting_only": formatting_only,
            "missing": missing[:50],
            "extra": extra[:50],
            "divergences": value_divergences,
        }, fh, indent=2)

    print("\nwrote divergences.json")


if __name__ == "__main__":
    main()
