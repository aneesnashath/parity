#!/usr/bin/env python3
"""
Condense a divergence report into something worth paying an LLM to read.

286 divergences that all share one delta carry the same information as
3 examples plus a count. This groups divergences by signature, keeps a
few representatives per group, and pulls the relevant PIC clauses out of
the COBOL so the classifier has the specification inline.

Usage:
    python3 condense.py evidence/mutation_no_overflow_guard.json interest.cbl
"""

import json
import re
import sys
from collections import defaultdict
from decimal import Decimal

EXAMPLES_PER_GROUP = 3


def extract_pic_clauses(cobol_path):
    """Pull field definitions out of the COBOL. This is the spec."""
    clauses = []
    with open(cobol_path) as fh:
        for n, line in enumerate(fh, 1):
            if re.search(r'\bPIC\b', line) and not line.lstrip().startswith('*'):
                clauses.append({"line": n, "text": line.strip()})
    return clauses


def extract_arithmetic(cobol_path):
    """Lines performing arithmetic, where rounding semantics live."""
    hits = []
    with open(cobol_path) as fh:
        for n, line in enumerate(fh, 1):
            if re.search(r'\b(COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|ROUNDED)\b', line) \
               and not line.lstrip().startswith('*'):
                hits.append({"line": n, "text": line.strip()})
    return hits


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: condense.py <divergences.json> <source.cbl>")

    report = json.load(open(sys.argv[1]))
    divs = report["divergences"]

    groups = defaultdict(list)
    for d in divs:
        groups[(d["field"], d["delta"])].append(d)

    summarised = []
    for (field, delta), members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        expected = [Decimal(m["expected"]) for m in members]
        actual = [Decimal(m["actual"]) for m in members]
        summarised.append({
            "signature": f"{field} differs by {delta}",
            "field": field,
            "delta": delta,
            "occurrences": len(members),
            "share_of_all_records": f"{len(members) / report['records_compared']:.2%}",
            "expected_range": [str(min(expected)), str(max(expected))],
            "actual_range": [str(min(actual)), str(max(actual))],
            "examples": [
                {k: m[k] for k in ("account", "expected", "actual", "golden_line", "actual_line")}
                for m in members[:EXAMPLES_PER_GROUP]
            ],
        })

    out = {
        "records_compared": report["records_compared"],
        "total_value_divergences": report["value_divergences"],
        "formatting_only_benign": report["formatting_only"],
        "distinct_divergence_classes": len(groups),
        "classes": summarised,
        "specification_source": sys.argv[2],
        "pic_clauses": extract_pic_clauses(sys.argv[2]),
        "arithmetic_statements": extract_arithmetic(sys.argv[2]),
    }

    with open("evidence/parity_summary.json", "w") as fh:
        json.dump(out, fh, indent=2)

    orig = len(open(sys.argv[1]).read())
    new = len(open("evidence/parity_summary.json").read())
    print(f"{report['value_divergences']} divergences -> "
          f"{len(groups)} distinct class(es)")
    for s in summarised:
        print(f"  {s['signature']}: {s['occurrences']} records "
              f"({s['share_of_all_records']})")
    print(f"\n{orig:,} bytes -> {new:,} bytes  ({new/orig:.1%} of original)")
    print("wrote evidence/parity_summary.json")


if __name__ == "__main__":
    main()