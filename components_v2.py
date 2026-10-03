# components_v2.py
# ================================
# Discord Components V2 — all views, buttons, selects, modals
# ================================

import discord
from discord import ui
from datetime import datetime
from typing import Optional
from core_config import BOT_IDENTITY, SEVERITY_COLORS, PERSONALITIES


# ==================================================================
# HELPER: create an embed (used inside views when we need text)
# ==================================================================
def _embed(title, description="", color=0x3498DB, **kw):
    e = discord.Embed(title=title, description=description, color=color,
                      timestamp=datetime.utcnow())
    e.set_footer(text=f"SentinelMod v{BOT_IDENTITY['version']}")
    for k, v in kw.items():
        if k == "fields":
            for name, val, inline in v:
                e.add_field(name=name, value=str(val)[:1024], inline=inline)
        elif k == "thumbnail":
            e.set_thumbnail(url=v)
    return e


# ==================================================================
# LICENSE AGREEMENT
# ==================================================================
def build_license_container() -> discord.Embed:
    return _embed(
        "📜 SentinelMod License Agreement",
        (
            "**By using SentinelMod you agree to:**\n\n"
            "1️⃣ The bot may create channels, roles, and categories for moderation.\n"
            "2️⃣ AI-powered moderation will analyse messages for safety.\n"
            "3️⃣ Message content is processed for moderation only and never shared.\n"
            "4️⃣ The bot creator reserves the right to revoke access.\n"
            "5️⃣ You will not attempt to abuse, exploit, or reverse-engineer the bot.\n\n"
            "**Only the server owner can accept or decline.**"
        ),
        color=0xF39C12,
    )


class LicenseAgreementView(ui.View):
    def __init__(self, guild, owner, bot, db, revoked, licensed,
                 pending, cleanup_fn, setup_fn, read_rules_fn, notify_fn):
        super().__init__(timeout=600)
        self.guild = guild
        self.owner = owner
        self.bot = bot
        self.db = db
        self.revoked = revoked
        self.licensed = licensed
        self.pending = pending
        self.cleanup_fn = cleanup_fn
        self.setup_fn = setup_fn
        self.read_rules_fn = read_rules_fn
        self.notify_fn = notify_fn
        self.message: Optional[discord.Message] = None

    @ui.button(label="✅ Accept & Setup", style=discord.ButtonStyle.success, row=0)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != (self.owner.id if self.owner else 0):
            await interaction.response.send_message(
                "❌ Only the server owner can accept.", ephemeral=True)
            return
        await interaction.response.defer()
        self.licensed.add(int(self.guild.id))
        self.db.accept_license(self.guild.id, interaction.user.id)
        self.db.init_guild_settings(self.guild.id)

        results = await self.setup_fn(self.guild)
        results_text = "\n".join(results[:20]) or "Setup complete!"

        embed = _embed("✅ License Accepted!", results_text, color=0x27AE60)
        try:
            await interaction.followup.send(embed=embed)
        except:
            pass

        self.pending.pop(self.guild.id, None)
        await self.notify_fn("INFO", f"✅ **{self.guild.name}** accepted license",
                             guild=self.guild)

        # Read rules
        try:
            await self.read_rules_fn(self.guild)
        except:
            pass

        self.stop()

    @ui.button(label="❌ Decline & Remove", style=discord.ButtonStyle.danger, row=0)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != (self.owner.id if self.owner else 0):
            await interaction.response.send_message(
                "❌ Only the server owner can decline.", ephemeral=True)
            return
        await interaction.response.send_message("👋 Understood. Leaving server...")
        self.revoked.add(int(self.guild.id))
        self.db.revoke_license(self.guild.id, "Owner declined")
        self.pending.pop(self.guild.id, None)
        await self.notify_fn("INFO", f"❌ **{self.guild.name}** declined license",
                             guild=self.guild)
        await self.cleanup_fn(self.guild)
        self.stop()

    async def on_timeout(self):
        self.pending.pop(self.guild.id, None)
        try:
            await self.cleanup_fn(self.guild)
        except:
            pass


