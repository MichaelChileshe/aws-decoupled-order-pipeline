#!/usr/bin/env python3
"""The measurement: how many orders of a run were processed, how many were lost, how many processed twice.

Usage:  python3 scripts/count_orders.py <RUN> <EXPECTED>        e.g.  python3 scripts/count_orders.py BF 200
"""
import json, sys
from kit_aws import aws

run, expected = sys.argv[1], int(sys.argv[2])
res = aws("dynamodb", "scan", "--table-name", "ubuntu-fulfilled-orders",
          "--filter-expression", "begins_with(order_id, :p)",
          "--expression-attribute-values", json.dumps({":p": {"S": f"{run}-"}}))
items = res.get("Items", [])
counts = {i["order_id"]["S"]: int(i["process_count"]["N"]) for i in items}
dupes = {k: v for k, v in counts.items() if v > 1}
missing = [f"{run}-{n:04d}" for n in range(1, expected + 1) if f"{run}-{n:04d}" not in counts]
workers = {i["worker_id"]["S"] for i in items if "worker_id" in i}

print(f"run {run}: expected {expected} | processed {len(counts)} | LOST {len(missing)} | "
      f"processed more than once {len(dupes)} | workers used {len(workers)}")
if missing:
    print("  missing:", ", ".join(missing[:20]) + (" ..." if len(missing) > 20 else ""))
if dupes:
    print("  duplicates:", ", ".join(f"{k} x{v}" for k, v in sorted(dupes.items())[:20]))
