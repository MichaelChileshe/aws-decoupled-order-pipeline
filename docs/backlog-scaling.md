# Scaling workers on backlog per worker

## Why not CPU

The workers spend almost all their time waiting on network calls to SQS, SSM and DynamoDB, plus the simulated 5 s of pick-and-pack. Their CPU stays flat whether 0 or 10,000 orders are queued. A CPU-based policy would never scale out when it matters. The signal that reflects the work is the queue itself.

## The metric

[`templates/backlog-target-tracking.json`](../templates/backlog-target-tracking.json) uses CloudWatch metric math inside a target-tracking policy:

```
m1 = AWS/SQS ApproximateNumberOfMessagesVisible   (QueueName = ubuntu-fulfilment, Sum)
m2 = AWS/AutoScaling GroupInServiceInstances       (AutoScalingGroupName = ubuntu-fulfilment-workers, Average)
e1 = m1 / m2                                       <- backlog per worker, the tracked value
TargetValue = 12
```

**Why 12:** acceptable wait ÷ time per order = 60 s ÷ 5 s = 12. A worker holding 12 orders clears them in about a minute. Above that, add workers; below it, remove them.

`GroupInServiceInstances` only exists once group metrics collection is enabled (`enable-metrics-collection --granularity 1Minute`), which is free. The Auto Scaling group runs 1–4 t3.micro workers across two AZs, with `--default-instance-warmup 60` so a booting worker doesn't distort the maths.

Target tracking creates two CloudWatch alarms ([`22`](screenshots/22-step9-scaling-alarms-created.png)):

- **AlarmHigh**: 3 consecutive minutes above target, so scale out.
- **AlarmLow**: 15 consecutive minutes below target, so scale in. Deliberately slow, to avoid thrashing.

## What happened

| Run | Scale-out | Result |
|---|---|---|
| Baseline, 50 orders | 1 worker for 4m28s, then desired 4; 4 in service at 4m47s | drained in **6m03s** ([`25`](screenshots/25-step10-baseline-50-orders-scale-out.png)) |
| Outage recovery, 200 orders | 1 worker at 09:36:35; desired 4 at 09:40:47 (backlog ≈ 177 per worker); 4 in service at 09:41:06 | drained in **~11 min** (estimated; see [`reliability-drills.md`](reliability-drills.md#drill-2--every-worker-down-200-orders-arrive)) |
| Scale-in after the outage | `AlarmLow` in alarm at 10:02:41 ([`32`](screenshots/32-step12-alarmlow-scale-in.png)) | three workers terminated 10:02:50, 10:05:01, 10:05:58 ([`31`](screenshots/31-step12-scaling-activities-200-processed-0-lost.png)) |

Scale-out took about 4 minutes both times. SQS publishes its metrics once a minute and the alarm needs 3 data points, plus launch and boot time. For a Black Friday peak, that lag is the reason to **pre-scale** (a scheduled action raising the minimum before the sale opens) and let backlog scaling handle whatever the forecast missed.

## The gap at zero

With 0 workers in service, `m1 / m2` divides by zero, so this policy can't be trusted to restart an empty fleet. In the outage drill I brought the fleet back by setting min 1 by hand, and the policy took over from there. Production options:

- keep **min ≥ 1** (what this design does), or
- add a simple step-scaling alarm on `ApproximateNumberOfMessagesVisible > 0` that sets capacity to 1 when the fleet is at zero.
