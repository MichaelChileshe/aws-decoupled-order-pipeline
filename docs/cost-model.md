# Cost model

## What this build cost

| Item | Usage | Approx. cost (us-east-1 list price) |
|---|---|---|
| EC2 t3.micro workers | 1–4 instances over ~1.75 h, roughly 5 instance-hours at US$0.0104/h | ~US$0.05 |
| Public IPv4 addresses | ~5 address-hours at US$0.005/h | ~US$0.03 |
| SNS | a few hundred publishes (PublishBatch) + SQS deliveries | free tier |
| SQS | a few thousand requests, long polling | free tier |
| DynamoDB on-demand | ~300 writes, a few scans | < US$0.01 |
| SSM Parameter Store | standard parameter | free |
| CloudWatch | 2 target-tracking alarms for a few hours; ASG group metrics are free | < US$0.01 |
| **Total** | | **well under US$0.10** |

## Why Cost Explorer showed `-US$0.00` on the day

Cost Explorer isn't a live meter. AWS processes billing data in batches and refreshes Cost Explorer at least once every 24 hours, so today's usage usually appears tomorrow. The same-day screenshot ([`38`](screenshots/38-step15-cost-explorer-same-day.png)) shows what had been processed by then, not the final figure.

How I use the two checks together:

- **Same day, the clean check** ([`37`](screenshots/37-step15-clean-check.png)) proves nothing is still running. That's what stops the bill growing.
- **Next day, Cost Explorer** confirms the few cents above landed as expected. Anything bigger would point at a leftover resource.

## Running this for real

| Cost driver | Lab | Production thinking |
|---|---|---|
| Workers | on-demand t3.micro, public IP | **Spot** instances: a terminated worker loses nothing, because its message simply reappears. Private subnets + VPC endpoints instead of public IPs |
| Idle polling | long polling (20 s) | long polling: an idle worker makes ~4,300 receives a day instead of ~170,000 with short polling |
| Queue requests | single messages | batch receive/delete (up to 10 per call) cuts request charges ~10× |
| Scaling | 1–4 on backlog | the same policy, plus a scheduled pre-scale before known peaks |
| NAT | none | if private subnets are used, **VPC endpoints** for SQS/DynamoDB/SSM avoid a NAT gateway (~US$32/month + data) |
