#!/usr/bin/env python3
"""Attach a queue policy that lets ONLY the ubuntu-orders SNS topic send to this queue.

Usage:  python3 scripts/allow_sns.py <PREFIX>        e.g.  python3 scripts/allow_sns.py FUL
Reads <PREFIX>_URL, <PREFIX>_ARN and TOPIC_ARN from the environment.
The policy is Allow-only (no Deny), so it can never lock an administrator out.
"""
import json, os, sys
from kit_aws import ROOT, aws, env

prefix = sys.argv[1]
url, arn, topic = env(f"{prefix}_URL"), env(f"{prefix}_ARN"), env("TOPIC_ARN")

policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "AllowOrdersTopicOnly",
        "Effect": "Allow",
        "Principal": {"Service": "sns.amazonaws.com"},
        "Action": "sqs:SendMessage",
        "Resource": arn,
        "Condition": {"ArnEquals": {"aws:SourceArn": topic}},
    }],
}
aws("sqs", "set-queue-attributes", "--queue-url", url, "--attributes", json.dumps({"Policy": json.dumps(policy)}))

os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
out = os.path.join(ROOT, "build", f"queue-policy-{prefix.lower()}.json")
with open(out, "w") as f:
    json.dump(policy, f, indent=2)
print(f"{prefix}: queue policy set (only {topic.split(':')[-1]} may send). Copy saved to {out}")
