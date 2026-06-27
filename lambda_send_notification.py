import boto3
import json

sns = boto3.client('sns')

def lambda_handler(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        
        amount    = float(body.get('amount', 0))
        sender    = body.get('sender')
        recipient = body.get('recipient')
        reference = body.get('reference')

        # Send SNS notification
        sns.publish(
            TopicArn='arn:aws:sns:us-east-1:070340244863:OluTech-Alerts',
            Subject='OluPay Payment Notification',
            Message=(
                f'Payment confirmed!\n'
                f'Ref: {reference}\n'
                f'From: {sender}\n'
                f'To: {recipient}\n'
                f'Amount: NGN {amount:,.2f}'
            )
        )

    return {'statusCode': 200}