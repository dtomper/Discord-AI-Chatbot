import os
import time
import json
import discord
import requests
import urllib.parse
from hashlib import md5
from webserver import keep_alive

keep_alive()

TOKEN = os.environ['bot_token']

chillmode = False # In case so many requests were sent to Cleverbot that it no longer accepts any
chillmode_start = 0
chillmode_duration = 600

class UserSession():
    def __init__(self, name):
        self.name = name
        self.creation_time = time.time()

        self.session = requests.Session()
        self.lines = [] # History of messages
        self.max_lines = 10 # Max amount of messages to remember (older messages will be removed to save space and time)
        self.session_id = ""

        self.set_XVIS_cookie()

    def set_XVIS_cookie(self):
        # Initialize session by setting XVIS cookie

        url = 'https://www.cleverbot.com/extras/conversation-social-min.js'

        headers = {
            'Host': 'www.cleverbot.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.cleverbot.com/',
            'Dnt': '1',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'close',
        }

        self.session.get(url, headers=headers)
    
    def get_reply(self, message):
        global chillmode, chillmode_start

        if chillmode:
            duration_left = chillmode_duration - (time.time() - chillmode_start)
            if duration_left > 0:
                return {'success': False, 'message': '', 'error': f'Let me chill bro. ({int(duration_left)} seconds left)'}
            else:
                chillmode = False

        if message == "":
            return {'success': False, 'message': '', 'error': 'Say something, don\'t be shy.'}

        url = 'https://www.cleverbot.com/webservicemin'

        headers = {
            'Host': 'www.cleverbot.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.cleverbot.com/',
            'Content-Type': 'text/plain;charset=UTF-8',
            'Origin': 'https://www.cleverbot.com',
            'Dnt': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'close',
        }

        params = {
            'uc': 'UseOfficialCleverbotAPI',
            'ncf': 'V2',
        }

        # Fix message
        message = message.strip().capitalize()
        if message[-1] not in ['.', '?', '!']:
            message += '.'

        # Make request body
        data = 'stimulus=' + urllib.parse.quote_plus(message)
        for i, line in enumerate(self.lines[::-1]):
            data += f'&vText{i+2}=' + urllib.parse.quote_plus(line)
        
        data += '&cb_settings_language=en&cb_settings_scripting=no'

        if self.session_id:
            data += '&sessionid=' + self.session_id
        
        data += '&islearning=1&icognoid=wsf'
        data += '&icognocheck=' + md5(data[7:33].encode()).hexdigest()

        # data = urllib.parse.quote_plus(data)

        # Send request
        response = self.session.post(url, params=params, headers=headers, data=data)

        if response.status_code == 409:
            chillmode = True
            chillmode_start = time.time()

            return {'success': False, 'message': '', 'error': f'Chill mode has been turned ON. Try again after {chillmode_duration} seconds.'}
        
        if response.status_code != 200:
            return {'success': False, 'message': '', 'error': 'Something went wrong, please try again later.'}
        
        reply, self.session_id = response.content.decode().split('\r')[0:2]

        self.lines.append(message)
        self.lines.append(reply)

        self.lines = self.lines[- self.max_lines * 2: ]

        return {'success': True, 'message': reply, 'error': ''}

user_sessions = {}

with open("config.json", "r") as f:
    config = json.load(f)

command_prefix = config['bot-command-prefix']
message_prefix = config['bot-message-prefix']

allowed_channels = config['allowed-channels']
blacklisted_channels = config['blacklisted-channels']

allowed_users = config['allowed-users']
blacklisted_users = config['blacklisted-users']

# If any response is longer than this number, it'll be cropped and will end with ...
max_response_length = 1900 # The current limit set by Discord is 2000, but let's just say 1900 for safety measures

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged in as', self.user)

    async def on_message(self, message):
        if message.author != self.user:
            if message.content.startswith(command_prefix):
                command = message.content[len(command_prefix):].strip().lower()

                if command == "":
                    return
                
                if command == "sessions":
                    if user_sessions == {}:
                        await message.reply(f"```No session is currently active. Say something to start one!```")
                        return

                    response = "```"
                    response += f"Total Active Sessions: {len(user_sessions)}"
                    response += "\n----------\n"
                    response += '\n'.join([usersession.name + f" ({int(time.time() - usersession.creation_time)} seconds ago)" for usersession in user_sessions.values()])

                    if len(response) > max_response_length - 4: # -4 for the \n``` that will be added later
                        response = response[:max_response_length - 4 - 3] + "..."

                    response += "\n```"

                    await message.reply(response)
                    return
                
                if command == "delete_my_session":
                    if message.author.id not in user_sessions:
                        await message.reply("```You have no active to session. Say something to start one!```")
                        return
                    
                    del(user_sessions[message.author.id])

                    await message.reply("```Session successfully deleted!```")
                    return

                if command == "help":
                    help_message = "Here's a list of all commands available:"
                    help_message += "\n----------\n"
                    help_message += f"{command_prefix}help              : Shows this help message.\n"
                    help_message += f"{command_prefix}sessions          : Shows a list of all active sessions.\n"
                    help_message += f"{command_prefix}delete_my_session : Deletes sender's session.\n"

                    await message.reply(f"```{help_message}```")
                    return

                else:
                    await message.reply(f"```Unknown command. Type {command_prefix}help to see all commands available.```")
                    return

            if message.content.startswith(message_prefix):
                if int(message.channel.id) in blacklisted_channels:
                    return
                
                if int(message.author.id) in blacklisted_users:
                    return
                
                if allowed_channels != [] and int(message.channel.id) not in allowed_channels:
                    return
                
                if allowed_users != [] and int(message.author.id) not in allowed_users:
                    return

                if message.author.id not in user_sessions:
                    user_sessions[message.author.id] = UserSession(name = str(message.author))

                cleverbot_message = message.content[len(message_prefix):].strip()
                print("-->", cleverbot_message)
                cleverbot_reply = user_sessions[message.author.id].get_reply(cleverbot_message)
                if cleverbot_reply['success']:
                    print("<--", cleverbot_reply['message'])
                    await message.reply(cleverbot_reply['message'])
                else:
                    print("ERROR:", cleverbot_reply)
                    await message.reply(f"```{cleverbot_reply['error']}```")
                
                return

client = MyClient(intents=discord.Intents.all())
client.run(TOKEN)