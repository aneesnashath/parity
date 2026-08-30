#!/usr/bin/env python3
"""
Generate fixed-width input records for the INTEREST COBOL program.

Record layout (24 bytes):
    cols  1-10  account id      PIC X(10)
    cols 11-19  principal       PIC 9(7)V99   implied decimal, zero padded
    cols 20-24  rate            PIC 9(2)V999  implied decimal, zero padded

The record mix is deliberately weighted toward half-cent boundaries,
because that is where exact decimal arithmetic and binary floating point
part company. If the Java rewrite is correct, these records prove it.
If it is not, these records are the ones that expose it.
"""

import random
from decimal import Decimal, ROUND_HALF_UP

N_RECORDS = 2000
SEED = 20260829          # fixed seed: the trace set is reproducible
OUTFILE = "input.dat"

random.seed(SEED)


def encode(acct: str, principal: Decimal, rate: Decimal) -> str:
    """Pack one record into the 24-byte fixed-width layout."""
    p = int((principal * 100).to_integral_value())      # 2 implied decimals
    r = int((rate * 1000).to_integral_value())          # 3 implied decimals
    return f"{acct:<10}{p:09d}{r:05d}"


def half_cent_principal() -> Decimal:
    """
    Principal ending in an odd tenth. At a 5.000% rate the exact interest
    lands on a half cent (e.g. 100.10 -> 5.005), which is precisely the
    value where HALF_UP and HALF_EVEN disagree.
    """
    whole = random.randint(1, 99999)
    tenth = random.choice([1, 3, 5, 7, 9])
    return Decimal(f"{whole}.{tenth}0")


records = []

for i in range(N_RECORDS):
    acct = f"ACCT{i:06d}"
    bucket = i % 10

    if bucket < 4:
        # 40% - half-cent boundary cases at a flat 5.000% rate
        principal = half_cent_principal()
        rate = Decimal("5.000")

    elif bucket < 6:
        # 20% - zero and near-zero principals
        principal = random.choice(
            [Decimal("0.00"), Decimal("0.01"), Decimal("0.05"), Decimal("0.10")]
        )
        rate = Decimal(f"{random.randint(1, 15)}.{random.randint(0, 999):03d}")

    elif bucket < 8:
        # 20% - upper range of PIC S9(7)V99, checks for overflow handling
        principal = Decimal(f"{random.randint(9000000, 9999999)}.{random.randint(0, 99):02d}")
        rate = Decimal(f"{random.randint(1, 15)}.{random.randint(0, 999):03d}")

    elif bucket < 9:
        # 10% - zero rate, interest must be exactly 0.00
        principal = Decimal(f"{random.randint(1, 99999)}.{random.randint(0, 99):02d}")
        rate = Decimal("0.000")

    else:
        # 10% - ordinary traffic
        principal = Decimal(f"{random.randint(1, 999999)}.{random.randint(0, 99):02d}")
        rate = Decimal(f"{random.randint(1, 20)}.{random.randint(0, 999):03d}")

    records.append(encode(acct, principal, rate))


with open(OUTFILE, "w") as fh:
    fh.write("\n".join(records) + "\n")

print(f"wrote {len(records)} records to {OUTFILE}")
print("first 3 records:")
for r in records[:3]:
    print(f"  {r}")
