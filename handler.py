import json
import logging
import os
import requests

import boto3


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

QUEUE_URL = os.getenv('QUEUE_URL')
SQS = boto3.client('sqs')


def producer(event, context):
    print(event.get('body'))
    status_code = 200
    message = ''

    if not event.get('body'):
        return {'statusCode': 400, 'body': json.dumps({'message': 'No body was found'})}

    try:
        message_attrs = {
            'AttributeName': {'StringValue': 'AttributeValue', 'DataType': 'String'}
        }
        SQS.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=event['body'],
            MessageAttributes=message_attrs,
        )
        message = 'Message accepted!'
    except Exception as e:
        logger.exception('Sending message to SQS queue failed!')
        message = str(e)
        status_code = 500

    return {'statusCode': status_code, 'body': json.dumps({'message': message})}


def consumer(event, context):
    logger.info('Received message: {}'.format(event))
    event_body = json.loads(event.get('Records')[0].get('body'))
    message_body = event_body.get('message_body')
    message_subject = event_body.get('message_subject')
    to_address = event_body.get('to_address')
    sending_domain = os.environ.get('SENDING_DOMAIN')
    if not to_address and not message_body:
        return {'statusCode': 400, 'body': json.dumps({'message': 'sms request requires a message_body and to_number field'})}

    logger.info(f"MESSAGE BODY :==> {message_body}")
    logger.info(f"TO ADDRESS:==> {to_address}")

    # get mailgun api key from env
    mailgun_api_key = os.environ.get('MAILGUN_API_KEY')

    # send mailgun email sending url
    mailgun_api = f"https://api.mailgun.net/v3/{sending_domain}/messages"

    # send email
    response = requests.request(
        "POST",
        mailgun_api,
        auth=("api", mailgun_api_key),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"from": f"Lead Notifier <no-reply@{sending_domain}>",
                "to": [to_address],
                "subject": message_subject,
                "text": message_body}
    )

    logger.info(response.text)
    