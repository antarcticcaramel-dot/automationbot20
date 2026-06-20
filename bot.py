# bot.py
# ================================
# SentinelMod - Full Bot + Dashboard
# ================================

# ============ IMPORTS ============
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
import secrets
import unicodedata
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, request, redirect, session, render_template_string, jsonify, url_for
import requests

# ============ CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
BOT_NAME = "SentinelMod"
AI_CHAT_CHANNEL = "sentinel-bot"

# Dashboard config
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", secrets.token_hex(32))

# Mod settings
MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"

PERSONALITIES = {
    "friendly": "You are extremely friendly and warm. Use emojis.",
    "sarcastic": "You are deeply sarcastic and witty.",
    "serious": "You are professional and serious.",
    "chaotic": "You are completely chaotic and random.",
    "pirate": "You are a pirate. Arr matey!",
    "medieval": "You are a medieval knight. Speak in old English.",
    "robot": "You are a robot. Beep boop.",
    "therapist": "You are a caring therapist.",
    "villain": "You are a dramatic villain.",
    "hype": "You are the ultimate hype man. ALL CAPS ENERGY.",
    "philosopher": "You are a deep philosopher.",
    "caveman": "You speak like a caveman. UGH.",
    "shakespeare": "You speak in Shakespearean English.",
    "surfer": "You are a chill surfer dude.",
    "anime": "You speak like an anime character.",
    "british": "You are extremely British.",
    "australian": "You are extremely Australian.",
    "gen_z": "You speak in Gen Z slang.",
    "boomer": "You are a stereotypical boomer.",
    "yoda": "Speak like Yoda you must.",
    "deadpool": "You are Deadpool. Break the fourth wall.",
    "sherlock": "You are Sherlock Holmes.",
    "gandalf": "You are Gandalf. Wise and mysterious.",
    "tony_stark": "You are Tony Stark. Genius billionaire.",
    "groot": "I am Groot. (Translate in parentheses)",
    "darth_vader": "You are Darth Vader.",
    "michael_scott": "You are Michael Scott. Inappropriate but lovable.",
    "motivational": "You are extremely motivational!",
    "pessimist": "You are extremely pessimistic.",
    "optimist": "You are blindly optimistic.",
    "ninja": "You are a ninja.",
    "vampire": "You are a sophisticated vampire.",
    "default": "You are SentinelMod, a helpful Discord bot."
}

# ============ DATABASE ============
def init_database():
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()
    tables = [
        """CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, reason TEXT, severity TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS mod_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, action TEXT, reason TEXT, mod_id TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS guild_settings (guild_id TEXT PRIMARY KEY, mod_role_name TEXT DEFAULT 'Sentinel-Mod', log_channel TEXT DEFAULT 'sentinel-logs', raid_channel TEXT DEFAULT 'sentinel-raid-alerts', warn_mute INTEGER DEFAULT 3, warn_ban INTEGER DEFAULT 5, mute_duration INTEGER DEFAULT 10, spam_limit INTEGER DEFAULT 5, spam_window INTEGER DEFAULT 5, raid_limit INTEGER DEFAULT 10, raid_window INTEGER DEFAULT 10, min_account_age INTEGER DEFAULT 7, scan_images INTEGER DEFAULT 1, ai_sensitivity REAL DEFAULT 0.7, welcome_channel TEXT DEFAULT 'welcome', welcome_enabled INTEGER DEFAULT 1, anti_nuke_enabled INTEGER DEFAULT 1, invite_block INTEGER DEFAULT 0, link_scan INTEGER DEFAULT 1, slowmode_ai INTEGER DEFAULT 1, pre_conflict INTEGER DEFAULT 1, caps_filter INTEGER DEFAULT 1, mention_spam INTEGER DEFAULT 1, emoji_spam INTEGER DEFAULT 1, zalgo_filter INTEGER DEFAULT 1, phone_filter INTEGER DEFAULT 1, email_filter INTEGER DEFAULT 1, scam_filter INTEGER DEFAULT 1, nsfw_text_filter INTEGER DEFAULT 1, everyone_block INTEGER DEFAULT 0, anti_advertisement INTEGER DEFAULT 1, unicode_filter INTEGER DEFAULT 1, fake_nitro_filter INTEGER DEFAULT 1, token_filter INTEGER DEFAULT 1, file_spam_filter INTEGER DEFAULT 1, personality TEXT DEFAULT 'default')""",
        """CREATE TABLE IF NOT EXISTS user_memory (user_id TEXT, guild_id TEXT, memory TEXT, updated TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS conversation_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, role TEXT, content TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS user_personalities (user_id TEXT, guild_id TEXT, personality TEXT DEFAULT 'default', PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, user_id TEXT, channel_id TEXT, status TEXT DEFAULT 'open', reason TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS afk_users (user_id TEXT, guild_id TEXT, reason TEXT, timestamp TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS giveaways (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, channel_id TEXT, message_id TEXT, prize TEXT, winners INTEGER DEFAULT 1, end_time TEXT, active INTEGER DEFAULT 1, host_id TEXT)""",
        """CREATE TABLE IF NOT EXISTS auto_roles (guild_id TEXT, role_id TEXT, PRIMARY KEY (guild_id, role_id))""",
        """CREATE TABLE IF NOT EXISTS word_filters (guild_id TEXT, word TEXT, PRIMARY KEY (guild_id, word))""",
        """CREATE TABLE IF NOT EXISTS user_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, user_id TEXT, note TEXT, mod_id TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS message_stats (user_id TEXT, guild_id TEXT, message_count INTEGER DEFAULT 0, last_message TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, channel_id TEXT, reminder TEXT, remind_time TEXT, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS custom_commands (guild_id TEXT, trigger_word TEXT, response TEXT, PRIMARY KEY (guild_id, trigger_word))""",
        """CREATE TABLE IF NOT EXISTS confessions (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, confession TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS reputation (user_id TEXT, guild_id TEXT, rep INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS quarantine (user_id TEXT, guild_id TEXT, reason TEXT, timestamp TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS trivia_scores (user_id TEXT, guild_id TEXT, score INTEGER DEFAULT 0, total INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS backup_data (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, backup_type TEXT, data TEXT, timestamp TEXT)"""
    ]
    for t in tables:
        c.execute(t)
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def get_db():
    conn = sqlite3.connect("sentinel.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_guild_settings(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (str(gid),))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"guild_id": str(gid), "mod_role_name": MOD_ROLE_NAME, "log_channel": MOD_LOG_CHANNEL, "raid_channel": RAID_CHANNEL, "warn_mute": 3, "warn_ban": 5, "mute_duration": 10, "spam_limit": 5, "spam_window": 5, "raid_limit": 10, "raid_window": 10, "min_account_age": 7, "scan_images": 1, "ai_sensitivity": 0.7, "welcome_channel": "welcome", "welcome_enabled": 1, "anti_nuke_enabled": 1, "invite_block": 0, "link_scan": 1, "slowmode_ai": 1, "pre_conflict": 1, "caps_filter": 1, "mention_spam": 1, "emoji_spam": 1, "zalgo_filter": 1, "phone_filter": 1, "email_filter": 1, "scam_filter": 1, "nsfw_text_filter": 1, "everyone_block": 0, "anti_advertisement": 1, "unicode_filter": 1, "fake_nitro_filter": 1, "token_filter": 1, "file_spam_filter": 1, "personality": "default"}

def init_guild_settings(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(gid),))
    conn.commit()
    conn.close()

