# bot.py
# ================================
# SentinelMod v9.0 - QUANTUM EDITION
# - Discord Components V2 throughout
# - Advanced natural language commands (@bot ban @user 7d spam)
# - Multi-model AI with smart routing (GPT-OSS 120B, Llama 3.3 70B, Qwen3.8)
# - Prompt injection shield (Llama Prompt Guard 2)
# - Scheduled punishments (temp bans/mutes with duration parsing)
# - Advanced appeal system with AI judge
# - Server analytics with real-time graphs
# - Voice transcription (Whisper)
# - Smart duplicate detection, raid shields, anti-nuke
# ================================

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
import random
import re
import io
import hashlib
import platform
import sys
import time as time_module
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from typing import Optional

# Local modules
from core_config import *
from ai_engine import AIEngine, PromptGuard
from moderation import ModerationEngine
from components_v2 import *
from command_parser import NaturalCommandParser
from database import Database
from utils import *

try:
    import image_moderation
    IMAGE_MOD = True
except ImportError:
    IMAGE_MOD = False
    
try:
    import welcome_system
    WELCOME = True
except ImportError:
    WELCOME = False

try:
    import test_server
    TEST_SERVER = True
except ImportError:
    TEST_SERVER = False

try:
    import smart_rules
    SMART_RULES = True
except ImportError:
    SMART_RULES = False

try:
    import psutil
    PSUTIL = True
except ImportError:
    PSUTIL = False

BOT_START_TIME = time_module.time()

# ============ BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ============ GLOBAL ENGINES ============
db = Database("sentinel.db")
ai = AIEngine(
    groq_key=os.getenv("GROQ_API_KEY"),
    openrouter_key=os.getenv("OPENROUTER_KEY", ""),
    hf_key=os.getenv("HF_API_KEY", "")
)
prompt_guard = PromptGuard(ai)
mod_engine = ModerationEngine(db, ai)
cmd_parser = NaturalCommandParser(ai, bot)

# ============ RUNTIME STATE ============
live_context: dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
user_message_patterns: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
recent_actions: dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
revoked_servers: set = set()
licensed_servers: set = set()
pending_licenses: dict[int, dict] = {}
server_rules_cache: dict[str, str] = {}
spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)
trivia_sessions = {}
voice_sessions: dict[int, dict] = {}
file_tracker = defaultdict(list)
scheduled_punishments: dict[str, dict] = {}  # NEW: temp bans/mutes

# Expose to modules
mod_engine.live_context = live_context
mod_engine.user_message_patterns = user_message_patterns
mod_engine.recent_actions = recent_actions
mod_engine.server_rules_cache = server_rules_cache
mod_engine.spam_tracker = spam_tracker
mod_engine.file_tracker = file_tracker
mod_engine.bot = bot


# ============ CONTEXT HELPERS ============
def update_live_context(guild_id, channel_id, author_name, author_id, content):
    key = f"{guild_id}:{channel_id}"
    live_context[key].append({
        "time": datetime.now().strftime("%H:%M"),
        "author": author_name, "author_id": author_id,
        "content": content, "ts": time.time(),
    })
    user_message_patterns[f"{guild_id}:{author_id}"].append({"content": content, "ts": time.time()})


def log_recent_action(guild_id, action_type, target_name, reason, details=""):
    recent_actions[guild_id].append({
        "time": datetime.now().isoformat(),
        "time_human": datetime.now().strftime("%I:%M %p"),
        "action": action_type, "target": target_name,
        "reason": reason, "details": details,
    })


# ============ PERMISSIONS ============
def is_owner(user_id):
    return int(user_id) == BOT_IDENTITY["creator_discord_id"]

def has_mod_permissions(member, guild_settings):
    if is_owner(member.id): return True
    if member.guild_permissions.administrator: return True
    mod_role = discord.utils.get(member.guild.roles, name=guild_settings.get("mod_role_name", MOD_ROLE_NAME))
    if mod_role and mod_role in member.roles: return True
    return member.guild_permissions.ban_members or member.guild_permissions.manage_messages