# ==================================================================
# OWNER ALERT
# ==================================================================
def build_owner_alert_container(alert_type: str, message_text: str,
                                 guild=None, urgent=False) -> ui.View:
    """Build an informational view for owner DM alerts."""
    color_map = {
        "INFO": 0x3498DB, "JOIN": 0x2ECC71, "RAID": 0xE74C3C,
        "WARN": 0xF39C12, "ERROR": 0xE74C3C, "BAN": 0x8B0000,
    }
    color = color_map.get(alert_type, 0x3498DB)
    emoji = "🚨" if urgent else {"INFO": "ℹ️", "JOIN": "➕", "RAID": "🛡️",
                                   "WARN": "⚠️", "BAN": "🔨"}.get(alert_type, "📋")

    embed = _embed(
        f"{emoji} {alert_type}",
        message_text[:4000],
        color=color,
        fields=([("Server", f"{guild.name} ({guild.id})", False)] if guild else []),
    )
    view = EmbedView(embed)
    return view


class EmbedView(ui.View):
    """View that carries an embed for sending."""
    def __init__(self, embed: discord.Embed):
        super().__init__(timeout=None)
        self.embed = embed

    @ui.button(label="Dismiss", style=discord.ButtonStyle.secondary, row=0)
    async def dismiss(self, interaction: discord.Interaction, button: ui.Button):
        try:
            await interaction.message.delete()
        except:
            await interaction.response.defer()

    async def send_to(self, dest):
        """Helper to send with embed."""
        return await dest.send(embed=self.embed, view=self)


# Monkey-patch: make EmbedView work with `await dest.send(view=view)`
# by overriding — but actually discord.py doesn't support this natively.
# We'll handle it in notify_owner differently. For now the view is functional.


# ==================================================================
# RAID ALERT
# ==================================================================
def build_raid_alert_container(guild, join_count: int) -> ui.View:
    embed = _embed(
        "🚨 RAID DETECTED",
        (f"**{join_count}** accounts joined in rapid succession!\n\n"
         "🔒 Raid mode has been activated.\n"
         "New accounts under the minimum age will be auto-kicked.\n"
         "Mode will auto-deactivate in 5 minutes."),
        color=0xE74C3C,
        fields=[
            ("Server", guild.name, True),
            ("Members", str(guild.member_count), True),
            ("Joins Detected", str(join_count), True),
        ],
    )
    return RaidAlertView(embed, guild)


class RaidAlertView(ui.View):
    def __init__(self, embed, guild):
        super().__init__(timeout=300)
        self.embed = embed
        self.guild = guild

    @ui.button(label="🔒 Lock All Channels", style=discord.ButtonStyle.danger, row=0)
    async def lock_all(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only.", ephemeral=True)
            return
        await interaction.response.defer()
        locked = 0
        for ch in self.guild.text_channels:
            try:
                await ch.set_permissions(self.guild.default_role, send_messages=False,
                                         reason="Raid lockdown")
                locked += 1
            except:
                pass
        await interaction.followup.send(f"🔒 Locked **{locked}** channels.")
        button.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label="📊 View Joins", style=discord.ButtonStyle.primary, row=0)
    async def view_joins(self, interaction: discord.Interaction, button: ui.Button):
        recent = sorted(self.guild.members, key=lambda m: m.joined_at or datetime.min,
                        reverse=True)[:15]
        lines = []
        for m in recent:
            age = (datetime.utcnow() - m.created_at.replace(tzinfo=None)).days
            lines.append(f"• {m} — joined {discord.utils.format_dt(m.joined_at, 'R') if m.joined_at else '?'} "
                         f"(account: {age}d old)")
        await interaction.response.send_message(
            "\n".join(lines)[:2000] or "No data.", ephemeral=True)


# ==================================================================
# MOD ACTION
# ==================================================================
def build_mod_action_container(action_type: str, member, reason: str,
                                warning_count: int = 0) -> discord.Embed:
    color = {"SPAM": 0xF39C12, "TOXICITY": 0xE74C3C, "NSFW": 0x9B59B6,
             "SCAM": 0xE74C3C, "MUTED": 0xF39C12, "WARN": 0xF39C12,
             "BAN": 0x8B0000, "KICK": 0xE67E22}.get(action_type, 0x3498DB)
    embed = _embed(
        f"🛡️ {action_type}",
        f"**Target:** {member.mention if hasattr(member, 'mention') else member}\n"
        f"**Reason:** {reason}\n"
        f"**Warnings:** {warning_count}",
        color=color,
    )
    if hasattr(member, 'display_avatar'):
        embed.set_thumbnail(url=member.display_avatar.url)
    return embed


