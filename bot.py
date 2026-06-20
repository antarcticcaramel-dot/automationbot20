# bot.py
# ================================
# SentinelMod - FULL Bot + Dashboard
# ALL FEATURES INCLUDED
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
        """CREATE TABLE IF NOT EXISTS backup_data (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, backup_type TEXT, data TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS birthdays (user_id TEXT, guild_id TEXT, birthday TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS suggestions (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, user_id TEXT, suggestion TEXT, status TEXT DEFAULT 'pending', message_id TEXT, timestamp TEXT)"""
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
mention_tracker = defaultdict(list)
file_tracker = defaultdict(list)
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
                mem = await ask_groq(f"Current memory: {get_user_memory(uid, gid)}\nNew: User: {prompt}\nBot: {full}\nUpdate memory with important facts. Under 500 chars.", "Remember user facts only.")
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
    return f"You are SentinelMod, a Discord bot.\nPersonality: {personality}\n{f'Memory about user: {memory}' if memory else ''}\n{extra}\nKeep responses under 1500 chars."

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

CRITICAL: If unclear/chat → command="chat". For mod actions target MUST be in Mentioned list. Never confuse sender with target. If confidence < 0.8 → chat.

JSON only:
{{"command":"create_channel|delete_channel|create_role|delete_role|create_category|delete_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|add_role_to_user|remove_role_from_user|start_giveaway|create_poll|set_afk|backup_server|setup_server|summarize|translate|add_word_filter|remove_word_filter|enable_feature|disable_feature|add_note|get_notes|set_autorole|raid_mode|trivia|wouldyourather|eightball|roast|compliment|dadjoke|ship|rate|fact|truthordare|story|debate|riddle|pickupline|horoscope|remind|birthday|confession|rep|server_health|activity_stats|mod_stats|suggestion|quarantine|unquarantine|add_custom_command|remove_custom_command|list_custom_commands|help|chat|unknown",
"needs_confirmation":true/false,
"confirmation_message":"detailed",
"confidence":0.0-1.0,
"params":{{"name":null,"target_user_id":null,"target_user_name":null,"target_user2":null,"reason":null,"duration":null,"category":null,"color":null,"private":false,"amount":null,"prize":null,"winners":null,"question":null,"options":null,"language":null,"text":null,"feature":null,"word":null,"note":null,"channel":null,"topic":null,"response":null,"reminder_time":null,"rating_target":null,"zodiac":null,"birthday_date":null}}}}"""
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
    trivia = await ask_groq_json('Generate trivia. JSON: {"question":"q","correct":"a","wrong1":"b","wrong2":"c","wrong3":"d","category":"cat","difficulty":"easy"}')
    if not trivia:
        return "❌ Failed!"
    answers = [trivia["correct"], trivia["wrong1"], trivia["wrong2"], trivia["wrong3"]]
    random.shuffle(answers)
    idx = answers.index(trivia["correct"])
    emojis = ["🇦","🇧","🇨","🇩"]
    embed = discord.Embed(title=f"🧠 Trivia - {trivia['category']}", description=trivia["question"], color=discord.Color.blue())
    embed.add_field(name="Difficulty", value=trivia["difficulty"].upper())
    embed.add_field(name="Options", value="\n".join(f"{emojis[i]} {a}" for i, a in enumerate(answers)), inline=False)
    embed.set_footer(text="React! 30 seconds!")
    msg = await message.channel.send(embed=embed)
    for e in emojis[:4]:
        await msg.add_reaction(e)
    trivia_sessions[msg.id] = {"correct_emoji": emojis[idx], "correct_answer": trivia["correct"], "guild_id": gid, "answered": []}
    await asyncio.sleep(30)
    if msg.id in trivia_sessions:
        await message.channel.send(embed=discord.Embed(title="⏰ Time's Up!", description=f"Answer: **{trivia['correct']}**", color=discord.Color.green()))
        del trivia_sessions[msg.id]
    return None

async def do_fun_embed(ftype, params, author):
    prompts = {
        "wouldyourather": ("Generate fun Would You Rather question.", "🤔 Would You Rather?"),
        "eightball": (f"Magic 8ball answer for: '{params.get('question','...')}'. Mystical, brief.", "🎱 Magic 8-Ball"),
        "roast": (f"Playful roast of {params.get('target_user_name','someone')}. Fun not mean. 2-3 sentences.", "🔥 Roast"),
        "compliment": (f"Heartfelt compliment for {params.get('target_user_name', author.name)}. 2-3 sentences.", "💝 Compliment"),
        "dadjoke": ("Tell a dad joke. Groan-worthy.", "👨 Dad Joke"),
        "ship": (f"Love compatibility between {params.get('target_user_name','x')} and {params.get('target_user2','y')}. % + ship name.", "💕 Ship"),
        "rate": (f"Rate '{params.get('rating_target','life')}' out of 10 with funny explanation.", "⭐ Rating"),
        "fact": ("Random surprising fact. 2-3 sentences.", "🤯 Fact"),
        "truthordare": (f"Generate {'truth' if random.choice([True,False]) else 'dare'} for Discord.", "🎯 Truth or Dare"),
        "story": (f"Short creative story {('about '+params.get('text','')) if params.get('text') else ''}. 150 words.", "📖 Story"),
        "riddle": ("Give a riddle with answer at end.", "🧩 Riddle"),
        "pickupline": ("Creative funny pickup line.", "😘 Pickup Line"),
        "horoscope": (f"Fun horoscope for {params.get('zodiac','Aries')} today. 3-4 sentences.", f"⭐ {params.get('zodiac','Aries')} Horoscope"),
    }
    p, title = prompts.get(ftype, ("Tell joke.", "😄 Fun"))
    result = await ask_groq(p, "Fun Discord bot.")
    if result:
        colors = {"roast": discord.Color.red(), "compliment": discord.Color.pink(), "ship": discord.Color.red(), "fact": discord.Color.teal(), "horoscope": discord.Color.purple()}
        embed = discord.Embed(title=title, description=result, color=colors.get(ftype, discord.Color.blue()))
        embed.set_footer(text=f"Asked by {author.display_name}")
        return embed
    return None

# ============ EXECUTE COMMAND ============
async def execute_command(parsed, message, guild, author):
    cmd = parsed.get("command", "unknown")
    params = parsed.get("params", {})
    settings = get_guild_settings(guild.id)
    try:
        if cmd == "create_channel":
            name = (params.get("name") or "new-channel").lower().replace(" ", "-")
            existing = discord.utils.get(guild.text_channels, name=name)
            if existing:
                return f"⏭️ {existing.mention} already exists!"
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
                return f"❌ Channel **#{name}** not found."
            await ch.delete(reason=f"Deleted by {author.name}")
            return f"🗑️ Deleted **#{name}**!"
        elif cmd == "create_role":
            name = params.get("name") or "New Role"
            if discord.utils.get(guild.roles, name=name):
                return f"⏭️ Role **{name}** already exists!"
            color = discord.Color.default()
            if params.get("color"):
                try:
                    color = discord.Color(int(params["color"].replace("#",""), 16))
                except:
                    pass
            role = await guild.create_role(name=name, color=color, hoist=params.get("hoist", False), mentionable=params.get("mentionable", False))
            return f"✅ Created role {role.mention}!"
        elif cmd == "delete_role":
            role = discord.utils.get(guild.roles, name=params.get("name"))
            if not role:
                return "❌ Role not found."
            await role.delete()
            return f"🗑️ Deleted role!"
        elif cmd == "create_category":
            name = params.get("name") or "New Category"
            if discord.utils.get(guild.categories, name=name):
                return f"⏭️ Category exists!"
            await guild.create_category(name=name)
            return f"✅ Created category **{name}**!"
        elif cmd == "delete_category":
            cat = discord.utils.get(guild.categories, name=params.get("name"))
            if not cat:
                return "❌ Category not found."
            await cat.delete()
            return f"🗑️ Deleted!"
        elif cmd == "ban_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found. Please @mention them!"
            if t.id == author.id:
                return "❌ You can't ban yourself!"
            if t.id == guild.me.id:
                return "❌ I can't ban myself!"
            reason = params.get("reason") or "No reason"
            try:
                await t.send(embed=discord.Embed(title="🔨 Banned", description=f"Banned from **{guild.name}**\nReason: {reason}", color=discord.Color.dark_red()))
            except:
                pass
            await guild.ban(t, reason=f"{author.name}: {reason}")
            log_mod_action(t.id, guild.id, "BAN", reason, author.id)
            add_warning(t.id, guild.id, reason, "critical")
            embed = discord.Embed(title="🔨 User Banned", color=discord.Color.dark_red(), timestamp=datetime.now())
            embed.add_field(name="User", value=f"{t} ({t.id})", inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"🔨 Banned **{t.name}**!"
        elif cmd == "kick_user":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found. Please @mention them!"
            if t.id == author.id:
                return "❌ You can't kick yourself!"
            reason = params.get("reason") or "No reason"
            try:
                await t.send(embed=discord.Embed(title="👢 Kicked", description=f"Kicked from **{guild.name}**\nReason: {reason}", color=discord.Color.orange()))
            except:
                pass
            await guild.kick(t, reason=f"{author.name}: {reason}")
            log_mod_action(t.id, guild.id, "KICK", reason, author.id)
            embed = discord.Embed(title="👢 User Kicked", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="User", value=f"{t} ({t.id})", inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
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
                await t.send(embed=discord.Embed(title="🔇 Muted", description=f"Muted in **{guild.name}** for {dur}min\nReason: {reason}", color=discord.Color.orange()))
            except:
                pass
            embed = discord.Embed(title="🔇 User Muted", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="User", value=t.mention, inline=True)
            embed.add_field(name="Duration", value=f"{dur} min", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await alert_mods(guild, embed)
            return f"🔇 Muted **{t.name}** for {dur} minutes!"
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
                await t.send(embed=discord.Embed(title="⚠️ Warning", description=f"Warning in **{guild.name}**\nReason: {reason}\nTotal: {wc}/{settings.get('warn_ban',5)}", color=discord.Color.yellow()))
            except:
                pass
            embed = discord.Embed(title="⚠️ Warning Issued", color=discord.Color.yellow(), timestamp=datetime.now())
            embed.add_field(name="User", value=t.mention, inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Total", value=f"{wc}/{settings.get('warn_ban',5)}", inline=True)
            await alert_mods(guild, embed)
            return f"⚠️ Warned **{t.name}** ({wc} warnings)"
        elif cmd == "clear_warnings":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            clear_warnings(t.id, guild.id)
            return f"✅ Cleared warnings for **{t.name}**!"
        elif cmd == "warn_check":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            ws = get_warnings(t.id, guild.id)
            if not ws:
                return f"✅ **{t.name}** has no warnings!"
            lines = [f"**{t.name}** - {len(ws)} warnings:"]
            for i, w in enumerate(ws[:5], 1):
                lines.append(f"#{i} [{w['severity'].upper()}] {w['reason']} - {w['timestamp'][:10]}")
            return "\n".join(lines)
        elif cmd == "quarantine":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ User not found."
            reason = params.get("reason") or "Suspicious activity"
            q = discord.utils.get(guild.roles, name="Quarantined")
            if not q:
                q = await guild.create_role(name="Quarantined", color=discord.Color.dark_gray())
                for ch in guild.text_channels:
                    try:
                        await ch.set_permissions(q, send_messages=False, add_reactions=False)
                    except:
                        pass
            await t.add_roles(q, reason=reason)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO quarantine (user_id, guild_id, reason, timestamp) VALUES (?, ?, ?, ?)", (str(t.id), str(guild.id), reason, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            embed = discord.Embed(title="🔒 Quarantined", color=discord.Color.dark_gray(), timestamp=datetime.now())
            embed.add_field(name="User", value=t.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            await alert_mods(guild, embed)
            return f"🔒 Quarantined **{t.name}**!"
        elif cmd == "unquarantine":
            t = find_member_strict(guild, params)
            if not t:
                return "❌ Not found."
            q = discord.utils.get(guild.roles, name="Quarantined")
            if q and q in t.roles:
                await t.remove_roles(q)
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM quarantine WHERE user_id=? AND guild_id=?", (str(t.id), str(guild.id)))
            conn.commit()
            conn.close()
            return f"✅ Unquarantined **{t.name}**!"
        elif cmd == "lock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
            await ch.set_permissions(guild.default_role, send_messages=False)
            return f"🔒 Locked {ch.mention}!"
        elif cmd == "unlock_channel":
            ch_name = params.get("channel") or params.get("name")
            ch = discord.utils.get(guild.text_channels, name=ch_name) if ch_name else message.channel
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
            embed = discord.Embed(title="🔒 SERVER LOCKDOWN", description=f"By {author.mention}", color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="Channels", value=str(count))
            await alert_mods(guild, embed)
            return f"🔒 Server locked! {count} channels."
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
                return "❌ User or role not found."
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
            topic = params.get("text") or params.get("question") or "pineapple on pizza"
            r = await ask_groq(f"Start a debate about: {topic}. Present both sides. Ask channel to vote.", "Debate moderator.")
            if r:
                embed = discord.Embed(title=f"⚔️ Debate: {topic}", description=r, color=discord.Color.orange())
                msg = await message.channel.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
            return None
        elif cmd == "remind":
            text = params.get("text") or params.get("note") or "Reminder!"
            mins = int(params.get("reminder_time") or params.get("duration") or 10)
            t = datetime.now() + timedelta(minutes=mins)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reminders (user_id, guild_id, channel_id, reminder, remind_time) VALUES (?, ?, ?, ?, ?)", (str(author.id), str(guild.id), str(message.channel.id), text, t.isoformat()))
            conn.commit()
            conn.close()
            return f"⏰ I'll remind you in {mins} minutes: **{text}**"
        elif cmd == "birthday":
            date = params.get("birthday_date") or params.get("text")
            if not date:
                return "❌ Tell me your birthday! E.g. 'my birthday is January 15'"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO birthdays (user_id, guild_id, birthday) VALUES (?, ?, ?)", (str(author.id), str(guild.id), date))
            conn.commit()
            conn.close()
            return f"🎂 Birthday set to **{date}**!"
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
            embed = discord.Embed(title=f"🤫 Anonymous Confession #{cid}", description=text, color=discord.Color.dark_purple(), timestamp=datetime.now())
            embed.set_footer(text="Anonymous via SentinelMod")
            await message.channel.send(embed=embed)
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
            return f"✅ +1 rep to **{t.name}**! Total: **{rep}**"
        elif cmd == "start_giveaway":
            prize = params.get("prize") or "Mystery Prize"
            dur = int(params.get("duration") or 60)
            wins = int(params.get("winners") or 1)
            end = datetime.now() + timedelta(minutes=dur)
            embed = discord.Embed(title="🎉 GIVEAWAY!", description=f"**Prize:** {prize}\nReact with 🎉 to enter!", color=discord.Color.gold(), timestamp=end)
            embed.add_field(name="Winners", value=str(wins), inline=True)
            embed.add_field(name="By", value=author.mention, inline=True)
            embed.add_field(name="Ends", value=f"<t:{int(end.timestamp())}:R>", inline=True)
            msg = await message.channel.send(embed=embed)
            await msg.add_reaction("🎉")
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, host_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(guild.id), str(message.channel.id), str(msg.id), prize, wins, end.isoformat(), str(author.id)))
            conn.commit()
            conn.close()
            return f"🎉 Giveaway started for **{prize}**!"
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
            return f"💤 AFK set: **{reason}**"
        elif cmd == "backup_server":
            r = [{"name":x.name,"color":str(x.color),"hoist":x.hoist} for x in guild.roles if x.name != "@everyone"]
            ch = [{"name":x.name,"topic":x.topic,"category":x.category.name if x.category else None} for x in guild.text_channels]
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO backup_data (guild_id, backup_type, data, timestamp) VALUES (?, ?, ?, ?)", (str(guild.id), "full", json.dumps({"roles":r,"channels":ch}), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return f"💾 Backed up {len(r)} roles and {len(ch)} channels!"
        elif cmd == "setup_server":
            results = await setup_server(guild)
            return "🛡️ Setup complete!\n" + "\n".join(results[:15])
        elif cmd == "summarize":
            amt = min(int(params.get("amount") or 20), 50)
            msgs = []
            async for m in message.channel.history(limit=amt):
                if not m.author.bot:
                    msgs.append(f"{m.author.display_name}: {m.content}")
            if not msgs:
                return "❌ No messages."
            s = await ask_groq("Summarize in 3-5 bullet points:\n" + "\n".join(reversed(msgs)), "Summarizer.")
            return f"📝 **Summary:**\n{s}"
        elif cmd == "translate":
            text = params.get("text") or ""
            lang = params.get("language") or "English"
            if not text:
                return "❌ No text."
            t = await ask_groq(f"Translate to {lang}. ONLY translation:\n{text}", "Translator.")
            return f"🌐 **({lang}):** {t}"
        elif cmd == "add_word_filter":
            w = params.get("word")
            if not w:
                return "❌ No word."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)", (str(guild.id), w.lower()))
            conn.commit()
            conn.close()
            return f"✅ Added **{w}** to filter!"
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
                return f"📝 No notes for **{t.name}**."
            return f"📝 **{t.name}:**\n" + "\n".join(f"• {x['note']}" for x in n)
        elif cmd == "set_autorole":
            r = discord.utils.get(guild.roles, name=params.get("name"))
            if not r:
                return "❌ Role not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO auto_roles (guild_id, role_id) VALUES (?, ?)", (str(guild.id), str(r.id)))
            conn.commit()
            conn.close()
            return f"✅ **{r.name}** auto-assigned!"
        elif cmd == "raid_mode":
            text = (params.get("feature") or params.get("text") or "").lower()
            status = "on" in text or "enable" in text
            raid_mode_active[guild.id] = status
            return f"🚨 Raid mode **{'ON' if status else 'OFF'}**!"
        elif cmd == "server_health":
            total = guild.member_count
            bots = sum(1 for m in guild.members if m.bot)
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (str(guild.id),))
            wc = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id=?", (str(guild.id),))
            ma = c.fetchone()[0]
            conn.close()
            score = max(0, 100 - (wc // 5))
            embed = discord.Embed(title="🏥 Server Health", color=discord.Color.green() if score > 70 else discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="Score", value=f"{score}/100", inline=True)
            embed.add_field(name="Members", value=str(total-bots), inline=True)
            embed.add_field(name="Bots", value=str(bots), inline=True)
            embed.add_field(name="Channels", value=str(len(guild.text_channels)), inline=True)
            embed.add_field(name="Warnings", value=str(wc), inline=True)
            embed.add_field(name="Mod Actions", value=str(ma), inline=True)
            embed.add_field(name="Raid Mode", value="🔴 ON" if raid_mode_active[guild.id] else "🟢 OFF", inline=True)
            await message.channel.send(embed=embed)
            return None
        elif cmd == "activity_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 10", (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "📊 No data yet!"
            lines = []
            medals = ["🥇","🥈","🥉"]
            for i, r in enumerate(top):
                m = guild.get_member(int(r["user_id"]))
                medal = medals[i] if i < 3 else f"#{i+1}"
                lines.append(f"{medal} {m.display_name if m else '?'}: **{r['message_count']}** msgs")
            await message.channel.send(embed=discord.Embed(title="📊 Activity Stats", description="\n".join(lines), color=discord.Color.blue()))
            return None
        elif cmd == "mod_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT mod_id, COUNT(*) as t FROM mod_actions WHERE guild_id=? GROUP BY mod_id ORDER BY t DESC LIMIT 5", (str(guild.id),))
            top = c.fetchall()
            conn.close()
            if not top:
                return "🛡️ No mod data!"
            lines = []
            for i, r in enumerate(top, 1):
                m = guild.get_member(int(r["mod_id"]))
                lines.append(f"#{i} {m.display_name if m else '?'}: **{r['t']}** actions")
            await message.channel.send(embed=discord.Embed(title="🛡️ Mod Leaderboard", description="\n".join(lines), color=discord.Color.red()))
            return None
        elif cmd == "suggestion":
            text = params.get("text") or params.get("note")
            if not text:
                return "❌ No suggestion."
            ch = discord.utils.get(guild.text_channels, name="suggestions")
            if ch:
                embed = discord.Embed(title="💡 New Suggestion", description=text, color=discord.Color.blue(), timestamp=datetime.now())
                embed.set_footer(text=f"By {author.display_name}")
                msg = await ch.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO suggestions (guild_id, user_id, suggestion, message_id, timestamp) VALUES (?, ?, ?, ?, ?)", (str(guild.id), str(author.id), text, str(msg.id), datetime.now().isoformat()))
                conn.commit()
                conn.close()
                return f"✅ Posted in {ch.mention}!"
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
            return f"✅ Custom command added!\nTrigger: `{trigger}`\nResponse: {response[:200]}"
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
                return f"{'✅ Enabled' if v else '❌ Disabled'} **{f}**!"
            except:
                return f"❌ Unknown: {f}"
            finally:
                conn.close()
        elif cmd == "help":
            embed = discord.Embed(title="🛡️ SentinelMod Help", description="@mention me or chat in #sentinel-bot!", color=discord.Color.blue())
            embed.add_field(name="🔧 Server", value="make/delete channels, roles, categories", inline=False)
            embed.add_field(name="🔨 Mod", value="ban, kick, mute, warn, purge, lock, lockdown, quarantine", inline=False)
            embed.add_field(name="🎮 Fun", value="trivia, roast, compliment, 8ball, ship, rate, story, riddle", inline=False)
            embed.add_field(name="🤖 AI", value="summarize, translate, story, debate, confess", inline=False)
            embed.add_field(name="📊 Info", value="server health, activity, mod stats, remind, birthday", inline=False)
            embed.add_field(name="🎭 Personality", value="/personality or /setpersonality", inline=False)
            embed.add_field(name="🌐 Dashboard", value=f"{REDIRECT_URI.replace('/callback','')}", inline=False)
            await message.channel.send(embed=embed)
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
    u = msg.author
    g = msg.guild
    try:
        await msg.channel.purge(limit=10, check=lambda m: m.author == u)
    except:
        pass
    try:
        await u.timeout(datetime.now() + timedelta(minutes=settings.get("mute_duration",10)), reason="Spam")
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
            await ch.send(content=f"🚨 {mr.mention if mr else ''} RAID!", embed=discord.Embed(title="🚨 RAID DETECTED", color=discord.Color.red()))
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
    ch = discord.utils.get(guild.text_channels, name="sentinel-nuke-alerts")
    if ch:
        mr = discord.utils.get(guild.roles, name=get_guild_settings(guild.id)["mod_role_name"])
        await ch.send(content=mr.mention if mr else "", embed=embed)
    else:
        await alert_mods(guild, embed)

async def check_patterns(msg, settings):
    content = msg.content
    cl = content.lower()
    if settings.get("phone_filter",1) and re.search(r'\b(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b', content):
        return "phone", "Phone number", "high"
    if settings.get("email_filter",1) and re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
        return "email", "Email", "high"
    keywords = [
        (settings.get("fake_nitro_filter",1), ["free nitro","discord nitro free","claim nitro"], "fake_nitro", "Fake Nitro scam", "critical"),
        (settings.get("token_filter",1), ["discord token","grab token","token logger","grabify.link"], "token", "Token grabber", "critical"),
        (settings.get("scam_filter",1), ["you won","claim your prize","account will be deleted","verify your account"], "scam", "Scam", "critical"),
        (settings.get("anti_advertisement",1), ["join my server","subscribe to my","check out my server"], "ad", "Advertisement", "medium"),
        (settings.get("nsfw_text_filter",1), ["how old are you","send me a pic","don't tell your parents"], "grooming", "Grooming", "critical"),
        (1, ["i will expose you","pay me or","i know where you live"], "blackmail", "Blackmail", "critical"),
        (1, ["want to kill myself","want to die","going to hurt myself"], "self_harm", "Self-harm content", "high"),
        (1, ["death to all","kill all","exterminate"], "extremism", "Extremism", "critical"),
        (1, ["i'm from discord","official discord","your account has been flagged"], "social_eng", "Social engineering", "critical"),
    ]
    for en, words, t, r, sev in keywords:
        if en and any(w in cl for w in words):
            return t, r, sev
    if settings.get("zalgo_filter",1) and sum(1 for c in content if unicodedata.combining(c)) > 10:
        return "zalgo", "Zalgo text", "medium"
    if settings.get("caps_filter",1) and len(content) > 10:
        if sum(1 for c in content if c.isupper())/len(content) > 0.7:
            return "caps", "Excessive caps", "low"
    if settings.get("mention_spam",1) and len(msg.mentions) >= 5:
        return "mentions", "Mention spam", "high"
    if settings.get("everyone_block",0) and ("@everyone" in content or "@here" in content):
        return "everyone", "@everyone block", "medium"
    if settings.get("invite_block",0) and re.search(r'(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', content):
        return "invite", "Invite link", "medium"
    if settings.get("link_scan",1) and "http" in cl:
        bad = ["grabify","iplogger","discord.gift","free-nitro","phish","dlscord","ip-logger"]
        for b in bad:
            if b in cl:
                return "phishing", f"Phishing: {b}", "critical"
    if re.search(r'(.)\1{9,}', content):
        return "repeat", "Repeated chars", "low"
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
    return await ask_groq_json(f'Analyze for harm: "{content}" Context: {context}\nJSON: {{"toxic":true/false,"severity":"none|low|medium|high|critical","category":"none|harassment|threat|hate|sexual|bullying","confidence":0.0-1.0,"reason":"brief","immediate_action":true/false}}')

async def punish_user(msg, sev, reason, analysis):
    u = msg.author
    g = msg.guild
    s = get_guild_settings(g.id)
    wc = add_warning(u.id, g.id, reason, sev)
    log_mod_action(u.id, g.id, "AI_WARN", reason, bot.user.id)
    try:
        await msg.delete()
    except:
        pass
    try:
        await msg.channel.send(embed=discord.Embed(title="🛡️ Message Removed", description=f"{u.mention} message removed.\nReason: {reason}", color=discord.Color.orange()), delete_after=8)
    except:
        pass
    try:
        await u.send(embed=discord.Embed(title="⚠️ Warning", description=f"Message removed in **{g.name}**\nReason: {reason}\nWarnings: {wc}/{s.get('warn_ban',5)}", color=discord.Color.yellow()))
    except:
        pass
    colors = {"low":discord.Color.yellow(),"medium":discord.Color.orange(),"high":discord.Color.red(),"critical":discord.Color.dark_red()}
    embed = discord.Embed(title="🚨 AI Moderation", color=colors.get(sev, discord.Color.red()), timestamp=datetime.now())
    embed.add_field(name="User", value=f"{u.mention} ({u.id})", inline=True)
    embed.add_field(name="Severity", value=sev.upper(), inline=True)
    embed.add_field(name="Confidence", value=f"{analysis.get('confidence',0)*100:.0f}%", inline=True)
    embed.add_field(name="Warnings", value=f"{wc}/{s.get('warn_ban',5)}", inline=True)
    embed.add_field(name="Message", value=f"||{msg.content[:400]}||", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    action = "⚠️ Warning"
    if wc >= s.get("warn_mute",3) and wc < s.get("warn_ban",5):
        try:
            await u.timeout(datetime.now() + timedelta(minutes=s.get("mute_duration",10)), reason=reason)
            action = f"🔇 Muted {s.get('mute_duration',10)}min"
        except:
            pass
    if wc >= s.get("warn_ban",5):
        try:
            await g.ban(u, reason=f"AI: {reason}")
            action = "🔨 BANNED"
        except:
            pass
    if analysis.get("immediate_action") and sev == "critical":
        try:
            await g.ban(u, reason=f"IMMEDIATE: {reason}")
            action = "🔨 IMMEDIATELY BANNED"
        except:
            pass
    embed.add_field(name="Action", value=action, inline=False)
    await alert_mods(g, embed)

# ============ SETUP & VIEWS ============
async def setup_server(guild):
    results = []
    s = get_guild_settings(guild.id)
    for rn, c, h in [(s["mod_role_name"], discord.Color.red(), True), ("Muted", discord.Color.dark_gray(), False), ("Member", discord.Color.blue(), False), ("Quarantined", discord.Color.dark_gray(), False)]:
        if not discord.utils.get(guild.roles, name=rn):
            try:
                await guild.create_role(name=rn, color=c, hoist=h, mentionable=True)
                results.append(f"✅ Role: {rn}")
            except:
                results.append(f"❌ Role: {rn}")
        else:
            results.append(f"⏭️ Role exists: {rn}")
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    scat = discord.utils.get(guild.categories, name="🛡️ SENTINELAI")
    if not scat:
        try:
            ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
            if mr:
                ow[mr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            scat = await guild.create_category(name="🛡️ SENTINELAI", overwrites=ow)
            results.append("✅ Category: SENTINELAI")
        except:
            pass
    for cn, t in [(s["log_channel"],"Mod logs"),(s["raid_channel"],"Raid alerts"),("sentinel-nuke-alerts","Nuke alerts"),("sentinel-bot","Chat with SentinelMod AI!")]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try:
                await guild.create_text_channel(name=cn, category=scat, topic=t)
                results.append(f"✅ #{cn}")
            except:
                results.append(f"❌ #{cn}")
        else:
            results.append(f"⏭️ #{cn}")
    for cn, t in [("welcome","Welcome"),("rules","Rules"),("general","General"),("announcements","Announcements"),("suggestions","Suggestions")]:
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
    opts = [discord.SelectOption(label=n.replace("_"," ").title(), value=n, description=PERSONALITIES[n][:50]) for n in list(PERSONALITIES.keys())[:25]]
    view = discord.ui.View(timeout=60)
    select = discord.ui.Select(placeholder="Choose...", options=opts)
    async def cb(i):
        p = i.data["values"][0]
        set_user_personality(str(i.user.id), str(i.guild.id), p)
        await i.response.send_message(f"✅ Personality: **{p.replace('_',' ').title()}**!", ephemeral=True)
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
    await interaction.response.send_message(f"✅ Now: **{p.replace('_',' ').title()}**!\n*{PERSONALITIES[p]}*", ephemeral=True)

@bot.tree.command(name="help", description="Show help")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ SentinelMod Help", color=discord.Color.blue())
    embed.add_field(name="💬 Chat", value=f"@mention me or chat in #sentinel-bot", inline=False)
    embed.add_field(name="🔧 Server", value="make/delete channels, roles, categories", inline=False)
    embed.add_field(name="🔨 Moderation", value="ban, kick, mute, warn, purge, lock, quarantine", inline=False)
    embed.add_field(name="🎮 Fun", value="trivia, roast, compliment, 8ball, ship, rate, story", inline=False)
    embed.add_field(name="🤖 AI", value="summarize, translate, story, debate, confess", inline=False)
    embed.add_field(name="🎭 Personality", value="/personality or /setpersonality", inline=False)
    embed.add_field(name="🌐 Dashboard", value=f"{REDIRECT_URI.replace('/callback','')}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="dashboard", description="Get dashboard link")
async def dashboard_cmd(interaction: discord.Interaction):
    url = REDIRECT_URI.replace('/callback', '')
    embed = discord.Embed(title="🌐 Web Dashboard", description=f"Manage your server:\n**{url}**", color=discord.Color.blue())
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
                await ch.send(f"⏰ <@{rem['user_id']}> Reminder: **{rem['reminder']}**")
        except:
            pass
        c.execute("UPDATE reminders SET active=0 WHERE id=?", (rem["id"],))
    conn.commit()
    conn.close()

# ============ EVENTS ============
@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 {bot.user} ONLINE")
    print(f"🏠 {len(bot.guilds)} servers")
    print(f"🎭 {len(PERSONALITIES)} personalities")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for g in bot.guilds:
        init_guild_settings(g.id)
    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} commands synced")
    except Exception as e:
        print(f"Sync error: {e}")
    check_giveaways.start()
    check_reminders.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="everything 👁️ | @mention me!"))

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
    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    if age < s.get("min_account_age", 7):
        ch = discord.utils.get(g.text_channels, name=s["raid_channel"])
        if ch:
            await ch.send(embed=discord.Embed(title="⚠️ Suspicious Account", color=discord.Color.yellow()).add_field(name="User", value=member.mention).add_field(name="Age", value=f"{age} days"))
    if s.get("welcome_enabled", 1):
        wch = discord.utils.get(g.text_channels, name=s.get("welcome_channel","welcome"))
        if wch:
            w = await ask_groq(f"Short warm welcome for {member.display_name} joining {g.name}. 2 sentences.", "Friendly.")
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
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO trivia_scores (user_id, guild_id, score, total) VALUES (?, ?, 1, 1) ON CONFLICT(user_id, guild_id) DO UPDATE SET score=score+1, total=total+1", (str(user.id), str(s["guild_id"])))
            conn.commit()
            conn.close()
            await reaction.message.channel.send(f"✅ {user.mention} correct! **{s['correct_answer']}**")
            del trivia_sessions[reaction.message.id]

@bot.event
async def on_audit_log_entry_create(entry):
    g = entry.guild
    s = get_guild_settings(g.id)
    if not s.get("anti_nuke_enabled", 1):
        return
    nuke = [discord.AuditLogAction.channel_delete, discord.AuditLogAction.role_delete, discord.AuditLogAction.ban, discord.AuditLogAction.kick, discord.AuditLogAction.webhook_create]
    if entry.action in nuke and entry.user:
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
                                await message.reply(f"❌ User not found. @mention them directly!")
                                return
                    nc = parsed.get("needs_confirmation", False) or parsed.get("command") in dangerous
                    if nc:
                        cn = parsed.get('command','').replace('_',' ').title()
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
                        embed = discord.Embed(title=f"⚠️ Confirm: {cn}", description=parsed.get("confirmation_message","Confirm?") + "\n\n" + "\n".join(details), color=discord.Color.orange())
                        embed.set_footer(text="30 seconds to confirm")
                        view = ConfirmView(parsed, message, message.guild, message.author)
                        await message.reply(embed=embed, view=view)
                    else:
                        async with message.channel.typing():
                            r = await execute_command(parsed, message, message.guild, message.author)
                        if r:
                            await message.reply(r[:2000])
                    return
            sys = get_system_prompt(str(message.author.id), str(message.guild.id), f"Server: {message.guild.name}\nUser: {message.author.display_name}")
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
                await message.channel.send(embed=discord.Embed(title="💙 We're Here", description=f"{message.author.mention} please reach out:\n**988** Suicide Prevention\nText **HOME** to **741741**\n**findahelpline.com**", color=discord.Color.blue()))
            except:
                pass
        wc = add_warning(message.author.id, message.guild.id, pr, ps)
        if ps in ["high","critical"]:
            embed = discord.Embed(title=f"🚨 {pt.replace('_',' ').title()}", color=discord.Color.red(), timestamp=datetime.now())
            embed.add_field(name="User", value=message.author.mention, inline=True)
            embed.add_field(name="Reason", value=pr, inline=True)
            embed.add_field(name="Warnings", value=str(wc), inline=True)
            await alert_mods(message.guild, embed)
        if ps == "critical" and pt in ["fake_nitro","token","phishing","scam","social_eng","blackmail","extremism","grooming"]:
            try:
                await message.guild.ban(message.author, reason=f"IMMEDIATE: {pr}")
            except:
                pass
        if wc >= s.get("warn_mute", 3):
            try:
                await message.author.timeout(datetime.now() + timedelta(minutes=10), reason=pr)
            except:
                pass
        if wc >= s.get("warn_ban", 5):
            try:
                await message.guild.ban(message.author, reason="Too many violations")
            except:
                pass
        return
    # Word filter
    words = get_filtered_words(message.guild.id)
    cl = message.content.lower()
    norm = cl
    for old, new in [("@","a"),("0","o"),("1","i"),("3","e"),("$","s"),("5","s"),("4","a")]:
        norm = norm.replace(old, new)
    for w in words:
        if w in cl or w in norm:
            try:
                await message.delete()
            except:
                pass
            wc = add_warning(message.author.id, message.guild.id, "Filtered word", "medium")
            await message.channel.send(f"⚠️ {message.author.mention} Word not allowed!", delete_after=5)
            return
    if len(message.content) < 3:
        await bot.process_commands(message)
        return
    # Pre-conflict
    ck = f"{message.guild.id}:{message.channel.id}"
    recent_messages[ck].append({"author": message.author.name, "content": message.content, "time": time.time()})
    recent_messages[ck] = [m for m in recent_messages[ck] if time.time() - m["time"] < 60]
    if s.get("pre_conflict", 1) and len(recent_messages[ck]) >= 6:
        mt = "\n".join(f"{m['author']}: {m['content']}" for m in recent_messages[ck][-10:])
        conflict = await ask_groq_json(f'Conflict check:\n{mt}\nJSON:{{"escalating":true/false,"severity":"none|mild|moderate|severe","reason":"brief"}}')
        if conflict and conflict.get("escalating") and conflict.get("severity") in ["moderate","severe"]:
            await message.channel.send(embed=discord.Embed(title="⚠️ Cool Down", description="Please be respectful! 😊", color=discord.Color.yellow()), delete_after=30)
            if conflict.get("severity") == "severe":
                await alert_mods(message.guild, discord.Embed(title="🔥 Conflict", color=discord.Color.orange()).add_field(name="Channel", value=message.channel.mention))
                if s.get("slowmode_ai", 1):
                    try:
                        await message.channel.edit(slowmode_delay=10)
                        await asyncio.sleep(60)
                        await message.channel.edit(slowmode_delay=0)
                    except:
                        pass
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
        reason = a.get("reason","Toxic")
        if s.get("slowmode_ai", 1) and sev in ["high","critical"]:
            try:
                await message.channel.edit(slowmode_delay=10)
                await asyncio.sleep(60)
                await message.channel.edit(slowmode_delay=0)
            except:
                pass
        if conf >= s.get("ai_sensitivity",0.7):
            if sev in ["medium","high","critical"]:
                await punish_user(message, sev, reason, a)
            elif sev == "low":
                add_warning(message.author.id, message.guild.id, reason, "low")
                try:
                    await message.author.send(embed=discord.Embed(title="⚠️ Heads up", description=f"Be respectful in **{message.guild.name}**\nReason: {reason}", color=discord.Color.yellow()))
                except:
                    pass
    await bot.process_commands(message)

# ============ DASHBOARD ============
app = Flask(__name__)
app.secret_key = SECRET_KEY

DASHBOARD_CSS = """
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter','Segoe UI',sans-serif}
:root{--primary:#5865F2;--primary-hover:#4752C4;--success:#3ba55c;--danger:#ed4245;--warning:#faa61a;--bg-1:#0a0b14;--bg-2:#13141f;--bg-3:#1a1b2e;--card:rgba(255,255,255,0.04);--card-hover:rgba(255,255,255,0.08);--border:rgba(255,255,255,0.08);--text:#fff;--text-dim:#a0a0b0;--text-faded:#6b6c80}
body{background:radial-gradient(ellipse at top,#1a1b3e 0%,#0a0b14 50%);min-height:100vh;color:var(--text);overflow-x:hidden}
.bg-shapes{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;overflow:hidden;pointer-events:none}
.shape{position:absolute;border-radius:50%;filter:blur(80px);opacity:0.3;animation:float 20s infinite ease-in-out}
.shape1{width:400px;height:400px;background:#5865F2;top:-100px;left:-100px}
.shape2{width:500px;height:500px;background:#EB459E;bottom:-200px;right:-100px;animation-delay:-5s}
.shape3{width:300px;height:300px;background:#3ba55c;top:50%;left:50%;animation-delay:-10s}
@keyframes float{0%,100%{transform:translate(0,0)}50%{transform:translate(50px,50px)}}
.container{max-width:1400px;margin:0 auto;padding:20px;position:relative;z-index:1}
.navbar{display:flex;justify-content:space-between;align-items:center;padding:20px 30px;background:rgba(255,255,255,0.03);backdrop-filter:blur(20px);border:1px solid var(--border);border-radius:20px;margin-bottom:30px;position:sticky;top:20px;z-index:100}
.logo{display:flex;align-items:center;gap:12px;font-size:24px;font-weight:800}
.logo-icon{width:40px;height:40px;background:linear-gradient(135deg,#5865F2,#EB459E);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;box-shadow:0 8px 20px rgba(88,101,242,0.4)}
.logo-text{background:linear-gradient(135deg,#fff 0%,#a0a0b0 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-right{display:flex;align-items:center;gap:15px}
.user-badge{display:flex;align-items:center;gap:10px;background:var(--card);padding:8px 16px;border-radius:50px;border:1px solid var(--border)}
.user-badge img{width:32px;height:32px;border-radius:50%;border:2px solid var(--primary)}
.btn{padding:10px 20px;border-radius:10px;border:none;cursor:pointer;font-weight:600;transition:all 0.3s;text-decoration:none;display:inline-flex;align-items:center;gap:8px;font-size:14px}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{background:var(--primary-hover);transform:translateY(-2px);box-shadow:0 10px 25px rgba(88,101,242,0.4)}
.btn-danger{background:var(--danger);color:#fff}
.btn-danger:hover{background:#c93538}
.btn-success{background:var(--success);color:#fff}
.btn-secondary{background:var(--card);color:#fff;border:1px solid var(--border)}
.btn-secondary:hover{background:var(--card-hover)}
.login-container{min-height:100vh;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center}
.login-hero{max-width:600px;padding:40px}
.login-hero h1{font-size:80px;font-weight:900;margin-bottom:20px;background:linear-gradient(135deg,#5865F2,#EB459E,#FAA61A);-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:gradient 5s ease infinite;background-size:200% 200%}
@keyframes gradient{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.login-hero p{font-size:20px;color:var(--text-dim);margin-bottom:40px;line-height:1.6}
.login-features{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:40px 0}
.login-feature{background:var(--card);padding:20px;border-radius:15px;border:1px solid var(--border)}
.login-feature-icon{font-size:32px;margin-bottom:10px}
.login-feature h3{font-size:14px;margin-bottom:5px}
.login-feature p{font-size:12px;color:var(--text-dim);margin:0}
.discord-login-btn{display:inline-flex;align-items:center;gap:12px;background:#5865F2;color:#fff;padding:18px 40px;border-radius:14px;font-size:18px;font-weight:700;text-decoration:none;box-shadow:0 15px 40px rgba(88,101,242,0.5);transition:all 0.3s}
.discord-login-btn:hover{transform:translateY(-3px);box-shadow:0 20px 50px rgba(88,101,242,0.7)}
.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:30px}
.page-title{font-size:36px;font-weight:800}
.page-subtitle{color:var(--text-dim);font-size:14px;margin-top:5px}
.tabs{display:flex;gap:8px;margin-bottom:30px;overflow-x:auto;padding:6px;background:var(--card);border-radius:15px;border:1px solid var(--border)}
.tab{padding:12px 24px;background:transparent;border:none;color:var(--text-dim);cursor:pointer;border-radius:10px;font-weight:600;white-space:nowrap;transition:all 0.3s}
.tab.active{background:var(--primary);color:#fff;box-shadow:0 4px 15px rgba(88,101,242,0.4)}
.tab:hover:not(.active){background:var(--card-hover);color:#fff}
.tab-content{display:none}
.tab-content.active{display:block;animation:fadeIn 0.3s}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;margin-bottom:30px}
.stat-card{background:linear-gradient(135deg,var(--card) 0%,rgba(88,101,242,0.05) 100%);padding:25px;border-radius:20px;border:1px solid var(--border);position:relative;overflow:hidden;transition:all 0.3s}
.stat-card:hover{transform:translateY(-5px);border-color:var(--primary);box-shadow:0 15px 35px rgba(88,101,242,0.2)}
.stat-card::before{content:'';position:absolute;top:0;right:0;width:100px;height:100px;background:linear-gradient(135deg,var(--primary),transparent);border-radius:50%;filter:blur(40px);opacity:0.5}
.stat-icon{font-size:32px;margin-bottom:10px}
.stat-number{font-size:42px;font-weight:800;background:linear-gradient(135deg,#fff,#5865F2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat-label{color:var(--text-dim);font-size:13px;text-transform:uppercase;letter-spacing:1px;margin-top:5px}
.section{background:var(--card);border-radius:20px;border:1px solid var(--border);padding:30px;margin-bottom:25px;backdrop-filter:blur(20px)}
.section-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:15px;border-bottom:1px solid var(--border)}
.section-title{font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px}
.servers-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}
.server-card{background:var(--card);padding:25px;border-radius:20px;border:1px solid var(--border);transition:all 0.4s;cursor:pointer;position:relative;overflow:hidden}
.server-card::before{content:'';position:absolute;top:0;left:0;width:100%;height:4px;background:linear-gradient(90deg,#5865F2,#EB459E);transform:scaleX(0);transition:transform 0.4s;transform-origin:left}
.server-card:hover::before{transform:scaleX(1)}
.server-card:hover{transform:translateY(-5px);border-color:var(--primary);box-shadow:0 20px 40px rgba(0,0,0,0.3)}
.server-header{display:flex;align-items:center;gap:15px;margin-bottom:15px}
.server-icon-wrap{width:70px;height:70px;border-radius:18px;overflow:hidden;background:linear-gradient(135deg,#5865F2,#EB459E);display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:800;flex-shrink:0}
.server-icon-wrap img{width:100%;height:100%;object-fit:cover}
.server-info h3{font-size:18px;font-weight:700;margin-bottom:4px}
.server-badge{display:inline-block;padding:4px 10px;border-radius:50px;font-size:11px;font-weight:600;text-transform:uppercase}
.badge-active{background:rgba(59,165,92,0.2);color:#3ba55c}
.badge-inactive{background:rgba(237,66,69,0.2);color:#ed4245}
.feature-list{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.feature-toggle{background:var(--card);padding:18px;border-radius:14px;border:1px solid var(--border);transition:all 0.3s;cursor:pointer}
.feature-toggle:hover{background:var(--card-hover);border-color:var(--primary)}
.feature-toggle-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.feature-toggle-name{font-weight:600;font-size:14px}
.feature-toggle-desc{font-size:12px;color:var(--text-dim)}
.toggle-switch{position:relative;width:48px;height:26px;background:#333;border-radius:50px;cursor:pointer;transition:0.3s;flex-shrink:0}
.toggle-switch.on{background:linear-gradient(135deg,#5865F2,#7289DA);box-shadow:0 0 15px rgba(88,101,242,0.5)}
.toggle-dot{position:absolute;top:3px;left:3px;width:20px;height:20px;background:#fff;border-radius:50%;transition:0.3s;box-shadow:0 2px 6px rgba(0,0,0,0.3)}
.toggle-switch.on .toggle-dot{left:25px}
.list-item{display:flex;align-items:center;gap:15px;padding:15px;background:var(--card);border-radius:12px;border:1px solid var(--border);margin-bottom:10px;transition:all 0.3s}
.list-item:hover{background:var(--card-hover);transform:translateX(5px)}
.list-avatar{width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#5865F2,#EB459E);display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}
.list-content{flex:1}
.list-title{font-weight:600;font-size:14px}
.list-subtitle{font-size:12px;color:var(--text-dim);margin-top:3px}
.list-meta{font-size:11px;color:var(--text-faded)}
.severity-tag{padding:3px 10px;border-radius:50px;font-size:10px;font-weight:700;text-transform:uppercase}
.sev-low{background:rgba(250,166,26,0.2);color:#faa61a}
.sev-medium{background:rgba(237,140,69,0.2);color:#ed8c45}
.sev-high{background:rgba(237,66,69,0.2);color:#ed4245}
.sev-critical{background:rgba(150,0,0,0.3);color:#ff6b6b}
.form-group{margin-bottom:20px}
.form-label{display:block;margin-bottom:8px;font-weight:600;font-size:13px;color:var(--text-dim)}
.form-input,.form-select,.form-textarea{width:100%;padding:12px 16px;background:var(--bg-2);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:14px;transition:all 0.3s}
.form-input:focus,.form-select:focus,.form-textarea:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(88,101,242,0.2)}
.form-textarea{resize:vertical;min-height:80px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.empty-state{text-align:center;padding:60px 20px;color:var(--text-dim)}
.empty-state-icon{font-size:64px;margin-bottom:20px;opacity:0.3}
.back-btn{display:inline-flex;align-items:center;gap:8px;color:var(--primary);text-decoration:none;margin-bottom:20px;font-weight:600;transition:all 0.3s}
.back-btn:hover{transform:translateX(-5px)}
.alert{padding:15px 20px;border-radius:12px;margin-bottom:20px;display:flex;align-items:center;gap:12px}
.alert-success{background:rgba(59,165,92,0.1);border:1px solid #3ba55c;color:#3ba55c}
.alert-info{background:rgba(88,101,242,0.1);border:1px solid #5865F2;color:#5865F2}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;backdrop-filter:blur(5px)}
.modal.active{display:flex}
.modal-content{background:var(--bg-2);padding:30px;border-radius:20px;border:1px solid var(--border);max-width:500px;width:90%;max-height:80vh;overflow-y:auto}
.modal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.close-btn{background:none;border:none;color:#fff;font-size:24px;cursor:pointer;opacity:0.5;transition:opacity 0.3s}
.close-btn:hover{opacity:1}
.command-row{display:flex;justify-content:space-between;align-items:center;padding:15px;background:var(--card);border-radius:10px;margin-bottom:10px;border:1px solid var(--border)}
.command-trigger{font-family:monospace;background:rgba(88,101,242,0.2);padding:4px 10px;border-radius:6px;color:#5865F2;font-size:13px}
.delete-btn{background:rgba(237,66,69,0.2);color:#ed4245;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;transition:all 0.3s}
.delete-btn:hover{background:#ed4245;color:#fff}
.search-bar{position:relative;margin-bottom:20px}
.search-input{width:100%;padding:14px 20px 14px 50px;background:var(--card);border:1px solid var(--border);border-radius:14px;color:#fff;font-size:14px}
.search-icon{position:absolute;left:18px;top:50%;transform:translateY(-50%);opacity:0.5}
.notification{position:fixed;top:20px;right:20px;padding:15px 25px;background:var(--primary);color:#fff;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.3);z-index:2000;animation:slideIn 0.3s;display:none}
.notification.show{display:block}
@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}
.activity-chart{height:200px;background:var(--bg-2);border-radius:12px;padding:20px;display:flex;align-items:flex-end;gap:8px;border:1px solid var(--border)}
.chart-bar{flex:1;background:linear-gradient(180deg,#5865F2,#EB459E);border-radius:6px 6px 0 0;min-height:5px;transition:all 0.3s;cursor:pointer}
.chart-bar:hover{opacity:0.8}
.personality-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;max-height:400px;overflow-y:auto;padding:10px}
.personality-card{background:var(--card);padding:15px;border-radius:12px;text-align:center;cursor:pointer;border:1px solid var(--border);transition:all 0.3s;font-size:13px}
.personality-card:hover{background:var(--primary);transform:translateY(-3px);border-color:var(--primary)}
.personality-card.selected{background:linear-gradient(135deg,#5865F2,#EB459E);border-color:#fff}
@media (max-width: 768px) {
.feature-list{grid-template-columns:1fr}
.form-row{grid-template-columns:1fr}
.login-features{grid-template-columns:1fr}
.login-hero h1{font-size:50px}
.stats-grid{grid-template-columns:repeat(2,1fr)}
}
</style>
"""

DASHBOARD_HTML = """
<!DOCTYPE html><html><head><title>SentinelMod Dashboard</title>
""" + DASHBOARD_CSS + """
</head><body>
<div class="bg-shapes"><div class="shape shape1"></div><div class="shape shape2"></div><div class="shape shape3"></div></div>
<div id="notification" class="notification"></div>
<div class="container">{{ content | safe }}</div>
<script>
function showNotification(msg, type) {
    const n = document.getElementById('notification');
    n.textContent = msg;
    n.style.background = type === 'error' ? '#ed4245' : type === 'success' ? '#3ba55c' : '#5865F2';
    n.classList.add('show');
    setTimeout(() => n.classList.remove('show'), 3000);
}
function switchTab(tabName, element) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    element.classList.add('active');
    document.getElementById('tab-' + tabName).classList.add('active');
}
function toggleFeature(guildId, key, el) {
    fetch('/api/toggle/' + guildId + '/' + key, { method: 'POST' })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            el.classList.toggle('on');
            showNotification('✅ Setting updated!', 'success');
        } else {
            showNotification('❌ Failed to update', 'error');
        }
    });
}
function updateSetting(guildId, key, value) {
    fetch('/api/setting/' + guildId + '/' + key, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: value })
    }).then(r => r.json()).then(d => {
        if (d.success) showNotification('✅ Updated!', 'success');
    });
}
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function addCustomCommand(guildId) {
    const trigger = document.getElementById('cc-trigger').value;
    const response = document.getElementById('cc-response').value;
    if (!trigger || !response) { showNotification('❌ Fill both fields!', 'error'); return; }
    fetch('/api/custom/' + guildId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger: trigger, response: response })
    }).then(r => r.json()).then(d => {
        if (d.success) { showNotification('✅ Added!', 'success'); setTimeout(() => location.reload(), 1000); }
    });
}
function deleteCustomCommand(guildId, trigger) {
    if (!confirm('Delete "' + trigger + '"?')) return;
    fetch('/api/custom/' + guildId + '/' + encodeURIComponent(trigger), { method: 'DELETE' })
    .then(r => r.json()).then(d => {
        if (d.success) { showNotification('✅ Deleted!', 'success'); setTimeout(() => location.reload(), 1000); }
    });
}
function addWordFilter(guildId) {
    const word = document.getElementById('wf-word').value;
    if (!word) return;
    fetch('/api/wordfilter/' + guildId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word: word })
    }).then(r => r.json()).then(d => {
        if (d.success) { showNotification('✅ Added!', 'success'); setTimeout(() => location.reload(), 1000); }
    });
}
function removeWordFilter(guildId, word) {
    fetch('/api/wordfilter/' + guildId + '/' + encodeURIComponent(word), { method: 'DELETE' })
    .then(r => r.json()).then(d => {
        if (d.success) { showNotification('✅ Removed!', 'success'); setTimeout(() => location.reload(), 1000); }
    });
}
function clearUserWarnings(guildId, userId) {
    if (!confirm('Clear all warnings?')) return;
    fetch('/api/clearwarnings/' + guildId + '/' + userId, { method: 'POST' })
    .then(r => r.json()).then(d => {
        if (d.success) { showNotification('✅ Cleared!', 'success'); setTimeout(() => location.reload(), 1000); }
    });
}
function sendAnnouncement(guildId) {
    const channel = document.getElementById('ann-channel').value;
    const message = document.getElementById('ann-message').value;
    if (!channel || !message) { showNotification('❌ Fill both!', 'error'); return; }
    fetch('/api/announce/' + guildId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: channel, message: message })
    }).then(r => r.json()).then(d => {
        if (d.success) { showNotification('✅ Sent!', 'success'); document.getElementById('ann-message').value = ''; }
        else showNotification('❌ ' + (d.error || 'Failed'), 'error');
    });
}
</script>
</body></html>
"""

def render_page(content):
    return render_template_string(DASHBOARD_HTML, content=content)

@app.route("/")
def index():
    if "user" not in session:
        return render_page("""
<div class="login-container">
<div class="login-hero">
<h1>🛡️ SentinelMod</h1>
<p>The most powerful AI-driven Discord moderation bot. Manage everything from one beautiful dashboard.</p>
<div class="login-features">
<div class="login-feature"><div class="login-feature-icon">🤖</div><h3>AI Moderation</h3><p>Smart toxicity detection</p></div>
<div class="login-feature"><div class="login-feature-icon">⚡</div><h3>Instant Setup</h3><p>One click activation</p></div>
<div class="login-feature"><div class="login-feature-icon">🎮</div><h3>50+ Features</h3><p>Fun, mod, AI tools</p></div>
</div>
<a href="/login" class="discord-login-btn">🚀 Login with Discord</a>
</div>
</div>""")

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
                managable.append({**ug, "has_bot": int(ug["id"]) in bot_guild_ids})
        except:
            pass

    cards = ""
    for g in managable[:50]:
        icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None
        icon_html = f'<img src="{icon_url}">' if icon_url else g['name'][0]
        if g["has_bot"]:
            cards += f'''
<div class="server-card" onclick="window.location='/server/{g['id']}'">
<div class="server-header">
<div class="server-icon-wrap">{icon_html}</div>
<div class="server-info">
<h3>{g['name']}</h3>
<span class="server-badge badge-active">● Bot Active</span>
</div>
</div>
<a href="/server/{g['id']}" class="btn btn-primary" style="width:100%;justify-content:center;">⚙️ Manage Server</a>
</div>'''
        else:
            invite = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={g['id']}"
            cards += f'''
<div class="server-card">
<div class="server-header">
<div class="server-icon-wrap">{icon_html}</div>
<div class="server-info">
<h3>{g['name']}</h3>
<span class="server-badge badge-inactive">○ Not Added</span>
</div>
</div>
<a href="{invite}" target="_blank" class="btn btn-success" style="width:100%;justify-content:center;">➕ Add Bot to Server</a>
</div>'''

    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user.get("avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    total_servers = len([m for m in managable if m["has_bot"]])

    return render_page(f"""
<div class="navbar">
<div class="logo"><div class="logo-icon">🛡️</div><span class="logo-text">SentinelMod</span></div>
<div class="nav-right">
<div class="user-badge"><img src="{avatar}"><span>{user['username']}</span></div>
<a href="/logout" class="btn btn-danger">Logout</a>
</div>
</div>
<div class="page-header">
<div>
<h1 class="page-title">Welcome back, {user['username']}! 👋</h1>
<p class="page-subtitle">Managing {total_servers} server(s) with SentinelMod</p>
</div>
</div>
<div class="stats-grid">
<div class="stat-card"><div class="stat-icon">🏠</div><div class="stat-number">{total_servers}</div><div class="stat-label">Active Servers</div></div>
<div class="stat-card"><div class="stat-icon">👥</div><div class="stat-number">{sum(bot.get_guild(int(m["id"])).member_count for m in managable if m["has_bot"] and bot.get_guild(int(m["id"])))}</div><div class="stat-label">Total Members</div></div>
<div class="stat-card"><div class="stat-icon">⚙️</div><div class="stat-number">{len(managable)}</div><div class="stat-label">Manageable Servers</div></div>
<div class="stat-card"><div class="stat-icon">🤖</div><div class="stat-number">99%</div><div class="stat-label">Uptime</div></div>
</div>
<div class="section">
<div class="section-header">
<h2 class="section-title">🌐 Your Servers</h2>
</div>
<div class="servers-grid">{cards if cards else '<div class="empty-state"><div class="empty-state-icon">🔍</div><h3>No servers found</h3><p>Make sure you have admin permissions in a Discord server.</p></div>'}</div>
</div>""")

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
    customs_count = c.fetchone()[0]
    c.execute("SELECT * FROM warnings WHERE guild_id=? ORDER BY timestamp DESC LIMIT 20", (guild_id,))
    recent_warns = c.fetchall()
    c.execute("SELECT * FROM mod_actions WHERE guild_id=? ORDER BY timestamp DESC LIMIT 20", (guild_id,))
    recent_actions = c.fetchall()
    c.execute("SELECT * FROM custom_commands WHERE guild_id=?", (guild_id,))
    customs = c.fetchall()
    c.execute("SELECT word FROM word_filters WHERE guild_id=?", (guild_id,))
    words = c.fetchall()
    c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 10", (guild_id,))
    top_users = c.fetchall()
    c.execute("SELECT user_id, rep FROM reputation WHERE guild_id=? ORDER BY rep DESC LIMIT 10", (guild_id,))
    top_rep = c.fetchall()
    c.execute("SELECT * FROM giveaways WHERE guild_id=? AND active=1 ORDER BY id DESC", (guild_id,))
    giveaways = c.fetchall()
    c.execute("SELECT * FROM reminders WHERE guild_id=? AND active=1 ORDER BY remind_time", (guild_id,))
    reminders = c.fetchall()
    conn.close()

    features = [
        ("welcome_enabled", "👋", "Welcome Messages", "Greet new members"),
        ("anti_nuke_enabled", "💣", "Anti-Nuke", "Stop mass destruction"),
        ("invite_block", "🚫", "Block Invites", "Block discord.gg links"),
        ("link_scan", "🔗", "Link Scanner", "Detect phishing links"),
        ("slowmode_ai", "🐌", "AI Slowmode", "Auto slow heated chats"),
        ("pre_conflict", "⚠️", "Pre-Conflict AI", "Detect arguments early"),
        ("caps_filter", "🔤", "Caps Filter", "Block excessive caps"),
        ("mention_spam", "📢", "Mention Spam", "Block mass mentions"),
        ("emoji_spam", "😂", "Emoji Spam", "Block emoji floods"),
        ("zalgo_filter", "🌀", "Zalgo Filter", "Block weird text"),
        ("phone_filter", "📞", "Phone Filter", "Block phone numbers"),
        ("email_filter", "📧", "Email Filter", "Block email addresses"),
        ("scam_filter", "💸", "Scam Filter", "Detect scam patterns"),
        ("fake_nitro_filter", "💎", "Fake Nitro", "Block nitro scams"),
        ("token_filter", "🔑", "Token Grabber", "Block token grabbers"),
        ("anti_advertisement", "📣", "Anti-Ads", "Block advertisements"),
        ("everyone_block", "🔕", "@everyone Block", "Block @everyone usage"),
        ("nsfw_text_filter", "🔞", "NSFW Filter", "Block NSFW text"),
        ("unicode_filter", "🔠", "Unicode Bypass", "Detect unicode tricks"),
        ("file_spam_filter", "📁", "File Spam", "Block file spam")
    ]
    feature_html = ""
    for key, icon, name, desc in features:
        val = s.get(key, 0)
        feature_html += f'''
<div class="feature-toggle">
<div class="feature-toggle-header">
<div><span style="font-size:18px;">{icon}</span> <span class="feature-toggle-name">{name}</span></div>
<div class="toggle-switch {'on' if val else ''}" onclick="toggleFeature('{guild_id}', '{key}', this)"><div class="toggle-dot"></div></div>
</div>
<div class="feature-toggle-desc">{desc}</div>
</div>'''

    warns_html = ""
    for w in recent_warns:
        m = guild.get_member(int(w["user_id"]))
        name = m.display_name if m else f"Unknown User"
        avatar_char = name[0].upper()
        warns_html += f'''
<div class="list-item">
<div class="list-avatar">{avatar_char}</div>
<div class="list-content">
<div class="list-title">{name}</div>
<div class="list-subtitle">{w['reason']}</div>
<div class="list-meta">{w['timestamp'][:16]}</div>
</div>
<span class="severity-tag sev-{w['severity']}">{w['severity']}</span>
<button class="delete-btn" onclick="clearUserWarnings('{guild_id}', '{w['user_id']}')">Clear</button>
</div>'''

    actions_html = ""
    for a in recent_actions:
        m = guild.get_member(int(a["user_id"]))
        mod = guild.get_member(int(a["mod_id"]))
        name = m.display_name if m else "Unknown"
        mod_name = mod.display_name if mod else ("Bot" if a["mod_id"] == str(bot.user.id) else "Unknown")
        actions_html += f'''
<div class="list-item">
<div class="list-avatar">{name[0].upper()}</div>
<div class="list-content">
<div class="list-title">{name} - <span style="color:#5865F2;">{a['action']}</span></div>
<div class="list-subtitle">{a['reason']} • by {mod_name}</div>
<div class="list-meta">{a['timestamp'][:16]}</div>
</div>
</div>'''

    customs_html = ""
    for cc in customs:
        customs_html += f'''
<div class="command-row">
<div><span class="command-trigger">{cc['trigger_word']}</span> → {cc['response'][:60]}{'...' if len(cc['response']) > 60 else ''}</div>
<button class="delete-btn" onclick="deleteCustomCommand('{guild_id}', '{cc['trigger_word']}')">Delete</button>
</div>'''

    words_html = ""
    for w in words:
        words_html += f'''
<div class="command-row">
<span class="command-trigger">{w['word']}</span>
<button class="delete-btn" onclick="removeWordFilter('{guild_id}', '{w['word']}')">Remove</button>
</div>'''

    top_html = ""
    for i, r in enumerate(top_users, 1):
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "Unknown"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        top_html += f'''
<div class="list-item">
<div style="font-size:24px;width:42px;text-align:center;">{medal}</div>
<div class="list-content">
<div class="list-title">{name}</div>
<div class="list-subtitle">{r['message_count']} messages sent</div>
</div>
</div>'''

    rep_html = ""
    for i, r in enumerate(top_rep, 1):
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "Unknown"
        rep_html += f'''
<div class="list-item">
<div class="list-avatar">{name[0].upper()}</div>
<div class="list-content">
<div class="list-title">{name}</div>
<div class="list-subtitle">⭐ {r['rep']} reputation</div>
</div>
</div>'''

    channels_options = ""
    for ch in guild.text_channels[:50]:
        channels_options += f'<option value="{ch.name}">#{ch.name}</option>'

    giveaways_html = ""
    for gw in giveaways:
        giveaways_html += f'''
<div class="list-item">
<div style="font-size:24px;">🎉</div>
<div class="list-content">
<div class="list-title">{gw['prize']}</div>
<div class="list-subtitle">{gw['winners']} winner(s) • Ends: {gw['end_time'][:16]}</div>
</div>
</div>'''

    reminders_html = ""
    for r in reminders:
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "?"
        reminders_html += f'''
<div class="list-item">
<div style="font-size:24px;">⏰</div>
<div class="list-content">
<div class="list-title">{name}: {r['reminder']}</div>
<div class="list-subtitle">At: {r['remind_time'][:16]}</div>
</div>
</div>'''

    avatar = f"https://cdn.discordapp.com/avatars/{session['user']['id']}/{session['user']['avatar']}.png" if session['user'].get("avatar") else ""
    server_icon = f"https://cdn.discordapp.com/icons/{guild.id}/{guild.icon}.png" if guild.icon else None
    server_icon_html = f'<img src="{server_icon}">' if server_icon else guild.name[0]

    return render_page(f"""
<div class="navbar">
<div class="logo"><div class="logo-icon">🛡️</div><span class="logo-text">SentinelMod</span></div>
<div class="nav-right">
<div class="user-badge"><img src="{avatar}"><span>{session['user']['username']}</span></div>
<a href="/logout" class="btn btn-danger">Logout</a>
</div>
</div>

<a href="/" class="back-btn">← Back to Servers</a>

<div class="page-header">
<div style="display:flex;align-items:center;gap:20px;">
<div class="server-icon-wrap" style="width:80px;height:80px;font-size:32px;">{server_icon_html}</div>
<div>
<h1 class="page-title">{guild.name}</h1>
<p class="page-subtitle">{guild.member_count} members • {len(guild.text_channels)} channels • {len(guild.roles)} roles</p>
</div>
</div>
</div>

<div class="stats-grid">
<div class="stat-card"><div class="stat-icon">👥</div><div class="stat-number">{guild.member_count}</div><div class="stat-label">Members</div></div>
<div class="stat-card"><div class="stat-icon">⚠️</div><div class="stat-number">{warns}</div><div class="stat-label">Warnings</div></div>
<div class="stat-card"><div class="stat-icon">🔨</div><div class="stat-number">{actions}</div><div class="stat-label">Mod Actions</div></div>
<div class="stat-card"><div class="stat-icon">⚡</div><div class="stat-number">{customs_count}</div><div class="stat-label">Custom Commands</div></div>
</div>

<div class="tabs">
<button class="tab active" onclick="switchTab('overview', this)">📊 Overview</button>
<button class="tab" onclick="switchTab('features', this)">⚙️ Features</button>
<button class="tab" onclick="switchTab('moderation', this)">🛡️ Moderation</button>
<button class="tab" onclick="switchTab('warnings', this)">⚠️ Warnings</button>
<button class="tab" onclick="switchTab('commands', this)">⚡ Commands</button>
<button class="tab" onclick="switchTab('filters', this)">🔤 Filters</button>
<button class="tab" onclick="switchTab('leaderboard', this)">🏆 Leaderboard</button>
<button class="tab" onclick="switchTab('events', this)">🎉 Events</button>
<button class="tab" onclick="switchTab('settings', this)">🔧 Settings</button>
<button class="tab" onclick="switchTab('announce', this)">📢 Announce</button>
</div>

<div id="tab-overview" class="tab-content active">
<div class="section">
<div class="section-header"><h2 class="section-title">📊 Quick Overview</h2></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
<div>
<h3 style="margin-bottom:15px;color:var(--text-dim);font-size:14px;">RECENT WARNINGS</h3>
{warns_html if warns_html else '<p style="color:var(--text-dim);">No warnings yet!</p>'}
</div>
<div>
<h3 style="margin-bottom:15px;color:var(--text-dim);font-size:14px;">RECENT MOD ACTIONS</h3>
{actions_html if actions_html else '<p style="color:var(--text-dim);">No actions yet!</p>'}
</div>
</div>
</div>
</div>

<div id="tab-features" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">⚙️ Bot Features</h2></div>
<p style="color:var(--text-dim);margin-bottom:20px;">Toggle features on or off. Changes apply instantly.</p>
<div class="feature-list">{feature_html}</div>
</div>
</div>

<div id="tab-moderation" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">🛡️ Moderation Settings</h2></div>
<div class="form-row">
<div class="form-group">
<label class="form-label">Warnings before Mute</label>
<input type="number" class="form-input" value="{s.get('warn_mute', 3)}" onchange="updateSetting('{guild_id}', 'warn_mute', this.value)">
</div>
<div class="form-group">
<label class="form-label">Warnings before Ban</label>
<input type="number" class="form-input" value="{s.get('warn_ban', 5)}" onchange="updateSetting('{guild_id}', 'warn_ban', this.value)">
</div>
</div>
<div class="form-row">
<div class="form-group">
<label class="form-label">Mute Duration (minutes)</label>
<input type="number" class="form-input" value="{s.get('mute_duration', 10)}" onchange="updateSetting('{guild_id}', 'mute_duration', this.value)">
</div>
<div class="form-group">
<label class="form-label">AI Sensitivity (0.0 - 1.0)</label>
<input type="number" step="0.1" min="0" max="1" class="form-input" value="{s.get('ai_sensitivity', 0.7)}" onchange="updateSetting('{guild_id}', 'ai_sensitivity', this.value)">
</div>
</div>
<div class="form-row">
<div class="form-group">
<label class="form-label">Spam Limit (msgs)</label>
<input type="number" class="form-input" value="{s.get('spam_limit', 5)}" onchange="updateSetting('{guild_id}', 'spam_limit', this.value)">
</div>
<div class="form-group">
<label class="form-label">Spam Window (seconds)</label>
<input type="number" class="form-input" value="{s.get('spam_window', 5)}" onchange="updateSetting('{guild_id}', 'spam_window', this.value)">
</div>
</div>
<div class="form-row">
<div class="form-group">
<label class="form-label">Raid Detection Limit</label>
<input type="number" class="form-input" value="{s.get('raid_limit', 10)}" onchange="updateSetting('{guild_id}', 'raid_limit', this.value)">
</div>
<div class="form-group">
<label class="form-label">Min Account Age (days)</label>
<input type="number" class="form-input" value="{s.get('min_account_age', 7)}" onchange="updateSetting('{guild_id}', 'min_account_age', this.value)">
</div>
</div>
</div>
</div>

<div id="tab-warnings" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">⚠️ All Warnings ({warns})</h2></div>
{warns_html if warns_html else '<div class="empty-state"><div class="empty-state-icon">✅</div><h3>No warnings</h3><p>Your server is squeaky clean!</p></div>'}
</div>
</div>

<div id="tab-commands" class="tab-content">
<div class="section">
<div class="section-header">
<h2 class="section-title">⚡ Custom Commands</h2>
</div>
<div class="form-row">
<div class="form-group">
<label class="form-label">Trigger Word</label>
<input type="text" id="cc-trigger" class="form-input" placeholder="e.g. hello">
</div>
<div class="form-group">
<label class="form-label">Response</label>
<input type="text" id="cc-response" class="form-input" placeholder="e.g. Hi there!">
</div>
</div>
<button class="btn btn-primary" onclick="addCustomCommand('{guild_id}')">➕ Add Command</button>
<div style="margin-top:25px;">
{customs_html if customs_html else '<div class="empty-state"><div class="empty-state-icon">⚡</div><h3>No custom commands yet</h3><p>Create one above!</p></div>'}
</div>
</div>
</div>

<div id="tab-filters" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">🔤 Word Filters</h2></div>
<div style="display:flex;gap:10px;margin-bottom:20px;">
<input type="text" id="wf-word" class="form-input" placeholder="Enter word to block..." style="flex:1;">
<button class="btn btn-primary" onclick="addWordFilter('{guild_id}')">➕ Add</button>
</div>
{words_html if words_html else '<div class="empty-state"><div class="empty-state-icon">🔤</div><h3>No filtered words</h3><p>Add words you want auto-deleted</p></div>'}
</div>
</div>

<div id="tab-leaderboard" class="tab-content">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
<div class="section">
<div class="section-header"><h2 class="section-title">💬 Most Active</h2></div>
{top_html if top_html else '<p style="color:var(--text-dim);">No data yet</p>'}
</div>
<div class="section">
<div class="section-header"><h2 class="section-title">⭐ Top Reputation</h2></div>
{rep_html if rep_html else '<p style="color:var(--text-dim);">No reputation yet</p>'}
</div>
</div>
</div>

<div id="tab-events" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">🎉 Active Giveaways</h2></div>
{giveaways_html if giveaways_html else '<div class="empty-state"><div class="empty-state-icon">🎁</div><h3>No active giveaways</h3><p>Start one in Discord: @SentinelMod start a giveaway</p></div>'}
</div>
<div class="section">
<div class="section-header"><h2 class="section-title">⏰ Pending Reminders</h2></div>
{reminders_html if reminders_html else '<div class="empty-state"><div class="empty-state-icon">⏰</div><h3>No pending reminders</h3></div>'}
</div>
</div>

<div id="tab-settings" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">🔧 General Settings</h2></div>
<div class="form-group">
<label class="form-label">Mod Role Name</label>
<input type="text" class="form-input" value="{s.get('mod_role_name', 'Sentinel-Mod')}" onchange="updateSetting('{guild_id}', 'mod_role_name', this.value)">
</div>
<div class="form-row">
<div class="form-group">
<label class="form-label">Log Channel</label>
<input type="text" class="form-input" value="{s.get('log_channel', 'sentinel-logs')}" onchange="updateSetting('{guild_id}', 'log_channel', this.value)">
</div>
<div class="form-group">
<label class="form-label">Raid Alerts Channel</label>
<input type="text" class="form-input" value="{s.get('raid_channel', 'sentinel-raid-alerts')}" onchange="updateSetting('{guild_id}', 'raid_channel', this.value)">
</div>
</div>
<div class="form-group">
<label class="form-label">Welcome Channel</label>
<input type="text" class="form-input" value="{s.get('welcome_channel', 'welcome')}" onchange="updateSetting('{guild_id}', 'welcome_channel', this.value)">
</div>
</div>
</div>

<div id="tab-announce" class="tab-content">
<div class="section">
<div class="section-header"><h2 class="section-title">📢 Send Announcement</h2></div>
<p style="color:var(--text-dim);margin-bottom:20px;">Send a message to any channel as the bot.</p>
<div class="form-group">
<label class="form-label">Channel</label>
<select id="ann-channel" class="form-select">{channels_options}</select>
</div>
<div class="form-group">
<label class="form-label">Message</label>
<textarea id="ann-message" class="form-textarea" placeholder="Type your announcement..."></textarea>
</div>
<button class="btn btn-primary" onclick="sendAnnouncement('{guild_id}')">📤 Send Announcement</button>
</div>
</div>
""")

@app.route("/api/toggle/<guild_id>/<feature>", methods=["POST"])
def toggle_feature(guild_id, feature):
    if "user" not in session:
        return jsonify({"success": False})
    valid = ["welcome_enabled","anti_nuke_enabled","invite_block","link_scan","slowmode_ai","pre_conflict","caps_filter","mention_spam","emoji_spam","zalgo_filter","phone_filter","email_filter","scam_filter","fake_nitro_filter","token_filter","anti_advertisement","everyone_block","nsfw_text_filter","unicode_filter","file_spam_filter"]
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

@app.route("/api/setting/<guild_id>/<key>", methods=["POST"])
def update_setting_api(guild_id, key):
    if "user" not in session:
        return jsonify({"success": False})
    valid = ["warn_mute","warn_ban","mute_duration","ai_sensitivity","spam_limit","spam_window","raid_limit","min_account_age","mod_role_name","log_channel","raid_channel","welcome_channel"]
    if key not in valid:
        return jsonify({"success": False})
    data = request.get_json()
    value = data.get("value")
    try:
        if key in ["warn_mute","warn_ban","mute_duration","spam_limit","spam_window","raid_limit","min_account_age"]:
            value = int(value)
        elif key == "ai_sensitivity":
            value = float(value)
    except:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (value, guild_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/custom/<guild_id>", methods=["POST"])
def add_custom_api(guild_id):
    if "user" not in session:
        return jsonify({"success": False})
    data = request.get_json()
    trigger = data.get("trigger", "").lower().strip()
    response = data.get("response", "").strip()
    if not trigger or not response:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO custom_commands (guild_id, trigger_word, response) VALUES (?, ?, ?)", (guild_id, trigger, response))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/custom/<guild_id>/<trigger>", methods=["DELETE"])
def del_custom_api(guild_id, trigger):
    if "user" not in session:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM custom_commands WHERE guild_id=? AND trigger_word=?", (guild_id, trigger))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/wordfilter/<guild_id>", methods=["POST"])
def add_word_api(guild_id):
    if "user" not in session:
        return jsonify({"success": False})
    data = request.get_json()
    word = data.get("word", "").lower().strip()
    if not word:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)", (guild_id, word))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/wordfilter/<guild_id>/<word>", methods=["DELETE"])
def del_word_api(guild_id, word):
    if "user" not in session:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (guild_id, word.lower()))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/clearwarnings/<guild_id>/<user_id>", methods=["POST"])
def clear_warns_api(guild_id, user_id):
    if "user" not in session:
        return jsonify({"success": False})
    clear_warnings(user_id, guild_id)
    return jsonify({"success": True})

@app.route("/api/announce/<guild_id>", methods=["POST"])
def announce_api(guild_id):
    if "user" not in session:
        return jsonify({"success": False, "error": "Not logged in"})
    data = request.get_json()
    channel_name = data.get("channel")
    message = data.get("message")
    if not channel_name or not message:
        return jsonify({"success": False, "error": "Missing fields"})
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return jsonify({"success": False, "error": "Guild not found"})
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        return jsonify({"success": False, "error": "Channel not found"})
    try:
        embed = discord.Embed(title="📢 Announcement", description=message, color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_footer(text=f"Sent via Dashboard by {session['user']['username']}")
        asyncio.run_coroutine_threadsafe(channel.send(embed=embed), bot.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

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
        print("🌐 Dashboard on port 8080")
        print("🚀 Starting SentinelMod...")
        bot.run(DISCORD_TOKEN)
