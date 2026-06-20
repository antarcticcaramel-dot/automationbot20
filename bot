# bot.py
# ================================
# SentinelAI - AI Moderator Bot
# Full System - Single File
# ================================

# ============ SECTION 1 - IMPORTS ============
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
import os
import asyncio
import sqlite3
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from collections import defaultdict

# ============ SECTION 2 - CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

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
SPAM_MUTE_DURATION = 10

# Anti-Raid Settings
RAID_JOIN_LIMIT = 10
RAID_TIME_WINDOW = 10
RAID_ACCOUNT_AGE_DAYS = 7

# Image Scanning
SCAN_IMAGES = True

# ============ SECTION 3 - KEEP ALIVE SERVER ============
class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SentinelAI is alive!")

    def log_message(self, format, *args):
        pass  # Suppress logs

def run_server():
    server = HTTPServer(("0.0.0.0", 8080), KeepAlive)
    server.serve_forever()

def keep_alive():
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    print("✅ Keep alive server running on port 8080")

# ============ SECTION 4 - DATABASE SETUP ============
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()

    # Warnings table
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

    # Mod actions table
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

    # Guild settings table
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
            ai_sensitivity REAL DEFAULT 0.7
        )
    """)

    # Spam tracking table
    c.execute("""
        CREATE TABLE IF NOT EXISTS spam_tracking (
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            window_start TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    # Raid tracking table
    c.execute("""
        CREATE TABLE IF NOT EXISTS raid_tracking (
            guild_id TEXT PRIMARY KEY,
            join_count INTEGER DEFAULT 0,
            window_start TEXT NOT NULL,
            raid_mode INTEGER DEFAULT 0
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
    else:
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
            "ai_sensitivity": 0.7
        }

def init_guild_settings(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO guild_settings (guild_id)
        VALUES (?)
    """, (str(guild_id),))
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

    c.execute("""
        SELECT COUNT(*) FROM warnings
        WHERE user_id = ? AND guild_id = ?
    """, (str(user_id), str(guild_id)))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_warnings(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM warnings
        WHERE user_id = ? AND guild_id = ?
        ORDER BY timestamp DESC
    """, (str(user_id), str(guild_id)))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_warnings(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        DELETE FROM warnings
        WHERE user_id = ? AND guild_id = ?
    """, (str(user_id), str(guild_id)))
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

# ============ SECTION 6 - BOT SETUP ============
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory trackers
spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)

