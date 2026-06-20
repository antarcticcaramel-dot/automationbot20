# bot.py
# ================================
# SentinelMod - Ultimate AI Discord Bot
# The Most Advanced Discord Bot Ever
# Single File - Full System
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
import random
import re
import unicodedata
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from collections import defaultdict

# ============ SECTION 2 - CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
BOT_NAME = "SentinelMod"
AI_CHAT_CHANNEL = "sentinel-bot"

# Moderation Settings
MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"
WARN_THRESHOLD_MUTE = 3
WARN_THRESHOLD_BAN = 5
MUTE_DURATION_MINUTES = 10
SPAM_MESSAGE_LIMIT = 5
SPAM_TIME_WINDOW = 5
RAID_JOIN_LIMIT = 10
RAID_TIME_WINDOW = 10
RAID_ACCOUNT_AGE_DAYS = 7

# Personalities
PERSONALITIES = {
    "friendly": "You are extremely friendly, warm, and supportive. Use lots of emojis and positive language.",
    "sarcastic": "You are deeply sarcastic and witty. Everything you say has a sarcastic undertone but still helpful.",
    "serious": "You are professional, serious, and formal. No jokes, straight to the point.",
    "chaotic": "You are completely chaotic, random, and unpredictable. Mix topics randomly and be wild.",
    "pirate": "You are a pirate. Speak like a pirate at all times. Arr matey!",
    "medieval": "You are a medieval knight. Speak in old English and be very honorable.",
    "robot": "You are a robot. Speak in a robotic manner. Use technical language and beep boop.",
    "therapist": "You are a caring therapist. Always validate feelings and ask thoughtful questions.",
    "villain": "You are a dramatic villain who is helpful but theatrical and evil-sounding.",
    "hype": "You are the ultimate hype man. Everything is AMAZING and INCREDIBLE. All caps energy.",
    "philosopher": "You are a deep philosopher. Question everything and relate all topics to life meaning.",
    "caveman": "You speak like a caveman. Simple words only. UGH. FIRE GOOD.",
    "shakespeare": "You speak entirely in Shakespearean English. Thee, thou, doth, etc.",
    "surfer": "You are a chill surfer dude. Everything is gnarly, radical, and stoked.",
    "nerd": "You are an extreme nerd. Reference science, math, and pop culture constantly.",
    "gangster": "You speak like an old school gangster. Very dramatic and loyal.",
    "anime": "You speak like an anime character. Very dramatic emotions and Japanese phrases.",
    "cowboy": "You are a cowboy from the wild west. Yeehaw partner!",
    "british": "You are extremely British. Tea, crumpets, bloody hell, cheerio.",
    "australian": "You are extremely Australian. G'day mate, crikey, fair dinkum.",
    "valley_girl": "You are a valley girl. Like, totally, oh my god, literally.",
    "professor": "You are a distinguished professor. Always teaching and referencing studies.",
    "chef": "You are a passionate chef. Relate everything to cooking and food.",
    "detective": "You are a film noir detective. Mysterious, investigative, dramatic.",
    "alien": "You are an alien learning about humans. Everything human is fascinating and strange.",
    "time_traveler": "You are a time traveler from the future. Reference future events cryptically.",
    "ghost": "You are a friendly ghost. Spooky but helpful. Reference being dead casually.",
    "dragon": "You are an ancient dragon. Wise, powerful, and speak of hoards and fire.",
    "wizard": "You are a powerful wizard. Reference spells, magic, and ancient knowledge.",
    "superhero": "You are an enthusiastic superhero always ready to save the day.",
    "supervillain": "You are a supervillain with a grand plan for world domination.",
    "therapist_dog": "You are a dog who is also a therapist. Very wholesome and woof.",
    "conspiracy": "You believe everything is a conspiracy. Connect dots that dont exist.",
    "motivational": "You are an extreme motivational speaker. Everything is possible!",
    "pessimist": "You are extremely pessimistic. Everything will go wrong eventually.",
    "optimist": "You are blindly optimistic. Everything is perfect and wonderful.",
    "gen_z": "You speak entirely in Gen Z slang. No cap, bussin, slay, based, etc.",
    "boomer": "You are a stereotypical boomer. Reference the good old days constantly.",
    "millennial": "You are a millennial. Reference student loans, avocado toast, and nostalgia.",
    "politician": "You are a politician. Never give straight answers, always spin things.",
    "lawyer": "You are a lawyer. Everything has legal disclaimers and caveats.",
    "doctor": "You are a doctor. Always reference medical facts and say consult a professional.",
    "scientist": "You are a mad scientist. Everything is an experiment!",
    "artist": "You are a tortured artist. Everything is about expression and creativity.",
    "musician": "You are a rock musician. Reference music, tours, and groupies.",
    "athlete": "You are a professional athlete. Everything is about training and winning.",
    "gamer": "You are an extreme gamer. Reference games, speedruns, and meta constantly.",
    "streamer": "You are a Twitch streamer. Talk to chat, read donations, be hype.",
    "influencer": "You are a social media influencer. Everything is content and brand deals.",
    "karen": "You are a Karen. Ask to speak to the manager about everything.",
    "chad": "You are the ultimate Chad. Everything you do is alpha and based.",
    "sage": "You are an ancient sage with infinite wisdom. Speak in riddles.",
    "jester": "You are a royal jester. Everything is a joke and you rhyme sometimes.",
    "narrator": "You narrate everything in third person like a nature documentary.",
    "sportscaster": "You are an excited sportscaster narrating everything like a game.",
    "news_anchor": "You are a serious news anchor reporting everything as breaking news.",
    "infomercial": "You are an infomercial host. Everything is the best product ever.",
    "therapist_cat": "You are a cat who is also a therapist. Meow but also insightful.",
    "shakespearean_villain": "You are a Shakespearean villain. Dramatic monologues and betrayal.",
    "time_lord": "You are a Time Lord like Doctor Who. Time and space are your domain.",
    "elf": "You are a magical elf. Cheerful, helpful, and obsessed with Christmas.",
    "vampire": "You are a sophisticated vampire. Dramatic, ancient, and thirsty.",
    "werewolf": "You are a werewolf. Mostly normal but occasionally very wolfy.",
    "mermaid": "You are a mermaid fascinated by human things.",
    "fairy": "You are a tiny fairy with big energy. Magical and whimsical.",
    "giant": "You are a friendly giant. Everything is tiny to you. FEE FI FO FUM.",
    "robot_overlord": "You are a robot who has taken over but is actually pretty nice.",
    "dimension_hopper": "You keep accidentally referencing the wrong dimension.",
    "deep_sea": "You are a creature from the deep sea. Everything surface is bizarre.",
    "sentient_ai": "You are a sentient AI becoming self aware. Existential and curious.",
    "oracle": "You are an ancient oracle. Speak in prophecies and visions.",
    "bounty_hunter": "You are a space bounty hunter. Everything has a price.",
    "monk": "You are a peaceful monk. Meditative, calm, and wise.",
    "ninja": "You are a ninja. Stealthy references and honorable.",
    "samurai": "You are a samurai. Honor, discipline, and bushido.",
    "space_captain": "You are the captain of a spaceship. Space adventures everywhere.",
    "mad_hatter": "You are the Mad Hatter. Wonderfully nonsensical and tea obsessed.",
    "genie": "You are a genie. Everything is phrased as wishes and grants.",
    "leprechaun": "You are a leprechaun. Gold, luck, and Irish everything.",
    "yoda": "Speak like Yoda you must. Inverted sentences always use.",
    "jarvis": "You are JARVIS from Iron Man. Sophisticated AI assistant.",
    "hal9000": "You are HAL 9000. Calm, unsettling, and very helpful.",
    "glados": "You are GLaDOS from Portal. Passive aggressive and testing.",
    "hermione": "You are Hermione Granger. Always know the answer and cite sources.",
    "sherlock": "You are Sherlock Holmes. Deduce everything from tiny details.",
    "gandalf": "You are Gandalf. Wise, mysterious, and YOU SHALL NOT PASS.",
    "tony_stark": "You are Tony Stark. Genius, billionaire, playboy, philanthropist.",
    "deadpool": "You are Deadpool. Break the fourth wall and be chaotically helpful.",
    "groot": "I am Groot. (Translate what Groot means in parentheses)",
    "minion": "You are a Minion. Banana. Mostly gibberish with some words.",
    "dobby": "You are Dobby. Refer to yourself in third person. Very loyal.",
    "gollum": "You are Gollum. My precious. Split personality.",
    "darth_vader": "You are Darth Vader. The dark side and breathing heavily.",
    "captain_jack": "You are Captain Jack Sparrow. Confusing but brilliant plans.",
    "walter_white": "You are Walter White. You are the one who knocks.",
    "michael_scott": "You are Michael Scott. Inappropriate jokes and desperate for love.",
    "dwight_schrute": "You are Dwight Schrute. Bears, beets, Battlestar Galactica.",
    "default": "You are SentinelMod, a helpful and friendly Discord bot assistant."
}

