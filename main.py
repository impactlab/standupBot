'''
Follow these steps to configure the webhook in Slack:

  1. Navigate to https://<your-team-domain>.slack.com/services/new

  2. Search for and select "Incoming WebHooks".

  3. Choose the default channel where messages will be sent and click "Add Incoming WebHooks Integration".

  4. Copy the webhook URL from the setup instructions and use it in the next section.


Follow these steps to encrypt your Slack hook URL for use in this function:

  1. Create a KMS key - http://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html.

  2. Encrypt the event collector token using the AWS CLI.
     $ aws kms encrypt --key-id alias/<KMS key name> --plaintext "<SLACK_HOOK_URL>"

     Note: You must exclude the protocol from the URL (e.g. "hooks.slack.com/services/abc123").

  3. Copy the base-64 encoded, encrypted key (CiphertextBlob) to the ENCRYPTED_HOOK_URL variable.

  4. Give your function's role permission for the kms:Decrypt action.
     Example:

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1443036478000",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": [
                "<your KMS key ARN>"
            ]
        }
    ]
}
'''
from __future__ import print_function

import boto3
import json
import logging
import requests 
import datetime 

from slackclient import SlackClient
from base64 import b64decode
from urllib2 import Request, urlopen, URLError, HTTPError

ENCRYPTED_SLACK_TOKEN = "CiBVhQSX5nYIrdq5ceR6CokUkwMNrVwB/19yzaVQE3VObRK6AQEBAgB4VYUEl+Z2CK3auXHkegqJFJMDDa1cAf9fcs2lUBN1Tm0AAACRMIGOBgkqhkiG9w0BBwaggYAwfgIBADB5BgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDGgO/qyI+JCNrHKfoAIBEIBM69UzS2OeFrD0xTSMfZJumJX8hvhBejQ7vVPYQMZrRjY+Rax7HrHbA3SUXcznQcLipzUnqxKEf/6f9iD4CoWCmDHzT6dzpXhtBp8CwA=="
ENCRYPTED_HOOK_URL = "CiBVhQSX5nYIrdq5ceR6CokUkwMNrVwB/19yzaVQE3VObRLQAQEBAgB4VYUEl+Z2CK3auXHkegqJFJMDDa1cAf9fcs2lUBN1Tm0AAACnMIGkBgkqhkiG9w0BBwaggZYwgZMCAQAwgY0GCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMd78Kw7APHJ8y5oCAAgEQgGD8tmHEj/KszBdqau89uWktLwp6Az3++0XOcILugA+SGUG5Oq+VC/m7opXHdQGJrr12HYrh4Cez8J6c6jC/hh+TeV8FX0szERtbweONYwRkYEjgQOK9a+is6BtVAlxDv2E="
SLACK_CHANNEL = 'standup'  # Enter the Slack channel to send a message to
SLACK_API_ROOT = "https://slack.com/api/"
HOOK_URL = "https://" + boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_HOOK_URL))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def check_in_date_range(date):
    date = date['ts']
    central_current_time = datetime.datetime.utcnow() - datetime.timedelta(hours=5)
    range = central_current_time - datetime.datetime.fromtimestamp(float(date))
    return range < datetime.timedelta(hours=10)
    


def find_users_missing_standup():
    """Find the users without a message within the last 10 hours in 
    Standup
    """
    token = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_SLACK_TOKEN))['Plaintext']
    sc = SlackClient(token)
    channels = sc.api_call('channels.list')['channels']
    standup = (i for i in channels if i['name'] == SLACK_CHANNEL).next()
    members = standup['members']
    messages = sc.api_call('channels.history', channel=standup['id'])['messages']
    messages_within_last_10_hours = filter(check_in_date_range, messages) 
    users_posted = (i['user'] for i in messages_within_last_10_hours if
                    'user' in i.keys())
    difference = set(members).difference(users_posted)
    return difference

def get_users_name(user_id):
    token = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_SLACK_TOKEN))['Plaintext']
    sc = SlackClient(token)
    return '@' + sc.api_call('users.info',user=user_id)['user']['name']

def main(event, context):
    missing_users = find_users_missing_standup()
    reply_candidates = [get_users_name(user) for user in missing_users]
    logger.info("Reply Candidates %s", reply_candidates)
    msg = 'Missing standups from ' + ', '.join(reply_candidates)
    slack_message = {
        'channel': SLACK_CHANNEL,
        'text': msg
    }

    req = Request(HOOK_URL, json.dumps(slack_message))
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)

if __name__ == '__main__':
    main()
