{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowOrdersTopicOnly",
      "Effect": "Allow",
      "Principal": { "Service": "sns.amazonaws.com" },
      "Action": "sqs:SendMessage",
      "Resource": "@@QUEUE_ARN@@",
      "Condition": { "ArnEquals": { "aws:SourceArn": "@@TOPIC_ARN@@" } }
    }
  ]
}
