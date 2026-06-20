# bot.py
# ================================
# SentinelAI - Conversational AI Bot
# Full System - Single File
# ================================

# ============ SECTION 1 - IMPORTS ============
import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import asyncio
import sqlite3
import time
import threading
import random
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from collections import defaultdict

# ============ SECTION 2 - CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
BOT_NAME = "SentinelMod"

# Moderation Settings
MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"
WARN_THRESHOLD_MUTE = 3
WARN_THRESHOLD_BAN = 5
MUTE_DURATION_MINUTES = 10

# Anti-Spam Settings
SPAM_MESSAGE_LIMIT = 5
SPAM_TIME_WINDOW = 5

# Anti-Raid Settings
RAID_JOIN_LIMIT = 10
RAID_TIME_WINDOW = 10
RAID_ACCOUNT_AGE_DAYS = 7

# ============ SECTION 3 - KEEP ALIVE ============
class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SentinelAI is alive!")

    def log_message(self, format, *args):
        pass

def run_server():
    server = HTTPServer(("0.0.0.0", 8080), KeepAlive)
    server.serve_forever()

def keep_alive():
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    print("✅ Keep alive server running on port 8080")

# ============ SECTION 4 - DATABASE ============
def init_database():
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            severity TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS mod_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT NOT NULL,
            mod_id TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id TEXT PRIMARY KEY,
            mod_role_name TEXT DEFAULT 'Sentinel-Mod',
            log_channel TEXT DEFAULT 'sentinel-logs',
            raid_channel TEXT DEFAULT 'sentinel-raid-alerts',
            warn_mute INTEGER DEFAULT 3,
            warn_ban INTEGER DEFAULT 5,
            mute_duration INTEGER DEFAULT 10,
            spam_limit INTEGER DEFAULT 5,
            spam_window INTEGER DEFAULT 5,
            raid_limit INTEGER DEFAULT 10,
            raid_window INTEGER DEFAULT 10,
            min_account_age INTEGER DEFAULT 7,
            scan_images INTEGER DEFAULT 1,
            ai_sensitivity REAL DEFAULT 0.7,
            welcome_channel TEXT DEFAULT 'welcome',
            welcome_enabled INTEGER DEFAULT 1,
            anti_nuke_enabled INTEGER DEFAULT 1,
            invite_block INTEGER DEFAULT 0,
            link_scan INTEGER DEFAULT 1,
            slowmode_ai INTEGER DEFAULT 1,
            pre_conflict INTEGER DEFAULT 1,
            word_filter TEXT DEFAULT '',
            alt_detection INTEGER DEFAULT 1,
            caps_filter INTEGER DEFAULT 1,
            mention_spam INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            reason TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS afk_users (
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message_id TEXT,
            prize TEXT NOT NULL,
            winners INTEGER DEFAULT 1,
            end_time TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            host_id TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS auto_roles (
            guild_id TEXT NOT NULL,
            role_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, role_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS word_filters (
            guild_id TEXT NOT NULL,
            word TEXT NOT NULL,
            PRIMARY KEY (guild_id, word)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            note TEXT NOT NULL,
            mod_id TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS backup_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            backup_type TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ============ SECTION 5 - DATABASE HELPERS ============
def get_db():
    conn = sqlite3.connect("sentinel.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_guild_settings(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "guild_id": str(guild_id),
        "mod_role_name": MOD_ROLE_NAME,
        "log_channel": MOD_LOG_CHANNEL,
        "raid_channel": RAID_CHANNEL,
        "warn_mute": WARN_THRESHOLD_MUTE,
        "warn_ban": WARN_THRESHOLD_BAN,
        "mute_duration": MUTE_DURATION_MINUTES,
        "spam_limit": SPAM_MESSAGE_LIMIT,
        "spam_window": SPAM_TIME_WINDOW,
        "raid_limit": RAID_JOIN_LIMIT,
        "raid_window": RAID_TIME_WINDOW,
        "min_account_age": RAID_ACCOUNT_AGE_DAYS,
        "scan_images": 1,
        "ai_sensitivity": 0.7,
        "welcome_channel": "welcome",
        "welcome_enabled": 1,
        "anti_nuke_enabled": 1,
        "invite_block": 0,
        "link_scan": 1,
        "slowmode_ai": 1,
        "pre_conflict": 1,
        "word_filter": "",
        "alt_detection": 1,
        "caps_filter": 1,
        "mention_spam": 1
    }

def init_guild_settings(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
        (str(guild_id),)
    )
    conn.commit()
    conn.close()

def add_warning(user_id, guild_id, reason, severity):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO warnings (user_id, guild_id, reason, severity, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (str(user_id), str(guild_id), reason, severity, datetime.now().isoformat()))
    conn.commit()
    c.execute(
        "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?",
        (str(user_id), str(guild_id))
    )
    count = c.fetchone()[0]
    conn.close()
    return count

def get_warnings(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?
        ORDER BY timestamp DESC
    """, (str(user_id), str(guild_id)))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_warnings(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "DELETE FROM warnings WHERE user_id = ? AND guild_id = ?",
        (str(user_id), str(guild_id))
    )
    conn.commit()
    conn.close()

def log_mod_action(user_id, guild_id, action, reason, mod_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO mod_actions (user_id, guild_id, action, reason, mod_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(user_id), str(guild_id), action, reason, str(mod_id), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_filtered_words(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT word FROM word_filters WHERE guild_id = ?", (str(guild_id),))
    words = [row[0] for row in c.fetchall()]
    conn.close()
    return words

# ============ SECTION 6 - BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory trackers
spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)
nuke_action_tracker = defaultdict(list)
recent_messages = defaultdict(list)
mention_tracker = defaultdict(list)
caps_tracker = defaultdict(list)
pending_confirmations = {}

# ============ SECTION 7 - AI HELPERS ============
async def ask_groq(prompt, system="You are a helpful AI.", max_tokens=1000):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq error: {e}")
    return None

async def ask_groq_json(prompt, system="Respond only in JSON."):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data["choices"][0]["message"]["content"].strip()
                    if "```" in result:
                        result = result.split("```")[1]
                        if result.startswith("json"):
                            result = result[4:]
                    return json.loads(result.strip())
    except Exception as e:
        print(f"Groq JSON error: {e}")
    return None

# ============ SECTION 8 - AI COMMAND PARSER ============
async def parse_command(message_content, guild, author):
    """Parse natural language into a structured command using AI"""

    # Get server context
    channels = [c.name for c in guild.text_channels][:20]
    roles = [r.name for r in guild.roles][:20]
    categories = [c.name for c in guild.categories][:10]
    members = [m.name for m in guild.members if not m.bot][:20]

    prompt = f"""You are SentinelMod, a Discord bot command parser.

Server info:
- Channels: {', '.join(channels)}
- Roles: {', '.join(roles)}
- Categories: {', '.join(categories)}
- Members (sample): {', '.join(members)}

User message: "{message_content}"
User: {author.name}

Parse this into a command. Respond ONLY in this JSON format:
{{
    "command": "one of: create_channel, delete_channel, create_role, delete_role, create_category, delete_category, ban_user, kick_user, mute_user, unmute_user, warn_user, clear_warnings, lock_channel, unlock_channel, lockdown, unlock_server, slowmode, purge, add_role_to_user, remove_role_from_user, create_ticket, close_ticket, start_giveaway, create_poll, set_afk, backup_server, setup_server, warn_check, summarize, translate, add_word_filter, remove_word_filter, set_welcome, enable_feature, disable_feature, add_note, get_notes, set_autorole, raid_mode, help, chat, unknown",
    "needs_confirmation": true or false,
    "confirmation_message": "What to ask user to confirm (if needed)",
    "params": {{
        "name": "channel/role/category name if applicable",
        "target_user": "username or null",
        "reason": "reason if applicable or null",
        "duration": number in minutes or null,
        "category": "category name or null",
        "color": "hex color or null",
        "private": true or false,
        "amount": number or null,
        "prize": "giveaway prize or null",
        "winners": number or null,
        "question": "poll question or null",
        "options": ["option1", "option2"] or null,
        "language": "language to translate to or null",
        "text": "text to translate or null",
        "feature": "feature name or null",
        "word": "word to filter or null",
        "note": "note content or null",
        "channel": "channel name or null",
        "topic": "channel topic or null",
        "hoist": true or false,
        "mentionable": true or false
    }},
    "response": "friendly confirmation message to send after doing the action"
}}

dangerous_commands that need confirmation = [ban_user, kick_user, delete_channel, delete_role, delete_category, lockdown, purge]
safe_commands that dont need confirmation = everything else"""

    return await ask_groq_json(prompt)

# ============ SECTION 9 - COMMAND EXECUTOR ============
async def execute_command(parsed, message, guild, author):
    """Execute the parsed command"""

    command = parsed.get("command", "unknown")
    params = parsed.get("params", {})
    response_msg = parsed.get("response", "Done!")

    # Helper to find member
    def find_member(name):
        if not name:
            return None
        name = name.lower().replace("@", "")
        for m in guild.members:
            if m.name.lower() == name or m.display_name.lower() == name:
                return m
        return None

    # Helper to find or create channel
    async def get_or_create_channel(name, category_name=None, topic="", private=False):
        clean = name.lower().replace(" ", "-")
        existing = discord.utils.get(guild.text_channels, name=clean)
        if existing:
            return existing, False
        cat = None
        if category_name:
            cat = discord.utils.get(guild.categories, name=category_name)
            if not cat:
                cat = await guild.create_category(name=category_name)
        overwrites = {}
        if private:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        ch = await guild.create_text_channel(
            name=clean, category=cat, topic=topic, overwrites=overwrites
        )
        return ch, True

    # Helper to find or create role
    async def get_or_create_role(name, color_hex=None, hoist=False, mentionable=False):
        existing = discord.utils.get(guild.roles, name=name)
        if existing:
            return existing, False
        color = discord.Color.default()
        if color_hex:
            try:
                color = discord.Color(int(color_hex.replace("#", ""), 16))
            except:
                pass
        role = await guild.create_role(
            name=name, color=color, hoist=hoist, mentionable=mentionable
        )
        return role, True

    settings = get_guild_settings(guild.id)

    try:
        # ---- CREATE CHANNEL ----
        if command == "create_channel":
            name = params.get("name", "new-channel")
            ch, created = await get_or_create_channel(
                name,
                params.get("category"),
                params.get("topic", ""),
                params.get("private", False)
            )
            if created:
                return f"✅ Created channel {ch.mention}!"
            else:
                return f"⏭️ Channel {ch.mention} already exists!"

        # ---- DELETE CHANNEL ----
        elif command == "delete_channel":
            name = params.get("name") or params.get("channel")
            if not name:
                return "❌ Please specify a channel name."
            clean = name.lower().replace(" ", "-")
            ch = discord.utils.get(guild.text_channels, name=clean)
            if not ch:
                return f"❌ Channel **#{clean}** not found."
            await ch.delete(reason=f"Deleted by {author.name} via SentinelMod")
            return f"🗑️ Deleted channel **#{clean}**!"

        # ---- CREATE ROLE ----
        elif command == "create_role":
            name = params.get("name", "New Role")
            role, created = await get_or_create_role(
                name,
                params.get("color"),
                params.get("hoist", False),
                params.get("mentionable", False)
            )
            if created:
                return f"✅ Created role {role.mention}!"
            else:
                return f"⏭️ Role {role.mention} already exists!"

        # ---- DELETE ROLE ----
        elif command == "delete_role":
            name = params.get("name")
            if not name:
                return "❌ Please specify a role name."
            role = discord.utils.get(guild.roles, name=name)
            if not role:
                return f"❌ Role **{name}** not found."
            await role.delete(reason=f"Deleted by {author.name} via SentinelMod")
            return f"🗑️ Deleted role **{name}**!"

        # ---- CREATE CATEGORY ----
        elif command == "create_category":
            name = params.get("name", "New Category")
            existing = discord.utils.get(guild.categories, name=name)
            if existing:
                return f"⏭️ Category **{name}** already exists!"
            overwrites = {}
            if params.get("private"):
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    author: discord.PermissionOverwrite(read_messages=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True)
                }
            cat = await guild.create_category(name=name, overwrites=overwrites)
            return f"✅ Created category **{cat.name}**!"

        # ---- DELETE CATEGORY ----
        elif command == "delete_category":
            name = params.get("name")
            if not name:
                return "❌ Please specify a category name."
            cat = discord.utils.get(guild.categories, name=name)
            if not cat:
                return f"❌ Category **{name}** not found."
            await cat.delete(reason=f"Deleted by {author.name} via SentinelMod")
            return f"🗑️ Deleted category **{name}**!"

        # ---- BAN USER ----
        elif command == "ban_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "No reason provided"
            await guild.ban(target, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "BAN", reason, author.id)
            warn_count = add_warning(target.id, guild.id, reason, "critical")

            mod_embed = discord.Embed(
                title="🔨 User Banned",
                color=discord.Color.dark_red(),
                timestamp=datetime.now()
            )
            mod_embed.add_field(name="User", value=f"{target.mention} ({target.id})", inline=True)
            mod_embed.add_field(name="By", value=author.mention, inline=True)
            mod_embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, mod_embed)
            return f"🔨 Banned **{target.name}**. Reason: {reason}"

        # ---- KICK USER ----
        elif command == "kick_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "No reason provided"
            await guild.kick(target, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "KICK", reason, author.id)

            mod_embed = discord.Embed(
                title="👢 User Kicked",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            mod_embed.add_field(name="User", value=f"{target.mention}", inline=True)
            mod_embed.add_field(name="By", value=author.mention, inline=True)
            mod_embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, mod_embed)
            return f"👢 Kicked **{target.name}**. Reason: {reason}"

        # ---- MUTE USER ----
        elif command == "mute_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            duration = params.get("duration") or settings.get("mute_duration", 10)
            reason = params.get("reason") or "No reason provided"
            until = datetime.now() + timedelta(minutes=int(duration))
            await target.timeout(until, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "MUTE", reason, author.id)
            add_warning(target.id, guild.id, reason, "medium")

            mod_embed = discord.Embed(
                title="🔇 User Muted",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            mod_embed.add_field(name="User", value=target.mention, inline=True)
            mod_embed.add_field(name="Duration", value=f"{duration} mins", inline=True)
            mod_embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, mod_embed)

            try:
                dm = discord.Embed(
                    title="🔇 You have been muted",
                    description=f"You were muted in **{guild.name}**",
                    color=discord.Color.orange()
                )
                dm.add_field(name="Duration", value=f"{duration} minutes")
                dm.add_field(name="Reason", value=reason)
                await target.send(embed=dm)
            except:
                pass

            return f"🔇 Muted **{target.name}** for {duration} minutes. Reason: {reason}"

        # ---- UNMUTE USER ----
        elif command == "unmute_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            await target.timeout(None)
            return f"🔊 Unmuted **{target.name}**!"

        # ---- WARN USER ----
        elif command == "warn_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "No reason provided"
            warn_count = add_warning(target.id, guild.id, reason, "manual")
            log_mod_action(target.id, guild.id, "WARN", reason, author.id)

            try:
                dm = discord.Embed(
                    title="⚠️ Warning",
                    description=f"You received a warning in **{guild.name}**",
                    color=discord.Color.yellow()
                )
                dm.add_field(name="Reason", value=reason)
                dm.add_field(
                    name="Warnings",
                    value=f"{warn_count}/{settings.get('warn_ban', 5)}"
                )
                await target.send(embed=dm)
            except:
                pass

            mod_embed = discord.Embed(
                title="⚠️ User Warned",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            mod_embed.add_field(name="User", value=target.mention, inline=True)
            mod_embed.add_field(name="By", value=author.mention, inline=True)
            mod_embed.add_field(name="Reason", value=reason, inline=False)
            mod_embed.add_field(
                name="Total Warnings",
                value=f"{warn_count}/{settings.get('warn_ban', 5)}",
                inline=True
            )
            await alert_mods(guild, mod_embed)
            return f"⚠️ Warned **{target.name}**. ({warn_count} warnings) Reason: {reason}"

        # ---- CLEAR WARNINGS ----
        elif command == "clear_warnings":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            clear_warnings(target.id, guild.id)
            return f"✅ Cleared all warnings for **{target.name}**!"

        # ---- WARN CHECK ----
        elif command == "warn_check":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            warns = get_warnings(target.id, guild.id)
            if not warns:
                return f"✅ **{target.name}** has no warnings!"
            lines = [f"**{target.name}** has {len(warns)} warnings:"]
            for i, w in enumerate(warns[:5], 1):
                lines.append(f"#{i} [{w['severity'].upper()}] {w['reason']} - {w['timestamp'][:10]}")
            return "\n".join(lines)

        # ---- LOCK CHANNEL ----
        elif command == "lock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
            await ch.set_permissions(guild.default_role, send_messages=False)
            return f"🔒 Locked {ch.mention}!"

        # ---- UNLOCK CHANNEL ----
        elif command == "unlock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
            await ch.set_permissions(guild.default_role, send_messages=None)
            return f"🔓 Unlocked {ch.mention}!"

        # ---- LOCKDOWN ----
        elif command == "lockdown":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=False)
                    count += 1
                except:
                    pass
            embed = discord.Embed(
                title="🔒 SERVER LOCKDOWN",
                description=f"Server locked by {author.mention}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Channels Locked", value=str(count))
            await alert_mods(guild, embed)
            return f"🔒 Server locked! {count} channels affected."

        # ---- UNLOCK SERVER ----
        elif command == "unlock_server":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=None)
                    count += 1
                except:
                    pass
            return f"🔓 Server unlocked! {count} channels restored."

        # ---- SLOWMODE ----
        elif command == "slowmode":
            duration = int(params.get("duration") or 5)
            ch_name = params.get("channel")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
            await ch.edit(slowmode_delay=duration)
            return f"🐌 Slowmode set to {duration}s in {ch.mention}!"

        # ---- PURGE ----
        elif command == "purge":
            amount = int(params.get("amount") or 10)
            amount = min(amount, 100)
            deleted = await message.channel.purge(limit=amount + 1)
            return f"🗑️ Deleted {len(deleted)-1} messages!"

        # ---- ADD ROLE TO USER ----
        elif command == "add_role_to_user":
            target = find_member(params.get("target_user"))
            role_name = params.get("name")
            if not target or not role_name:
                return "❌ Please specify user and role."
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                return f"❌ Role **{role_name}** not found."
            await target.add_roles(role)
            return f"✅ Added **{role.name}** to {target.mention}!"

        # ---- REMOVE ROLE FROM USER ----
        elif command == "remove_role_from_user":
            target = find_member(params.get("target_user"))
            role_name = params.get("name")
            if not target or not role_name:
                return "❌ Please specify user and role."
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                return f"❌ Role **{role_name}** not found."
            await target.remove_roles(role)
            return f"✅ Removed **{role.name}** from {target.mention}!"

        # ---- START GIVEAWAY ----
        elif command == "start_giveaway":
            prize = params.get("prize") or "Mystery Prize"
            duration = int(params.get("duration") or 60)
            winners = int(params.get("winners") or 1)
            end_time = datetime.now() + timedelta(minutes=duration)

            embed = discord.Embed(
                title="🎉 GIVEAWAY!",
                description=f"**Prize:** {prize}\n\nReact with 🎉 to enter!",
                color=discord.Color.gold(),
                timestamp=end_time
            )
            embed.add_field(name="Winners", value=str(winners), inline=True)
            embed.add_field(name="Hosted by", value=author.mention, inline=True)
            embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            embed.set_footer(text="Ends at")

            msg = await message.channel.send(embed=embed)
            await msg.add_reaction("🎉")

            conn = get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO giveaways
                (guild_id, channel_id, message_id, prize, winners, end_time, host_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(guild.id), str(message.channel.id), str(msg.id),
                prize, winners, end_time.isoformat(), str(author.id)
            ))
            conn.commit()
            conn.close()
            return f"🎉 Giveaway started for **{prize}**! Ends in {duration} minutes."

        # ---- CREATE POLL ----
        elif command == "create_poll":
            question = params.get("question") or "Poll"
            options = params.get("options") or ["Yes", "No"]
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

            embed = discord.Embed(
                title=f"📊 {question}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            for i, opt in enumerate(options[:5]):
                embed.add_field(name=f"{emojis[i]} {opt}", value="\u200b", inline=False)

            msg = await message.channel.send(embed=embed)
            for i in range(len(options[:5])):
                await msg.add_reaction(emojis[i])
            return None  # Already sent embed

        # ---- SET AFK ----
        elif command == "set_afk":
            reason = params.get("reason") or "AFK"
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO afk_users (user_id, guild_id, reason, timestamp)
                VALUES (?, ?, ?, ?)
            """, (str(author.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💤 Set your AFK: **{reason}**"

        # ---- BACKUP SERVER ----
        elif command == "backup_server":
            roles_data = [{
                "name": r.name,
                "color": str(r.color),
                "hoist": r.hoist,
                "permissions": r.permissions.value
            } for r in guild.roles if r.name != "@everyone"]

            channels_data = [{
                "name": c.name,
                "topic": c.topic,
                "category": c.category.name if c.category else None
            } for c in guild.text_channels]

            backup = {
                "roles": roles_data,
                "channels": channels_data,
                "timestamp": datetime.now().isoformat()
            }

            conn = get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO backup_data (guild_id, backup_type, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (str(guild.id), "full", json.dumps(backup), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💾 Backed up {len(roles_data)} roles and {len(channels_data)} channels!"

        # ---- SETUP SERVER ----
        elif command == "setup_server":
            results = await setup_server(guild)
            return f"🛡️ Setup complete!\n" + "\n".join(results[:10])

        # ---- SUMMARIZE ----
        elif command == "summarize":
            amount = int(params.get("amount") or 20)
            amount = min(amount, 50)
            msgs = []
            async for msg in message.channel.history(limit=amount):
                if not msg.author.bot:
                    msgs.append(f"{msg.author.display_name}: {msg.content}")

            if not msgs:
                return "❌ No messages to summarize."

            conversation = "\n".join(reversed(msgs))
            summary = await ask_groq(
                f"Summarize in 3-5 bullet points:\n\n{conversation}",
                "You are a summarization AI."
            )
            return f"📝 **Summary:**\n{summary}"

        # ---- TRANSLATE ----
        elif command == "translate":
            text = params.get("text")
            language = params.get("language") or "English"
            if not text:
                return "❌ Please provide text to translate."
            translation = await ask_groq(
                f"Translate to {language}. Reply with ONLY the translation:\n\n{text}",
                "You are a translation AI."
            )
            return f"🌐 **Translation ({language}):**\n{translation}"

        # ---- ADD WORD FILTER ----
        elif command == "add_word_filter":
            word = params.get("word")
            if not word:
                return "❌ Please specify a word."
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)",
                (str(guild.id), word.lower())
            )
            conn.commit()
            conn.close()
            return f"✅ Added **{word}** to word filter!"

        # ---- REMOVE WORD FILTER ----
        elif command == "remove_word_filter":
            word = params.get("word")
            if not word:
                return "❌ Please specify a word."
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "DELETE FROM word_filters WHERE guild_id = ? AND word = ?",
                (str(guild.id), word.lower())
            )
            conn.commit()
            conn.close()
            return f"✅ Removed **{word}** from word filter!"

        # ---- ADD NOTE ----
        elif command == "add_note":
            target = find_member(params.get("target_user"))
            note = params.get("note")
            if not target or not note:
                return "❌ Please specify user and note."
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO user_notes (guild_id, user_id, note, mod_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (str(guild.id), str(target.id), note, str(author.id), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"📝 Added note for **{target.name}**: {note}"

        # ---- GET NOTES ----
        elif command == "get_notes":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "SELECT * FROM user_notes WHERE guild_id = ? AND user_id = ?",
                (str(guild.id), str(target.id))
            )
            notes = c.fetchall()
            conn.close()
            if not notes:
                return f"📝 No notes for **{target.name}**."
            lines = [f"📝 **Notes for {target.name}:**"]
            for n in notes:
                lines.append(f"• {n['note']} - {n['timestamp'][:10]}")
            return "\n".join(lines)

        # ---- SET AUTOROLE ----
        elif command == "set_autorole":
            role_name = params.get("name")
            if not role_name:
                return "❌ Please specify a role."
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                return f"❌ Role **{role_name}** not found."
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO auto_roles (guild_id, role_id) VALUES (?, ?)",
                (str(guild.id), str(role.id))
            )
            conn.commit()
            conn.close()
            return f"✅ **{role.name}** will now be given to new members!"

        # ---- RAID MODE ----
        elif command == "raid_mode":
            feature = params.get("feature") or ""
            status = "on" in feature.lower() or "enable" in feature.lower()
            raid_mode_active[guild.id] = status
            return f"🚨 Raid mode is now **{'ON' if status else 'OFF'}**!"

        # ---- ENABLE/DISABLE FEATURE ----
        elif command == "enable_feature" or command == "disable_feature":
            feature = params.get("feature", "").lower()
            enabled = command == "enable_feature"
            feature_map = {
                "welcome": "welcome_enabled",
                "anti_nuke": "anti_nuke_enabled",
                "invite_block": "invite_block",
                "link_scan": "link_scan",
                "slowmode_ai": "slowmode_ai",
                "pre_conflict": "pre_conflict",
                "image_scan": "scan_images",
                "caps_filter": "caps_filter",
                "mention_spam": "mention_spam",
                "alt_detection": "alt_detection"
            }
            db_key = feature_map.get(feature)
            if not db_key:
                return f"❌ Unknown feature: **{feature}**"
            conn = get_db()
            c = conn.cursor()
            c.execute(
                f"UPDATE guild_settings SET {db_key} = ? WHERE guild_id = ?",
                (1 if enabled else 0, str(guild.id))
            )
            conn.commit()
            conn.close()
            return f"{'✅ Enabled' if enabled else '❌ Disabled'} **{feature}**!"

        # ---- SET WELCOME ----
        elif command == "set_welcome":
            ch_name = params.get("channel") or params.get("name")
            if not ch_name:
                return "❌ Please specify a channel."
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "UPDATE guild_settings SET welcome_channel = ? WHERE guild_id = ?",
                (ch_name.lower().replace(" ", "-"), str(guild.id))
            )
            conn.commit()
            conn.close()
            return f"✅ Welcome channel set to **#{ch_name}**!"

        # ---- HELP ----
        elif command == "help":
            return """🛡️ **SentinelMod - What I can do:**

**🔧 Server Management**
• "make a channel called gaming"
• "create a private channel called staff"
• "delete the channel called old-chat"
• "make a role called VIP with red color"
• "create a category called Gaming"
• "add the VIP role to @user"

**🔨 Moderation**
• "ban @user for spamming"
• "kick @user for being rude"
• "mute @user for 10 minutes"
• "warn @user for bad language"
• "check warnings for @user"
• "clear warnings for @user"
• "purge 20 messages"
• "lock this channel"
• "lockdown the server"

**🔍 AI Features**
• "summarize the last 50 messages"
• "translate [text] to Spanish"
• "add word filter: badword"

**🎉 Fun**
• "start a giveaway for Nitro lasting 60 minutes"
• "create a poll: favorite color? Red, Blue, Green"
• "set my AFK to studying"

**💾 Utility**
• "backup the server"
• "setup the server"
• "enable invite block"
• "disable welcome messages"
• "set autorole to Member" """

        # ---- CHAT ----
        elif command == "chat":
            response = await ask_groq(
                message_content,
                "You are SentinelMod, a helpful and friendly Discord bot. "
                "Be concise, helpful and friendly."
            )
            return response

        else:
            response = await ask_groq(
                message_content,
                "You are SentinelMod, a helpful Discord bot assistant. "
                "Answer helpfully and concisely."
            )
            return response

    except discord.Forbidden:
        return "❌ I don't have permission to do that!"
    except Exception as e:
        print(f"Execute error: {e}")
        return f"❌ Something went wrong: {str(e)}"

# ============ SECTION 10 - CONFIRMATION SYSTEM ============
class ConfirmView(discord.ui.View):
    def __init__(self, parsed, original_message, guild, author):
        super().__init__(timeout=30)
        self.parsed = parsed
        self.original_message = original_message
        self.guild = guild
        self.author = author
        self.result = None

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Only the person who asked can confirm.", ephemeral=True
            )
            return
        await interaction.response.defer()
        result = await execute_command(
            self.parsed, self.original_message, self.guild, self.author
        )
        if result:
            await interaction.followup.send(result)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Only the person who asked can cancel.", ephemeral=True
            )
            return
        await interaction.response.send_message("❌ Action cancelled.")
        self.stop()

# ============ SECTION 11 - SERVER SETUP ============
async def setup_server(guild):
    results = []
    settings = get_guild_settings(guild.id)

    # Roles
    for role_name, color, hoist in [
        (settings["mod_role_name"], discord.Color.red(), True),
        ("Muted", discord.Color.dark_gray(), False),
        ("Member", discord.Color.blue(), False)
    ]:
        existing = discord.utils.get(guild.roles, name=role_name)
        if not existing:
            try:
                await guild.create_role(
                    name=role_name, color=color, hoist=hoist, mentionable=True
                )
                results.append(f"✅ Created role: **{role_name}**")
            except:
                results.append(f"❌ Failed role: **{role_name}**")
        else:
            results.append(f"⏭️ Role exists: **{role_name}**")

    # Sentinel category
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    sentinel_cat = discord.utils.get(guild.categories, name="🛡️ SENTINELAI")
    if not sentinel_cat:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                )
            sentinel_cat = await guild.create_category(
                name="🛡️ SENTINELAI", overwrites=overwrites
            )
            results.append("✅ Created category: **🛡️ SENTINELAI**")
        except:
            results.append("❌ Failed category: **🛡️ SENTINELAI**")
    else:
        results.append("⏭️ Category exists: **🛡️ SENTINELAI**")

    # Sentinel channels
    for ch_name, topic in [
        (settings["log_channel"], "Moderation logs"),
        (settings["raid_channel"], "Raid alerts"),
        ("sentinel-nuke-alerts", "Anti-nuke alerts"),
        ("sentinel-audit", "Audit logs"),
        ("sentinel-reports", "User reports")
    ]:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if not existing:
            try:
                await guild.create_text_channel(
                    name=ch_name, category=sentinel_cat, topic=topic
                )
                results.append(f"✅ Created channel: **#{ch_name}**")
            except:
                results.append(f"❌ Failed channel: **#{ch_name}**")
        else:
            results.append(f"⏭️ Channel exists: **#{ch_name}**")

    # Public channels
    for ch_name, topic in [
        ("welcome", "Welcome new members"),
        ("rules", "Server rules"),
        ("announcements", "Server announcements"),
        ("general", "General chat")
    ]:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if not existing:
            try:
                await guild.create_text_channel(name=ch_name, topic=topic)
                results.append(f"✅ Created channel: **#{ch_name}**")
            except:
                results.append(f"❌ Failed channel: **#{ch_name}**")
        else:
            results.append(f"⏭️ Channel exists: **#{ch_name}**")

    # Ticket system
    ticket_cat = discord.utils.get(guild.categories, name="🎫 TICKETS")
    if not ticket_cat:
        try:
            ticket_cat = await guild.create_category(name="🎫 TICKETS")
            results.append("✅ Created category: **🎫 TICKETS**")
        except:
            results.append("❌ Failed category: **🎫 TICKETS**")

    ticket_ch = discord.utils.get(guild.text_channels, name="create-ticket")
    if not ticket_ch and ticket_cat:
        try:
            ticket_ch = await guild.create_text_channel(
                name="create-ticket",
                category=ticket_cat,
                topic="Create a support ticket"
            )
            embed = discord.Embed(
                title="🎫 Support Tickets",
                description="Click below to create a support ticket.",
                color=discord.Color.blue()
            )
            await ticket_ch.send(embed=embed, view=TicketView())
            results.append("✅ Created channel: **#create-ticket**")
        except:
            results.append("❌ Failed channel: **#create-ticket**")

    return results

# ============ SECTION 12 - MODERATION SYSTEMS ============
async def alert_mods(guild, embed, channel_name=None):
    settings = get_guild_settings(guild.id)
    log_name = channel_name or settings["log_channel"]
    log_channel = discord.utils.get(guild.text_channels, name=log_name)
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    if log_channel:
        ping = mod_role.mention if mod_role else ""
        await log_channel.send(content=f"🚨 {ping}", embed=embed)

async def check_spam(message, settings):
    key = f"{message.author.id}:{message.guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    window = settings.get("spam_window", 5)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < window]
    return len(spam_tracker[key]) >= settings.get("spam_limit", 5)

async def handle_spam(message, settings):
    user = message.author
    guild = message.guild
    try:
        deleted = await message.channel.purge(
            limit=10, check=lambda m: m.author == user
        )
    except:
        deleted = []
    try:
        until = datetime.now() + timedelta(minutes=settings.get("mute_duration", 10))
        await user.timeout(until, reason="Spam detected")
    except:
        pass
    warn_count = add_warning(user.id, guild.id, "Spam detected", "medium")
    log_mod_action(user.id, guild.id, "SPAM_MUTE", "Spam", bot.user.id)
    try:
        await user.send(embed=discord.Embed(
            title="⚠️ Spam Detected",
            description=f"You were muted for spamming in **{guild.name}**",
            color=discord.Color.orange()
        ))
    except:
        pass
    embed = discord.Embed(
        title="🔇 Spam Handled",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=f"{user.mention}", inline=True)
    embed.add_field(name="Deleted", value=str(len(deleted)), inline=True)
    embed.add_field(name="Warnings", value=str(warn_count), inline=True)
    await alert_mods(guild, embed)

async def check_raid(member):
    guild = member.guild
    settings = get_guild_settings(guild.id)
    now = time.time()
    raid_tracker[guild.id].append({"time": now, "member": member})
    window = settings.get("raid_window", 10)
    raid_tracker[guild.id] = [
        j for j in raid_tracker[guild.id] if now - j["time"] < window
    ]
    return len(raid_tracker[guild.id]) >= settings.get("raid_limit", 10)

async def handle_raid(guild, new_member):
    settings = get_guild_settings(guild.id)
    if not raid_mode_active[guild.id]:
        raid_mode_active[guild.id] = True
        raid_channel = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
        if raid_channel:
            embed = discord.Embed(
                title="🚨 RAID DETECTED",
                description="Auto-defense activated!",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            ping = mod_role.mention if mod_role else ""
            await raid_channel.send(content=f"🚨 {ping} RAID!", embed=embed)
        await asyncio.sleep(300)
        raid_mode_active[guild.id] = False
    account_age = (datetime.now() - new_member.created_at.replace(tzinfo=None)).days
    if account_age < settings.get("min_account_age", 7):
        try:
            await new_member.kick(reason="Raid protection")
        except:
            pass

async def check_nuke(guild, action_type, executor):
    if executor == guild.me:
        return False
    key = f"{guild.id}:{executor.id}"
    now = time.time()
    nuke_action_tracker[key].append({"time": now, "action": action_type})
    nuke_action_tracker[key] = [
        a for a in nuke_action_tracker[key] if now - a["time"] < 10
    ]
    return len(nuke_action_tracker[key]) >= 3

async def handle_nuke(guild, executor, action_type):
    settings = get_guild_settings(guild.id)
    try:
        await guild.ban(executor, reason="Anti-nuke triggered")
    except:
        pass
    nuke_channel = discord.utils.get(guild.text_channels, name="sentinel-nuke-alerts")
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    embed = discord.Embed(
        title="💣 NUKE ATTEMPT STOPPED",
        description=f"**{executor}** was attempting to nuke!",
        color=discord.Color.dark_red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=f"{executor} ({executor.id})", inline=True)
    embed.add_field(name="Action", value=action_type, inline=True)
    embed.add_field(name="Result", value="🔨 BANNED", inline=True)
    ping = mod_role.mention if mod_role else ""
    if nuke_channel:
        await nuke_channel.send(content=f"💣 {ping}", embed=embed)

async def check_toxicity(content, context="", sensitivity=0.7):
    prompt = f"""Analyze this Discord message for toxicity.

Context:
{context}

Message: "{content}"

Respond ONLY in JSON:
{{
    "toxic": true or false,
    "severity": "none" or "low" or "medium" or "high" or "critical",
    "category": "none" or "harassment" or "hate_speech" or "threat" or "spam" or "sexual" or "bullying" or "manipulation" or "slur" or "doxxing" or "self_harm" or "extremism",
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation",
    "sentiment": "positive" or "neutral" or "negative" or "hostile",
    "bypass_detected": true or false
}}"""
    return await ask_groq_json(prompt)

async def check_word_filter(content, guild_id):
    words = get_filtered_words(guild_id)
    content_lower = content.lower()
    # Check for bypasses like l33t speak
    normalized = content_lower
    normalized = normalized.replace("@", "a").replace("0", "o").replace("1", "i")
    normalized = normalized.replace("3", "e").replace("$", "s").replace("5", "s")
    for word in words:
        if word in content_lower or word in normalized:
            return True, word
    return False, None

async def check_caps(content):
    if len(content) < 10:
        return False
    caps = sum(1 for c in content if c.isupper())
    return (caps / len(content)) > 0.7

async def check_mention_spam(message):
    if len(message.mentions) >= 5:
        return True
    key = f"{message.author.id}:{message.guild.id}"
    now = time.time()
    mention_tracker[key].append(now)
    mention_tracker[key] = [t for t in mention_tracker[key] if now - t < 10]
    return len(mention_tracker[key]) >= 5

async def check_alt_account(member, settings):
    account_age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    return account_age < settings.get("min_account_age", 7)

async def punish_user(message, severity, reason, analysis):
    user = message.author
    guild = message.guild
    settings = get_guild_settings(guild.id)
    warn_count = add_warning(user.id, guild.id, reason, severity)
    log_mod_action(user.id, guild.id, "AI_WARN", reason, bot.user.id)
    try:
        await message.delete()
    except:
        pass
    try:
        embed = discord.Embed(
            title="🛡️ Message Removed",
            description=f"{user.mention} your message was removed.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason)
        await message.channel.send(embed=embed, delete_after=8)
    except:
        pass
    try:
        dm = discord.Embed(
            title="⚠️ Warning",
            description=f"Message removed in **{guild.name}**",
            color=discord.Color.yellow()
        )
        dm.add_field(name="Reason", value=reason)
        dm.add_field(
            name="Warnings",
            value=f"{warn_count}/{settings.get('warn_ban', 5)}"
        )
        await user.send(embed=dm)
    except:
        pass
    colors = {
        "low": discord.Color.yellow(),
        "medium": discord.Color.orange(),
        "high": discord.Color.red(),
        "critical": discord.Color.dark_red()
    }
    mod_embed = discord.Embed(
        title="🚨 AI Moderation Alert",
        color=colors.get(severity, discord.Color.red()),
        timestamp=datetime.now()
    )
    mod_embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
    mod_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    mod_embed.add_field(name="Severity", value=severity.upper(), inline=True)
    mod_embed.add_field(name="Category", value=analysis.get("category", "unknown"), inline=True)
    mod_embed.add_field(name="Confidence", value=f"{analysis.get('confidence', 0)*100:.0f}%", inline=True)
    mod_embed.add_field(name="Bypass", value="Yes ⚠️" if analysis.get("bypass_detected") else "No", inline=True)
    mod_embed.add_field(name="Warnings", value=f"{warn_count}/{settings.get('warn_ban', 5)}", inline=True)
    mod_embed.add_field(name="Message", value=f"||{message.content[:500]}||", inline=False)
    mod_embed.add_field(name="Reason", value=reason, inline=False)
    action = "⚠️ Warning"
    if warn_count >= settings.get("warn_mute", 3) and warn_count < settings.get("warn_ban", 5):
        try:
            until = datetime.now() + timedelta(minutes=settings.get("mute_duration", 10))
            await user.timeout(until, reason=f"AI: {reason}")
            action = f"🔇 Muted {settings.get('mute_duration', 10)} mins"
            log_mod_action(user.id, guild.id, "AI_MUTE", reason, bot.user.id)
        except:
            action = "❌ Could not mute"
    if warn_count >= settings.get("warn_ban", 5):
        try:
            await guild.ban(user, reason=f"AI: {reason}")
            action = "🔨 BANNED"
            log_mod_action(user.id, guild.id, "AI_BAN", reason, bot.user.id)
        except:
            action = "❌ Could not ban"
    mod_embed.add_field(name="Action", value=action, inline=False)
    await alert_mods(guild, mod_embed)

# ============ SECTION 13 - TICKET SYSTEM ============
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class TicketModal(discord.ui.Modal, title="Create Support Ticket"):
    reason = discord.ui.TextInput(
        label="Describe your issue",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        settings = get_guild_settings(guild.id)
        ticket_cat = discord.utils.get(guild.categories, name="🎫 TICKETS")
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])

        ticket_name = f"ticket-{user.name.lower()[:10]}-{random.randint(1000, 9999)}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )
        try:
            channel = await guild.create_text_channel(
                name=ticket_name, category=ticket_cat, overwrites=overwrites
            )
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                INSERT INTO tickets (guild_id, user_id, channel_id, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(guild.id), str(user.id), str(channel.id),
                str(self.reason.value), datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            embed = discord.Embed(
                title="🎫 Ticket Created",
                description=f"Hello {user.mention}! Support will be with you shortly.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Issue", value=str(self.reason.value))
            ping = mod_role.mention if mod_role else ""
            await channel.send(
                content=f"{user.mention} {ping}",
                embed=embed,
                view=CloseTicketView()
            )
            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "UPDATE tickets SET status = 'closed' WHERE channel_id = ?",
            (str(interaction.channel.id),)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ============ SECTION 14 - BACKGROUND TASKS ============
@tasks.loop(minutes=1)
async def check_giveaways():
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM giveaways WHERE active = 1 AND end_time <= ?",
        (datetime.now().isoformat(),)
    )
    ended = [dict(row) for row in c.fetchall()]
    conn.close()

    for giveaway in ended:
        try:
            guild = bot.get_guild(int(giveaway["guild_id"]))
            if not guild:
                continue
            channel = guild.get_channel(int(giveaway["channel_id"]))
            if not channel:
                continue
            message = await channel.fetch_message(int(giveaway["message_id"]))
            if not message:
                continue
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot] if reaction else []
            if not users:
                await channel.send("❌ No valid entries for the giveaway!")
            else:
                num_winners = min(giveaway["winners"], len(users))
                winners = random.sample(users, num_winners)
                mentions = ", ".join(w.mention for w in winners)
                embed = discord.Embed(
                    title="🎉 Giveaway Ended!",
                    description=f"**Prize:** {giveaway['prize']}\n**Winner(s):** {mentions}",
                    color=discord.Color.gold()
                )
                await channel.send(content=f"🎉 {mentions}!", embed=embed)
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "UPDATE giveaways SET active = 0 WHERE id = ?",
                (giveaway["id"],)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Giveaway error: {e}")

# ============ SECTION 15 - BOT EVENTS ============
@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 SentinelMod ONLINE")
    print(f"📛 Bot: {bot.user}")
    print(f"🏠 Servers: {len(bot.guilds)}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for guild in bot.guilds:
        init_guild_settings(guild.id)
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    check_giveaways.start()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="your server 🛡️ | @mention me!"
        )
    )