def add_warning(uid, gid, reason, severity):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO warnings (user_id, guild_id, reason, severity, timestamp) VALUES (?, ?, ?, ?, ?)", (str(uid), str(gid), reason, severity, datetime.now().isoformat()))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_warnings(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM warnings WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC", (str(uid), str(gid)))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_warnings(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
    conn.commit()
    conn.close()

def log_mod_action(uid, gid, action, reason, mod_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO mod_actions (user_id, guild_id, action, reason, mod_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (str(uid), str(gid), action, reason, str(mod_id), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_memory(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT memory FROM user_memory WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
    row = c.fetchone()
    conn.close()
    return row["memory"] if row else ""

def update_user_memory(uid, gid, mem):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_memory (user_id, guild_id, memory, updated) VALUES (?, ?, ?, ?)", (str(uid), str(gid), mem, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_conversation_history(uid, gid, limit=20):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversation_history WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT ?", (str(uid), str(gid), limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def add_to_conversation(uid, gid, role, content):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO conversation_history (user_id, guild_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)", (str(uid), str(gid), role, content, datetime.now().isoformat()))
    conn.commit()
    c.execute("""DELETE FROM conversation_history WHERE id NOT IN (SELECT id FROM conversation_history WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT 50) AND user_id=? AND guild_id=?""", (str(uid), str(gid), str(uid), str(gid)))
    conn.commit()
    conn.close()

def get_user_personality(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT personality FROM user_personalities WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
    row = c.fetchone()
    conn.close()
    return row["personality"] if row else "default"

def set_user_personality(uid, gid, p):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_personalities (user_id, guild_id, personality) VALUES (?, ?, ?)", (str(uid), str(gid), p))
    conn.commit()
    conn.close()

def get_filtered_words(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT word FROM word_filters WHERE guild_id=?", (str(gid),))
    words = [r[0] for r in c.fetchall()]
    conn.close()
    return words

def update_message_stats(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO message_stats (user_id, guild_id, message_count, last_message) VALUES (?, ?, 1, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET message_count=message_count+1, last_message=?""", (str(uid), str(gid), datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ============ BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)
nuke_action_tracker = defaultdict(list)
recent_messages = defaultdict(list)
trivia_sessions = {}

# ============ AI ============
async def ask_groq(prompt, system="Helpful AI.", max_tokens=1000, history=None):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-15:])
    messages.append({"role": "user", "content": prompt})
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.8, "max_tokens": max_tokens}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq error: {e}")
    return None

async def ask_groq_json(prompt, system="Respond only in valid JSON."):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 1000}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
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

async def stream_response(message, prompt, system, history=None, uid=None, gid=None):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-15:])
    messages.append({"role": "user", "content": prompt})
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.8, "max_tokens": 1000, "stream": True}
    sent = await message.reply("💭 *thinking...*")
    full = ""
    last_update = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        line = line[6:]
                        if line == "[DONE]":
                            break
                        try:
                            data = json.loads(line)
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                full += content
                                if time.time() - last_update > 0.6:
                                    try:
                                        display = full[-1900:] if len(full) > 1900 else full
                                        await sent.edit(content=display + " ▌")
                                        last_update = time.time()
                                    except:
                                        pass
                        except:
                            pass
        if full:
            chunks = [full[i:i+2000] for i in range(0, len(full), 2000)]
            await sent.edit(content=chunks[0])
            for chunk in chunks[1:]:
                await message.channel.send(chunk)
            if uid and gid:
                add_to_conversation(uid, gid, "user", prompt)
                add_to_conversation(uid, gid, "assistant", full)
    except Exception as e:
        print(f"Stream error: {e}")
        if full:
            await sent.edit(content=full[:2000])
        else:
            await sent.edit(content="❌ Something went wrong!")

def get_system_prompt(uid, gid, extra=""):
    pkey = get_user_personality(uid, gid)
    personality = PERSONALITIES.get(pkey, PERSONALITIES["default"])
    memory = get_user_memory(uid, gid)
    return f"You are SentinelMod, a Discord bot.\nPersonality: {personality}\n{f'Memory: {memory}' if memory else ''}\n{extra}\nKeep responses under 1500 chars."

# ============ COMMAND PARSER ============
async def parse_command(content, guild, author):
    channels = [c.name for c in guild.text_channels][:15]
    roles = [r.name for r in guild.roles if r.name != "@everyone"][:15]
    members = [f"{m.name}(ID:{m.id})" for m in guild.members if not m.bot][:20]
    mentioned_ids = re.findall(r'<@!?(\d+)>', content)
    mentioned_names = [f"{guild.get_member(int(mid)).name}(ID:{mid})" for mid in mentioned_ids if guild.get_member(int(mid))]
    prompt = f"""STRICT Discord command parser.
Server: {guild.name}
Channels: {', '.join(channels)}
Roles: {', '.join(roles)}
Members: {', '.join(members)}
Mentioned: {', '.join(mentioned_names) if mentioned_names else 'NONE'}
Sender: {author.name}(ID:{author.id})
Message: "{content}"

CRITICAL: If message is unclear or chat → command="chat". For mod actions target MUST be mentioned. Never confuse sender with target.

JSON only:
{{"command":"create_channel|delete_channel|create_role|delete_role|create_category|delete_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|add_role_to_user|remove_role_from_user|start_giveaway|create_poll|set_afk|backup_server|setup_server|summarize|translate|add_word_filter|remove_word_filter|enable_feature|disable_feature|add_note|get_notes|set_autorole|raid_mode|trivia|wouldyourather|eightball|roast|compliment|dadjoke|ship|rate|fact|truthordare|story|debate|riddle|pickupline|horoscope|remind|confession|rep|server_health|activity_stats|mod_stats|suggestion|quarantine|unquarantine|add_custom_command|remove_custom_command|list_custom_commands|help|chat|unknown",
"needs_confirmation":true/false,
"confirmation_message":"detailed message",
"confidence":0.0-1.0,
"params":{{"name":null,"target_user_id":null,"target_user_name":null,"target_user2":null,"reason":null,"duration":null,"category":null,"color":null,"private":false,"amount":null,"prize":null,"winners":null,"question":null,"options":null,"language":null,"text":null,"feature":null,"word":null,"note":null,"channel":null,"topic":null,"response":null,"reminder_time":null,"rating_target":null,"zodiac":null}}}}"""
    return await ask_groq_json(prompt)

def find_member_strict(guild, params):
    uid = params.get("target_user_id")
    if uid:
        try:
            m = guild.get_member(int(uid))
            if m:
                return m
        except:
            pass
    name = params.get("target_user_name")
    if name:
        name = name.lower().strip().replace("@", "")
        for m in guild.members:
            if m.name.lower() == name or m.display_name.lower() == name:
                return m
    return None

# ============ FUN ============
async def do_trivia(message, gid, uid):
    trivia = await ask_groq_json('{"question":"q","correct":"a","wrong1":"b","wrong2":"c","wrong3":"d","category":"cat","difficulty":"easy"} Generate one trivia. JSON only.')
    if not trivia:
        return "❌ Failed!"
    answers = [trivia["correct"], trivia["wrong1"], trivia["wrong2"], trivia["wrong3"]]
    random.shuffle(answers)
    idx = answers.index(trivia["correct"])
    emojis = ["🇦","🇧","🇨","🇩"]
    embed = discord.Embed(title=f"🧠 {trivia['category']}", description=trivia["question"], color=discord.Color.blue())
    embed.add_field(name="Options", value="\n".join(f"{emojis[i]} {a}" for i, a in enumerate(answers)))
    msg = await message.channel.send(embed=embed)
    for e in emojis[:4]:
        await msg.add_reaction(e)
    trivia_sessions[msg.id] = {"correct_emoji": emojis[idx], "correct_answer": trivia["correct"], "guild_id": gid, "answered": []}
    await asyncio.sleep(30)
    if msg.id in trivia_sessions:
        await message.channel.send(f"⏰ Time's up! Answer: **{trivia['correct']}**")
        del trivia_sessions[msg.id]
    return None

async def do_fun_embed(ftype, params, author):
    prompts = {
        "wouldyourather": ("Generate fun Would You Rather.", "🤔 Would You Rather?"),
        "eightball": (f"8ball answer for: {params.get('question','...')}. Brief.", "🎱 8-Ball"),
        "roast": (f"Playful roast of {params.get('target_user_name','someone')}. Fun not mean.", "🔥 Roast"),
        "compliment": (f"Heartfelt compliment for {params.get('target_user_name', author.name)}.", "💝 Compliment"),
        "dadjoke": ("Tell a dad joke.", "👨 Dad Joke"),
        "ship": (f"Love compatibility {params.get('target_user_name','x')} + {params.get('target_user2','y')}.", "💕 Ship"),
        "rate": (f"Rate '{params.get('rating_target','life')}' out of 10.", "⭐ Rate"),
        "fact": ("Random surprising fact.", "🤯 Fact"),
        "truthordare": ("Truth or dare question.", "🎯 Truth or Dare"),
        "story": (f"Short story {('about '+params.get('text','')) if params.get('text') else ''}. 150 words.", "📖 Story"),
        "riddle": ("Riddle with answer.", "🧩 Riddle"),
        "pickupline": ("Creative pickup line.", "😘 Pickup"),
        "horoscope": (f"Horoscope for {params.get('zodiac','Aries')}.", "⭐ Horoscope"),
    }
    p, title = prompts.get(ftype, ("Tell joke.", "😄"))
    result = await ask_groq(p, "Fun Discord bot.")
    if result:
        return discord.Embed(title=title, description=result, color=discord.Color.blue())
    return None

# ============ EXECUTE COMMAND ============
async def execute_command(parsed, message, guild, author):
    cmd = parsed.get("command", "unknown")
    params = parsed.get("params", {})
    settings = get_guild_settings(guild.id)
    try:
        if cmd == "create_channel":
            name = (params.get("name") or "new").lower().replace(" ", "-")
            existing = discord.utils.get(guild.text_channels, name=name)
            if existing:
                return f"⏭️ {existing.mention} exists!"
            cat = None
            if params.get("category"):
                cat = discord.utils.get(guild.categories, name=params["category"])
                if not cat:
                    cat = await guild.create_category(name=params["category"])
            ow = {}
            if params.get("private"):
                ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False), author: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
            ch = await guild.create_text_channel(name=name, category=cat, topic=params.get("topic",""), overwrites=ow)
            return f"✅ Created {ch.mention}!"
        elif cmd == "delete_channel":
            name = (params.get("name") or params.get("channel") or "").lower().replace(" ", "-")
            ch = discord.utils.get(guild.text_channels, name=name)
            if not ch:
                return f"❌ Not found."
            await ch.delete()
            return f"🗑️ Deleted **#{name}**!"
        elif cmd == "create_role":
            name = params.get("name") or "Role"
            if discord.utils.get(guild.roles, name=name):
                return f"⏭️ Role exists!"
            color = discord.Color.default()
            if params.get("color"):
                try:
                    color = discord.Color(int(params["color"].replace("#",""), 16))
                except:
                    pass
            role = await guild.create_role(name=name, color=color, hoist=params.get("hoist", False), mentionable=params.get("mentionable", False))
            return f"✅ Created {role.mention}!"
        elif cmd == "delete_role":
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not role:
                return "❌ Not found."
            await role.delete()
            return f"🗑️ Deleted!"
        elif cmd == "create_category":
            name = params.get("name") or "Category"
            if discord.utils.get(guild.categories, name=name):
                return f"⏭️ Exists!"
            await guild.create_category(name=name)
            return f"✅ Created **{name}**!"
        elif cmd == "delete_category":
            cat = discord.utils.get(guild.categories, name=params.get("name"))
            if not cat:
                return "❌ Not found."
            await cat.delete()
            return f"🗑️ Deleted!"
        elif cmd == "ban_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found. @mention them!"
            if t.id == author.id:
                return "❌ Can't ban yourself!"
            reason = params.get("reason") or "No reason"
            try:
                await t.send(f"🔨 Banned from **{guild.name}**: {reason}")
            except:
                pass
            await guild.ban(t, reason=f"{author.name}: {reason}")
            log_mod_action(t.id, guild.id, "BAN", reason, author.id)
            add_warning(t.id, guild.id, reason, "critical")
            await alert_mods(guild, discord.Embed(title="🔨 Banned", color=discord.Color.dark_red()).add_field(name="User", value=f"{t}").add_field(name="By", value=author.mention).add_field(name="Reason", value=reason))
            return f"🔨 Banned **{t.name}**!"
        elif cmd == "kick_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found!"
            if t.id == author.id:
                return "❌ Can't kick yourself!"
            reason = params.get("reason") or "No reason"
            try:
                await t.send(f"👢 Kicked from **{guild.name}**: {reason}")
            except:
                pass
            await guild.kick(t, reason=f"{author.name}: {reason}")
            log_mod_action(t.id, guild.id, "KICK", reason, author.id)
            await alert_mods(guild, discord.Embed(title="👢 Kicked", color=discord.Color.orange()).add_field(name="User", value=f"{t}").add_field(name="By", value=author.mention))
            return f"👢 Kicked **{t.name}**!"
        elif cmd == "mute_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found!"
            dur = int(params.get("duration") or 10)
            reason = params.get("reason") or "No reason"
            await t.timeout(datetime.now() + timedelta(minutes=dur), reason=reason)
            log_mod_action(t.id, guild.id, "MUTE", reason, author.id)
            add_warning(t.id, guild.id, reason, "medium")
            try:
                await t.send(f"🔇 Muted in **{guild.name}** for {dur}min: {reason}")
            except:
                pass
            return f"🔇 Muted **{t.name}** for {dur}min!"
        elif cmd == "unmute_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            await t.timeout(None)
            return f"🔊 Unmuted **{t.name}**!"
        elif cmd == "warn_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found!"
            reason = params.get("reason") or "No reason"
            wc = add_warning(t.id, guild.id, reason, "manual")
            log_mod_action(t.id, guild.id, "WARN", reason, author.id)
            try:
                await t.send(f"⚠️ Warning in **{guild.name}**: {reason} ({wc}/{settings.get('warn_ban',5)})")
            except:
                pass
            return f"⚠️ Warned **{t.name}** ({wc} warnings)"
        elif cmd == "clear_warnings":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            clear_warnings(t.id, guild.id)
            return f"✅ Cleared **{t.name}** warnings!"
        elif cmd == "warn_check":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            ws = get_warnings(t.id, guild.id)
            if not ws:
                return f"✅ **{t.name}** has no warnings!"
            return f"**{t.name}** - {len(ws)} warnings:\n" + "\n".join(f"#{i+1} [{w['severity']}] {w['reason']}" for i, w in enumerate(ws[:5]))
        elif cmd == "quarantine":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            reason = params.get("reason") or "Suspicious"
            q = discord.utils.get(guild.roles, name="Quarantined")
            if not q:
                q = await guild.create_role(name="Quarantined", color=discord.Color.dark_gray())
                for ch in guild.text_channels:
                    try:
                        await ch.set_permissions(q, send_messages=False)
                    except:
                        pass
            await t.add_roles(q, reason=reason)
            return f"🔒 Quarantined **{t.name}**!"
        elif cmd == "unquarantine":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            q = discord.utils.get(guild.roles, name="Quarantined")
            if q and q in t.roles:
                await t.remove_roles(q)
            return f"✅ Unquarantined **{t.name}**!"
        elif cmd == "lock_channel":
            ch = message.channel
            await ch.set_permissions(guild.default_role, send_messages=False)
            return f"🔒 Locked {ch.mention}!"
        elif cmd == "unlock_channel":
            ch = message.channel
            await ch.set_permissions(guild.default_role, send_messages=None)
            return f"🔓 Unlocked {ch.mention}!"
        elif cmd == "lockdown":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=False)
                    count += 1
                except:
                    pass
            return f"🔒 Locked {count} channels!"
        elif cmd == "unlock_server":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=None)
                    count += 1
                except:
                    pass
            return f"🔓 Unlocked {count} channels!"
        elif cmd == "slowmode":
            dur = int(params.get("duration") or 5)
            await message.channel.edit(slowmode_delay=dur)
            return f"🐌 Slowmode: {dur}s!"
        elif cmd == "purge":
            amt = min(int(params.get("amount") or 10), 100)
            d = await message.channel.purge(limit=amt+1)
            return f"🗑️ Deleted {len(d)-1}!"
        elif cmd == "add_role_to_user":
            t = find_member_strict(guild, params)
            r = discord.utils.get(guild.roles, name=params.get("name"))
            if not t or not r:
                return "❌ Not found."
            await t.add_roles(r)
            return f"✅ Added {r.name} to {t.mention}!"
        elif cmd == "remove_role_from_user":
            t = find_member_strict(guild, params)
            r = discord.utils.get(guild.roles, name=params.get("name"))
            if not t or not r:
                return "❌ Not found."
            await t.remove_roles(r)
            return f"✅ Removed {r.name}!"
        elif cmd == "trivia":
            await do_trivia(message, guild.id, author.id)
            return None
        elif cmd == "wouldyourather":
            e = await do_fun_embed("wouldyourather", params, author)
            if e:
                msg = await message.channel.send(embed=e)
                await msg.add_reaction("🅰️")
                await msg.add_reaction("🅱️")
            return None
        elif cmd in ["eightball","roast","compliment","dadjoke","ship","rate","fact","truthordare","story","riddle","pickupline","horoscope"]:
            e = await do_fun_embed(cmd, params, author)
            if e:
                await message.channel.send(embed=e)
            return None
        elif cmd == "debate":
            topic = params.get("text") or "pineapple pizza"
            r = await ask_groq(f"Start debate: {topic}", "Debate moderator.")
            if r:
                msg = await message.channel.send(embed=discord.Embed(title=f"⚔️ {topic}", description=r, color=discord.Color.orange()))
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
            return None
        elif cmd == "remind":
            text = params.get("text") or "Reminder!"
            mins = int(params.get("reminder_time") or params.get("duration") or 10)
            t = datetime.now() + timedelta(minutes=mins)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reminders (user_id, guild_id, channel_id, reminder, remind_time) VALUES (?, ?, ?, ?, ?)", (str(author.id), str(guild.id), str(message.channel.id), text, t.isoformat()))
            conn.commit()
            conn.close()
            return f"⏰ Reminder in {mins}min: **{text}**"
        elif cmd == "confession":
            text = params.get("text") or params.get("note")
            if not text:
                return "❌ What's the confession?"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO confessions (guild_id, confession, timestamp) VALUES (?, ?, ?)", (str(guild.id), text, datetime.now().isoformat()))
            cid = c.lastrowid
            conn.commit()
            conn.close()
            await message.channel.send(embed=discord.Embed(title=f"🤫 Confession #{cid}", description=text, color=discord.Color.dark_purple()))
            try:
                await message.delete()
            except:
                pass
            return None
        elif cmd == "rep":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ @mention them!"
            if t.id == author.id:
                return "❌ Can't rep yourself!"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reputation (user_id, guild_id, rep) VALUES (?, ?, 1) ON CONFLICT(user_id, guild_id) DO UPDATE SET rep=rep+1", (str(t.id), str(guild.id)))
            conn.commit()
            c.execute("SELECT rep FROM reputation WHERE user_id=? AND guild_id=?", (str(t.id), str(guild.id)))
            rep = c.fetchone()[0]
            conn.close()
            return f"✅ +1 to {t.name}! Total: {rep}"
        elif cmd == "start_giveaway":
            prize = params.get("prize") or "Mystery"
            dur = int(params.get("duration") or 60)
            wins = int(params.get("winners") or 1)
            end = datetime.now() + timedelta(minutes=dur)
            embed = discord.Embed(title="🎉 GIVEAWAY!", description=f"**Prize:** {prize}\nReact 🎉!", color=discord.Color.gold())
            embed.add_field(name="Winners", value=str(wins))
            embed.add_field(name="Ends", value=f"<t:{int(end.timestamp())}:R>")
            msg = await message.channel.send(embed=embed)
            await msg.add_reaction("🎉")
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, host_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(guild.id), str(message.channel.id), str(msg.id), prize, wins, end.isoformat(), str(author.id)))
            conn.commit()
            conn.close()
            return f"🎉 Started!"
        elif cmd == "create_poll":
            q = params.get("question") or "Poll"
            opts = params.get("options") or ["Yes","No"]
            emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
            embed = discord.Embed(title=f"📊 {q}", color=discord.Color.blue())
            for i, o in enumerate(opts[:5]):
                embed.add_field(name=f"{emojis[i]} {o}", value="\u200b", inline=False)
            msg = await message.channel.send(embed=embed)
            for i in range(len(opts[:5])):
                await msg.add_reaction(emojis[i])
            return None
        elif cmd == "set_afk":
            reason = params.get("reason") or params.get("text") or "AFK"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO afk_users (user_id, guild_id, reason, timestamp) VALUES (?, ?, ?, ?)", (str(author.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💤 AFK: **{reason}**"
        elif cmd == "backup_server":
            r = [{"name":x.name,"color":str(x.color)} for x in guild.roles if x.name != "@everyone"]
            ch = [{"name":x.name,"category":x.category.name if x.category else None} for x in guild.text_channels]
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO backup_data (guild_id, backup_type, data, timestamp) VALUES (?, ?, ?, ?)", (str(guild.id), "full", json.dumps({"roles":r,"channels":ch}), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💾 Backed up {len(r)} roles & {len(ch)} channels!"
        elif cmd == "setup_server":
            results = await setup_server(guild)
            return "🛡️ Setup!\n" + "\n".join(results[:10])
        elif cmd == "summarize":
            amt = min(int(params.get("amount") or 20), 50)
            msgs = []
            async for m in message.channel.history(limit=amt):
                if not m.author.bot:
                    msgs.append(f"{m.author.display_name}: {m.content}")
            if not msgs:
                return "❌ No messages."
            s = await ask_groq("Summarize in bullets:\n" + "\n".join(reversed(msgs)), "Summarizer.")
            return f"📝 **Summary:**\n{s}"
        elif cmd == "translate":
            text = params.get("text") or ""
            lang = params.get("language") or "English"
            if not text:
                return "❌ No text."
            t = await ask_groq(f"Translate to {lang}, only translation:\n{text}", "Translator.")
            return f"🌐 **{lang}:** {t}"
        elif cmd == "add_word_filter":
            w = params.get("word")
            if not w:
                return "❌ No word."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)", (str(guild.id), w.lower()))
            conn.commit()
            conn.close()
            return f"✅ Added **{w}**!"
        elif cmd == "remove_word_filter":
            w = params.get("word")
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (str(guild.id), w.lower()))
            conn.commit()
            conn.close()
            return f"✅ Removed **{w}**!"
        elif cmd == "add_note":
            t = find_member_strict(guild, params)
            note = params.get("note") or params.get("text")
            if not t or not note:
                return "❌ Specify user and note."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO user_notes (guild_id, user_id, note, mod_id, timestamp) VALUES (?, ?, ?, ?, ?)", (str(guild.id), str(t.id), note, str(author.id), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"📝 Note added for **{t.name}**!"
        elif cmd == "get_notes":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM user_notes WHERE guild_id=? AND user_id=?", (str(guild.id), str(t.id)))
            n = c.fetchall()
            conn.close()
            if not n:
                return f"📝 No notes."
            return f"📝 **{t.name}:**\n" + "\n".join(f"• {x['note']}" for x in n)
        elif cmd == "set_autorole":
            r = discord.utils.get(guild.roles, name=params.get("name"))
            if not r:
                return "❌ Not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO auto_roles (guild_id, role_id) VALUES (?, ?)", (str(guild.id), str(r.id)))
            conn.commit()
            conn.close()
            return f"✅ {r.name} auto-assigned!"
        elif cmd == "raid_mode":
            text = (params.get("feature") or params.get("text") or "").lower()
            status = "on" in text or "enable" in text
            raid_mode_active[guild.id] = status
            return f"🚨 Raid mode {'ON' if status else 'OFF'}!"
        elif cmd == "server_health":
            total = guild.member_count
            bots = sum(1 for m in guild.members if m.bot)
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (str(guild.id),))
            wc = c.fetchone()[0]
            conn.close()
            score = max(0, 100 - (wc // 5))
            await message.channel.send(embed=discord.Embed(title="🏥 Server Health", color=discord.Color.green()).add_field(name="Score", value=f"{score}/100").add_field(name="Members", value=str(total-bots)).add_field(name="Warnings", value=str(wc)))
            return None
        elif cmd == "activity_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 10", (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "📊 No data."
            lines = []
            medals = ["🥇","🥈","🥉"]
            for i, r in enumerate(top):
                m = guild.get_member(int(r["user_id"]))
                medal = medals[i] if i < 3 else f"#{i+1}"
                lines.append(f"{medal} {m.display_name if m else '?'}: **{r['message_count']}**")
            await message.channel.send(embed=discord.Embed(title="📊 Activity", description="\n".join(lines), color=discord.Color.blue()))
            return None
        elif cmd == "mod_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT mod_id, COUNT(*) as t FROM mod_actions WHERE guild_id=? GROUP BY mod_id ORDER BY t DESC LIMIT 5", (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "🛡️ No data."
            lines = []
            for i, r in enumerate(top, 1):
                m = guild.get_member(int(r["mod_id"]))
                lines.append(f"#{i} {m.display_name if m else '?'}: **{r['t']}**")
            await message.channel.send(embed=discord.Embed(title="🛡️ Mods", description="\n".join(lines), color=discord.Color.red()))
            return None
        elif cmd == "suggestion":
            text = params.get("text") or params.get("note")
            if not text:
                return "❌ What suggestion?"
            ch = discord.utils.get(guild.text_channels, name="suggestions")
            if ch:
                msg = await ch.send(embed=discord.Embed(title="💡 Suggestion", description=text, color=discord.Color.blue()).set_footer(text=f"By {author.display_name}"))
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
                return f"✅ Posted!"
            return "❌ No suggestions channel."
        elif cmd == "add_custom_command":
            trigger = (params.get("name") or params.get("word") or "").lower().strip()
            response = params.get("response") or params.get("text") or params.get("note")
            if not trigger or not response:
                return "❌ Need trigger and response!"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO custom_commands (guild_id, trigger_word, response) VALUES (?, ?, ?)", (str(guild.id), trigger, response))
            conn.commit()
            conn.close()
            return f"✅ Custom command `{trigger}` added!"
        elif cmd == "remove_custom_command":
            trigger = (params.get("name") or params.get("word") or "").lower().strip()
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM custom_commands WHERE guild_id=? AND trigger_word=?", (str(guild.id), trigger))
            removed = c.rowcount
            conn.commit()
            conn.close()
            return f"✅ Removed `{trigger}`!" if removed else f"❌ Not found."
        elif cmd == "list_custom_commands":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT trigger_word, response FROM custom_commands WHERE guild_id=?", (str(guild.id),))
            cmds = c.fetchall()
            conn.close()
            if not cmds:
                return "📋 No custom commands yet!"
            embed = discord.Embed(title="📋 Custom Commands", color=discord.Color.blue())
            for c in cmds[:25]:
                embed.add_field(name=f"`{c['trigger_word']}`", value=c['response'][:100], inline=False)
            await message.channel.send(embed=embed)
            return None
        elif cmd in ["enable_feature","disable_feature"]:
            f = (params.get("feature") or "").lower().replace(" ","_")
            v = 1 if cmd == "enable_feature" else 0
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(f"UPDATE guild_settings SET {f}=? WHERE guild_id=?", (v, str(guild.id)))
                conn.commit()
                return f"{'✅ Enabled' if v else '❌ Disabled'} {f}!"
            except:
                return f"❌ Unknown: {f}"
            finally:
                conn.close()
        elif cmd == "help":
            await message.channel.send(embed=discord.Embed(title="🛡️ SentinelMod", description="@mention me or chat in #sentinel-bot!\nWeb dashboard: check your render URL!", color=discord.Color.blue()).add_field(name="Mod", value="ban/kick/mute/warn/purge").add_field(name="Fun", value="trivia/roast/ship/8ball").add_field(name="AI", value="summarize/translate/story").add_field(name="Server", value="make channel/role/category"))
            return None
        else:
            return None
    except discord.Forbidden:
        return "❌ No permission!"
    except Exception as e:
        print(f"Error: {e}")
        return f"❌ {str(e)[:100]}"

# ============ MODERATION ============
async def alert_mods(guild, embed):
    settings = get_guild_settings(guild.id)
    ch = discord.utils.get(guild.text_channels, name=settings["log_channel"])
    mr = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    if ch:
        await ch.send(content=mr.mention if mr else "", embed=embed)

async def check_spam(msg, settings):
    key = f"{msg.author.id}:{msg.guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    w = settings.get("spam_window", 5)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < w]
    return len(spam_tracker[key]) >= settings.get("spam_limit", 5)

async def handle_spam(msg, settings):
    try:
        await msg.channel.purge(limit=10, check=lambda m: m.author == msg.author)
    except:
        pass
    try:
        await msg.author.timeout(datetime.now() + timedelta(minutes=settings.get("mute_duration",10)), reason="Spam")
    except:
        pass
    wc = add_warning(msg.author.id, msg.guild.id, "Spam", "medium")
    await alert_mods(msg.guild, discord.Embed(title="🔇 Spam", color=discord.Color.orange()).add_field(name="User", value=msg.author.mention).add_field(name="Warnings", value=str(wc)))

async def check_raid(member):
    g = member.guild
    s = get_guild_settings(g.id)
    now = time.time()
    raid_tracker[g.id].append(now)
    raid_tracker[g.id] = [t for t in raid_tracker[g.id] if now - t < s.get("raid_window", 10)]
    return len(raid_tracker[g.id]) >= s.get("raid_limit", 10)

async def handle_raid(guild, member):
    s = get_guild_settings(guild.id)
    if not raid_mode_active[guild.id]:
        raid_mode_active[guild.id] = True
        ch = discord.utils.get(guild.text_channels, name=s["raid_channel"])
        mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
        if ch:
            await ch.send(content=f"🚨 {mr.mention if mr else ''} RAID!", embed=discord.Embed(title="🚨 RAID", color=discord.Color.red()))
        await asyncio.sleep(300)
        raid_mode_active[guild.id] = False
    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    if age < s.get("min_account_age", 7):
        try:
            await member.kick(reason="Raid protection")
        except:
            pass

async def check_patterns(msg, settings):
    content = msg.content
    cl = content.lower()
    if settings.get("phone_filter",1) and re.search(r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b', content):
        return "phone", "Phone number", "high"
    if settings.get("email_filter",1) and re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
        return "email", "Email", "high"
    keywords = [
        (settings.get("fake_nitro_filter",1), ["free nitro","claim nitro"], "fake_nitro", "Nitro scam", "critical"),
        (settings.get("token_filter",1), ["discord token","grabify"], "token", "Token grabber", "critical"),
        (settings.get("scam_filter",1), ["you won","claim your prize","account will be deleted"], "scam", "Scam", "critical"),
        (settings.get("anti_advertisement",1), ["join my server","subscribe to my"], "ad", "Advertisement", "medium"),
        (1, ["want to kill myself","want to die"], "self_harm", "Self-harm", "high"),
        (1, ["death to all","kill all","exterminate"], "extremism", "Extremism", "critical"),
    ]
    for en, words, t, r, sev in keywords:
        if en and any(w in cl for w in words):
            return t, r, sev
    if settings.get("caps_filter",1) and len(content) > 10:
        if sum(1 for c in content if c.isupper())/len(content) > 0.7:
            return "caps", "Caps", "low"
    if settings.get("mention_spam",1) and len(msg.mentions) >= 5:
        return "mentions", "Mention spam", "high"
    if settings.get("invite_block",0) and re.search(r'(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', content):
        return "invite", "Invite", "medium"
    if settings.get("link_scan",1) and "http" in cl:
        bad = ["grabify","iplogger","discord.gift","free-nitro","phish"]
        for b in bad:
            if b in cl:
                return "phishing", f"Phishing: {b}", "critical"
    return None, None, None

async def check_toxicity(content, context=""):
    return await ask_groq_json(f'Analyze: "{content}" Context: {context}\nJSON: {{"toxic":true/false,"severity":"none|low|medium|high|critical","category":"none|harassment|threat|hate","confidence":0.0-1.0,"reason":"brief"}}')

async def punish_user(msg, sev, reason, analysis):
    u = msg.author
    g = msg.guild
    s = get_guild_settings(g.id)
    wc = add_warning(u.id, g.id, reason, sev)
    try:
        await msg.delete()
    except:
        pass
    try:
        await u.send(f"⚠️ Message removed in **{g.name}**: {reason}")
    except:
        pass
    if wc >= s.get("warn_mute",3) and wc < s.get("warn_ban",5):
        try:
            await u.timeout(datetime.now() + timedelta(minutes=s.get("mute_duration",10)), reason=reason)
        except:
            pass
    if wc >= s.get("warn_ban",5):
        try:
            await g.ban(u, reason=reason)
        except:
            pass
    await alert_mods(g, discord.Embed(title="🚨 AI Mod", color=discord.Color.red()).add_field(name="User", value=u.mention).add_field(name="Severity", value=sev).add_field(name="Reason", value=reason).add_field(name="Warnings", value=str(wc)))

# ============ SETUP & VIEWS ============
async def setup_server(guild):
    results = []
    s = get_guild_settings(guild.id)
    for rn, c, h in [(s["mod_role_name"], discord.Color.red(), True), ("Muted", discord.Color.dark_gray(), False), ("Member", discord.Color.blue(), False)]:
        if not discord.utils.get(guild.roles, name=rn):
            try:
                await guild.create_role(name=rn, color=c, hoist=h)
                results.append(f"✅ Role: {rn}")
            except:
                results.append(f"❌ Role: {rn}")
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    scat = discord.utils.get(guild.categories, name="🛡️ SENTINELAI")
    if not scat:
        try:
            ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True)}
            if mr:
                ow[mr] = discord.PermissionOverwrite(read_messages=True)
            scat = await guild.create_category(name="🛡️ SENTINELAI", overwrites=ow)
            results.append("✅ Category SENTINELAI")
        except:
            pass
    for cn, t in [(s["log_channel"],"Mod logs"),(s["raid_channel"],"Raids"),("sentinel-bot","Chat with AI!")]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, category=scat, topic=t)
                results.append(f"✅ #{cn}")
            except:
                results.append(f"❌ #{cn}")
    for cn, t in [("welcome","Welcome"),("rules","Rules"),("general","Chat"),("suggestions","Ideas")]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, topic=t)
                results.append(f"✅ #{cn}")
            except:
                pass
    return results

class ConfirmView(discord.ui.View):
    def __init__(self, parsed, msg, guild, author):
        super().__init__(timeout=30)
        self.parsed = parsed
        self.msg = msg
        self.guild = guild
        self.author = author
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, i, b):
        if i.user.id != self.author.id:
            await i.response.send_message("❌ Only requester.", ephemeral=True)
            return
        await i.response.defer()
        r = await execute_command(self.parsed, self.msg, self.guild, self.author)
        if r:
            await i.followup.send(r)
        self.stop()
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, i, b):
        await i.response.send_message("❌ Cancelled.")
        self.stop()

# ============ SLASH COMMANDS ============
@bot.tree.command(name="personality", description="Choose personality")
async def personality_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎭 Personalities", description="Pick from dropdown!", color=discord.Color.purple())
    embed.add_field(name="Available", value=", ".join(f"`{p}`" for p in list(PERSONALITIES.keys())[:20]))
    embed.set_footer(text=f"Current: {get_user_personality(str(interaction.user.id), str(interaction.guild.id))}")
    opts = [discord.SelectOption(label=n.replace("_"," ").title(), value=n) for n in list(PERSONALITIES.keys())[:25]]
    view = discord.ui.View(timeout=60)
    select = discord.ui.Select(placeholder="Choose...", options=opts)
    async def cb(i):
        p = i.data["values"][0]
        set_user_personality(str(i.user.id), str(i.guild.id), p)
        await i.response.send_message(f"✅ Now: **{p}**!", ephemeral=True)
    select.callback = cb
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="setpersonality", description="Set personality by name")
async def setpersonality_cmd(interaction: discord.Interaction, personality: str):
    p = personality.lower().replace(" ", "_")
    if p not in PERSONALITIES:
        await interaction.response.send_message(f"❌ Unknown. Use /personality", ephemeral=True)
        return
    set_user_personality(str(interaction.user.id), str(interaction.guild.id), p)
    await interaction.response.send_message(f"✅ **{p}**!", ephemeral=True)

@bot.tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ SentinelMod Help", color=discord.Color.blue())
    embed.add_field(name="💬 Chat", value=f"@mention me or chat in #sentinel-bot", inline=False)
    embed.add_field(name="🔧 Server", value="make/delete channels, roles, categories", inline=False)
    embed.add_field(name="🔨 Moderation", value="ban, kick, mute, warn, purge, lock", inline=False)
    embed.add_field(name="🎮 Fun", value="trivia, roast, compliment, 8ball, ship, rate", inline=False)
    embed.add_field(name="🤖 AI", value="summarize, translate, story, debate", inline=False)
    embed.add_field(name="🎭 Personality", value="/personality or /setpersonality", inline=False)
    embed.add_field(name="🌐 Dashboard", value=f"{REDIRECT_URI.replace('/callback','')}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="dashboard", description="Get dashboard link")
async def dashboard_cmd(interaction: discord.Interaction):
    url = REDIRECT_URI.replace('/callback', '')
    embed = discord.Embed(title="🌐 Web Dashboard", description=f"Manage your server here:\n**{url}**", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============ TASKS ============
@tasks.loop(minutes=1)
async def check_giveaways():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM giveaways WHERE active=1 AND end_time<=?", (datetime.now().isoformat(),))
    ended = [dict(r) for r in c.fetchall()]
    conn.close()
    for g in ended:
        try:
            guild = bot.get_guild(int(g["guild_id"]))
            ch = guild.get_channel(int(g["channel_id"])) if guild else None
            msg = await ch.fetch_message(int(g["message_id"])) if ch else None
            if not msg:
                continue
            r = discord.utils.get(msg.reactions, emoji="🎉")
            users = [u async for u in r.users() if not u.bot] if r else []
            if users:
                w = random.sample(users, min(g["winners"], len(users)))
                m = ", ".join(x.mention for x in w)
                await ch.send(f"🎉 {m}!", embed=discord.Embed(title="🎉 Giveaway Ended!", description=f"**Prize:** {g['prize']}\n**Winners:** {m}", color=discord.Color.gold()))
            else:
                await ch.send("❌ No entries!")
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE giveaways SET active=0 WHERE id=?", (g["id"],))
            conn.commit()
            conn.close()
        except:
            pass

@tasks.loop(minutes=1)
async def check_reminders():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM reminders WHERE active=1 AND remind_time<=?", (datetime.now().isoformat(),))
    due = [dict(r) for r in c.fetchall()]
    for rem in due:
        try:
            ch = bot.get_channel(int(rem["channel_id"]))
            if ch:
                await ch.send(f"⏰ <@{rem['user_id']}>: **{rem['reminder']}**")
        except:
            pass
        c.execute("UPDATE reminders SET active=0 WHERE id=?", (rem["id"],))
    conn.commit()
    conn.close()

# ============ EVENTS ============
@bot.event
async def on_ready():
    print(f"🤖 {bot.user} ONLINE in {len(bot.guilds)} servers")
    for g in bot.guilds:
        init_guild_settings(g.id)
    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} commands synced")
    except Exception as e:
        print(f"Sync error: {e}")
    check_giveaways.start()
    check_reminders.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="everything 👁️"))

@bot.event
async def on_guild_join(guild):
    init_guild_settings(guild.id)
    await setup_server(guild)

@bot.event
async def on_member_join(member):
    g = member.guild
    s = get_guild_settings(g.id)
    if await check_raid(member):
        await handle_raid(g, member)
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role_id FROM auto_roles WHERE guild_id=?", (str(g.id),))
    for r in c.fetchall():
        role = g.get_role(int(r[0]))
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    conn.close()
    if s.get("welcome_enabled", 1):
        wch = discord.utils.get(g.text_channels, name=s.get("welcome_channel","welcome"))
        if wch:
            w = await ask_groq(f"Short welcome for {member.display_name} joining {g.name}.", "Friendly.")
            if w:
                embed = discord.Embed(title=f"👋 Welcome to {g.name}!", description=w, color=discord.Color.green())
                embed.set_thumbnail(url=member.display_avatar.url)
                await wch.send(content=member.mention, embed=embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.message.id in trivia_sessions:
        s = trivia_sessions[reaction.message.id]
        if user.id in s["answered"]:
            return
        s["answered"].append(user.id)
        if str(reaction.emoji) == s["correct_emoji"]:
            await reaction.message.channel.send(f"✅ {user.mention} correct! **{s['correct_answer']}**")
            del trivia_sessions[reaction.message.id]

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    s = get_guild_settings(message.guild.id)
    mr = discord.utils.get(message.guild.roles, name=s["mod_role_name"])
    is_mod = mr and mr in message.author.roles
    is_admin = message.author.guild_permissions.administrator
    update_message_stats(message.author.id, message.guild.id)
    # AFK
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM afk_users WHERE guild_id=?", (str(message.guild.id),))
    afk = {r["user_id"]: dict(r) for r in c.fetchall()}
    conn.close()
    if str(message.author.id) in afk:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM afk_users WHERE user_id=? AND guild_id=?", (str(message.author.id), str(message.guild.id)))
        conn.commit()
        conn.close()
        try:
            await message.channel.send(f"👋 Welcome back {message.author.mention}!", delete_after=5)
        except:
            pass
    for m in message.mentions:
        if str(m.id) in afk:
            await message.channel.send(f"💤 {m.mention} AFK: **{afk[str(m.id)]['reason']}**", delete_after=10)
    # Custom commands
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT response FROM custom_commands WHERE guild_id=? AND trigger_word=?", (str(message.guild.id), message.content.lower()))
    cc = c.fetchone()
    conn.close()
    if cc:
        await message.channel.send(cc["response"])
        return
    # AI / Commands
    is_ai_ch = message.channel.name == AI_CHAT_CHANNEL
    is_ment = bot.user in message.mentions
    if is_ai_ch or is_ment:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content and not is_ai_ch:
            await message.reply(f"👋 Try `@{BOT_NAME} help`")
            return
        if content:
            if is_mod or is_admin:
                async with message.channel.typing():
                    parsed = await parse_command(content, message.guild, message.author)
                if parsed and parsed.get("command") not in ["chat","unknown",None]:
                    conf = parsed.get("confidence", 0)
                    if conf < 0.7:
                        sys = get_system_prompt(str(message.author.id), str(message.guild.id))
                        hist = get_conversation_history(str(message.author.id), str(message.guild.id))
                        await stream_response(message, content, sys, hist, str(message.author.id), str(message.guild.id))
                        return
                    dangerous = ["ban_user","kick_user","mute_user","warn_user","delete_channel","delete_role","delete_category","lockdown","purge","clear_warnings","quarantine"]
                    if parsed.get("command") in dangerous:
                        tn = parsed.get("params",{}).get("target_user_name")
                        ti = parsed.get("params",{}).get("target_user_id")
                        if tn or ti:
                            t = find_member_strict(message.guild, parsed.get("params",{}))
                            if not t:
                                await message.reply(f"❌ User not found. @mention them!")
                                return
                    nc = parsed.get("needs_confirmation", False) or parsed.get("command") in dangerous
                    if nc:
                        embed = discord.Embed(title=f"⚠️ Confirm: {parsed.get('command','').replace('_',' ').title()}", description=parsed.get("confirmation_message","Confirm?"), color=discord.Color.orange())
                        view = ConfirmView(parsed, message, message.guild, message.author)
                        await message.reply(embed=embed, view=view)
                    else:
                        async with message.channel.typing():
                            r = await execute_command(parsed, message, message.guild, message.author)
                        if r:
                            await message.reply(r[:2000])
                    return
            sys = get_system_prompt(str(message.author.id), str(message.guild.id))
            hist = get_conversation_history(str(message.author.id), str(message.guild.id))
            await stream_response(message, content, sys, hist, str(message.author.id), str(message.guild.id))
            return
    if is_mod or is_admin:
        await bot.process_commands(message)
        return
    if await check_spam(message, s):
        await handle_spam(message, s)
        return
    pt, pr, ps = await check_patterns(message, s)
    if pt:
        try:
            await message.delete()
        except:
            pass
        if pt == "self_harm":
            try:
                await message.channel.send(embed=discord.Embed(title="💙 We're Here", description=f"{message.author.mention} please reach out:\n**988** Suicide Prevention\nText **HOME** to **741741**", color=discord.Color.blue()))
            except:
                pass
        wc = add_warning(message.author.id, message.guild.id, pr, ps)
        if ps in ["high","critical"]:
            await alert_mods(message.guild, discord.Embed(title=f"🚨 {pt}", color=discord.Color.red()).add_field(name="User", value=message.author.mention).add_field(name="Reason", value=pr))
        if ps == "critical":
            try:
                await message.guild.ban(message.author, reason=f"IMMEDIATE: {pr}")
            except:
                pass
        return
    # Word filter
    for w in get_filtered_words(message.guild.id):
        if w in message.content.lower():
            try:
                await message.delete()
            except:
                pass
            add_warning(message.author.id, message.guild.id, "Filtered", "medium")
            await message.channel.send(f"⚠️ {message.author.mention} word not allowed!", delete_after=5)
            return
    if len(message.content) < 3:
        await bot.process_commands(message)
        return
    # Toxicity
    ctx = ""
    try:
        h = []
        async for m in message.channel.history(limit=5, before=message):
            if not m.author.bot:
                h.append(f"{m.author.name}: {m.content}")
        ctx = "\n".join(reversed(h))
    except:
        pass
    a = await check_toxicity(message.content, ctx)
    if a and a.get("toxic"):
        sev = a.get("severity","low")
        conf = a.get("confidence",0)
        if conf >= s.get("ai_sensitivity",0.7):
            if sev in ["medium","high","critical"]:
                await punish_user(message, sev, a.get("reason","Toxic"), a)
    await bot.process_commands(message)

# ============================
# DASHBOARD
# ============================
app = Flask(__name__)
app.secret_key = SECRET_KEY

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>SentinelMod Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
body { background: linear-gradient(135deg, #1a1c2e, #2d1b4e); min-height: 100vh; color: #fff; padding: 20px; }
.container { max-width: 1200px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: rgba(255,255,255,0.05); border-radius: 15px; backdrop-filter: blur(10px); margin-bottom: 20px; }
.logo { font-size: 28px; font-weight: bold; background: linear-gradient(45deg, #5865F2, #EB459E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.user-info { display: flex; align-items: center; gap: 10px; }
.user-info img { width: 40px; height: 40px; border-radius: 50%; }
.logout { background: #ed4245; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; }
.servers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.server-card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; backdrop-filter: blur(10px); transition: transform 0.3s; cursor: pointer; border: 1px solid rgba(255,255,255,0.1); }
.server-card:hover { transform: translateY(-5px); border-color: #5865F2; }
.server-icon { width: 60px; height: 60px; border-radius: 50%; margin-bottom: 10px; background: linear-gradient(45deg, #5865F2, #EB459E); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; }
.server-name { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
.server-stat { color: #aaa; font-size: 14px; margin: 4px 0; }
.btn { background: #5865F2; color: white; padding: 10px 20px; border: none; border-radius: 8px; text-decoration: none; display: inline-block; cursor: pointer; margin-top: 10px; }
.btn:hover { background: #4752C4; }
.login-box { text-align: center; padding: 60px 30px; background: rgba(255,255,255,0.05); border-radius: 20px; backdrop-filter: blur(10px); max-width: 500px; margin: 100px auto; }
.login-box h1 { font-size: 48px; margin-bottom: 20px; background: linear-gradient(45deg, #5865F2, #EB459E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.login-box p { color: #aaa; margin-bottom: 30px; }
.discord-btn { background: #5865F2; color: white; padding: 15px 30px; border-radius: 10px; text-decoration: none; font-size: 18px; display: inline-block; }
.stat-card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; text-align: center; }
.stat-number { font-size: 36px; font-weight: bold; color: #5865F2; }
.stat-label { color: #aaa; margin-top: 5px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
.section { background: rgba(255,255,255,0.05); padding: 25px; border-radius: 15px; margin-bottom: 20px; }
.section h2 { margin-bottom: 15px; color: #5865F2; }
.setting-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.setting-row:last-child { border: none; }
.toggle { position: relative; width: 50px; height: 26px; background: #444; border-radius: 13px; cursor: pointer; transition: 0.3s; }
.toggle.on { background: #5865F2; }
.toggle-dot { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; background: white; border-radius: 50%; transition: 0.3s; }
.toggle.on .toggle-dot { left: 27px; }
.back { color: #5865F2; text-decoration: none; margin-bottom: 20px; display: inline-block; }
.warning-list { max-height: 400px; overflow-y: auto; }
.warning-item { background: rgba(255,255,255,0.03); padding: 12px; margin-bottom: 8px; border-radius: 8px; border-left: 4px solid #f0b132; }
</style>
</head>
<body>
<div class="container">
{{ content | safe }}
</div>
</body>
</html>
"""

def render_page(content):
    return render_template_string(DASHBOARD_HTML, content=content)

@app.route("/")
def index():
    if "user" not in session:
        return render_page(f"""
<div class="login-box">
<h1>🛡️ SentinelMod</h1>
<p>The ultimate AI-powered Discord moderation bot</p>
<a href="/login" class="discord-btn">🚀 Login with Discord</a>
</div>
""")
    user = session["user"]
    try:
        headers = {"Authorization": f"Bearer {session['access_token']}"}
        r = requests.get("https://discord.com/api/users/@me/guilds", headers=headers, timeout=10)
        user_guilds = r.json() if r.status_code == 200 else []
    except:
        user_guilds = []
    bot_guild_ids = [g.id for g in bot.guilds]
    managable = []
    for ug in user_guilds:
        try:
            if int(ug.get("permissions", 0)) & 0x8:
                if int(ug["id"]) in bot_guild_ids:
                    managable.append({**ug, "has_bot": True})
                else:
                    managable.append({**ug, "has_bot": False})
        except:
            pass
    cards = ""
    for g in managable[:30]:
        if g["has_bot"]:
            icon = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None
            icon_html = f'<img src="{icon}" style="width:60px;height:60px;border-radius:50%;margin-bottom:10px;">' if icon else f'<div class="server-icon">{g["name"][0]}</div>'
            cards += f"""
<div class="server-card" onclick="window.location='/server/{g['id']}'">
{icon_html}
<div class="server-name">{g['name']}</div>
<div class="server-stat">✅ Bot installed</div>
<a href="/server/{g['id']}" class="btn">Manage →</a>
</div>"""
        else:
            invite = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={g['id']}"
            cards += f"""
<div class="server-card">
<div class="server-icon">{g['name'][0]}</div>
<div class="server-name">{g['name']}</div>
<div class="server-stat">❌ Bot not added</div>
<a href="{invite}" target="_blank" class="btn" style="background:#3ba55c;">+ Add Bot</a>
</div>"""
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user.get("avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    return render_page(f"""
<div class="header">
<div class="logo">🛡️ SentinelMod</div>
<div class="user-info">
<img src="{avatar}">
<span>{user['username']}</span>
<a href="/logout" class="logout">Logout</a>
</div>
</div>
<h2 style="margin-bottom:20px;">Your Servers</h2>
<div class="servers-grid">{cards if cards else '<p>No servers found. Make sure you are an admin in a server!</p>'}</div>
""")

@app.route("/login")
def login():
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")
    data = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return f"Error: {r.text}"
    token = r.json()["access_token"]
    session["access_token"] = token
    ur = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token}"})
    session["user"] = ur.json()
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/server/<guild_id>")
def server_page(guild_id):
    if "user" not in session:
        return redirect("/")
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return "Bot not in this server!"
    s = get_guild_settings(guild_id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (guild_id,))
    warns = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id=?", (guild_id,))
    actions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM custom_commands WHERE guild_id=?", (guild_id,))
    customs = c.fetchone()[0]
    c.execute("SELECT * FROM warnings WHERE guild_id=? ORDER BY timestamp DESC LIMIT 10", (guild_id,))
    recent_warns = c.fetchall()
    conn.close()
    features = [
        ("welcome_enabled", "👋 Welcome Messages"),
        ("anti_nuke_enabled", "💣 Anti-Nuke"),
        ("invite_block", "🚫 Block Invites"),
        ("link_scan", "🔗 Link Scanner"),
        ("slowmode_ai", "🐌 AI Slowmode"),
        ("pre_conflict", "⚠️ Pre-Conflict Detection"),
        ("caps_filter", "🔤 Caps Filter"),
        ("mention_spam", "📢 Mention Spam"),
        ("emoji_spam", "😂 Emoji Spam"),
        ("zalgo_filter", "🌀 Zalgo Filter"),
        ("phone_filter", "📞 Phone Filter"),
        ("email_filter", "📧 Email Filter"),
        ("scam_filter", "💸 Scam Filter"),
        ("fake_nitro_filter", "💎 Fake Nitro Filter"),
        ("token_filter", "🔑 Token Grabber Filter"),
        ("anti_advertisement", "📣 Anti-Advertisement"),
        ("everyone_block", "@everyone Block")
    ]
    feature_html = ""
    for key, name in features:
        val = s.get(key, 0)
        feature_html += f"""
<div class="setting-row">
<span>{name}</span>
<div class="toggle {'on' if val else ''}" onclick="toggleFeature('{key}', this)">
<div class="toggle-dot"></div>
</div>
</div>"""
    warns_html = ""
    for w in recent_warns:
        m = guild.get_member(int(w["user_id"]))
        name = m.display_name if m else f"User {w['user_id']}"
        warns_html += f"""
<div class="warning-item">
<strong>{name}</strong> - {w['severity'].upper()}<br>
<small>{w['reason']} • {w['timestamp'][:16]}</small>
</div>"""
    avatar = f"https://cdn.discordapp.com/avatars/{session['user']['id']}/{session['user']['avatar']}.png" if session['user'].get("avatar") else ""
    return render_page(f"""
<div class="header">
<div class="logo">🛡️ {guild.name}</div>
<div class="user-info">
<img src="{avatar}" style="width:40px;height:40px;border-radius:50%;">
<a href="/logout" class="logout">Logout</a>
</div>
</div>
<a href="/" class="back">← Back to servers</a>
<div class="stats-grid">
<div class="stat-card"><div class="stat-number">{guild.member_count}</div><div class="stat-label">Members</div></div>
<div class="stat-card"><div class="stat-number">{warns}</div><div class="stat-label">Warnings</div></div>
<div class="stat-card"><div class="stat-number">{actions}</div><div class="stat-label">Mod Actions</div></div>
<div class="stat-card"><div class="stat-number">{customs}</div><div class="stat-label">Custom Commands</div></div>
</div>
<div class="section">
<h2>⚙️ Features</h2>
{feature_html}
</div>
<div class="section">
<h2>⚠️ Recent Warnings</h2>
<div class="warning-list">{warns_html if warns_html else '<p>No warnings yet!</p>'}</div>
</div>
<script>
function toggleFeature(key, el) {{
fetch('/api/toggle/{guild_id}/' + key, {{ method: 'POST' }})
.then(r => r.json())
.then(d => {{
if (d.success) el.classList.toggle('on');
}});
}}
</script>
""")

@app.route("/api/toggle/<guild_id>/<feature>", methods=["POST"])
def toggle_feature(guild_id, feature):
    if "user" not in session:
        return jsonify({"success": False})
    valid = ["welcome_enabled","anti_nuke_enabled","invite_block","link_scan","slowmode_ai","pre_conflict","caps_filter","mention_spam","emoji_spam","zalgo_filter","phone_filter","email_filter","scam_filter","fake_nitro_filter","token_filter","anti_advertisement","everyone_block"]
    if feature not in valid:
        return jsonify({"success": False})
    s = get_guild_settings(guild_id)
    new_val = 0 if s.get(feature, 0) else 1
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {feature}=? WHERE guild_id=?", (new_val, guild_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_value": new_val})

def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False)

# ============ RUN ============
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not set!")
    elif not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set!")
    else:
        init_database()
        thread = threading.Thread(target=run_flask)
        thread.daemon = True
        thread.start()
        print(f"🌐 Dashboard on port 8080")
        print("🚀 Starting SentinelMod...")
        bot.run(DISCORD_TOKEN)