# ============ SECTION 7 - SERVER AUTO SETUP ============
async def setup_server(guild):
    """Automatically set up the server for SentinelAI"""
    settings = get_guild_settings(guild.id)
    results = []

    # 1. Create Sentinel-Mod role
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    if not mod_role:
        try:
            mod_role = await guild.create_role(
                name=settings["mod_role_name"],
                color=discord.Color.red(),
                hoist=True,
                mentionable=True,
                reason="SentinelAI Setup"
            )
            results.append(f"✅ Created role: **{settings['mod_role_name']}**")
        except Exception as e:
            results.append(f"❌ Could not create mod role: {e}")
    else:
        results.append(f"✅ Role already exists: **{settings['mod_role_name']}**")

    # 2. Create SentinelAI category
    sentinel_category = discord.utils.get(guild.categories, name="🛡️ SENTINELAI")
    if not sentinel_category:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
            sentinel_category = await guild.create_category(
                name="🛡️ SENTINELAI",
                overwrites=overwrites,
                reason="SentinelAI Setup"
            )
            results.append("✅ Created category: **🛡️ SENTINELAI**")
        except Exception as e:
            results.append(f"❌ Could not create category: {e}")

    # 3. Create sentinel-logs channel
    log_channel = discord.utils.get(guild.text_channels, name=settings["log_channel"])
    if not log_channel:
        try:
            log_channel = await guild.create_text_channel(
                name=settings["log_channel"],
                category=sentinel_category,
                topic="🤖 SentinelAI moderation logs",
                reason="SentinelAI Setup"
            )
            results.append(f"✅ Created channel: **#{settings['log_channel']}**")
        except Exception as e:
            results.append(f"❌ Could not create log channel: {e}")
    else:
        results.append(f"✅ Channel already exists: **#{settings['log_channel']}**")

    # 4. Create sentinel-raid-alerts channel
    raid_channel = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
    if not raid_channel:
        try:
            raid_channel = await guild.create_text_channel(
                name=settings["raid_channel"],
                category=sentinel_category,
                topic="🚨 SentinelAI raid alerts",
                reason="SentinelAI Setup"
            )
            results.append(f"✅ Created channel: **#{settings['raid_channel']}**")
        except Exception as e:
            results.append(f"❌ Could not create raid channel: {e}")
    else:
        results.append(f"✅ Channel already exists: **#{settings['raid_channel']}**")

    # 5. Create sentinel-reports channel
    report_channel = discord.utils.get(guild.text_channels, name="sentinel-reports")
    if not report_channel:
        try:
            report_channel = await guild.create_text_channel(
                name="sentinel-reports",
                topic="📢 Report users here using /report",
                reason="SentinelAI Setup"
            )
            results.append("✅ Created channel: **#sentinel-reports**")
        except Exception as e:
            results.append(f"❌ Could not create reports channel: {e}")
    else:
        results.append("✅ Channel already exists: **#sentinel-reports**")

    # 6. Send welcome embed to logs
    if log_channel:
        try:
            embed = discord.Embed(
                title="🛡️ SentinelAI Activated",
                description="AI Moderation is now active on this server.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="AI Model", value=GROQ_MODEL, inline=True)
            embed.add_field(name="Mod Role", value=settings["mod_role_name"], inline=True)
            embed.add_field(name="Warn → Mute", value=f"{settings['warn_mute']} warnings", inline=True)
            embed.add_field(name="Warn → Ban", value=f"{settings['warn_ban']} warnings", inline=True)
            embed.add_field(
                name="Spam Limit",
                value=f"{settings['spam_limit']} msg/{settings['spam_window']}s",
                inline=True
            )
            embed.add_field(
                name="Raid Protection",
                value=f"{settings['raid_limit']} joins/{settings['raid_window']}s",
                inline=True
            )
            embed.set_footer(text="SentinelAI | All systems active")
            await log_channel.send(embed=embed)
        except:
            pass

    return results

# ============ SECTION 8 - AI TOXICITY CHECKER ============
async def check_toxicity(message_content, context="", sensitivity=0.7):
    prompt = f"""You are a Discord moderation AI. Analyze this message for toxicity.

Context of conversation:
{context}

Message to analyze: "{message_content}"

Respond ONLY in this exact JSON format, nothing else:
{{
    "toxic": true or false,
    "severity": "none" or "low" or "medium" or "high" or "critical",
    "category": "none" or "harassment" or "hate_speech" or "threat" or "spam" or "sexual" or "bullying" or "manipulation" or "slur" or "doxxing",
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation under 100 words"
}}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a moderation AI. Always respond only in valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 250
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data["choices"][0]["message"]["content"].strip()
                    if "```" in result:
                        result = result.split("```")[1]
                        if result.startswith("json"):
                            result = result[4:]
                    return json.loads(result.strip())
                else:
                    print(f"Groq API error: {resp.status}")
                    return None
    except Exception as e:
        print(f"Toxicity check error: {e}")
        return None

# ============ SECTION 9 - IMAGE SCANNER ============
async def scan_image(image_url):
    prompt = f"""Analyze this image URL for potentially harmful content.
URL: {image_url}

Check if the URL contains suspicious patterns suggesting: nsfw, adult, explicit, gore, violence.

Respond ONLY in this JSON format:
{{
    "suspicious": true or false,
    "reason": "brief reason or none",
    "confidence": 0.0 to 1.0
}}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a content moderation AI. Respond only in JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 150
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
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
        print(f"Image scan error: {e}")
    return None

# ============ SECTION 10 - ANTI-SPAM SYSTEM ============
async def check_spam(message, settings):
    user_id = message.author.id
    guild_id = message.guild.id
    key = f"{user_id}:{guild_id}"
    now = time.time()

    spam_tracker[key].append(now)

    window = settings.get("spam_window", SPAM_TIME_WINDOW)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < window]

    limit = settings.get("spam_limit", SPAM_MESSAGE_LIMIT)
    if len(spam_tracker[key]) >= limit:
        spam_tracker[key] = []
        return True

    return False

