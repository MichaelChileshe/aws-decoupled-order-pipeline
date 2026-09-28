# Reliability drills: poison messages, a full outage, and the visibility trap

Every drill is measured the same way. Each worker records each processed order in DynamoDB with `ADD process_count 1` and deletes the SQS message **only after** that write succeeds. [`scripts/count_orders.py`](../scripts/count_orders.py) reports processed, **lost** and **processed more than once** for each run.

---

## Drill 1 · Poison messages: DLQ, fix, redrive

**Scenario:** a new console, `SKU-PS6`, goes on sale before the warehouse catalog is updated. Orders for it can't be fulfilled yet.

**What the worker does:** it checks the SKU against the SSM parameter `/ubuntu-retail/catalog`. If the SKU is unknown, it logs `FAILED`, sets the message's visibility to 0 (retry now, not in 30 s), and does **not** delete it. After the 3rd receive, SQS moves the message to `ubuntu-fulfilment-dlq` (`maxReceiveCount` 3).

**Result:**

1. Three `PS6` orders published; 60 s later, `ubuntu-fulfilment-dlq` held **3** ([`26`](screenshots/26-step11-poison-orders-in-dlq.png)). The healthy queue kept flowing the whole time.
2. I peeked at the DLQ to confirm what was parked ([`27`](screenshots/27-step11-dlq-peek-receive-counts.png)). See the note in [`debugging-journey.md`](debugging-journey.md#2--peeking-with-visibility-0-returns-the-same-message-again-and-again).
3. Fixed the cause: added `SKU-PS6` to the catalog (parameter version 2).
4. `aws sqs start-message-move-task --source-arn <DLQ ARN>` returned `COMPLETED 3`. With no destination given, SQS sends messages back to their original queue. Redriven messages get a new message ID and enqueue time, so they get a fresh set of 3 attempts.
5. `count_orders PS6 3`: **3 processed, 0 lost** ([`28`](screenshots/28-step11-catalog-fix-redrive-zero-lost.png)).

**Lesson:** "failed" and "lost" are different things. The DLQ turned a data-quality problem into a queue of work waiting for a fix.

---

## Drill 2 · Every worker down, 200 orders arrive

**Scenario:** the Black Friday incident, replayed. Last year this failure lost 1,200 orders.

| Time (UTC) | Event | Evidence |
|---|---|---|
| ~09:32 | `update-auto-scaling-group --min-size 0 --desired-capacity 0`; 90 s later: `0 0 0` | [`29`](screenshots/29-step12-fleet-at-zero-200-orders-waiting.png) |
| 09:34:03 | `publish_orders.py BF 200`. Fulfilment: **200 waiting, 0 in flight**. Email 254, analytics 255: the other teams kept receiving | [`29`](screenshots/29-step12-fleet-at-zero-200-orders-waiting.png) |
| 09:36:35 | min 1 / desired 1: the fleet comes back | [`30`](screenshots/30-step12-recovery-scale-out-drain.png) |
| 09:40:47 | desired capacity → **4** (backlog ≈ 177 per worker vs target 12) | [`30`](screenshots/30-step12-recovery-scale-out-drain.png), [`31`](screenshots/31-step12-scaling-activities-200-processed-0-lost.png) |
| 09:41:06 | 4 workers in service; queue falling ~25 orders a minute | [`30`](screenshots/30-step12-recovery-scale-out-drain.png) |
| ~09:47 | queue empty (estimated, below) | |
| 10:02:41 | `AlarmLow` fires; fleet scales back to 1 | [`32`](screenshots/32-step12-alarmlow-scale-in.png) |

**Result: `count_orders BF 200` → 200 processed, 0 lost, 0 duplicates, 4 workers** ([`31`](screenshots/31-step12-scaling-activities-200-processed-0-lost.png)).

**Drain time, honestly.** My `watch_drain.py` stopped polling between 09:44:55 (64 orders left) and 10:24:10, while my laptop sat idle, so the "47m54s" it printed is not the drain time. The last measured stretch went from 146 to 64 in 3m12s, about 25 orders a minute with 4 workers, which leaves ~2.5 minutes for the final 64. So the queue drained **about 11 minutes after recovery**. The scale-in alarm agrees independently: `AlarmLow` needs 15 consecutive low minutes and fired at 10:02:41, so the backlog was low by about 09:47. I report this as an estimate rather than a measurement.

---

## Drill 3 · The visibility timeout trap

**Scenario:** someone "tunes" the queue and sets the visibility timeout below the processing time. No error is raised anywhere.

**Setup:** 3 workers in service; `VisibilityTimeout=2` on `ubuntu-fulfilment` (each order takes 5 s); `publish_orders.py VIS 30`.

**What happens:** worker A receives an order and starts its 5 s of work. At 2 s the order reappears and worker B takes it; at 4 s, possibly worker C. Each one records the order.

**Result** ([`33`](screenshots/33-step13-visibility-2s-duplicates.png), [`34`](screenshots/34-step13-duplicates-and-depths.png)):

```
run VIS: expected 30 | processed 30 | LOST 0 | processed more than once 7 | workers used 3
duplicates: VIS-0002 x2, VIS-0006 x2, VIS-0019 x2, VIS-0020 x2, VIS-0021 x2, VIS-0025 x3, VIS-0029 x3
```

- **7 of 30 orders processed more than once**, 2 of them three times. In a warehouse, that's two or three parcels for one order.
- For contrast, at the correct 30 s timeout the same code processed **254 orders with 0 duplicates** (runs FANOUT, BASE, PS6 and BF).
- **I expected DLQ spill-over too, and there was none (DLQ 0).** A message only reaches the DLQ on its 4th receive. With all 3 workers busy most of the time, there was rarely an idle worker free to receive a reappearing message a 4th time. With more workers, or longer processing, perfectly good orders would have been dead-lettered as well.

**The fix** ([`35`](screenshots/35-step13-fix-visibility-and-purge.png)): visibility back to 30 s, DLQ purged, fleet back to 1. The two production rules are in [ADR 0005](adr/0005-visibility-timeout-sizing-and-idempotent-consumers.md):

1. Set the visibility timeout above the worst-case processing time. For long or variable jobs, extend it while working (`ChangeMessageVisibility` as a heartbeat).
2. Make the consumer idempotent: a conditional write (`attribute_not_exists(order_id)`) that skips an order already processed. My worker uses `ADD` on purpose, so duplicates are counted instead of hidden.