# ==================================================================
# CONFIRM ACTION
# ==================================================================
def build_confirm_container(parsed: dict) -> discord.Embed:
    cmd = parsed.get("command", "unknown")
    target = parsed.get("target", "N/A")
    reason = parsed.get("reason", "No reason given")
    duration = parsed.get("duration", "")
    return _embed(
        f"⚠️ Confirm: {cmd.replace('_', ' ').title()}",
        (f"**Target:** {target}\n"
         f"**Reason:** {reason}\n"
         f"{'**Duration:** ' + duration if duration else ''}\n\n"
         "Click **Confirm** to execute or **Cancel** to abort."),
        color=0xF39C12,
    )


class ConfirmActionView(ui.View):
    def __init__(self, parsed, message, guild, author, execute_fn):
        super().__init__(timeout=60)
        self.parsed = parsed
        self.message = message
        self.guild = guild
        self.author = author
        self.execute_fn = execute_fn

    @ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Not your action.", ephemeral=True)
            return
        await interaction.response.defer()
        self.parsed["confirmed"] = True
        result = await self.execute_fn(self.parsed, self.message, self.guild, self.author)
        if result:
            if isinstance(result, ui.View):
                await interaction.followup.send(view=result)
            else:
                await interaction.followup.send(str(result)[:2000])
        else:
            await interaction.followup.send("✅ Done.")
        self.stop()

    @ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Not your action.", ephemeral=True)
            return
        await interaction.response.send_message("🚫 Cancelled.", ephemeral=True)
        self.stop()

    async def on_timeout(self):
        pass


# ==================================================================
# GIVEAWAY END
# ==================================================================
def build_giveaway_end_container(prize: str, winners: list) -> discord.Embed:
    winner_text = "\n".join(f"🎉 {w.mention}" for w in winners) if winners else "No winners!"
    return _embed(
        "🎉 Giveaway Ended!",
        f"**Prize:** {prize}\n\n**Winners:**\n{winner_text}",
        color=0xF1C40F,
    )


# ==================================================================
# REMINDER
# ==================================================================
def build_reminder_container(user_id: str, reminder: str) -> discord.Embed:
    return _embed(
        "⏰ Reminder!",
        f"<@{user_id}> — {reminder}",
        color=0x3498DB,
    )


