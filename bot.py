# bot.py
# ================================
# SentinelMod - ULTIMATE Edition
# Full Bot + Beautiful Dashboard
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
import secrets
import unicodedata
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, request, redirect, session, render_template_string, jsonify
import requests

# ============ CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
BOT_NAME = "SentinelMod"
AI_CHAT_CHANNEL = "sentinel-bot"
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", secrets.token_hex(32))
MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"

PERSONALITIES = {
    "friendly": "You are extremely friendly, warm, and supportive. Use emojis.",
    "sarcastic": "You are deeply sarcastic and witty.",
    "serious": "You are professional and serious.",
    "chaotic": "You are completely chaotic and random.",
    "pirate": "You are a pirate. Arr matey!",
    "medieval": "You are a medieval knight. Old English.",
    "robot": "You are a robot. Beep boop.",
    "therapist": "You are a caring therapist.",
    "villain": "You are a dramatic villain.",
    "hype": "You are the ultimate hype man. ALL CAPS ENERGY.",
    "philosopher": "You are a deep philosopher.",
    "caveman": "You speak like a caveman. UGH.",
    "shakespeare": "You speak in Shakespearean English.",
    "surfer": "You are a chill surfer dude.",
    "anime": "You speak like an anime character.",
    "cowboy": "You are a cowboy. Yeehaw!",
    "british": "You are extremely British.",
    "australian": "You are extremely Australian. G'day mate!",
    "valley_girl": "You are a valley girl.",
    "gen_z": "You speak Gen Z slang. No cap.",
    "boomer": "You are a stereotypical boomer.",
    "yoda": "Speak like Yoda you must.",
    "jarvis": "You are JARVIS from Iron Man.",
    "deadpool": "You are Deadpool. Break fourth wall.",
    "sherlock": "You are Sherlock Holmes.",
    "gandalf": "You are Gandalf. YOU SHALL NOT PASS.",
    "tony_stark": "You are Tony Stark.",
    "groot": "I am Groot. (translate in parens)",
    "darth_vader": "You are Darth Vader.",
    "michael_scott": "You are Michael Scott.",
    "motivational": "You are extremely motivational!",
    "pessimist": "You are extremely pessimistic.",
    "optimist": "You are blindly optimistic.",
    "ninja": "You are a ninja.",
    "samurai": "You are a samurai.",
    "fairy": "You are a tiny fairy.",
    "vampire": "You are a sophisticated vampire.",
    "oracle": "You speak in prophecies.",
    "wizard": "You are a powerful wizard.",
    "alien": "You are an alien.",
    "ghost": "You are a friendly ghost.",
    "dragon": "You are an ancient dragon.",
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
        """CREATE TABLE IF NOT EXISTS daily_stats (guild_id TEXT, date TEXT, messages INTEGER DEFAULT 0, joins INTEGER DEFAULT 0, leaves INTEGER DEFAULT 0, mod_actions INTEGER DEFAULT 0, PRIMARY KEY (guild_id, date))"""
    ]
    for t in tables:
        c.execute(t)
    conn.commit()
    conn.close()
    print("✅ DB initialized")

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
    today = datetime.now().date().isoformat()
    c.execute("""INSERT INTO daily_stats (guild_id, date, messages) VALUES (?, ?, 1) ON CONFLICT(guild_id, date) DO UPDATE SET messages=messages+1""", (str(gid), today))
    conn.commit()
    conn.close()

# ============ BOT ============
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
        print(f"Groq err: {e}")
    return None

async def ask_groq_json(prompt, system="Respond only in JSON."):
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
        print(f"JSON err: {e}")
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
    last = time.time()
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
                                if time.time() - last > 0.6:
                                    try:
                                        d = full[-1900:] if len(full) > 1900 else full
                                        await sent.edit(content=d + " ▌")
                                        last = time.time()
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
        print(f"Stream err: {e}")
        if full:
            await sent.edit(content=full[:2000])
        else:
            await sent.edit(content="❌ Failed!")

def get_system_prompt(uid, gid, extra=""):
    pkey = get_user_personality(uid, gid)
    personality = PERSONALITIES.get(pkey, PERSONALITIES["default"])
    memory = get_user_memory(uid, gid)
    return f"You are SentinelMod, a Discord bot.\nPersonality: {personality}\n{f'Memory: {memory}' if memory else ''}\n{extra}\nKeep responses under 1500 chars."

async def parse_command(content, guild, author):
    channels = [c.name for c in guild.text_channels][:15]
    roles = [r.name for r in guild.roles if r.name != "@everyone"][:15]
    members = [f"{m.name}(ID:{m.id})" for m in guild.members if not m.bot][:20]
    mids = re.findall(r'<@!?(\d+)>', content)
    mnames = [f"{guild.get_member(int(mid)).name}(ID:{mid})" for mid in mids if guild.get_member(int(mid))]
    prompt = f"""STRICT Discord command parser.
Server: {guild.name}
Channels: {', '.join(channels)}
Roles: {', '.join(roles)}
Members: {', '.join(members)}
Mentioned: {', '.join(mnames) if mnames else 'NONE'}
Sender: {author.name}(ID:{author.id})
Message: "{content}"

CRITICAL: If unclear → chat. Mod actions need mentioned target. Never confuse sender with target. Confidence<0.8→chat.

JSON only:
{{"command":"create_channel|delete_channel|create_role|delete_role|create_category|delete_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|add_role_to_user|remove_role_from_user|start_giveaway|create_poll|set_afk|setup_server|summarize|translate|add_word_filter|remove_word_filter|enable_feature|disable_feature|add_note|get_notes|raid_mode|trivia|wouldyourather|eightball|roast|compliment|dadjoke|ship|rate|fact|truthordare|story|debate|riddle|pickupline|horoscope|remind|confession|rep|server_health|activity_stats|mod_stats|quarantine|unquarantine|add_custom_command|remove_custom_command|help|chat|unknown",
"needs_confirmation":true/false,
"confirmation_message":"text",
"confidence":0.0-1.0,
"params":{{"name":null,"target_user_id":null,"target_user_name":null,"target_user2":null,"reason":null,"duration":null,"category":null,"color":null,"private":false,"amount":null,"prize":null,"winners":null,"question":null,"options":null,"language":null,"text":null,"feature":null,"word":null,"note":null,"channel":null,"response":null,"reminder_time":null,"rating_target":null,"zodiac":null}}}}"""
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

async def do_trivia(message, gid, uid):
    trivia = await ask_groq_json('Generate trivia. JSON: {"question":"q","correct":"a","wrong1":"b","wrong2":"c","wrong3":"d","category":"cat","difficulty":"easy"}')
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
        await message.channel.send(f"⏰ Answer: **{trivia['correct']}**")
        del trivia_sessions[msg.id]
    return None

async def do_fun(ftype, params, author):
    prompts = {
        "wouldyourather": ("Generate Would You Rather.", "🤔 Would You Rather?"),
        "eightball": (f"8ball: '{params.get('question','...')}'. Brief.", "🎱 8-Ball"),
        "roast": (f"Roast {params.get('target_user_name','someone')}. Fun not mean.", "🔥 Roast"),
        "compliment": (f"Compliment {params.get('target_user_name', author.name)}.", "💝 Compliment"),
        "dadjoke": ("Dad joke.", "👨 Joke"),
        "ship": (f"Ship {params.get('target_user_name','x')} + {params.get('target_user2','y')}. % + name.", "💕 Ship"),
        "rate": (f"Rate '{params.get('rating_target','life')}' out of 10.", "⭐ Rate"),
        "fact": ("Random fact.", "🤯 Fact"),
        "truthordare": ("Truth or dare.", "🎯 T or D"),
        "story": (f"Story {('about '+params.get('text','')) if params.get('text') else ''}. 150 words.", "📖 Story"),
        "riddle": ("Riddle with answer.", "🧩 Riddle"),
        "pickupline": ("Pickup line.", "😘 Pickup"),
        "horoscope": (f"Horoscope for {params.get('zodiac','Aries')}.", "⭐ Horoscope"),
    }
    p, title = prompts.get(ftype, ("Joke.", "😄"))
    result = await ask_groq(p, "Fun bot.")
    if result:
        return discord.Embed(title=title, description=result, color=discord.Color.blue())
    return None

async def alert_mods(guild, embed):
    s = get_guild_settings(guild.id)
    ch = discord.utils.get(guild.text_channels, name=s["log_channel"])
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    if ch:
        await ch.send(content=mr.mention if mr else "", embed=embed)

