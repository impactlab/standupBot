#!/bin/bash

set -e 

zip -r slackbot.zip . 
aws s3 sync . s3://slackstandup