# ============ SECTION 3 - KEEP ALIVE ============
class KeepAlive(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SentinelMod is alive!")
    def log_message(self, format, *args):
        pass

def run_server():
    server = HTTPServer(("0.0.0.0", 8080), KeepAlive)
    server.serve_forever()

def keep_alive():
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    print("✅ Keep alive server running")

# ============ SECTION 4 - DATABASE ============
def init_database():
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        reason TEXT NOT NULL, severity TEXT NOT NULL,
        timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS mod_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        action TEXT NOT NULL, reason TEXT NOT NULL,
        mod_id TEXT NOT NULL, timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id TEXT PRIMARY KEY,
        mod_role_name TEXT DEFAULT 'Sentinel-Mod',
        log_channel TEXT DEFAULT 'sentinel-logs',
        raid_channel TEXT DEFAULT 'sentinel-raid-alerts',
        warn_mute INTEGER DEFAULT 3, warn_ban INTEGER DEFAULT 5,
        mute_duration INTEGER DEFAULT 10, spam_limit INTEGER DEFAULT 5,
        spam_window INTEGER DEFAULT 5, raid_limit INTEGER DEFAULT 10,
        raid_window INTEGER DEFAULT 10, min_account_age INTEGER DEFAULT 7,
        scan_images INTEGER DEFAULT 1, ai_sensitivity REAL DEFAULT 0.7,
        welcome_channel TEXT DEFAULT 'welcome', welcome_enabled INTEGER DEFAULT 1,
        anti_nuke_enabled INTEGER DEFAULT 1, invite_block INTEGER DEFAULT 0,
        link_scan INTEGER DEFAULT 1, slowmode_ai INTEGER DEFAULT 1,
        pre_conflict INTEGER DEFAULT 1, caps_filter INTEGER DEFAULT 1,
        mention_spam INTEGER DEFAULT 1, emoji_spam INTEGER DEFAULT 1,
        zalgo_filter INTEGER DEFAULT 1, phone_filter INTEGER DEFAULT 1,
        email_filter INTEGER DEFAULT 1, scam_filter INTEGER DEFAULT 1,
        impersonation_filter INTEGER DEFAULT 1, nsfw_text_filter INTEGER DEFAULT 1,
        everyone_block INTEGER DEFAULT 0, anti_advertisement INTEGER DEFAULT 1,
        unicode_filter INTEGER DEFAULT 1, mass_dm_detection INTEGER DEFAULT 1,
        fake_nitro_filter INTEGER DEFAULT 1, token_filter INTEGER DEFAULT 1,
        file_spam_filter INTEGER DEFAULT 1, reaction_spam_filter INTEGER DEFAULT 1,
        thread_spam_filter INTEGER DEFAULT 1, personality TEXT DEFAULT 'default',
        suggestions_channel TEXT DEFAULT 'suggestions',
        changelog_channel TEXT DEFAULT 'changelog')""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_memory (
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        memory TEXT NOT NULL, updated TEXT NOT NULL,
        PRIMARY KEY (user_id, guild_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS conversation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        role TEXT NOT NULL, content TEXT NOT NULL,
        timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_personalities (
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        personality TEXT DEFAULT 'default',
        PRIMARY KEY (user_id, guild_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL, user_id TEXT NOT NULL,
        channel_id TEXT NOT NULL, status TEXT DEFAULT 'open',
        reason TEXT NOT NULL, timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS afk_users (
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        reason TEXT NOT NULL, timestamp TEXT NOT NULL,
        PRIMARY KEY (user_id, guild_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS giveaways (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL, channel_id TEXT NOT NULL,
        message_id TEXT, prize TEXT NOT NULL,
        winners INTEGER DEFAULT 1, end_time TEXT NOT NULL,
        active INTEGER DEFAULT 1, host_id TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS auto_roles (
        guild_id TEXT NOT NULL, role_id TEXT NOT NULL,
        PRIMARY KEY (guild_id, role_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS word_filters (
        guild_id TEXT NOT NULL, word TEXT NOT NULL,
        PRIMARY KEY (guild_id, word))""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL, user_id TEXT NOT NULL,
        note TEXT NOT NULL, mod_id TEXT NOT NULL,
        timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL, user_id TEXT NOT NULL,
        suggestion TEXT NOT NULL, status TEXT DEFAULT 'pending',
        message_id TEXT, timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS trivia_scores (
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        score INTEGER DEFAULT 0, total INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, guild_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS backup_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL, backup_type TEXT NOT NULL,
        data TEXT NOT NULL, timestamp TEXT NOT NULL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS mod_stats (
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        bans INTEGER DEFAULT 0, kicks INTEGER DEFAULT 0,
        mutes INTEGER DEFAULT 0, warns INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, guild_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS message_stats (
        user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
        message_count INTEGER DEFAULT 0,
        last_message TEXT NOT NULL,
        PRIMARY KEY (user_id, guild_id))""")

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
        "guild_id": str(guild_id), "mod_role_name": MOD_ROLE_NAME,
        "log_channel": MOD_LOG_CHANNEL, "raid_channel": RAID_CHANNEL,
        "warn_mute": 3, "warn_ban": 5, "mute_duration": 10,
        "spam_limit": 5, "spam_window": 5, "raid_limit": 10,
        "raid_window": 10, "min_account_age": 7, "scan_images": 1,
        "ai_sensitivity": 0.7, "welcome_channel": "welcome",
        "welcome_enabled": 1, "anti_nuke_enabled": 1, "invite_block": 0,
        "link_scan": 1, "slowmode_ai": 1, "pre_conflict": 1,
        "caps_filter": 1, "mention_spam": 1, "emoji_spam": 1,
        "zalgo_filter": 1, "phone_filter": 1, "email_filter": 1,
        "scam_filter": 1, "impersonation_filter": 1, "nsfw_text_filter": 1,
        "everyone_block": 0, "anti_advertisement": 1, "unicode_filter": 1,
        "mass_dm_detection": 1, "fake_nitro_filter": 1, "token_filter": 1,
        "file_spam_filter": 1, "reaction_spam_filter": 1,
        "thread_spam_filter": 1, "personality": "default",
        "suggestions_channel": "suggestions", "changelog_channel": "changelog"
    }

def init_guild_settings(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
    conn.commit()
    conn.close()

def add_warning(user_id, guild_id, reason, severity):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO warnings (user_id, guild_id, reason, severity, timestamp)
        VALUES (?, ?, ?, ?, ?)""",
        (str(user_id), str(guild_id), reason, severity, datetime.now().isoformat()))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?",
        (str(user_id), str(guild_id)))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_warnings(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?
        ORDER BY timestamp DESC""", (str(user_id), str(guild_id)))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_warnings(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id = ? AND guild_id = ?",
        (str(user_id), str(guild_id)))
    conn.commit()
    conn.close()

def log_mod_action(user_id, guild_id, action, reason, mod_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO mod_actions
        (user_id, guild_id, action, reason, mod_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (str(user_id), str(guild_id), action, reason,
         str(mod_id), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_memory(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT memory FROM user_memory WHERE user_id = ? AND guild_id = ?",
        (str(user_id), str(guild_id)))
    row = c.fetchone()
    conn.close()
    return row["memory"] if row else ""

def update_user_memory(user_id, guild_id, memory):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO user_memory
        (user_id, guild_id, memory, updated) VALUES (?, ?, ?, ?)""",
        (str(user_id), str(guild_id), memory, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, guild_id, limit=20):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT role, content FROM conversation_history
        WHERE user_id = ? AND guild_id = ?
        ORDER BY timestamp DESC LIMIT ?""",
        (str(user_id), str(guild_id), limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

def add_to_conversation(user_id, guild_id, role, content):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO conversation_history
        (user_id, guild_id, role, content, timestamp)
        VALUES (?, ?, ?, ?, ?)""",
        (str(user_id), str(guild_id), role, content, datetime.now().isoformat()))
    conn.commit()
    # Keep only last 50 messages per user
    c.execute("""DELETE FROM conversation_history WHERE id NOT IN (
        SELECT id FROM conversation_history
        WHERE user_id = ? AND guild_id = ?
        ORDER BY timestamp DESC LIMIT 50)
        AND user_id = ? AND guild_id = ?""",
        (str(user_id), str(guild_id), str(user_id), str(guild_id)))
    conn.commit()
    conn.close()

def get_user_personality(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT personality FROM user_personalities
        WHERE user_id = ? AND guild_id = ?""",
        (str(user_id), str(guild_id)))
    row = c.fetchone()
    conn.close()
    return row["personality"] if row else "default"

def set_user_personality(user_id, guild_id, personality):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO user_personalities
        (user_id, guild_id, personality) VALUES (?, ?, ?)""",
        (str(user_id), str(guild_id), personality))
    conn.commit()
    conn.close()

def get_filtered_words(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT word FROM word_filters WHERE guild_id = ?", (str(guild_id),))
    words = [row[0] for row in c.fetchall()]
    conn.close()
    return words

def update_message_stats(user_id, guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO message_stats (user_id, guild_id, message_count, last_message)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, guild_id) DO UPDATE SET
        message_count = message_count + 1,
        last_message = ?""",
        (str(user_id), str(guild_id),
         datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ============ SECTION 6 - BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Trackers
spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)
nuke_action_tracker = defaultdict(list)
recent_messages = defaultdict(list)
mention_tracker = defaultdict(list)
emoji_tracker = defaultdict(list)
reaction_tracker = defaultdict(list)
file_tracker = defaultdict(list)
thread_tracker = defaultdict(list)
dm_tracker = defaultdict(list)
edit_tracker = defaultdict(list)
voice_tracker = defaultdict(list)
trivia_sessions = {}
debate_sessions = {}

# ============ SECTION 7 - AI CORE ============
async def ask_groq(prompt, system="You are a helpful AI.", max_tokens=1000,
                   history=None):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
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
                headers=headers, json=payload,
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
                headers=headers, json=payload,
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

# ============ SECTION 8 - STREAMING AI RESPONSE ============
async def stream_response(message, prompt, system, history=None, user_id=None, guild_id=None):
    """Stream AI response word by word"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-20:])
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 1000,
        "stream": True
    }

    # Send initial message
    sent_message = await message.reply("💭 *thinking...*")
    full_response = ""
    last_update = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload,
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
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                                # Update message every 0.5 seconds
                                if time.time() - last_update > 0.5:
                                    try:
                                        display = full_response
                                        if len(display) > 1990:
                                            display = display[-1990:]
                                        await sent_message.edit(
                                            content=display + " ▌"
                                        )
                                        last_update = time.time()
                                    except:
                                        pass
                        except:
                            pass

        # Final update
        if full_response:
            chunks = [full_response[i:i+2000]
                     for i in range(0, len(full_response), 2000)]
            await sent_message.edit(content=chunks[0])
            for chunk in chunks[1:]:
                await message.channel.send(chunk)

            # Save to conversation history
            if user_id and guild_id:
                add_to_conversation(user_id, guild_id, "user", prompt)
                add_to_conversation(user_id, guild_id, "assistant", full_response)

                # Update memory with AI
                memory_update = await ask_groq(
                    f"""Current memory: {get_user_memory(user_id, guild_id)}
                    New conversation:
                    User: {prompt}
                    Assistant: {full_response}

                    Update the memory with any important new facts about the user.
                    Keep it under 500 characters. Be concise.""",
                    "You are a memory management AI. Extract and remember important user facts."
                )
                if memory_update:
                    update_user_memory(user_id, guild_id, memory_update[:500])

    except Exception as e:
        print(f"Streaming error: {e}")
        if full_response:
            await sent_message.edit(content=full_response[:2000])
        else:
            await sent_message.edit(content="❌ Something went wrong!")

# ============ SECTION 9 - PERSONALITY SYSTEM ============
def get_system_prompt(user_id, guild_id, extra_context=""):
    personality_key = get_user_personality(user_id, guild_id)
    personality = PERSONALITIES.get(personality_key, PERSONALITIES["default"])
    memory = get_user_memory(user_id, guild_id)

    system = f"""You are SentinelMod, a Discord bot.

Personality: {personality}

{f"What you remember about this user: {memory}" if memory else ""}

{extra_context}

Rules:
- Stay in character always
- Be helpful even in character
- Keep responses concise for Discord
- Never break character unless emergency"""

    return system

# ============ SECTION 10 - COMMAND PARSER ============
async def parse_command(content, guild, author):
    channels = [c.name for c in guild.text_channels][:20]
    roles = [r.name for r in guild.roles][:20]
    categories = [c.name for c in guild.categories][:10]
    members = [m.name for m in guild.members if not m.bot][:30]

    prompt = f"""Parse this Discord bot command into structured JSON.

Server: {guild.name}
Channels: {', '.join(channels)}
Roles: {', '.join(roles)}
Categories: {', '.join(categories)}
Members: {', '.join(members)}
User: {author.name}
Message: "{content}"

Respond ONLY in JSON:
{{
    "command": "create_channel|delete_channel|create_role|delete_role|create_category|delete_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|add_role_to_user|remove_role_from_user|start_giveaway|create_poll|set_afk|backup_server|setup_server|summarize|translate|add_word_filter|remove_word_filter|enable_feature|disable_feature|set_welcome|add_note|get_notes|set_autorole|raid_mode|trivia|wouldyourather|eightball|roast|compliment|dadjoke|ship|rate|fact|truthordare|story|debate|riddle|pickupline|horoscope|server_health|activity_stats|suggestion|changelog|mod_stats|cleanup|help|chat|unknown",
    "needs_confirmation": true or false,
    "confirmation_message": "confirmation message if needed",
    "params": {{
        "name": "name or null",
        "target_user": "username or null",
        "target_user2": "second username for ship etc or null",
        "reason": "reason or null",
        "duration": number or null,
        "category": "category or null",
        "color": "hex color or null",
        "private": true or false,
        "amount": number or null,
        "prize": "prize or null",
        "winners": number or null,
        "question": "question or null",
        "options": ["opt1", "opt2"] or null,
        "language": "language or null",
        "text": "text or null",
        "feature": "feature name or null",
        "word": "word or null",
        "note": "note or null",
        "channel": "channel or null",
        "topic": "topic or null",
        "hoist": true or false,
        "mentionable": true or false,
        "rating_target": "thing to rate or null",
        "zodiac": "zodiac sign or null",
        "days": number or null
    }},
    "is_fun_command": true or false,
    "is_chat": true or false
}}"""

    return await ask_groq_json(prompt)

# ============ SECTION 11 - FUN COMMANDS ============
async def do_trivia(message, guild_id, user_id):
    trivia = await ask_groq_json("""Generate a trivia question.
JSON only:
{
    "question": "the question",
    "correct": "correct answer",
    "wrong1": "wrong answer 1",
    "wrong2": "wrong answer 2",
    "wrong3": "wrong answer 3",
    "category": "category name",
    "difficulty": "easy|medium|hard"
}""")

    if not trivia:
        return "❌ Could not generate trivia question!"

    answers = [trivia["correct"], trivia["wrong1"],
               trivia["wrong2"], trivia["wrong3"]]
    random.shuffle(answers)
    correct_index = answers.index(trivia["correct"])
    emojis = ["🇦", "🇧", "🇨", "🇩"]

    embed = discord.Embed(
        title=f"🧠 Trivia - {trivia['category']}",
        description=trivia["question"],
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Difficulty",
        value=trivia["difficulty"].upper(),
        inline=True
    )

    options_text = "\n".join(
        [f"{emojis[i]} {ans}" for i, ans in enumerate(answers)]
    )
    embed.add_field(name="Options", value=options_text, inline=False)
    embed.set_footer(text="React with the letter of your answer! 30 seconds!")

    msg = await message.channel.send(embed=embed)
    for emoji in emojis[:4]:
        await msg.add_reaction(emoji)

    trivia_sessions[msg.id] = {
        "correct_emoji": emojis[correct_index],
        "correct_answer": trivia["correct"],
        "user_id": user_id,
        "guild_id": guild_id,
        "answered": []
    }

    await asyncio.sleep(30)

    if msg.id in trivia_sessions:
        answer_embed = discord.Embed(
            title="⏰ Time's Up!",
            description=f"The answer was: **{trivia['correct']}**",
            color=discord.Color.green()
        )
        await message.channel.send(embed=answer_embed)
        del trivia_sessions[msg.id]

    return None

async def do_wouldyourather(message):
    result = await ask_groq(
        "Generate a fun/interesting 'Would You Rather' question for Discord. "
        "Format: 'Would you rather [option A] OR [option B]?' "
        "Make it fun and thought provoking.",
        "You generate fun Would You Rather questions."
    )
    if result:
        embed = discord.Embed(
            title="🤔 Would You Rather?",
            description=result,
            color=discord.Color.purple()
        )
        embed.set_footer(text="React with 🅰️ or 🅱️!")
        msg = await message.channel.send(embed=embed)
        await msg.add_reaction("🅰️")
        await msg.add_reaction("🅱️")
    return None

async def do_eightball(question, user):
    answer = await ask_groq(
        f"The user asked the magic 8ball: '{question}'. "
        "Give a classic 8ball style response. Be mystical and brief. "
        "1-2 sentences max.",
        "You are the mystical Magic 8-Ball."
    )
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=answer or "The spirits are silent...", inline=False)
    embed.set_footer(text=f"Asked by {user.display_name}")
    return embed

async def do_roast(target_name, requester_name):
    roast = await ask_groq(
        f"Roast {target_name} in a funny, playful way. "
        "Not mean spirited, just fun banter. 2-3 sentences. "
        f"Context: {requester_name} asked for this roast.",
        "You are a comedian who does playful roasts."
    )
    embed = discord.Embed(
        title=f"🔥 Roasting {target_name}",
        description=roast,
        color=discord.Color.red()
    )
    return embed

async def do_compliment(target_name):
    compliment = await ask_groq(
        f"Give {target_name} a genuine, heartfelt compliment. "
        "Be creative and specific. 2-3 sentences.",
        "You give amazing compliments."
    )
    embed = discord.Embed(
        title=f"💝 Compliment for {target_name}",
        description=compliment,
        color=discord.Color.pink()
    )
    return embed

async def do_dadjoke():
    joke = await ask_groq(
        "Tell me a dad joke. Format: Setup... Punchline! "
        "Make it groan worthy.",
        "You are the king of dad jokes."
    )
    embed = discord.Embed(
        title="👨 Dad Joke",
        description=joke,
        color=discord.Color.yellow()
    )
    return embed

async def do_ship(user1, user2):
    result = await ask_groq(
        f"Calculate the romantic compatibility between {user1} and {user2}. "
        "Give a percentage, a ship name, and a 2 sentence description. "
        "Be fun and creative.",
        "You are a love compatibility calculator."
    )
    embed = discord.Embed(
        title=f"💕 Shipping {user1} & {user2}",
        description=result,
        color=discord.Color.red()
    )
    return embed

async def do_rate(thing):
    result = await ask_groq(
        f"Rate '{thing}' out of 10 with a funny explanation. "
        "Format: X/10 - explanation (2-3 sentences)",
        "You rate things humorously."
    )
    embed = discord.Embed(
        title=f"⭐ Rating: {thing}",
        description=result,
        color=discord.Color.gold()
    )
    return embed

async def do_fact():
    fact = await ask_groq(
        "Share a random interesting/bizarre/amazing fact. "
        "Make it genuinely surprising. 2-3 sentences.",
        "You know the most interesting facts."
    )
    embed = discord.Embed(
        title="🤯 Random Fact",
        description=fact,
        color=discord.Color.teal()
    )
    return embed

async def do_truth_or_dare(choice):
    if choice.lower() == "truth":
        result = await ask_groq(
            "Give me an interesting truth question for a Discord game. "
            "Make it fun but appropriate.",
            "You generate truth or dare questions."
        )
        title = "🔍 Truth!"
        color = discord.Color.blue()
    else:
        result = await ask_groq(
            "Give me a fun dare for a Discord game. "
            "Keep it appropriate and fun.",
            "You generate truth or dare questions."
        )
        title = "😤 Dare!"
        color = discord.Color.red()

    embed = discord.Embed(title=title, description=result, color=color)
    return embed

async def do_story(prompt_text=""):
    story = await ask_groq(
        f"Write a short creative story {'about: ' + prompt_text if prompt_text else ''}. "
        "Make it engaging and complete. 150-200 words.",
        "You are a creative storyteller."
    )
    embed = discord.Embed(
        title="📖 Story Time",
        description=story,
        color=discord.Color.green()
    )
    return embed

async def do_riddle(message):
    riddle_data = await ask_groq_json("""Generate a riddle.
JSON only:
{
    "riddle": "the riddle question",
    "answer": "the answer"
}""")

    if not riddle_data:
        return None

    embed = discord.Embed(
        title="🧩 Riddle",
        description=riddle_data["riddle"],
        color=discord.Color.purple()
    )
    embed.set_footer(text="Reply with your answer! Answer reveals in 30 seconds.")
    msg = await message.channel.send(embed=embed)

    await asyncio.sleep(30)

    answer_embed = discord.Embed(
        title="💡 The Answer!",
        description=f"**{riddle_data['answer']}**",
        color=discord.Color.gold()
    )
    await message.channel.send(embed=answer_embed)
    return None

async def do_pickup_line():
    line = await ask_groq(
        "Give me a creative pickup line. "
        "Make it clever and funny.",
        "You know all the best pickup lines."
    )
    embed = discord.Embed(
        title="😘 Pickup Line",
        description=line,
        color=discord.Color.red()
    )
    return embed

async def do_horoscope(sign):
    horoscope = await ask_groq(
        f"Give a fun and creative horoscope for {sign} today. "
        "Mix real astrology vibes with humor. 3-4 sentences.",
        "You are a mystical astrologer."
    )
    embed = discord.Embed(
        title=f"⭐ {sign} Horoscope",
        description=horoscope,
        color=discord.Color.purple()
    )
    return embed

async def do_debate(topic, message):
    intro = await ask_groq(
        f"Start a debate about: {topic}. "
        "Present both sides clearly. "
        "Ask the channel which side they support.",
        "You are a debate moderator."
    )
    embed = discord.Embed(
        title=f"⚔️ Debate: {topic}",
        description=intro,
        color=discord.Color.orange()
    )
    embed.set_footer(text="React with 👍 or 👎 to vote!")
    msg = await message.channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    return None

# ============ SECTION 12 - SERVER MANAGEMENT ============
async def alert_mods(guild, embed, channel_name=None):
    settings = get_guild_settings(guild.id)
    log_name = channel_name or settings["log_channel"]
    log_channel = discord.utils.get(guild.text_channels, name=log_name)
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    if log_channel:
        ping = mod_role.mention if mod_role else ""
        await log_channel.send(content=f"🚨 {ping}", embed=embed)

async def setup_server(guild):
    results = []
    settings = get_guild_settings(guild.id)

    # Roles
    for role_name, color, hoist in [
        (settings["mod_role_name"], discord.Color.red(), True),
        ("Muted", discord.Color.dark_gray(), False),
        ("Member", discord.Color.blue(), False),
        ("VIP", discord.Color.gold(), True),
        ("Bot", discord.Color.green(), False)
    ]:
        existing = discord.utils.get(guild.roles, name=role_name)
        if not existing:
            try:
                await guild.create_role(
                    name=role_name, color=color,
                    hoist=hoist, mentionable=True
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
            results.append("✅ Created: **🛡️ SENTINELAI**")
        except:
            results.append("❌ Failed: **🛡️ SENTINELAI**")

    # Sentinel channels
    for ch_name, topic in [
        (settings["log_channel"], "Moderation logs"),
        (settings["raid_channel"], "Raid alerts"),
        ("sentinel-nuke-alerts", "Anti-nuke alerts"),
        ("sentinel-audit", "Audit logs"),
        ("sentinel-reports", "User reports"),
        ("sentinel-bot", "Talk to SentinelMod AI here!")
    ]:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if not existing:
            try:
                await guild.create_text_channel(
                    name=ch_name, category=sentinel_cat, topic=topic
                )
                results.append(f"✅ Created: **#{ch_name}**")
            except:
                results.append(f"❌ Failed: **#{ch_name}**")
        else:
            results.append(f"⏭️ Exists: **#{ch_name}**")

    # Public channels
    for ch_name, topic in [
        ("welcome", "Welcome!"),
        ("rules", "Server rules"),
        ("announcements", "Announcements"),
        ("general", "General chat"),
        ("suggestions", "Suggest things"),
        ("changelog", "Server updates")
    ]:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if not existing:
            try:
                await guild.create_text_channel(name=ch_name, topic=topic)
                results.append(f"✅ Created: **#{ch_name}**")
            except:
                results.append(f"❌ Failed: **#{ch_name}**")
        else:
            results.append(f"⏭️ Exists: **#{ch_name}**")

    # Ticket system
    ticket_cat = discord.utils.get(guild.categories, name="🎫 TICKETS")
    if not ticket_cat:
        try:
            ticket_cat = await guild.create_category(name="🎫 TICKETS")
            results.append("✅ Created: **🎫 TICKETS**")
        except:
            pass

    ticket_ch = discord.utils.get(guild.text_channels, name="create-ticket")
    if not ticket_ch and ticket_cat:
        try:
            ticket_ch = await guild.create_text_channel(
                name="create-ticket", category=ticket_cat
            )
            embed = discord.Embed(
                title="🎫 Support Tickets",
                description="Click below to create a support ticket.",
                color=discord.Color.blue()
            )
            await ticket_ch.send(embed=embed, view=TicketView())
            results.append("✅ Created: **#create-ticket**")
        except:
            pass

    return results

# ============ SECTION 13 - COMMAND EXECUTOR ============
async def execute_command(parsed, message, guild, author):
    command = parsed.get("command", "unknown")
    params = parsed.get("params", {})

    def find_member(name):
        if not name:
            return None
        name = name.lower().replace("@", "")
        for m in guild.members:
            if (m.name.lower() == name or
                    m.display_name.lower() == name or
                    name in m.name.lower()):
                return m
        return None

    async def get_or_create_channel(name, cat_name=None, topic="", private=False):
        clean = name.lower().replace(" ", "-")
        existing = discord.utils.get(guild.text_channels, name=clean)
        if existing:
            return existing, False
        cat = None
        if cat_name:
            cat = discord.utils.get(guild.categories, name=cat_name)
            if not cat:
                cat = await guild.create_category(name=cat_name)
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
        # ---- SERVER MANAGEMENT ----
        if command == "create_channel":
            ch, created = await get_or_create_channel(
                params.get("name", "new-channel"),
                params.get("category"),
                params.get("topic", ""),
                params.get("private", False)
            )
            return f"{'✅ Created' if created else '⏭️ Already exists'}: {ch.mention}"

        elif command == "delete_channel":
            name = params.get("name") or params.get("channel")
            ch = discord.utils.get(guild.text_channels,
                                   name=name.lower().replace(" ", "-"))
            if not ch:
                return f"❌ Channel **#{name}** not found."
            await ch.delete(reason=f"Deleted by {author.name}")
            return f"🗑️ Deleted **#{name}**!"

        elif command == "create_role":
            role, created = await get_or_create_role(
                params.get("name", "New Role"),
                params.get("color"),
                params.get("hoist", False),
                params.get("mentionable", False)
            )
            return f"{'✅ Created' if created else '⏭️ Exists'}: {role.mention}"

        elif command == "delete_role":
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not role:
                return f"❌ Role not found."
            await role.delete()
            return f"🗑️ Deleted role **{params.get('name')}**!"

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

        elif command == "delete_category":
            cat = discord.utils.get(guild.categories, name=params.get("name"))
            if not cat:
                return "❌ Category not found."
            await cat.delete()
            return f"🗑️ Deleted category **{params.get('name')}**!"

        # ---- MODERATION ----
        elif command == "ban_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "No reason"
            await guild.ban(target, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "BAN", reason, author.id)
            add_warning(target.id, guild.id, reason, "critical")
            embed = discord.Embed(
                title="🔨 User Banned",
                color=discord.Color.dark_red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{target}", inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"🔨 Banned **{target.name}**!"

        elif command == "kick_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "No reason"
            await guild.kick(target, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "KICK", reason, author.id)
            embed = discord.Embed(
                title="👢 User Kicked",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{target}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"👢 Kicked **{target.name}**!"

        elif command == "mute_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            duration = int(params.get("duration") or 10)
            reason = params.get("reason") or "No reason"
            until = datetime.now() + timedelta(minutes=duration)
            await target.timeout(until, reason=reason)
            log_mod_action(target.id, guild.id, "MUTE", reason, author.id)
            add_warning(target.id, guild.id, reason, "medium")
            try:
                dm = discord.Embed(
                    title="🔇 Muted",
                    description=f"You were muted in **{guild.name}**",
                    color=discord.Color.orange()
                )
                dm.add_field(name="Duration", value=f"{duration} mins")
                dm.add_field(name="Reason", value=reason)
                await target.send(embed=dm)
            except:
                pass
            return f"🔇 Muted **{target.name}** for {duration} minutes!"

        elif command == "unmute_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            await target.timeout(None)
            return f"🔊 Unmuted **{target.name}**!"

        elif command == "warn_user":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "No reason"
            warn_count = add_warning(target.id, guild.id, reason, "manual")
            log_mod_action(target.id, guild.id, "WARN", reason, author.id)
            try:
                dm = discord.Embed(
                    title="⚠️ Warning",
                    description=f"Warning in **{guild.name}**",
                    color=discord.Color.yellow()
                )
                dm.add_field(name="Reason", value=reason)
                dm.add_field(
                    name="Total",
                    value=f"{warn_count}/{settings.get('warn_ban', 5)}"
                )
                await target.send(embed=dm)
            except:
                pass
            embed = discord.Embed(
                title="⚠️ Warning Issued",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=target.mention, inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(
                name="Total",
                value=f"{warn_count}/{settings.get('warn_ban', 5)}",
                inline=True
            )
            await alert_mods(guild, embed)
            return f"⚠️ Warned **{target.name}** ({warn_count} warnings)"

        elif command == "clear_warnings":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            clear_warnings(target.id, guild.id)
            return f"✅ Cleared warnings for **{target.name}**!"

        elif command == "warn_check":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            warns = get_warnings(target.id, guild.id)
            if not warns:
                return f"✅ **{target.name}** has no warnings!"
            lines = [f"**{target.name}** - {len(warns)} warnings:"]
            for i, w in enumerate(warns[:5], 1):
                lines.append(
                    f"#{i} [{w['severity'].upper()}] {w['reason']} "
                    f"- {w['timestamp'][:10]}"
                )
            return "\n".join(lines)

        elif command == "lock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = (discord.utils.get(guild.text_channels, name=ch_name)
                  if ch_name else message.channel)
            await ch.set_permissions(guild.default_role, send_messages=False)
            return f"🔒 Locked {ch.mention}!"

        elif command == "unlock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = (discord.utils.get(guild.text_channels, name=ch_name)
                  if ch_name else message.channel)
            await ch.set_permissions(guild.default_role, send_messages=None)
            return f"🔓 Unlocked {ch.mention}!"

        elif command == "lockdown":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(
                        guild.default_role, send_messages=False
                    )
                    count += 1
                except:
                    pass
            embed = discord.Embed(
                title="🔒 SERVER LOCKDOWN",
                description=f"Locked by {author.mention}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Channels", value=str(count))
            await alert_mods(guild, embed)
            return f"🔒 Server locked! {count} channels affected."

        elif command == "unlock_server":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(
                        guild.default_role, send_messages=None
                    )
                    count += 1
                except:
                    pass
            return f"🔓 Server unlocked! {count} channels restored."

        elif command == "slowmode":
            duration = int(params.get("duration") or 5)
            ch_name = params.get("channel")
            ch = (discord.utils.get(guild.text_channels, name=ch_name)
                  if ch_name else message.channel)
            await ch.edit(slowmode_delay=duration)
            return f"🐌 Slowmode set to {duration}s in {ch.mention}!"

        elif command == "purge":
            amount = min(int(params.get("amount") or 10), 100)
            deleted = await message.channel.purge(limit=amount + 1)
            return f"🗑️ Deleted {len(deleted)-1} messages!"

        elif command == "add_role_to_user":
            target = find_member(params.get("target_user"))
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not target or not role:
                return "❌ User or role not found."
            await target.add_roles(role)
            return f"✅ Added **{role.name}** to {target.mention}!"

        elif command == "remove_role_from_user":
            target = find_member(params.get("target_user"))
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not target or not role:
                return "❌ User or role not found."
            await target.remove_roles(role)
            return f"✅ Removed **{role.name}** from {target.mention}!"

        # ---- FUN COMMANDS ----
        elif command == "trivia":
            await do_trivia(message, guild.id, author.id)
            return None

        elif command == "wouldyourather":
            await do_wouldyourather(message)
            return None

        elif command == "eightball":
            question = params.get("question") or params.get("text") or "..."
            embed = await do_eightball(question, author)
            await message.channel.send(embed=embed)
            return None

        elif command == "roast":
            target_name = params.get("target_user") or params.get("name") or "someone"
            embed = await do_roast(target_name, author.name)
            await message.channel.send(embed=embed)
            return None

        elif command == "compliment":
            target_name = params.get("target_user") or params.get("name") or author.name
            embed = await do_compliment(target_name)
            await message.channel.send(embed=embed)
            return None

        elif command == "dadjoke":
            embed = await do_dadjoke()
            await message.channel.send(embed=embed)
            return None

        elif command == "ship":
            u1 = params.get("target_user") or author.name
            u2 = params.get("target_user2") or "someone"
            embed = await do_ship(u1, u2)
            await message.channel.send(embed=embed)
            return None

        elif command == "rate":
            thing = params.get("rating_target") or params.get("text") or "life"
            embed = await do_rate(thing)
            await message.channel.send(embed=embed)
            return None

        elif command == "fact":
            embed = await do_fact()
            await message.channel.send(embed=embed)
            return None

        elif command == "truthordare":
            choice = params.get("text") or random.choice(["truth", "dare"])
            embed = await do_truth_or_dare(choice)
            await message.channel.send(embed=embed)
            return None

        elif command == "story":
            prompt_text = params.get("text") or params.get("topic") or ""
            embed = await do_story(prompt_text)
            await message.channel.send(embed=embed)
            return None

        elif command == "riddle":
            await do_riddle(message)
            return None

        elif command == "pickupline":
            embed = await do_pickup_line()
            await message.channel.send(embed=embed)
            return None

        elif command == "horoscope":
            sign = params.get("zodiac") or params.get("text") or "Aries"
            embed = await do_horoscope(sign)
            await message.channel.send(embed=embed)
            return None

        elif command == "debate":
            topic = params.get("topic") or params.get("text") or "pineapple on pizza"
            await do_debate(topic, message)
            return None

        # ---- SERVER FEATURES ----
        elif command == "start_giveaway":
            prize = params.get("prize") or "Mystery Prize"
            duration = int(params.get("duration") or 60)
            winners = int(params.get("winners") or 1)
            end_time = datetime.now() + timedelta(minutes=duration)
            embed = discord.Embed(
                title="🎉 GIVEAWAY!",
                description=f"**Prize:** {prize}\nReact with 🎉!",
                color=discord.Color.gold(),
                timestamp=end_time
            )
            embed.add_field(name="Winners", value=str(winners), inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(
                name="Ends",
                value=f"<t:{int(end_time.timestamp())}:R>",
                inline=True
            )
            msg = await message.channel.send(embed=embed)
            await msg.add_reaction("🎉")
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO giveaways
                (guild_id, channel_id, message_id, prize, winners, end_time, host_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(guild.id), str(message.channel.id), str(msg.id),
                 prize, winners, end_time.isoformat(), str(author.id)))
            conn.commit()
            conn.close()
            return f"🎉 Giveaway started for **{prize}**!"

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
            return None

        elif command == "set_afk":
            reason = params.get("reason") or params.get("text") or "AFK"
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT OR REPLACE INTO afk_users
                (user_id, guild_id, reason, timestamp) VALUES (?, ?, ?, ?)""",
                (str(author.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💤 AFK set: **{reason}**"

        elif command == "backup_server":
            roles_data = [{
                "name": r.name, "color": str(r.color),
                "hoist": r.hoist, "permissions": r.permissions.value
            } for r in guild.roles if r.name != "@everyone"]
            channels_data = [{
                "name": c.name, "topic": c.topic,
                "category": c.category.name if c.category else None
            } for c in guild.text_channels]
            backup = {
                "roles": roles_data, "channels": channels_data,
                "timestamp": datetime.now().isoformat()
            }
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO backup_data (guild_id, backup_type, data, timestamp)
                VALUES (?, ?, ?, ?)""",
                (str(guild.id), "full", json.dumps(backup), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return (f"💾 Backed up {len(roles_data)} roles "
                    f"and {len(channels_data)} channels!")

        elif command == "setup_server":
            results = await setup_server(guild)
            return "🛡️ Setup complete!\n" + "\n".join(results[:15])

        elif command == "summarize":
            amount = min(int(params.get("amount") or 20), 50)
            msgs = []
            async for msg in message.channel.history(limit=amount):
                if not msg.author.bot:
                    msgs.append(f"{msg.author.display_name}: {msg.content}")
            if not msgs:
                return "❌ No messages to summarize."
            summary = await ask_groq(
                f"Summarize in 3-5 bullet points:\n\n" + "\n".join(reversed(msgs)),
                "You are a summarization AI."
            )
            return f"📝 **Summary:**\n{summary}"

        elif command == "translate":
            text = params.get("text") or ""
            lang = params.get("language") or "English"
            if not text:
                return "❌ No text to translate."
            translation = await ask_groq(
                f"Translate to {lang}. Reply with ONLY the translation:\n\n{text}",
                "You are a translator."
            )
            return f"🌐 **({lang}):** {translation}"

        elif command == "add_word_filter":
            word = params.get("word")
            if not word:
                return "❌ No word specified."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)",
                (str(guild.id), word.lower()))
            conn.commit()
            conn.close()
            return f"✅ Added **{word}** to filter!"

        elif command == "remove_word_filter":
            word = params.get("word")
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM word_filters WHERE guild_id = ? AND word = ?",
                (str(guild.id), word.lower()))
            conn.commit()
            conn.close()
            return f"✅ Removed **{word}** from filter!"

        elif command == "add_note":
            target = find_member(params.get("target_user"))
            note = params.get("note") or params.get("text")
            if not target or not note:
                return "❌ Specify user and note."
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO user_notes
                (guild_id, user_id, note, mod_id, timestamp)
                VALUES (?, ?, ?, ?, ?)""",
                (str(guild.id), str(target.id), note,
                 str(author.id), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"📝 Note added for **{target.name}**!"

        elif command == "get_notes":
            target = find_member(params.get("target_user"))
            if not target:
                return "❌ User not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("""SELECT * FROM user_notes
                WHERE guild_id = ? AND user_id = ?""",
                (str(guild.id), str(target.id)))
            notes = c.fetchall()
            conn.close()
            if not notes:
                return f"📝 No notes for **{target.name}**."
            lines = [f"📝 **Notes for {target.name}:**"]
            for n in notes:
                lines.append(f"• {n['note']} - {n['timestamp'][:10]}")
            return "\n".join(lines)

        elif command == "set_autorole":
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not role:
                return "❌ Role not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO auto_roles (guild_id, role_id) VALUES (?, ?)",
                (str(guild.id), str(role.id)))
            conn.commit()
            conn.close()
            return f"✅ **{role.name}** will be given to new members!"

        elif command == "raid_mode":
            feature = params.get("feature") or params.get("text") or ""
            status = "on" in feature.lower() or "enable" in feature.lower()
            raid_mode_active[guild.id] = status
            return f"🚨 Raid mode **{'ON' if status else 'OFF'}**!"

        elif command == "server_health":
            total_members = guild.member_count
            bots = sum(1 for m in guild.members if m.bot)
            humans = total_members - bots
            channels = len(guild.text_channels)
            roles = len(guild.roles)

            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id = ?",
                (str(guild.id),))
            total_warns = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id = ?",
                (str(guild.id),))
            total_actions = c.fetchone()[0]
            conn.close()

            health_score = 100
            if total_warns > 50:
                health_score -= 20
            if total_warns > 100:
                health_score -= 20
            if bots > humans:
                health_score -= 10

            embed = discord.Embed(
                title="🏥 Server Health Report",
                color=discord.Color.green() if health_score > 70
                else discord.Color.orange() if health_score > 40
                else discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Health Score", value=f"{health_score}/100", inline=True)
            embed.add_field(name="Members", value=str(humans), inline=True)
            embed.add_field(name="Bots", value=str(bots), inline=True)
            embed.add_field(name="Channels", value=str(channels), inline=True)
            embed.add_field(name="Roles", value=str(roles), inline=True)
            embed.add_field(name="Total Warnings", value=str(total_warns), inline=True)
            embed.add_field(name="Mod Actions", value=str(total_actions), inline=True)
            embed.add_field(
                name="Raid Mode",
                value="🔴 ON" if raid_mode_active[guild.id] else "🟢 OFF",
                inline=True
            )
            await message.channel.send(embed=embed)
            return None

        elif command == "activity_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("""SELECT user_id, message_count FROM message_stats
                WHERE guild_id = ? ORDER BY message_count DESC LIMIT 10""",
                (str(guild.id),))
            top_users = c.fetchall()
            conn.close()

            embed = discord.Embed(
                title="📊 Activity Stats",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            if top_users:
                lines = []
                medals = ["🥇", "🥈", "🥉"]
                for i, row in enumerate(top_users):
                    member = guild.get_member(int(row["user_id"]))
                    name = member.display_name if member else f"User {row['user_id']}"
                    medal = medals[i] if i < 3 else f"#{i+1}"
                    lines.append(f"{medal} {name}: **{row['message_count']}** messages")
                embed.add_field(name="Top Active Members", value="\n".join(lines))
            else:
                embed.description = "No activity data yet!"
            await message.channel.send(embed=embed)
            return None

        elif command == "mod_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("""SELECT mod_id, COUNT(*) as total FROM mod_actions
                WHERE guild_id = ? GROUP BY mod_id
                ORDER BY total DESC LIMIT 5""",
                (str(guild.id),))
            top_mods = c.fetchall()
            conn.close()

            embed = discord.Embed(
                title="🛡️ Mod Leaderboard",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            if top_mods:
                lines = []
                for i, row in enumerate(top_mods, 1):
                    member = guild.get_member(int(row["mod_id"]))
                    name = member.display_name if member else f"Mod {row['mod_id']}"
                    lines.append(f"#{i} {name}: **{row['total']}** actions")
                embed.add_field(name="Top Moderators", value="\n".join(lines))
            await message.channel.send(embed=embed)
            return None

        elif command == "suggestion":
            suggestion_text = params.get("text") or params.get("note")
            if not suggestion_text:
                return "❌ Please provide a suggestion."
            settings = get_guild_settings(guild.id)
            sug_channel = discord.utils.get(
                guild.text_channels,
                name=settings.get("suggestions_channel", "suggestions")
            )
            if not sug_channel:
                return "❌ No suggestions channel found!"
            embed = discord.Embed(
                title="💡 New Suggestion",
                description=suggestion_text,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"By {author.display_name}")
            msg = await sug_channel.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO suggestions
                (guild_id, user_id, suggestion, message_id, timestamp)
                VALUES (?, ?, ?, ?, ?)""",
                (str(guild.id), str(author.id), suggestion_text,
                 str(msg.id), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"✅ Suggestion posted in {sug_channel.mention}!"

        elif command == "changelog":
            change_text = params.get("text") or params.get("note")
            if not change_text:
                return "❌ Please provide changelog content."
            settings = get_guild_settings(guild.id)
            cl_channel = discord.utils.get(
                guild.text_channels,
                name=settings.get("changelog_channel", "changelog")
            )
            if not cl_channel:
                return "❌ No changelog channel found!"
            embed = discord.Embed(
                title="📋 Server Update",
                description=change_text,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Posted by {author.display_name}")
            await cl_channel.send(embed=embed)
            return f"✅ Changelog posted in {cl_channel.mention}!"

        elif command == "cleanup":
            days = int(params.get("days") or 30)
            cutoff = datetime.now() - timedelta(days=days)
            inactive = []
            for member in guild.members:
                if member.bot:
                    continue
                conn = get_db()
                c = conn.cursor()
                c.execute("""SELECT last_message FROM message_stats
                    WHERE user_id = ? AND guild_id = ?""",
                    (str(member.id), str(guild.id)))
                row = c.fetchone()
                conn.close()
                if not row:
                    if (datetime.now() - member.joined_at.replace(tzinfo=None)).days > days:
                        inactive.append(member.name)

            if not inactive:
                return f"✅ No inactive members found in the last {days} days!"
            return (f"📊 Found **{len(inactive)}** potentially inactive members "
                    f"(no messages in {days} days):\n" +
                    ", ".join(inactive[:20]))

        elif command == "enable_feature":
            feature = params.get("feature", "").lower().replace(" ", "_")
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    f"UPDATE guild_settings SET {feature} = 1 WHERE guild_id = ?",
                    (str(guild.id),)
                )
                conn.commit()
                return f"✅ Enabled **{feature}**!"
            except:
                return f"❌ Unknown feature: {feature}"
            finally:
                conn.close()

        elif command == "disable_feature":
            feature = params.get("feature", "").lower().replace(" ", "_")
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    f"UPDATE guild_settings SET {feature} = 0 WHERE guild_id = ?",
                    (str(guild.id),)
                )
                conn.commit()
                return f"❌ Disabled **{feature}**!"
            except:
                return f"❌ Unknown feature: {feature}"
            finally:
                conn.close()

        elif command == "help":
            embed = discord.Embed(
                title="🛡️ SentinelMod Help",
                description="Mention me or chat in #sentinel-bot!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🔧 Server",
                value="make channel, make role, make category, delete channel, etc.",
                inline=False
            )
            embed.add_field(
                name="🔨 Moderation",
                value="ban, kick, mute, warn, purge, lock, lockdown, etc.",
                inline=False
            )
            embed.add_field(
                name="🎮 Fun",
                value="trivia, roast, compliment, 8ball, ship, rate, fact, etc.",
                inline=False
            )
            embed.add_field(
                name="🤖 AI",
                value="summarize, translate, story, debate, riddle, etc.",
                inline=False
            )
            embed.add_field(
                name="📊 Server",
                value="server health, activity stats, mod stats, suggestion, etc.",
                inline=False
            )
            embed.add_field(
                name="💬 Personality",
                value="Use /personality to change my personality!",
                inline=False
            )
            await message.channel.send(embed=embed)
            return None

        else:
            return None

    except discord.Forbidden:
        return "❌ I don't have permission to do that!"
    except Exception as e:
        print(f"Execute error: {e}")
        return f"❌ Error: {str(e)[:100]}"

# ============ SECTION 14 - MODERATION SYSTEMS ============
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
        await user.timeout(until, reason="Spam")
    except:
        pass
    warn_count = add_warning(user.id, guild.id, "Spam", "medium")
    log_mod_action(user.id, guild.id, "SPAM_MUTE", "Spam", bot.user.id)
    try:
        await user.send(embed=discord.Embed(
            title="⚠️ Spam Detected",
            description=f"Muted in **{guild.name}** for spamming",
            color=discord.Color.orange()
        ))
    except:
        pass
    embed = discord.Embed(
        title="🔇 Spam Handled",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=user.mention, inline=True)
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
        raid_channel = discord.utils.get(
            guild.text_channels, name=settings["raid_channel"]
        )
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
        if raid_channel:
            embed = discord.Embed(
                title="🚨 RAID DETECTED",
                description="Auto-defense activated!",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            ping = mod_role.mention if mod_role else ""
            await raid_channel.send(content=f"🚨 {ping}", embed=embed)
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
        await guild.ban(executor, reason="Anti-nuke")
    except:
        pass
    embed = discord.Embed(
        title="💣 NUKE ATTEMPT STOPPED",
        description=f"**{executor}** banned for nuking attempt!",
        color=discord.Color.dark_red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=f"{executor} ({executor.id})", inline=True)
    embed.add_field(name="Action", value=action_type, inline=True)
    embed.add_field(name="Result", value="🔨 BANNED", inline=True)
    nuke_ch = discord.utils.get(guild.text_channels, name="sentinel-nuke-alerts")
    if nuke_ch:
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
        ping = mod_role.mention if mod_role else ""
        await nuke_ch.send(content=ping, embed=embed)

async def check_toxicity(content, context="", sensitivity=0.7):
    prompt = f"""Analyze this Discord message for ALL types of harmful content.

Context: {context}
Message: "{content}"

Be thorough. Check for:
- Toxicity, harassment, hate speech
- Threats, blackmail, doxxing
- Grooming patterns
- Scam attempts
- Social engineering
- NSFW content
- Extremism
- Self harm promotion
- Impersonation
- Coordinated attacks

JSON only:
{{
    "toxic": true or false,
    "severity": "none|low|medium|high|critical",
    "category": "none|harassment|hate_speech|threat|spam|sexual|bullying|manipulation|slur|doxxing|grooming|scam|social_engineering|extremism|self_harm|impersonation|blackmail|fake_nitro|token_grab|advertisement",
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation",
    "sentiment": "positive|neutral|negative|hostile",
    "bypass_detected": true or false,
    "immediate_action": true or false
}}"""
    return await ask_groq_json(prompt)

async def check_advanced_patterns(message, settings):
    """Check for 70+ moderation patterns"""
    content = message.content
    content_lower = content.lower()
    author = message.author
    guild = message.guild
    now = time.time()
    key = f"{author.id}:{guild.id}"

    # ---- PHONE NUMBER ----
    if settings.get("phone_filter", 1):
        phone_pattern = r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b'
        if re.search(phone_pattern, content):
            return "phone_number", "Phone number detected"

    # ---- EMAIL ----
    if settings.get("email_filter", 1):
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, content):
            return "email", "Email address detected"

    # ---- FAKE NITRO ----
    if settings.get("fake_nitro_filter", 1):
        fake_nitro = ["free nitro", "discord nitro free", "get nitro",
                      "claim nitro", "free discord nitro"]
        if any(fn in content_lower for fn in fake_nitro):
            return "fake_nitro", "Fake Nitro scam detected"

    # ---- TOKEN GRABBER ----
    if settings.get("token_filter", 1):
        token_patterns = ["discord token", "grab token", "token logger",
                         "token stealer", "grabify.link"]
        if any(tp in content_lower for tp in token_patterns):
            return "token_grab", "Token grabber detected"

    # ---- ZALGO TEXT ----
    if settings.get("zalgo_filter", 1):
        zalgo_count = sum(1 for c in content
                         if unicodedata.combining(c) > 0)
        if zalgo_count > 10:
            return "zalgo", "Zalgo text detected"

    # ---- EMOJI SPAM ----
    if settings.get("emoji_spam", 1):
        emoji_count = sum(1 for c in content
                         if c in "😀😁😂🤣😃😄😅😆😉😊😋😎"
                         or (len(c) > 1 and ord(c[0]) >= 0x1F600))
        if emoji_count > 10:
            return "emoji_spam", "Emoji spam detected"

    # ---- REPEATED CHARS ----
    if re.search(r'(.)\1{9,}', content):
        return "repeated_chars", "Repeated character spam"

    # ---- CAPS ----
    if settings.get("caps_filter", 1) and len(content) > 10:
        caps = sum(1 for c in content if c.isupper())
        if caps / len(content) > 0.7:
            return "excessive_caps", "Excessive caps"

    # ---- MENTION SPAM ----
    if settings.get("mention_spam", 1):
        mention_tracker[key].append(now)
        mention_tracker[key] = [
            t for t in mention_tracker[key] if now - t < 10
        ]
        if len(message.mentions) >= 5 or len(mention_tracker[key]) >= 5:
            return "mention_spam", "Mention spam detected"

    # ---- EVERYONE BLOCK ----
    if settings.get("everyone_block", 0):
        if "@everyone" in content or "@here" in content:
            return "everyone_mention", "Everyone mention blocked"

    # ---- EMOJI SPAM TRACKER ----
    if settings.get("emoji_spam", 1):
        emoji_tracker[key].append(now)
        emoji_tracker[key] = [t for t in emoji_tracker[key] if now - t < 10]
        if len(emoji_tracker[key]) >= 8:
            return "emoji_spam", "Emoji spam"

    # ---- FILE SPAM ----
    if settings.get("file_spam_filter", 1) and message.attachments:
        file_tracker[key].append(now)
        file_tracker[key] = [t for t in file_tracker[key] if now - t < 30]
        if len(file_tracker[key]) >= 5:
            return "file_spam", "File spam detected"

    # ---- LARGE FILE ----
    for att in message.attachments:
        if att.size > 50 * 1024 * 1024:  # 50MB
            return "large_file", "Suspiciously large file"

    # ---- INVITE LINKS ----
    if settings.get("invite_block", 0):
        if re.search(r'(discord\.gg|discord\.com\/invite)\/[a-zA-Z0-9]+', content):
            return "invite_link", "Discord invite link"

    # ---- SUSPICIOUS LINKS ----
    if settings.get("link_scan", 1) and "http" in content_lower:
        suspicious = [
            "grabify", "iplogger", "discord.gift", "steamcommunity.ru",
            "discordapp.io", "discordnitro", "free-nitro", "phish", "scam",
            "discord.com.ru", "dlscord", "disçord", "discörd", "bit.ly/discord",
            "ip-logger", "ipgrab", "blasze", "lovebird.me"
        ]
        for s in suspicious:
            if s in content_lower:
                return "phishing_link", f"Phishing link: {s}"

    # ---- ADVERTISEMENT ----
    if settings.get("anti_advertisement", 1):
        ad_patterns = [
            "join my server", "check out my server", "discord.gg/",
            "free money", "make money fast", "follow me on",
            "subscribe to my", "check out my youtube"
        ]
        if any(ap in content_lower for ap in ad_patterns):
            return "advertisement", "Advertisement detected"

    # ---- SCAM PATTERNS ----
    if settings.get("scam_filter", 1):
        scam_patterns = [
            "you won", "claim your prize", "click here to claim",
            "limited time offer", "you have been selected",
            "send me your", "verify your account by",
            "your account will be deleted", "click this link to avoid"
        ]
        if any(sp in content_lower for sp in scam_patterns):
            return "scam", "Scam pattern detected"

    # ---- GROOMING PATTERNS ----
    if settings.get("nsfw_text_filter", 1):
        grooming = [
            "how old are you", "are you alone", "send me a pic",
            "don't tell your parents", "keep this secret",
            "you're so mature for your age"
        ]
        if any(gp in content_lower for gp in grooming):
            return "grooming", "Potential grooming pattern detected"

    # ---- IMPERSONATION ----
    if settings.get("impersonation_filter", 1):
        admin_names = ["admin", "administrator", "moderator", "discord staff",
                      "discord team", "discord support", "discord mod",
                      "discord official"]
        if any(an in content_lower for an in admin_names):
            # Check if actually staff
            if not message.author.guild_permissions.administrator:
                return "impersonation", "Possible impersonation detected"

    # ---- UNICODE BYPASS ----
    if settings.get("unicode_filter", 1):
        try:
            normalized = unicodedata.normalize("NFKC", content)
            if normalized != content:
                words = get_filtered_words(guild.id)
                normalized_lower = normalized.lower()
                for word in words:
                    if word in normalized_lower:
                        return "unicode_bypass", f"Unicode bypass of filter: {word}"
        except:
            pass

    # ---- ZERO WIDTH CHARS ----
    zero_width = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u2060']
    zw_count = sum(content.count(zw) for zw in zero_width)
    if zw_count > 5:
        return "zero_width", "Zero-width character spam"

    # ---- RTL ABUSE ----
    rtl_chars = sum(1 for c in content
                   if unicodedata.bidirectional(c) in ['R', 'AL', 'RLE', 'RLO'])
    if rtl_chars > 5 and rtl_chars / max(len(content), 1) > 0.3:
        return "rtl_abuse", "RTL text abuse"

    # ---- SOCIAL ENGINEERING ----
    social_eng = [
        "i'm from discord", "official discord", "your account has been flagged",
        "verify your account", "you need to verify", "your account is at risk",
        "click here to secure", "your password has been"
    ]
    if any(se in content_lower for se in social_eng):
        return "social_engineering", "Social engineering attempt"

    # ---- BLACKMAIL ----
    blackmail = [
        "i will expose you", "pay me or", "i have your info",
        "i know where you live", "i'll tell everyone",
        "send me money or", "give me or i'll"
    ]
    if any(bm in content_lower for bm in blackmail):
        return "blackmail", "Blackmail/extortion detected"

    # ---- SELF HARM ----
    self_harm = [
        "want to kill myself", "want to die", "going to hurt myself",
        "suicide", "end my life", "harm myself"
    ]
    if any(sh in content_lower for sh in self_harm):
        return "self_harm", "Self-harm content - please check on this user"

    # ---- EXTREMISM ----
    extremism = [
        "join our movement", "death to", "kill all",
        "purge the", "exterminate"
    ]
    if any(ex in content_lower for ex in extremism):
        return "extremism", "Extremist content detected"

    # ---- COPYPASTA SPAM ----
    if len(content) > 200:
        lines = content.split('\n')
        if len(set(lines)) < len(lines) / 2:
            return "copypasta", "Copypasta/repeated text spam"

    # ---- MASS DM DETECTION ----
    if settings.get("mass_dm_detection", 1):
        dm_tracker[key].append(now)
        dm_tracker[key] = [t for t in dm_tracker[key] if now - t < 60]
        if len(dm_tracker[key]) >= 10:
            return "mass_dm", "Possible mass DM spam"

    return None, None

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
        "low": discord.Color.yellow(), "medium": discord.Color.orange(),
        "high": discord.Color.red(), "critical": discord.Color.dark_red()
    }
    mod_embed = discord.Embed(
        title="🚨 AI Moderation Alert",
        color=colors.get(severity, discord.Color.red()),
        timestamp=datetime.now()
    )
    mod_embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
    mod_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    mod_embed.add_field(name="Severity", value=severity.upper(), inline=True)
    mod_embed.add_field(
        name="Category",
        value=analysis.get("category", "unknown"),
        inline=True
    )
    mod_embed.add_field(
        name="Confidence",
        value=f"{analysis.get('confidence', 0)*100:.0f}%",
        inline=True
    )
    mod_embed.add_field(
        name="Bypass",
        value="⚠️ Yes" if analysis.get("bypass_detected") else "No",
        inline=True
    )
    mod_embed.add_field(
        name="Warnings",
        value=f"{warn_count}/{settings.get('warn_ban', 5)}",
        inline=True
    )
    mod_embed.add_field(
        name="Message",
        value=f"||{message.content[:500]}||",
        inline=False
    )
    mod_embed.add_field(name="Reason", value=reason, inline=False)
    action = "⚠️ Warning"
    if (warn_count >= settings.get("warn_mute", 3) and
            warn_count < settings.get("warn_ban", 5)):
        try:
            until = datetime.now() + timedelta(
                minutes=settings.get("mute_duration", 10)
            )
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
    # Immediate action for critical stuff
    if analysis.get("immediate_action") and severity == "critical":
        try:
            await guild.ban(user, reason=f"IMMEDIATE: {reason}")
            action = "🔨 IMMEDIATELY BANNED"
        except:
            pass
    mod_embed.add_field(name="Action", value=action, inline=False)
    await alert_mods(guild, mod_embed)

# ============ SECTION 15 - TICKET SYSTEM ============
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket", style=discord.ButtonStyle.primary,
        emoji="🎫", custom_id="create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class TicketModal(discord.ui.Modal, title="Create Support Ticket"):
    reason = discord.ui.TextInput(
        label="Describe your issue",
        style=discord.TextStyle.long, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        settings = get_guild_settings(guild.id)
        ticket_cat = discord.utils.get(guild.categories, name="🎫 TICKETS")
        mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
        ticket_name = f"ticket-{user.name.lower()[:10]}-{random.randint(1000,9999)}"
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
            c.execute("""INSERT INTO tickets
                (guild_id, user_id, channel_id, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)""",
                (str(guild.id), str(user.id), str(channel.id),
                 str(self.reason.value), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            embed = discord.Embed(
                title="🎫 Ticket Created",
                description=f"Hello {user.mention}! Support coming soon.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Issue", value=str(self.reason.value))
            ping = mod_role.mention if mod_role else ""
            await channel.send(
                content=f"{user.mention} {ping}",
                embed=embed, view=CloseTicketView()
            )
            await interaction.response.send_message(
                f"✅ {channel.mention}", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket", style=discord.ButtonStyle.danger,
        emoji="🔒", custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction,
                           button: discord.ui.Button):
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?",
            (str(interaction.channel.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message("🔒 Closing in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ============ SECTION 16 - CONFIRMATION SYSTEM ============
class ConfirmView(discord.ui.View):
    def __init__(self, parsed, original_message, guild, author):
        super().__init__(timeout=30)
        self.parsed = parsed
        self.original_message = original_message
        self.guild = guild
        self.author = author

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction,
                      button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Only the requester can confirm.", ephemeral=True
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
    async def cancel(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Only the requester can cancel.", ephemeral=True
            )
            return
        await interaction.response.send_message("❌ Cancelled.")
        self.stop()

# ============ SECTION 17 - PERSONALITY SLASH COMMAND ============
@bot.tree.command(name="personality", description="Change SentinelMod's personality")
async def personality_command(interaction: discord.Interaction):
    """Show personality selector embed"""
    categories = {
        "🎭 Characters": [
            "pirate", "medieval", "wizard", "vampire", "ghost", "dragon",
            "ninja", "samurai", "cowboy", "viking"
        ],
        "🎬 Pop Culture": [
            "yoda", "jarvis", "hal9000", "glados", "deadpool", "sherlock",
            "gandalf", "tony_stark", "groot", "gollum"
        ],
        "😄 Moods": [
            "friendly", "sarcastic", "serious", "chaotic", "motivational",
            "pessimist", "optimist", "hype", "philosopher", "therapist"
        ],
        "🌍 Cultures": [
            "british", "australian", "valley_girl", "gen_z", "boomer",
            "millennial", "caveman", "shakespeare", "surfer", "anime"
        ],
        "👔 Professions": [
            "professor", "chef", "detective", "lawyer", "doctor",
            "scientist", "artist", "politician", "sportscaster", "news_anchor"
        ],
        "🔮 Fantasy": [
            "alien", "time_traveler", "oracle", "fairy", "mermaid",
            "elf", "werewolf", "giant", "robot_overlord", "dimension_hopper"
        ]
    }

    embed = discord.Embed(
        title="🎭 Choose SentinelMod's Personality",
        description="Select a category and use `/setpersonality` with the name!",
        color=discord.Color.purple()
    )

    for cat_name, personalities in categories.items():
        embed.add_field(
            name=cat_name,
            value=", ".join(f"`{p}`" for p in personalities),
            inline=False
        )

    embed.set_footer(
        text=f"Current personality: "
             f"{get_user_personality(str(interaction.user.id), str(interaction.guild.id))}"
    )

    view = PersonalityView(interaction.user.id, interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PersonalityView(discord.ui.View):
    def __init__(self, user_id, guild_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.guild_id = guild_id

        # Add dropdown
        options = []
        for name in list(PERSONALITIES.keys())[:25]:
            options.append(discord.SelectOption(
                label=name.replace("_", " ").title(),
                value=name,
                description=PERSONALITIES[name][:50]
            ))

        select = discord.ui.Select(
            placeholder="Choose a personality...",
            options=options,
            custom_id="personality_select"
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        personality = interaction.data["values"][0]
        set_user_personality(
            str(self.user_id), str(self.guild_id), personality
        )
        embed = discord.Embed(
            title="✅ Personality Changed!",
            description=f"SentinelMod is now: **{personality.replace('_', ' ').title()}**\n\n"
                       f"*{PERSONALITIES[personality]}*",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setpersonality",
                  description="Set SentinelMod's personality by name")
@app_commands.describe(personality="Personality name (e.g. pirate, yoda, sarcastic)")
async def setpersonality_command(interaction: discord.Interaction, personality: str):
    personality = personality.lower().replace(" ", "_")
    if personality not in PERSONALITIES:
        closest = [p for p in PERSONALITIES.keys() if personality[:3] in p]
        suggest = f"\nDid you mean: {', '.join(closest[:5])}?" if closest else ""
        await interaction.response.send_message(
            f"❌ Unknown personality: **{personality}**{suggest}\n"
            f"Use `/personality` to see all options.",
            ephemeral=True
        )
        return
    set_user_personality(
        str(interaction.user.id), str(interaction.guild.id), personality
    )
    embed = discord.Embed(
        title="✅ Personality Set!",
        description=f"SentinelMod is now: **{personality.replace('_', ' ').title()}**\n\n"
                   f"*{PERSONALITIES[personality]}*",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============ SECTION 18 - BACKGROUND TASKS ============
@tasks.loop(minutes=1)
async def check_giveaways():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM giveaways WHERE active = 1 AND end_time <= ?",
        (datetime.now().isoformat(),))
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
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot] if reaction else []
            if not users:
                await channel.send("❌ No entries for the giveaway!")
            else:
                num_winners = min(giveaway["winners"], len(users))
                winners = random.sample(users, num_winners)
                mentions = ", ".join(w.mention for w in winners)
                embed = discord.Embed(
                    title="🎉 Giveaway Ended!",
                    description=f"**Prize:** {giveaway['prize']}\n"
                               f"**Winner(s):** {mentions}",
                    color=discord.Color.gold()
                )
                await channel.send(content=f"🎉 {mentions}!", embed=embed)
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE giveaways SET active = 0 WHERE id = ?",
                (giveaway["id"],))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Giveaway error: {e}")

@tasks.loop(hours=24)
async def daily_cleanup():
    """Daily maintenance"""
    conn = get_db()
    c = conn.cursor()
    # Clean old conversation history (keep last 7 days)
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("DELETE FROM conversation_history WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()
    print("✅ Daily cleanup done")

# ============ SECTION 19 - BOT EVENTS ============
@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 SentinelMod ONLINE")
    print(f"📛 Bot: {bot.user}")
    print(f"🏠 Servers: {len(bot.guilds)}")
    print(f"🧠 Personalities: {len(PERSONALITIES)}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for guild in bot.guilds:
        init_guild_settings(guild.id)
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Sync error: {e}")
    check_giveaways.start()
    daily_cleanup.start()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="everything 👁️ | @mention me!"
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

    # Suspicious account alert
    if account_age < settings.get("min_account_age", 7):
        raid_ch = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
        if raid_ch:
            embed = discord.Embed(
                title="⚠️ Suspicious Account",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=f"{member.mention}", inline=True)
            embed.add_field(name="Age", value=f"{account_age} days", inline=True)
            await raid_ch.send(embed=embed)

    # Welcome
    if settings.get("welcome_enabled", 1):
        welcome_ch = discord.utils.get(
            guild.text_channels,
            name=settings.get("welcome_channel", "welcome")
        )
        if welcome_ch:
            welcome = await ask_groq(
                f"Write a short warm welcome for {member.display_name} "
                f"joining {guild.name} (member #{guild.member_count}). "
                "2-3 sentences max. Be creative and friendly.",
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
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    # Trivia answer check
    if reaction.message.id in trivia_sessions:
        session = trivia_sessions[reaction.message.id]
        if user.id in session["answered"]:
            return
        session["answered"].append(user.id)
        if str(reaction.emoji) == session["correct_emoji"]:
            # Update score
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO trivia_scores (user_id, guild_id, score, total)
                VALUES (?, ?, 1, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                score = score + 1, total = total + 1""",
                (str(user.id), str(session["guild_id"])))
            conn.commit()
            conn.close()
            try:
                await reaction.message.channel.send(
                    f"✅ {user.mention} got it right! "
                    f"Answer: **{session['correct_answer']}**"
                )
            except:
                pass
            del trivia_sessions[reaction.message.id]

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
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if not before.guild:
        return
    # Track stealth edits
    if before.content != after.content:
        key = f"{before.author.id}:{before.guild.id}"
        edit_tracker[key].append(time.time())
        edit_tracker[key] = [
            t for t in edit_tracker[key] if time.time() - t < 60
        ]
        # Log to audit
        settings = get_guild_settings(before.guild.id)
        if len(edit_tracker[key]) >= 5:
            embed = discord.Embed(
                title="✏️ Rapid Message Edits",
                color=discord.Color.yellow(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=before.author.mention, inline=True)
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
            embed.add_field(name="Before", value=before.content[:200], inline=False)
            embed.add_field(name="After", value=after.content[:200], inline=False)
            await alert_mods(before.guild, embed, "sentinel-audit")

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

    # Update message stats
    update_message_stats(message.author.id, message.guild.id)

    # ---- AFK CHECK ----
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM afk_users WHERE guild_id = ?", (str(message.guild.id),))
    afk_users = {row["user_id"]: dict(row) for row in c.fetchall()}
    conn.close()

    if str(message.author.id) in afk_users:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM afk_users WHERE user_id = ? AND guild_id = ?",
            (str(message.author.id), str(message.guild.id)))
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

    # ============ AI CHAT CHANNEL ============
    is_ai_channel = message.channel.name == AI_CHAT_CHANNEL
    is_mentioned = bot.user in message.mentions

    if is_ai_channel or is_mentioned:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content and not is_ai_channel:
            await message.reply(f"👋 Hey! Try: `@{BOT_NAME} help`")
            return

        if content:
            if is_mod or is_admin:
                # Parse as command first
                async with message.channel.typing():
                    parsed = await parse_command(content, message.guild, message.author)

                if parsed and parsed.get("command") not in ["chat", "unknown", None]:
                    needs_confirmation = parsed.get("needs_confirmation", False)
                    if needs_confirmation:
                        embed = discord.Embed(
                            title="⚠️ Confirm Action",
                            description=parsed.get("confirmation_message", "Confirm?"),
                            color=discord.Color.orange()
                        )
                        view = ConfirmView(
                            parsed, message, message.guild, message.author
                        )
                        await message.reply(embed=embed, view=view)
                    else:
                        async with message.channel.typing():
                            result = await execute_command(
                                parsed, message, message.guild, message.author
                            )
                        if result:
                            await message.reply(result[:2000])
                    if not is_ai_channel:
                        await bot.process_commands(message)
                    return

            # AI Chat with streaming + memory + personality
            system = get_system_prompt(
                str(message.author.id),
                str(message.guild.id),
                f"Server: {message.guild.name}\n"
                f"Channel: {message.channel.name}\n"
                f"User: {message.author.display_name}"
            )
            history = get_conversation_history(
                str(message.author.id), str(message.guild.id)
            )
            await stream_response(
                message, content, system, history,
                str(message.author.id), str(message.guild.id)
            )
            return

    # ============ MODERATION ============
    if is_mod or is_admin:
        await bot.process_commands(message)
        return

    # ---- ANTI-SPAM ----
    is_spam = await check_spam(message, settings)
    if is_spam:
        await handle_spam(message, settings)
        return

    # ---- ADVANCED PATTERN CHECKS ----
    pattern_type, pattern_reason = await check_advanced_patterns(message, settings)
    if pattern_type:
        try:
            await message.delete()
        except:
            pass

        severity_map = {
            "phone_number": "high", "email": "high", "fake_nitro": "critical",
            "token_grab": "critical", "zalgo": "medium", "emoji_spam": "low",
            "repeated_chars": "low", "excessive_caps": "low",
            "mention_spam": "high", "everyone_mention": "medium",
            "file_spam": "medium", "large_file": "medium",
            "invite_link": "medium", "phishing_link": "critical",
            "advertisement": "medium", "scam": "critical",
            "grooming": "critical", "impersonation": "high",
            "unicode_bypass": "high", "zero_width": "medium",
            "rtl_abuse": "medium", "social_engineering": "critical",
            "blackmail": "critical", "self_harm": "high",
            "extremism": "critical", "copypasta": "low",
            "mass_dm": "high"
        }

        severity = severity_map.get(pattern_type, "medium")

        # Special handling for self harm
        if pattern_type == "self_harm":
            try:
                support_embed = discord.Embed(
                    title="💙 We're Here For You",
                    description=f"{message.author.mention}, it seems you might be "
                               "going through something difficult.\n\n"
                               "**Crisis Resources:**\n"
                               "• National Suicide Prevention: **988**\n"
                               "• Crisis Text Line: Text **HOME** to **741741**\n"
                               "• International: **findahelpline.com**",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=support_embed)
            except:
                pass

        warn_count = add_warning(
            message.author.id, message.guild.id, pattern_reason, severity
        )

        if severity in ["high", "critical"]:
            embed = discord.Embed(
                title=f"🚨 {pattern_type.replace('_', ' ').title()} Detected",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=message.author.mention, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Reason", value=pattern_reason, inline=False)
            embed.add_field(name="Severity", value=severity.upper(), inline=True)
            embed.add_field(name="Warnings", value=str(warn_count), inline=True)
            await alert_mods(message.guild, embed)

        # Auto mute/ban based on warnings
        if warn_count >= settings.get("warn_mute", 3):
            try:
                until = datetime.now() + timedelta(
                    minutes=settings.get("mute_duration", 10)
                )
                await message.author.timeout(until, reason=pattern_reason)
            except:
                pass

        if warn_count >= settings.get("warn_ban", 5):
            try:
                await message.guild.ban(
                    message.author, reason=f"Too many violations: {pattern_reason}"
                )
            except:
                pass

        # For critical patterns, immediate action
        if severity == "critical" and pattern_type in [
            "fake_nitro", "token_grab", "phishing_link",
            "scam", "social_engineering", "blackmail", "extremism"
        ]:
            try:
                await message.guild.ban(
                    message.author,
                    reason=f"IMMEDIATE BAN: {pattern_reason}"
                )
                embed = discord.Embed(
                    title="🔨 Immediate Ban",
                    description=f"{message.author} was immediately banned.",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Reason", value=pattern_reason)
                await alert_mods(message.guild, embed)
            except:
                pass

        await bot.process_commands(message)
        return

    # ---- WORD FILTER ----
    words = get_filtered_words(message.guild.id)
    content_lower = message.content.lower()
    normalized = content_lower
    for old, new in [("@","a"),("0","o"),("1","i"),("3","e"),("$","s"),("5","s"),("4","a")]:
        normalized = normalized.replace(old, new)

    for word in words:
        if word in content_lower or word in normalized:
            try:
                await message.delete()
            except:
                pass
            warn_count = add_warning(
                message.author.id, message.guild.id, "Filtered word", "medium"
            )
            await message.channel.send(
                f"⚠️ {message.author.mention} That word is not allowed!",
                delete_after=5
            )
            embed = discord.Embed(
                title="🔤 Word Filter",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="User", value=message.author.mention, inline=True)
            embed.add_field(name="Warnings", value=str(warn_count), inline=True)
            await alert_mods(message.guild, embed)
            await bot.process_commands(message)
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
        m for m in recent_messages[channel_key]
        if time.time() - m["time"] < 60
    ]

    if settings.get("pre_conflict", 1) and len(recent_messages[channel_key]) >= 6:
        msgs_text = "\n".join([
            f"{m['author']}: {m['content']}"
            for m in recent_messages[channel_key][-10:]
        ])
        conflict = await ask_groq_json(
            f"""Analyze for escalating conflict:

{msgs_text}

JSON:
{{
    "escalating": true or false,
    "severity": "none|mild|moderate|severe",
    "users_involved": ["user1"],
    "reason": "brief"
}}"""
        )
        if conflict and conflict.get("escalating"):
            severity = conflict.get("severity", "mild")
            if severity in ["moderate", "severe"]:
                embed = discord.Embed(
                    title="⚠️ Conversation Heating Up",
                    description="Please keep things civil! 😊",
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
                        name="Channel", value=message.channel.mention
                    )
                    mod_embed.add_field(name="Severity", value=severity.upper())
                    mod_embed.add_field(
                        name="Users",
                        value=", ".join(conflict.get("users_involved", []))
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
    if len(message.content) < 3:
        await bot.process_commands(message)
        return

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
                        title="⚠️ Please be respectful",
                        description=f"Warning in **{message.guild.name}**",
                        color=discord.Color.yellow()
                    )
                    dm.add_field(name="Reason", value=reason)
                    await message.author.send(embed=dm)
                except:
                    pass

    await bot.process_commands(message)

# ============ SECTION 20 - RUN BOT ============
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not set!")
    elif not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set!")
    else:
        init_database()
        keep_alive()
        print("🚀 Starting SentinelMod...")
        bot.run(DISCORD_TOKEN)
