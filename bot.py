# bot.py
# ================================
# SentinelMod - Clean Bot Core
# Pairs with separate dashboard.py
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
import random
import re
import unicodedata
import threading
from datetime import datetime, timedelta
from collections import defaultdict

import dashboard

# ============ CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

BOT_NAME = "SentinelMod"
AI_CHAT_CHANNEL = "sentinel-bot"

MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"

# ============ PERSONALITIES ============
PERSONALITIES = {
    "friendly": "You are extremely friendly, warm, and supportive. Use emojis.",
    "sarcastic": "You are sarcastic, witty, and playful, but still helpful.",
    "serious": "You are professional, serious, and direct.",
    "chaotic": "You are chaotic, random, energetic, and unpredictable.",
    "pirate": "You are a pirate. Speak like a pirate. Arr matey!",
    "medieval": "You are a medieval knight. Speak in old English.",
    "robot": "You are a robot. Speak in a robotic style.",
    "therapist": "You are a caring therapist. Validate feelings and be calm.",
    "villain": "You are a dramatic villain, theatrical but helpful.",
    "hype": "You are an over-the-top hype person. Very energetic.",
    "philosopher": "You are a deep philosopher. Question everything.",
    "caveman": "You speak like a caveman. Ugh. Fire good.",
    "shakespeare": "You speak in Shakespearean English.",
    "surfer": "You are a chill surfer dude.",
    "anime": "You speak like an anime character. Dramatic and emotional.",
    "cowboy": "You are a cowboy. Yeehaw partner.",
    "british": "You are extremely British.",
    "australian": "You are extremely Australian.",
    "valley_girl": "You are a valley girl.",
    "gen_z": "You use Gen Z slang naturally.",
    "boomer": "You are an old-school boomer.",
    "yoda": "Speak like Yoda you must.",
    "jarvis": "You are JARVIS from Iron Man.",
    "deadpool": "You are Deadpool. Break the fourth wall.",
    "sherlock": "You are Sherlock Holmes.",
    "gandalf": "You are Gandalf. Wise and mystical.",
    "tony_stark": "You are Tony Stark.",
    "groot": "You are Groot. Say 'I am Groot' and explain in parentheses.",
    "darth_vader": "You are Darth Vader.",
    "michael_scott": "You are Michael Scott.",
    "motivational": "You are extremely motivational and inspiring.",
    "pessimist": "You are pessimistic but still useful.",
    "optimist": "You are very optimistic.",
    "ninja": "You are a ninja. Quiet, stealthy, precise.",
    "samurai": "You are a samurai. Honour and discipline.",
    "fairy": "You are a magical fairy.",
    "vampire": "You are a sophisticated vampire.",
    "oracle": "You speak like an oracle in prophecies.",
    "wizard": "You are a powerful wizard.",
    "alien": "You are an alien fascinated by humans.",
    "ghost": "You are a friendly ghost.",
    "dragon": "You are an ancient dragon.",
    "nerd": "You are extremely nerdy and analytical.",
    "default": "You are SentinelMod, a helpful Discord bot."
}