# ============ RULES SYSTEM ============
async def find_rules_channel(guild) -> Optional[discord.TextChannel]:
    cache_key = f"rules_ch_{guild.id}"
    if cache_key in server_rules_cache:
        ch = discord.utils.get(guild.text_channels, name=server_rules_cache[cache_key])
        if ch and ch.permissions_for(guild.me).read_messages:
            return ch

    readable = [c for c in guild.text_channels if c.permissions_for(guild.me).read_messages]
    if not readable: return None

    # Fast path: name matching
    for ch in readable:
        name_lower = ch.name.lower()
        if any(k in name_lower for k in ['rule', 'guideline', 'conduct', 'policy']):
            server_rules_cache[cache_key] = ch.name
            return ch

    # Discord's own rules channel
    if guild.rules_channel:
        server_rules_cache[cache_key] = guild.rules_channel.name
        return guild.rules_channel

    # AI fallback
    channel_list = [{"name": c.name, "topic": (c.topic or "")[:80]} for c in readable[:30]]
    result = await ai.ask_json(f"""Identify the rules channel. JSON: {{"name": "channel_name_or_null", "confidence": 0.0-1.0}}

Channels: {json.dumps(channel_list)[:2000]}""")

    if result and result.get("confidence", 0) >= 0.6 and result.get("name"):
        ch = discord.utils.get(guild.text_channels, name=result["name"])
        if ch:
            server_rules_cache[cache_key] = ch.name
            return ch
    return None


async def read_server_rules(guild) -> str:
    gid = str(guild.id)
    if gid in server_rules_cache:
        return server_rules_cache[gid]

    if SMART_RULES:
        try:
            data = await smart_rules.load_and_extract_rules(guild)
            rules = data.get("rules", [])
            if rules:
                lines = [f"Rule {r.get('number','?')}: {r.get('title','')}\n{r.get('description','')}" for r in rules]
                combined = "\n\n".join(lines)[:3000]
                server_rules_cache[gid] = combined
                return combined
        except Exception as e:
            print(f"smart_rules: {e}")

    rules_ch = await find_rules_channel(guild)
    if not rules_ch: return ""

    rules_text = []
    try:
        async for msg in rules_ch.history(limit=30, oldest_first=True):
            if msg.content and len(msg.content.strip()) > 10:
                rules_text.append(msg.content[:500])
            for embed in msg.embeds:
                if embed.description:
                    rules_text.append(embed.description[:500])
                for field in embed.fields:
                    rules_text.append(f"{field.name}: {field.value}"[:300])
    except Exception as e:
        print(f"Rules read: {e}")
        return ""

    combined = "\n\n".join(rules_text)[:3000]
    if combined: server_rules_cache[gid] = combined
    return combined


# ============ LICENSE SYSTEM ============
def load_licenses():
    for row in db.query("SELECT guild_id FROM revoked_licenses"):
        revoked_servers.add(int(row["guild_id"]))
    for row in db.query("SELECT guild_id FROM accepted_licenses"):
        licensed_servers.add(int(row["guild_id"]))
    print(f"✓ Loaded {len(licensed_servers)} licensed, {len(revoked_servers)} revoked")


async def send_license_agreement(guild):
    if int(guild.id) in licensed_servers: return True
    if int(guild.id) in revoked_servers:
        try: await guild.leave()
        except: pass
        return False

    target_channel = guild.system_channel if (guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages) else None
    if not target_channel:
        for name in ["general", "main", "lobby", "chat", "welcome"]:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch and ch.permissions_for(guild.me).send_messages:
                target_channel = ch
                break
    if not target_channel:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                target_channel = ch
                break
    if not target_channel:
        try: await guild.leave()
        except: pass
        return False

    container = build_license_container()
    view = LicenseAgreementView(guild, guild.owner, bot, db, revoked_servers, licensed_servers,
                                 pending_licenses, cleanup_and_leave, setup_server, read_server_rules, notify_owner)

    try:
        msg = await target_channel.send(
            content=f"{guild.owner.mention if guild.owner else '**Server Owner**'} — action required:",
            view=view
        )
        view.message = msg
        pending_licenses[guild.id] = {"message": msg, "view": view}
        await notify_owner("INFO", f"License sent to **{guild.name}**", guild=guild)
        return None
    except Exception as e:
        print(f"License err: {e}")
        try: await guild.leave()
        except: pass
        return False


