# ADR 0002: Scale the worker fleet on backlog per worker, not CPU

**Status:** Accepted
**Context:** Fulfilment workers are I/O-bound. They wait on SQS, SSM, DynamoDB and the warehouse work itself, so CPU stays low whether the queue holds 0 orders or 10,000.

## Options considered

| Option | Verdict |
|---|---|
| Target tracking on average CPU | ❌ Would never scale out under a queue backlog |
| Step scaling on raw queue depth | ⚠️ Works, but the right depth threshold changes with fleet size, so it needs retuning as the fleet grows |
| **Target tracking on backlog per worker** (queue depth ÷ in-service workers, via metric math) | ✅ Chosen |
| Lambda with an SQS event source instead of EC2 | ⚠️ Scales automatically and is often the better default. EC2 was kept here to model long-running warehouse integrations and to make the scaling explicit and measurable |

## Decision

- Metric: `ApproximateNumberOfMessagesVisible ÷ GroupInServiceInstances` (metric math inside the target-tracking policy). Group metrics collection is enabled at 1-minute granularity.
- Target: **12** = acceptable wait (60 s) ÷ processing time per order (5 s).
- Fleet: min 1, max 4 (a lab cost cap), two AZs, 60 s default instance warm-up.

## Consequences

- Baseline 50 orders: scaled 1 → 4 at 4m28s and drained in 6m03s. The outage recovery scaled 1 → 4 and drained 200 orders in about 11 minutes.
- Scale-out lags about 3–4 minutes (1-minute SQS metrics × 3 data points + boot). Known peaks such as Black Friday should be **pre-scaled** with a scheduled action; backlog scaling handles the rest.
- Scale-in is deliberately slow (15 low minutes).
- **At zero workers the ratio divides by zero**, so this policy can't restart an empty fleet. Keep min ≥ 1, or add a step-scaling alarm on "queue not empty" for scale-from-zero.
