#!/usr/bin/env python3
"""Watch the fulfilment queue drain and the worker fleet scale. Stops when the queue is empty twice in a row.

Usage:  python3 scripts/watch_drain.py        (Ctrl+C stops it at any time - nothing is changed)
"""
import time, datetime
UTC = datetime.timezone.utc
from kit_aws import aws, env

url = env("FUL_URL")
ASG = "ubuntu-fulfilment-workers"
start = time.time()
empty_polls = 0
print("time(UTC)   elapsed  waiting  in-flight  workers(in service)")
while True:
    at = aws("sqs", "get-queue-attributes", "--queue-url", url, "--attribute-names",
             "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible")["Attributes"]
    waiting, flight = int(at["ApproximateNumberOfMessages"]), int(at["ApproximateNumberOfMessagesNotVisible"])
    g = aws("autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", ASG)["AutoScalingGroups"]
    in_service = sum(1 for i in g[0]["Instances"] if i["LifecycleState"] == "InService") if g else 0
    desired = g[0]["DesiredCapacity"] if g else 0
    el = int(time.time() - start)
    print(f"{datetime.datetime.now(UTC):%H:%M:%S}   {el//60:>3}m{el%60:02d}s  {waiting:>7}  {flight:>9}  {in_service} (desired {desired})")
    empty_polls = empty_polls + 1 if waiting == 0 and flight == 0 else 0
    if empty_polls >= 2:
        print(f"\nDRAINED: fulfilment queue empty after {el//60}m{el%60:02d}s")
        break
    time.sleep(15)
