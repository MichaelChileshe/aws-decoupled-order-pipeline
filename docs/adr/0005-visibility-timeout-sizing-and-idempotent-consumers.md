# ADR 0005: Size the visibility timeout above processing time, and make consumers idempotent

**Status:** Accepted
**Context:** SQS standard queues deliver at least once. A received message becomes visible again when its visibility timeout expires, whether or not the worker holding it has finished.

## What I measured

| Visibility timeout | Processing time | Orders | Processed more than once |
|---|---|---|---|
| **30 s** | 5 s | 254 (FANOUT, BASE, PS6, BF) | **0** |
| **2 s** | 5 s | 30 (VIS) | **7** (5 × 2, 2 × 3) |

No error was raised anywhere during the 2 s run. The only symptom was duplicate work: in a warehouse, extra parcels.

## Decision

1. **Visibility timeout ≥ worst-case processing time**, with headroom. Here 30 s for 5 s of work. For long or variable jobs, the worker extends the timeout as it goes (`ChangeMessageVisibility` heartbeat) rather than guessing a huge fixed value.
2. **Delete only after the result is durably recorded.** The worker deletes the message only if the DynamoDB write succeeded; otherwise it releases the message for another attempt.
3. **Idempotent consumers in production:** record an order with a conditional write (`attribute_not_exists(order_id)`), so a second delivery is detected and skipped. The lab worker uses `ADD process_count :one` deliberately, so duplicates are counted rather than hidden. That's how the 7 were measured.

## Consequences

- Duplicates become a non-event rather than an incident, whatever their cause: timeout, scale-in mid-message, network retry.
- The DLQ stays meaningful. A too-short timeout can also push successfully processed messages past `maxReceiveCount`. It didn't in my run (DLQ 0, too few idle workers), but it would with a larger fleet.
- Changing a queue's visibility timeout is now treated as a reviewed change, not a tuning knob.