async def cleanup_and_leave(guild):
    try:
        s = db.get_guild_settings(guild.id)
        channels = json.loads(s.get("created_channels", "[]"))
        roles = json.loads(s.get("created_roles", "[]"))
        categories = json.loads(s.get("created_categories", "[]"))

        for name in channels:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                try: await ch.delete(reason="SentinelMod cleanup")
                except: pass
                await asyncio.sleep(0.3)
        for name in roles:
            r = discord.utils.get(guild.roles, name=name)
            if r:
                try: await r.delete(reason="SentinelMod cleanup")
                except: pass
                await asyncio.sleep(0.3)
        for name in categories:
            cat = discord.utils.get(guild.categories, name=name)
            if cat:
                for ch in cat.channels:
                    try: await ch.delete()
                    except: pass
                try: await cat.delete()
                except: pass
                await asyncio.sleep(0.3)
    except Exception as e:
        print(f"Cleanup err: {e}")

    try: await guild.leave()
    except: pass


# ============ SETUP SERVER ============
async def setup_server(guild):
    results = []
    s = db.get_guild_settings(guild.id)

    roles_to_create = [
        (s.get("mod_role_name", MOD_ROLE_NAME), discord.Color.red(), True),
        ("Muted", discord.Color.dark_gray(), False),
        ("Quarantined", discord.Color.dark_gray(), False),
        ("Trusted", discord.Color.green(), False),
    ]
    for rn, color, hoist in roles_to_create:
        if not discord.utils.get(guild.roles, name=rn):
            try:
                await guild.create_role(name=rn, color=color, hoist=hoist)
                db.track_created_role(guild.id, rn)
                results.append(f"✅ Created role: {rn}")
            except Exception as e:
                results.append(f"❌ Role {rn}: {e}")
        else:
            results.append(f"⏭️ Role exists: {rn}")

    mr = discord.utils.get(guild.roles, name=s.get("mod_role_name", MOD_ROLE_NAME))

    scat = discord.utils.get(guild.categories, name="SENTINELAI")
    if not scat:
        try:
            ow = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            if mr: ow[mr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            scat = await guild.create_category(name="SENTINELAI", overwrites=ow)
            db.track_created_category(guild.id, "SENTINELAI")
            results.append("✅ Created category: SENTINELAI")
        except: pass

    for cn in [s.get("log_channel", MOD_LOG_CHANNEL), s.get("raid_channel", RAID_CHANNEL), AI_CHAT_CHANNEL]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, category=scat)
                db.track_created_channel(guild.id, cn)
                results.append(f"✅ Created: #{cn}")
            except Exception as e:
                results.append(f"❌ #{cn}: {e}")
        else:
            results.append(f"⏭️ Exists: #{cn}")

    existing = [ch.name for ch in guild.text_channels]
    for cn in ["welcome", "rules", "general"]:
        if not any(cn in ex or ex in cn for ex in existing):
            try:
                await guild.create_text_channel(name=cn)
                db.track_created_channel(guild.id, cn)
                results.append(f"✅ Created: #{cn}")
            except: pass

    return results


# ============ NOTIFICATIONS ============
async def notify_owner(alert_type, message_text, guild=None, urgent=False):
    try:
        owner = await bot.fetch_user(BOT_IDENTITY["creator_discord_id"])
        if not owner: return
        container = build_owner_alert_container(alert_type, message_text, guild, urgent)
        await owner.send(view=container)
    except: pass


