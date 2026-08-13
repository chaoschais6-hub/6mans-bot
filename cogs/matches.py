import discord
from discord import app_commands
from discord.ext import commands

import database as db
import elo


class MatchesCog(commands.Cog, name="Matches"):
    @app_commands.command(name="result", description="Report the score of your current match")
    @app_commands.describe(
        my_score="Your team's score",
        opp_score="Opponent team's score",
    )
    async def result(
        self,
        interaction: discord.Interaction,
        my_score: int,
        opp_score: int,
    ):
        await self._do_result(interaction.guild, interaction.user, interaction.channel, my_score, opp_score)

    @commands.command(name="result", help="Report match result: !result <my_score> <opp_score>")
    async def result_prefix(self, ctx: commands.Context, my_score: int, opp_score: int):
        await self._do_result(ctx.guild, ctx.author, ctx.channel, my_score, opp_score)

    async def _do_result(self, guild, user, channel, my_score, opp_score):
        match = db.get_pending_match_for_user(guild.id, user.id)
        if not match:
            await channel.send(f"{user.mention} you don't have an active match to report.")
            return
        if my_score < 0 or opp_score < 0:
            await channel.send(f"{user.mention} scores can't be negative.")
            return
        if my_score == opp_score:
            await channel.send(f"{user.mention} ties aren't supported. Report a winning score.")
            return

        if user.id in match["team1"]:
            score1, score2 = my_score, opp_score
        else:
            score1, score2 = opp_score, my_score

        updated = db.report_match(match["id"], score1, score2, user.id)
        if not updated:
            await channel.send(f"{user.mention} that match was already reported.")
            return

        team1 = [(uid, db.get_player(guild.id, uid)["mmr"]) for uid in match["team1"]]
        team2 = [(uid, db.get_player(guild.id, uid)["mmr"]) for uid in match["team2"]]
        updates = elo.apply_match_result(team1, team2, score1, score2)

        lines = []
        for uid, new_mmr, delta, won in updates:
            member = guild.get_member(uid)
            name = member.display_name if member else f"<@{uid}>"
            sign = "+" if delta >= 0 else ""
            lines.append(f"▫️ {name}: **{new_mmr}** ({sign}{delta})")

        msg = (
            f"**Match #{match['id']} result recorded** — reported by {user.mention}\n"
            f"Team A {score1} - {score2} Team B\n\n"
            f"**MMR changes**\n" + "\n".join(lines)
        )
        await channel.send(msg)

        for uid, new_mmr, _delta, won in updates:
            db.update_player(guild.id, uid, mmr_new=new_mmr, won=won)

    @app_commands.command(name="active", description="Show all pending matches in this server")
    async def active(self, interaction: discord.Interaction):
        matches = db.get_active_matches(interaction.guild.id)
        if not matches:
            await interaction.response.send_message(
                "No active matches right now.", ephemeral=False
            )
            return
        lines = []
        for m in matches:
            a = ", ".join(f"<@{uid}>" for uid in m["team1"])
            b = ", ".join(f"<@{uid}>" for uid in m["team2"])
            lines.append(f"**Match #{m['id']}**: {a} vs {b}")
        await interaction.response.send_message("\n".join(lines), ephemeral=False)


async def setup(bot):
    await bot.add_cog(MatchesCog(bot))