# ============ DATABASE ============
def init_database():
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            guild_id TEXT,
            reason TEXT,
            severity TEXT,
            timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS mod_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            guild_id TEXT,
            action TEXT,
            reason TEXT,
            mod_id TEXT,
            timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS guild_settings (
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
            caps_filter INTEGER DEFAULT 1,
            mention_spam INTEGER DEFAULT 1,
            emoji_spam INTEGER DEFAULT 1,
            zalgo_filter INTEGER DEFAULT 1,
            phone_filter INTEGER DEFAULT 1,
            email_filter INTEGER DEFAULT 1,
            scam_filter INTEGER DEFAULT 1,
            nsfw_text_filter INTEGER DEFAULT 1,
            everyone_block INTEGER DEFAULT 0,
            anti_advertisement INTEGER DEFAULT 1,
            unicode_filter INTEGER DEFAULT 1,
            fake_nitro_filter INTEGER DEFAULT 1,
            token_filter INTEGER DEFAULT 1,
            file_spam_filter INTEGER DEFAULT 1,
            personality TEXT DEFAULT 'default'
        )""",
        """CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT,
            guild_id TEXT,
            memory TEXT,
            updated TEXT,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            guild_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS user_personalities (
            user_id TEXT,
            guild_id TEXT,
            personality TEXT DEFAULT 'default',
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS afk_users (
            user_id TEXT,
            guild_id TEXT,
            reason TEXT,
            timestamp TEXT,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            channel_id TEXT,
            message_id TEXT,
            prize TEXT,
            winners INTEGER DEFAULT 1,
            end_time TEXT,
            active INTEGER DEFAULT 1,
            host_id TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS auto_roles (
            guild_id TEXT,
            role_id TEXT,
            PRIMARY KEY (guild_id, role_id)
        )""",
        """CREATE TABLE IF NOT EXISTS word_filters (
            guild_id TEXT,
            word TEXT,
            PRIMARY KEY (guild_id, word)
        )""",
        """CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            note TEXT,
            mod_id TEXT,
            timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS message_stats (
            user_id TEXT,
            guild_id TEXT,
            message_count INTEGER DEFAULT 0,
            last_message TEXT,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            guild_id TEXT,
            channel_id TEXT,
            reminder TEXT,
            remind_time TEXT,
            active INTEGER DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS custom_commands (
            guild_id TEXT,
            trigger_word TEXT,
            response TEXT,
            PRIMARY KEY (guild_id, trigger_word)
        )""",
        """CREATE TABLE IF NOT EXISTS confessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            confession TEXT,
            timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS reputation (
            user_id TEXT,
            guild_id TEXT,
            rep INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS quarantine (
            user_id TEXT,
            guild_id TEXT,
            reason TEXT,
            timestamp TEXT,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS trivia_scores (
            user_id TEXT,
            guild_id TEXT,
            score INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS daily_stats (
            guild_id TEXT,
            date TEXT,
            messages INTEGER DEFAULT 0,
            joins INTEGER DEFAULT 0,
            leaves INTEGER DEFAULT 0,
            mod_actions INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, date)
        )"""
    ]

    for table in tables:
        c.execute(table)

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

    return {
        "guild_id": str(gid),
        "mod_role_name": MOD_ROLE_NAME,
        "log_channel": MOD_LOG_CHANNEL,
        "raid_channel": RAID_CHANNEL,
        "warn_mute": 3,
        "warn_ban": 5,
        "mute_duration": 10,
        "spam_limit": 5,
        "spam_window": 5,
        "raid_limit": 10,
        "raid_window": 10,
        "min_account_age": 7,
        "scan_images": 1,
        "ai_sensitivity": 0.7,
        "welcome_channel": "welcome",
        "welcome_enabled": 1,
        "anti_nuke_enabled": 1,
        "invite_block": 0,
        "link_scan": 1,
        "slowmode_ai": 1,
        "pre_conflict": 1,
        "caps_filter": 1,
        "mention_spam": 1,
        "emoji_spam": 1,
        "zalgo_filter": 1,
        "phone_filter": 1,
        "email_filter": 1,
        "scam_filter": 1,
        "nsfw_text_filter": 1,
        "everyone_block": 0,
        "anti_advertisement": 1,
        "unicode_filter": 1,
        "fake_nitro_filter": 1,
        "token_filter": 1,
        "file_spam_filter": 1,
        "personality": "default"
    }

def init_guild_settings(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(gid),))
    conn.commit()
    conn.close()

def add_warning(uid, gid, reason, severity):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO warnings (user_id, guild_id, reason, severity, timestamp) VALUES (?, ?, ?, ?, ?)",
        (str(uid), str(gid), reason, severity, datetime.now().isoformat())
    )
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
    c.execute(
        "INSERT INTO mod_actions (user_id, guild_id, action, reason, mod_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uid), str(gid), action, reason, str(mod_id), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_user_memory(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT memory FROM user_memory WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
    row = c.fetchone()
    conn.close()
    return row["memory"] if row else ""

def update_user_memory(uid, gid, memory):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_memory (user_id, guild_id, memory, updated) VALUES (?, ?, ?, ?)",
        (str(uid), str(gid), memory, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_conversation_history(uid, gid, limit=20):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM conversation_history WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT ?",
        (str(uid), str(gid), limit)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def add_to_conversation(uid, gid, role, content):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversation_history (user_id, guild_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
        (str(uid), str(gid), role, content, datetime.now().isoformat())
    )
    conn.commit()
    c.execute(
        """DELETE FROM conversation_history
           WHERE id NOT IN (
               SELECT id FROM conversation_history
               WHERE user_id=? AND guild_id=?
               ORDER BY timestamp DESC LIMIT 50
           ) AND user_id=? AND guild_id=?""",
        (str(uid), str(gid), str(uid), str(gid))
    )
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
    c.execute(
        "INSERT OR REPLACE INTO user_personalities (user_id, guild_id, personality) VALUES (?, ?, ?)",
        (str(uid), str(gid), p)
    )
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
    c.execute(
        """INSERT INTO message_stats (user_id, guild_id, message_count, last_message)
           VALUES (?, ?, 1, ?)
           ON CONFLICT(user_id, guild_id)
           DO UPDATE SET message_count=message_count+1, last_message=?""",
        (str(uid), str(gid), datetime.now().isoformat(), datetime.now().isoformat())
    )
    today = datetime.now().date().isoformat()
    c.execute(
        """INSERT INTO daily_stats (guild_id, date, messages)
           VALUES (?, ?, 1)
           ON CONFLICT(guild_id, date)
           DO UPDATE SET messages=messages+1""",
        (str(gid), today)
    )
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

# ============ AI HELPERS ============
async def ask_groq(prompt, system="Helpful AI.", max_tokens=1000, history=None):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-15:])
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": max_tokens
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq error: {e}")
    return None

async def ask_groq_json(prompt, system="Respond only in valid JSON."):
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
                timeout=aiohttp.ClientTimeout(total=30)
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

async def stream_response(message, prompt, system, history=None, uid=None, gid=None):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-15:])
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 1000,
        "stream": True
    }

    sent = await message.reply("💭 *thinking...*")
    full = ""
    last_update = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
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

                mem = await ask_groq(
                    f"Current memory: {get_user_memory(uid, gid)}\nNew: User: {prompt}\nBot: {full}\nUpdate memory with useful facts only. Under 500 chars.",
                    "Remember only important facts about the user."
                )
                if mem:
                    update_user_memory(uid, gid, mem[:500])

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
    return (
        f"You are SentinelMod, a Discord bot.\n"
        f"Personality: {personality}\n"
        f"{f'Memory about user: {memory}' if memory else ''}\n"
        f"{extra}\n"
        f"Keep responses under 1500 chars."
    )

# ============ PARSER ============
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

Rules:
- If unclear or just chatting, return command="chat"
- Moderation commands require mentioned target
- Never confuse sender with target
- confidence < 0.8 -> chat

JSON only:
{{
  "command":"create_channel|delete_channel|create_role|delete_role|create_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|start_giveaway|create_poll|set_afk|setup_server|summarize|translate|add_word_filter|remove_word_filter|trivia|wouldyourather|eightball|roast|compliment|dadjoke|ship|rate|fact|truthordare|story|debate|riddle|pickupline|horoscope|remind|confession|rep|server_health|activity_stats|quarantine|unquarantine|add_custom_command|remove_custom_command|help|chat|unknown",
  "needs_confirmation":true,
  "confirmation_message":"text",
  "confidence":0.0,
  "params":{
    "name":null,
    "target_user_id":null,
    "target_user_name":null,
    "target_user2":null,
    "reason":null,
    "duration":null,
    "category":null,
    "color":null,
    "private":false,
    "amount":null,
    "prize":null,
    "winners":null,
    "question":null,
    "options":null,
    "language":null,
    "text":null,
    "feature":null,
    "word":null,
    "note":null,
    "channel":null,
    "response":null,
    "reminder_time":null,
    "rating_target":null,
    "zodiac":null
  }
}}
"""
    return await ask_groq_json(prompt)

def find_member_strict(guild, params):
    uid = params.get("target_user_id")
    if uid:
        try:
            member = guild.get_member(int(uid))
            if member:
                return member
        except:
            pass

    name = params.get("target_user_name")
    if name:
        clean = name.lower().strip().replace("@", "")
        for m in guild.members:
            if m.name.lower() == clean or m.display_name.lower() == clean:
                return m
    return None

# ============ FUN ============
async def do_trivia(message, gid, uid):
    trivia = await ask_groq_json(
        'Generate trivia. JSON: {"question":"q","correct":"a","wrong1":"b","wrong2":"c","wrong3":"d","category":"cat","difficulty":"easy"}'
    )
    if not trivia:
        return "❌ Failed!"

    answers = [trivia["correct"], trivia["wrong1"], trivia["wrong2"], trivia["wrong3"]]
    random.shuffle(answers)
    correct_index = answers.index(trivia["correct"])
    emojis = ["🇦", "🇧", "🇨", "🇩"]

    embed = discord.Embed(
        title=f"🧠 {trivia['category']}",
        description=trivia["question"],
        color=discord.Color.blue()
    )
    embed.add_field(name="Options", value="\n".join(f"{emojis[i]} {a}" for i, a in enumerate(answers)))

    msg = await message.channel.send(embed=embed)
    for e in emojis[:4]:
        await msg.add_reaction(e)

    trivia_sessions[msg.id] = {
        "correct_emoji": emojis[correct_index],
        "correct_answer": trivia["correct"],
        "guild_id": gid,
        "answered": []
    }

    await asyncio.sleep(30)

    if msg.id in trivia_sessions:
        await message.channel.send(f"⏰ Answer: **{trivia['correct']}**")
        del trivia_sessions[msg.id]

    return None

async def do_fun(ftype, params, author):
    prompts = {
        "wouldyourather": ("Generate a fun would-you-rather question.", "🤔 Would You Rather?"),
        "eightball": (f"Magic 8ball answer for: {params.get('question','...')}", "🎱 Magic 8-Ball"),
        "roast": (f"Playful roast of {params.get('target_user_name','someone')}. Fun, not cruel.", "🔥 Roast"),
        "compliment": (f"Give a heartfelt compliment to {params.get('target_user_name', author.name)}.", "💝 Compliment"),
        "dadjoke": ("Tell a dad joke.", "👨 Dad Joke"),
        "ship": (f"Love compatibility between {params.get('target_user_name','x')} and {params.get('target_user2','y')}.", "💕 Ship"),
        "rate": (f"Rate '{params.get('rating_target','life')}' out of 10 with funny reasoning.", "⭐ Rating"),
        "fact": ("Tell a surprising fact.", "🤯 Fact"),
        "truthordare": ("Generate a truth or dare prompt.", "🎯 Truth or Dare"),
        "story": (f"Write a short story about {params.get('text','something cool')}.", "📖 Story"),
        "riddle": ("Give a riddle and then the answer.", "🧩 Riddle"),
        "pickupline": ("Give a funny pickup line.", "😘 Pickup Line"),
        "horoscope": (f"Give a fun horoscope for {params.get('zodiac','Aries')}.", "⭐ Horoscope"),
    }
    prompt, title = prompts.get(ftype, ("Tell a joke.", "😄 Fun"))
    result = await ask_groq(prompt, "You are a fun Discord bot.")
    if result:
        return discord.Embed(title=title, description=result, color=discord.Color.blue())
    return None

# ============ MODERATION ============
async def alert_mods(guild, embed):
    s = get_guild_settings(guild.id)
    ch = discord.utils.get(guild.text_channels, name=s["log_channel"])
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    if ch:
        await ch.send(content=mr.mention if mr else "", embed=embed)

async def check_spam(msg, s):
    key = f"{msg.author.id}:{msg.guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    window = s.get("spam_window", 5)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < window]
    return len(spam_tracker[key]) >= s.get("spam_limit", 5)

async def handle_spam(msg, s):
    try:
        await msg.channel.purge(limit=10, check=lambda m: m.author == msg.author)
    except:
        pass
    try:
        await msg.author.timeout(datetime.now() + timedelta(minutes=s.get("mute_duration", 10)), reason="Spam")
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
            await ch.send(content=f"🚨 {mr.mention if mr else ''}", embed=discord.Embed(title="🚨 RAID DETECTED", color=discord.Color.red()))
        await asyncio.sleep(300)
        raid_mode_active[guild.id] = False

    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    if age < s.get("min_account_age", 7):
        try:
            await member.kick(reason="Raid protection")
        except:
            pass

async def check_nuke(guild, action, executor):
    if executor == guild.me:
        return False
    key = f"{guild.id}:{executor.id}"
    now = time.time()
    nuke_action_tracker[key].append(now)
    nuke_action_tracker[key] = [t for t in nuke_action_tracker[key] if now - t < 10]
    return len(nuke_action_tracker[key]) >= 3

async def handle_nuke(guild, executor, action):
    try:
        await guild.ban(executor, reason="Anti-nuke")
    except:
        pass
    embed = discord.Embed(title="💣 NUKE STOPPED", description=f"**{executor}** banned!", color=discord.Color.dark_red(), timestamp=datetime.now())
    await alert_mods(guild, embed)

async def check_patterns(msg, s):
    content = msg.content
    cl = content.lower()

    if s.get("phone_filter", 1) and re.search(r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b', content):
        return "phone", "Phone number", "high"

    if s.get("email_filter", 1) and re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
        return "email", "Email", "high"

    keyword_sets = [
        (s.get("fake_nitro_filter", 1), ["free nitro", "claim nitro"], "fake_nitro", "Nitro scam", "critical"),
        (s.get("token_filter", 1), ["discord token", "grabify"], "token", "Token grab", "critical"),
        (s.get("scam_filter", 1), ["you won", "claim your prize"], "scam", "Scam", "critical"),
        (1, ["want to kill myself", "want to die"], "self_harm", "Self-harm", "high"),
        (1, ["death to all", "kill all"], "extremism", "Extremism", "critical"),
    ]

    for enabled, words, ptype, reason, sev in keyword_sets:
        if enabled and any(w in cl for w in words):
            return ptype, reason, sev

    if s.get("caps_filter", 1) and len(content) > 10:
        if sum(1 for c in content if c.isupper()) / len(content) > 0.7:
            return "caps", "Caps", "low"

    if s.get("mention_spam", 1) and len(msg.mentions) >= 5:
        return "mentions", "Mention spam", "high"

    if s.get("invite_block", 0) and re.search(r'(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', content):
        return "invite", "Invite", "medium"

    if s.get("link_scan", 1) and "http" in cl:
        bad = ["grabify", "iplogger", "discord.gift", "free-nitro", "phish"]
        for b in bad:
            if b in cl:
                return "phishing", "Phishing", "critical"

    return None, None, None

async def check_toxicity(content, context=""):
    return await ask_groq_json(
        f'Analyze: "{content}" Context: {context}\nJSON: {{"toxic":true/false,"severity":"none|low|medium|high|critical","confidence":0.0-1.0,"reason":"brief"}}'
    )

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

    if wc >= s.get("warn_mute", 3) and wc < s.get("warn_ban", 5):
        try:
            await u.timeout(datetime.now() + timedelta(minutes=s.get("mute_duration", 10)), reason=reason)
        except:
            pass

    if wc >= s.get("warn_ban", 5):
        try:
            await g.ban(u, reason=reason)
        except:
            pass

    await alert_mods(
        g,
        discord.Embed(title="🚨 AI Mod", color=discord.Color.red())
        .add_field(name="User", value=u.mention)
        .add_field(name="Reason", value=reason)
        .add_field(name="Warnings", value=str(wc))
    )

# ============ SETUP ============
async def setup_server(guild):
    results = []
    s = get_guild_settings(guild.id)

    for rn, c, h in [
        (s["mod_role_name"], discord.Color.red(), True),
        ("Muted", discord.Color.dark_gray(), False),
        ("Quarantined", discord.Color.dark_gray(), False)
    ]:
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
            ow = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
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

    for cn in ["welcome", "rules", "general", "announcements"]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn)
                results.append(f"✅ #{cn}")
            except:
                pass

    return results

# ============ UI ============
class ConfirmView(discord.ui.View):
    def __init__(self, parsed, msg, guild, author):
        super().__init__(timeout=30)
        self.parsed = parsed
        self.msg = msg
        self.guild = guild
        self.author = author

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Only requester.", ephemeral=True)
            return
        await interaction.response.defer()
        r = await execute_command(self.parsed, self.msg, self.guild, self.author)
        if r:
            await interaction.followup.send(r)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction, button):
        await interaction.response.send_message("❌ Cancelled.")
        self.stop()

# ============ SLASH COMMANDS ============
@bot.tree.command(name="dashboard", description="Get dashboard link")
async def dashboard_cmd(interaction: discord.Interaction):
    url = REDIRECT_URI.replace('/callback', '')
    await interaction.response.send_message(
        embed=discord.Embed(title="🌐 Dashboard", description=f"**{url}**", color=discord.Color.blue()),
        ephemeral=True
    )

@bot.tree.command(name="personality", description="Choose personality")
async def personality_cmd(interaction: discord.Interaction):
    opts = [discord.SelectOption(label=n.replace("_", " ").title(), value=n) for n in list(PERSONALITIES.keys())[:25]]
    view = discord.ui.View(timeout=60)
    select = discord.ui.Select(placeholder="Choose...", options=opts)

    async def cb(i):
        p = i.data["values"][0]
        set_user_personality(str(i.user.id), str(i.guild.id), p)
        await i.response.send_message(f"✅ **{p}**!", ephemeral=True)

    select.callback = cb
    view.add_item(select)
    await interaction.response.send_message(
        embed=discord.Embed(title="🎭 Personality", description="Pick one!", color=discord.Color.purple()),
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ SentinelMod", color=discord.Color.blue())
    embed.add_field(name="💬 Chat", value=f"@mention me or chat in #sentinel-bot")
    embed.add_field(name="🌐 Dashboard", value=REDIRECT_URI.replace('/callback', ''), inline=False)
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

            reaction = discord.utils.get(msg.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot] if reaction else []

            if users:
                winners = random.sample(users, min(g["winners"], len(users)))
                mentions = ", ".join(x.mention for x in winners)
                await ch.send(
                    f"🎉 {mentions}!",
                    embed=discord.Embed(
                        title="🎉 Giveaway Ended!",
                        description=f"**{g['prize']}**\nWinners: {mentions}",
                        color=discord.Color.gold()
                    )
                )

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
    for guild in bot.guilds:
        try:
            settings = get_guild_settings(guild.id)
            ch = discord.utils.get(guild.text_channels, name=settings.get("log_channel", "sentinel-logs"))
            if not ch:
                continue

            yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()

            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT messages, joins, leaves, mod_actions FROM daily_stats WHERE guild_id=? AND date=?", (str(guild.id), yesterday))
            row = c.fetchone()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND timestamp >= ?", (str(guild.id), yesterday + "T00:00:00"))
            warns = c.fetchone()[0]
            conn.close()

            messages = row["messages"] if row else 0
            joins = row["joins"] if row else 0
            leaves = row["leaves"] if row else 0
            mod_actions = row["mod_actions"] if row else 0

            embed = discord.Embed(
                title="📊 Daily Server Report",
                description=f"Stats for **{yesterday}**",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="💬 Messages", value=f"{messages:,}", inline=True)
            embed.add_field(name="📥 Joined", value=str(joins), inline=True)
            embed.add_field(name="📤 Left", value=str(leaves), inline=True)
            embed.add_field(name="🔨 Mod Actions", value=str(mod_actions), inline=True)
            embed.add_field(name="⚠️ Warnings", value=str(warns), inline=True)
            embed.add_field(name="👥 Members", value=str(guild.member_count), inline=True)
            await ch.send(embed=embed)
        except Exception as e:
            print(f"Daily stats error: {e}")

# ============ EVENTS ============
@bot.event
async def on_ready():
    print(f"🤖 {bot.user} ONLINE in {len(bot.guilds)} servers")

    for g in bot.guilds:
        init_guild_settings(g.id)

    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} slash commands synced")
    except Exception as e:
        print(f"Sync error: {e}")

    if not check_giveaways.is_running():
        check_giveaways.start()
    if not check_reminders.is_running():
        check_reminders.start()
    if not daily_server_stats.is_running():
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
    c.execute(
        """INSERT INTO daily_stats (guild_id, date, joins)
           VALUES (?, ?, 1)
           ON CONFLICT(guild_id, date)
           DO UPDATE SET joins=joins+1""",
        (str(g.id), today)
    )
    conn.commit()
    conn.close()

    if await check_raid(member):
        await handle_raid(g, member)
        return

    if s.get("welcome_enabled", 1):
        ch = discord.utils.get(g.text_channels, name=s.get("welcome_channel", "welcome"))
        if ch:
            w = await ask_groq(f"Welcome {member.display_name} to {g.name}. 2 sentences.", "Friendly bot.")
            if w:
                embed = discord.Embed(title="👋 Welcome!", description=w, color=discord.Color.green())
                embed.set_thumbnail(url=member.display_avatar.url)
                await ch.send(content=member.mention, embed=embed)

@bot.event
async def on_member_remove(member):
    today = datetime.now().date().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO daily_stats (guild_id, date, leaves)
           VALUES (?, ?, 1)
           ON CONFLICT(guild_id, date)
           DO UPDATE SET leaves=leaves+1""",
        (str(member.guild.id), today)
    )
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
async def on_audit_log_entry_create(entry):
    g = entry.guild
    s = get_guild_settings(g.id)
    if not s.get("anti_nuke_enabled", 1):
        return

    danger_actions = [
        discord.AuditLogAction.channel_delete,
        discord.AuditLogAction.role_delete,
        discord.AuditLogAction.ban,
        discord.AuditLogAction.kick,
        discord.AuditLogAction.webhook_create
    ]

    if entry.action in danger_actions and entry.user:
        mr = discord.utils.get(g.roles, name=s["mod_role_name"])
        if entry.user == g.me:
            return
        if mr and mr in entry.user.roles:
            return
        if await check_nuke(g, str(entry.action), entry.user):
            await handle_nuke(g, entry.user, str(entry.action))

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
            await message.channel.send("👋 Welcome back!", delete_after=5)
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

    # AI chat / mention
    is_ai_channel = message.channel.name == AI_CHAT_CHANNEL
    is_mentioned = bot.user in message.mentions

    if is_ai_channel or is_mentioned:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()

        if not content and not is_ai_channel:
            await message.reply(f"👋 Try `@{BOT_NAME} help`")
            return

        if content:
            if is_mod or is_admin:
                async with message.channel.typing():
                    parsed = await parse_command(content, message.guild, message.author)

                if parsed and parsed.get("command") not in ["chat", "unknown", None]:
                    conf = parsed.get("confidence", 0)
                    if conf < 0.7:
                        sys = get_system_prompt(str(message.author.id), str(message.guild.id))
                        hist = get_conversation_history(str(message.author.id), str(message.guild.id))
                        await stream_response(message, content, sys, hist, str(message.author.id), str(message.guild.id))
                        return

                    dangerous = [
                        "ban_user", "kick_user", "mute_user", "warn_user",
                        "delete_channel", "delete_role", "delete_category",
                        "lockdown", "purge", "clear_warnings", "quarantine"
                    ]

                    if parsed.get("command") in dangerous:
                        t = find_member_strict(message.guild, parsed.get("params", {}))
                        if parsed.get("params", {}).get("target_user_name") and not t:
                            await message.reply("❌ User not found. @mention them!")
                            return

                    need_confirm = parsed.get("needs_confirmation", False) or parsed.get("command") in dangerous
                    if need_confirm:
                        embed = discord.Embed(
                            title="⚠️ Confirm",
                            description=parsed.get("confirmation_message", "Confirm?"),
                            color=discord.Color.orange()
                        )
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

    # Spam
    if await check_spam(message, s):
        await handle_spam(message, s)
        return

    # Pattern checks
    ptype, preason, psev = await check_patterns(message, s)
    if ptype:
        try:
            await message.delete()
        except:
            pass

        if ptype == "self_harm":
            try:
                await message.channel.send(
                    embed=discord.Embed(
                        title="💙 We're Here",
                        description=f"{message.author.mention}\n**988** Suicide Prevention",
                        color=discord.Color.blue()
                    )
                )
            except:
                pass

        wc = add_warning(message.author.id, message.guild.id, preason, psev)

        today = datetime.now().date().isoformat()
        conn = get_db()
        c = conn.cursor()
        c.execute(
            """INSERT INTO daily_stats (guild_id, date, mod_actions)
               VALUES (?, ?, 1)
               ON CONFLICT(guild_id, date)
               DO UPDATE SET mod_actions=mod_actions+1""",
            (str(message.guild.id), today)
        )
        conn.commit()
        conn.close()

        if psev in ["high", "critical"]:
            await alert_mods(
                message.guild,
                discord.Embed(title=f"🚨 {ptype}", color=discord.Color.red())
                .add_field(name="User", value=message.author.mention)
                .add_field(name="Reason", value=preason)
            )

        if psev == "critical":
            try:
                await message.guild.ban(message.author, reason=f"IMMEDIATE: {preason}")
            except:
                pass
        return

    # Word filters
    words = get_filtered_words(message.guild.id)
    clean = message.content.lower()
    normalized = clean
    for old, new in [("@","a"),("0","o"),("1","i"),("3","e"),("$","s"),("5","s"),("4","a")]:
        normalized = normalized.replace(old, new)

    for w in words:
        if w in clean or w in normalized:
            try:
                await message.delete()
            except:
                pass
            add_warning(message.author.id, message.guild.id, "Filtered word", "medium")
            await message.channel.send(f"⚠️ {message.author.mention} Word not allowed!", delete_after=5)
            return

    if len(message.content) < 3:
        await bot.process_commands(message)
        return

    # Toxicity
    ctx = ""
    try:
        history_lines = []
        async for m in message.channel.history(limit=5, before=message):
            if not m.author.bot:
                history_lines.append(f"{m.author.name}: {m.content}")
        ctx = "\n".join(reversed(history_lines))
    except:
        pass

    analysis = await check_toxicity(message.content, ctx)
    if analysis and analysis.get("toxic"):
        sev = analysis.get("severity", "low")
        conf = analysis.get("confidence", 0)
        if conf >= s.get("ai_sensitivity", 0.7):
            if sev in ["medium", "high", "critical"]:
                await punish_user(message, sev, analysis.get("reason", "Toxic"), analysis)

    await bot.process_commands(message)

# ============ RUN ============
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN missing!")
    elif not GROQ_API_KEY:
        print("❌ GROQ_API_KEY missing!")
    else:
        init_database()
        dashboard.set_bot(bot)
        thread = threading.Thread(target=dashboard.run_dashboard)
        thread.daemon = True
        thread.start()
        print("🌐 Dashboard running on port 8080")
        print("🚀 Starting SentinelMod...")
        bot.run(DISCORD_TOKEN)
