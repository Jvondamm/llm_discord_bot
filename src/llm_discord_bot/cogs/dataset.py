import os
import time
import asyncio
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands, Embed, Object

from src.llm_discord_bot.utils import filter_mentions, split_message

load_dotenv()

global threads

class Dataset(commands.Cog, name="llm"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="add_dataset",
        description="Add a HuggingFace Dataset to the bot's database",
    )
    @app_commands.guilds(Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def add_dataset(self, context: Context, dataset: str) -> None:
        """
        Add a HuggingFace Dataset to the bot's database

        :param context: command context
        :param dataset: HF dataset link to load and store
        """
        await context.send(embed=Embed(description=f"Loading {dataset=}", color=0xD75BF4))
        t_start = time.time()
        await asyncio.to_thread(self.bot.llm.merge_dataset_to_db, huggingface_dataset=dataset)
        await context.send(embed=Embed(description=f"Finished Loading {dataset=} in {time.time() - t_start} seconds", color=0xD75BF4))

    @commands.hybrid_command(
        name="rag",
        description="Enable/Disable RAG",
    )
    @app_commands.guilds(Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def toggle_rag(self, context: Context) -> None:
        """
        Enable/Disable RAG

        :param context: command context
        """
        self.bot.rag = not self.bot.rag
        await context.send(embed=Embed(description=f"{'Enabled' if self.bot.rag else 'Disabled'} rag"))


    # TODO add clearing local index - list what is currently there and size of documents


async def setup(bot) -> None:
    await bot.add_cog(Dataset(bot))