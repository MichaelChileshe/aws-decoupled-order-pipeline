#!/usr/bin/env python3
"""Regenerates docs/architecture.svg + docs/architecture.png using the OFFICIAL AWS Architecture Icons.

The icon pack is not committed (AWS licenses it for diagrams, not redistribution). Download it from
https://aws.amazon.com/architecture/icons/, unzip, then:

    AWS_ICONS_DIR=/path/to/unzipped-icon-package python3 build_architecture.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from awsdiag import Diagram, GREY, INK

MSG, DATA, SCALE, RED, OK = "#E7157B", "#C925D1", "#ED7100", "#D13212", "#1D8102"
d = Diagram(1800, 1120)

d.text(40, 40, "Ubuntu Retail Group — decoupled order pipeline", 19, "bold")
d.text(40, 64, "SNS fan-out  ·  SQS queues + dead-letter queues  ·  FIFO for payments  ·  "
               "EC2 workers scaled on backlog per worker  ·  us-east-1", 13, "normal", GREY)

# checkout (outside AWS)
d.icon("users", 50, 300, 56)
d.text(78, 380, "Checkout", 13, "bold", anchor="middle")
d.text(78, 397, "publishes once", 11.5, "normal", GREY, "middle")
d.icon("users", 50, 895, 56)
d.text(78, 975, "Payment service", 13, "bold", anchor="middle")

d.group("cloud", 160, 95, 1615, 1000, "AWS Cloud")
d.group("region", 180, 135, 1575, 945, "Region  us-east-1")

# SNS topic
d.icon("sns", 240, 296, 64)
d.text(272, 382, "Amazon SNS", 13, "bold", anchor="middle")
d.text(272, 399, "topic ubuntu-orders", 11.5, "normal", GREY, "middle")
d.text(272, 415, "raw message delivery", 11.5, "normal", GREY, "middle")
d.line([(108, 328), (238, 328)], MSG)

# queues: text sits under each icon so the space to the right stays free for lines
queues = [
    (240, "ubuntu-fulfilment", "filter: OrderPlaced", "worker fleet"),
    (520, "ubuntu-email", "filter: OrderPlaced", "email service"),
    (720, "ubuntu-analytics", "no filter (every event)", "analytics team"),
]
QX = 560
for cy, name, filt, consumer in queues:
    d.icon("sqs", QX, cy - 28, 56)
    d.text(QX + 28, cy + 46, f"Amazon SQS  {name}", 13, "bold", anchor="middle")
    d.text(QX + 28, cy + 63, f"visibility 30 s · long polling 20 s → {consumer}", 11.5, "normal", GREY, "middle")
    d.text(QX + 28, cy + 80, "DLQ after 3 receives · kept 14 days", 11.5, "normal", RED, "middle")
    d.line([(304, 328), (400, 328), (400, cy), (QX - 2, cy)], MSG)
    d.label(408, cy - 10, filt, MSG, 11)

# worker VPC
d.group("vpc", 870, 175, 540, 330, "VPC  ubuntu-orders-vpc  10.40.0.0/16")
d.group("public", 890, 220, 500, 265, "2 public subnets (1a, 1b) · SG: no inbound")
d.icon("ec2_autoscaling", 905, 262, 48)
d.text(962, 280, "EC2 Auto Scaling  ubuntu-fulfilment-workers", 12.5, "bold")
d.text(962, 297, "1–4 × t3.micro · IMDSv2 · systemd worker", 11.5, "normal", GREY)
for i, x in enumerate([915, 1030, 1145, 1260]):
    d.icon("ec2_instance", x, 330, 52)
    d.text(x + 26, 400, f"worker {i + 1}", 11.5, "normal", GREY, "middle")
d.text(1140, 430, "receive → check catalog → work → record → THEN delete", 11.5, "bold", INK, "middle")
d.text(1140, 448, "fails → release (visibility 0) → 3 tries → DLQ", 11.5, "normal", RED, "middle")
d.line([(QX + 56, 240), (868, 240)], MSG)
d.label(640, 230, "long-poll, 1 order at a time", MSG, 11)

# data
d.icon("dynamodb", 1500, 205, 56)
d.text(1568, 225, "Amazon DynamoDB", 13, "bold")
d.text(1568, 242, "ubuntu-fulfilled-orders", 11.5, "normal", GREY)
d.text(1568, 258, "process_count shows duplicates", 11.5, "normal", GREY)
d.icon("param_store", 1504, 340, 48)
d.text(1568, 358, "SSM Parameter Store", 13, "bold")
d.text(1568, 375, "/ubuntu-retail/catalog", 11.5, "normal", GREY)
d.line([(1410, 233), (1498, 233)], DATA)
d.line([(1410, 364), (1502, 364)], DATA)

# scaling loop
d.icon("cw_alarm", 1110, 560, 52)
d.text(1175, 578, "Amazon CloudWatch · target tracking", 13, "bold")
d.text(1175, 595, "backlog per worker = visible messages ÷ workers in service", 11.5, "normal", GREY)
d.text(1175, 611, "target 12  (60 s acceptable wait ÷ 5 s per order)", 11.5, "normal", GREY)
d.text(1175, 627, "not CPU — the workers are nearly idle on CPU", 11.5, "normal", GREY)
d.line([(QX + 56, 256), (830, 256), (830, 586), (1108, 586)], SCALE, dashed=True)
d.label(590, 420, "ApproximateNumberOfMessagesVisible", SCALE, 11)
d.line([(1136, 558), (1136, 507)], SCALE)
d.label(1146, 540, "scale 1 ↔ 4", SCALE, 11)

# FIFO payments
d.icon("sqs", QX, 892, 56)
d.text(QX + 68, 912, "Amazon SQS FIFO  ubuntu-payments.fifo", 13, "bold")
d.text(QX + 68, 929, "message group = order ID → authorise, capture, settle in order", 11.5, "normal", GREY)
d.text(QX + 68, 945, "content-based deduplication (5 min) · FIFO DLQ", 11.5, "normal", GREY)
d.line([(108, 922), (QX - 2, 922)], MSG)

# measured + legend
bx, by = 1110, 700
d.box(bx, by, 630, 185, "#D5DBDB", fill="#fff", dashed=False)
d.text(bx + 16, by + 26, "Measured", 13.5, "bold")
d.text(bx + 16, by + 52, "Every worker down, 200 orders published:  200 processed, 0 lost", 13, "bold", OK)
d.text(bx + 16, by + 74, "Poison orders: 3 → DLQ → catalog fixed → redriven → 3 processed, 0 lost", 12, "normal", INK)
d.text(bx + 16, by + 94, "Baseline 50 orders: scaled 1 → 4 workers on backlog, drained in ~6 min", 12, "normal", INK)
d.text(bx + 16, by + 114, "Visibility 2 s (< 5 s work): 7 of 30 orders processed more than once", 12, "normal", RED)
d.text(bx + 16, by + 134, "Fan-out: email received 284 orders, analytics 285 events (incl. 1 cancellation)", 12, "normal", INK)
d.text(bx + 16, by + 156, "Duplicate payment send: SQS returned the original MessageId, depth 5 not 6", 12, "normal", INK)

lx, ly = 1110, 905
d.raw(f'<rect x="{lx}" y="{ly}" width="630" height="100" rx="4" fill="#fff" stroke="#D5DBDB"/>')
d.text(lx + 12, ly + 22, "Legend", 13, "bold")
d.line([(lx + 12, ly + 44), (lx + 62, ly + 44)], MSG)
d.text(lx + 72, ly + 48, "message path (publish, deliver, poll)", 12)
d.line([(lx + 12, ly + 66), (lx + 62, ly + 66)], DATA)
d.text(lx + 72, ly + 70, "worker reads catalog / records processed order", 12)
d.line([(lx + 12, ly + 88), (lx + 62, ly + 88)], SCALE, dashed=True)
d.text(lx + 72, ly + 92, "scaling signal (queue depth → alarm → Auto Scaling)", 12)

here = os.path.dirname(os.path.abspath(__file__))
d.save(os.path.join(here, "..", "architecture.svg"), os.path.join(here, "..", "architecture.png"))
print("wrote docs/architecture.svg and docs/architecture.png")