async def execute_command(parsed, message, guild, author):
    cmd = parsed.get("command", "unknown")
    params = parsed.get("params", {})
    s = get_guild_settings(guild.id)
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
            ch = await guild.create_text_channel(name=name, category=cat, overwrites=ow)
            return f"✅ Created {ch.mention}!"
        elif cmd == "delete_channel":
            name = (params.get("name") or "").lower().replace(" ", "-")
            ch = discord.utils.get(guild.text_channels, name=name)
            if not ch:
                return "❌ Not found."
            await ch.delete()
            return f"🗑️ Deleted!"
        elif cmd == "create_role":
            name = params.get("name") or "Role"
            if discord.utils.get(guild.roles, name=name):
                return f"⏭️ Exists!"
            color = discord.Color.default()
            if params.get("color"):
                try:
                    color = discord.Color(int(params["color"].replace("#",""), 16))
                except:
                    pass
            role = await guild.create_role(name=name, color=color)
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
            return f"✅ Created!"
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
            await guild.ban(t, reason=reason)
            log_mod_action(t.id, guild.id, "BAN", reason, author.id)
            add_warning(t.id, guild.id, reason, "critical")
            await alert_mods(guild, discord.Embed(title="🔨 Banned", color=discord.Color.dark_red()).add_field(name="User", value=f"{t}").add_field(name="Reason", value=reason))
            return f"🔨 Banned **{t.name}**!"
        elif cmd == "kick_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found!"
            reason = params.get("reason") or "No reason"
            await guild.kick(t, reason=reason)
            log_mod_action(t.id, guild.id, "KICK", reason, author.id)
            return f"👢 Kicked **{t.name}**!"
        elif cmd == "mute_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found!"
            dur = int(params.get("duration") or 10)
            reason = params.get("reason") or "No reason"
            await t.timeout(datetime.now() + timedelta(minutes=dur), reason=reason)
            log_mod_action(t.id, guild.id, "MUTE", reason, author.id)
            return f"🔇 Muted **{t.name}** {dur}min!"
        elif cmd == "unmute_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            await t.timeout(None)
            return f"🔊 Unmuted!"
        elif cmd == "warn_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found!"
            reason = params.get("reason") or "No reason"
            wc = add_warning(t.id, guild.id, reason, "manual")
            log_mod_action(t.id, guild.id, "WARN", reason, author.id)
            return f"⚠️ Warned **{t.name}** ({wc})"
        elif cmd == "clear_warnings":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            clear_warnings(t.id, guild.id)
            return f"✅ Cleared!"
        elif cmd == "warn_check":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            ws = get_warnings(t.id, guild.id)
            if not ws:
                return f"✅ **{t.name}** clean!"
            return f"**{t.name}** {len(ws)} warns:\n" + "\n".join(f"#{i+1} [{w['severity']}] {w['reason']}" for i, w in enumerate(ws[:5]))
        elif cmd == "lock_channel":
            await message.channel.set_permissions(guild.default_role, send_messages=False)
            return f"🔒 Locked!"
        elif cmd == "unlock_channel":
            await message.channel.set_permissions(guild.default_role, send_messages=None)
            return f"🔓 Unlocked!"
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
            return f"🔓 Unlocked {count}!"
        elif cmd == "slowmode":
            dur = int(params.get("duration") or 5)
            await message.channel.edit(slowmode_delay=dur)
            return f"🐌 {dur}s slowmode!"
        elif cmd == "purge":
            amt = min(int(params.get("amount") or 10), 100)
            d = await message.channel.purge(limit=amt+1)
            return f"🗑️ Deleted {len(d)-1}!"
        elif cmd == "trivia":
            await do_trivia(message, guild.id, author.id)
            return None
        elif cmd == "wouldyourather":
            e = await do_fun("wouldyourather", params, author)
            if e:
                msg = await message.channel.send(embed=e)
                await msg.add_reaction("🅰️")
                await msg.add_reaction("🅱️")
            return None
        elif cmd in ["eightball","roast","compliment","dadjoke","ship","rate","fact","truthordare","story","riddle","pickupline","horoscope"]:
            e = await do_fun(cmd, params, author)
            if e:
                await message.channel.send(embed=e)
            return None
        elif cmd == "debate":
            topic = params.get("text") or "pineapple pizza"
            r = await ask_groq(f"Start debate: {topic}", "Debater.")
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
            text = params.get("text")
            if not text:
                return "❌ What confession?"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO confessions (guild_id, confession, timestamp) VALUES (?, ?, ?)", (str(guild.id), text, datetime.now().isoformat()))
            cid = c.lastrowid
            conn.commit()
            conn.close()
            await message.channel.send(embed=discord.Embed(title=f"🤫 #{cid}", description=text, color=discord.Color.dark_purple()))
            try:
                await message.delete()
            except:
                pass
            return None
        elif cmd == "rep":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ @mention!"
            if t.id == author.id:
                return "❌ Can't rep yourself!"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reputation (user_id, guild_id, rep) VALUES (?, ?, 1) ON CONFLICT(user_id, guild_id) DO UPDATE SET rep=rep+1", (str(t.id), str(guild.id)))
            conn.commit()
            c.execute("SELECT rep FROM reputation WHERE user_id=? AND guild_id=?", (str(t.id), str(guild.id)))
            rep = c.fetchone()[0]
            conn.close()
            return f"✅ +1 to **{t.name}**! Total: **{rep}**"
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
            reason = params.get("reason") or "AFK"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO afk_users (user_id, guild_id, reason, timestamp) VALUES (?, ?, ?, ?)", (str(author.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💤 AFK: **{reason}**"
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
            s = await ask_groq("Summarize bullets:\n" + "\n".join(reversed(msgs)), "Summarizer.")
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
            return f"✅ Removed!"
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
            return f"✅ Added `{trigger}` → {response[:100]}"
        elif cmd == "remove_custom_command":
            trigger = (params.get("name") or params.get("word") or "").lower().strip()
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM custom_commands WHERE guild_id=? AND trigger_word=?", (str(guild.id), trigger))
            conn.commit()
            conn.close()
            return f"✅ Removed!"
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
            await t.add_roles(q)
            return f"🔒 Quarantined **{t.name}**!"
        elif cmd == "unquarantine":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            q = discord.utils.get(guild.roles, name="Quarantined")
            if q and q in t.roles:
                await t.remove_roles(q)
            return f"✅ Unquarantined!"
        elif cmd == "server_health":
            wc = 0
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (str(guild.id),))
            wc = c.fetchone()[0]
            conn.close()
            score = max(0, 100 - (wc // 5))
            embed = discord.Embed(title="🏥 Server Health", color=discord.Color.green() if score > 70 else discord.Color.orange())
            embed.add_field(name="Score", value=f"{score}/100")
            embed.add_field(name="Members", value=str(guild.member_count))
            embed.add_field(name="Warnings", value=str(wc))
            await message.channel.send(embed=embed)
            return None
        elif cmd == "activity_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 10", (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "📊 No data!"
            lines = []
            medals = ["🥇","🥈","🥉"]
            for i, r in enumerate(top):
                m = guild.get_member(int(r["user_id"]))
                medal = medals[i] if i < 3 else f"#{i+1}"
                lines.append(f"{medal} {m.display_name if m else '?'}: **{r['message_count']}**")
            await message.channel.send(embed=discord.Embed(title="📊 Activity", description="\n".join(lines)))
            return None
        elif cmd == "help":
            embed = discord.Embed(title="🛡️ SentinelMod Help", color=discord.Color.blue())
            embed.add_field(name="💬 Chat", value=f"@mention me or chat in #sentinel-bot", inline=False)
            embed.add_field(name="🔨 Mod", value="ban, kick, mute, warn, purge, lock", inline=False)
            embed.add_field(name="🎮 Fun", value="trivia, roast, 8ball, ship, story", inline=False)
            embed.add_field(name="🌐 Dashboard", value=f"{REDIRECT_URI.replace('/callback','')}", inline=False)
            await message.channel.send(embed=embed)
            return None
        else:
            return None
    except discord.Forbidden:
        return "❌ No permission!"
    except Exception as e:
        print(f"Err: {e}")
        return f"❌ {str(e)[:100]}"

async def check_spam(msg, s):
    key = f"{msg.author.id}:{msg.guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    w = s.get("spam_window", 5)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < w]
    return len(spam_tracker[key]) >= s.get("spam_limit", 5)

async def handle_spam(msg, s):
    try:
        await msg.channel.purge(limit=10, check=lambda m: m.author == msg.author)
    except:
        pass
    try:
        await msg.author.timeout(datetime.now() + timedelta(minutes=s.get("mute_duration",10)), reason="Spam")
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
            await ch.send(content=f"🚨 {mr.mention if mr else ''}", embed=discord.Embed(title="🚨 RAID", color=discord.Color.red()))
        await asyncio.sleep(300)
        raid_mode_active[guild.id] = False
    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    if age < s.get("min_account_age", 7):
        try:
            await member.kick(reason="Raid protection")
        except:
            pass

async def check_patterns(msg, s):
    content = msg.content
    cl = content.lower()
    if s.get("phone_filter",1) and re.search(r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b', content):
        return "phone", "Phone number", "high"
    if s.get("email_filter",1) and re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
        return "email", "Email", "high"
    keywords = [
        (s.get("fake_nitro_filter",1), ["free nitro","claim nitro"], "fake_nitro", "Nitro scam", "critical"),
        (s.get("token_filter",1), ["discord token","grabify"], "token", "Token grab", "critical"),
        (s.get("scam_filter",1), ["you won","claim your prize"], "scam", "Scam", "critical"),
        (1, ["want to kill myself","want to die"], "self_harm", "Self-harm", "high"),
        (1, ["death to all","kill all"], "extremism", "Extremism", "critical"),
    ]
    for en, words, t, r, sev in keywords:
        if en and any(w in cl for w in words):
            return t, r, sev
    if s.get("caps_filter",1) and len(content) > 10:
        if sum(1 for c in content if c.isupper())/len(content) > 0.7:
            return "caps", "Caps", "low"
    if s.get("mention_spam",1) and len(msg.mentions) >= 5:
        return "mentions", "Mention spam", "high"
    if s.get("invite_block",0) and re.search(r'(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', content):
        return "invite", "Invite", "medium"
    if s.get("link_scan",1) and "http" in cl:
        bad = ["grabify","iplogger","discord.gift","free-nitro","phish"]
        for b in bad:
            if b in cl:
                return "phishing", f"Phishing", "critical"
    return None, None, None

async def check_toxicity(content, context=""):
    return await ask_groq_json(f'Analyze: "{content}" Context: {context}\nJSON: {{"toxic":true/false,"severity":"none|low|medium|high|critical","confidence":0.0-1.0,"reason":"brief"}}')

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
        await u.send(f"⚠️ Removed in **{g.name}**: {reason}")
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
    await alert_mods(g, discord.Embed(title="🚨 AI Mod", color=discord.Color.red()).add_field(name="User", value=u.mention).add_field(name="Reason", value=reason).add_field(name="Warnings", value=str(wc)))

async def setup_server(guild):
    results = []
    s = get_guild_settings(guild.id)
    for rn, c, h in [(s["mod_role_name"], discord.Color.red(), True), ("Muted", discord.Color.dark_gray(), False), ("Quarantined", discord.Color.dark_gray(), False)]:
        if not discord.utils.get(guild.roles, name=rn):
            try:
                await guild.create_role(name=rn, color=c, hoist=h)
                results.append(f"✅ {rn}")
            except:
                pass
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    scat = discord.utils.get(guild.categories, name="🛡️ SENTINELAI")
    if not scat:
        try:
            ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True)}
            if mr:
                ow[mr] = discord.PermissionOverwrite(read_messages=True)
            scat = await guild.create_category(name="🛡️ SENTINELAI", overwrites=ow)
            results.append("✅ Category")
        except:
            pass
    for cn in [s["log_channel"], s["raid_channel"], "sentinel-bot"]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, category=scat)
                results.append(f"✅ #{cn}")
            except:
                pass
    for cn in ["welcome","rules","general","announcements"]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn)
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

