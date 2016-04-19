## Slack Standup Bot

The Impact Lab has a channel in Slack, called #standup, where we post our daily to-do/post-mortem info. 

This bot exists to remind those who didn't post a standup message to do so at new each day. 

## Deploying 
This code is designed to be deployed on AWS Lambda. You'll need to configure both a slack API client and incoming webhook for the bot to post to.

## Testing
You can test the bot by running `python main.py`
