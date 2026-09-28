{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ConsumeFulfilmentQueueOnly",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "@@FUL_ARN@@"
    },
    {
      "Sid": "RecordFulfilledOrders",
      "Effect": "Allow",
      "Action": "dynamodb:UpdateItem",
      "Resource": "@@TABLE_ARN@@"
    },
    {
      "Sid": "ReadProductCatalog",
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "@@CATALOG_ARN@@"
    }
  ]
}