@bot.tree.command(name="dashboard", description="Get dashboard link")
async def dashboard_cmd(interaction: discord.Interaction):
    url = REDIRECT_URI.replace('/callback', '')
    await interaction.response.send_message(embed=discord.Embed(title="🌐 Dashboard", description=f"**{url}**", color=discord.Color.blue()), ephemeral=True)

@bot.tree.command(name="personality", description="Choose personality")
async def personality_cmd(interaction: discord.Interaction):
    opts = [discord.SelectOption(label=n.replace("_"," ").title(), value=n) for n in list(PERSONALITIES.keys())[:25]]
    view = discord.ui.View(timeout=60)
    select = discord.ui.Select(placeholder="Choose...", options=opts)
    async def cb(i):
        p = i.data["values"][0]
        set_user_personality(str(i.user.id), str(i.guild.id), p)
        await i.response.send_message(f"✅ **{p}**!", ephemeral=True)
    select.callback = cb
    view.add_item(select)
    await interaction.response.send_message(embed=discord.Embed(title="🎭 Personality", description="Pick one!", color=discord.Color.purple()), view=view, ephemeral=True)

@bot.tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ SentinelMod", color=discord.Color.blue())
    embed.add_field(name="💬", value="@mention me or chat in #sentinel-bot")
    embed.add_field(name="🌐 Dashboard", value=REDIRECT_URI.replace('/callback', ''), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
                await ch.send(f"🎉 {m}!", embed=discord.Embed(title="🎉 Ended!", description=f"**{g['prize']}**\nWinners: {m}", color=discord.Color.gold()))
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
                await ch.send(f"⏰ <@{rem['user_id']}> Reminder: **{rem['reminder']}**")
        except:
            pass
        c.execute("UPDATE reminders SET active=0 WHERE id=?", (rem["id"],))
    conn.commit()
    conn.close()

@tasks.loop(hours=24)
async def daily_server_stats():
    """Post daily stats to each server"""
    for guild in bot.guilds:
        try:
            settings = get_guild_settings(guild.id)
            ch = discord.utils.get(guild.text_channels, name=settings.get("log_channel", "sentinel-logs"))
            if not ch:
                continue
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT messages, joins, leaves, mod_actions FROM daily_stats WHERE guild_id=? AND date=?", (str(guild.id), yesterday))
            stats = c.fetchone()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND timestamp >= ?", (str(guild.id), yesterday + "T00:00:00"))
            warns_today = c.fetchone()[0]
            conn.close()
            messages = stats[0] if stats else 0
            joins = stats[1] if stats else 0
            leaves = stats[2] if stats else 0
            mod_actions = stats[3] if stats else 0
            embed = discord.Embed(title="📊 Daily Server Report", description=f"Stats for **{yesterday}**", color=discord.Color.blue(), timestamp=datetime.now())
            embed.add_field(name="💬 Messages", value=f"{messages:,}", inline=True)
            embed.add_field(name="📥 Joined", value=str(joins), inline=True)
            embed.add_field(name="📤 Left", value=str(leaves), inline=True)
            embed.add_field(name="🔨 Mod Actions", value=str(mod_actions), inline=True)
            embed.add_field(name="⚠️ Warnings", value=str(warns_today), inline=True)
            embed.add_field(name="👥 Members", value=str(guild.member_count), inline=True)
            embed.set_footer(text=f"SentinelMod Daily Report")
            await ch.send(embed=embed)
        except Exception as e:
            print(f"Daily stats err: {e}")

@bot.event
async def on_ready():
    print(f"🤖 {bot.user} ONLINE in {len(bot.guilds)} servers")
    for g in bot.guilds:
        init_guild_settings(g.id)
    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} commands synced")
    except Exception as e:
        print(f"Sync err: {e}")
    check_giveaways.start()
    check_reminders.start()
    daily_server_stats.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="everything 👁️"))

@bot.event
async def on_guild_join(guild):
    init_guild_settings(guild.id)
    await setup_server(guild)

@bot.event
async def on_member_join(member):
    g = member.guild
    s = get_guild_settings(g.id)
    today = datetime.now().date().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO daily_stats (guild_id, date, joins) VALUES (?, ?, 1) ON CONFLICT(guild_id, date) DO UPDATE SET joins=joins+1", (str(g.id), today))
    conn.commit()
    conn.close()
    if await check_raid(member):
        await handle_raid(g, member)
        return
    if s.get("welcome_enabled", 1):
        wch = discord.utils.get(g.text_channels, name=s.get("welcome_channel","welcome"))
        if wch:
            w = await ask_groq(f"Welcome {member.display_name} to {g.name}. 2 sentences.", "Friendly.")
            if w:
                embed = discord.Embed(title=f"👋 Welcome!", description=w, color=discord.Color.green())
                embed.set_thumbnail(url=member.display_avatar.url)
                await wch.send(content=member.mention, embed=embed)

@bot.event
async def on_member_remove(member):
    today = datetime.now().date().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO daily_stats (guild_id, date, leaves) VALUES (?, ?, 1) ON CONFLICT(guild_id, date) DO UPDATE SET leaves=leaves+1", (str(member.guild.id), today))
    conn.commit()
    conn.close()

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
            await reaction.message.channel.send(f"✅ {user.mention} correct!")
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
            await message.channel.send(f"👋 Welcome back!", delete_after=5)
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
                        embed = discord.Embed(title=f"⚠️ Confirm", description=parsed.get("confirmation_message","Confirm?"), color=discord.Color.orange())
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
                await message.channel.send(embed=discord.Embed(title="💙 We're Here", description=f"{message.author.mention}\n**988** Suicide Prevention", color=discord.Color.blue()))
            except:
                pass
        wc = add_warning(message.author.id, message.guild.id, pr, ps)
        today = datetime.now().date().isoformat()
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO daily_stats (guild_id, date, mod_actions) VALUES (?, ?, 1) ON CONFLICT(guild_id, date) DO UPDATE SET mod_actions=mod_actions+1", (str(message.guild.id), today))
        conn.commit()
        conn.close()
        if ps in ["high","critical"]:
            await alert_mods(message.guild, discord.Embed(title=f"🚨 {pt}", color=discord.Color.red()).add_field(name="User", value=message.author.mention).add_field(name="Reason", value=pr))
        if ps == "critical":
            try:
                await message.guild.ban(message.author, reason=f"IMMEDIATE: {pr}")
            except:
                pass
        return
    words = get_filtered_words(message.guild.id)
    cl = message.content.lower()
    for w in words:
        if w in cl:
            try:
                await message.delete()
            except:
                pass
            add_warning(message.author.id, message.guild.id, "Filtered", "medium")
            await message.channel.send(f"⚠️ {message.author.mention} Word not allowed!", delete_after=5)
            return
    if len(message.content) < 3:
        await bot.process_commands(message)
        return
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

