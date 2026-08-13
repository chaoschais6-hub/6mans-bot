import asyncio
import discord
from discord import app_commands
from discord.ext import commands

import database as db
import rltracker

from discord.app_commands import Choice


def _run_blocking(func):
    return asyncio.get_event_loop().run_in_executor(None, func)


class RLTrackerCog(commands.Cog, name="RL Tracker"):
    @app_commands.command(
        name="link",
        description="Link your Rocket League account to your Discord",
    )
    @app_commands.describe(
        platform="Platform you play Rocket League on",
        username="Your in-game name on that platform",
    )
    @app_commands.choices(
        platform=[
            Choice(name="Epic Games", value="epic"),
            Choice(name="Steam", value="steam"),
            Choice(name="Xbox Live", value="xbl"),
            Choice(name="PlayStation", value="psn"),
        ]
    )
    async def link(
        self,
        interaction: discord.Interaction,
        platform: str,
        username: str,
    ):
        await interaction.response.defer(ephemeral=False)
        # Verify the profile exists before saving so we don't store junk.
        try:
            result = await _run_blocking(
                lambda: rltracker.fetch_rank(platform, username.strip())
            )
        except rltracker.NoApiKeyError:
            await interaction.followup.send(
                f"RL Tracker isn't configured yet. Ask an admin to set up "
                f"an API key first.",
                ephemeral=True,
            )
            return
        except rltracker.PlayerNotFoundError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        except rltracker.RLTrackerError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        db.set_rl_link(interaction.guild.id, interaction.user.id, platform, username.strip())
        await interaction.followup.send(
            f"Linked <@{interaction.user.id}> → **{username.strip()}** "
            f"({platform}). "
            f"Use `/rlrank` to see their RL ratings.",
            ephemeral=False,
        )

    @app_commands.command(
        name="unlink",
        description="Unlink your Rocket League account",
    )
    async def unlink(self, interaction: discord.Interaction):
        db.clear_rl_link(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(
            f"Unlinked <@{interaction.user.id}>'s RL account.", ephemeral=True
        )

    @app_commands.command(
        name="rlrank",
        description="Show a linked player's real Rocket League 2s/3s ratings",
    )
    @app_commands.describe(user="Player to check (defaults to you)")
    async def rlrank(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer(ephemeral=False)
        user = user or interaction.user

        link = db.get_rl_link(interaction.guild.id, user.id)
        if link is None:
            await interaction.followup.send(
                f"<@{user.id}> hasn't set up a linked RL account. Run `/link` first.",
                ephemeral=True,
            )
            return

        try:
            result = await _run_blocking(
                lambda: rltracker.fetch_rank(link["platform"], link["username"])
            )
        except rltracker.NoApiKeyError:
            await interaction.followup.send(
                "RL Tracker isn't configured yet. Ask an admin to set up "
                "an API key first.",
                ephemeral=True,
            )
            return
        except rltracker.PlayerNotFoundError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        except rltracker.RLTrackerError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        if result["error"]:
            await interaction.followup.send(
                f"**{user.display_name}** ({result['platform']}/{result['username']})\n"
                f"{result['error']}",
                ephemeral=False,
            )
            return

        twos = f"{result['twos']}" if result["twos"] is not None else "n/a"
        threes = f"{result['threes']}" if result["threes"] is not None else "n/a"
        triple_weighted = (
            f"(x1.25 = **{int(result['threes'] * rltracker.TRIPLES_MULTIPLIER)}**) "
            if result["threes"] is not None
            else ""
        )

        builder = (
            f"**{user.display_name}** ({result['platform']}/{result['username']})\n"
            f"2v2: **{twos}**\n"
            f"3v3: **{threes}** {triple_weighted}\n"
            f"Effective rating (highest of 2s / 3s×1.25): **{result['rating']}**"
        )
        await interaction.followup.send(builder, ephemeral=False)


async def setup(bot):
    await bot.add_cog(RLTrackerCog(bot))