async def alert_mods(guild, container_or_embed):
    s = db.get_guild_settings(guild.id)
    ch = discord.utils.get(guild.text_channels, name=s.get("log_channel", MOD_LOG_CHANNEL))
    mr = discord.utils.get(guild.roles, name=s.get("mod_role_name", MOD_ROLE_NAME))
    if ch:
        try:
            if isinstance(container_or_embed, discord.ui.View):
                await ch.send(content=mr.mention if mr else "", view=container_or_embed)
            else:
                await ch.send(content=mr.mention if mr else "", embed=container_or_embed)
        except: pass


# ============ SCHEDULED PUNISHMENTS (TEMP BANS/MUTES) ============
async def schedule_unpunish(guild_id, user_id, action, when_iso):
    pid = f"{guild_id}:{user_id}:{action}:{int(time.time())}"
    scheduled_punishments[pid] = {
        "guild_id": guild_id, "user_id": user_id,
        "action": action, "when": when_iso
    }
    db.add_scheduled_punishment(pid, guild_id, user_id, action, when_iso)


@tasks.loop(seconds=30)
async def process_scheduled_punishments():
    now = datetime.now()
    due = db.get_due_punishments(now.isoformat())
    for p in due:
        try:
            guild = bot.get_guild(int(p["guild_id"]))
            if not guild:
                db.remove_scheduled_punishment(p["id"])
                continue
            member = guild.get_member(int(p["user_id"]))
            if p["action"] == "unban":
                try:
                    user = await bot.fetch_user(int(p["user_id"]))
                    await guild.unban(user, reason="Temp ban expired")
                    log_recent_action(guild.id, "AUTO-UNBAN", str(user), "Temp ban expired")
                except: pass
            elif p["action"] == "unmute" and member:
                try:
                    await member.timeout(None, reason="Temp mute expired")
                    log_recent_action(guild.id, "AUTO-UNMUTE", member.display_name, "Temp mute expired")
                except: pass
            db.remove_scheduled_punishment(p["id"])
        except Exception as e:
            print(f"Scheduled punish err: {e}")


# ============ EVENTS ============
@bot.event
async def on_ready():
    print(f"\n{'='*60}")
    print(f"  SentinelMod v{BOT_IDENTITY['version']} - QUANTUM EDITION")
    print(f"  {bot.user} • {len(bot.guilds)} servers")
    print(f"{'='*60}\n")
    BOT_IDENTITY["bot_id"] = bot.user.id
    load_licenses()

    for i, g in enumerate(bot.guilds):
        if int(g.id) in revoked_servers:
            print(f"[REVOKED] {g.name}")
            try: await g.leave()
            except: pass
            continue
        if int(g.id) not in licensed_servers:
            print(f"[PENDING] {g.name}")
            await asyncio.sleep(i * 1.5)
            asyncio.create_task(send_license_agreement(g))
            continue
        db.init_guild_settings(g.id)
        print(f"[OK] {g.name}")

    if SMART_RULES:
        try: smart_rules.setup(bot)
        except Exception as e: print(f"smart_rules: {e}")
    if WELCOME:
        try: welcome_system.setup(bot)
        except Exception as e: print(f"welcome: {e}")
    if TEST_SERVER:
        try: test_server.setup(bot)
        except Exception as e: print(f"test_server: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"✓ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"✗ Sync: {e}")

    for task in [server_memory_extraction, memory_cleanup, check_giveaways,
                 check_reminders, cleanup_trackers, refresh_all_rules,
                 process_scheduled_punishments]:
        if not task.is_running():
            task.start()

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"v{BOT_IDENTITY['version']} • {len(bot.guilds)} servers"
        )
    )
    await notify_owner("INFO", f"🚀 v{BOT_IDENTITY['version']} ONLINE • {len(bot.guilds)} servers")


@bot.event
async def on_guild_join(guild):
    print(f"➕ Joined: {guild.name}")
    if int(guild.id) in revoked_servers:
        try: await guild.leave()
        except: pass
        return
    await notify_owner("JOIN", f"Added to **{guild.name}** ({guild.member_count} members)", guild=guild)
    await send_license_agreement(guild)


@bot.event
async def on_guild_remove(guild):
    print(f"➖ Removed: {guild.name}")
    pending_licenses.pop(guild.id, None)
    server_rules_cache.pop(str(guild.id), None)
    await notify_owner("INFO", f"Removed from **{guild.name}**", guild=guild)