@bot.event
async def on_guild_join(guild):
    print(f"📥 Joined: {guild.name}")
    init_guild_settings(guild.id)
    await setup_server(guild)

@bot.event
async def on_member_join(member):
    guild = member.guild
    settings = get_guild_settings(guild.id)
    account_age = (datetime.now() - member.created_at.replace(tzinfo=None)).days

    is_raid = await check_raid(member)
    if is_raid:
        await handle_raid(guild, member)
        return

    # Auto roles
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role_id FROM auto_roles WHERE guild_id = ?", (str(guild.id),))
    for row in c.fetchall():
        role = guild.get_role(int(row[0]))
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    conn.close()

    # Alert suspicious accounts
    min_age = settings.get("min_account_age", 7)
    if account_age < min_age:
        raid_channel = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
        if raid_channel:
            embed = discord.Embed(
                title="⚠️ Suspicious Account Joined",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{member.mention}", inline=True)
            embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
            await raid_channel.send(embed=embed)

    # Welcome message
    if settings.get("welcome_enabled", 1):
        welcome_ch = discord.utils.get(
            guild.text_channels,
            name=settings.get("welcome_channel", "welcome")
        )
        if welcome_ch:
            welcome = await ask_groq(
                f"Write a short warm welcome for {member.display_name} "
                f"joining {guild.name} (member #{guild.member_count}). "
                f"2-3 sentences max.",
                "You are a friendly Discord bot."
            )
            if welcome:
                embed = discord.Embed(
                    title=f"👋 Welcome to {guild.name}!",
                    description=welcome,
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Member #{guild.member_count}")
                await welcome_ch.send(content=member.mention, embed=embed)

@bot.event
async def on_audit_log_entry_create(entry):
    guild = entry.guild
    settings = get_guild_settings(guild.id)
    if not settings.get("anti_nuke_enabled", 1):
        return
    nuke_actions = [
        discord.AuditLogAction.channel_delete,
        discord.AuditLogAction.role_delete,
        discord.AuditLogAction.ban,
        discord.AuditLogAction.kick,
        discord.AuditLogAction.webhook_create
    ]
    if entry.action in nuke_actions and entry.user:
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
        if entry.user == guild.me:
            return
        if mod_role and mod_role in entry.user.roles:
            return
        is_nuke = await check_nuke(guild, str(entry.action), entry.user)
        if is_nuke:
            await handle_nuke(guild, entry.user, str(entry.action))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.guild:
        return

    settings = get_guild_settings(message.guild.id)
    mod_role = discord.utils.get(message.guild.roles, name=settings["mod_role_name"])
    is_mod = mod_role and mod_role in message.author.roles
    is_admin = message.author.guild_permissions.administrator

    # ============ BOT MENTION HANDLER ============
    if bot.user in message.mentions:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content:
            await message.reply(
                "👋 Hey! Mention me with a command. Try: "
                f"`@{BOT_NAME} help`"
            )
            return

        # Check permissions
        if not is_mod and not is_admin:
            # Non-mods can only chat and ask questions
            response = await ask_groq(
                content,
                "You are SentinelMod, a friendly Discord bot. "
                "Be helpful and friendly. Don't perform server actions."
            )
            if response:
                await message.reply(response[:2000])
            return

        # Parse the command
        async with message.channel.typing():
            parsed = await parse_command(content, message.guild, message.author)

        if not parsed:
            await message.reply("❌ I couldn't understand that. Try again!")
            return

        command = parsed.get("command", "unknown")
        needs_confirmation = parsed.get("needs_confirmation", False)

        # Send confirmation if needed
        if needs_confirmation:
            confirm_msg = parsed.get(
                "confirmation_message",
                f"Are you sure you want to **{command.replace('_', ' ')}**?"
            )
            embed = discord.Embed(
                title="⚠️ Confirm Action",
                description=confirm_msg,
                color=discord.Color.orange()
            )
            view = ConfirmView(parsed, message, message.guild, message.author)
            await message.reply(embed=embed, view=view)
        else:
            async with message.channel.typing():
                result = await execute_command(
                    parsed, message, message.guild, message.author
                )
            if result:
                await message.reply(result[:2000])

        await bot.process_commands(message)
        return

    # ============ MODERATION CHECKS ============
    # Skip mods
    if is_mod or is_admin:
        await bot.process_commands(message)
        return

    # ---- AFK CHECK ----
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM afk_users WHERE guild_id = ?",
        (str(message.guild.id),)
    )
    afk_users = {row["user_id"]: dict(row) for row in c.fetchall()}
    conn.close()

    if str(message.author.id) in afk_users:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "DELETE FROM afk_users WHERE user_id = ? AND guild_id = ?",
            (str(message.author.id), str(message.guild.id))
        )
        conn.commit()
        conn.close()
        try:
            await message.channel.send(
                f"👋 Welcome back {message.author.mention}! AFK removed.",
                delete_after=5
            )
        except:
            pass

    for mentioned in message.mentions:
        if str(mentioned.id) in afk_users:
            afk_data = afk_users[str(mentioned.id)]
            await message.channel.send(
                f"💤 {mentioned.mention} is AFK: **{afk_data['reason']}**",
                delete_after=10
            )

    # ---- ANTI-SPAM ----
    is_spam = await check_spam(message, settings)
    if is_spam:
        await handle_spam(message, settings)
        return

    # ---- MENTION SPAM ----
    if settings.get("mention_spam", 1):
        if await check_mention_spam(message):
            try:
                await message.delete()
            except:
                pass
            warn_count = add_warning(
                message.author.id, message.guild.id, "Mention spam", "high"
            )
            await message.channel.send(
                f"⚠️ {message.author.mention} Stop mention spamming!",
                delete_after=5
            )
            if warn_count >= settings.get("warn_mute", 3):
                try:
                    until = datetime.now() + timedelta(minutes=10)
                    await message.author.timeout(until, reason="Mention spam")
                except:
                    pass
            return

    # ---- CAPS FILTER ----
    if settings.get("caps_filter", 1) and len(message.content) > 10:
        if await check_caps(message.content):
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(
                f"⚠️ {message.author.mention} Please don't use excessive caps!",
                delete_after=5
            )
            return

    # ---- WORD FILTER ----
    filtered, word = await check_word_filter(message.content, message.guild.id)
    if filtered:
        try:
            await message.delete()
        except:
            pass
        warn_count = add_warning(
            message.author.id, message.guild.id, f"Used filtered word", "medium"
        )
        await message.channel.send(
            f"⚠️ {message.author.mention} That word is not allowed here!",
            delete_after=5
        )
        embed = discord.Embed(
            title="🔤 Word Filter Triggered",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="User", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Warnings", value=str(warn_count), inline=True)
        await alert_mods(message.guild, embed)
        return

    # ---- INVITE LINK BLOCKER ----
    if settings.get("invite_block", 0):
        pattern = r'(discord\.gg|discord\.com\/invite)\/[a-zA-Z0-9]+'
        if re.search(pattern, message.content):
            try:
                await message.delete()
            except:
                pass
            warn_count = add_warning(
                message.author.id, message.guild.id, "Posted invite link", "medium"
            )
            await message.channel.send(
                f"⚠️ {message.author.mention} No invite links!",
                delete_after=5
            )
            return

    # ---- LINK SCANNER ----
    if settings.get("link_scan", 1) and "http" in message.content:
        suspicious_domains = [
            "grabify", "iplogger", "discord.gift", "steamcommunity.ru",
            "discordapp.io", "discordnitro", "free-nitro", "phish", "scam",
            "discord.com.ru", "dlscord"
        ]
        for domain in suspicious_domains:
            if domain in message.content.lower():
                try:
                    await message.delete()
                except:
                    pass
                warn_count = add_warning(
                    message.author.id, message.guild.id,
                    f"Suspicious link detected", "high"
                )
                embed = discord.Embed(
                    title="🔗 Suspicious Link Removed",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="User", value=message.author.mention, inline=True)
                embed.add_field(name="Domain", value=domain, inline=True)
                await alert_mods(message.guild, embed)
                await message.channel.send(
                    f"⚠️ {message.author.mention} Suspicious link removed!",
                    delete_after=5
                )
                return

    # ---- IMAGE SCAN ----
    if settings.get("scan_images", 1) and message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext)
                   for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                suspicious_patterns = ["nsfw", "explicit", "porn", "gore", "nude"]
                if any(p in attachment.filename.lower() for p in suspicious_patterns):
                    try:
                        await message.delete()
                    except:
                        pass
                    warn_count = add_warning(
                        message.author.id, message.guild.id, "Suspicious image", "high"
                    )
                    embed = discord.Embed(
                        title="🖼️ Suspicious Image Removed",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="User", value=message.author.mention, inline=True)
                    await alert_mods(message.guild, embed)
                    return

    # ---- SKIP SHORT MESSAGES ----
    if len(message.content) < 3:
        await bot.process_commands(message)
        return

    # ---- PRE-CONFLICT DETECTION ----
    channel_key = f"{message.guild.id}:{message.channel.id}"
    recent_messages[channel_key].append({
        "author": message.author.name,
        "content": message.content,
        "time": time.time()
    })
    recent_messages[channel_key] = [
        m for m in recent_messages[channel_key] if time.time() - m["time"] < 60
    ]

    if settings.get("pre_conflict", 1) and len(recent_messages[channel_key]) >= 6:
        msgs_text = "\n".join([
            f"{m['author']}: {m['content']}"
            for m in recent_messages[channel_key][-10:]
        ])
        conflict = await ask_groq_json(
            f"""Analyze this conversation for escalating conflict.

{msgs_text}

JSON only:
{{
    "escalating": true or false,
    "severity": "none" or "mild" or "moderate" or "severe",
    "users_involved": ["user1", "user2"],
    "reason": "brief reason"
}}"""
        )
        if conflict and conflict.get("escalating"):
            severity = conflict.get("severity", "mild")
            if severity in ["moderate", "severe"]:
                embed = discord.Embed(
                    title="⚠️ Conversation Getting Heated",
                    description="Please keep things civil and respectful.",
                    color=discord.Color.yellow()
                )
                await message.channel.send(embed=embed, delete_after=30)
                if severity == "severe":
                    mod_embed = discord.Embed(
                        title="🔥 Conflict Alert",
                        color=discord.Color.orange(),
                        timestamp=datetime.now()
                    )
                    mod_embed.add_field(
                        name="Channel", value=message.channel.mention, inline=True
                    )
                    mod_embed.add_field(
                        name="Severity", value=severity.upper(), inline=True
                    )
                    mod_embed.add_field(
                        name="Users",
                        value=", ".join(conflict.get("users_involved", [])),
                        inline=False
                    )
                    await alert_mods(message.guild, mod_embed)
                    if settings.get("slowmode_ai", 1):
                        try:
                            await message.channel.edit(slowmode_delay=10)
                            await asyncio.sleep(60)
                            await message.channel.edit(slowmode_delay=0)
                        except:
                            pass

    # ---- AI TOXICITY CHECK ----
    context = ""
    try:
        history = []
        async for msg in message.channel.history(limit=5, before=message):
            if not msg.author.bot:
                history.append(f"{msg.author.name}: {msg.content}")
        context = "\n".join(reversed(history))
    except:
        pass

    sensitivity = settings.get("ai_sensitivity", 0.7)
    analysis = await check_toxicity(message.content, context, sensitivity)

    if analysis and analysis.get("toxic", False):
        severity = analysis.get("severity", "low")
        confidence = analysis.get("confidence", 0)
        reason = analysis.get("reason", "Toxic content")
        category = analysis.get("category", "none")

        # Auto slowmode for high toxicity
        if settings.get("slowmode_ai", 1) and severity in ["high", "critical"]:
            try:
                await message.channel.edit(slowmode_delay=10)
                await asyncio.sleep(60)
                await message.channel.edit(slowmode_delay=0)
            except:
                pass

        if confidence >= sensitivity:
            if severity in ["medium", "high", "critical"]:
                await punish_user(message, severity, reason, analysis)
            elif severity == "low":
                warn_count = add_warning(
                    message.author.id, message.guild.id, reason, severity
                )
                try:
                    dm = discord.Embed(
                        title="⚠️ Warning",
                        description=f"Please keep things respectful in **{message.guild.name}**",
                        color=discord.Color.yellow()
                    )
                    dm.add_field(name="Reason", value=reason)
                    await message.author.send(embed=dm)
                except:
                    pass

    await bot.process_commands(message)

# ============ SECTION 16 - RUN BOT ============
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set!")
    elif not GROQ_API_KEY:
        print("❌ ERROR: GROQ_API_KEY not set!")
    else:
        init_database()
        keep_alive()
        print("🚀 Starting SentinelMod...")
        bot.run(DISCORD_TOKEN)
