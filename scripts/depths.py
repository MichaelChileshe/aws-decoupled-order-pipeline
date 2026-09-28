#!/usr/bin/env python3
"""Show how many messages are waiting (visible) and being worked on (in flight) in every project queue."""
import os
from kit_aws import aws

QUEUES = ["FUL", "FUL_DLQ", "EMAIL", "EMAIL_DLQ", "ANALYTICS", "ANALYTICS_DLQ", "PAY", "PAY_DLQ", "SCRATCH"]
print(f"{'queue':<30}{'waiting':>9}{'in flight':>11}")
for q in QUEUES:
    url = os.environ.get(f"{q}_URL")
    if not url:
        continue
    at = aws("sqs", "get-queue-attributes", "--queue-url", url, "--attribute-names",
             "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible")["Attributes"]
    print(f"{url.rsplit('/', 1)[-1]:<30}{at['ApproximateNumberOfMessages']:>9}{at['ApproximateNumberOfMessagesNotVisible']:>11}")
