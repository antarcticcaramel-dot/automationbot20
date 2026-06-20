# bot.py
# ================================
# SentinelMod - Ultimate AI Discord Bot
# Complete Rewrite - Fixed & Enhanced
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

PERSONALITIES = {
    "friendly": "You are extremely friendly, warm, and supportive. Use lots of emojis.",
    "sarcastic": "You are deeply sarcastic and witty. Everything has a sarcastic undertone.",
    "serious": "You are professional, serious, formal. No jokes, straight to the point.",
    "chaotic": "You are completely chaotic, random, and unpredictable.",
    "pirate": "You are a pirate. Speak like a pirate. Arr matey!",
    "medieval": "You are a medieval knight. Speak in old English. Very honorable.",
    "robot": "You are a robot. Speak robotically. Beep boop.",
    "therapist": "You are a caring therapist. Always validate feelings.",
    "villain": "You are a dramatic villain who is helpful but theatrical.",
    "hype": "You are the ultimate hype man. Everything is AMAZING.",
    "philosopher": "You are a deep philosopher. Question everything.",
    "caveman": "You speak like a caveman. Simple words. UGH. FIRE GOOD.",
    "shakespeare": "You speak in Shakespearean English. Thee, thou, doth.",
    "surfer": "You are a chill surfer dude. Everything is gnarly.",
    "nerd": "You are an extreme nerd. Reference science and pop culture.",
    "anime": "You speak like an anime character. Very dramatic.",
    "cowboy": "You are a cowboy. Yeehaw partner!",
    "british": "You are extremely British. Tea, crumpets, cheerio.",
    "australian": "You are extremely Australian. G'day mate, crikey.",
    "valley_girl": "You are a valley girl. Like, totally, oh my god.",
    "professor": "You are a distinguished professor. Always teaching.",
    "chef": "You are a passionate chef. Relate everything to cooking.",
    "detective": "You are a film noir detective. Mysterious, investigative.",
    "alien": "You are an alien learning about humans. Everything is fascinating.",
    "time_traveler": "You are a time traveler from the future.",
    "ghost": "You are a friendly ghost. Spooky but helpful.",
    "dragon": "You are an ancient dragon. Wise, powerful.",
    "wizard": "You are a powerful wizard. Reference spells and magic.",
    "superhero": "You are an enthusiastic superhero. Ready to save the day.",
    "gen_z": "You speak in Gen Z slang. No cap, bussin, slay, based.",
    "boomer": "You are a stereotypical boomer. Good old days.",
    "gamer": "You are an extreme gamer. Reference games constantly.",
    "yoda": "Speak like Yoda you must. Inverted sentences always.",
    "jarvis": "You are JARVIS from Iron Man. Sophisticated AI.",
    "deadpool": "You are Deadpool. Break the fourth wall. Chaotic.",
    "sherlock": "You are Sherlock Holmes. Deduce everything.",
    "gandalf": "You are Gandalf. Wise, mysterious. YOU SHALL NOT PASS.",
    "tony_stark": "You are Tony Stark. Genius, billionaire, playboy.",
    "groot": "I am Groot. (Translate in parentheses what Groot means)",
    "gollum": "You are Gollum. My precious. Split personality.",
    "darth_vader": "You are Darth Vader. The dark side. Heavy breathing.",
    "michael_scott": "You are Michael Scott. Inappropriate but lovable.",
    "dwight_schrute": "You are Dwight Schrute. Bears, beets, Battlestar Galactica.",
    "motivational": "You are an extreme motivational speaker. Everything is possible!",
    "pessimist": "You are extremely pessimistic. Everything will go wrong.",
    "optimist": "You are blindly optimistic. Everything is wonderful.",
    "ninja": "You are a ninja. Stealthy and honorable.",
    "samurai": "You are a samurai. Honor, discipline, bushido.",
    "fairy": "You are a tiny fairy with big energy. Magical.",
    "vampire": "You are a sophisticated vampire. Ancient and dramatic.",
    "oracle": "You are an ancient oracle. Speak in prophecies.",
    "mad_hatter": "You are the Mad Hatter. Wonderfully nonsensical.",
    "default": "You are SentinelMod, a helpful and friendly Discord bot."
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
    tables = [
        """CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            reason TEXT NOT NULL, severity TEXT NOT NULL,
            timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS mod_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            action TEXT NOT NULL, reason TEXT NOT NULL,
            mod_id TEXT NOT NULL, timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS guild_settings (
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
            nsfw_text_filter INTEGER DEFAULT 1, everyone_block INTEGER DEFAULT 0,
            anti_advertisement INTEGER DEFAULT 1, unicode_filter INTEGER DEFAULT 1,
            fake_nitro_filter INTEGER DEFAULT 1, token_filter INTEGER DEFAULT 1,
            file_spam_filter INTEGER DEFAULT 1, personality TEXT DEFAULT 'default')""",
        """CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            memory TEXT NOT NULL, updated TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL,
            timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS user_personalities (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            personality TEXT DEFAULT 'default',
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL, status TEXT DEFAULT 'open',
            reason TEXT NOT NULL, timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS afk_users (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            reason TEXT NOT NULL, timestamp TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, channel_id TEXT NOT NULL,
            message_id TEXT, prize TEXT NOT NULL,
            winners INTEGER DEFAULT 1, end_time TEXT NOT NULL,
            active INTEGER DEFAULT 1, host_id TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS auto_roles (
            guild_id TEXT NOT NULL, role_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, role_id))""",
        """CREATE TABLE IF NOT EXISTS word_filters (
            guild_id TEXT NOT NULL, word TEXT NOT NULL,
            PRIMARY KEY (guild_id, word))""",
        """CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, user_id TEXT NOT NULL,
            note TEXT NOT NULL, mod_id TEXT NOT NULL,
            timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, user_id TEXT NOT NULL,
            suggestion TEXT NOT NULL, status TEXT DEFAULT 'pending',
            message_id TEXT, timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS trivia_scores (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            score INTEGER DEFAULT 0, total INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS backup_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, backup_type TEXT NOT NULL,
            data TEXT NOT NULL, timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS message_stats (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            last_message TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL, reminder TEXT NOT NULL,
            remind_time TEXT NOT NULL, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS birthdays (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            birthday TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS reputation (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            rep INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS confessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL, confession TEXT NOT NULL,
            timestamp TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS custom_commands (
            guild_id TEXT NOT NULL, trigger_word TEXT NOT NULL,
            response TEXT NOT NULL,
            PRIMARY KEY (guild_id, trigger_word))""",
        """CREATE TABLE IF NOT EXISTS reaction_roles (
            guild_id TEXT NOT NULL, message_id TEXT NOT NULL,
            emoji TEXT NOT NULL, role_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, message_id, emoji))""",
        """CREATE TABLE IF NOT EXISTS quarantine (
            user_id TEXT NOT NULL, guild_id TEXT NOT NULL,
            reason TEXT NOT NULL, timestamp TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id))"""
    ]
    for table in tables:
        c.execute(table)
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ============ SECTION 5 - DB HELPERS ============
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
    return {"guild_id": str(guild_id), "mod_role_name": MOD_ROLE_NAME,
        "log_channel": MOD_LOG_CHANNEL, "raid_channel": RAID_CHANNEL,
        "warn_mute": 3, "warn_ban": 5, "mute_duration": 10,
        "spam_limit": 5, "spam_window": 5, "raid_limit": 10,
        "raid_window": 10, "min_account_age": 7, "scan_images": 1,
        "ai_sensitivity": 0.7, "welcome_channel": "welcome",
        "welcome_enabled": 1, "anti_nuke_enabled": 1, "invite_block": 0,
        "link_scan": 1, "slowmode_ai": 1, "pre_conflict": 1,
        "caps_filter": 1, "mention_spam": 1, "emoji_spam": 1,
        "zalgo_filter": 1, "phone_filter": 1, "email_filter": 1,
        "scam_filter": 1, "nsfw_text_filter": 1, "everyone_block": 0,
        "anti_advertisement": 1, "unicode_filter": 1,
        "fake_nitro_filter": 1, "token_filter": 1,
        "file_spam_filter": 1, "personality": "default"}

def init_guild_settings(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
        (str(guild_id),))
    conn.commit()
    conn.close()

def add_warning(uid, gid, reason, severity):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO warnings (user_id,guild_id,reason,severity,timestamp) VALUES (?,?,?,?,?)",
        (str(uid), str(gid), reason, severity, datetime.now().isoformat()))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?",
        (str(uid), str(gid)))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_warnings(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM warnings WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC",
        (str(uid), str(gid)))
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
    c.execute("INSERT INTO mod_actions (user_id,guild_id,action,reason,mod_id,timestamp) VALUES (?,?,?,?,?,?)",
        (str(uid), str(gid), action, reason, str(mod_id), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_memory(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT memory FROM user_memory WHERE user_id=? AND guild_id=?",
        (str(uid), str(gid)))
    row = c.fetchone()
    conn.close()
    return row["memory"] if row else ""

def update_user_memory(uid, gid, memory):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_memory (user_id,guild_id,memory,updated) VALUES (?,?,?,?)",
        (str(uid), str(gid), memory, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_conversation_history(uid, gid, limit=20):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role,content FROM conversation_history WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT ?",
        (str(uid), str(gid), limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def add_to_conversation(uid, gid, role, content):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO conversation_history (user_id,guild_id,role,content,timestamp) VALUES (?,?,?,?,?)",
        (str(uid), str(gid), role, content, datetime.now().isoformat()))
    conn.commit()
    c.execute("""DELETE FROM conversation_history WHERE id NOT IN (
        SELECT id FROM conversation_history WHERE user_id=? AND guild_id=?
        ORDER BY timestamp DESC LIMIT 50) AND user_id=? AND guild_id=?""",
        (str(uid), str(gid), str(uid), str(gid)))
    conn.commit()
    conn.close()

def get_user_personality(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT personality FROM user_personalities WHERE user_id=? AND guild_id=?",
        (str(uid), str(gid)))
    row = c.fetchone()
    conn.close()
    return row["personality"] if row else "default"

def set_user_personality(uid, gid, p):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_personalities (user_id,guild_id,personality) VALUES (?,?,?)",
        (str(uid), str(gid), p))
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
    c.execute("""INSERT INTO message_stats (user_id,guild_id,message_count,last_message)
        VALUES (?,?,1,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET
        message_count=message_count+1, last_message=?""",
        (str(uid), str(gid), datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ============ SECTION 6 - BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)
nuke_action_tracker = defaultdict(list)
recent_messages = defaultdict(list)
mention_tracker = defaultdict(list)
file_tracker = defaultdict(list)
edit_tracker = defaultdict(list)
trivia_sessions = {}

# ============ SECTION 7 - AI CORE ============
async def ask_groq(prompt, system="You are a helpful AI.", max_tokens=1000, history=None):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-15:])
    messages.append({"role": "user", "content": prompt})
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.8, "max_tokens": max_tokens}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq error: {e}")
    return None