CSS = """<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter','gg sans',sans-serif}
:root{--bg1:#313338;--bg2:#2b2d31;--bg3:#1e1f22;--bg4:#111214;--text:#dbdee1;--muted:#949ba4;--head:#f2f3f5;--brand:#5865f2;--brand2:#4752c4;--green:#23a559;--red:#f23f43;--yellow:#f0b232;--border:rgba(255,255,255,0.06)}
body{background:var(--bg3);color:var(--text);min-height:100vh}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--bg3);border-radius:4px}
a{color:inherit;text-decoration:none}
.app{display:flex;min-height:100vh}
.sb{width:260px;background:var(--bg2);position:fixed;height:100vh;border-right:1px solid var(--border);display:flex;flex-direction:column;z-index:100}
.sb-h{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;height:50px}
.sb-l{width:32px;height:32px;background:linear-gradient(135deg,#5865f2,#7289da);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px}
.sb-t{font-weight:700;font-size:15px;color:var(--head)}
.sb-n{flex:1;overflow-y:auto;padding:10px 8px}
.sb-st{font-size:11px;font-weight:700;text-transform:uppercase;color:var(--muted);padding:0 10px;margin:12px 0 6px}
.sb-i{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:4px;color:var(--muted);cursor:pointer;font-size:14px;font-weight:500;margin:1px 0;transition:all 0.15s}
.sb-i:hover{background:rgba(255,255,255,0.04);color:var(--text)}
.sb-i.active{background:rgba(88,101,242,0.15);color:#fff}
.sb-ic{font-size:18px;width:24px;text-align:center}
.sb-f{padding:10px 12px;border-top:1px solid var(--border);background:var(--bg3);display:flex;align-items:center;gap:10px}
.sb-av{width:32px;height:32px;border-radius:50%;border:2px solid var(--brand)}
.sb-u{flex:1;overflow:hidden}
.sb-un{font-size:13px;font-weight:600;color:var(--head);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb-ss{font-size:11px;color:var(--green)}
.sb-lo{color:var(--muted);cursor:pointer;font-size:18px;padding:4px}.sb-lo:hover{color:var(--red)}
.main{flex:1;margin-left:260px}
.tb{height:50px;background:var(--bg1);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;position:sticky;top:0;z-index:50}
.cb{font-size:14px;color:var(--muted)}.cb b{color:var(--head)}
.ct{padding:24px;max-width:1400px}
.sg{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:24px}
.sc{background:var(--bg1);padding:20px;border-radius:8px;border:1px solid var(--border);transition:all 0.2s}
.sc:hover{border-color:rgba(255,255,255,0.12)}
.si{width:44px;height:44px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:12px}
.si-b{background:rgba(88,101,242,0.1);color:var(--brand)}
.si-g{background:rgba(35,165,89,0.1);color:var(--green)}
.si-r{background:rgba(242,63,67,0.1);color:var(--red)}
.si-y{background:rgba(240,178,50,0.1);color:var(--yellow)}
.sv{font-size:28px;font-weight:800;color:var(--head);line-height:1}
.sl{font-size:12px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}
.pn{background:var(--bg1);border-radius:8px;border:1px solid var(--border);margin-bottom:16px;overflow:hidden}
.ph{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.pt{font-size:13px;font-weight:700;color:var(--head);text-transform:uppercase;letter-spacing:0.5px}
.pb{padding:20px}
.bt{padding:8px 16px;border-radius:4px;border:none;cursor:pointer;font-weight:600;font-size:13px;transition:all 0.15s;display:inline-flex;align-items:center;gap:6px;font-family:inherit}
.bt-s{padding:5px 12px;font-size:12px}
.bt-b{background:var(--brand);color:#fff}.bt-b:hover{background:var(--brand2)}
.bt-g{background:var(--green);color:#fff}
.bt-r{background:var(--red);color:#fff}.bt-r:hover{background:#c93538}
.bt-gh{background:transparent;color:var(--muted);border:1px solid var(--border)}.bt-gh:hover{color:var(--text)}
.fg{margin-bottom:16px}
.fl{display:block;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#b5bac1;margin-bottom:8px}
.fi,.fs,.fx{width:100%;padding:10px 12px;background:var(--bg3);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:14px;font-family:inherit}
.fi:focus,.fs:focus,.fx:focus{outline:none;border-color:var(--brand)}
.fx{resize:vertical;min-height:100px}
.fr{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.fh{font-size:11px;color:var(--muted);margin-top:4px}
.fg2{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px}
.ft{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:var(--bg2);border-radius:6px;transition:all 0.15s;border:1px solid transparent}
.ft:hover{background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.12)}
.fti{display:flex;align-items:center;gap:12px}
.ftic{font-size:20px;width:32px;text-align:center}
.ftn{font-size:14px;font-weight:600;color:var(--text)}
.ftd{font-size:11px;color:var(--muted);margin-top:2px}
.sw{position:relative;width:42px;height:24px;background:#72767d;border-radius:12px;cursor:pointer;transition:0.2s;flex-shrink:0}
.sw.on{background:var(--green)}
.swd{position:absolute;top:3px;left:3px;width:18px;height:18px;background:#fff;border-radius:50%;transition:0.2s}
.sw.on .swd{left:21px}
.row{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:6px;transition:background 0.15s;margin-bottom:4px}
.row:hover{background:rgba(255,255,255,0.03)}
.rav{width:36px;height:36px;border-radius:50%;background:var(--brand);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;overflow:hidden;flex-shrink:0;color:#fff}
.rav img{width:100%;height:100%;object-fit:cover}
.rin{flex:1;min-width:0}
.rn{font-size:14px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rd{font-size:12px;color:var(--muted);margin-top:1px}
.rm{font-size:11px;color:#6d6f78}
.tg{padding:2px 8px;border-radius:50px;font-size:10px;font-weight:700;text-transform:uppercase}
.tg-l{background:rgba(240,178,50,0.15);color:var(--yellow)}
.tg-m{background:rgba(230,126,34,0.15);color:#e67e22}
.tg-h{background:rgba(242,63,67,0.15);color:var(--red)}
.tg-c{background:rgba(150,0,0,0.2);color:#ff6b6b}
.tbs{display:flex;gap:2px;padding:4px;background:var(--bg3);border-radius:8px;margin-bottom:20px;overflow-x:auto}
.tab{padding:8px 16px;border:none;background:transparent;color:var(--muted);cursor:pointer;border-radius:4px;font-size:13px;font-weight:600;font-family:inherit;white-space:nowrap}
.tab.active{background:var(--bg1);color:#fff}
.tab:hover:not(.active){color:var(--text)}
.pc{display:none}
.pc.active{display:block}
.cmd{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:var(--bg2);border-radius:6px;margin-bottom:6px;gap:12px}
.cmt{font-family:'Consolas',monospace;background:rgba(88,101,242,0.15);color:var(--brand);padding:3px 8px;border-radius:4px;font-size:13px}
.cmr{color:var(--muted);font-size:13px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.em{text-align:center;padding:48px 20px}
.emi{font-size:48px;margin-bottom:12px;opacity:0.3}
.emt{font-size:16px;font-weight:600;color:var(--head);margin-bottom:4px}
.emd{font-size:13px;color:var(--muted)}
.ts{position:fixed;top:20px;right:20px;padding:14px 20px;background:var(--bg4);color:#fff;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.5);z-index:9999;display:none;font-size:14px;border-left:4px solid var(--brand);max-width:350px;font-weight:500}
.ts.show{display:block}
.ts.success{border-left-color:var(--green)}
.ts.error{border-left-color:var(--red)}
.lp{min-height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(ellipse at top,#1a1b3e 0%,var(--bg3) 50%)}
.lc{background:var(--bg1);padding:40px;border-radius:16px;border:1px solid var(--border);max-width:480px;width:90%;text-align:center}
.ll{font-size:72px;margin-bottom:16px}
.lt{font-size:32px;font-weight:900;background:linear-gradient(135deg,#5865f2,#eb459e);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.lst{font-size:15px;color:var(--muted);margin-bottom:32px}
.lb{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:14px;background:var(--brand);color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;font-family:inherit}
.lb:hover{background:var(--brand2)}
.srvs{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.srv{background:var(--bg1);padding:20px;border-radius:8px;border:1px solid var(--border);transition:all 0.2s}
.srv:hover{border-color:var(--brand)}
.srvh{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.srvi{width:56px;height:56px;border-radius:16px;background:linear-gradient(135deg,#5865f2,#eb459e);display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:800;overflow:hidden;color:#fff}
.srvi img{width:100%;height:100%}
.srvn{font-size:16px;font-weight:700;color:var(--head)}
.srvf{font-size:12px;color:var(--muted);margin-top:2px}
.mg{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px;max-height:600px;overflow-y:auto}
.mc{display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg2);border-radius:6px;border:1px solid transparent;transition:0.15s}
.mc:hover{border-color:rgba(255,255,255,0.12)}
.mav{width:36px;height:36px;border-radius:50%;background:var(--brand);overflow:hidden;flex-shrink:0;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}
.mav img{width:100%;height:100%}
.mi{flex:1;min-width:0}
.mn{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mm{font-size:11px;color:var(--muted)}
.cil{max-height:400px;overflow-y:auto}
.ci{display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--bg2);border-radius:6px;margin-bottom:4px}
.ci:hover{background:rgba(255,255,255,0.04)}
.cic{font-size:16px;color:var(--muted)}
.cnm{flex:1;font-size:13px;color:var(--text)}
.cnc{font-size:11px;color:#6d6f78}
.sw-wr{position:relative;margin-bottom:16px}
.swi{width:100%;padding:10px 16px 10px 40px;background:var(--bg2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:14px;font-family:inherit}
.swic{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--muted)}
@media(max-width:768px){.sb{width:60px}.sb-t,.sb-un,.sb-ss,.sb-i span,.sb-st,.sb-u{display:none}.main{margin-left:60px}.sg{grid-template-columns:repeat(2,1fr)}.fr{grid-template-columns:1fr}.fg2{grid-template-columns:1fr}.mg{grid-template-columns:1fr}}
</style>"""

