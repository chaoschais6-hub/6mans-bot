import discord
from discord import app_commands
from discord.ext import commands

import database as db


class SettingsCog(commands.Cog, name="Settings"):
    @app_commands.command(name="pingrole", description="Set the role to ping when a match starts")
    @app_commands.describe(role="Role to ping for match announcements")
    @app_commands.default_permissions(manage_roles=True)
    async def pingrole(self, interaction: discord.Interaction, role: discord.Role):
        db.set_ping_role(interaction.guild.id, role.id)
        await interaction.response.send_message(
            f"Match announcements will now ping {role.mention}.", ephemeral=True
        )

    @app_commands.command(name="clear_pingrole", description="Stop pinging a role for matches")
    @app_commands.default_permissions(manage_roles=True)
    async def clear_pingrole(self, interaction: discord.Interaction):
        db.set_ping_role(interaction.guild.id, None)
        await interaction.response.send_message(
            "Match ping role cleared.", ephemeral=True
        )

    @app_commands.command(name="setchannel", description="Lock bot commands to a specific channel")
    @app_commands.describe(channel="Channel to allow commands in (leave empty to unlock)")
    @app_commands.default_permissions(manage_roles=True)
    async def setchannel(
        self, interaction: discord.Interaction, channel: discord.TextChannel = None
    ):
        if channel is None:
            db.set_queue_channel(interaction.guild.id, None)
            await interaction.response.send_message(
                "Channel lock removed. Queueing is now DISABLED everywhere "
                "until you set a channel again.",
                ephemeral=True,
            )
        else:
            db.set_queue_channel(interaction.guild.id, channel.id)
            await interaction.response.send_message(
                f"Commands now locked to {channel.mention}.", ephemeral=True
            )

    @app_commands.command(name="showchannel", description="Show the current locked channel")
    async def showchannel(self, interaction: discord.Interaction):
        cid = db.get_queue_channel(interaction.guild.id)
        if cid:
            ch = interaction.guild.get_channel(cid)
            await interaction.response.send_message(
                f"Commands locked to: {ch.mention if ch else f'<#{cid}>'}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No channel lock set. Queueing is DISABLED everywhere until an admin "
                "sets a channel with `/setchannel`.",
                ephemeral=True,
            )

    @app_commands.command(
        name="setqueuetimeout",
        description="Set how long a player can wait in queue before auto-removed",
    )
    @app_commands.describe(minutes="Timeout in minutes (1-720)")
    @app_commands.default_permissions(manage_roles=True)
    async def setqueuetimeout(self, interaction: discord.Interaction, minutes: int):
        if minutes < 1 or minutes > 720:
            await interaction.response.send_message(
                "Timeout must be between 1 and 720 minutes.", ephemeral=True
            )
            return
        db.set_queue_timeout(interaction.guild.id, minutes)
        await interaction.response.send_message(
            f"Queue timeout set to **{minutes}** minute(s).",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(SettingsCog(bot))