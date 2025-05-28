import platform
import random
import os
import aiohttp
import discord
from discord import app_commands, Object
from discord.ext import commands
from discord.ext.commands import Context


class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot
    #     self.context_menu_user = app_commands.ContextMenu(
    #         name="Grab ID", callback=self.grab_id
    #     )
    #     self.bot.tree.add_command(self.context_menu_user)
    #
    # async def grab_id(
    #     self, interaction: discord.Interaction, user: discord.User
    # ) -> None:
    #     """
    #     Grabs the ID of the user.
    #
    #     :param interaction: The application command interaction.
    #     :param user: The user that is being interacted with.
    #     """
    #     embed = discord.Embed(
    #         description=f"The ID of {user.mention} is `{user.id}`.",
    #         color=0xBEBEFE,
    #     )
    #     await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="help", description="List all loaded commands."
    )
    @app_commands.guilds(discord.Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def help(self, context: Context) -> None:
        """
        List all loaded commands

        :param context: command context
        """
        embed = discord.Embed(
            title="Help", description="List of available commands:", color=0xBEBEFE
        )
        for i in self.bot.cogs:
            if i == "owner" and not (await self.bot.is_owner(context.author)):
                continue
            cog = self.bot.get_cog(i.lower())
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"{command.name} - {description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=i.capitalize(), value=f"```{help_text}```", inline=False
            )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="botinfo",
        description="Get bot configuration, llm models, owner, etc...",
    )
    @app_commands.guilds(discord.Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def info(self, context: Context) -> None:
        """
        Get bot configuration, llm models, owner, etc...

        :param context: command context
        """
        embed = discord.Embed(
            description=f"Generating conversation with model: {self.bot.llm.llm.model}\n"
                        f"Generating embeddings with model: {self.bot.llm.embedding_model_name}",
            color=0xBEBEFE,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(name="Owner:", value="virxx", inline=True)
        embed.add_field(
            name="Python Version:", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(
            name="Prefix:",
            value=f"/ (slash commands)",
            inline=False,
        )
        embed.set_footer(text=f"Requested by: {context.author}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="See if bot is online and it's latency"
    )
    @app_commands.guilds(discord.Object(id=os.getenv("DISCORD_GUILD_ID")))
    async def ping(self, context: Context) -> None:
        """
        See if bot is online and it's latency

        :param context: command context
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot latency:{round(self.bot.latency * 1000)}ms.",
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(General(bot))