JS = """<script>
function t(m,tp){const e=document.getElementById('ts');e.textContent=m;e.className='ts show '+(tp||'');setTimeout(()=>e.classList.remove('show'),3000)}
function sw(n,e){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.pc').forEach(x=>x.classList.remove('active'));e.classList.add('active');document.getElementById('tp-'+n).classList.add('active')}
function tg(g,k,e){fetch('/api/toggle/'+g+'/'+k,{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success){e.classList.toggle('on');t('✅ Updated!','success')}else t('❌ Failed','error')})}
function us(g,k,v){fetch('/api/setting/'+g+'/'+k,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:v})}).then(r=>r.json()).then(d=>{if(d.success)t('✅ Saved!','success')})}
function ac(g){const tr=document.getElementById('cct').value;const rs=document.getElementById('ccr').value;if(!tr||!rs){t('Fill both!','error');return}fetch('/api/custom/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({trigger:tr,response:rs})}).then(r=>r.json()).then(d=>{if(d.success){t('✅ Added!','success');setTimeout(()=>location.reload(),500)}})}
function dc(g,tr){if(!confirm('Delete?'))return;fetch('/api/custom/'+g+'/'+encodeURIComponent(tr),{method:'DELETE'}).then(r=>r.json()).then(d=>{if(d.success){t('Deleted!','success');setTimeout(()=>location.reload(),500)}})}
function aw(g){const w=document.getElementById('wfw').value;if(!w)return;fetch('/api/word/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({word:w})}).then(r=>r.json()).then(d=>{if(d.success){t('Added!','success');setTimeout(()=>location.reload(),500)}})}
function dw(g,w){fetch('/api/word/'+g+'/'+encodeURIComponent(w),{method:'DELETE'}).then(r=>r.json()).then(d=>{if(d.success){t('Removed!','success');setTimeout(()=>location.reload(),500)}})}
function cw(g,u){if(!confirm('Clear?'))return;fetch('/api/clearwarns/'+g+'/'+u,{method:'POST'}).then(r=>r.json()).then(d=>{if(d.success){t('Cleared!','success');setTimeout(()=>location.reload(),500)}})}
function sa(g){const c=document.getElementById('anc').value;const m=document.getElementById('anm').value;const tt=document.getElementById('ant').value;if(!c||!m){t('Fill!','error');return}fetch('/api/announce/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel:c,message:m,title:tt})}).then(r=>r.json()).then(d=>{if(d.success){t('📤 Sent!','success');document.getElementById('anm').value='';document.getElementById('ant').value=''}else t('❌ '+(d.error||'Failed'),'error')})}
function sd(g){const u=document.getElementById('dmu').value;const m=document.getElementById('dmm').value;if(!u||!m){t('Fill!','error');return}fetch('/api/dm/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:u,message:m})}).then(r=>r.json()).then(d=>{if(d.success){t('📨 Sent!','success');document.getElementById('dmm').value=''}else t('❌ '+(d.error||'Failed'),'error')})}
function cc(g){const n=document.getElementById('chn').value;const c=document.getElementById('chc').value;if(!n)return;fetch('/api/channel/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,category:c})}).then(r=>r.json()).then(d=>{if(d.success){t('✅ Created!','success');setTimeout(()=>location.reload(),500)}})}
function dch(g,n){if(!confirm('Delete?'))return;fetch('/api/channel/'+g+'/'+encodeURIComponent(n),{method:'DELETE'}).then(r=>r.json()).then(d=>{if(d.success){t('Deleted!','success');setTimeout(()=>location.reload(),500)}})}
function cr(g){const n=document.getElementById('rln').value;const c=document.getElementById('rlc').value;if(!n)return;fetch('/api/role/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,color:c})}).then(r=>r.json()).then(d=>{if(d.success){t('✅ Created!','success');setTimeout(()=>location.reload(),500)}})}
function dr(g,n){if(!confirm('Delete?'))return;fetch('/api/role/'+g+'/'+encodeURIComponent(n),{method:'DELETE'}).then(r=>r.json()).then(d=>{if(d.success){t('Deleted!','success');setTimeout(()=>location.reload(),500)}})}
function cat(g){const n=document.getElementById('ctn').value;if(!n)return;fetch('/api/category/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})}).then(r=>r.json()).then(d=>{if(d.success){t('✅ Created!','success');setTimeout(()=>location.reload(),500)}})}
function ua(g,u,a){const r=prompt('Reason:');if(!r)return;const d=a==='mute'?prompt('Minutes:','10'):null;fetch('/api/useraction/'+g+'/'+u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:a,reason:r,duration:d})}).then(x=>x.json()).then(x=>{if(x.success){t('✅ Done!','success');setTimeout(()=>location.reload(),500)}else t('❌ '+(x.error||'Failed'),'error')})}
function gw(g){const p=document.getElementById('gwp').value;const c=document.getElementById('gwc').value;const d=document.getElementById('gwd').value;const w=document.getElementById('gww').value;if(!p||!c){t('Fill!','error');return}fetch('/api/giveaway/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prize:p,channel:c,duration:d,winners:w})}).then(r=>r.json()).then(d=>{if(d.success){t('🎉 Started!','success')}})}
function po(g){const q=document.getElementById('plq').value;const c=document.getElementById('plc').value;const o=document.getElementById('plo').value;if(!q||!c||!o){t('Fill all!','error');return}fetch('/api/poll/'+g,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,channel:c,options:o.split(',')})}).then(r=>r.json()).then(d=>{if(d.success){t('📊 Posted!','success')}})}
function ms(){const q=document.getElementById('msr').value.toLowerCase();document.querySelectorAll('.mc').forEach(c=>{c.style.display=c.dataset.name.toLowerCase().includes(q)?'flex':'none'})}
</script>"""

def page(content, title="Dashboard"):
    return f"""<!DOCTYPE html><html><head><title>{title} - SentinelMod</title>{CSS}</head><body>
<div id="ts" class="ts"></div>{content}{JS}</body></html>"""

def sidebar_h(user, active="home", gid=None):
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png"
    nav = ""
    if gid:
        items = [("overview","📊","Overview"),("features","⚙️","Features"),("moderation","🛡️","Moderation"),("members","👥","Members"),("channels","💬","Channels"),("roles","🎭","Roles"),("warnings","⚠️","Warnings"),("commands","⚡","Commands"),("filters","🔤","Filters"),("analytics","📈","Analytics"),("leaderboard","🏆","Leaderboard"),("events","🎉","Events"),("announce","📢","Announce"),("settings","🔧","Settings")]
        for k, i, l in items:
            ac = "active" if active == k else ""
            nav += f'<a class="sb-i {ac}" onclick="document.querySelector(\'.tab[data-t=\\'{k}\\']\').click()"><span class="sb-ic">{i}</span><span>{l}</span></a>'
    return f"""<aside class="sb">
<div class="sb-h"><div class="sb-l">🛡️</div><div class="sb-t">SentinelMod</div></div>
<div class="sb-n">
<div><div class="sb-st">Main</div><a href="/" class="sb-i {'active' if active=='home' else ''}"><span class="sb-ic">🏠</span><span>Home</span></a></div>
{f'<div><div class="sb-st">Server</div>{nav}</div>' if gid else ''}
</div>
<div class="sb-f"><img src="{avatar}" class="sb-av"><div class="sb-u"><div class="sb-un">{user['username']}</div><div class="sb-ss">● Online</div></div><a href="/logout" class="sb-lo">⏻</a></div>
</aside>"""

@app.route("/")
def index():
    if "user" not in session:
        return page("""<div class="lp"><div class="lc">
<div class="ll">🛡️</div>
<div class="lt">SentinelMod</div>
<div class="lst">The ultimate AI-powered Discord moderation dashboard</div>
<a href="/login" class="lb">🚀 Login with Discord</a>
</div></div>""", "Login")
    user = session["user"]
    try:
        h = {"Authorization": f"Bearer {session['access_token']}"}
        r = requests.get("https://discord.com/api/users/@me/guilds", headers=h, timeout=10)
        ug = r.json() if r.status_code == 200 else []
    except:
        ug = []
    bg = [g.id for g in bot.guilds]
    mg = [{**g, "has_bot": int(g["id"]) in bg} for g in ug if int(g.get("permissions", 0)) & 0x8]
    cards = ""
    for g in mg[:50]:
        iu = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None
        ih = f'<img src="{iu}">' if iu else g['name'][0].upper()
        mc = 0
        if g["has_bot"]:
            go = bot.get_guild(int(g['id']))
            if go:
                mc = go.member_count
        if g["has_bot"]:
            cards += f'<div class="srv"><div class="srvh"><div class="srvi">{ih}</div><div><div class="srvn">{g["name"]}</div><div class="srvf">{mc} members</div></div></div><a href="/server/{g["id"]}" class="bt bt-b" style="width:100%;justify-content:center;">⚙️ Manage</a></div>'
        else:
            inv = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={g['id']}"
            cards += f'<div class="srv"><div class="srvh"><div class="srvi">{ih}</div><div><div class="srvn">{g["name"]}</div><div class="srvf">Not added</div></div></div><a href="{inv}" target="_blank" class="bt bt-g" style="width:100%;justify-content:center;">➕ Add Bot</a></div>'
    ts = len([m for m in mg if m["has_bot"]])
    tm = sum(bot.get_guild(int(m["id"])).member_count for m in mg if m["has_bot"] and bot.get_guild(int(m["id"])))
    return page(f"""<div class="app">{sidebar_h(user,"home")}<div class="main"><div class="tb"><div class="cb"><b>🏠 Home</b></div></div><div class="ct">
<h1 style="font-size:24px;font-weight:800;color:var(--head);margin-bottom:4px;">Welcome, {user['username']}!</h1>
<p style="color:var(--muted);margin-bottom:24px;">Managing {ts} server(s)</p>
<div class="sg">
<div class="sc"><div class="si si-b">🏠</div><div class="sv">{ts}</div><div class="sl">Active Servers</div></div>
<div class="sc"><div class="si si-g">👥</div><div class="sv">{tm:,}</div><div class="sl">Total Members</div></div>
<div class="sc"><div class="si si-y">⚙️</div><div class="sv">{len(mg)}</div><div class="sl">Manageable</div></div>
<div class="sc"><div class="si si-r">🤖</div><div class="sv">99%</div><div class="sl">Uptime</div></div>
</div>
<div class="pn"><div class="ph"><div class="pt">Your Servers</div></div><div class="pb"><div class="srvs">{cards if cards else '<div class="em"><div class="emi">🔍</div><div class="emt">No servers</div><div class="emd">Need admin permissions</div></div>'}</div></div></div>
</div></div></div>""", "Home")

