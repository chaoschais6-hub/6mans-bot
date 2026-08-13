import discord
from discord import app_commands
from discord.ext import commands

import database as db
from balancing import balance_teams


class QueueCog(commands.Cog, name="Queue"):
    def __init__(self, bot):
        self.bot = bot
        self._queues = {}  # guild_id -> dict of user_id -> None (ordered)

    def _queue(self, guild_id):
        return self._queues.setdefault(guild_id, {})

    def _check_channel(self, interaction: discord.Interaction) -> bool:
        """Return True if command is allowed in this channel.

        Queueing is DISABLED until an admin locks a channel with /setchannel.
        """
        allowed = db.get_queue_channel(interaction.guild.id)
        if allowed is None:
            return False
        return interaction.channel.id == allowed

    def _channel_lock_msg(self, interaction: discord.Interaction) -> str:
        allowed = db.get_queue_channel(interaction.guild.id)
        if allowed:
            ch = interaction.guild.get_channel(allowed)
            return f"Commands are locked to {ch.mention if ch else f'<#{allowed}>'}."
        return "Queueing is disabled. An admin must set a channel with `/setchannel`."

    group = app_commands.Group(name="queue", description="6mans queue commands")

    @group.command(name="join", description="Join the 6mans queue")
    async def join(self, interaction: discord.Interaction):
        if not self._check_channel(interaction):
            await interaction.response.send_message(
                self._channel_lock_msg(interaction), ephemeral=True
            )
            return

        guild = interaction.guild
        user = interaction.user
        q = self._queue(guild.id)

        if user.id in q:
            await interaction.response.send_message(
                "You're already in the queue!", ephemeral=True
            )
            return

        if db.get_pending_match_for_user(guild.id, user.id):
            await interaction.response.send_message(
                "You're in an active match. Report it with `/result` first.",
                ephemeral=True,
            )
            return

        q[user.id] = None
        await interaction.response.send_message(
            f"{user.mention} joined the queue. **({len(q)}/6)**", ephemeral=False
        )

        if len(q) == 6:
            await self._start_match(interaction, guild, q)

    @group.command(name="leave", description="Leave the 6mans queue")
    async def leave(self, interaction: discord.Interaction):
        if not self._check_channel(interaction):
            await interaction.response.send_message(
                self._channel_lock_msg(interaction), ephemeral=True
            )
            return

        q = self._queue(interaction.guild.id)
        if interaction.user.id not in q:
            await interaction.response.send_message(
                "You're not in the queue.", ephemeral=True
            )
            return
        del q[interaction.user.id]
        await interaction.response.send_message(
            f"{interaction.user.mention} left the queue. **({len(q)}/6)**",
            ephemeral=False,
        )

    @group.command(name="status", description="Show who is in the queue")
    async def status(self, interaction: discord.Interaction):
        if not self._check_channel(interaction):
            await interaction.response.send_message(
                self._channel_lock_msg(interaction), ephemeral=True
            )
            return

        q = self._queue(interaction.guild.id)
        if not q:
            await interaction.response.send_message(
                "The queue is empty. Use `/queue join` to jump in!", ephemeral=False
            )
            return
        mentions = ", ".join(f"<@{uid}>" for uid in q)
        await interaction.response.send_message(
            f"**Queue ({len(q)}/6):** {mentions}", ephemeral=False
        )

    # ----- Prefix commands -----
    @commands.command(name="q", aliases=["queue"], help="Join the 6mans queue")
    async def q_prefix(self, ctx: commands.Context):
        if not self._check_channel_prefix(ctx):
            await ctx.reply(self._channel_lock_msg_prefix(ctx))
            return
        await self._do_join(ctx.guild, ctx.author, ctx.channel)

    @commands.command(name="l", aliases=["leave"], help="Leave the 6mans queue")
    async def l_prefix(self, ctx: commands.Context):
        if not self._check_channel_prefix(ctx):
            await ctx.reply(self._channel_lock_msg_prefix(ctx))
            return
        await self._do_leave(ctx.guild, ctx.author, ctx.channel)

    def _check_channel_prefix(self, ctx: commands.Context) -> bool:
        allowed = db.get_queue_channel(ctx.guild.id)
        if allowed is None:
            return False
        return ctx.channel.id == allowed

    def _channel_lock_msg_prefix(self, ctx: commands.Context) -> str:
        allowed = db.get_queue_channel(ctx.guild.id)
        if allowed:
            ch = ctx.guild.get_channel(allowed)
            return f"Commands are locked to {ch.mention if ch else f'<#{allowed}>'}."
        return "Queueing is disabled. An admin must set a channel with `/setchannel`."

    async def _do_join(self, guild, user, channel):
        q = self._queue(guild.id)
        if user.id in q:
            await channel.send(f"{user.mention} you're already in the queue!")
            return
        if db.get_pending_match_for_user(guild.id, user.id):
            await channel.send(f"{user.mention} you're in an active match. Use `!result` first.")
            return
        q[user.id] = None
        await channel.send(f"{user.mention} joined the queue. **({len(q)}/6)**")
        if len(q) == 6:
            await self._start_match_prefix(guild, q, channel)

    async def _do_leave(self, guild, user, channel):
        q = self._queue(guild.id)
        if user.id not in q:
            await channel.send(f"{user.mention} you're not in the queue.")
            return
        del q[user.id]
        await channel.send(f"{user.mention} left the queue. **({len(q)}/6)**")

    def _effective_mmr(self, guild, uid):
        """Role-based MMR wins over individual MMR when configured."""
        member = guild.get_member(uid)
        if member is not None:
            role_mmr = db.get_effective_mmr(guild.id, [r.id for r in member.roles])
            if role_mmr is not None:
                return role_mmr
        return db.get_player(guild.id, uid)["mmr"]

    async def _start_match(self, interaction, guild, q):
        ids = list(q.keys())
        q.clear()

        players = [(uid, self._effective_mmr(guild, uid)) for uid in ids]
        team_a, team_b = balance_teams(players)

        a_ids = [uid for uid, _ in team_a]
        b_ids = [uid for uid, _ in team_b]
        match_id = db.create_match(guild.id, a_ids, b_ids)

        a_avg = sum(m for _, m in team_a) // 3
        b_avg = sum(m for _, m in team_b) // 3
        a_mentions = " ".join(f"<@{uid}>" for uid in a_ids)
        b_mentions = " ".join(f"<@{uid}>" for uid in b_ids)

        ping = ""
        role_id = db.get_ping_role(guild.id)
        if role_id:
            role = guild.get_role(role_id)
            if role:
                ping = f"{role.mention} "

        await interaction.channel.send(
            f"{ping}**Match #{match_id} is live!**\n"
            f"**Team A** (avg MMR {a_avg}): {a_mentions}\n"
            f"**Team B** (avg MMR {b_avg}): {b_mentions}\n"
            f"Winning team reports with `/result <your_score> <opponent_score>`"
        )

    async def _start_match_prefix(self, guild, q, channel):
        ids = list(q.keys())
        q.clear()

        players = [(uid, self._effective_mmr(guild, uid)) for uid in ids]
        team_a, team_b = balance_teams(players)

        a_ids = [uid for uid, _ in team_a]
        b_ids = [uid for uid, _ in team_b]
        match_id = db.create_match(guild.id, a_ids, b_ids)

        a_avg = sum(m for _, m in team_a) // 3
        b_avg = sum(m for _, m in team_b) // 3
        a_mentions = " ".join(f"<@{uid}>" for uid in a_ids)
        b_mentions = " ".join(f"<@{uid}>" for uid in b_ids)

        ping = ""
        role_id = db.get_ping_role(guild.id)
        if role_id:
            role = guild.get_role(role_id)
            if role:
                ping = f"{role.mention} "

        await channel.send(
            f"{ping}**Match #{match_id} is live!**\n"
            f"**Team A** (avg MMR {a_avg}): {a_mentions}\n"
            f"**Team B** (avg MMR {b_avg}): {b_mentions}\n"
            f"Winning team reports with `!result <your_score> <opponent_score>`"
        )


async def setup(bot):
    await bot.add_cog(QueueCog(bot))