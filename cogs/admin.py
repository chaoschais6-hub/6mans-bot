import discord
from discord import app_commands
from discord.ext import commands

import database as db


class AdminCog(commands.Cog, name="Admin"):
    @app_commands.command(
        name="set_mmr", description="[Admin] Set a player's MMR directly"
    )
    @app_commands.describe(user="Player to modify", mmr="New MMR value (0-9999)")
    @app_commands.default_permissions(administrator=True)
    async def set_mmr(
        self, interaction: discord.Interaction, user: discord.User, mmr: int
    ):
        if mmr < 0 or mmr > 9999:
            await interaction.response.send_message(
                "MMR must be between 0 and 9999.", ephemeral=True
            )
            return
        db.set_player_mmr(interaction.guild.id, user.id, mmr)
        await interaction.response.send_message(
            f"Set {user.mention}'s MMR to **{mmr}**.", ephemeral=True
        )

    @app_commands.command(
        name="reset_mmr", description="[Admin] Reset a player's MMR to default (1000)"
    )
    @app_commands.describe(user="Player to reset")
    @app_commands.default_permissions(administrator=True)
    async def reset_mmr(self, interaction: discord.Interaction, user: discord.User):
        db.set_player_mmr(interaction.guild.id, user.id, 1000)
        await interaction.response.send_message(
            f"Reset {user.mention}'s MMR to **1000**.", ephemeral=True
        )

    @app_commands.command(
        name="wipe_queue", description="[Admin] Clear the current queue"
    )
    @app_commands.default_permissions(administrator=True)
    async def wipe_queue(self, interaction: discord.Interaction):
        queue_cog = self.bot.get_cog("Queue")
        if queue_cog:
            q = queue_cog._queue(interaction.guild.id)
            q.clear()
        await interaction.response.send_message("Queue cleared.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))