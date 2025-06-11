import asyncio
import os
import json
from pathlib import Path
from platform import python_version, system, release

from discord import Intents, Message, Embed, Object
from discord import __version__ as __discord_version__
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv

import logging

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from transformers import pipeline

from llm_discord_bot.utils import filter_mentions, split_message, remove_id

logger = logging.getLogger("BOT")

load_dotenv()
intents = Intents.default()
intents.message_content = True


class Bot(commands.Bot):
    def __init__(self, llm, config_file):
        self.prefix: str = os.getenv("DISCORD_PREFIX")
        self.rag: bool = False
        self.llm: pipeline = llm
        self.llm_config: json = None
        self.guild: Object = Object(id=os.getenv("DISCORD_GUILD_ID"))

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.load_config(config_file)

    @staticmethod
    async def on_command_completion(context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: command context
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

    def load_config(self, config_file):
        with open(config_file) as f:
            self.llm_config = json.load(f)


    async def load_cogs(self) -> None:
        """Executes on bot start, load all cogs as extensions within cogs/ dir"""
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
        """Loads cogs and syncs commands"""
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

    async def _respond(self, message: Message, history_text: str):
        """
        Private function that generates a response from the llm

        :param message: Discord message object
        :param history_text: The discord channel history for context
        """
        async with message.channel.typing():
            prompt = remove_id(message.content)
            bot_response, docs = await asyncio.to_thread(self.llm.response, query=prompt, context=history_text, identity=self.llm_config["identity"], rag=self.rag)
            filtered_bot_response = filter_mentions(bot_response)
            if docs:
                for i, doc in enumerate(docs):
                    data = None
                    if isinstance(doc, Document):
                        data = doc.page_content
                    elif isinstance(doc, str):
                        data = doc
                    else:
                        logger.error(f"Unknown {doc=}, skipping this source...")
                    if data:
                        logger.info(f"Source Number {i}:\n\n{data}")

            message_chunks = split_message(filtered_bot_response)
            for chunk in message_chunks:
                await message.channel.send(chunk)

    async def on_message(self, message: Message):
        """
        Triggers upon any message sent to the guild

        :param message: A discord Message object
        """
        # Never reply to yourself
        if message.author == self.user:
            return

        # Grab channel history
        history_list = []
        channel_history = [user async for user in message.channel.history(limit=self.llm_config["history_lines"] + 1)]
        for history in channel_history:
            if remove_id(history.content) != remove_id(message.content):
                history_list.append(history.author.name + ": " + remove_id(history.content))
        history_list.reverse()
        history_text = '\n'.join(history_list)

        # Process text or PDF attachments
        if message.attachments is not None:
            for attachment in message.attachments:
                logger.info(f"Found attachment {attachment.filename}, adding to rag database")
                if 'text' in attachment.content_type:
                    try:
                        file_content = await attachment.read()
                        file_string = file_content.decode('utf-8')
                        self.llm.merge_to_db(attachment.filename, attachment.size, [Document(page_content=file_string)])
                    except UnicodeDecodeError:
                       logger.warning(f"Cannot decode {attachment.filename} as UTF-8, filetype {attachment.content_type} may be unknown")
                elif attachment.content_type == 'application/pdf':
                    filepath = Path('tmp')
                    try:
                        await attachment.save(fp=filepath)
                        loader = PyPDFLoader(filepath)
                        self.llm.merge_to_db(attachment.filename, attachment.size, loader.load())
                    except Exception as e:
                        logger.error(f"Parsing {attachment.filename} resulted in {e}")
                        await message.channel.send(f"I had an error when trying the read the PDF {attachment.filename}")
                        break
                    try:
                        os.remove(filepath)
                    except FileNotFoundError:
                        pass
                else:
                    await message.channel.send(f"I couldn't recognize the file format you attached: {attachment.content_type}.\n"
                                         f"I currently support content types of `text` and `pdf`.")
                    return

        if self.user.mentioned_in(message):
            logger.info(f"Direct message received from author={message.author.name}, generating response...")
            await self._respond(message, history_text)

    async def on_command_error(self, context: Context, error: commands) -> None:
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
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error