@bot.event
async def on_member_join(member):
    g = member.guild
    if int(g.id) not in licensed_servers: return

    today = datetime.now().date().isoformat()
    db.execute(
        "INSERT INTO daily_stats (guild_id,date,joins) VALUES (?,?,1) ON CONFLICT DO UPDATE SET joins=joins+1",
        (str(g.id), today)
    )

    # Raid detection
    now = time.time()
    s = db.get_guild_settings(g.id)
    raid_tracker[g.id].append(now)
    raid_tracker[g.id] = [t for t in raid_tracker[g.id] if now - t < s.get("raid_window", 10)]

    if len(raid_tracker[g.id]) >= s.get("raid_limit", 10):
        if not raid_mode_active[g.id]:
            raid_mode_active[g.id] = True
            ch = discord.utils.get(g.text_channels, name=s.get("raid_channel", RAID_CHANNEL))
            mr = discord.utils.get(g.roles, name=s.get("mod_role_name", MOD_ROLE_NAME))
            if ch:
                container = build_raid_alert_container(g, len(raid_tracker[g.id]))
                await ch.send(content=f"{mr.mention if mr else '@here'} 🚨 **RAID DETECTED**", view=container)
            await notify_owner("RAID", f"🚨 Raid in **{g.name}**!", guild=g, urgent=True)

            async def reset():
                await asyncio.sleep(300)
                raid_mode_active[g.id] = False
            asyncio.create_task(reset())

        age_days = (datetime.now(timezone.utc) - member.created_at).days
        if age_days < s.get("min_account_age", 7):
            try: await member.kick(reason="Raid protection: account too new")
            except: pass


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    if reaction.message.id in trivia_sessions:
        s = trivia_sessions[reaction.message.id]
        if user.id in s["answered"]: return
        s["answered"].append(user.id)
        if str(reaction.emoji) == s["correct_emoji"]:
            await reaction.message.channel.send(f"🎉 {user.mention} got it! Answer: **{s['correct_answer']}**")
            del trivia_sessions[reaction.message.id]


