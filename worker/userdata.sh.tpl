#!/bin/bash
# Boot script for every fulfilment worker. Installs the worker as a systemd service so it
# starts on boot and restarts itself if it ever crashes.
set -euo pipefail

cat > /usr/local/bin/order-worker.sh <<'WORKER'
#!/bin/bash
# Ubuntu Retail fulfilment worker: long-poll the queue, process one order, record it, THEN delete it.
QUEUE_URL="@@FUL_URL@@"
TABLE="ubuntu-fulfilled-orders"
CATALOG_PARAM="/ubuntu-retail/catalog"
PROCESS_SECONDS=5
export AWS_DEFAULT_REGION="@@REGION@@"

TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
log() { echo "$(date -u +%H:%M:%S) $*"; }
log "worker $INSTANCE_ID started"

while true; do
  MSG=$(aws sqs receive-message --queue-url "$QUEUE_URL" --max-number-of-messages 1 --wait-time-seconds 20 \
          --message-attribute-names All \
          --query 'Messages[0].[ReceiptHandle, MessageAttributes.order_id.StringValue, MessageAttributes.sku.StringValue]' \
          --output text)
  RC=$?
  if [ $RC -ne 0 ]; then log "receive failed (rc=$RC), retrying in 5s"; sleep 5; continue; fi
  if [ -z "$MSG" ] || [ "$MSG" = "None" ]; then continue; fi

  RECEIPT=$(printf '%s' "$MSG" | cut -f1)
  ORDER_ID=$(printf '%s' "$MSG" | cut -f2)
  SKU=$(printf '%s' "$MSG" | cut -f3)

  CATALOG=$(aws ssm get-parameter --name "$CATALOG_PARAM" --query Parameter.Value --output text)
  if ! printf ',%s,' "$CATALOG" | grep -q ",$SKU,"; then
    log "FAILED $ORDER_ID: $SKU is not in the catalog. Not deleting - it will retry, then go to the DLQ"
    aws sqs change-message-visibility --queue-url "$QUEUE_URL" --receipt-handle "$RECEIPT" --visibility-timeout 0 > /dev/null
    continue
  fi

  sleep "$PROCESS_SECONDS"   # stands in for pick, pack and label

  NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if aws dynamodb update-item --table-name "$TABLE" \
       --key "{\"order_id\":{\"S\":\"$ORDER_ID\"}}" \
       --update-expression "ADD process_count :one SET item_sku = :sku, worker_id = :w, processed_at = :t" \
       --expression-attribute-values "{\":one\":{\"N\":\"1\"},\":sku\":{\"S\":\"$SKU\"},\":w\":{\"S\":\"$INSTANCE_ID\"},\":t\":{\"S\":\"$NOW\"}}" > /dev/null; then
    aws sqs delete-message --queue-url "$QUEUE_URL" --receipt-handle "$RECEIPT" > /dev/null
    log "OK $ORDER_ID ($SKU)"
  else
    log "FAILED to record $ORDER_ID - releasing it for another try"
    aws sqs change-message-visibility --queue-url "$QUEUE_URL" --receipt-handle "$RECEIPT" --visibility-timeout 0 > /dev/null
  fi
done
WORKER
chmod +x /usr/local/bin/order-worker.sh

cat > /etc/systemd/system/order-worker.service <<'UNIT'
[Unit]
Description=Ubuntu Retail order fulfilment worker
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/order-worker.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now order-worker.service