async def handle_spam(message, settings):
    user = message.author
    guild = message.guild

    # Delete spam messages
    try:
        def is_spam_message(m):
            return m.author == user
        deleted = await message.channel.purge(limit=10, check=is_spam_message)
    except:
        deleted = []

    # Mute user
    try:
        mute_duration = settings.get("mute_duration", MUTE_DURATION_MINUTES)
        until = datetime.now() + timedelta(minutes=mute_duration)
        await user.timeout(until, reason="SentinelAI: Spam detected")
    except discord.Forbidden:
        pass

    # Add warning
    warn_count = add_warning(user.id, guild.id, "Spam detected", "medium")
    log_mod_action(user.id, guild.id, "SPAM_MUTE", "Spam detected", bot.user.id)

    # DM user
    try:
        embed = discord.Embed(
            title="⚠️ Spam Detected",
            description=f"You were muted for spamming in **{guild.name}**",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Duration",
            value=f"{settings.get('mute_duration', MUTE_DURATION_MINUTES)} minutes"
        )
        await user.send(embed=embed)
    except:
        pass

    # Alert mods
    settings_data = get_guild_settings(guild.id)
    log_channel = discord.utils.get(guild.text_channels, name=settings_data["log_channel"])
    mod_role = discord.utils.get(guild.roles, name=settings_data["mod_role_name"])

    if log_channel:
        embed = discord.Embed(
            title="🔇 Spam Detected & Handled",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Messages Deleted", value=str(len(deleted)), inline=True)
        embed.add_field(
            name="Action",
            value=f"Muted {settings.get('mute_duration', MUTE_DURATION_MINUTES)} mins",
            inline=True
        )
        embed.add_field(name="Total Warnings", value=str(warn_count), inline=True)
        ping = mod_role.mention if mod_role else ""
        await log_channel.send(content=ping, embed=embed)

# ============ SECTION 11 - ANTI-RAID SYSTEM ============
async def check_raid(member):
    guild = member.guild
    settings = get_guild_settings(guild.id)
    guild_id = guild.id
    now = time.time()

    raid_tracker[guild_id].append({
        "time": now,
        "member": member
    })

    window = settings.get("raid_window", RAID_TIME_WINDOW)
    raid_tracker[guild_id] = [
        j for j in raid_tracker[guild_id]
        if now - j["time"] < window
    ]

    limit = settings.get("raid_limit", RAID_JOIN_LIMIT)
    if len(raid_tracker[guild_id]) >= limit:
        return True

    return False

async def handle_raid(guild, new_member):
    settings = get_guild_settings(guild.id)

    if not raid_mode_active[guild.id]:
        raid_mode_active[guild.id] = True

        raid_channel = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])

        if raid_channel:
            embed = discord.Embed(
                title="🚨 RAID DETECTED",
                description="A potential raid has been detected. Auto-defense activated.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="Trigger",
                value=f"{settings['raid_limit']} joins in {settings['raid_window']}s",
                inline=True
            )
            embed.add_field(
                name="Actions",
                value="• Kicking suspicious accounts\n• Monitoring joins\n• Raid mode ON",
                inline=False
            )
            embed.set_footer(text="Use /raidmode off to disable")
            ping = mod_role.mention if mod_role else ""
            await raid_channel.send(content=f"🚨 {ping} RAID ALERT!", embed=embed)

        # Auto disable raid mode after 5 minutes
        await asyncio.sleep(300)
        raid_mode_active[guild.id] = False

    # Kick suspicious new accounts during raid
    account_age = (datetime.now() - new_member.created_at.replace(tzinfo=None)).days
    min_age = settings.get("min_account_age", RAID_ACCOUNT_AGE_DAYS)

    if account_age < min_age:
        try:
            await new_member.kick(
                reason=f"SentinelAI: Raid protection - Account too new ({account_age} days)"
            )
            raid_channel = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
            if raid_channel:
                await raid_channel.send(
                    f"🔨 Kicked **{new_member}** - Account age: {account_age} days"
                )
        except discord.Forbidden:
            pass