@bot.event
async def on_message(message):
    if message.author.bot: return

    # DM = appeal handler
    if not message.guild:
        from appeal_system import handle_appeal_dm
        await handle_appeal_dm(message, bot, db, ai, alert_mods)
        return

    # License gates
    if int(message.guild.id) in revoked_servers:
        try: await message.guild.leave()
        except: pass
        return
    if int(message.guild.id) not in licensed_servers:
        return

    guild = message.guild
    author = message.author
    s = db.get_guild_settings(guild.id)

    update_live_context(guild.id, message.channel.id, author.display_name, author.id, message.content)
    db.update_message_stats(author.id, guild.id)
    db.archive_message(guild.id, message.channel.id, author.id, message.content)

    owner_talking = is_owner(author.id)
    is_mod = has_mod_permissions(author, s)

    # AFK system
    afk_entry = db.query_one("SELECT * FROM afk_users WHERE user_id=? AND guild_id=?",
                               (str(author.id), str(guild.id)))
    if afk_entry:
        db.execute("DELETE FROM afk_users WHERE user_id=? AND guild_id=?", (str(author.id), str(guild.id)))
        try:
            await message.channel.send(f"👋 Welcome back {author.mention}!", delete_after=8)
        except: pass

    for m in message.mentions:
        afk = db.query_one("SELECT * FROM afk_users WHERE user_id=? AND guild_id=?",
                             (str(m.id), str(guild.id)))
        if afk:
            try:
                await message.channel.send(
                    f"💤 **{m.display_name}** is AFK: *{afk['reason']}*",
                    delete_after=10
                )
            except: pass

    # Custom commands
    cc = db.query_one("SELECT response FROM custom_commands WHERE guild_id=? AND trigger_word=?",
                        (str(guild.id), message.content.lower().strip()))
    if cc:
        await message.channel.send(cc["response"])
        return

    is_ai_ch = message.channel.name == AI_CHAT_CHANNEL
    is_mentioned = bot.user in message.mentions
    server_rules = server_rules_cache.get(str(guild.id), "")

    # ============ CONVERSATIONAL / COMMAND MODE ============
    if is_ai_ch or is_mentioned:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content:
            if is_mentioned:
                greetings = ["Yeah Boss? 👑"] if owner_talking else ["Hey! 👋", "What's up?", "I'm here!"]
                await message.reply(random.choice(greetings))
            return

        # Prompt injection guard
        if not owner_talking:
            guard_result = await prompt_guard.check(content)
            if guard_result["is_injection"]:
                await message.reply("⚠️ Nice try, but I'm not falling for prompt injection.", delete_after=10)
                db.add_warning(author.id, guild.id, "Prompt injection attempt", "high", 0.95, content[:200])
                return

        # Rules questions
        if await answer_rules_question(message, content, server_rules):
            return

        # Natural command parsing (ADVANCED)
        parsed = None
        if cmd_parser.likely_command(content):
            try:
                parsed = await asyncio.wait_for(
                    cmd_parser.parse(content, guild, author, is_owner_user=owner_talking),
                    timeout=15.0
                )
            except: parsed = None

        if parsed and parsed.get("command") not in ["chat", None, ""] and parsed.get("confidence", 0) >= 0.65:
            # Permission check
            cmd_type = parsed.get("command")
            if not owner_talking and not is_mod:
                allowed = ["trivia", "eightball", "roast", "compliment", "dadjoke", "ship", "rate",
                           "fact", "story", "riddle", "remind", "set_afk", "rep", "memory_view",
                           "help", "create_poll", "summarize", "translate", "activity_stats",
                           "server_health", "read_rules", "refresh_rules", "balance", "profile"]
                if cmd_type not in allowed:
                    await message.reply("❌ You don't have permission for that command.")
                    return

            # Dangerous commands need confirmation
            dangerous = ["ban_user", "kick_user", "lockdown", "purge", "delete_channel",
                         "delete_role", "delete_category", "revoke_license", "leave_server",
                         "mass_ban", "mass_kick"]
            if parsed.get("needs_confirmation") or cmd_type in dangerous:
                view = ConfirmActionView(parsed, message, guild, author, execute_command)
                container = build_confirm_container(parsed)
                await message.reply(view=view)
            else:
                r = await execute_command(parsed, message, guild, author)
                if r:
                    if isinstance(r, discord.ui.View):
                        await message.reply(view=r)
                    else:
                        await message.reply(r[:2000])
            return

        # AI chat response
        from ai_chat import handle_ai_chat
        await handle_ai_chat(message, content, bot, db, ai, server_rules, owner_talking, is_mod,
                              voice_sessions, live_context, recent_actions)
        return

    # ============ MODERATION FOR ALL MESSAGES ============
    if is_mod or owner_talking:
        await bot.process_commands(message)
        return

    # Spam check
    key = f"{author.id}:{guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < s.get("spam_window", 5)]

    if len(spam_tracker[key]) >= s.get("spam_limit", 5):
        try: await message.channel.purge(limit=10, check=lambda m: m.author == author)
        except: pass
        try:
            await author.timeout(datetime.now(timezone.utc) + timedelta(minutes=s.get("mute_duration", 10)),
                                 reason="Spam")
        except: pass
        wc, _ = db.add_warning(author.id, guild.id, "Spam", "medium")
        log_recent_action(guild.id, "MUTED (SPAM)", author.display_name, f"Warning #{wc}")
        container = build_mod_action_container("SPAM", author, "Spam detected", wc)
        await alert_mods(guild, container)
        spam_tracker[key] = []
        return

    # AI moderation
    if s.get("ai_mod_enabled", 1):
        moderated = await mod_engine.check_message(message, s, server_rules, log_recent_action, alert_mods, notify_owner)
        if moderated:
            today = datetime.now().date().isoformat()
            db.execute(
                "INSERT INTO daily_stats (guild_id,date,mod_actions) VALUES (?,?,1) ON CONFLICT DO UPDATE SET mod_actions=mod_actions+1",
                (str(guild.id), today)
            )
            return

    await bot.process_commands(message)


