import os
import time
import asyncio
import logging
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands, Embed, Object, ui, Interaction, ButtonStyle


load_dotenv()

logger = logging.getLogger("DATASET_COG")

class ConfirmView(ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @ui.button(label="Confirm", style=ButtonStyle.green)
    async def confirm_button(self, interaction: Interaction, button: ui.Button):
        self.value = True
        self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.red)
    async def cancel_button(self, interaction: Interaction, button: ui.Button):
        self.value = False
        self.stop()

class Dataset(commands.Cog, name="llm"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="add_dataset",
        description="Add a HuggingFace Dataset to the bot's database, optionally provide a split and subset.",
    )
    @app_commands.guilds(Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def add_dataset(self,
                          context: Context,
                          dataset: str,
                          split: str = "train") -> None:
        """
        Add a HuggingFace Dataset to the bot's database. Ensure you trust the dataset first!

        :param context: command context
        :param dataset: HF dataset link to load and store
        :param split: HF dataset split, defaults to 'train'
        """
        if self.bot.llm.check_dataset_unique(dataset):
            await context.send(embed=Embed(description=f"Loading {dataset=} on {split=}", color=0xD75BF4))
            t_start = time.time()
            await asyncio.to_thread(self.bot.llm.merge_dataset_to_db, huggingface_dataset=dataset, split=split)
            await context.send(embed=Embed(description=f"Finished Loading {dataset=} in {round(time.time() - t_start, 1)} seconds", color=0xD75BF4))
        else:
            await context.send(embed=Embed(description=f"{dataset=} already exists in the database"))

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
        logger.info(f"Changed rag to {self.bot.rag}")
        await context.send(embed=Embed(description=f"{'Enabled' if self.bot.rag else 'Disabled'} rag"))


    @commands.hybrid_command(
        name="wipe",
        description="Wipe database of all datasets",
    )
    @app_commands.guilds(Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def wipe_database(self, context: Context) -> None:
        """
        Wipe database of all datasets

        :param context: command context
        """
        view = ConfirmView()
        message = await context.send("Are you sure?", view=view)
        await view.wait()
        await message.delete()

        if view.value is None:
            await context.send(embed=Embed(description="Timed out."))
        elif view.value:
            await context.send(embed=Embed(description="Confirmed, wiping database"))
            await asyncio.to_thread(self.bot.llm.drop_database)
        else:
            await context.send(embed=Embed(description="Cancelled"))


    @commands.hybrid_command(
        name="database_size",
        description="Get the current size of the database",
    )
    @app_commands.guilds(Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def get_database_size(self, context: Context) -> None:
        if self.bot.llm.database:
            pass
        else:
            await context.send()

async def setup(bot) -> None:
    await bot.add_cog(Dataset(bot))