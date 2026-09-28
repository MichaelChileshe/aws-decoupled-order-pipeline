# Teardown

Run from the repo folder after `source ./env.sh`. There is no `Deny` statement anywhere in this project, so every delete works for the account administrator, in any retry order.

```bash
# 1. Workers first (they hold network interfaces in the subnets)
aws autoscaling delete-auto-scaling-group --auto-scaling-group-name ubuntu-fulfilment-workers --force-delete
aws ec2 wait instance-terminated --filters Name=tag:aws:autoscaling:groupName,Values=ubuntu-fulfilment-workers
aws ec2 delete-launch-template --launch-template-name ubuntu-order-worker

# 2. IAM
aws iam remove-role-from-instance-profile --instance-profile-name ubuntu-order-worker-profile --role-name ubuntu-order-worker-role
aws iam delete-instance-profile --instance-profile-name ubuntu-order-worker-profile
aws iam detach-role-policy --role-name ubuntu-order-worker-role --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam delete-role-policy --role-name ubuntu-order-worker-role --policy-name fulfilment-worker
aws iam delete-role --role-name ubuntu-order-worker-role

# 3. Network
aws ec2 delete-security-group --group-id "$WORKER_SG"
aws ec2 delete-subnet --subnet-id "$SUBNET_A"
aws ec2 delete-subnet --subnet-id "$SUBNET_B"
aws ec2 delete-route-table --route-table-id "$RT_ID"
aws ec2 detach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"
aws ec2 delete-internet-gateway --internet-gateway-id "$IGW_ID"
aws ec2 delete-vpc --vpc-id "$VPC_ID"

# 4. Messaging and data (deleting the topic removes its subscriptions)
aws sns delete-topic --topic-arn "$TOPIC_ARN"
aws sqs delete-queue --queue-url "$FUL_URL"
aws sqs delete-queue --queue-url "$FUL_DLQ_URL"
aws sqs delete-queue --queue-url "$EMAIL_URL"
aws sqs delete-queue --queue-url "$EMAIL_DLQ_URL"
aws sqs delete-queue --queue-url "$ANALYTICS_URL"
aws sqs delete-queue --queue-url "$ANALYTICS_DLQ_URL"
aws sqs delete-queue --queue-url "$PAY_URL"
aws sqs delete-queue --queue-url "$PAY_DLQ_URL"
aws sqs delete-queue --queue-url "$SCRATCH_URL"
aws dynamodb delete-table --table-name ubuntu-fulfilled-orders
aws ssm delete-parameter --name /ubuntu-retail/catalog
```

**Why this order:**

- `--force-delete` terminates the workers and removes the scaling policy and its two CloudWatch alarms.
- The security group and subnets can't be deleted while instance network interfaces still exist, which is why the instances go first.
- Deleting the subnets removes their route-table associations, which lets the route table go.
- Deleted queues can take up to 60 s to disappear from listings, and a queue name can't be reused for 60 s.

## Clean check (after 60 s)

```bash
aws sqs list-queues --queue-name-prefix ubuntu- --query QueueUrls --output text
aws sns list-topics --query "Topics[?contains(TopicArn,'ubuntu-orders')].TopicArn" --output text
aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[?AutoScalingGroupName=='ubuntu-fulfilment-workers'].AutoScalingGroupName" --output text
aws ec2 describe-vpcs --filters Name=tag:Name,Values=ubuntu-orders-vpc --query 'Vpcs[].VpcId' --output text
aws dynamodb list-tables --query "TableNames[?starts_with(@,'ubuntu-')]" --output text
aws iam list-roles --query "Roles[?starts_with(RoleName,'ubuntu-order')].RoleName" --output text
aws cloudwatch describe-alarms --alarm-name-prefix TargetTracking-ubuntu --query 'MetricAlarms[].AlarmName' --output text
```

My result: every query came back empty (the only output was `None` from `list-queues`) ([`37`](screenshots/37-step15-clean-check.png)). The role filter is `ubuntu-order` on purpose, so an unrelated, older `ubuntu-retail-*` CI role doesn't muddy the check.

Cost Explorer confirms the final figure the next day; see [`cost-model.md`](cost-model.md#why-cost-explorer-showed--us000-on-the-day).