# ============ SECTION 12 - MOD ALERT SYSTEM ============
async def alert_mods(guild, embed, channel_name=None):
    settings = get_guild_settings(guild.id)
    log_name = channel_name or settings["log_channel"]
    log_channel = discord.utils.get(guild.text_channels, name=log_name)
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])

    if log_channel:
        ping = mod_role.mention if mod_role else ""
        await log_channel.send(content=f"🚨 {ping}", embed=embed)

async def send_warning_dm(user, reason, warn_count, settings):
    try:
        embed = discord.Embed(
            title="⚠️ Warning Received",
            description="Your message was flagged by SentinelAI.",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(
            name="Warnings",
            value=f"{warn_count}/{settings.get('warn_ban', WARN_THRESHOLD_BAN)}",
            inline=True
        )

        if warn_count >= settings.get("warn_mute", WARN_THRESHOLD_MUTE):
            embed.add_field(
                name="🔇 Muted",
                value=f"You have been muted for {settings.get('mute_duration', MUTE_DURATION_MINUTES)} minutes.",
                inline=False
            )
        if warn_count >= settings.get("warn_ban", WARN_THRESHOLD_BAN):
            embed.add_field(
                name="🔨 Banned",
                value="You have been banned for repeated violations.",
                inline=False
            )

        embed.set_footer(text="SentinelAI Moderation")
        await user.send(embed=embed)
    except discord.Forbidden:
        pass

# ============ SECTION 13 - PUNISHMENT SYSTEM ============
async def punish_user(message, severity, reason, analysis):
    user = message.author
    guild = message.guild
    settings = get_guild_settings(guild.id)

    warn_count = add_warning(user.id, guild.id, reason, severity)
    log_mod_action(user.id, guild.id, "AI_WARN", reason, bot.user.id)

    # Delete message
    try:
        await message.delete()
    except discord.Forbidden:
        pass

    # Temp warning in channel
    warn_embed = discord.Embed(
        title="🛡️ Message Removed by SentinelAI",
        description=f"{user.mention}, your message was removed.",
        color=discord.Color.orange()
    )
    warn_embed.add_field(name="Reason", value=reason, inline=False)
    warn_embed.add_field(
        name="Warnings",
        value=f"{warn_count}/{settings.get('warn_ban', WARN_THRESHOLD_BAN)}",
        inline=True
    )
    try:
        await message.channel.send(embed=warn_embed, delete_after=8)
    except:
        pass

    # DM user
    await send_warning_dm(user, reason, warn_count, settings)

    # Severity colors
    severity_colors = {
        "low": discord.Color.yellow(),
        "medium": discord.Color.orange(),
        "high": discord.Color.red(),
        "critical": discord.Color.dark_red()
    }

    # Mod alert embed
    mod_embed = discord.Embed(
        title="🚨 AI Moderation Alert",
        color=severity_colors.get(severity, discord.Color.red()),
        timestamp=datetime.now()
    )
    mod_embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
    mod_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    mod_embed.add_field(name="Severity", value=f"**{severity.upper()}**", inline=True)
    mod_embed.add_field(name="Category", value=analysis.get("category", "unknown"), inline=True)
    mod_embed.add_field(name="Confidence", value=f"{analysis.get('confidence', 0)*100:.0f}%", inline=True)
    mod_embed.add_field(
        name="Warnings",
        value=f"{warn_count}/{settings.get('warn_ban', WARN_THRESHOLD_BAN)}",
        inline=True
    )
    mod_embed.add_field(name="Message", value=f"||{message.content[:500]}||", inline=False)
    mod_embed.add_field(name="AI Reason", value=reason, inline=False)

    action_taken = "⚠️ Warning issued"

    # MUTE
    if (warn_count >= settings.get("warn_mute", WARN_THRESHOLD_MUTE) and
            warn_count < settings.get("warn_ban", WARN_THRESHOLD_BAN)):
        try:
            until = datetime.now() + timedelta(
                minutes=settings.get("mute_duration", MUTE_DURATION_MINUTES)
            )
            await user.timeout(until, reason=f"SentinelAI: {reason}")
            action_taken = f"🔇 Muted for {settings.get('mute_duration', MUTE_DURATION_MINUTES)} minutes"
            log_mod_action(user.id, guild.id, "AI_MUTE", reason, bot.user.id)
        except discord.Forbidden:
            action_taken = "❌ Could not mute (missing permissions)"

    # BAN
    if warn_count >= settings.get("warn_ban", WARN_THRESHOLD_BAN):
        try:
            await guild.ban(user, reason=f"SentinelAI: {reason} ({warn_count} warnings)")
            action_taken = "🔨 BANNED"
            log_mod_action(user.id, guild.id, "AI_BAN", reason, bot.user.id)
        except discord.Forbidden:
            action_taken = "❌ Could not ban (missing permissions)"

    mod_embed.add_field(name="Action", value=action_taken, inline=False)
    await alert_mods(guild, mod_embed)

# ============ SECTION 14 - BOT EVENTS ============
@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 SentinelAI is ONLINE")
    print(f"📛 Bot: {bot.user}")
    print(f"🏠 Servers: {len(bot.guilds)}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for guild in bot.guilds:
        init_guild_settings(guild.id)

    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for rule breakers 🛡️"
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

    # Check for raid
    is_raid = await check_raid(member)
    if is_raid:
        await handle_raid(guild, member)
        return

    # Flag suspicious accounts
    min_age = settings.get("min_account_age", RAID_ACCOUNT_AGE_DAYS)
    if account_age < min_age:
        raid_channel = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
        if raid_channel:
            embed = discord.Embed(
                title="⚠️ Suspicious New Account",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
            embed.add_field(name="Created", value=str(member.created_at)[:16], inline=True)
            await raid_channel.send(embed=embed)

@bot.event
async def on_message(message):
    # Ignore bots and DMs
    if message.author.bot:
        return
    if not message.guild:
        return

    settings = get_guild_settings(message.guild.id)

    # Skip mod roles
    mod_role = discord.utils.get(message.guild.roles, name=settings["mod_role_name"])
    if mod_role and mod_role in message.author.roles:
        await bot.process_commands(message)
        return

    # ---- ANTI-SPAM CHECK ----
    is_spam = await check_spam(message, settings)
    if is_spam:
        await handle_spam(message, settings)
        return

    # ---- IMAGE SCAN ----
    if settings.get("scan_images", 1) and message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext)
                   for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                scan = await scan_image(attachment.url)
                if scan and scan.get("suspicious") and scan.get("confidence", 0) >= 0.8:
                    try:
                        await message.delete()
                    except:
                        pass

                    warn_count = add_warning(
                        message.author.id,
                        message.guild.id,
                        f"Suspicious image: {scan.get('reason', 'Unknown')}",
                        "high"
                    )

                    mod_embed = discord.Embed(
                        title="🖼️ Suspicious Image Removed",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    mod_embed.add_field(
                        name="User",
                        value=f"{message.author.mention}",
                        inline=True
                    )
                    mod_embed.add_field(
                        name="Channel",
                        value=message.channel.mention,
                        inline=True
                    )
                    mod_embed.add_field(
                        name="Reason",
                        value=scan.get("reason", "Unknown"),
                        inline=False
                    )
                    mod_embed.add_field(
                        name="Confidence",
                        value=f"{scan.get('confidence', 0)*100:.0f}%",
                        inline=True
                    )
                    mod_embed.add_field(name="Warnings", value=str(warn_count), inline=True)
                    await alert_mods(message.guild, mod_embed)
                    return

    # ---- SKIP SHORT MESSAGES ----
    if len(message.content) < 3:
        await bot.process_commands(message)
        return

    # ---- AI TOXICITY CHECK ----
    context = ""
    try:
        history = []
        async for msg in message.channel.history(limit=5, before=message):
            history.append(f"{msg.author.name}: {msg.content}")
        context = "\n".join(reversed(history))
    except:
        pass

    sensitivity = settings.get("ai_sensitivity", 0.7)
    analysis = await check_toxicity(message.content, context, sensitivity)

    if analysis and analysis.get("toxic", False):
        severity = analysis.get("severity", "low")
        confidence = analysis.get("confidence", 0)
        reason = analysis.get("reason", "Toxic content detected")

        if confidence >= sensitivity:
            if severity in ["medium", "high", "critical"]:
                await punish_user(message, severity, reason, analysis)
            elif severity == "low":
                warn_count = add_warning(
                    message.author.id,
                    message.guild.id,
                    reason,
                    severity
                )
                await send_warning_dm(message.author, reason, warn_count, settings)

    await bot.process_commands(message)

# ============ SECTION 15 - SLASH COMMANDS ============

# /setup
@bot.tree.command(name="setup", description="Set up SentinelAI on this server")
async def setup_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You need Administrator permission.", ephemeral=True
        )
        return

    await interaction.response.defer()
    results = await setup_server(interaction.guild)

    embed = discord.Embed(
        title="🛡️ SentinelAI Setup Complete",
        description="\n".join(results),
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="SentinelAI is now active!")
    await interaction.followup.send(embed=embed)

# /warnings
@bot.tree.command(name="warnings", description="Check warnings for a user")
@app_commands.describe(user="The user to check")
async def check_warnings_cmd(interaction: discord.Interaction, user: discord.Member):
    warns = get_warnings(user.id, interaction.guild.id)

    if not warns:
        await interaction.response.send_message(
            f"✅ {user.mention} has no warnings.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"⚠️ Warnings for {user.display_name}",
        color=discord.Color.yellow()
    )

    for i, warn in enumerate(warns[:10], 1):
        embed.add_field(
            name=f"#{i} - {warn['severity'].upper()}",
            value=f"{warn['reason']}\n*{warn['timestamp'][:16]}*",
            inline=False
        )

    embed.set_footer(text=f"Total: {len(warns)} warnings")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# /clearwarnings
@bot.tree.command(name="clearwarnings", description="Clear all warnings for a user")
@app_commands.describe(user="The user to clear warnings for")
async def clear_warnings_cmd(interaction: discord.Interaction, user: discord.Member):
    settings = get_guild_settings(interaction.guild.id)
    mod_role = discord.utils.get(interaction.guild.roles, name=settings["mod_role_name"])

    if not mod_role or mod_role not in interaction.user.roles:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need the Moderator role.", ephemeral=True
            )
            return

    clear_warnings(user.id, interaction.guild.id)
    log_mod_action(user.id, interaction.guild.id, "CLEAR_WARNS", "Manual clear", interaction.user.id)
    await interaction.response.send_message(
        f"✅ Cleared all warnings for {user.mention}.", ephemeral=True
    )

# /warn
@bot.tree.command(name="warn", description="Manually warn a user")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def warn_cmd(interaction: discord.Interaction, user: discord.Member, reason: str):
    settings = get_guild_settings(interaction.guild.id)
    mod_role = discord.utils.get(interaction.guild.roles, name=settings["mod_role_name"])

    if not mod_role or mod_role not in interaction.user.roles:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need the Moderator role.", ephemeral=True
            )
            return

    warn_count = add_warning(user.id, interaction.guild.id, reason, "manual")
    log_mod_action(user.id, interaction.guild.id, "MANUAL_WARN", reason, interaction.user.id)
    await send_warning_dm(user, reason, warn_count, settings)

    await interaction.response.send_message(
        f"⚠️ Warned {user.mention} - **{reason}** "
        f"(Warning {warn_count}/{settings.get('warn_ban', WARN_THRESHOLD_BAN)})",
        ephemeral=True
    )

