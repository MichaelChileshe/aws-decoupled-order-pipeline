#!/usr/bin/env python3
"""Create an SQS queue AND its dead-letter queue, wired together with a redrive policy.

Usage:  python3 scripts/create_queue.py <queue-name> <visibility-seconds> <PREFIX> [--fifo]
Example: python3 scripts/create_queue.py ubuntu-fulfilment 30 FUL

Saves four values to ~/p16/env.sh:  <PREFIX>_URL  <PREFIX>_ARN  <PREFIX>_DLQ_URL  <PREFIX>_DLQ_ARN
"""
import argparse, json
from kit_aws import aws, save

p = argparse.ArgumentParser()
p.add_argument("name")
p.add_argument("visibility", type=int)
p.add_argument("prefix")
p.add_argument("--fifo", action="store_true")
p.add_argument("--max-receives", type=int, default=3)
a = p.parse_args()

suffix = ".fifo" if a.fifo else ""
main_name = a.name + suffix
dlq_name = a.name + "-dlq" + suffix
fifo_attrs = {"FifoQueue": "true", "ContentBasedDeduplication": "true"} if a.fifo else {}

# 1. The dead-letter queue: keeps failed messages for the maximum 14 days.
dlq_attrs = {"MessageRetentionPeriod": "1209600", **fifo_attrs}
dlq_url = aws("sqs", "create-queue", "--queue-name", dlq_name, "--attributes", json.dumps(dlq_attrs))["QueueUrl"]
dlq_arn = aws("sqs", "get-queue-attributes", "--queue-url", dlq_url,
              "--attribute-names", "QueueArn")["Attributes"]["QueueArn"]

# 2. The main queue: long polling on, visibility timeout set, redrive to the DLQ after N failed receives.
redrive = {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": str(a.max_receives)}
main_attrs = {
    "VisibilityTimeout": str(a.visibility),
    "ReceiveMessageWaitTimeSeconds": "20",
    "MessageRetentionPeriod": "345600",
    "RedrivePolicy": json.dumps(redrive),
    **fifo_attrs,
}
url = aws("sqs", "create-queue", "--queue-name", main_name, "--attributes", json.dumps(main_attrs))["QueueUrl"]
arn = aws("sqs", "get-queue-attributes", "--queue-url", url, "--attribute-names", "QueueArn")["Attributes"]["QueueArn"]

save(f"{a.prefix}_URL", url)
save(f"{a.prefix}_ARN", arn)
save(f"{a.prefix}_DLQ_URL", dlq_url)
save(f"{a.prefix}_DLQ_ARN", dlq_arn)
print(f"\n{main_name}: visibility {a.visibility}s, long polling 20s, DLQ {dlq_name} after {a.max_receives} receives")