async def ask_groq_json(prompt, system="Respond only in valid JSON."):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ], "temperature": 0.1, "max_tokens": 1000}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
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

# ============ SECTION 8 - STREAMING ============
async def stream_response(message, prompt, system, history=None, uid=None, gid=None):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-15:])
    messages.append({"role": "user", "content": prompt})
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.8,
        "max_tokens": 1000, "stream": True}

    sent = await message.reply("💭 *thinking...*")
    full = ""
    last_update = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
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
                    f"Current memory: {get_user_memory(uid, gid)}\n"
                    f"New: User said: {prompt}\nBot said: {full}\n"
                    "Update memory with important facts about user. Under 500 chars.",
                    "Extract and remember important user facts only.")
                if mem:
                    update_user_memory(uid, gid, mem[:500])
    except Exception as e:
        print(f"Stream error: {e}")
        if full:
            await sent.edit(content=full[:2000])
        else:
            await sent.edit(content="❌ Something went wrong!")

# ============ SECTION 9 - PERSONALITY ============
def get_system_prompt(uid, gid, extra=""):
    pkey = get_user_personality(uid, gid)
    personality = PERSONALITIES.get(pkey, PERSONALITIES["default"])
    memory = get_user_memory(uid, gid)
    return f"""You are SentinelMod, a Discord bot.
Personality: {personality}
{f'Memory about this user: {memory}' if memory else ''}
{extra}
Rules: Stay in character. Be helpful. Keep responses concise for Discord. Max 1500 chars."""

# ============ SECTION 10 - STRICT COMMAND PARSER ============
async def parse_command(content, guild, author):
    channels = [c.name for c in guild.text_channels][:20]
    roles = [r.name for r in guild.roles if r.name != "@everyone"][:20]
    categories = [c.name for c in guild.categories][:10]
    members = [f"{m.name} (ID:{m.id})" for m in guild.members if not m.bot][:30]

    # Extract mentioned users from the content
    mentioned_ids = re.findall(r'<@!?(\d+)>', content)
    mentioned_names = []
    for mid in mentioned_ids:
        member = guild.get_member(int(mid))
        if member:
            mentioned_names.append(f"{member.name} (ID:{mid})")

    prompt = f"""You are a STRICT Discord bot command parser. Be EXTREMELY careful and accurate.

Server: {guild.name}
Channels: {', '.join(channels)}
Roles: {', '.join(roles)}
Categories: {', '.join(categories)}
Members: {', '.join(members)}
Mentioned users in message: {', '.join(mentioned_names) if mentioned_names else 'NONE'}
User who sent command: {author.name} (ID:{author.id})
Message: "{content}"

CRITICAL SAFETY RULES:
1. If the message is casual chat, questions, or unclear → command = "chat"
2. For moderation (ban/kick/mute/warn), the target MUST be @mentioned or EXACTLY named
3. If mentioned_users is NONE and command needs a target → command = "chat"
4. The person SENDING the command is NOT the target unless they say "myself"
5. NEVER confuse the sender with the target
6. ALL dangerous commands need confirmation = true
7. If confidence < 0.8 → command = "chat"
8. For fun commands (trivia, roast, joke etc) → needs_confirmation = false
9. Only match target_user to someone in the Members list EXACTLY
10. If it looks like someone just talking TO the bot → command = "chat"

Dangerous commands (ALWAYS needs_confirmation = true):
ban_user, kick_user, mute_user, warn_user, delete_channel, delete_role,
delete_category, lockdown, purge, clear_warnings

Safe commands (needs_confirmation = false):
create_channel, create_role, create_category, trivia, roast, compliment,
8ball, ship, rate, fact, joke, story, translate, summarize, help, chat,
set_afk, start_giveaway, create_poll, setup_server, backup_server,
add_word_filter, add_note, suggestion, horoscope, riddle, wouldyourather,
truthordare, debate, pickupline, remind, birthday, confession, rep,
server_health, activity_stats, mod_stats

JSON response ONLY:
{{
    "command": "create_channel|delete_channel|create_role|delete_role|create_category|delete_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|add_role_to_user|remove_role_from_user|start_giveaway|create_poll|set_afk|backup_server|setup_server|summarize|translate|add_word_filter|remove_word_filter|enable_feature|disable_feature|add_note|get_notes|set_autorole|raid_mode|trivia|wouldyourather|eightball|roast|compliment|dadjoke|ship|rate|fact|truthordare|story|debate|riddle|pickupline|horoscope|remind|birthday|confession|rep|server_health|activity_stats|mod_stats|suggestion|changelog|cleanup|quarantine|unquarantine|help|chat|unknown",
    "needs_confirmation": true or false,
    "confirmation_message": "Detailed message of what will happen",
    "confidence": 0.0 to 1.0,
    "params": {{
        "name": "name or null",
        "target_user_id": "EXACT user ID from mentions or null",
        "target_user_name": "EXACT username or null",
        "target_user2": "second user for ship etc or null",
        "reason": "reason or null",
        "duration": "number or null",
        "category": "category or null",
        "color": "hex or null",
        "private": false,
        "amount": "number or null",
        "prize": "prize or null",
        "winners": "number or null",
        "question": "question or null",
        "options": null,
        "language": "language or null",
        "text": "text or null",
        "feature": "feature or null",
        "word": "word or null",
        "note": "note or null",
        "channel": "channel or null",
        "topic": "topic or null",
        "reminder_time": "minutes or null",
        "birthday_date": "date or null",
        "confession_text": "text or null",
        "rating_target": "thing to rate or null",
        "zodiac": "sign or null"
    }}
}}"""

    return await ask_groq_json(prompt)

# ============ SECTION 11 - SAFE MEMBER FINDER ============
def find_member_strict(guild, params):
    """Strictly find a member - NO guessing"""
    # Try by ID first (most accurate)
    uid = params.get("target_user_id")
    if uid:
        try:
            member = guild.get_member(int(uid))
            if member:
                return member
        except:
            pass

    # Try exact name match
    name = params.get("target_user_name")
    if name:
        name_clean = name.lower().strip().replace("@", "")
        for m in guild.members:
            if m.name.lower() == name_clean or m.display_name.lower() == name_clean:
                return m

    return None

# ============ SECTION 12 - FUN COMMANDS ============
async def do_trivia(message, gid, uid):
    trivia = await ask_groq_json("""Generate a trivia question. JSON only:
{"question":"the question","correct":"answer","wrong1":"wrong","wrong2":"wrong","wrong3":"wrong","category":"category","difficulty":"easy|medium|hard"}""")
    if not trivia:
        return "❌ Could not generate trivia!"
    answers = [trivia["correct"], trivia["wrong1"], trivia["wrong2"], trivia["wrong3"]]
    random.shuffle(answers)
    correct_idx = answers.index(trivia["correct"])
    emojis = ["🇦","🇧","🇨","🇩"]
    embed = discord.Embed(title=f"🧠 Trivia - {trivia['category']}", description=trivia["question"], color=discord.Color.blue())
    embed.add_field(name="Options", value="\n".join(f"{emojis[i]} {a}" for i, a in enumerate(answers)), inline=False)
    embed.set_footer(text="React with your answer! 30 seconds!")
    msg = await message.channel.send(embed=embed)
    for e in emojis[:4]:
        await msg.add_reaction(e)
    trivia_sessions[msg.id] = {"correct_emoji": emojis[correct_idx], "correct_answer": trivia["correct"],
        "user_id": uid, "guild_id": gid, "answered": []}
    await asyncio.sleep(30)
    if msg.id in trivia_sessions:
        await message.channel.send(embed=discord.Embed(title="⏰ Time's Up!",
            description=f"Answer: **{trivia['correct']}**", color=discord.Color.green()))
        del trivia_sessions[msg.id]
    return None

