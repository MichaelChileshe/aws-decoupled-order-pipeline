# ADR 0006: Public subnets with no inbound access for the lab; private subnets + VPC endpoints for production

**Status:** Accepted (lab) / Proposed (production)
**Context:** Workers need outbound HTTPS to SQS, DynamoDB and SSM. Nothing ever needs to connect *to* them.

## Decision (lab)

- Two public subnets in two AZs with a route to an internet gateway; workers get public IPv4 addresses for outbound traffic.
- The security group has **no inbound rules**. Administration is Session Manager only: no SSH, no key pair, no open port.
- IMDSv2 is required on every worker. The instance role allows one queue, one table and one parameter.

## Why not private subnets in the lab

Private subnets need either a NAT gateway (~US$32/month plus data processing) or four interface endpoints (SQS, SSM, ssmmessages, ec2messages) plus a DynamoDB gateway endpoint. For a same-day build, that cost buys no extra evidence, because the security group already refuses all inbound traffic.

## Production

- Private subnets only; no public IPs.
- Gateway endpoint for DynamoDB (free); interface endpoints for SQS and the three Session Manager services, the same pattern as `aws-private-connectivity-endpoints`.
- Optionally a queue policy condition on `aws:SourceVpce`, so the fulfilment queue can only be consumed from inside the worker VPC. It would need to be Allow-scoped or carefully teardown-tested, as that earlier project showed.
