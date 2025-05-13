from discord.ext import commands
from discord.ext.commands import Context
from discord import Embed


class Admin(commands.Cog, name="admin"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="quit",
        description="Make the bot quit",
    )
    @commands.is_owner()
    async def quit(self, context: Context) -> None:
        """
        Make the bot quit

        :param context: command context
        """
        await context.send(embed=Embed(description="Quitting, see ya later...", color=0xBEBEFE))
        await self.bot.close()

async def setup(bot) -> None:
    await bot.add_cog(Admin(bot))