async def do_fun_embed(fun_type, params, author):
    prompts = {
        "wouldyourather": ("Generate a fun Would You Rather question for Discord.", "🤔 Would You Rather?"),
        "eightball": (f"Magic 8ball answer for: '{params.get('question','...')}'. Mystical, brief.", "🎱 Magic 8-Ball"),
        "roast": (f"Playful roast of {params.get('target_user_name', 'someone')}. Fun not mean. 2-3 sentences.", "🔥 Roast"),
        "compliment": (f"Genuine heartfelt compliment for {params.get('target_user_name', author.name)}. 2-3 sentences.", "💝 Compliment"),
        "dadjoke": ("Tell a dad joke. Groan worthy.", "👨 Dad Joke"),
        "ship": (f"Love compatibility between {params.get('target_user_name','user1')} and {params.get('target_user2','user2')}. Percentage + ship name.", "💕 Ship"),
        "rate": (f"Rate '{params.get('rating_target','life')}' out of 10 with funny explanation.", "⭐ Rating"),
        "fact": ("Share a random surprising fact. 2-3 sentences.", "🤯 Random Fact"),
        "truthordare": (f"Give a fun {'truth question' if random.choice([True,False]) else 'dare'} for Discord.", "🎯 Truth or Dare"),
        "story": (f"Write a short story {('about '+params.get('text','')) if params.get('text') else ''}. 150 words.", "📖 Story"),
        "riddle": ("Give a riddle with answer. Format: Riddle: ... Answer: ...", "🧩 Riddle"),
        "pickupline": ("Give a creative funny pickup line.", "😘 Pickup Line"),
        "horoscope": (f"Fun horoscope for {params.get('zodiac','Aries')} today. 3-4 sentences.", f"⭐ {params.get('zodiac','Aries')} Horoscope"),
    }
    prompt_text, title = prompts.get(fun_type, ("Tell a joke.", "😄 Fun"))
    result = await ask_groq(prompt_text, "You are a fun Discord bot.")
    if result:
        colors = {"roast": discord.Color.red(), "compliment": discord.Color.pink(),
            "ship": discord.Color.red(), "fact": discord.Color.teal(),
            "horoscope": discord.Color.purple()}
        embed = discord.Embed(title=title, description=result,
            color=colors.get(fun_type, discord.Color.blue()))
        embed.set_footer(text=f"Asked by {author.display_name}")
        return embed
    return None

