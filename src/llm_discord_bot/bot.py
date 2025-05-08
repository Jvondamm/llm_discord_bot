import re
import random
import os
import json
from platform import python_version, system, release

from discord import Intents, Message
from discord import __version__ as __discord_version__
from discord.ext import commands
from dotenv import load_dotenv

import logging

logger = logging.getLogger("BOT")

load_dotenv()
intents = Intents.all()


def remove_id(text):
    """Removes discord IDs from strings"""
    return re.sub(r'<@\d+>', '', text)

def split_message(message):
    """Split messages into 2000 character chunks (discord's message limit)"""
    return [message[i:i + 2000] for i in range(0, len(message), 2000)]


def format_prompt(prompt, user, question, history):
    formatted_prompt = prompt.replace("{user}", user)
    formatted_prompt = formatted_prompt.replace("{question}", question)
    formatted_prompt = formatted_prompt.replace("{history}", history)
    return formatted_prompt


def filter_mentions(text):
    """Remove any broadcasts"""
    pattern = r'[@]?(\b(here|everyone|channel)\b)'
    filtered_text = re.sub(pattern, '', text)
    return filtered_text


class Bot(commands.Bot):
    def __init__(self, llm, config_file):
        self.prefix: str = os.getenv("DISCORD_PREFIX")
        self.llm = llm
        self.llm_config: json = None

        super().__init__(
            command_prefix=commands.when_mentioned_or(self.prefix),
            intents=intents,
            help_command=None,
        )
        self.load_config(config_file)

    def load_config(self, config_file):
        with open(config_file) as f:
            self.llm_config = json.load(f)

    async def setup_hook(self) -> None:
        """
        Logon message
        """
        logger.info(f"Logged in as {self.user.name}")
        logger.info(f"discord.py API version: {__discord_version__}")
        logger.info(f"Python version: {python_version()}")
        logger.info(
            f"Running on: {system()} {release()} ({os.name})"
        )

    async def on_message(self, message: Message):
        """Triggers on any message received to the server (guild)"""

        async def respond(message, history_text):
            """The response logic"""
            async with message.channel.typing():
                prompt = format_prompt(self.llm_config["question_prompt"], message.author.name, remove_id(message.content),
                                       history_text)
                bot_response, relevant_docs = self.llm.response(prompt, self.llm_config["identity"])
                filtered_bot_response = filter_mentions(bot_response)
                message_chunks = split_message(filtered_bot_response)
                for chunk in message_chunks:
                    await message.channel.send(chunk)
                if relevant_docs:
                    await message.channel.send("Sources:\n")
                    for chunk in split_message(relevant_docs):
                        await message.channel.send(chunk)

        # Never reply to yourself
        if message.author == self.user:
            return

        # Grab the channel history so we can add it as context for replies, makes a nice blob of data
        history_list = []
        channel_history = [user async for user in message.channel.history(limit=self.llm_config["history_lines"] + 1)]
        for history in channel_history:
            if remove_id(history.content) != remove_id(message.content):
                history_list.append(history.author.name + ": " + remove_id(history.content))

        # Reverse the order of the history so it looks more like the chat log
        # Then join it into a single text blob
        history_list.reverse()
        history_text = '\n'.join(history_list)

        if self.user.mentioned_in(message):
            logger.info(f"Direct message received from author={message.author.name}, generating response...")
            await respond(message, history_text)
        elif any (trigger in message.content for trigger in self.llm_config["triggers"]) and \
               random.random() <= float(self.llm_config["trigger_level"]):
            logger.info(f"Found trigger word in channel message from author={message.author.name} and dice-rolled above the trigger-level, generating response...")
            await respond(message, history_text)
