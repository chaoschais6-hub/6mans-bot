import discord
from discord import app_commands
from discord.ext import commands

import database as db


class MMRCog(commands.Cog, name="MMR"):
    @app_commands.command(name="mmr", description="Show your MMR and match record")
    async def mmr(self, interaction: discord.Interaction):
        p = db.get_player(interaction.guild.id, interaction.user.id)
        total = p["wins"] + p["losses"]
        rate = f"{p['wins'] / total * 100:.0f}%" if total else "n/a"
        await interaction.response.send_message(
            f"**{interaction.user.display_name}**\n"
            f"MMR: **{p['mmr']}**\n"
            f"Record: {p['wins']}W - {p['losses']}L\n"
            f"Win rate: {rate}",
            ephemeral=False,
        )

    @app_commands.command(name="leaderboard", description="Top 10 players by MMR")
    async def leaderboard(self, interaction: discord.Interaction):
        top = db.leaderboard(interaction.guild.id, 10)
        if not top:
            await interaction.response.send_message(
                "No ranked players yet. Queue up a match!", ephemeral=False
            )
            return

        medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
        lines = []
        for i, p in enumerate(top):
            lines.append(
                f"{medals[i]} **{p['mmr']}** <@{p['user_id']}> — {p['wins']}W {p['losses']}L"
            )
        await interaction.response.send_message(
            "**Leaderboard**\n" + "\n".join(lines), ephemeral=False
        )


async def setup(bot):
    await bot.add_cog(MMRCog(bot))