async def answer_rules_question(message, content, server_rules):
    kw = ['rule', 'allowed', 'banned', 'can i', 'is it ok', 'permitted', 'forbidden', 'guideline',
          'what are the', 'against the rules']
    if not any(k in content.lower() for k in kw): return False

    if not server_rules:
        server_rules = await read_server_rules(message.guild)
    if not server_rules or len(server_rules.strip()) < 20:
        await message.reply("❌ I couldn't find any rules. Use `/reload_rules` or ask an admin to set one up.")
        return True

    rules_ch = await find_rules_channel(message.guild)
    ch_name = rules_ch.name if rules_ch else "rules"

    sent = await message.reply("*reading rules...*")

    prompt = f"""User asked about rules.

RULES:
{server_rules[:2500]}

QUESTION: "{content}"

Answer directly, quoting specific rules. If they ask for a list, LIST them numbered. Be concise, 2-5 sentences unless listing. NEVER swear."""

    response = await ai.chat(prompt,
        system="You're SentinelMod. Answer rules questions directly, cite specific rules. Never swear.",
        max_tokens=800, temperature=0.4)

    if not response:
        response = f"Check #{ch_name} for the full rules!"

    response = sanitize_bot_response(response.strip())
    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
    await sent.edit(content=chunks[0])
    for chunk in chunks[1:]:
        await message.channel.send(chunk)
    return True


# ============ COMMAND EXECUTION ============
async def execute_command(parsed, message, guild, author):
    from command_executor import execute as _execute
    return await _execute(parsed, message, guild, author, bot, db, ai,
                           log_recent_action, notify_owner, alert_mods,
                           cleanup_and_leave, setup_server, read_server_rules,
                           find_rules_channel, server_rules_cache, voice_sessions,
                           licensed_servers, revoked_servers, schedule_unpunish,
                           is_owner, trivia_sessions)


# ============ BACKGROUND TASKS ============
@tasks.loop(hours=1)
async def server_memory_extraction():
    for guild in bot.guilds:
        try:
            s = db.get_guild_settings(guild.id)
            if s.get("memory_mode") in ["server", "both"]:
                await extract_server_memory(guild.id)
                await asyncio.sleep(2)
        except: pass


async def extract_server_memory(gid):
    try:
        messages = db.query(
            "SELECT user_id, content FROM message_archive WHERE guild_id=? ORDER BY timestamp DESC LIMIT 100",
            (str(gid),)
        )
        if len(messages) < 15: return
        guild = bot.get_guild(int(gid))
        if not guild: return

        msg_lines = []
        for m in reversed(messages):
            member = guild.get_member(int(m["user_id"]))
            msg_lines.append(f"{member.display_name if member else 'User'}: {m['content']}")

        existing = db.get_server_memory(gid)
        extracted = await ai.ask_json(
            f"""Analyze. JSON: {{"server_culture":{{"vibe":null}},"new_inside_jokes":[],"popular_topics":[],"common_phrases":[],"server_mood":"chill|chaotic|wholesome|toxic|gaming"}}
Messages: {chr(10).join(msg_lines)[:3000]}"""
        )
        if not extracted: return

        memory = existing
        for k, v in extracted.get("server_culture", {}).items():
            if v: memory["server_culture"][k] = v
        for joke in extracted.get("new_inside_jokes", []):
            if joke: memory["inside_jokes"].append({"text": joke, "time": datetime.now().isoformat()})
        if extracted.get("popular_topics"):
            memory["popular_topics"] = extracted["popular_topics"][:15]
        if extracted.get("common_phrases"):
            for phrase in extracted["common_phrases"]:
                if phrase and phrase not in memory.get("common_phrases", []):
                    memory.setdefault("common_phrases", []).append(phrase)
        if extracted.get("server_mood"):
            memory["server_mood"] = extracted["server_mood"]
        memory["total_interactions"] += len(messages)
        db.save_server_memory(gid, memory)
    except Exception as e:
        print(f"Server mem: {e}")


