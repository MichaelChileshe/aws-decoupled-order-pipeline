#!/usr/bin/env python3
"""Publish test orders to the ubuntu-orders SNS topic, 10 at a time (PublishBatch).

Usage:  python3 scripts/publish_orders.py <RUN> <COUNT> [--sku SKU] [--event EVENT]
Examples:
  python3 scripts/publish_orders.py BF 200                     200 normal orders  BF-0001 .. BF-0200
  python3 scripts/publish_orders.py PS6 3 --sku SKU-PS6        3 orders for a product not in the catalog
  python3 scripts/publish_orders.py FANOUT 1 --event OrderCancelled

Every order carries three message attributes: event_type, order_id, sku.
With raw message delivery on, SNS copies them onto the SQS message, which is what the worker reads.
"""
import argparse, datetime, json, os, tempfile
from kit_aws import aws, env

SKUS = ["SKU-TV55", "SKU-FRIDGE", "SKU-AIRFRYER"]
PRICES = {"SKU-TV55": 8999.00, "SKU-FRIDGE": 12499.00, "SKU-AIRFRYER": 1299.00, "SKU-PS6": 11999.00}

p = argparse.ArgumentParser()
p.add_argument("run")
p.add_argument("count", type=int)
p.add_argument("--sku")
p.add_argument("--event", default="OrderPlaced")
p.add_argument("--start", type=int, default=1, help="first order number (default 1)")
a = p.parse_args()

topic = env("TOPIC_ARN")
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def attr(v):
    return {"DataType": "String", "StringValue": v}


entries = []
for i in range(a.start, a.start + a.count):
    order_id = f"{a.run}-{i:04d}"
    sku = a.sku or SKUS[i % len(SKUS)]
    body = {"order_id": order_id, "event": a.event, "sku": sku, "qty": 1,
            "amount_zar": PRICES.get(sku, 999.00), "store": "online", "placed_at": now}
    entries.append({
        "Id": f"m{i}",
        "Message": json.dumps(body),
        "MessageAttributes": {"event_type": attr(a.event), "order_id": attr(order_id), "sku": attr(sku)},
    })

sent = failed = 0
for start in range(0, len(entries), 10):  # PublishBatch takes at most 10 entries
    batch = entries[start:start + 10]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(batch, f)
        path = f.name
    res = aws("sns", "publish-batch", "--topic-arn", topic, "--publish-batch-request-entries", f"file://{path}")
    os.remove(path)
    sent += len(res.get("Successful", []))
    failed += len(res.get("Failed", []))
    for fail in res.get("Failed", []):
        print("  failed:", fail)

print(f"{now}  published {sent} x {a.event}  ({a.run}-{a.start:04d} .. {a.run}-{a.start + a.count - 1:04d})  failed: {failed}")
