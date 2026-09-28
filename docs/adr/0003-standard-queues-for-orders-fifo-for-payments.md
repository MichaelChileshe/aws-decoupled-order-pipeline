# ADR 0003: Standard queues for orders, a FIFO queue for payment steps

**Status:** Accepted
**Context:** Orders and payment steps have different correctness needs. Orders need to be absorbed at any volume and processed eventually. Payment steps (authorise → capture → settle) must happen in order, and must never run twice.

## Decision

| | Orders | Payment steps |
|---|---|---|
| Queue type | **Standard** | **FIFO** (`ubuntu-payments.fifo`) |
| Delivery | at least once, best-effort order | ordered within a message group; deduplicated for 5 minutes |
| Grouping | n/a | message group ID = **order ID** |
| Dedup | consumer-side (ADR 0005) | **content-based deduplication** |
| DLQ | standard DLQ | **FIFO** DLQ (required: same type as the source) |
| Throughput | effectively unlimited | capped per API action (higher with batching / high-throughput mode) |

## Consequences

- A resent "authorise" returned the **original MessageId**, and the queue held 5 messages, not 6. A retrying payment client can't create a double charge within the 5-minute window.
- Grouping by order ID keeps each order's steps in sequence while different orders still process in parallel.
- A stuck message blocks later steps of **its own** order only, which is the desired behaviour for money.
- The 5-minute dedup window isn't forever. Downstream payment-provider calls must still carry an idempotency key.
- Using FIFO for all orders was rejected: it would add throughput limits and head-of-line blocking without adding any correctness orders need.