@tasks.loop(hours=6)
async def refresh_all_rules():
    for guild in bot.guilds:
        if int(guild.id) in licensed_servers:
            try:
                server_rules_cache.pop(str(guild.id), None)
                await read_server_rules(guild)
                await asyncio.sleep(1)
            except: pass


@tasks.loop(hours=24)
async def memory_cleanup():
    for guild in bot.guilds:
        try:
            s = db.get_guild_settings(guild.id)
            cutoff = (datetime.now() - timedelta(days=s.get("memory_retention_days", 90))).isoformat()
            db.execute("DELETE FROM message_archive WHERE guild_id=? AND timestamp<?", (str(guild.id), cutoff))
            db.execute("DELETE FROM conversation_history WHERE guild_id=? AND timestamp<?", (str(guild.id), cutoff))
        except: pass


@tasks.loop(hours=1)
async def cleanup_trackers():
    now = time.time()
    dead = [k for k, times in spam_tracker.items() if not any(t > now - 300 for t in times)]
    for k in dead: del spam_tracker[k]
    dead = [k for k, times in file_tracker.items() if not any(t > now - 300 for t in times)]
    for k in dead: del file_tracker[k]


@tasks.loop(minutes=1)
async def check_giveaways():
    due = db.query("SELECT * FROM giveaways WHERE active=1 AND end_time<=?", (datetime.now().isoformat(),))
    for g in due:
        try:
            guild = bot.get_guild(int(g["guild_id"]))
            if not guild: continue
            ch = guild.get_channel(int(g["channel_id"]))
            if not ch: continue
            try:
                msg = await ch.fetch_message(int(g["message_id"]))
                r = discord.utils.get(msg.reactions, emoji="🎉")
                users = [u async for u in r.users() if not u.bot] if r else []
            except:
                users = []
            if users:
                winners = random.sample(users, min(g["winners"], len(users)))
                mention = ", ".join(x.mention for x in winners)
                container = build_giveaway_end_container(g["prize"], winners)
                await ch.send(content=mention, view=container)
            else:
                await ch.send(f"🎉 **{g['prize']}** - No valid entries!")
            db.execute("UPDATE giveaways SET active=0 WHERE id=?", (g["id"],))
        except Exception as e:
            print(f"Giveaway: {e}")


@tasks.loop(minutes=1)
async def check_reminders():
    due = db.query("SELECT * FROM reminders WHERE active=1 AND remind_time<=?", (datetime.now().isoformat(),))
    for rem in due:
        try:
            ch = bot.get_channel(int(rem["channel_id"]))
            if ch:
                container = build_reminder_container(rem["user_id"], rem["reminder"])
                await ch.send(content=f"<@{rem['user_id']}>", view=container)
        except: pass
        db.execute("UPDATE reminders SET active=0 WHERE id=?", (rem["id"],))


# ============ SLASH COMMANDS ============
from slash_commands import register_slash_commands
register_slash_commands(bot, db, ai, mod_engine, voice_sessions, licensed_servers,
                         revoked_servers, server_rules_cache, cleanup_and_leave,
                         find_rules_channel, read_server_rules, is_owner,
                         BOT_START_TIME, PERSONALITIES, notify_owner,
                         scheduled_punishments, schedule_unpunish)


# ============ ENTRY POINT ============
if __name__ == "__main__":
    if not os.getenv("DISCORD_TOKEN"):
        print("❌ DISCORD_TOKEN missing!")
        exit(1)
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY missing!")
        exit(1)

    db.init_schema()

    if DASHBOARD:
        try:
            dashboard.set_bot(bot)
            threading.Thread(target=dashboard.run_dashboard, daemon=True).start()
            print("✓ Dashboard started")
        except Exception as e:
            print(f"✗ Dashboard: {e}")

    print(f"🚀 Starting SentinelMod v{BOT_IDENTITY['version']}...")
    bot.run(os.getenv("DISCORD_TOKEN"))