# /mute
@bot.tree.command(name="mute", description="Manually mute a user")
@app_commands.describe(user="User to mute", minutes="Duration in minutes", reason="Reason")
async def mute_cmd(
    interaction: discord.Interaction,
    user: discord.Member,
    minutes: int,
    reason: str
):
    settings = get_guild_settings(interaction.guild.id)
    mod_role = discord.utils.get(interaction.guild.roles, name=settings["mod_role_name"])

    if not mod_role or mod_role not in interaction.user.roles:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need the Moderator role.", ephemeral=True
            )
            return

    try:
        until = datetime.now() + timedelta(minutes=minutes)
        await user.timeout(until, reason=f"Manual: {reason}")
        log_mod_action(user.id, interaction.guild.id, "MANUAL_MUTE", reason, interaction.user.id)
        await interaction.response.send_message(
            f"🔇 Muted {user.mention} for {minutes} minutes. Reason: {reason}",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message("❌ Cannot mute this user.", ephemeral=True)

# /ban
@bot.tree.command(name="ban", description="Manually ban a user")
@app_commands.describe(user="User to ban", reason="Reason")
async def ban_cmd(interaction: discord.Interaction, user: discord.Member, reason: str):
    settings = get_guild_settings(interaction.guild.id)
    mod_role = discord.utils.get(interaction.guild.roles, name=settings["mod_role_name"])

    if not mod_role or mod_role not in interaction.user.roles:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need the Moderator role.", ephemeral=True
            )
            return

    try:
        await interaction.guild.ban(user, reason=f"Manual: {reason}")
        log_mod_action(user.id, interaction.guild.id, "MANUAL_BAN", reason, interaction.user.id)
        await interaction.response.send_message(
            f"🔨 Banned {user.mention}. Reason: {reason}",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message("❌ Cannot ban this user.", ephemeral=True)

# /analyze
@bot.tree.command(name="analyze", description="Analyze a message for toxicity")
@app_commands.describe(message="The message to analyze")
async def analyze_cmd(interaction: discord.Interaction, message: str):
    await interaction.response.defer(ephemeral=True)
    analysis = await check_toxicity(message)

    if not analysis:
        await interaction.followup.send("❌ Analysis failed.", ephemeral=True)
        return

    embed = discord.Embed(title="🔍 Message Analysis", color=discord.Color.blue())
    embed.add_field(name="Message", value=f"||{message[:500]}||", inline=False)
    embed.add_field(name="Toxic", value="Yes ⚠️" if analysis.get("toxic") else "No ✅", inline=True)
    embed.add_field(name="Severity", value=analysis.get("severity", "N/A").upper(), inline=True)
    embed.add_field(name="Category", value=analysis.get("category", "N/A"), inline=True)
    embed.add_field(name="Confidence", value=f"{analysis.get('confidence', 0)*100:.0f}%", inline=True)
    embed.add_field(name="Reason", value=analysis.get("reason", "N/A"), inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# /raidmode
@bot.tree.command(name="raidmode", description="Toggle raid mode on/off")
@app_commands.describe(status="on or off")
@app_commands.choices(status=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off")
])
async def raidmode_cmd(interaction: discord.Interaction, status: str):
    settings = get_guild_settings(interaction.guild.id)
    mod_role = discord.utils.get(interaction.guild.roles, name=settings["mod_role_name"])

    if not mod_role or mod_role not in interaction.user.roles:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need the Moderator role.", ephemeral=True
            )
            return

    raid_mode_active[interaction.guild.id] = (status == "on")

    embed = discord.Embed(
        title="🚨 Raid Mode",
        description=f"Raid mode is now **{status.upper()}**",
        color=discord.Color.red() if status == "on" else discord.Color.green()
    )
    if status == "on":
        embed.add_field(
            name="Active Protections",
            value="• Suspicious accounts will be kicked\n• All joins monitored\n• Mods alerted",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# /report
@bot.tree.command(name="report", description="Report a user to moderators")
@app_commands.describe(user="User to report", reason="Reason for report")
async def report_cmd(interaction: discord.Interaction, user: discord.Member, reason: str):
    settings = get_guild_settings(interaction.guild.id)
    log_channel = discord.utils.get(interaction.guild.text_channels, name=settings["log_channel"])
    mod_role = discord.utils.get(interaction.guild.roles, name=settings["mod_role_name"])

    if log_channel:
        embed = discord.Embed(
            title="📢 User Report",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Reported User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="Reported By", value=f"{interaction.user.mention}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        ping = mod_role.mention if mod_role else ""
        await log_channel.send(content=f"📢 {ping} New report!", embed=embed)

    await interaction.response.send_message(
        "✅ Your report has been sent to moderators. Thank you.",
        ephemeral=True
    )

# /stats
@bot.tree.command(name="stats", description="View moderation statistics")
async def stats_cmd(interaction: discord.Interaction):
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT COUNT(*) FROM warnings WHERE guild_id = ?",
        (str(interaction.guild.id),)
    )
    total_warns = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(DISTINCT user_id) FROM warnings WHERE guild_id = ?",
        (str(interaction.guild.id),)
    )
    warned_users = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM mod_actions WHERE guild_id = ?",
        (str(interaction.guild.id),)
    )
    total_actions = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM mod_actions WHERE guild_id = ? AND action LIKE 'AI_%'",
        (str(interaction.guild.id),)
    )
    ai_actions = c.fetchone()[0]
    conn.close()

    embed = discord.Embed(
        title="📊 SentinelAI Statistics",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Total Warnings", value=str(total_warns), inline=True)
    embed.add_field(name="Users Warned", value=str(warned_users), inline=True)
    embed.add_field(name="Total Actions", value=str(total_actions), inline=True)
    embed.add_field(name="AI Actions", value=str(ai_actions), inline=True)
    embed.add_field(
        name="Raid Mode",
        value="🔴 ON" if raid_mode_active[interaction.guild.id] else "🟢 OFF",
        inline=True
    )
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)

    await interaction.response.send_message(embed=embed)