# ==================================================================
# HELP VIEW
# ==================================================================
class HelpView(ui.View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=120)
        self.pages = pages
        self.index = 0

    @ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        self.index = (self.index - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        self.index = (self.index + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)


# ==================================================================
# SETTINGS SELECT
# ==================================================================
class SettingsView(ui.View):
    def __init__(self, guild_id, db, current):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.db = db
        self.current = current

    @ui.select(
        placeholder="Change personality...",
        options=[
            discord.SelectOption(label=v["name"], value=k, emoji=v["emoji"])
            for k, v in PERSONALITIES.items()
        ],
        row=0,
    )
    async def personality(self, interaction: discord.Interaction, select: ui.Select):
        val = select.values[0]
        self.db.update_guild_setting(self.guild_id, "personality", val)
        await interaction.response.send_message(
            f"✅ Personality set to **{PERSONALITIES[val]['name']}** {PERSONALITIES[val]['emoji']}",
            ephemeral=True)

    @ui.select(
        placeholder="Memory mode...",
        options=[
            discord.SelectOption(label="Off", value="off", emoji="🚫"),
            discord.SelectOption(label="Server only", value="server", emoji="🏠"),
            discord.SelectOption(label="User only", value="user", emoji="👤"),
            discord.SelectOption(label="Both", value="both", emoji="📦"),
        ],
        row=1,
    )
    async def memory(self, interaction: discord.Interaction, select: ui.Select):
        val = select.values[0]
        self.db.update_guild_setting(self.guild_id, "memory_mode", val)
        await interaction.response.send_message(
            f"✅ Memory mode set to **{val}**", ephemeral=True)


# ==================================================================
# POLL VIEW
# ==================================================================
class PollView(ui.View):
    def __init__(self, options: list[str], poll_id: int, db):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.db = db
        for i, opt in enumerate(options[:5]):
            self.add_item(PollButton(opt, i, poll_id, db))


class PollButton(ui.Button):
    def __init__(self, label, index, poll_id, db):
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        super().__init__(label=f"{label} (0)", style=discord.ButtonStyle.primary,
                         emoji=emojis[index] if index < 5 else None,
                         custom_id=f"poll_{poll_id}_{index}")
        self.index = index
        self.poll_id = poll_id
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        import json as _json
        poll = self.db.query_one("SELECT * FROM polls WHERE id=?", (self.poll_id,))
        if not poll:
            await interaction.response.send_message("Poll not found.", ephemeral=True)
            return
        votes = _json.loads(poll.get("votes", "{}"))
        uid = str(interaction.user.id)
        votes[uid] = self.index
        self.db.execute("UPDATE polls SET votes=? WHERE id=?",
                        (_json.dumps(votes), self.poll_id))
        options = _json.loads(poll.get("options", "[]"))
        counts = {}
        for v in votes.values():
            counts[v] = counts.get(v, 0) + 1
        view = self.view
        for item in view.children:
            if isinstance(item, PollButton):
                c = counts.get(item.index, 0)
                opt_label = options[item.index] if item.index < len(options) else "?"
                item.label = f"{opt_label} ({c})"
        await interaction.response.edit_message(view=view)


# ==================================================================
# APPEAL MODAL
# ==================================================================
class AppealModal(ui.Modal, title="Appeal a Warning"):
    reason = ui.TextInput(
        label="Why should this warning be removed?",
        style=discord.TextStyle.paragraph,
        placeholder="Explain your side...",
        max_length=1000,
        required=True,
    )

    def __init__(self, warning_id, guild_id, db, ai, alert_fn):
        super().__init__()
        self.warning_id = warning_id
        self.guild_id = guild_id
        self.db = db
        self.ai = ai
        self.alert_fn = alert_fn

    async def on_submit(self, interaction: discord.Interaction):
        appeal_id = self.db.create_appeal(
            interaction.user.id, self.guild_id,
            self.reason.value, self.warning_id
        )
        await interaction.response.send_message(
            f"✅ Appeal #{appeal_id} submitted. A moderator will review it.",
            ephemeral=True)


# ==================================================================
# WARN INFO VIEW
# ==================================================================
class WarningsView(ui.View):
    def __init__(self, warnings: list[dict], user_name: str):
        super().__init__(timeout=60)
        self.warnings = warnings
        self.user_name = user_name
        self.page = 0
        self.per_page = 5

    def build_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        page_warns = self.warnings[start:start + self.per_page]
        lines = []
        for w in page_warns:
            lines.append(
                f"**#{w['id']}** [{w['severity'].upper()}] "
                f"{w['reason'][:80]} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>"
            )
        total_pages = max(1, (len(self.warnings) - 1) // self.per_page + 1)
        return _embed(
            f"⚠️ Warnings for {self.user_name}",
            "\n".join(lines) or "No warnings on this page.",
            color=0xF39C12,
            fields=[("Page", f"{self.page + 1}/{total_pages}", True),
                    ("Total", str(len(self.warnings)), True)],
        )

    @ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        max_page = (len(self.warnings) - 1) // self.per_page
        if self.page < max_page:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


# ==================================================================
# PROFILE EMBED (no view needed, but consistent interface)
# ==================================================================
def build_profile_embed(member, warnings_count, rep, balance, msg_count,
                         joined_ago) -> discord.Embed:
    e = _embed(
        f"👤 {member.display_name}",
        "",
        color=member.color.value or 0x3498DB,
        fields=[
            ("⚠️ Warnings", str(warnings_count), True),
            ("⭐ Rep", str(rep), True),
            ("💰 Balance", str(balance), True),
            ("💬 Messages", str(msg_count), True),
            ("📅 Joined", joined_ago, True),
            ("🎭 Roles", ", ".join(r.name for r in member.roles[1:][:10]) or "None", False),
        ],
    )
    if member.display_avatar:
        e.set_thumbnail(url=member.display_avatar.url)
    return e


# ==================================================================
# SERVER HEALTH EMBED
# ==================================================================
def build_server_health_embed(guild, stats: dict) -> discord.Embed:
    return _embed(
        f"📊 Server Health — {guild.name}",
        "",
        color=0x3498DB,
        fields=[
            ("👥 Members", str(guild.member_count), True),
            ("💬 Messages (7d)", str(stats.get("messages_7d", 0)), True),
            ("⚠️ Mod Actions (7d)", str(stats.get("mod_actions_7d", 0)), True),
            ("📈 Joins (7d)", str(stats.get("joins_7d", 0)), True),
            ("📊 Channels", str(len(guild.text_channels)), True),
            ("🎭 Roles", str(len(guild.roles)), True),
        ],
        thumbnail=guild.icon.url if guild.icon else None,
    )