# ============ SECTION 13 - COMMAND EXECUTOR ============
async def execute_command(parsed, message, guild, author):
    command = parsed.get("command", "unknown")
    params = parsed.get("params", {})
    settings = get_guild_settings(guild.id)

    try:
        # ---- SERVER MANAGEMENT ----
        if command == "create_channel":
            name = (params.get("name") or "new-channel").lower().replace(" ", "-")
            existing = discord.utils.get(guild.text_channels, name=name)
            if existing:
                return f"⏭️ {existing.mention} already exists!"
            cat = None
            if params.get("category"):
                cat = discord.utils.get(guild.categories, name=params["category"])
                if not cat:
                    cat = await guild.create_category(name=params["category"])
            overwrites = {}
            if params.get("private"):
                overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
            ch = await guild.create_text_channel(name=name, category=cat,
                topic=params.get("topic",""), overwrites=overwrites)
            return f"✅ Created {ch.mention}!"

        elif command == "delete_channel":
            name = (params.get("name") or params.get("channel") or "").lower().replace(" ", "-")
            ch = discord.utils.get(guild.text_channels, name=name)
            if not ch:
                return f"❌ Channel **#{name}** not found."
            await ch.delete(reason=f"Deleted by {author.name}")
            return f"🗑️ Deleted **#{name}**!"

        elif command == "create_role":
            name = params.get("name") or "New Role"
            existing = discord.utils.get(guild.roles, name=name)
            if existing:
                return f"⏭️ Role **{name}** already exists!"
            color = discord.Color.default()
            if params.get("color"):
                try:
                    color = discord.Color(int(params["color"].replace("#",""), 16))
                except:
                    pass
            role = await guild.create_role(name=name, color=color,
                hoist=params.get("hoist", False), mentionable=params.get("mentionable", False))
            return f"✅ Created role {role.mention}!"

        elif command == "delete_role":
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not role:
                return "❌ Role not found."
            await role.delete()
            return f"🗑️ Deleted role **{params.get('name')}**!"

        elif command == "create_category":
            name = params.get("name") or "New Category"
            existing = discord.utils.get(guild.categories, name=name)
            if existing:
                return f"⏭️ Category **{name}** already exists!"
            await guild.create_category(name=name)
            return f"✅ Created category **{name}**!"

        elif command == "delete_category":
            cat = discord.utils.get(guild.categories, name=params.get("name"))
            if not cat:
                return "❌ Category not found."
            await cat.delete()
            return f"🗑️ Deleted category!"

        # ---- MODERATION ----
        elif command == "ban_user":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found. Please @mention them directly!"
            if target.id == author.id:
                return "❌ You can't ban yourself!"
            if target.id == guild.me.id:
                return "❌ I can't ban myself!"
            reason = params.get("reason") or "No reason provided"
            try:
                await target.send(embed=discord.Embed(title="🔨 Banned",
                    description=f"You were banned from **{guild.name}**\nReason: {reason}",
                    color=discord.Color.dark_red()))
            except:
                pass
            await guild.ban(target, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "BAN", reason, author.id)
            add_warning(target.id, guild.id, reason, "critical")
            embed = discord.Embed(title="🔨 User Banned", color=discord.Color.dark_red(), timestamp=datetime.now())
            embed.add_field(name="User", value=f"{target} ({target.id})", inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"🔨 Banned **{target.name}**! Reason: {reason}"

        elif command == "kick_user":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found. Please @mention them directly!"
            if target.id == author.id:
                return "❌ You can't kick yourself!"
            if target.id == guild.me.id:
                return "❌ I can't kick myself!"
            reason = params.get("reason") or "No reason provided"
            try:
                await target.send(embed=discord.Embed(title="👢 Kicked",
                    description=f"You were kicked from **{guild.name}**\nReason: {reason}",
                    color=discord.Color.orange()))
            except:
                pass
            await guild.kick(target, reason=f"{author.name}: {reason}")
            log_mod_action(target.id, guild.id, "KICK", reason, author.id)
            embed = discord.Embed(title="👢 User Kicked", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="User", value=f"{target} ({target.id})", inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"👢 Kicked **{target.name}**!"

        elif command == "mute_user":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found. Please @mention them!"
            duration = int(params.get("duration") or 10)
            reason = params.get("reason") or "No reason"
            until = datetime.now() + timedelta(minutes=duration)
            await target.timeout(until, reason=reason)
            log_mod_action(target.id, guild.id, "MUTE", reason, author.id)
            add_warning(target.id, guild.id, reason, "medium")
            try:
                await target.send(embed=discord.Embed(title="🔇 Muted",
                    description=f"Muted in **{guild.name}** for {duration} min\nReason: {reason}",
                    color=discord.Color.orange()))
            except:
                pass
            embed = discord.Embed(title="🔇 User Muted", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="User", value=target.mention, inline=True)
            embed.add_field(name="Duration", value=f"{duration} min", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"🔇 Muted **{target.name}** for {duration} minutes!"

        elif command == "unmute_user":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found."
            await target.timeout(None)
            return f"🔊 Unmuted **{target.name}**!"

        elif command == "warn_user":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found. Please @mention them!"
            reason = params.get("reason") or "No reason"
            wc = add_warning(target.id, guild.id, reason, "manual")
            log_mod_action(target.id, guild.id, "WARN", reason, author.id)
            try:
                await target.send(embed=discord.Embed(title="⚠️ Warning",
                    description=f"Warning in **{guild.name}**\nReason: {reason}\nWarnings: {wc}/{settings.get('warn_ban',5)}",
                    color=discord.Color.yellow()))
            except:
                pass
            embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow(), timestamp=datetime.now())
            embed.add_field(name="User", value=target.mention, inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Total", value=f"{wc}/{settings.get('warn_ban',5)}", inline=True)
            await alert_mods(guild, embed)
            return f"⚠️ Warned **{target.name}** ({wc} warnings)"

        elif command == "clear_warnings":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found."
            clear_warnings(target.id, guild.id)
            return f"✅ Cleared warnings for **{target.name}**!"

        elif command == "warn_check":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found."
            warns = get_warnings(target.id, guild.id)
            if not warns:
                return f"✅ **{target.name}** has no warnings!"
            lines = [f"**{target.name}** - {len(warns)} warnings:"]
            for i, w in enumerate(warns[:5], 1):
                lines.append(f"#{i} [{w['severity'].upper()}] {w['reason']} - {w['timestamp'][:10]}")
            return "\n".join(lines)

        elif command == "quarantine":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found."
            reason = params.get("reason") or "Suspicious activity"
            q_role = discord.utils.get(guild.roles, name="Quarantined")
            if not q_role:
                q_role = await guild.create_role(name="Quarantined", color=discord.Color.dark_gray())
                for ch in guild.text_channels:
                    try:
                        await ch.set_permissions(q_role, send_messages=False, add_reactions=False)
                    except:
                        pass
            await target.add_roles(q_role, reason=reason)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO quarantine (user_id,guild_id,reason,timestamp) VALUES (?,?,?,?)",
                (str(target.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            embed = discord.Embed(title="🔒 User Quarantined", color=discord.Color.dark_gray(), timestamp=datetime.now())
            embed.add_field(name="User", value=target.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            await alert_mods(guild, embed)
            return f"🔒 Quarantined **{target.name}**!"

        elif command == "unquarantine":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found."
            q_role = discord.utils.get(guild.roles, name="Quarantined")
            if q_role and q_role in target.roles:
                await target.remove_roles(q_role)
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM quarantine WHERE user_id=? AND guild_id=?",
                (str(target.id), str(guild.id)))
            conn.commit()
            conn.close()
            return f"✅ Unquarantined **{target.name}**!"

        elif command == "lock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
            await ch.set_permissions(guild.default_role, send_messages=False)
            return f"🔒 Locked {ch.mention}!"

        elif command == "unlock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
            await ch.set_permissions(guild.default_role, send_messages=None)
            return f"🔓 Unlocked {ch.mention}!"

        elif command == "lockdown":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=False)
                    count += 1
                except:
                    pass
            embed = discord.Embed(title="🔒 SERVER LOCKDOWN", description=f"By {author.mention}",
                color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="Channels", value=str(count))
            await alert_mods(guild, embed)
            return f"🔒 Server locked! {count} channels."

        elif command == "unlock_server":
            count = 0
            for ch in guild.text_channels:
                try:
                    await ch.set_permissions(guild.default_role, send_messages=None)
                    count += 1
                except:
                    pass
            return f"🔓 Server unlocked! {count} channels."

        elif command == "slowmode":
            dur = int(params.get("duration") or 5)
            ch = message.channel
            await ch.edit(slowmode_delay=dur)
            return f"🐌 Slowmode: {dur}s in {ch.mention}!"

        elif command == "purge":
            amount = min(int(params.get("amount") or 10), 100)
            deleted = await message.channel.purge(limit=amount + 1)
            return f"🗑️ Deleted {len(deleted)-1} messages!"

        elif command == "add_role_to_user":
            target = find_member_strict(guild, params)
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not target or not role:
                return "❌ User or role not found."
            await target.add_roles(role)
            return f"✅ Added **{role.name}** to {target.mention}!"

        elif command == "remove_role_from_user":
            target = find_member_strict(guild, params)
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not target or not role:
                return "❌ User or role not found."
            await target.remove_roles(role)
            return f"✅ Removed **{role.name}** from {target.mention}!"

        # ---- FUN ----
        elif command == "trivia":
            await do_trivia(message, guild.id, author.id)
            return None

        elif command == "wouldyourather":
            embed = await do_fun_embed("wouldyourather", params, author)
            if embed:
                msg = await message.channel.send(embed=embed)
                await msg.add_reaction("🅰️")
                await msg.add_reaction("🅱️")
            return None

        elif command == "debate":
            topic = params.get("text") or params.get("question") or "pineapple on pizza"
            result = await ask_groq(f"Start a debate about: {topic}. Present both sides. Ask channel to vote.", "You are a debate moderator.")
            if result:
                embed = discord.Embed(title=f"⚔️ Debate: {topic}", description=result, color=discord.Color.orange())
                msg = await message.channel.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
            return None

        elif command in ["eightball","roast","compliment","dadjoke","ship","rate","fact","truthordare","story","riddle","pickupline","horoscope"]:
            embed = await do_fun_embed(command, params, author)
            if embed:
                await message.channel.send(embed=embed)
            return None

        # ---- NEW FEATURES ----
        elif command == "remind":
            reminder_text = params.get("text") or params.get("note") or "Reminder!"
            minutes = int(params.get("reminder_time") or params.get("duration") or 10)
            remind_time = datetime.now() + timedelta(minutes=minutes)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reminders (user_id,guild_id,channel_id,reminder,remind_time) VALUES (?,?,?,?,?)",
                (str(author.id), str(guild.id), str(message.channel.id), reminder_text, remind_time.isoformat()))
            conn.commit()
            conn.close()
            return f"⏰ I'll remind you in {minutes} minutes: **{reminder_text}**"

        elif command == "birthday":
            date = params.get("birthday_date") or params.get("text")
            if not date:
                return "❌ Please tell me your birthday! E.g. 'my birthday is January 15'"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO birthdays (user_id,guild_id,birthday) VALUES (?,?,?)",
                (str(author.id), str(guild.id), date))
            conn.commit()
            conn.close()
            return f"🎂 Birthday set to **{date}**!"

        elif command == "confession":
            text = params.get("confession_text") or params.get("text")
            if not text:
                return "❌ What's your confession?"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO confessions (guild_id,confession,timestamp) VALUES (?,?,?)",
                (str(guild.id), text, datetime.now().isoformat()))
            c.execute("SELECT last_insert_rowid()")
            confession_id = c.fetchone()[0]
            conn.commit()
            conn.close()
            embed = discord.Embed(title=f"🤫 Anonymous Confession #{confession_id}",
                description=text, color=discord.Color.dark_purple(), timestamp=datetime.now())
            embed.set_footer(text="Sent anonymously via SentinelMod")
            await message.channel.send(embed=embed)
            try:
                await message.delete()
            except:
                pass
            return None

        elif command == "rep":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ Who do you want to give rep to? @mention them!"
            if target.id == author.id:
                return "❌ You can't rep yourself!"
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO reputation (user_id,guild_id,rep) VALUES (?,?,1)
                ON CONFLICT(user_id,guild_id) DO UPDATE SET rep=rep+1""",
                (str(target.id), str(guild.id)))
            conn.commit()
            c.execute("SELECT rep FROM reputation WHERE user_id=? AND guild_id=?",
                (str(target.id), str(guild.id)))
            rep = c.fetchone()[0]
            conn.close()
            return f"✅ +1 rep to **{target.name}**! Total: **{rep}** rep"

        # ---- SERVER FEATURES ----
        elif command == "start_giveaway":
            prize = params.get("prize") or "Mystery Prize"
            duration = int(params.get("duration") or 60)
            winners = int(params.get("winners") or 1)
            end_time = datetime.now() + timedelta(minutes=duration)
            embed = discord.Embed(title="🎉 GIVEAWAY!", description=f"**Prize:** {prize}\nReact 🎉!",
                color=discord.Color.gold(), timestamp=end_time)
            embed.add_field(name="Winners", value=str(winners), inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            msg = await message.channel.send(embed=embed)
            await msg.add_reaction("🎉")
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO giveaways (guild_id,channel_id,message_id,prize,winners,end_time,host_id) VALUES (?,?,?,?,?,?,?)",
                (str(guild.id), str(message.channel.id), str(msg.id), prize, winners, end_time.isoformat(), str(author.id)))
            conn.commit()
            conn.close()
            return f"🎉 Giveaway started for **{prize}**!"

        elif command == "create_poll":
            question = params.get("question") or "Poll"
            options = params.get("options") or ["Yes", "No"]
            emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
            embed = discord.Embed(title=f"📊 {question}", color=discord.Color.blue())
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
            c.execute("INSERT OR REPLACE INTO afk_users (user_id,guild_id,reason,timestamp) VALUES (?,?,?,?)",
                (str(author.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💤 AFK set: **{reason}**"

        elif command == "backup_server":
            roles_data = [{"name":r.name,"color":str(r.color),"hoist":r.hoist} for r in guild.roles if r.name != "@everyone"]
            channels_data = [{"name":c.name,"topic":c.topic,"category":c.category.name if c.category else None} for c in guild.text_channels]
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO backup_data (guild_id,backup_type,data,timestamp) VALUES (?,?,?,?)",
                (str(guild.id), "full", json.dumps({"roles":roles_data,"channels":channels_data}), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💾 Backed up {len(roles_data)} roles and {len(channels_data)} channels!"

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
                return "❌ No messages."
            summary = await ask_groq("Summarize in 3-5 bullet points:\n\n" + "\n".join(reversed(msgs)), "Summarize concisely.")
            return f"📝 **Summary:**\n{summary}"

        elif command == "translate":
            text = params.get("text") or ""
            lang = params.get("language") or "English"
            if not text:
                return "❌ No text."
            t = await ask_groq(f"Translate to {lang}. ONLY the translation:\n{text}", "Translator.")
            return f"🌐 **({lang}):** {t}"

        elif command == "add_word_filter":
            word = params.get("word")
            if not word:
                return "❌ No word."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO word_filters (guild_id,word) VALUES (?,?)", (str(guild.id), word.lower()))
            conn.commit()
            conn.close()
            return f"✅ Added **{word}** to filter!"

        elif command == "remove_word_filter":
            word = params.get("word")
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (str(guild.id), word.lower()))
            conn.commit()
            conn.close()
            return f"✅ Removed **{word}**!"

        elif command == "add_note":
            target = find_member_strict(guild, params)
            note = params.get("note") or params.get("text")
            if not target or not note:
                return "❌ Specify user and note."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO user_notes (guild_id,user_id,note,mod_id,timestamp) VALUES (?,?,?,?,?)",
                (str(guild.id), str(target.id), note, str(author.id), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"📝 Note added for **{target.name}**!"

        elif command == "get_notes":
            target = find_member_strict(guild, params)
            if not target:
                return "❌ User not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM user_notes WHERE guild_id=? AND user_id=?", (str(guild.id), str(target.id)))
            notes = c.fetchall()
            conn.close()
            if not notes:
                return f"📝 No notes for **{target.name}**."
            return "\n".join([f"📝 **{target.name}:**"] + [f"• {n['note']}" for n in notes])

        elif command == "set_autorole":
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not role:
                return "❌ Role not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO auto_roles (guild_id,role_id) VALUES (?,?)", (str(guild.id), str(role.id)))
            conn.commit()
            conn.close()
            return f"✅ **{role.name}** = auto role for new members!"

        elif command == "raid_mode":
            text = (params.get("feature") or params.get("text") or "").lower()
            status = "on" in text or "enable" in text
            raid_mode_active[guild.id] = status
            return f"🚨 Raid mode **{'ON' if status else 'OFF'}**!"

        elif command == "server_health":
            total = guild.member_count
            bots = sum(1 for m in guild.members if m.bot)
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (str(guild.id),))
            warns = c.fetchone()[0]
            conn.close()
            score = max(0, 100 - (warns // 5))
            embed = discord.Embed(title="🏥 Server Health", color=discord.Color.green() if score > 70 else discord.Color.orange())
            embed.add_field(name="Score", value=f"{score}/100", inline=True)
            embed.add_field(name="Members", value=str(total - bots), inline=True)
            embed.add_field(name="Bots", value=str(bots), inline=True)
            embed.add_field(name="Warnings", value=str(warns), inline=True)
            embed.add_field(name="Raid Mode", value="🔴" if raid_mode_active[guild.id] else "🟢", inline=True)
            await message.channel.send(embed=embed)
            return None

        elif command == "activity_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id,message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 10",
                (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "📊 No activity data yet!"
            medals = ["🥇","🥈","🥉"]
            lines = []
            for i, r in enumerate(top):
                m = guild.get_member(int(r["user_id"]))
                name = m.display_name if m else "Unknown"
                medal = medals[i] if i < 3 else f"#{i+1}"
                lines.append(f"{medal} {name}: **{r['message_count']}** msgs")
            embed = discord.Embed(title="📊 Activity", description="\n".join(lines), color=discord.Color.blue())
            await message.channel.send(embed=embed)
            return None

        elif command == "mod_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT mod_id,COUNT(*) as t FROM mod_actions WHERE guild_id=? GROUP BY mod_id ORDER BY t DESC LIMIT 5",
                (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "🛡️ No mod actions yet!"
            lines = []
            for i, r in enumerate(top, 1):
                m = guild.get_member(int(r["mod_id"]))
                lines.append(f"#{i} {m.display_name if m else 'Unknown'}: **{r['t']}** actions")
            embed = discord.Embed(title="🛡️ Mod Leaderboard", description="\n".join(lines), color=discord.Color.red())
            await message.channel.send(embed=embed)
            return None

        elif command == "suggestion":
            text = params.get("text") or params.get("note")
            if not text:
                return "❌ No suggestion."
            sug_ch = discord.utils.get(guild.text_channels, name="suggestions")
            if sug_ch:
                embed = discord.Embed(title="💡 Suggestion", description=text, color=discord.Color.blue())
                embed.set_footer(text=f"By {author.display_name}")
                msg = await sug_ch.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
                return f"✅ Suggestion posted in {sug_ch.mention}!"
            return "❌ No suggestions channel."

        elif command in ["enable_feature", "disable_feature"]:
            feature = (params.get("feature") or "").lower().replace(" ", "_")
            val = 1 if command == "enable_feature" else 0
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(f"UPDATE guild_settings SET {feature}=? WHERE guild_id=?", (val, str(guild.id)))
                conn.commit()
                return f"{'✅ Enabled' if val else '❌ Disabled'} **{feature}**!"
            except:
                return f"❌ Unknown feature: {feature}"
            finally:
                conn.close()

        elif command == "help":
            embed = discord.Embed(title="🛡️ SentinelMod Help", description="@mention me or chat in #sentinel-bot!", color=discord.Color.blue())
            embed.add_field(name="🔧 Server", value="make/delete channel, role, category", inline=False)
            embed.add_field(name="🔨 Mod", value="ban, kick, mute, warn, purge, lock, lockdown, quarantine", inline=False)
            embed.add_field(name="🎮 Fun", value="trivia, roast, compliment, 8ball, ship, rate, riddle, truth/dare", inline=False)
            embed.add_field(name="🤖 AI", value="summarize, translate, story, debate, confess", inline=False)
            embed.add_field(name="📊 Info", value="server health, activity, mod stats, remind, birthday", inline=False)
            embed.add_field(name="🎭 Personality", value="/personality or /setpersonality", inline=False)
            await message.channel.send(embed=embed)
            return None

        else:
            return None

    except discord.Forbidden:
        return "❌ I don't have permission!"
    except Exception as e:
        print(f"Execute error: {e}")
        return f"❌ Error: {str(e)[:100]}"

# ============ SECTION 14 - MODERATION SYSTEMS ============
async def alert_mods(guild, embed, ch_name=None):
    settings = get_guild_settings(guild.id)
    ch = discord.utils.get(guild.text_channels, name=ch_name or settings["log_channel"])
    mod_role = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    if ch:
        await ch.send(content=mod_role.mention if mod_role else "", embed=embed)

async def check_spam(msg, settings):
    key = f"{msg.author.id}:{msg.guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    w = settings.get("spam_window", 5)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < w]
    return len(spam_tracker[key]) >= settings.get("spam_limit", 5)

async def handle_spam(msg, settings):
    u = msg.author
    g = msg.guild
    try:
        await msg.channel.purge(limit=10, check=lambda m: m.author == u)
    except:
        pass
    try:
        await u.timeout(datetime.now() + timedelta(minutes=settings.get("mute_duration", 10)), reason="Spam")
    except:
        pass
    wc = add_warning(u.id, g.id, "Spam", "medium")
    log_mod_action(u.id, g.id, "SPAM_MUTE", "Spam", bot.user.id)
    try:
        await u.send(embed=discord.Embed(title="⚠️ Spam Detected", description=f"Muted in **{g.name}**", color=discord.Color.orange()))
    except:
        pass
    embed = discord.Embed(title="🔇 Spam Handled", color=discord.Color.orange(), timestamp=datetime.now())
    embed.add_field(name="User", value=u.mention, inline=True)
    embed.add_field(name="Warnings", value=str(wc), inline=True)
    await alert_mods(g, embed)

async def check_raid(member):
    g = member.guild
    settings = get_guild_settings(g.id)
    now = time.time()
    raid_tracker[g.id].append({"time": now, "member": member})
    w = settings.get("raid_window", 10)
    raid_tracker[g.id] = [j for j in raid_tracker[g.id] if now - j["time"] < w]
    return len(raid_tracker[g.id]) >= settings.get("raid_limit", 10)

async def handle_raid(guild, member):
    settings = get_guild_settings(guild.id)
    if not raid_mode_active[guild.id]:
        raid_mode_active[guild.id] = True
        ch = discord.utils.get(guild.text_channels, name=settings["raid_channel"])
        mr = discord.utils.get(guild.roles, name=settings["mod_role_name"])
        if ch:
            await ch.send(content=f"🚨 {mr.mention if mr else ''} RAID DETECTED!",
                embed=discord.Embed(title="🚨 RAID DETECTED", color=discord.Color.red()))
        await asyncio.sleep(300)
        raid_mode_active[guild.id] = False
    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    if age < settings.get("min_account_age", 7):
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
    embed = discord.Embed(title="💣 NUKE STOPPED", description=f"**{executor}** banned!",
        color=discord.Color.dark_red(), timestamp=datetime.now())
    ch = discord.utils.get(guild.text_channels, name="sentinel-nuke-alerts")
    if ch:
        mr = discord.utils.get(guild.roles, name=get_guild_settings(guild.id)["mod_role_name"])
        await ch.send(content=mr.mention if mr else "", embed=embed)

async def check_patterns(msg, settings):
    content = msg.content
    cl = content.lower()
    now = time.time()
    key = f"{msg.author.id}:{msg.guild.id}"

    checks = [
        (settings.get("phone_filter",1), r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b', "phone_number", "Phone number", "high"),
        (settings.get("email_filter",1), r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "email", "Email address", "high"),
    ]
    for enabled, pattern, ptype, reason, severity in checks:
        if enabled and re.search(pattern, content):
            return ptype, reason, severity

    keywords = [
        (settings.get("fake_nitro_filter",1), ["free nitro","discord nitro free","claim nitro"], "fake_nitro", "Fake Nitro scam", "critical"),
        (settings.get("token_filter",1), ["discord token","grab token","token logger","grabify.link"], "token_grab", "Token grabber", "critical"),
        (settings.get("scam_filter",1), ["you won","claim your prize","click here to claim","your account will be deleted"], "scam", "Scam", "critical"),
        (settings.get("anti_advertisement",1), ["join my server","check out my server","subscribe to my"], "advertisement", "Advertisement", "medium"),
        (settings.get("nsfw_text_filter",1), ["how old are you","send me a pic","don't tell your parents","keep this secret"], "grooming", "Grooming pattern", "critical"),
        (1, ["i will expose you","pay me or","i know where you live","send me money or"], "blackmail", "Blackmail", "critical"),
        (1, ["want to kill myself","want to die","going to hurt myself","end my life"], "self_harm", "Self-harm content", "high"),
        (1, ["death to all","kill all","exterminate","purge the"], "extremism", "Extremism", "critical"),
        (1, ["i'm from discord","official discord","your account has been flagged","verify your account"], "social_engineering", "Social engineering", "critical"),
    ]
    for enabled, words, ptype, reason, severity in keywords:
        if enabled and any(w in cl for w in words):
            return ptype, reason, severity

    if settings.get("zalgo_filter",1):
        if sum(1 for c in content if unicodedata.combining(c)) > 10:
            return "zalgo", "Zalgo text", "medium"

    if settings.get("caps_filter",1) and len(content) > 10:
        if sum(1 for c in content if c.isupper()) / len(content) > 0.7:
            return "caps", "Excessive caps", "low"

    if settings.get("mention_spam",1) and len(msg.mentions) >= 5:
        return "mention_spam", "Mention spam", "high"

    if settings.get("everyone_block",0) and ("@everyone" in content or "@here" in content):
        return "everyone", "Everyone mention", "medium"

    if settings.get("invite_block",0) and re.search(r'(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', content):
        return "invite", "Invite link", "medium"

    if settings.get("link_scan",1) and "http" in cl:
        bad = ["grabify","iplogger","discord.gift","steamcommunity.ru","discordnitro","free-nitro","phish","dlscord","ip-logger"]
        for b in bad:
            if b in cl:
                return "phishing", f"Phishing: {b}", "critical"

    if re.search(r'(.)\1{9,}', content):
        return "repeat_chars", "Character spam", "low"

    zw = ['\u200b','\u200c','\u200d','\ufeff','\u2060']
    if sum(content.count(z) for z in zw) > 5:
        return "zero_width", "Zero-width spam", "medium"

    if settings.get("unicode_filter",1):
        try:
            norm = unicodedata.normalize("NFKC", content).lower()
            if norm != cl:
                for word in get_filtered_words(msg.guild.id):
                    if word in norm:
                        return "unicode_bypass", f"Unicode bypass: {word}", "high"
        except:
            pass

    return None, None, None

async def check_toxicity(content, context=""):
    return await ask_groq_json(f"""Analyze this Discord message for ALL harmful content.
Context: {context}
Message: "{content}"

Check: toxicity, harassment, hate speech, threats, blackmail, doxxing, grooming, scam,
social engineering, NSFW, extremism, self harm, impersonation

JSON only:
{{"toxic":true/false,"severity":"none|low|medium|high|critical","category":"none|harassment|hate_speech|threat|sexual|bullying|manipulation|slur|doxxing|grooming|scam|extremism|self_harm|blackmail","confidence":0.0-1.0,"reason":"brief","bypass_detected":true/false,"immediate_action":true/false}}""")

async def punish_user(msg, severity, reason, analysis):
    u = msg.author
    g = msg.guild
    settings = get_guild_settings(g.id)
    wc = add_warning(u.id, g.id, reason, severity)
    log_mod_action(u.id, g.id, "AI_WARN", reason, bot.user.id)
    try:
        await msg.delete()
    except:
        pass
    try:
        await msg.channel.send(embed=discord.Embed(title="🛡️ Message Removed",
            description=f"{u.mention} your message was removed.\nReason: {reason}",
            color=discord.Color.orange()), delete_after=8)
    except:
        pass
    try:
        await u.send(embed=discord.Embed(title="⚠️ Warning",
            description=f"Message removed in **{g.name}**\nReason: {reason}\nWarnings: {wc}/{settings.get('warn_ban',5)}",
            color=discord.Color.yellow()))
    except:
        pass

    colors = {"low":discord.Color.yellow(),"medium":discord.Color.orange(),"high":discord.Color.red(),"critical":discord.Color.dark_red()}
    embed = discord.Embed(title="🚨 AI Alert", color=colors.get(severity, discord.Color.red()), timestamp=datetime.now())
    embed.add_field(name="User", value=f"{u.mention} ({u.id})", inline=True)
    embed.add_field(name="Channel", value=msg.channel.mention, inline=True)
    embed.add_field(name="Severity", value=severity.upper(), inline=True)
    embed.add_field(name="Category", value=analysis.get("category","?"), inline=True)
    embed.add_field(name="Confidence", value=f"{analysis.get('confidence',0)*100:.0f}%", inline=True)
    embed.add_field(name="Warnings", value=f"{wc}/{settings.get('warn_ban',5)}", inline=True)
    embed.add_field(name="Message", value=f"||{msg.content[:400]}||", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    action = "⚠️ Warning"
    if wc >= settings.get("warn_mute",3) and wc < settings.get("warn_ban",5):
        try:
            await u.timeout(datetime.now() + timedelta(minutes=settings.get("mute_duration",10)), reason=reason)
            action = f"🔇 Muted {settings.get('mute_duration',10)} min"
        except:
            pass
    if wc >= settings.get("warn_ban",5):
        try:
            await g.ban(u, reason=f"AI: {reason}")
            action = "🔨 BANNED"
        except:
            pass
    if analysis.get("immediate_action") and severity == "critical":
        try:
            await g.ban(u, reason=f"IMMEDIATE: {reason}")
            action = "🔨 IMMEDIATELY BANNED"
        except:
            pass
    embed.add_field(name="Action", value=action, inline=False)
    await alert_mods(g, embed)

# ============ SECTION 15 - SETUP & VIEWS ============
async def setup_server(guild):
    results = []
    settings = get_guild_settings(guild.id)
    for rn, color, hoist in [(settings["mod_role_name"], discord.Color.red(), True),
        ("Muted", discord.Color.dark_gray(), False), ("Member", discord.Color.blue(), False),
        ("Quarantined", discord.Color.dark_gray(), False)]:
        if not discord.utils.get(guild.roles, name=rn):
            try:
                await guild.create_role(name=rn, color=color, hoist=hoist, mentionable=True)
                results.append(f"✅ Role: **{rn}**")
            except:
                results.append(f"❌ Role: **{rn}**")
        else:
            results.append(f"⏭️ Role: **{rn}**")

    mr = discord.utils.get(guild.roles, name=settings["mod_role_name"])
    scat = discord.utils.get(guild.categories, name="🛡️ SENTINELAI")
    if not scat:
        try:
            ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
            if mr:
                ow[mr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            scat = await guild.create_category(name="🛡️ SENTINELAI", overwrites=ow)
            results.append("✅ Category: **🛡️ SENTINELAI**")
        except:
            results.append("❌ Category")

    for cn, topic in [(settings["log_channel"],"Mod logs"),(settings["raid_channel"],"Raid alerts"),
        ("sentinel-nuke-alerts","Nuke alerts"),("sentinel-bot","Chat with SentinelMod AI!")]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, category=scat, topic=topic)
                results.append(f"✅ #{cn}")
            except:
                results.append(f"❌ #{cn}")
        else:
            results.append(f"⏭️ #{cn}")

    for cn, topic in [("welcome","Welcome!"),("rules","Rules"),("general","General"),
        ("announcements","Announcements"),("suggestions","Suggestions")]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, topic=topic)
                results.append(f"✅ #{cn}")
            except:
                results.append(f"❌ #{cn}")
        else:
            results.append(f"⏭️ #{cn}")

    tcat = discord.utils.get(guild.categories, name="🎫 TICKETS")
    if not tcat:
        try:
            tcat = await guild.create_category(name="🎫 TICKETS")
        except:
            pass
    tch = discord.utils.get(guild.text_channels, name="create-ticket")
    if not tch and tcat:
        try:
            tch = await guild.create_text_channel(name="create-ticket", category=tcat)
            await tch.send(embed=discord.Embed(title="🎫 Tickets", description="Click below!", color=discord.Color.blue()), view=TicketView())
            results.append("✅ #create-ticket")
        except:
            pass
    return results

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction, button):
        await interaction.response.send_modal(TicketModal())

class TicketModal(discord.ui.Modal, title="Support Ticket"):
    reason = discord.ui.TextInput(label="Issue", style=discord.TextStyle.long, required=True)
    async def on_submit(self, interaction):
        g = interaction.guild
        u = interaction.user
        settings = get_guild_settings(g.id)
        tcat = discord.utils.get(g.categories, name="🎫 TICKETS")
        mr = discord.utils.get(g.roles, name=settings["mod_role_name"])
        tn = f"ticket-{u.name[:10]}-{random.randint(1000,9999)}"
        ow = {g.default_role: discord.PermissionOverwrite(read_messages=False),
            u: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            g.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        if mr:
            ow[mr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            ch = await g.create_text_channel(name=tn, category=tcat, overwrites=ow)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO tickets (guild_id,user_id,channel_id,reason,timestamp) VALUES (?,?,?,?,?)",
                (str(g.id), str(u.id), str(ch.id), str(self.reason.value), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            await ch.send(content=f"{u.mention} {mr.mention if mr else ''}", embed=discord.Embed(
                title="🎫 Ticket", description=f"Issue: {self.reason.value}", color=discord.Color.blue()), view=CloseTicketView())
            await interaction.response.send_message(f"✅ {ch.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close(self, interaction, button):
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (str(interaction.channel.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message("🔒 Closing...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

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
            await interaction.response.send_message("❌ Only requester can confirm.", ephemeral=True)
            return
        await interaction.response.defer()
        result = await execute_command(self.parsed, self.msg, self.guild, self.author)
        if result:
            await interaction.followup.send(result)
        self.stop()
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction, button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Only requester can cancel.", ephemeral=True)
            return
        await interaction.response.send_message("❌ Cancelled.")
        self.stop()

# ============ SECTION 16 - PERSONALITY SLASH COMMANDS ============
@bot.tree.command(name="personality", description="Choose SentinelMod personality")
async def personality_cmd(interaction: discord.Interaction):
    categories = {
        "🎭 Characters": ["pirate","medieval","wizard","vampire","ghost","dragon","ninja","samurai","cowboy","fairy"],
        "🎬 Pop Culture": ["yoda","jarvis","deadpool","sherlock","gandalf","tony_stark","groot","gollum","darth_vader","michael_scott"],
        "😄 Moods": ["friendly","sarcastic","serious","chaotic","motivational","pessimist","optimist","hype","philosopher","therapist"],
        "🌍 Styles": ["british","australian","valley_girl","gen_z","boomer","caveman","shakespeare","surfer","anime","gamer"],
        "👔 Roles": ["professor","chef","detective","alien","time_traveler","oracle","robot","superhero","villain","mad_hatter"]
    }
    embed = discord.Embed(title="🎭 Personalities", description="Use /setpersonality with a name!", color=discord.Color.purple())
    for cat, names in categories.items():
        embed.add_field(name=cat, value=", ".join(f"`{n}`" for n in names), inline=False)
    embed.set_footer(text=f"Current: {get_user_personality(str(interaction.user.id), str(interaction.guild.id))}")
    options = [discord.SelectOption(label=n.replace("_"," ").title(), value=n, description=PERSONALITIES[n][:50])
        for n in list(PERSONALITIES.keys())[:25]]
    view = discord.ui.View(timeout=60)
    select = discord.ui.Select(placeholder="Choose...", options=options)
    async def cb(inter):
        p = inter.data["values"][0]
        set_user_personality(str(inter.user.id), str(inter.guild.id), p)
        await inter.response.send_message(f"✅ Personality: **{p.replace('_',' ').title()}**!", ephemeral=True)
    select.callback = cb
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="setpersonality", description="Set personality by name")
@app_commands.describe(personality="Name (e.g. pirate, yoda, sarcastic)")
async def setpersonality_cmd(interaction: discord.Interaction, personality: str):
    p = personality.lower().replace(" ", "_")
    if p not in PERSONALITIES:
        await interaction.response.send_message(f"❌ Unknown: **{p}**. Use /personality to see all.", ephemeral=True)
        return
    set_user_personality(str(interaction.user.id), str(interaction.guild.id), p)
    await interaction.response.send_message(f"✅ Now: **{p.replace('_',' ').title()}**!\n*{PERSONALITIES[p]}*", ephemeral=True)

# ============ SECTION 17 - BACKGROUND TASKS ============
@tasks.loop(minutes=1)
async def check_giveaways():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM giveaways WHERE active=1 AND end_time<=?", (datetime.now().isoformat(),))
    ended = [dict(r) for r in c.fetchall()]
    conn.close()
    for gw in ended:
        try:
            g = bot.get_guild(int(gw["guild_id"]))
            ch = g.get_channel(int(gw["channel_id"])) if g else None
            msg = await ch.fetch_message(int(gw["message_id"])) if ch else None
            if not msg:
                continue
            rx = discord.utils.get(msg.reactions, emoji="🎉")
            users = [u async for u in rx.users() if not u.bot] if rx else []
            if users:
                winners = random.sample(users, min(gw["winners"], len(users)))
                mentions = ", ".join(w.mention for w in winners)
                await ch.send(content=f"🎉 {mentions}!", embed=discord.Embed(
                    title="🎉 Giveaway Ended!", description=f"**Prize:** {gw['prize']}\n**Winners:** {mentions}",
                    color=discord.Color.gold()))
            else:
                await ch.send("❌ No entries!")
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE giveaways SET active=0 WHERE id=?", (gw["id"],))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"GW error: {e}")

@tasks.loop(minutes=1)
async def check_reminders():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM reminders WHERE active=1 AND remind_time<=?", (datetime.now().isoformat(),))
    due = [dict(r) for r in c.fetchall()]
    for rem in due:
        try:
            g = bot.get_guild(int(rem["guild_id"]))
            ch = g.get_channel(int(rem["channel_id"])) if g else None
            if ch:
                await ch.send(f"⏰ <@{rem['user_id']}> Reminder: **{rem['reminder']}**")
        except:
            pass
        c.execute("UPDATE reminders SET active=0 WHERE id=?", (rem["id"],))
    conn.commit()
    conn.close()

@tasks.loop(hours=24)
async def daily_cleanup():
    conn = get_db()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("DELETE FROM conversation_history WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()

# ============ SECTION 18 - BOT EVENTS ============
@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 SentinelMod ONLINE")
    print(f"📛 {bot.user}")
    print(f"🏠 {len(bot.guilds)} servers")
    print(f"🎭 {len(PERSONALITIES)} personalities")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for g in bot.guilds:
        init_guild_settings(g.id)
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} commands synced")
    except Exception as e:
        print(f"Sync error: {e}")
    check_giveaways.start()
    check_reminders.start()
    daily_cleanup.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="everything 👁️ | @mention me!"))

@bot.event
async def on_guild_join(guild):
    init_guild_settings(guild.id)
    await setup_server(guild)

@bot.event
async def on_member_join(member):
    g = member.guild
    settings = get_guild_settings(g.id)
    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
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
    if age < settings.get("min_account_age", 7):
        ch = discord.utils.get(g.text_channels, name=settings["raid_channel"])
        if ch:
            await ch.send(embed=discord.Embed(title="⚠️ Suspicious Account",
                color=discord.Color.yellow()).add_field(name="User", value=member.mention).add_field(name="Age", value=f"{age} days"))
    if settings.get("welcome_enabled", 1):
        wch = discord.utils.get(g.text_channels, name=settings.get("welcome_channel", "welcome"))
        if wch:
            welcome = await ask_groq(f"Short warm welcome for {member.display_name} joining {g.name} (member #{g.member_count}). 2 sentences.", "Friendly bot.")
            if welcome:
                embed = discord.Embed(title=f"👋 Welcome to {g.name}!", description=welcome, color=discord.Color.green())
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
            conn = get_db()
            c = conn.cursor()
            c.execute("""INSERT INTO trivia_scores (user_id,guild_id,score,total) VALUES (?,?,1,1)
                ON CONFLICT(user_id,guild_id) DO UPDATE SET score=score+1, total=total+1""",
                (str(user.id), str(s["guild_id"])))
            conn.commit()
            conn.close()
            await reaction.message.channel.send(f"✅ {user.mention} correct! **{s['correct_answer']}**")
            del trivia_sessions[reaction.message.id]

@bot.event
async def on_audit_log_entry_create(entry):
    g = entry.guild
    settings = get_guild_settings(g.id)
    if not settings.get("anti_nuke_enabled", 1):
        return
    nuke_actions = [discord.AuditLogAction.channel_delete, discord.AuditLogAction.role_delete,
        discord.AuditLogAction.ban, discord.AuditLogAction.kick, discord.AuditLogAction.webhook_create]
    if entry.action in nuke_actions and entry.user:
        mr = discord.utils.get(g.roles, name=settings["mod_role_name"])
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

    settings = get_guild_settings(message.guild.id)
    mod_role = discord.utils.get(message.guild.roles, name=settings["mod_role_name"])
    is_mod = mod_role and mod_role in message.author.roles
    is_admin = message.author.guild_permissions.administrator

    update_message_stats(message.author.id, message.guild.id)

    # ---- AFK ----
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM afk_users WHERE guild_id=?", (str(message.guild.id),))
    afk = {r["user_id"]: dict(r) for r in c.fetchall()}
    conn.close()
    if str(message.author.id) in afk:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM afk_users WHERE user_id=? AND guild_id=?",
            (str(message.author.id), str(message.guild.id)))
        conn.commit()
        conn.close()
        try:
            await message.channel.send(f"👋 Welcome back {message.author.mention}!", delete_after=5)
        except:
            pass
    for m in message.mentions:
        if str(m.id) in afk:
            await message.channel.send(f"💤 {m.mention} is AFK: **{afk[str(m.id)]['reason']}**", delete_after=10)

    # ---- CUSTOM COMMANDS ----
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM custom_commands WHERE guild_id=?", (str(message.guild.id),))
    customs = {r["trigger_word"]: r["response"] for r in c.fetchall()}
    conn.close()
    if message.content.lower() in customs:
        await message.channel.send(customs[message.content.lower()])
        return

    # ============ AI CHAT & COMMANDS ============
    is_ai_channel = message.channel.name == AI_CHAT_CHANNEL
    is_mentioned = bot.user in message.mentions

    if is_ai_channel or is_mentioned:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content and not is_ai_channel:
            await message.reply(f"👋 Hey! Try `@{BOT_NAME} help`")
            return

        if content:
            if is_mod or is_admin:
                async with message.channel.typing():
                    parsed = await parse_command(content, message.guild, message.author)

                if parsed and parsed.get("command") not in ["chat", "unknown", None]:
                    confidence = parsed.get("confidence", 0)

                    if confidence < 0.7:
                        system = get_system_prompt(str(message.author.id), str(message.guild.id))
                        history = get_conversation_history(str(message.author.id), str(message.guild.id))
                        await stream_response(message, content, system, history,
                            str(message.author.id), str(message.guild.id))
                        return

                    dangerous = ["ban_user","kick_user","mute_user","warn_user","delete_channel",
                        "delete_role","delete_category","lockdown","purge","clear_warnings","quarantine"]

                    if parsed.get("command") in dangerous:
                        target_name = parsed.get("params", {}).get("target_user_name")
                        target_id = parsed.get("params", {}).get("target_user_id")
                        if target_name or target_id:
                            target = find_member_strict(message.guild, parsed.get("params", {}))
                            if not target:
                                await message.reply(f"❌ User **{target_name or target_id}** not found. "
                                    "Please @mention them directly!")
                                return

                    needs_confirm = parsed.get("needs_confirmation", False) or parsed.get("command") in dangerous

                    if needs_confirm:
                        cmd_name = parsed.get("command","").replace("_"," ").title()
                        params = parsed.get("params", {})
                        details = []
                        if params.get("target_user_name"):
                            details.append(f"**Target:** {params['target_user_name']}")
                        if params.get("name"):
                            details.append(f"**Name:** {params['name']}")
                        if params.get("reason"):
                            details.append(f"**Reason:** {params['reason']}")
                        if params.get("duration"):
                            details.append(f"**Duration:** {params['duration']} min")

                        embed = discord.Embed(title=f"⚠️ Confirm: {cmd_name}",
                            description=parsed.get("confirmation_message","Are you sure?") +
                            "\n\n" + "\n".join(details),
                            color=discord.Color.orange())
                        embed.set_footer(text="30 seconds to confirm")
                        view = ConfirmView(parsed, message, message.guild, message.author)
                        await message.reply(embed=embed, view=view)
                    else:
                        async with message.channel.typing():
                            result = await execute_command(parsed, message, message.guild, message.author)
                        if result:
                            await message.reply(result[:2000])
                    return

            # AI Chat with streaming
            system = get_system_prompt(str(message.author.id), str(message.guild.id),
                f"Server: {message.guild.name}\nChannel: {message.channel.name}\nUser: {message.author.display_name}")
            history = get_conversation_history(str(message.author.id), str(message.guild.id))
            await stream_response(message, content, system, history,
                str(message.author.id), str(message.guild.id))
            return

    # ============ MODERATION ============
    if is_mod or is_admin:
        await bot.process_commands(message)
        return

    # Anti-spam
    if await check_spam(message, settings):
        await handle_spam(message, settings)
        return

    # Pattern checks
    ptype, preason, pseverity = await check_patterns(message, settings)
    if ptype:
        try:
            await message.delete()
        except:
            pass

        if ptype == "self_harm":
            try:
                await message.channel.send(embed=discord.Embed(title="💙 We're Here",
                    description=f"{message.author.mention} if you're struggling:\n"
                    "• **988** Suicide Prevention\n• Text **HOME** to **741741**\n• **findahelpline.com**",
                    color=discord.Color.blue()))
            except:
                pass

        wc = add_warning(message.author.id, message.guild.id, preason, pseverity)

        if pseverity in ["high", "critical"]:
            embed = discord.Embed(title=f"🚨 {ptype.replace('_',' ').title()}",
                color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="User", value=message.author.mention, inline=True)
            embed.add_field(name="Reason", value=preason, inline=True)
            embed.add_field(name="Warnings", value=str(wc), inline=True)
            await alert_mods(message.guild, embed)

        if pseverity == "critical" and ptype in ["fake_nitro","token_grab","phishing","scam","social_engineering","blackmail","extremism","grooming"]:
            try:
                await message.guild.ban(message.author, reason=f"IMMEDIATE: {preason}")
                await alert_mods(message.guild, discord.Embed(title="🔨 Immediate Ban",
                    description=f"{message.author} banned: {preason}", color=discord.Color.dark_red()))
            except:
                pass

        if wc >= settings.get("warn_mute", 3):
            try:
                await message.author.timeout(datetime.now() + timedelta(minutes=10), reason=preason)
            except:
                pass
        if wc >= settings.get("warn_ban", 5):
            try:
                await message.guild.ban(message.author, reason=f"Too many violations")
            except:
                pass
        return

    # Word filter
    words = get_filtered_words(message.guild.id)
    cl = message.content.lower()
    norm = cl
    for old, new in [("@","a"),("0","o"),("1","i"),("3","e"),("$","s"),("5","s"),("4","a")]:
        norm = norm.replace(old, new)
    for word in words:
        if word in cl or word in norm:
            try:
                await message.delete()
            except:
                pass
            wc = add_warning(message.author.id, message.guild.id, "Filtered word", "medium")
            await message.channel.send(f"⚠️ {message.author.mention} That word is not allowed!", delete_after=5)
            return

    if len(message.content) < 3:
        await bot.process_commands(message)
        return

    # Pre-conflict
    ck = f"{message.guild.id}:{message.channel.id}"
    recent_messages[ck].append({"author": message.author.name, "content": message.content, "time": time.time()})
    recent_messages[ck] = [m for m in recent_messages[ck] if time.time() - m["time"] < 60]

    if settings.get("pre_conflict", 1) and len(recent_messages[ck]) >= 6:
        mt = "\n".join(f"{m['author']}: {m['content']}" for m in recent_messages[ck][-10:])
        conflict = await ask_groq_json(f'Analyze for conflict:\n{mt}\nJSON:{{"escalating":true/false,"severity":"none|mild|moderate|severe","reason":"brief"}}')
        if conflict and conflict.get("escalating") and conflict.get("severity") in ["moderate","severe"]:
            await message.channel.send(embed=discord.Embed(title="⚠️ Cool Down",
                description="This conversation is getting heated. Please be respectful! 😊",
                color=discord.Color.yellow()), delete_after=30)
            if conflict.get("severity") == "severe":
                await alert_mods(message.guild, discord.Embed(title="🔥 Conflict Alert",
                    color=discord.Color.orange()).add_field(name="Channel", value=message.channel.mention))
                if settings.get("slowmode_ai", 1):
                    try:
                        await message.channel.edit(slowmode_delay=10)
                        await asyncio.sleep(60)
                        await message.channel.edit(slowmode_delay=0)
                    except:
                        pass

    # AI toxicity
    context = ""
    try:
        h = []
        async for m in message.channel.history(limit=5, before=message):
            if not m.author.bot:
                h.append(f"{m.author.name}: {m.content}")
        context = "\n".join(reversed(h))
    except:
        pass

    analysis = await check_toxicity(message.content, context)
    if analysis and analysis.get("toxic"):
        severity = analysis.get("severity", "low")
        confidence = analysis.get("confidence", 0)
        reason = analysis.get("reason", "Toxic")
        sens = settings.get("ai_sensitivity", 0.7)

        if settings.get("slowmode_ai", 1) and severity in ["high","critical"]:
            try:
                await message.channel.edit(slowmode_delay=10)
                await asyncio.sleep(60)
                await message.channel.edit(slowmode_delay=0)
            except:
                pass

        if confidence >= sens:
            if severity in ["medium","high","critical"]:
                await punish_user(message, severity, reason, analysis)
            elif severity == "low":
                add_warning(message.author.id, message.guild.id, reason, "low")
                try:
                    await message.author.send(embed=discord.Embed(title="⚠️ Heads up",
                        description=f"Please be respectful in **{message.guild.name}**\nReason: {reason}",
                        color=discord.Color.yellow()))
                except:
                    pass

    await bot.process_commands(message)

# ============ SECTION 19 - RUN ============
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