# /settings
@bot.tree.command(name="settings", description="View SentinelAI settings")
async def settings_cmd(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild.id)

    embed = discord.Embed(
        title="⚙️ SentinelAI Settings",
        color=discord.Color.blue()
    )
    embed.add_field(name="Mod Role", value=settings["mod_role_name"], inline=True)
    embed.add_field(name="Log Channel", value=f"#{settings['log_channel']}", inline=True)
    embed.add_field(name="Raid Channel", value=f"#{settings['raid_channel']}", inline=True)
    embed.add_field(name="Mute After", value=f"{settings['warn_mute']} warnings", inline=True)
    embed.add_field(name="Ban After", value=f"{settings['warn_ban']} warnings", inline=True)
    embed.add_field(name="Mute Duration", value=f"{settings['mute_duration']} min", inline=True)
    embed.add_field(
        name="Spam Limit",
        value=f"{settings['spam_limit']} msg/{settings['spam_window']}s",
        inline=True
    )
    embed.add_field(
        name="Raid Limit",
        value=f"{settings['raid_limit']} joins/{settings['raid_window']}s",
        inline=True
    )
    embed.add_field(
        name="Min Account Age",
        value=f"{settings['min_account_age']} days",
        inline=True
    )
    embed.add_field(
        name="AI Sensitivity",
        value=f"{settings['ai_sensitivity']*100:.0f}%",
        inline=True
    )
    embed.add_field(
        name="Image Scanning",
        value="✅ ON" if settings["scan_images"] else "❌ OFF",
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============ SECTION 16 - RUN BOT ============
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not set!")
    elif not GROQ_API_KEY:
        print("❌ ERROR: GROQ_API_KEY not set!")
    else:
        init_database()
        keep_alive()
        print("🚀 Starting SentinelAI...")
        bot.run(DISCORD_TOKEN)
