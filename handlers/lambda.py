import sys
import time
import json
import logging
from slackclient import SlackClient
try:
    from config import *
except:
    from handlers.config import *

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def merge_send_list(event):
    slack_client = SlackClient(slack_bot_token)
    logger.info('Creating a list of channels and people to send message to')
    send_list = set()
    if event.get('channels') != None:
        logger.info('User has passed channels as a parameter')
        for item in event['channels']:
            logger.debug("Adding channel {}".format(item))
            send_list.add(item)
    if event.get('users') != None:
        logger.info('User has passed users as a parameter')
        logger.info("Getting user info from Slack")
        user_data = slack_client.api_call('users.list')
        for item in user_data['members']:
            real_name = item.get('real_name')
            if real_name != None and (real_name in event['users']):
                logger.debug("Adding @{} to send_list".format(item['name']))
                send_list.add('@'+ item['name'])
            elif item['name'] in event['users']:
                logger.debug("Adding @{} to send_list".format(item['name']))
                send_list.add('@'+ item['name'])
    logger.info("Send list is:")
    logger.info(send_list)
    return send_list

def make_message(event):
    message = ""
    snippet = 0
    if event.get("snippet") != None:
        logger.info("Adding code snippet")
        message = "```" + event['snippet'] + "```"
        snippet = 1
    if event.get("message") != None:
        logger.info("Adding message")
        if snippet:
            message = message + '\n' + event['message']
        else:
            message = event['message']
    return message


def send_message(recipient, message):
    slack_client = SlackClient(slack_bot_token)
    logger.info("Sending message to {}".format(recipient))
    response = slack_client.api_call('chat.postMessage', channel=recipient, text=message, as_user=True)
    if not(response['ok']):
        logger.info("Could not send message to {}".format(recipient))
        logger.debug(response)
        tstamp = int(time.time())
        failure_message = "[{}] Could not send message to *{}*\nSlack Error:```{}```\nOriginal message for reference:\n".format(tstamp, recipient, response)
        slack_client.api_call('chat.postMessage', channel=error_channel, text="---"*12, as_user=True)
        slack_client.api_call('chat.postMessage', channel=error_channel, text=failure_message+message, as_user=True)
    else:
        logger.info("Message successfully sent!")
    

def response_command_handler(command, channel):
    logger.info("Command: {}".format(str(command)))
    logger.info("Response is going to: {}".format(channel))
    slack_client = SlackClient(slack_bot_token)
    if command[0] == "help":
        logger.info("Command help executed")
        slack_client.api_call('chat.postMessage', channel=channel, text=help_message, as_user=True)
    else:
        logger.info("Unknown command to yoda")
        bad_command_message = "Invalid command: ```yoda {}```\nThat is why you fail.".format(' '.join(command))
        slack_client.api_call('chat.postMessage', channel=channel, text=bad_command_message, as_user=True)


def response_handler(event):
    event = event['body']
    logger.info(event)
    event = json.loads(event)
    if event.get('challenge') != None:
        return {"statusCode": 200, "body": event['challenge']}
    slack_event = event['event']
    response_channel = slack_event['channel']
    received_message = slack_event['text']
    logger.debug("text: {} \nsent by {}".format(received_message, response_channel))
    if received_message.split(' ')[0] == "yoda":
        logger.info("Message sent to a channel with yoda in it")
        command = received_message.split(' ')
        response_command_handler(command[1:], response_channel)
    else:
        logger.info("Message not for yoda. Nothing to do.")
    return {"statusCode": 200}

def request_handler(event):
    slack_client = SlackClient(slack_bot_token)
    logger.info('Yoda is handling a request.')
    if event.get("users") == None and event.get("channels") == None:
        tstamp = int(time.time())
        error_message = "[{}] Bad call to yoda, angry he is. No users or channels provided.".format(tstamp)
        logger.info(error_message)
        slack_client.api_call('chat.postMessage', channel=error_channel, text="---"*12, as_user=True)
        slack_client.api_call('chat.postMessage', channel=error_channel, text=error_message, as_user=True)
        return {"statusCode": 400, "body": error_message}
    if event.get("snippet") == None and event.get("message") == None:
        tstamp = int(time.time())
        error_message = "[{}] Bad call to yoda, angry he is. No message or snippet provided.".format(tstamp)
        logger.info(error_message)
        slack_client.api_call('chat.postMessage', channel=error_channel, text="---"*12, as_user=True)
        slack_client.api_call('chat.postMessage', channel=error_channel, text=error_message, as_user=True)
        return {"statusCode": 400, "body": error_message}
    logger.info("Minimum parameters provided")
    send_list = merge_send_list(event)
    message = make_message(event)
    for recipient in send_list:
        logger.info("Preparing message for {}".format(recipient))
        send_message(recipient, message)
    return {"statusCode": 200}


def lambda_handler(event, context):
    logger.info('Yoda has been awakened')
    if event.get('body') == None:
        logger.info("Yoda is sending a message")
        return request_handler(event)
    else:
        logger.info("Yoda is dealing with a message sent to it.")
        return response_handler(event)

help_message = """
Yoda I am, teach you I will.

Invoke me as a lambda by calling the function: *your function name* and passing it a JSON object defined bellow, as the payload:
```
{
    "message": "Sample Message",
    "snippet": "Pass your code snippet/stack traces/logs here (as a string)",
    "users": ["Dhruv Jauhar", "sauce-monster", "John Doe", "cool-nickname93"],
    "channels": ["development", "general", "channel-name"]

}
```
Required parameters:
(message ^ snippet) & (users ^ channels) where users can be defined by their nickname or real name
Things to keep in mind: 
(•) In python json.dumps the above dict and in js, stringify the JSON and then pass it to the payload.
(•) Yoda can only post to channels he is invited to, before asking him to a post to channel he is not in, invite him to the channel.
(•) Duplicates in users and channels are removed.
(•) Join #slack-bot-errors channel, messages that could not be sent are sent here with additional information.
"""