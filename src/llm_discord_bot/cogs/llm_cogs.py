import time
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands, Embed, Object

load_dotenv()

class LlmCogs(commands.Cog, name="llm"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="add_dataset",
        description="Add a HuggingFace Dataset to the bot's database",
    )
    @app_commands.describe()
    @app_commands.guilds(Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def add_dataset(self, context: Context, dataset) -> None:
        """
        :param context: The application command context.
        :param dataset: HF dataset link to load and store
        """
        t_start = time.time()
        self.bot.llm.merge_dataset_to_db(dataset)
        embed = Embed(description=f"Loaded {dataset=} in {time.time() - t_start}", color=0xD75BF4)
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(LlmCogs(bot))