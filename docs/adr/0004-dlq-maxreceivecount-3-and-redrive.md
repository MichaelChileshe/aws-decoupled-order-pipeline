# ADR 0004: A dead-letter queue per queue, maxReceiveCount 3, redrive after the fix

**Status:** Accepted
**Context:** Some messages can't succeed yet: a product missing from the catalog, a malformed payload, a downstream system rejecting a record. Without a limit they retry forever, burn money, and hide behind healthy work.

## Decision

- Every queue has its own DLQ (`<queue>-dlq`, FIFO for FIFO) with a **redrive policy**: `maxReceiveCount` **3**.
- DLQ retention is **14 days**, longer than the source's 4 days. For standard queues a message's age counts from its original enqueue, so a shorter-lived DLQ could expire messages the moment they arrive.
- Workers fail fast. On a known failure they set the message's visibility to 0 (retry now) instead of waiting out 30 s.
- Recovery is **fix the cause, then redrive** with `start-message-move-task` (with no destination given, messages return to their original queue).
- Peeking at a queue counts as a receive. Never casually "poll" a live source queue from the console or CLI.

## Consequences

- The `SKU-PS6` drill: 3 orders parked in the DLQ within a minute, the healthy queue kept flowing, the catalog was fixed, the redrive reported `COMPLETED 3`, and all 3 were processed with 0 lost.
- Redriven messages get a new message ID and enqueue time, so they get a fresh set of attempts.
- A DLQ entry is **not** proof of failure. With a too-short visibility timeout, successfully processed orders can end up there too (ADR 0005). Triage checks the order store before replaying.
- Next step for production: a CloudWatch alarm on `ApproximateNumberOfMessagesVisible > 0` for every DLQ, so a parked message pages someone instead of waiting to be noticed.
