# slash_commands.py
# ================================
# All slash commands with Components V2 UI
# ================================

import discord
from discord import app_commands
from discord.ext import commands
import json
import time as time_module
from datetime import datetime, timedelta, timezone
from typing import Optional

from core_config import BOT_IDENTITY, PERSONALITIES
from components_v2 import (
    _embed, HelpView, WarningsView, SettingsView,
    build_profile_embed, build_server_health_embed,
    build_mod_action_container, AppealModal,
)
from utils import parse_duration, sanitize_bot_response


def register_slash_commands(
    bot, db, ai, mod_engine, voice_sessions, licensed_servers,
    revoked_servers, server_rules_cache, cleanup_and_leave,
    find_rules_channel, read_server_rules, is_owner,
    BOT_START_TIME, PERSONALITIES_MAP, notify_owner,
    scheduled_punishments, schedule_unpunish,
):
    # ------------------------------------------------------------------
    # /ban
    # ------------------------------------------------------------------
    @bot.tree.command(name="ban", description="Ban a user")
    @app_commands.describe(
        user="User to ban",
        reason="Reason for ban",
        duration="Duration (e.g. 7d, 24h) — leave empty for permanent",
        delete_days="Days of messages to delete (0-7)",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def slash_ban(interaction: discord.Interaction,
                        user: discord.Member,
                        reason: str = "No reason provided",
                        duration: Optional[str] = None,
                        delete_days: int = 1):
        if user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Cannot ban an admin.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await user.ban(reason=reason, delete_message_days=min(delete_days, 7))
            response = f"🔨 Banned **{user}**. Reason: {reason}"
            if duration:
                secs = parse_duration(duration)
                if secs:
                    when = (datetime.now() + timedelta(seconds=secs)).isoformat()
                    await schedule_unpunish(interaction.guild.id, user.id, "unban", when)
                    response = f"🔨 Temp-banned **{user}** for {duration}. Reason: {reason}"
            await interaction.followup.send(response)
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions.", ephemeral=True)

    # ------------------------------------------------------------------
    # /kick
    # ------------------------------------------------------------------
    @bot.tree.command(name="kick", description="Kick a user")
    @app_commands.describe(user="User to kick", reason="Reason")
    @app_commands.checks.has_permissions(kick_members=True)
    async def slash_kick(interaction: discord.Interaction,
                         user: discord.Member, reason: str = "No reason"):
        await interaction.response.defer()
        try:
            await user.kick(reason=reason)
            await interaction.followup.send(f"👢 Kicked **{user}**. Reason: {reason}")
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions.", ephemeral=True)

    # ------------------------------------------------------------------
    # /mute
    # ------------------------------------------------------------------
    @bot.tree.command(name="mute", description="Timeout a user")
    @app_commands.describe(user="User", duration="Duration (e.g. 10m, 1h, 7d)", reason="Reason")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def slash_mute(interaction: discord.Interaction,
                         user: discord.Member,
                         duration: str = "10m",
                         reason: str = "No reason"):
        secs = parse_duration(duration) or 600
        await interaction.response.defer()
        try:
            until = datetime.now(timezone.utc) + timedelta(seconds=secs)
            await user.timeout(until, reason=reason)
            await interaction.followup.send(
                f"🔇 Muted **{user}** for {duration}. Reason: {reason}")
        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions.", ephemeral=True)

    # ------------------------------------------------------------------
    # /warn
    # ------------------------------------------------------------------
    @bot.tree.command(name="warn", description="Warn a user")
    @app_commands.describe(user="User", reason="Reason")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def slash_warn(interaction: discord.Interaction,
                         user: discord.Member, reason: str = "Rule violation"):
        wc, _ = db.add_warning(user.id, interaction.guild.id, reason, "medium",
                                moderator=str(interaction.user.id))
        embed = build_mod_action_container("WARN", user, reason, wc)
        await interaction.response.send_message(
            f"⚠️ Warned **{user}** — #{wc}. Reason: {reason}", embed=embed)

    # ------------------------------------------------------------------
    # /warnings
    # ------------------------------------------------------------------
    @bot.tree.command(name="warnings", description="View warnings for a user")
    @app_commands.describe(user="User to check")
    async def slash_warnings(interaction: discord.Interaction,
                             user: Optional[discord.Member] = None):
        target = user or interaction.user
        warns = db.get_warnings(target.id, interaction.guild.id)
        if not warns:
            await interaction.response.send_message(
                f"✅ **{target.display_name}** has no warnings.", ephemeral=True)
            return
        view = WarningsView(warns, target.display_name)
        await interaction.response.send_message(
            embed=view.build_embed(), view=view, ephemeral=True)

    # ------------------------------------------------------------------
    # /purge
    # ------------------------------------------------------------------
    @bot.tree.command(name="purge", description="Bulk delete messages")
    @app_commands.describe(count="Number of messages (1-500)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def slash_purge(interaction: discord.Interaction, count: int = 10):
        count = min(max(count, 1), 500)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=count)
        await interaction.followup.send(f"🗑️ Deleted **{len(deleted)}** messages.",
                                         ephemeral=True)

    # ------------------------------------------------------------------
    # /profile
    # ------------------------------------------------------------------
    @bot.tree.command(name="profile", description="View user profile")
    @app_commands.describe(user="User (defaults to you)")
    async def slash_profile(interaction: discord.Interaction,
                            user: Optional[discord.Member] = None):
        target = user or interaction.user
        warns = db.get_warnings(target.id, interaction.guild.id)
        rep = db.get_rep(target.id, interaction.guild.id)
        bal = db.get_balance(target.id, interaction.guild.id)
        ms = db.query_one(
            "SELECT count FROM message_stats WHERE user_id=? AND guild_id=?",
            (str(target.id), str(interaction.guild.id)))
        joined = discord.utils.format_dt(target.joined_at, "R") if target.joined_at else "?"
        embed = build_profile_embed(target, len(warns), rep, bal["balance"],
                                     ms["count"] if ms else 0, joined)
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /settings
    # ------------------------------------------------------------------
    @bot.tree.command(name="settings", description="View and change bot settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_settings(interaction: discord.Interaction):
        s = db.get_guild_settings(interaction.guild.id)
        embed = _embed(
            "⚙️ Server Settings",
            "",
            color=0x3498DB,
            fields=[
                ("AI Moderation", "✅ On" if s.get("ai_mod_enabled") else "❌ Off", True),
                ("Personality", s.get("personality", "professional").title(), True),
                ("Memory Mode", s.get("memory_mode", "both"), True),
                ("Spam Limit", f"{s.get('spam_limit', 5)} msgs / {s.get('spam_window', 5)}s", True),
                ("Raid Limit", f"{s.get('raid_limit', 10)} joins / {s.get('raid_window', 10)}s", True),
                ("Warn → Kick", str(s.get("warn_threshold_kick", 5)), True),
                ("Warn → Ban", str(s.get("warn_threshold_ban", 8)), True),
            ],
        )
        view = SettingsView(str(interaction.guild.id), db, s)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ------------------------------------------------------------------
    # /health
    # ------------------------------------------------------------------
    @bot.tree.command(name="health", description="Server health dashboard")
    async def slash_health(interaction: discord.Interaction):
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        rows = db.query(
            "SELECT SUM(messages) as m, SUM(mod_actions) as a, SUM(joins) as j "
            "FROM daily_stats WHERE guild_id=? AND date>=?",
            (str(interaction.guild.id), week_ago))
        r = rows[0] if rows else {}
        stats = {
            "messages_7d": r.get("m", 0) or 0,
            "mod_actions_7d": r.get("a", 0) or 0,
            "joins_7d": r.get("j", 0) or 0,
        }
        embed = build_server_health_embed(interaction.guild, stats)
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /appeal
    # ------------------------------------------------------------------
    @bot.tree.command(name="appeal", description="Appeal a warning")
    @app_commands.describe(warning_id="Warning ID to appeal")
    async def slash_appeal(interaction: discord.Interaction, warning_id: int):
        modal = AppealModal(warning_id, str(interaction.guild.id), db, ai,
                            lambda g, e: None)
        await interaction.response.send_modal(modal)

    # ------------------------------------------------------------------
    # /reload_rules
    # ------------------------------------------------------------------
    @bot.tree.command(name="reload_rules", description="Refresh cached server rules")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_reload_rules(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        server_rules_cache.pop(str(interaction.guild.id), None)
        rules = await read_rules_server(interaction.guild)  # typo guard
        await interaction.followup.send(
            f"🔄 Rules refreshed — {len(rules)} chars loaded." if rules
            else "❌ No rules found.", ephemeral=True)

    # Alias with correct function name
    async def read_rules_server(guild):
        return await read_server_rules(guild)

    # ------------------------------------------------------------------
    # /botinfo
    # ------------------------------------------------------------------
    @bot.tree.command(name="botinfo", description="Bot information and stats")
    async def slash_botinfo(interaction: discord.Interaction):
        uptime_secs = int(time_module.time() - BOT_START_TIME)
        hours, remainder = divmod(uptime_secs, 3600)
        minutes, secs = divmod(remainder, 60)

        total_members = sum(g.member_count or 0 for g in bot.guilds)

        embed = _embed(
            f"🤖 {BOT_IDENTITY['name']} v{BOT_IDENTITY['version']}",
            f"*{BOT_IDENTITY['codename']} Edition*",
            color=0x3498DB,
            fields=[
                ("Servers", str(len(bot.guilds)), True),
                ("Members", str(total_members), True),
                ("Uptime", f"{hours}h {minutes}m {secs}s", True),
                ("Latency", f"{round(bot.latency * 1000)}ms", True),
                ("Licensed", str(len(licensed_servers)), True),
                ("Creator", BOT_IDENTITY["creator"], True),
            ],
        )
        if bot.user and bot.user.display_avatar:
            embed.set_thumbnail(url=bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /giveaway
    # ------------------------------------------------------------------
    @bot.tree.command(name="giveaway", description="Start a giveaway")
    @app_commands.describe(prize="What to give away", duration="Duration (e.g. 1h, 1d)",
                           winners="Number of winners")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_giveaway(interaction: discord.Interaction,
                             prize: str, duration: str = "1h", winners: int = 1):
        secs = parse_duration(duration) or 3600
        end = datetime.now() + timedelta(seconds=secs)
        embed = _embed(
            "🎉 GIVEAWAY 🎉",
            f"**Prize:** {prize}\n**Winners:** {winners}\n"
            f"**Ends:** <t:{int(end.timestamp())}:R>\n\nReact 🎉 to enter!",
            color=0xF1C40F,
        )
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🎉")
        db.execute(
            "INSERT INTO giveaways (guild_id,channel_id,message_id,prize,winners,end_time,host_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(interaction.guild.id), str(interaction.channel.id), str(msg.id),
             prize, winners, end.isoformat(), str(interaction.user.id)))

    # ------------------------------------------------------------------
    # /lockdown
    # ------------------------------------------------------------------
    @bot.tree.command(name="lockdown", description="Lock the current channel")
    @app_commands.describe(reason="Reason for lockdown")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slash_lockdown(interaction: discord.Interaction,
                             reason: str = "Channel lockdown"):
        await interaction.channel.set_permissions(
            interaction.guild.default_role, send_messages=False, reason=reason)
        await interaction.response.send_message(f"🔒 Channel locked. Reason: {reason}")

    # ------------------------------------------------------------------
    # /unlock
    # ------------------------------------------------------------------
    @bot.tree.command(name="unlock", description="Unlock the current channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slash_unlock(interaction: discord.Interaction):
        await interaction.channel.set_permissions(
            interaction.guild.default_role, send_messages=None, reason="Unlock")
        await interaction.response.send_message("🔓 Channel unlocked.")

    # ------------------------------------------------------------------
    # Error handler for slash commands
    # ------------------------------------------------------------------
    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction,
                                    error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission for this command.", ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Cooldown — try again in {error.retry_after:.0f}s.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"❌ An error occurred: {error}", ephemeral=True)
            print(f"Slash error: {error}")