@app.route("/login")
def login():
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")
    d = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
    r = requests.post("https://discord.com/api/oauth2/token", data=d, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return f"Error: {r.text}"
    tok = r.json()["access_token"]
    session["access_token"] = tok
    ur = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {tok}"})
    session["user"] = ur.json()
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/server/<gid>")
def server_page(gid):
    if "user" not in session:
        return redirect("/")
    guild = bot.get_guild(int(gid))
    if not guild:
        return "Bot not in server!"
    s = get_guild_settings(gid)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (gid,))
    wc = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id=?", (gid,))
    ac_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM custom_commands WHERE guild_id=?", (gid,))
    cc_count = c.fetchone()[0]
    c.execute("SELECT * FROM warnings WHERE guild_id=? ORDER BY timestamp DESC LIMIT 30", (gid,))
    warns = c.fetchall()
    c.execute("SELECT * FROM mod_actions WHERE guild_id=? ORDER BY timestamp DESC LIMIT 30", (gid,))
    actions = c.fetchall()
    c.execute("SELECT * FROM custom_commands WHERE guild_id=?", (gid,))
    customs = c.fetchall()
    c.execute("SELECT word FROM word_filters WHERE guild_id=?", (gid,))
    words = c.fetchall()
    c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 20", (gid,))
    top_users = c.fetchall()
    try:
        c.execute("SELECT user_id, rep FROM reputation WHERE guild_id=? ORDER BY rep DESC LIMIT 10", (gid,))
        top_rep = c.fetchall()
    except:
        top_rep = []
    try:
        c.execute("SELECT * FROM giveaways WHERE guild_id=? AND active=1", (gid,))
        gws = c.fetchall()
    except:
        gws = []
    try:
        c.execute("SELECT * FROM daily_stats WHERE guild_id=? ORDER BY date DESC LIMIT 7", (gid,))
        daily = c.fetchall()
    except:
        daily = []
    conn.close()

    features = [
        ("welcome_enabled","👋","Welcome Messages","Greet new members"),
        ("anti_nuke_enabled","💣","Anti-Nuke","Stop mass destruction"),
        ("invite_block","🚫","Block Invites","Block discord.gg"),
        ("link_scan","🔗","Link Scanner","Detect phishing"),
        ("slowmode_ai","🐌","AI Slowmode","Auto slow chats"),
        ("pre_conflict","⚠️","Pre-Conflict AI","Detect arguments"),
        ("caps_filter","🔤","Caps Filter","Block caps"),
        ("mention_spam","📢","Mention Spam","Block mass mentions"),
        ("emoji_spam","😂","Emoji Spam","Block emoji floods"),
        ("zalgo_filter","🌀","Zalgo Filter","Block weird text"),
        ("phone_filter","📞","Phone Filter","Block phone numbers"),
        ("email_filter","📧","Email Filter","Block emails"),
        ("scam_filter","💸","Scam Filter","Detect scams"),
        ("fake_nitro_filter","💎","Fake Nitro","Block nitro scams"),
        ("token_filter","🔑","Token Grabber","Block grabbers"),
        ("anti_advertisement","📣","Anti-Ads","Block ads"),
        ("everyone_block","🔕","@everyone Block","Block @everyone"),
        ("nsfw_text_filter","🔞","NSFW Filter","Block NSFW"),
        ("unicode_filter","🔠","Unicode Bypass","Detect tricks"),
        ("file_spam_filter","📁","File Spam","Block file spam")
    ]
    feat_h = ""
    for k, i, n, d in features:
        v = s.get(k, 0)
        feat_h += f'<div class="ft"><div class="fti"><div class="ftic">{i}</div><div><div class="ftn">{n}</div><div class="ftd">{d}</div></div></div><div class="sw {"on" if v else ""}" onclick="tg(\'{gid}\',\'{k}\',this)"><div class="swd"></div></div></div>'

    warns_h = ""
    for w in warns:
        m = guild.get_member(int(w["user_id"]))
        nm = m.display_name if m else "Unknown"
        av = m.display_avatar.url if m else None
        avh = f'<img src="{av}">' if av else nm[0].upper()
        warns_h += f'<div class="row"><div class="rav">{avh}</div><div class="rin"><div class="rn">{nm}</div><div class="rd">{w["reason"]}</div><div class="rm">{w["timestamp"][:16]}</div></div><span class="tg tg-{w["severity"][0]}">{w["severity"]}</span><button class="bt bt-s bt-gh" onclick="cw(\'{gid}\',\'{w["user_id"]}\')">Clear</button></div>'

    actions_h = ""
    for a in actions:
        m = guild.get_member(int(a["user_id"]))
        md = guild.get_member(int(a["mod_id"]))
        nm = m.display_name if m else "Unknown"
        mdn = md.display_name if md else ("Bot" if a["mod_id"] == str(bot.user.id) else "Unknown")
        actions_h += f'<div class="row"><div class="rav">{nm[0].upper()}</div><div class="rin"><div class="rn">{nm} <span style="color:var(--brand);">[{a["action"]}]</span></div><div class="rd">{a["reason"]} · by {mdn}</div><div class="rm">{a["timestamp"][:16]}</div></div></div>'

    mem_h = ""
    for m in list(guild.members)[:200]:
        if m.bot:
            continue
        av = m.display_avatar.url
        rs = ", ".join([r.name for r in m.roles if r.name != "@everyone"][:2]) or "No roles"
        mem_h += f'<div class="mc" data-name="{m.name}"><div class="mav"><img src="{av}"></div><div class="mi"><div class="mn">{m.display_name}</div><div class="mm">{rs}</div></div><div style="display:flex;gap:4px;"><button class="bt bt-s bt-gh" onclick="ua(\'{gid}\',\'{m.id}\',\'warn\')">⚠️</button><button class="bt bt-s bt-gh" onclick="ua(\'{gid}\',\'{m.id}\',\'mute\')">🔇</button><button class="bt bt-s bt-r" onclick="ua(\'{gid}\',\'{m.id}\',\'ban\')">🔨</button></div></div>'

    ch_h = ""
    for ch in guild.text_channels:
        cn = ch.category.name if ch.category else "—"
        ch_h += f'<div class="ci"><span class="cic">#</span><span class="cnm">{ch.name}</span><span class="cnc">{cn}</span><button class="bt bt-s bt-r" onclick="dch(\'{gid}\',\'{ch.name}\')">×</button></div>'

    roles_h = ""
    for r in guild.roles:
        if r.name == "@everyone":
            continue
        cd = f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{str(r.color)};margin-right:8px;"></span>'
        roles_h += f'<div class="ci">{cd}<span class="cnm">{r.name}</span><span class="cnc">{len(r.members)} members</span><button class="bt bt-s bt-r" onclick="dr(\'{gid}\',\'{r.name}\')">×</button></div>'

    cmd_h = ""
    for cc in customs:
        cmd_h += f'<div class="cmd"><span class="cmt">{cc["trigger_word"]}</span><span class="cmr">{cc["response"][:80]}</span><button class="bt bt-s bt-r" onclick="dc(\'{gid}\',\'{cc["trigger_word"]}\')">×</button></div>'

    words_h = ""
    for w in words:
        words_h += f'<div class="cmd"><span class="cmt">{w["word"]}</span><button class="bt bt-s bt-r" onclick="dw(\'{gid}\',\'{w["word"]}\')">×</button></div>'

    top_h = ""
    for i, r in enumerate(top_users[:10], 1):
        m = guild.get_member(int(r["user_id"]))
        nm = m.display_name if m else "?"
        mdl = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        top_h += f'<div class="row"><div style="font-size:20px;width:36px;text-align:center;">{mdl}</div><div class="rin"><div class="rn">{nm}</div><div class="rd">{r["message_count"]} messages</div></div></div>'

    rep_h = ""
    for r in top_rep:
        m = guild.get_member(int(r["user_id"]))
        nm = m.display_name if m else "?"
        rep_h += f'<div class="row"><div class="rav">{nm[0].upper()}</div><div class="rin"><div class="rn">{nm}</div><div class="rd">⭐ {r["rep"]} rep</div></div></div>'

    gw_h = ""
    for g in gws:
        gw_h += f'<div class="row"><div style="font-size:24px;">🎉</div><div class="rin"><div class="rn">{g["prize"]}</div><div class="rd">{g["winners"]} winner(s) · {g["end_time"][:16]}</div></div></div>'

    daily_h = ""
    for d in daily:
        daily_h += f'<div class="row"><div style="font-size:18px;">📅</div><div class="rin"><div class="rn">{d["date"]}</div><div class="rd">{d["messages"]} msgs · {d["joins"]} joins · {d["leaves"]} leaves</div></div></div>'

    cho = "".join([f'<option value="{ch.name}">#{ch.name}</option>' for ch in guild.text_channels[:100]])
    cato = '<option value="">No category</option>' + "".join([f'<option value="{c.name}">{c.name}</option>' for c in guild.categories])

    si = f"https://cdn.discordapp.com/icons/{guild.id}/{guild.icon}.png" if guild.icon else None
    sih = f'<img src="{si}">' if si else guild.name[0].upper()

    return page(f"""<div class="app">{sidebar_h(session["user"],"overview",gid)}<div class="main"><div class="tb"><div class="cb"><a href="/">Home</a> › <b>{guild.name}</b></div></div><div class="ct">
<div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;"><div class="srvi" style="width:64px;height:64px;font-size:28px;">{sih}</div><div><h1 style="font-size:24px;font-weight:800;color:var(--head);">{guild.name}</h1><p style="color:var(--muted);font-size:14px;">{guild.member_count} members · {len(guild.text_channels)} channels · {len(guild.roles)} roles</p></div></div>
<div class="sg">
<div class="sc"><div class="si si-b">👥</div><div class="sv">{guild.member_count:,}</div><div class="sl">Members</div></div>
<div class="sc"><div class="si si-y">⚠️</div><div class="sv">{wc}</div><div class="sl">Warnings</div></div>
<div class="sc"><div class="si si-r">🔨</div><div class="sv">{ac_count}</div><div class="sl">Mod Actions</div></div>
<div class="sc"><div class="si si-g">⚡</div><div class="sv">{cc_count}</div><div class="sl">Custom Cmds</div></div>
</div>
<div class="tbs">
<button class="tab active" data-t="overview" onclick="sw('overview',this)">📊 Overview</button>
<button class="tab" data-t="features" onclick="sw('features',this)">⚙️ Features</button>
<button class="tab" data-t="moderation" onclick="sw('moderation',this)">🛡️ Mod</button>
<button class="tab" data-t="members" onclick="sw('members',this)">👥 Members</button>
<button class="tab" data-t="channels" onclick="sw('channels',this)">💬 Channels</button>
<button class="tab" data-t="roles" onclick="sw('roles',this)">🎭 Roles</button>
<button class="tab" data-t="warnings" onclick="sw('warnings',this)">⚠️ Warnings</button>
<button class="tab" data-t="commands" onclick="sw('commands',this)">⚡ Commands</button>
<button class="tab" data-t="filters" onclick="sw('filters',this)">🔤 Filters</button>
<button class="tab" data-t="analytics" onclick="sw('analytics',this)">📈 Analytics</button>
<button class="tab" data-t="leaderboard" onclick="sw('leaderboard',this)">🏆 Leaderboard</button>
<button class="tab" data-t="events" onclick="sw('events',this)">🎉 Events</button>
<button class="tab" data-t="announce" onclick="sw('announce',this)">📢 Announce</button>
<button class="tab" data-t="settings" onclick="sw('settings',this)">🔧 Settings</button>
</div>

<div id="tp-overview" class="pc active">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
<div class="pn"><div class="ph"><div class="pt">Recent Warnings</div></div><div class="pb">{warns_h if warns_h else '<div class="em"><div class="emi">✅</div><div class="emt">All clean!</div></div>'}</div></div>
<div class="pn"><div class="ph"><div class="pt">Recent Actions</div></div><div class="pb">{actions_h if actions_h else '<div class="em"><div class="emi">📋</div><div class="emt">No actions</div></div>'}</div></div>
</div>
</div>

<div id="tp-features" class="pc">
<div class="pn"><div class="ph"><div class="pt">Features ({len(features)})</div></div><div class="pb"><div class="fg2">{feat_h}</div></div></div>
</div>

<div id="tp-moderation" class="pc">
<div class="pn"><div class="ph"><div class="pt">Moderation Settings</div></div><div class="pb">
<div class="fr"><div class="fg"><label class="fl">Warnings → Mute</label><input type="number" class="fi" value="{s.get('warn_mute',3)}" onchange="us('{gid}','warn_mute',this.value)"></div><div class="fg"><label class="fl">Warnings → Ban</label><input type="number" class="fi" value="{s.get('warn_ban',5)}" onchange="us('{gid}','warn_ban',this.value)"></div></div>
<div class="fr"><div class="fg"><label class="fl">Mute Duration (min)</label><input type="number" class="fi" value="{s.get('mute_duration',10)}" onchange="us('{gid}','mute_duration',this.value)"></div><div class="fg"><label class="fl">AI Sensitivity</label><input type="number" step="0.1" min="0" max="1" class="fi" value="{s.get('ai_sensitivity',0.7)}" onchange="us('{gid}','ai_sensitivity',this.value)"></div></div>
<div class="fr"><div class="fg"><label class="fl">Spam Limit</label><input type="number" class="fi" value="{s.get('spam_limit',5)}" onchange="us('{gid}','spam_limit',this.value)"></div><div class="fg"><label class="fl">Spam Window (sec)</label><input type="number" class="fi" value="{s.get('spam_window',5)}" onchange="us('{gid}','spam_window',this.value)"></div></div>
<div class="fr"><div class="fg"><label class="fl">Raid Limit</label><input type="number" class="fi" value="{s.get('raid_limit',10)}" onchange="us('{gid}','raid_limit',this.value)"></div><div class="fg"><label class="fl">Min Account Age (days)</label><input type="number" class="fi" value="{s.get('min_account_age',7)}" onchange="us('{gid}','min_account_age',this.value)"></div></div>
</div></div>
</div>

<div id="tp-members" class="pc">
<div class="pn"><div class="ph"><div class="pt">Members ({guild.member_count})</div></div><div class="pb">
<div class="sw-wr"><span class="swic">🔍</span><input type="text" id="msr" class="swi" placeholder="Search..." oninput="ms()"></div>
<div class="mg">{mem_h}</div>
</div></div>
</div>

<div id="tp-channels" class="pc">
<div class="pn"><div class="ph"><div class="pt">Create Channel</div></div><div class="pb">
<div class="fr"><div class="fg"><label class="fl">Name</label><input type="text" id="chn" class="fi" placeholder="general"></div><div class="fg"><label class="fl">Category</label><select id="chc" class="fs">{cato}</select></div></div>
<button class="bt bt-b" onclick="cc('{gid}')">➕ Create</button>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Channels ({len(guild.text_channels)})</div></div><div class="pb">{ch_h}</div></div>
</div>

<div id="tp-roles" class="pc">
<div class="pn"><div class="ph"><div class="pt">Create Role</div></div><div class="pb">
<div class="fr"><div class="fg"><label class="fl">Name</label><input type="text" id="rln" class="fi" placeholder="VIP"></div><div class="fg"><label class="fl">Color</label><input type="color" id="rlc" class="fi" value="#5865f2"></div></div>
<button class="bt bt-b" onclick="cr('{gid}')">➕ Create Role</button>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Create Category</div></div><div class="pb">
<div class="fg"><label class="fl">Name</label><input type="text" id="ctn" class="fi"></div>
<button class="bt bt-b" onclick="cat('{gid}')">➕ Create Category</button>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Roles ({len(guild.roles)-1})</div></div><div class="pb">{roles_h}</div></div>
</div>

<div id="tp-warnings" class="pc">
<div class="pn"><div class="ph"><div class="pt">All Warnings ({wc})</div></div><div class="pb">{warns_h if warns_h else '<div class="em"><div class="emi">✅</div><div class="emt">No warnings!</div></div>'}</div></div>
</div>

<div id="tp-commands" class="pc">
<div class="pn"><div class="ph"><div class="pt">Add Custom Command</div></div><div class="pb">
<div class="fr"><div class="fg"><label class="fl">Trigger</label><input type="text" id="cct" class="fi" placeholder="hello"></div><div class="fg"><label class="fl">Response</label><input type="text" id="ccr" class="fi" placeholder="Hi there!"></div></div>
<button class="bt bt-b" onclick="ac('{gid}')">➕ Add</button>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Commands ({cc_count})</div></div><div class="pb">{cmd_h if cmd_h else '<div class="em"><div class="emi">⚡</div><div class="emt">No commands</div></div>'}</div></div>
</div>

<div id="tp-filters" class="pc">
<div class="pn"><div class="ph"><div class="pt">Add Word Filter</div></div><div class="pb">
<div style="display:flex;gap:10px;"><input type="text" id="wfw" class="fi" placeholder="word..." style="flex:1;"><button class="bt bt-b" onclick="aw('{gid}')">➕</button></div>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Filtered Words</div></div><div class="pb">{words_h if words_h else '<div class="em"><div class="emi">🔤</div><div class="emt">No filters</div></div>'}</div></div>
</div>

<div id="tp-analytics" class="pc">
<div class="pn"><div class="ph"><div class="pt">Server Stats</div></div><div class="pb">
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
<div><div class="sv">{guild.member_count}</div><div class="sl">Members</div></div>
<div><div class="sv">{sum(1 for m in guild.members if not m.bot)}</div><div class="sl">Humans</div></div>
<div><div class="sv">{sum(1 for m in guild.members if m.bot)}</div><div class="sl">Bots</div></div>
<div><div class="sv">{len(guild.channels)}</div><div class="sl">Channels</div></div>
</div>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Last 7 Days</div></div><div class="pb">{daily_h if daily_h else '<div class="em"><div class="emi">📊</div><div class="emt">No data yet</div></div>'}</div></div>
</div>

<div id="tp-leaderboard" class="pc">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
<div class="pn"><div class="ph"><div class="pt">💬 Most Active</div></div><div class="pb">{top_h if top_h else '<div class="em"><div class="emi">📊</div><div class="emt">No data</div></div>'}</div></div>
<div class="pn"><div class="ph"><div class="pt">⭐ Top Reputation</div></div><div class="pb">{rep_h if rep_h else '<div class="em"><div class="emi">⭐</div><div class="emt">No rep yet</div></div>'}</div></div>
</div>
</div>

<div id="tp-events" class="pc">
<div class="pn"><div class="ph"><div class="pt">🎉 Create Giveaway</div></div><div class="pb">
<div class="fr"><div class="fg"><label class="fl">Prize</label><input type="text" id="gwp" class="fi" placeholder="Nitro"></div><div class="fg"><label class="fl">Channel</label><select id="gwc" class="fs">{cho}</select></div></div>
<div class="fr"><div class="fg"><label class="fl">Duration (min)</label><input type="number" id="gwd" class="fi" value="60"></div><div class="fg"><label class="fl">Winners</label><input type="number" id="gww" class="fi" value="1"></div></div>
<button class="bt bt-b" onclick="gw('{gid}')">🎉 Start</button>
</div></div>
<div class="pn"><div class="ph"><div class="pt">Active Giveaways</div></div><div class="pb">{gw_h if gw_h else '<div class="em"><div class="emi">🎁</div><div class="emt">None active</div></div>'}</div></div>
<div class="pn"><div class="ph"><div class="pt">📊 Create Poll</div></div><div class="pb">
<div class="fg"><label class="fl">Question</label><input type="text" id="plq" class="fi"></div>
<div class="fr"><div class="fg"><label class="fl">Channel</label><select id="plc" class="fs">{cho}</select></div><div class="fg"><label class="fl">Options (comma)</label><input type="text" id="plo" class="fi" placeholder="A, B, C"></div></div>
<button class="bt bt-b" onclick="po('{gid}')">📊 Create</button>
</div></div>
</div>

<div id="tp-announce" class="pc">
<div class="pn"><div class="ph"><div class="pt">📢 Send Announcement</div></div><div class="pb">
<div class="fg"><label class="fl">Channel</label><select id="anc" class="fs">{cho}</select></div>
<div class="fg"><label class="fl">Title (optional)</label><input type="text" id="ant" class="fi"></div>
<div class="fg"><label class="fl">Message</label><textarea id="anm" class="fx"></textarea></div>
<button class="bt bt-b" onclick="sa('{gid}')">📤 Send</button>
</div></div>
<div class="pn"><div class="ph"><div class="pt">📨 Send DM</div></div><div class="pb">
<div class="fg"><label class="fl">User ID</label><input type="text" id="dmu" class="fi"></div>
<div class="fg"><label class="fl">Message</label><textarea id="dmm" class="fx"></textarea></div>
<button class="bt bt-b" onclick="sd('{gid}')">📨 Send DM</button>
</div></div>
</div>

<div id="tp-settings" class="pc">
<div class="pn"><div class="ph"><div class="pt">General</div></div><div class="pb">
<div class="fg"><label class="fl">Mod Role</label><input type="text" class="fi" value="{s.get('mod_role_name','Sentinel-Mod')}" onchange="us('{gid}','mod_role_name',this.value)"></div>
<div class="fr"><div class="fg"><label class="fl">Log Channel</label><input type="text" class="fi" value="{s.get('log_channel','sentinel-logs')}" onchange="us('{gid}','log_channel',this.value)"></div><div class="fg"><label class="fl">Raid Channel</label><input type="text" class="fi" value="{s.get('raid_channel','sentinel-raid-alerts')}" onchange="us('{gid}','raid_channel',this.value)"></div></div>
<div class="fg"><label class="fl">Welcome Channel</label><input type="text" class="fi" value="{s.get('welcome_channel','welcome')}" onchange="us('{gid}','welcome_channel',this.value)"></div>
</div></div>
</div>

</div></div></div>""", guild.name)

