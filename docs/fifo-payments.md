# FIFO for payment steps: ordered per order, never twice

## Why FIFO here, and only here

Card payments go **authorise → capture → settle**. Capturing before authorising fails, and settling twice double-charges a customer. Standard queues deliver *at least once* and only roughly in order. That's fine for orders, where the worker is built to cope, but not for money movements.

A FIFO queue guarantees:

- **Order within a message group.** I use the order ID as the group, so each order's steps stay in sequence while different orders still process in parallel.
- **Deduplication for 5 minutes.** With content-based deduplication, an identical message body sent again within the window is accepted but not delivered twice.

I kept orders on standard queues because they need throughput and resilience more than strict order. Paying the FIFO throughput limits for every order would buy nothing. The trade-off is in [ADR 0003](adr/0003-standard-queues-for-orders-fifo-for-payments.md).

## What I built

`ubuntu-payments.fifo` with `FifoQueue=true` and `ContentBasedDeduplication=true`, plus `ubuntu-payments-dlq.fifo`. A FIFO queue's DLQ must also be FIFO. Both are created by [`scripts/create_queue.py`](../scripts/create_queue.py) with `--fifo`.

## The proof

Six sends. The sixth was an accidental resend of the first (same body, same group):

```
ORD-A step1 authorise R8999   -> 133a3408-...
ORD-B step1 authorise R1299   -> 43853624-...
ORD-A step2 capture   R8999   -> b01c9925-...
ORD-B step2 capture   R1299   -> e0c90074-...
ORD-A step3 settle    R8999   -> 36896649-...
ORD-A step1 authorise R8999   -> 133a3408-...   <- the ORIGINAL MessageId, not a new one
```

- **Deduplication:** SQS returned the first message's ID for the resend, and the queue held **5**, not 6 ([`09`](screenshots/09-step4-fifo-duplicate-send-same-message-id.png), [`10`](screenshots/10-step4-fifo-depth-five-not-six.png)). The caller got a success, not an error, which is exactly what a retrying payment client needs: its retry is safe.
- **Ordering:** receiving returned `ORD-A` step 1 → 2 → 3 and `ORD-B` step 1 → 2 ([`11`](screenshots/11-step4-fifo-ordered-per-group.png)).

## Limits to design around

- Throughput is capped per API action (higher with batching and high-throughput mode). Group by order ID so load spreads across many groups.
- While a group has a message in flight, nothing else from that group is delivered. A stuck message blocks its own order's later steps, which is exactly what you want for payments, and why the FIFO DLQ matters.
- Deduplication lasts 5 minutes. A resend after that is a new message, so downstream payment calls should still be idempotent (for example, with a payment-provider idempotency key).
