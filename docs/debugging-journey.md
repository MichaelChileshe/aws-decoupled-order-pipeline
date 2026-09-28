# Debugging journey

The pipeline did what it was designed to do every time. These are the moments where what I saw didn't match what I expected, and what each one taught me.

---

## 1 · How I learned to chain commands into one sequence

**What happened:** to demonstrate the visibility timeout, I sent one message, received it with a **5 s** visibility timeout, then received again straight away, expecting `None` because the message should still be hidden. I ran each command on its own, reading the output and then writing the next command.

**What I saw:** the second receive got the message, and the third showed a receive count of **3**, not 2 ([`08`](screenshots/08-step3-visibility-timeout-message-returns.png)).

```
cb977025-...    1      <- receive #1, hidden for 5 s
cb977025-...           <- receive #2: expected None, got the message
cb977025-...    3      <- receive #3: count 3, not 2
```

**Why:** SQS was right. My timing was the variable. The time I spent between receive #1 and receive #2 was longer than 5 s, so the message was already visible again. Receive #2 took it with the queue's default 30 s timeout, and by the time I ran receive #3 even that had expired.

**What it still proved:** the same MessageId came back every time and the receive count kept climbing. Receiving never removed the message; only deleting would have.

**What I changed:** I started combining related commands into a single sequence, so they execute back to back with the waits built in instead of depending on how quickly I move between them:

```bash
aws sqs receive-message --queue-url "$SCRATCH_URL" --wait-time-seconds 5 --visibility-timeout 5 ... \
  && aws sqs receive-message --queue-url "$SCRATCH_URL" --wait-time-seconds 2 ... \
  && sleep 4 \
  && aws sqs receive-message --queue-url "$SCRATCH_URL" --wait-time-seconds 5 --visibility-timeout 5 ...
```

- `&&` runs the next command only if the previous one succeeded, so a failure stops the chain instead of carrying on against broken state.
- The `sleep` is part of the sequence, so the timing is exact and repeatable.

I used the same habit for the rest of the build: scale the fleet to zero, `sleep 90`, then confirm `0 0 0`; publish 200 orders, `sleep 20`, then read the queue depths; change the visibility timeout, then read it back. Each drill became one deliberate sequence. It ran exactly as designed and took a fraction of the time.

---

## 2 · Peeking with visibility 0 returns the same message again and again

**What happened:** to look inside the fulfilment DLQ without hiding its messages from the redrive, I received with `--visibility-timeout 0 --max-number-of-messages 10`.

**What I saw:** one call returned `PS6-0003` **ten times**, with its receive count going 4, 5, 6 … 13 ([`27`](screenshots/27-step11-dlq-peek-receive-counts.png)).

**Why:** with visibility 0, a message is visible again the instant it's handed out, so SQS can return it repeatedly within one batch. Every hand-out counts as a receive. The DLQ still held all 3 messages; the redrive moved 3.

**Why it matters:** on the DLQ this was harmless, because a DLQ has no redrive policy of its own. On a **source** queue with `maxReceiveCount` 3, the same "harmless peek" would push a message into the DLQ by itself. The console's "poll for messages" counts the same way. Lesson: never peek at a live queue casually.

---

## 3 · The drain watcher went quiet for 39 minutes

**What happened:** during the outage drill, `watch_drain.py` printed a line every ~19 s up to 09:44:55, then nothing until 10:24:10. It finished with "DRAINED after 47m54s" ([`30`](screenshots/30-step12-recovery-scale-out-drain.png)).

**Why:** the script polls in a loop. While my laptop sat idle, the terminal session stopped running it. The queue kept draining; the observer didn't.

**What I did:** I didn't report 47m54s. I worked out the drain from the last measured rate (146 → 64 in 3m12s, about 25 orders a minute) as **about 11 minutes**, and checked it against a second, independent clock: the scale-in alarm, which needs 15 low minutes and fired at 10:02:41. The lesson for any metric in a write-up: know what your measuring tool was doing while you weren't looking.

---

## 4 · The trap didn't do everything I predicted

**What I predicted:** with visibility 2 s and 5 s of work, duplicates plus some good orders pushed into the DLQ.

**What happened:** 7 duplicates out of 30, and **0** in the DLQ.

**Why:** a message reaches the DLQ on its 4th receive. With only 3 workers, all busy most of the time, there was rarely a free worker to take a reappearing message a 4th time. I recorded what actually happened rather than what I had predicted. The risk is real, it just needs more idle consumers than I had.

---

## 5 · Cost Explorer said -US$0.00 on build day

**What I saw:** Cost Explorer showed `-US$0.00` for 27–28 September, right after teardown ([`38`](screenshots/38-step15-cost-explorer-same-day.png)).

**Why:** Cost Explorer isn't real-time. Billing data is processed in batches and refreshed at least once every 24 hours, so same-day EC2 usage normally appears the next day. The small, expected charges are listed in [`cost-model.md`](cost-model.md). The screenshot proves nothing was left running and billing, not that the build was free.