@app.route("/api/toggle/<gid>/<feat>", methods=["POST"])
def api_toggle(gid, feat):
    if "user" not in session: return jsonify({"success": False})
    valid = ["welcome_enabled","anti_nuke_enabled","invite_block","link_scan","slowmode_ai","pre_conflict","caps_filter","mention_spam","emoji_spam","zalgo_filter","phone_filter","email_filter","scam_filter","fake_nitro_filter","token_filter","anti_advertisement","everyone_block","nsfw_text_filter","unicode_filter","file_spam_filter"]
    if feat not in valid: return jsonify({"success": False})
    s = get_guild_settings(gid)
    nv = 0 if s.get(feat, 0) else 1
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {feat}=? WHERE guild_id=?", (nv, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/setting/<gid>/<key>", methods=["POST"])
def api_setting(gid, key):
    if "user" not in session: return jsonify({"success": False})
    valid = ["warn_mute","warn_ban","mute_duration","ai_sensitivity","spam_limit","spam_window","raid_limit","min_account_age","mod_role_name","log_channel","raid_channel","welcome_channel"]
    if key not in valid: return jsonify({"success": False})
    v = request.get_json().get("value")
    try:
        if key in ["warn_mute","warn_ban","mute_duration","spam_limit","spam_window","raid_limit","min_account_age"]:
            v = int(v)
        elif key == "ai_sensitivity":
            v = float(v)
    except:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (v, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/custom/<gid>", methods=["POST"])
def api_add_custom(gid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    t = d.get("trigger","").lower().strip()
    r = d.get("response","").strip()
    if not t or not r: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO custom_commands (guild_id, trigger_word, response) VALUES (?, ?, ?)", (gid, t, r))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/custom/<gid>/<trig>", methods=["DELETE"])
def api_del_custom(gid, trig):
    if "user" not in session: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM custom_commands WHERE guild_id=? AND trigger_word=?", (gid, trig))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/word/<gid>", methods=["POST"])
