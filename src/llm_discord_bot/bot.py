import re
import random
import os
import json
from platform import python_version, system, release

from discord import Intents, Message, Embed, Object
from discord import __version__ as __discord_version__
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv

import logging

from src.utils import format_prompt, filter_mentions, split_message, remove_id

logger = logging.getLogger("BOT")

load_dotenv()
intents = Intents.default()
intents.message_content = True


class Bot(commands.Bot):
    def __init__(self, llm, config_file):
        self.prefix: str = os.getenv("DISCORD_PREFIX")
        self.llm = llm
        self.llm_config: json = None
        self.guild = Object(id=os.getenv("DISCORD_GUILD_ID"))

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.load_config(config_file)

    def load_config(self, config_file):
        with open(config_file) as f:
            self.llm_config = json.load(f)


    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )

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
        await self.load_cogs()
        try:
            synced = await self.tree.sync(guild=self.guild)
            logger.info(f"Synced {len(synced)} commands to guild {self.guild.id}")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")

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
                    for doc in relevant_docs:
                        for chunk in split_message(doc):
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

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )

    async def on_command_error(self, context: Context, error) -> None:
        """
        The code in this event is executed every time a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            embed = Embed(
                description="You are not the owner of the bot!", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = Embed(
                title="Error!",
                # We need to capitalize because the command arguments have no capital letter in the code and they are the first word in the error message.
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error
