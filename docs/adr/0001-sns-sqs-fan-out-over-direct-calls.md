# ADR 0001: SNS fan-out to per-team SQS queues instead of direct calls

**Status:** Accepted
**Context:** On Black Friday, checkout called the order service synchronously, and the warehouse, email and analytics depended on that same service. When it failed for 38 minutes, 1,200 orders were lost and three teams went dark at once.

## Options considered

| Option | Verdict |
|---|---|
| Keep synchronous calls, add retries in checkout | ❌ Retries against a dead service just fail more slowly. The customer is still waiting, and still gives up |
| One shared queue that every team polls | ❌ One message goes to one consumer. Teams would steal each other's messages, or need a hand-rolled copy step |
| **SNS topic → one SQS queue per team** | ✅ Chosen |
| EventBridge bus → per-team targets | ⚠️ Richer routing and schema discovery, but more than a three-consumer fan-out needs today. It's the natural next step as event types multiply |

## Decision

- Checkout publishes once to the SNS topic `ubuntu-orders`, with `event_type`, `order_id` and `sku` as message attributes.
- Each team has its own SQS queue subscribed with **raw message delivery**. Fulfilment and email filter to `OrderPlaced`; analytics receives everything.
- Each queue policy allows `sqs:SendMessage` only from `sns.amazonaws.com` with `aws:SourceArn` = the topic.

## Consequences

- An order is durable as soon as SNS accepts it. Consumers can be down for days (4-day retention) without loss. I proved this with the whole fulfilment fleet at zero while 200 orders arrived: 200 processed, 0 lost.
- Teams fail independently. During the fulfilment outage, email and analytics kept receiving every order (284 and 285 messages by the end).
- A new consumer is a new subscription, not a change to checkout.
- Delivery is at least once, so every consumer must tolerate duplicates (ADR 0005).
- Filter-policy changes are eventually consistent (minutes), so filters are set before they're relied on.