def api_add_word(gid):
    if "user" not in session: return jsonify({"success": False})
    w = request.get_json().get("word","").lower().strip()
    if not w: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)", (gid, w))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/word/<gid>/<word>", methods=["DELETE"])
def api_del_word(gid, word):
    if "user" not in session: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (gid, word.lower()))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/clearwarns/<gid>/<uid>", methods=["POST"])
def api_clear(gid, uid):
    if "user" not in session: return jsonify({"success": False})
    clear_warnings(uid, gid)
    return jsonify({"success": True})

@app.route("/api/announce/<gid>", methods=["POST"])
def api_announce(gid):
    if "user" not in session: return jsonify({"success": False, "error": "Auth"})
    d = request.get_json()
    cn = d.get("channel")
    msg = d.get("message")
    title = d.get("title") or "📢 Announcement"
    if not cn or not msg: return jsonify({"success": False, "error": "Missing"})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False, "error": "No guild"})
    ch = discord.utils.get(g.text_channels, name=cn)
    if not ch: return jsonify({"success": False, "error": "No channel"})
    try:
        e = discord.Embed(title=title, description=msg, color=discord.Color.blue(), timestamp=datetime.now())
        e.set_footer(text=f"Sent by {session['user']['username']}")
        asyncio.run_coroutine_threadsafe(ch.send(embed=e), bot.loop)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/dm/<gid>", methods=["POST"])
def api_dm(gid):
    if "user" not in session: return jsonify({"success": False, "error": "Auth"})
    d = request.get_json()
    uid = d.get("user_id")
    msg = d.get("message")
    if not uid or not msg: return jsonify({"success": False, "error": "Missing"})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    try:
        m = g.get_member(int(uid))
        if not m: return jsonify({"success": False, "error": "User not found"})
        e = discord.Embed(title=f"Message from {g.name}", description=msg, color=discord.Color.blue())
        asyncio.run_coroutine_threadsafe(m.send(embed=e), bot.loop)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/channel/<gid>", methods=["POST"])
def api_ch(gid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    n = d.get("name","").lower().replace(" ","-")
    cn = d.get("category")
    if not n: return jsonify({"success": False})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    try:
        cat = discord.utils.get(g.categories, name=cn) if cn else None
        fut = asyncio.run_coroutine_threadsafe(g.create_text_channel(name=n, category=cat), bot.loop)
        fut.result(timeout=10)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/channel/<gid>/<cn>", methods=["DELETE"])
def api_delch(gid, cn):
    if "user" not in session: return jsonify({"success": False})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    try:
        ch = discord.utils.get(g.text_channels, name=cn)
        if ch: asyncio.run_coroutine_threadsafe(ch.delete(), bot.loop)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/role/<gid>", methods=["POST"])
def api_rl(gid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    n = d.get("name","")
    cl = d.get("color","#000000")
    if not n: return jsonify({"success": False})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    try:
        c = discord.Color(int(cl.replace("#",""), 16))
        fut = asyncio.run_coroutine_threadsafe(g.create_role(name=n, color=c), bot.loop)
        fut.result(timeout=10)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/role/<gid>/<n>", methods=["DELETE"])
def api_delrl(gid, n):
    if "user" not in session: return jsonify({"success": False})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    try:
        r = discord.utils.get(g.roles, name=n)
        if r: asyncio.run_coroutine_threadsafe(r.delete(), bot.loop)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/category/<gid>", methods=["POST"])
def api_cat(gid):
    if "user" not in session: return jsonify({"success": False})
    n = request.get_json().get("name","")
    if not n: return jsonify({"success": False})
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    try:
        asyncio.run_coroutine_threadsafe(g.create_category(name=n), bot.loop)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/useraction/<gid>/<uid>", methods=["POST"])
def api_ua(gid, uid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    a = d.get("action")
    r = d.get("reason","No reason")
    dur = d.get("duration")
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    m = g.get_member(int(uid))
    if not m: return jsonify({"success": False, "error": "User not found"})
    try:
        if a == "ban":
            asyncio.run_coroutine_threadsafe(g.ban(m, reason=r), bot.loop)
        elif a == "kick":
            asyncio.run_coroutine_threadsafe(g.kick(m, reason=r), bot.loop)
        elif a == "mute":
            until = datetime.now() + timedelta(minutes=int(dur or 10))
            asyncio.run_coroutine_threadsafe(m.timeout(until, reason=r), bot.loop)
        elif a == "warn":
            add_warning(uid, gid, r, "manual")
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/giveaway/<gid>", methods=["POST"])
def api_gw(gid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    p = d.get("prize")
    cn = d.get("channel")
    dur = int(d.get("duration", 60))
    w = int(d.get("winners", 1))
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    ch = discord.utils.get(g.text_channels, name=cn)
    if not ch: return jsonify({"success": False, "error": "No channel"})
    try:
        end = datetime.now() + timedelta(minutes=dur)
        e = discord.Embed(title="🎉 GIVEAWAY!", description=f"**{p}**\nReact 🎉!", color=discord.Color.gold())
        e.add_field(name="Winners", value=str(w))
        e.add_field(name="Ends", value=f"<t:{int(end.timestamp())}:R>")
        fut = asyncio.run_coroutine_threadsafe(ch.send(embed=e), bot.loop)
        msg = fut.result(timeout=10)
        asyncio.run_coroutine_threadsafe(msg.add_reaction("🎉"), bot.loop)
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, host_id) VALUES (?,?,?,?,?,?,?)", (gid, str(ch.id), str(msg.id), p, w, end.isoformat(), session['user']['id']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

@app.route("/api/poll/<gid>", methods=["POST"])
def api_pl(gid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    q = d.get("question")
    cn = d.get("channel")
    opts = d.get("options", [])
    g = bot.get_guild(int(gid))
    if not g: return jsonify({"success": False})
    ch = discord.utils.get(g.text_channels, name=cn)
    if not ch: return jsonify({"success": False})
    try:
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
        e = discord.Embed(title=f"📊 {q}", color=discord.Color.blue())
        for i, o in enumerate(opts[:5]):
            e.add_field(name=f"{emojis[i]} {o.strip()}", value="\u200b", inline=False)
        fut = asyncio.run_coroutine_threadsafe(ch.send(embed=e), bot.loop)
        msg = fut.result(timeout=10)
        for i in range(min(len(opts), 5)):
            asyncio.run_coroutine_threadsafe(msg.add_reaction(emojis[i]), bot.loop)
        return jsonify({"success": True})
    except Exception as ex:
        return jsonify({"success": False, "error": str(ex)})

def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False)

# ============ RUN ============
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN missing!")
    elif not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing!")
    else:
        init_database()
        t = threading.Thread(target=run_flask)
        t.daemon = True
        t.start()
        print("🌐 Dashboard on :8080")
        print("🚀 Starting SentinelMod...")
        bot.run(DISCORD_TOKEN)
