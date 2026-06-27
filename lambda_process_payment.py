import boto3
import json
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('olupay-merchants')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    """
    OluPay 2.0 — ProcessPayment Lambda
    Responsibilities:
    - Parse incoming payment request from API Gateway
    - Write transaction record to DynamoDB
    - Queue message to SQS for async notification
    """

    # Handle both API Gateway HTTP calls and Test tab calls
    if 'body' in event:
        body = json.loads(event['body'])
    else:
        body = event

    sender    = body.get('sender')
    recipient = body.get('recipient')
    amount    = float(body.get('amount'))
    reference = body.get('reference', str(uuid.uuid4()))
    timestamp = datetime.utcnow().isoformat()

    # 1. Write transaction to DynamoDB (merchant catalogue)
    table.put_item(Item={
        'MerchantID':       reference,
        'CreatedAt':        timestamp,
        'Sender':           sender,
        'Recipient':        recipient,
        'Amount':           str(amount),
        'Status':           'Completed',
        'MerchantCategory': 'Payment'
    })

    # 2. Send to SQS for async notification processing
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/070340244863/PaymentProcessingQueue',
        MessageBody=json.dumps({
            'reference': reference,
            'sender':    sender,
            'recipient': recipient,
            'amount':    amount,
            'timestamp': timestamp
        })
    )

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type':                 'application/json',
            'Access-Control-Allow-Origin':  '*'
        },
        'body': json.dumps({
            'message':   'Payment processed successfully',
            'reference': reference,
            'timestamp': timestamp,
            'status':    'Completed'
        })
    }