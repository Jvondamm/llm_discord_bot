from __future__ import annotations
import discord
import re
import random
import json
import sys

from discord import Member
from dotenv import load_dotenv
import os


from llm import Llm
import logging

logger = logging.getLogger("BOT")

load_dotenv()

# Load the llm config from the json file provided on command line
with open(config, 'r') as file:
    llm_config = json.load(file)

load_dotenv()
# Load the identity from the json file provided on command line
bot_file = sys.argv[2]
with open(bot_file, 'r') as file:
    bot_config = json.load(file)

# Configure discord intent for chatting
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

llama = llm(model_path=llm_config["model"])

# Removes discord IDs from strings
def remove_id(text):
    return re.sub(r'<@\d+>', '', text)

class Bot:
    # Remove any broadcasts
    def filter_mentions(text):
        pattern = r'[@]?(\b(here|everyone|channel)\b)'
        filtered_text = re.sub(pattern, '', text)
        return filtered_text


    def format_prompt(prompt, user, question, history):
        formatted_prompt = prompt.replace("{user}", user)
        formatted_prompt = formatted_prompt.replace("{question}", question)
        formatted_prompt = formatted_prompt.replace("{history}", history)
        return formatted_prompt


    # Split messages into 2000 character chunks (discord's message limit)
    def split_message(message):
        return [message[i:i + 2000] for i in range(0, len(message), 2000)]


    @bot.event
    async def on_ready():
        logger.info(f'Bot logged in as {bot.user.name}')


    @bot.event
    async def on_message(message):
        """Triggers on any message received to the server (guild)"""

        async def respond(message, history_text):
            """The response logic"""
            async with message.channel.typing():
                prompt = format_prompt(bot_config["question_prompt"], message.author.name, remove_id(message.content),
                                       history_text)
                bot_response = filter_mentions(llama.response(prompt, bot_config["identity"]))
                message_chunks = split_message(bot_response)
                for chunk in message_chunks:
                    await message.channel.send(chunk)

        # Never reply to yourself
        if message.author == bot.user:
            return

        # Grab the channel history so we can add it as context for replies, makes a nice blob of data
        history_list = []
        channel_history = [user async for user in message.channel.history(limit=bot_config["history_lines"] + 1)]
        for history in channel_history:
            if remove_id(history.content) != remove_id(message.content):
                history_list.append(history.author.name + ": " + remove_id(history.content))

        # Reverse the order of the history so it looks more like the chat log
        # Then join it into a single text blob
        history_list.reverse()
        history_text = '\n'.join(history_list)

        if bot.user.mentioned_in(message):
            logger.info(f"Direct message received from author={message.author.name}, generating response...")
            await respond(message, history_text)
        elif any (trigger in message.content for trigger in bot_config["triggers"]) and \
               random.random() <= float(bot_config["trigger_level"]):
            logger.info(f"Found trigger word in channel message from author={message.author.name} and dice-rolled above the trigger-level, generating response...")
            await respond(message, history_text)

# Run the main loop
bot.run(bot_config["discord_token"])