# Fan-out and filtering: one publish, three independent copies

## Why fan-out

On Black Friday, the warehouse, the confirmation emails and the sales dashboard all depended on one order service, so one failure took all three down. With SNS fan-out, checkout publishes **once** to the `ubuntu-orders` topic. SNS delivers a copy into a separate SQS queue for each team. Each queue buffers independently: a slow email service fills only the email queue, and a dead warehouse fleet fills only the fulfilment queue.

Adding a fourth consumer (a loyalty-points service, say) is a new subscription. Checkout doesn't change.

## What I built

| Queue | Subscription filter | Consumer |
|---|---|---|
| `ubuntu-fulfilment` | `{"event_type": ["OrderPlaced"]}` | the EC2 worker fleet |
| `ubuntu-email` | `{"event_type": ["OrderPlaced"]}` | the email service (not built; the queue simply accumulates) |
| `ubuntu-analytics` | none: every event | the analytics team (not built; the queue accumulates) |

Each queue has:

- A **queue policy** allowing `sqs:SendMessage` only from `sns.amazonaws.com` **with `aws:SourceArn` = the `ubuntu-orders` topic**. Without the condition, any SNS topic in any account could write into the queue. The template is [`policies/queue-policy-from-sns.json.tpl`](../policies/queue-policy-from-sns.json.tpl), applied by [`scripts/allow_sns.py`](../scripts/allow_sns.py). It's Allow-only.
- **Raw message delivery** on its subscription. The queue receives the order JSON exactly as published, and SNS message attributes (`event_type`, `order_id`, `sku`) arrive as SQS message attributes. Without it, every consumer would have to unwrap an SNS envelope.

Evidence: [`03`](screenshots/03-step2-filter-policy-applied.png)–[`06`](screenshots/06-step2-analytics-raw-delivery-no-filter.png).

## The proof

I published one `OrderPlaced` and one `OrderCancelled` for `FANOUT-0001`, with no workers running yet:

| Queue | Received | Why |
|---|---|---|
| `ubuntu-fulfilment` | 1 | the cancellation was filtered out |
| `ubuntu-email` | 1 | the cancellation was filtered out |
| `ubuntu-analytics` | 2 | no filter: both events |

Evidence: [`12`](screenshots/12-step5-fan-out-1-1-2.png).

When the first worker booted in step 9, it processed `FANOUT-0001` 11 seconds after its service started. The order had waited safely for a consumer that didn't exist yet ([`24`](screenshots/24-step9-worker-log-session-manager.png)).

At the end of the build the two unconsumed queues held exactly what the design predicts:

- **email: 284** = 1 + 50 + 3 + 200 + 30 `OrderPlaced` events across all runs.
- **analytics: 285** = the same, plus the one cancellation.

That includes the 200 orders published while the entire fulfilment fleet was down. The other teams never noticed the outage ([`36`](screenshots/36-step14-all-measurements.png)).

## Design note: filter changes are eventually consistent

SNS filter-policy changes can take a few minutes to apply fully. I set the filters, then did the polling and FIFO work before running the fan-out proof. By then the filters were in effect, and the first proof came out 1 / 1 / 2. In production, change a filter before you depend on it, not in the same deploy step that starts sending new event types.
