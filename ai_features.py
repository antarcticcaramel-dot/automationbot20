# ai_features.py
# ================================
# Advanced AI Features Module v2.0 - PRO EDITION
# - AI Image Generation (multi-style)
# - Server FAQ AI with auto-learning
# - Auto-Translate (reactions + commands)
# - Mood Tracking with graphs
# - Daily AI Summaries with stats
# - AI Chat Threads
# - Smart Roles AI
# - Content Recommendations
# - AI Game Master
# - Voice Channel Activity AI
# - Sentiment Alerts
# - AI Conversation Starters
# - Dream Interpreter
# - Recipe Generator
# - Story Continuation
# ================================

import discord
from discord.ext import tasks, commands
from discord import app_commands
import aiohttp
import json
import os
import asyncio
import sqlite3
import io
import re
import random
import hashlib
from datetime import datetime, timedelta
from collections import Counter, defaultdict

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ============ LANGUAGE FLAGS ============
FLAG_TO_LANG = {
    "🇺🇸": "English", "🇬🇧": "English", "🇪🇸": "Spanish", "🇫🇷": "French",
    "🇩🇪": "German", "🇮🇹": "Italian", "🇵🇹": "Portuguese", "🇧🇷": "Portuguese (Brazilian)",
    "🇯🇵": "Japanese", "🇰🇷": "Korean", "🇨🇳": "Chinese (Mandarin)", "🇷🇺": "Russian",
    "🇸🇦": "Arabic", "🇮🇳": "Hindi", "🇳🇱": "Dutch", "🇵🇱": "Polish",
    "🇹🇷": "Turkish", "🇻🇳": "Vietnamese", "🇹🇭": "Thai", "🇮🇩": "Indonesian",
    "🇬🇷": "Greek", "🇸🇪": "Swedish", "🇳🇴": "Norwegian", "🇩🇰": "Danish",
    "🇫🇮": "Finnish", "🇨🇿": "Czech", "🇭🇺": "Hungarian", "🇷🇴": "Romanian",
    "🇺🇦": "Ukrainian", "🇮🇱": "Hebrew", "🇲🇽": "Spanish (Mexican)",
    "🇦🇷": "Spanish (Argentinian)", "🇨🇦": "English (Canadian)", "🇦🇺": "English (Australian)",
}

# ============ IMAGE STYLES ============
IMAGE_STYLES = {
    "realistic": "photorealistic, high quality, detailed, 8k",
    "anime": "anime style, vibrant colors, detailed illustration, studio ghibli",
    "cartoon": "cartoon style, colorful, fun, animated",
    "pixel": "pixel art, 16-bit, retro game style",
    "oil": "oil painting, classical art, brushstrokes, masterpiece",
    "watercolor": "watercolor painting, soft colors, artistic",
    "cyberpunk": "cyberpunk, neon lights, futuristic, dystopian",
    "fantasy": "fantasy art, magical, ethereal, detailed",
    "sketch": "pencil sketch, hand drawn, artistic",
    "3d": "3d render, octane render, detailed, realistic lighting",
    "minimalist": "minimalist, clean, simple, modern",
    "vaporwave": "vaporwave aesthetic, pink and blue, retro, 80s",
}

# ============ MOOD EMOJIS ============
MOOD_EMOJIS = {
    "happy": "😄", "sad": "😢", "excited": "🤩", "tense": "😬",
    "chill": "😎", "chaotic": "🤪", "wholesome": "🥰", "dramatic": "😱",
    "bored": "😴", "energetic": "⚡", "anxious": "😰", "playful": "😜",
    "neutral": "😐", "frustrated": "😤", "nostalgic": "🥺", "creative": "🎨",
    "competitive": "🔥", "supportive": "🤗", "curious": "🤔", "rebellious": "😈",
}

# Module globals
bot = None
get_db_func = None
get_guild_settings_func = None
ask_groq_func = None
ask_groq_json_func = None
notify_owner_func = None

# In-memory caches for performance
faq_cache: dict = {}
ai_thread_sessions: dict = {}
game_sessions: dict = {}

def setup(bot_instance, get_db, get_settings, ask_groq, ask_json, notify_owner=None):
    """Initialize the module with bot references."""
    global bot, get_db_func, get_guild_settings_func, ask_groq_func, ask_groq_json_func, notify_owner_func
    bot = bot_instance
    get_db_func = get_db
    get_guild_settings_func = get_settings
    ask_groq_func = ask_groq
    ask_groq_json_func = ask_json
    notify_owner_func = notify_owner
    init_tables()
    register_commands()
    register_events()
    start_tasks()
    print("AI Features Pro v2.0 loaded")

def init_tables():
    """Create all necessary tables."""
    conn = get_db_func()
    c = conn.cursor()
    tables = [
        """CREATE TABLE IF NOT EXISTS server_faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT, question TEXT, answer TEXT,
            added_by TEXT, usage_count INTEGER DEFAULT 0,
            timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS mood_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT, date TEXT, mood TEXT,
            confidence REAL, sample_size INTEGER,
            top_emotions TEXT, energy_level TEXT,
            vibe_summary TEXT, timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT, date TEXT UNIQUE,
            summary TEXT, highlights TEXT, top_users TEXT,
            message_count INTEGER, generated_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS ai_features_settings (
            guild_id TEXT PRIMARY KEY,
            faq_channel TEXT DEFAULT 'general',
            mood_tracking_enabled INTEGER DEFAULT 1,
            mood_channel TEXT DEFAULT 'general',
            mood_alerts_enabled INTEGER DEFAULT 1,
            daily_summary_enabled INTEGER DEFAULT 1,
            summary_channel TEXT DEFAULT 'general',
            translate_enabled INTEGER DEFAULT 1,
            image_gen_enabled INTEGER DEFAULT 1,
            auto_faq_enabled INTEGER DEFAULT 1,
            ai_threads_enabled INTEGER DEFAULT 1,
            conversation_starter_enabled INTEGER DEFAULT 0,
            conversation_starter_hours INTEGER DEFAULT 6,
            sentiment_alerts_enabled INTEGER DEFAULT 1,
            smart_roles_enabled INTEGER DEFAULT 0,
            image_gen_limit INTEGER DEFAULT 5,
            image_gen_window INTEGER DEFAULT 10
        )""",
        """CREATE TABLE IF NOT EXISTS image_gen_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, guild_id TEXT, prompt TEXT,
            style TEXT, timestamp TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS ai_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT, guild_id TEXT, owner_id TEXT,
            topic TEXT, message_count INTEGER DEFAULT 0,
            created_at TEXT, last_active TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS conversation_starters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT, topic TEXT, last_sent TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS game_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT, channel_id TEXT, game_type TEXT,
            state TEXT, players TEXT, created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS user_interests (
            user_id TEXT, guild_id TEXT, interests TEXT,
            personality_type TEXT, updated TEXT,
            PRIMARY KEY (user_id, guild_id)
        )""",
        """CREATE TABLE IF NOT EXISTS sentiment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, guild_id TEXT,
            sentiment TEXT, score REAL, timestamp TEXT
        )""",
    ]
    for t in tables:
        c.execute(t)
    
    # Migrations
    migrations = [
        ("ALTER TABLE server_faq ADD COLUMN usage_count INTEGER DEFAULT 0", "usage_count"),
        ("ALTER TABLE mood_log ADD COLUMN energy_level TEXT", "energy_level"),
        ("ALTER TABLE mood_log ADD COLUMN vibe_summary TEXT", "vibe_summary"),
        ("ALTER TABLE daily_summaries ADD COLUMN message_count INTEGER", "message_count"),
        ("ALTER TABLE ai_features_settings ADD COLUMN auto_faq_enabled INTEGER DEFAULT 1", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN ai_threads_enabled INTEGER DEFAULT 1", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN conversation_starter_enabled INTEGER DEFAULT 0", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN conversation_starter_hours INTEGER DEFAULT 6", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN sentiment_alerts_enabled INTEGER DEFAULT 1", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN smart_roles_enabled INTEGER DEFAULT 0", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN mood_alerts_enabled INTEGER DEFAULT 1", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN image_gen_limit INTEGER DEFAULT 5", ""),
        ("ALTER TABLE ai_features_settings ADD COLUMN image_gen_window INTEGER DEFAULT 10", ""),
    ]
    for query, _ in migrations:
        try: c.execute(query)
        except sqlite3.OperationalError: pass
    
    conn.commit()
    conn.close()

def get_ai_settings(gid):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("SELECT * FROM ai_features_settings WHERE guild_id=?", (str(gid),))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO ai_features_settings (guild_id) VALUES (?)", (str(gid),))
        conn.commit()
        c.execute("SELECT * FROM ai_features_settings WHERE guild_id=?", (str(gid),))
        row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_ai_setting(gid, key, value):
    conn = get_db_func()
    c = conn.cursor()
    get_ai_settings(gid)
    c.execute(f"UPDATE ai_features_settings SET {key}=? WHERE guild_id=?", (value, str(gid)))
    conn.commit()
    conn.close()

# ============================================
# FEATURE 1: ADVANCED IMAGE GENERATION
# ============================================

async def generate_image_pollinations(prompt: str, style: str = "realistic", width: int = 1024, height: int = 1024) -> bytes | None:
    """Generate image using Pollinations.ai with style modifiers."""
    try:
        import urllib.parse
        # Add style modifier
        style_modifier = IMAGE_STYLES.get(style, "")
        full_prompt = f"{prompt}, {style_modifier}" if style_modifier else prompt
        
        # Clean prompt
        clean_prompt = re.sub(r'[^\w\s,.\-!?]', '', full_prompt)[:500]
        encoded = urllib.parse.quote(clean_prompt)
        
        # Add seed for variety
        seed = random.randint(1, 999999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&enhance=true&seed={seed}&model=flux"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except asyncio.TimeoutError:
        print("Image gen timeout")
    except Exception as e:
        print(f"Image gen err: {e}")
    return None

def check_image_rate_limit(uid: str, gid: str) -> tuple[bool, int]:
    """Returns (within_limit, remaining)."""
    settings = get_ai_settings(gid)
    limit = settings.get("image_gen_limit", 5)
    window = settings.get("image_gen_window", 10)
    conn = get_db_func()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(minutes=window)).isoformat()
    c.execute("SELECT COUNT(*) FROM image_gen_log WHERE user_id=? AND guild_id=? AND timestamp > ?",
              (str(uid), str(gid), cutoff))
    count = c.fetchone()[0]
    conn.close()
    return count < limit, max(0, limit - count)

def log_image_gen(uid, gid, prompt, style="realistic"):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("INSERT INTO image_gen_log (user_id, guild_id, prompt, style, timestamp) VALUES (?, ?, ?, ?, ?)",
              (str(uid), str(gid), prompt, style, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ============================================
# FEATURE 2: SERVER FAQ WITH AUTO-LEARNING
# ============================================

def add_faq(gid, question, answer, added_by):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("INSERT INTO server_faq (guild_id, question, answer, added_by, timestamp) VALUES (?, ?, ?, ?, ?)",
              (str(gid), question, answer, str(added_by), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    # Clear cache
    if str(gid) in faq_cache:
        del faq_cache[str(gid)]

def get_all_faqs(gid):
    # Use cache
    cache_key = str(gid)
    if cache_key in faq_cache:
        cached_data, cached_time = faq_cache[cache_key]
        if (datetime.now() - cached_time).total_seconds() < 300:  # 5 min cache
            return cached_data
    
    conn = get_db_func()
    c = conn.cursor()
    c.execute("SELECT * FROM server_faq WHERE guild_id=? ORDER BY usage_count DESC, timestamp DESC", (str(gid),))
    rows = c.fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    faq_cache[cache_key] = (result, datetime.now())
    return result

def delete_faq(faq_id, gid):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("DELETE FROM server_faq WHERE id=? AND guild_id=?", (faq_id, str(gid)))
    conn.commit()
    conn.close()
    if str(gid) in faq_cache:
        del faq_cache[str(gid)]

def increment_faq_usage(faq_id):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("UPDATE server_faq SET usage_count = usage_count + 1 WHERE id=?", (faq_id,))
    conn.commit()
    conn.close()

async def answer_with_faq(question: str, gid: str, guild_name: str) -> tuple[str | None, int | None]:
    """Use AI to answer question based on stored FAQs. Returns (answer, faq_id)."""
    faqs = get_all_faqs(gid)
    if not faqs:
        return None, None
    
    faq_text = "\n".join(f"[ID:{f['id']}] Q: {f['question']}\nA: {f['answer']}" for f in faqs[:30])
    
    prompt = f"""You are the FAQ assistant for **{guild_name}** Discord server.

Available FAQ knowledge:
{faq_text}

User question: "{question}"

Instructions:
- Match question to relevant FAQs
- Combine multiple FAQs if needed
- Reply with JSON: {{"answer": "your response", "faq_ids_used": [1, 2], "confidence": 0.0-1.0}}
- If no match: {{"answer": null, "confidence": 0.0}}
- Keep under 400 chars
- Be friendly"""
    
    result = await ask_groq_json_func(prompt, "FAQ assistant. JSON only.")
    if not result or not result.get("answer") or result.get("confidence", 0) < 0.6:
        return None, None
    
    # Track usage
    for fid in result.get("faq_ids_used", []):
        try: increment_faq_usage(int(fid))
        except: pass
    
    return result["answer"], result.get("faq_ids_used", [None])[0]

# ============================================
# FEATURE 3: TRANSLATION SYSTEM
# ============================================

async def translate_text(text: str, target_lang: str) -> str | None:
    if not text or len(text) < 2:
        return None
    prompt = f"""Translate to {target_lang}. Reply with ONLY the translation, no quotes, no explanation:

{text[:1500]}"""
    result = await ask_groq_func(prompt, "Precise translator. Output only translation.")
    return result.strip() if result else None

async def detect_language(text: str) -> str | None:
    if not text or len(text) < 5:
        return None
    prompt = f"""What language is this text? Respond with just the language name in English (e.g., "Spanish", "Japanese"):

{text[:500]}"""
    result = await ask_groq_func(prompt, "Language detector.")
    return result.strip() if result else None

# ============================================
# FEATURE 4: MOOD TRACKING
# ============================================

async def analyze_mood(messages: list[str]) -> dict:
    if len(messages) < 5:
        return None
    sample = "\n".join(messages[:50])
    prompt = f"""Analyze the MOOD of these Discord messages:

{sample[:2500]}

JSON:
{{
  "overall_mood": "happy/sad/excited/tense/chill/chaotic/wholesome/dramatic/bored/energetic/anxious/playful/frustrated/nostalgic/creative/competitive/supportive/curious/rebellious",
  "confidence": 0.0-1.0,
  "top_emotions": ["e1", "e2", "e3"],
  "energy_level": "low/medium/high",
  "vibe_summary": "one sentence",
  "concerning": false
}}

Mark "concerning": true if you detect concerning patterns (depression, harassment, drama)."""
    return await ask_groq_json_func(prompt, "Mood analyzer. JSON only.")

def save_mood(gid, mood_data, sample_size):
    conn = get_db_func()
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute("""INSERT INTO mood_log (guild_id, date, mood, confidence, sample_size, top_emotions, energy_level, vibe_summary, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (str(gid), today, mood_data.get("overall_mood", "neutral"),
               mood_data.get("confidence", 0.5), sample_size,
               json.dumps(mood_data.get("top_emotions", [])),
               mood_data.get("energy_level", "medium"),
               mood_data.get("vibe_summary", ""),
               datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_mood_history(gid, days=7):
    conn = get_db_func()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute("SELECT * FROM mood_log WHERE guild_id=? AND timestamp > ? ORDER BY timestamp DESC", (str(gid), cutoff))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def build_mood_graph(history: list) -> str:
    """ASCII mood graph for the last 7 days."""
    if not history:
        return "No data"
    days = {}
    for h in history:
        days[h["date"]] = h["mood"]
    sorted_dates = sorted(days.keys())[-7:]
    lines = []
    for date in sorted_dates:
        mood = days[date]
        emoji = MOOD_EMOJIS.get(mood, "💭")
        lines.append(f"{date[5:]}: {emoji} {mood}")
    return "\n".join(lines)

async def do_mood_report(guild):
    try:
        conn = get_db_func()
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        c.execute("SELECT content FROM message_archive WHERE guild_id=? AND timestamp > ? ORDER BY timestamp DESC LIMIT 100",
                  (str(guild.id), cutoff))
        messages = [r["content"] for r in c.fetchall()]
        conn.close()
        
        if len(messages) < 5: return
        
        mood_data = await analyze_mood(messages)
        if not mood_data: return
        
        save_mood(guild.id, mood_data, len(messages))
        
        # Alert if concerning
        settings = get_ai_settings(guild.id)
        if mood_data.get("concerning") and settings.get("sentiment_alerts_enabled", 1):
            if notify_owner_func:
                await notify_owner_func("INFO", f"Concerning mood in **{guild.name}**: {mood_data.get('vibe_summary', '')}", guild=guild)
        
        ch_name = settings.get("mood_channel", "general")
        ch = discord.utils.get(guild.text_channels, name=ch_name) or guild.system_channel
        if not ch: return
        
        mood = mood_data.get("overall_mood", "neutral")
        emoji = MOOD_EMOJIS.get(mood, "💭")
        
        history = get_mood_history(guild.id, 7)
        trend = build_mood_graph(history)
        
        embed = discord.Embed(
            title=f"{emoji} Daily Server Mood",
            description=f"**Vibe:** {mood.title()}\n\n*{mood_data.get('vibe_summary', '')}*",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Top Emotions", value=", ".join(mood_data.get("top_emotions", ["mixed"])[:3]).title(), inline=True)
        embed.add_field(name="Energy", value=mood_data.get("energy_level", "medium").title(), inline=True)
        embed.add_field(name="Sample", value=f"{len(messages)} msgs", inline=True)
        if trend:
            embed.add_field(name="7-Day Trend", value=f"```{trend}```", inline=False)
        embed.set_footer(text=f"Confidence: {mood_data.get('confidence', 0.5):.0%}")
        await ch.send(embed=embed)
    except Exception as e:
        print(f"Mood report err: {e}")

# ============================================
# FEATURE 5: DAILY SUMMARIES
# ============================================

async def generate_daily_summary(guild):
    try:
        conn = get_db_func()
        c = conn.cursor()
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        c.execute("""SELECT user_id, content, channel_id FROM message_archive 
                     WHERE guild_id=? AND timestamp > ? ORDER BY timestamp ASC LIMIT 200""",
                  (str(guild.id), today_start))
        rows = c.fetchall()
        
        if len(rows) < 10:
            conn.close()
            return None
        
        user_counts = Counter(r["user_id"] for r in rows)
        top_users = []
        for uid, count in user_counts.most_common(5):
            member = guild.get_member(int(uid))
            if member: top_users.append(f"{member.display_name} ({count})")
        
        channel_counts = Counter(r["channel_id"] for r in rows)
        top_channels = []
        for cid, count in channel_counts.most_common(3):
            ch = guild.get_channel(int(cid))
            if ch: top_channels.append(f"#{ch.name} ({count})")
        
        msg_lines = []
        for r in rows[:80]:
            member = guild.get_member(int(r["user_id"]))
            name = member.display_name if member else "User"
            msg_lines.append(f"{name}: {r['content'][:120]}")
        
        sample = "\n".join(msg_lines)
        
        prompt = f"""Create a FUN daily recap of **{guild.name}** today.

Top members: {', '.join(top_users[:5])}
Active channels: {', '.join(top_channels)}

Today's messages sample:
{sample[:2500]}

JSON:
{{
  "title": "catchy title",
  "summary": "2-3 sentence fun summary",
  "highlights": ["highlight 1", "highlight 2", "highlight 3"],
  "fun_stat": "one fun random stat",
  "drama_meter": 0-10,
  "wholesome_meter": 0-10,
  "tomorrow_prediction": "playful prediction"
}}

Reference actual things from messages!"""
        
        result = await ask_groq_json_func(prompt, "Fun recap writer.")
        if not result:
            conn.close()
            return None
        
        today = datetime.now().date().isoformat()
        c.execute("""INSERT OR REPLACE INTO daily_summaries 
                     (guild_id, date, summary, highlights, top_users, message_count, generated_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (str(guild.id), today, json.dumps(result),
                   json.dumps(result.get("highlights", [])),
                   json.dumps(top_users), len(rows), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        settings = get_ai_settings(guild.id)
        ch_name = settings.get("summary_channel", "general")
        ch = discord.utils.get(guild.text_channels, name=ch_name) or guild.system_channel
        if not ch: return result
        
        embed = discord.Embed(
            title=f"📊 {result.get('title', 'Daily Recap')}",
            description=result.get("summary", "Another day!"),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        if result.get("highlights"):
            embed.add_field(name="Highlights", value="\n".join(f"• {h}" for h in result["highlights"][:5])[:1024], inline=False)
        if top_users:
            embed.add_field(name="MVPs", value="\n".join(f"🏆 {u}" for u in top_users[:3]), inline=True)
        if top_channels:
            embed.add_field(name="Hot Channels", value="\n".join(top_channels[:3]), inline=True)
        
        # Meters
        drama = result.get("drama_meter", 0)
        wholesome = result.get("wholesome_meter", 0)
        meters = f"Drama: {'🔥' * (drama // 2)}{'·' * (5 - drama // 2)} {drama}/10\n"
        meters += f"Wholesome: {'💖' * (wholesome // 2)}{'·' * (5 - wholesome // 2)} {wholesome}/10"
        embed.add_field(name="Today's Meters", value=meters, inline=False)
        
        if result.get("fun_stat"):
            embed.add_field(name="Fun Stat", value=result["fun_stat"], inline=False)
        if result.get("tomorrow_prediction"):
            embed.add_field(name="Tomorrow's Forecast", value=result["tomorrow_prediction"], inline=False)
        embed.set_footer(text=f"{today} • {len(rows)} messages")
        await ch.send(embed=embed)
        return result
    except Exception as e:
        print(f"Summary err: {e}")
        return None

# ============================================
# FEATURE 6: CONVERSATION STARTERS
# ============================================

async def generate_conversation_starter(guild):
    """Generate a topic to spark conversation when chat is dead."""
    try:
        conn = get_db_func()
        c = conn.cursor()
        # Get popular topics
        c.execute("SELECT popular_topics FROM server_memory WHERE guild_id=?", (str(guild.id),))
        row = c.fetchone()
        topics = []
        if row and row["popular_topics"]:
            try: topics = json.loads(row["popular_topics"])
            except: pass
        conn.close()
        
        topic_hint = f"This server talks about: {', '.join(topics[:5])}" if topics else "General Discord community"
        
        prompt = f"""Generate ONE engaging conversation starter question for a Discord server.
{topic_hint}

Make it:
- Fun, casual, easy to answer
- Open-ended (not yes/no)
- Something everyone can chime in on
- Under 100 chars

Just respond with the question itself, no preamble."""
        
        question = await ask_groq_func(prompt, "Conversation starter generator. Be fun and engaging.")
        if not question: return
        
        question = question.strip().strip('"').strip("'")
        
        settings = get_ai_settings(guild.id)
        ch_name = settings.get("summary_channel", "general")
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if not ch: ch = guild.system_channel
        if not ch:
            for c in guild.text_channels:
                if c.permissions_for(guild.me).send_messages:
                    ch = c
                    break
        if not ch: return
        
        # Check if there's been recent activity
        try:
            async for msg in ch.history(limit=5):
                # If last message is less than 30 min old, skip
                if (datetime.now() - msg.created_at.replace(tzinfo=None)).total_seconds() < 1800:
                    return
                break
        except: pass
        
        embed = discord.Embed(
            title="💬 Let's chat!",
            description=question,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Conversation starter | Drop your thoughts below!")
        await ch.send(embed=embed)
    except Exception as e:
        print(f"Starter err: {e}")

# ============================================
# FEATURE 7: AI GAME MASTER
# ============================================

async def start_word_chain(channel, starter_word="apple"):
    """Word chain game - each word starts with last letter of previous."""
    game_sessions[channel.id] = {
        "type": "wordchain",
        "current_word": starter_word.lower(),
        "used_words": {starter_word.lower()},
        "started": datetime.now(),
        "players": {}
    }
    embed = discord.Embed(
        title="🔗 Word Chain Game",
        description=f"Start word: **{starter_word}**\n\nNext word must start with: **{starter_word[-1].upper()}**\n\nNo repeats! Type your word in chat.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Game ends in 5 minutes of inactivity")
    await channel.send(embed=embed)

async def handle_word_chain(message):
    if message.channel.id not in game_sessions: return False
    game = game_sessions[message.channel.id]
    if game["type"] != "wordchain": return False
    
    word = message.content.strip().lower()
    if not word.isalpha() or len(word) < 2: return False
    
    expected_letter = game["current_word"][-1]
    if not word.startswith(expected_letter):
        return False
    
    if word in game["used_words"]:
        try: await message.reply(f"Already used! Try another word starting with **{expected_letter.upper()}**", delete_after=5)
        except: pass
        return True
    
    game["current_word"] = word
    game["used_words"].add(word)
    game["players"][str(message.author.id)] = game["players"].get(str(message.author.id), 0) + 1
    
    try: await message.add_reaction("✅")
    except: pass
    
    # Bot responds with next word occasionally
    if random.random() < 0.3:
        next_letter = word[-1]
        bot_words = ["amazing", "elephant", "trumpet", "tiger", "rocket", "umbrella", "orange", "energy", "yellow", "wonder"]
        candidates = [w for w in bot_words if w.startswith(next_letter) and w not in game["used_words"]]
        if candidates:
            bot_word = random.choice(candidates)
            game["current_word"] = bot_word
            game["used_words"].add(bot_word)
            await asyncio.sleep(1)
            try: await message.channel.send(f"🤖 My word: **{bot_word}** (next letter: **{bot_word[-1].upper()}**)")
            except: pass
    
    return True

async def play_20_questions(channel, user, thing):
    """20 questions game where bot tries to guess what user is thinking of."""
    game_sessions[channel.id] = {
        "type": "20q",
        "thing": thing.lower(),
        "questions_asked": 0,
        "max_questions": 20,
        "host": user.id,
        "started": datetime.now()
    }
    await channel.send(f"🎮 **20 Questions** started! I'll try to guess what you're thinking of in 20 yes/no questions.\n\nReady? Let me start...")
    await asyncio.sleep(1)
    
    prompt = f"""Play 20 questions. Ask your FIRST yes/no question to figure out what someone is thinking of. Be strategic.
Just the question, nothing else."""
    question = await ask_groq_func(prompt, "20 questions game master.")
    if question:
        await channel.send(f"**Question 1/20:** {question}")

# ============================================
# FEATURE 8: AI CHAT THREADS
# ============================================

async def create_ai_thread(message, topic: str):
    """Create a Discord thread with AI conversation."""
    try:
        thread = await message.create_thread(name=f"AI: {topic[:50]}", auto_archive_duration=60)
        
        conn = get_db_func()
        c = conn.cursor()
        c.execute("""INSERT INTO ai_threads (channel_id, guild_id, owner_id, topic, created_at, last_active)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (str(thread.id), str(message.guild.id), str(message.author.id),
                   topic, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        ai_thread_sessions[thread.id] = {
            "topic": topic,
            "owner_id": message.author.id,
            "history": [],
        }
        
        # Initial AI message
        prompt = f"Start a conversation about: {topic}. Greet the user and engage them. Keep it natural and fun. 1-2 sentences."
        intro = await ask_groq_func(prompt, "Friendly AI chat companion. NEVER swear.")
        if intro:
            await thread.send(intro)
        return thread
    except Exception as e:
        print(f"Thread err: {e}")
        return None

async def handle_ai_thread_message(message):
    """Handle messages in AI threads."""
    if not isinstance(message.channel, discord.Thread): return False
    if message.channel.id not in ai_thread_sessions: return False
    
    session = ai_thread_sessions[message.channel.id]
    session["history"].append({"role": "user", "content": message.content})
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]
    
    async with message.channel.typing():
        prompt = f"Continue conversation about: {session['topic']}. Be engaging."
        response = await ask_groq_func(message.content, 
                                       f"You're an AI chat companion in a Discord thread. Topic: {session['topic']}. Be engaging, helpful, fun. NEVER swear. Keep responses conversational.",
                                       history=session["history"])
        if response:
            session["history"].append({"role": "assistant", "content": response})
            try: await message.channel.send(response[:2000])
            except: pass
    return True

# ============================================
# FEATURE 9: SMART CONTENT RECOMMENDATIONS
# ============================================

async def recommend_content(message, category: str):
    """Recommend movies, books, games, music based on user request."""
    prompt = f"""Recommend 3 {category} based on this request: "{message.content}"

JSON:
{{
  "recommendations": [
    {{"name": "name", "description": "1 sentence why", "rating": "9/10"}},
    {{"name": "name", "description": "...", "rating": "..."}},
    {{"name": "name", "description": "...", "rating": "..."}}
  ],
  "vibe": "the overall vibe of these recommendations"
}}"""
    return await ask_groq_json_func(prompt, "Content recommendation expert.")

# ============================================
# FEATURE 10: DREAM INTERPRETER
# ============================================

async def interpret_dream(dream_text: str):
    prompt = f"""Interpret this dream creatively and thoughtfully:

"{dream_text[:1000]}"

JSON:
{{
  "interpretation": "main interpretation (2-3 sentences)",
  "symbols": [
    {{"symbol": "what appeared", "meaning": "what it might mean"}},
    {{"symbol": "...", "meaning": "..."}}
  ],
  "mood": "the emotional theme",
  "advice": "thoughtful advice based on the dream"
}}

Be insightful but not preachy. Treat it like dream symbolism for fun."""
    return await ask_groq_json_func(prompt, "Dream interpreter. JSON only.")

# ============================================
# FEATURE 11: RECIPE GENERATOR
# ============================================

async def generate_recipe(ingredients: str):
    prompt = f"""Generate a recipe using these ingredients: {ingredients}

JSON:
{{
  "name": "recipe name",
  "description": "1 sentence description",
  "prep_time": "X min",
  "cook_time": "X min",
  "difficulty": "easy/medium/hard",
  "ingredients": ["ing 1 with amount", "ing 2 with amount"],
  "steps": ["step 1", "step 2", "step 3"],
  "tips": "one helpful tip"
}}"""
    return await ask_groq_json_func(prompt, "Recipe creator. JSON only.")

# ============================================
# FEATURE 12: STORY CONTINUATION
# ============================================

async def continue_story(story_so_far: str):
    prompt = f"""Continue this story by 2-3 paragraphs. Match the style and tone:

{story_so_far[:1500]}

Just write the continuation, no preamble. Keep it clean and engaging."""
    return await ask_groq_func(prompt, "Creative storyteller. NEVER swear.")

# ============================================
# SLASH COMMANDS
# ============================================

def register_commands():
    
    # ========== IMAGE GEN ==========
    @bot.tree.command(name="imagine", description="Generate an AI image")
    @app_commands.describe(prompt="Describe the image", style="Art style")
    @app_commands.choices(style=[app_commands.Choice(name=k.title(), value=k) for k in list(IMAGE_STYLES.keys())[:25]])
    async def imagine_cmd(interaction: discord.Interaction, prompt: str, style: app_commands.Choice[str] = None):
        style_value = style.value if style else "realistic"
        
        within, remaining = check_image_rate_limit(str(interaction.user.id), str(interaction.guild.id))
        if not within:
            await interaction.response.send_message("Slow down! You've hit the image limit.", ephemeral=True)
            return
        
        settings = get_ai_settings(interaction.guild.id)
        if not settings.get("image_gen_enabled", 1):
            await interaction.response.send_message("Image generation disabled here.", ephemeral=True)
            return
        
        await interaction.response.defer()
        loading = await interaction.followup.send(embed=discord.Embed(
            title="Generating image...",
            description=f"**Prompt:** {prompt[:200]}\n**Style:** {style_value.title()}\n\n*10-30 seconds...*",
            color=discord.Color.blurple()
        ))
        
        image_bytes = await generate_image_pollinations(prompt, style_value)
        if image_bytes:
            log_image_gen(interaction.user.id, interaction.guild.id, prompt, style_value)
            file = discord.File(io.BytesIO(image_bytes), filename="ai_image.png")
            embed = discord.Embed(
                title="Image Generated",
                description=f"**Prompt:** {prompt[:300]}\n**Style:** {style_value.title()}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_image(url="attachment://ai_image.png")
            embed.set_footer(text=f"By {interaction.user.display_name} | {remaining-1} left this window")
            await loading.delete()
            await interaction.followup.send(embed=embed, file=file)
        else:
            await loading.edit(embed=discord.Embed(title="Failed", description="Try a different prompt!", color=discord.Color.red()))
    
    @bot.tree.command(name="imagine_variations", description="Generate 4 variations of an image")
    @app_commands.describe(prompt="Describe the image")
    async def variations_cmd(interaction: discord.Interaction, prompt: str):
        within, _ = check_image_rate_limit(str(interaction.user.id), str(interaction.guild.id))
        if not within:
            await interaction.response.send_message("Slow down!", ephemeral=True); return
        
        await interaction.response.defer()
        loading = await interaction.followup.send("Generating 4 variations...")
        
        styles = random.sample(list(IMAGE_STYLES.keys()), 4)
        tasks = [generate_image_pollinations(prompt, s, 512, 512) for s in styles]
        results = await asyncio.gather(*tasks)
        
        files = []
        for i, (img, style) in enumerate(zip(results, styles)):
            if img: files.append(discord.File(io.BytesIO(img), filename=f"variation_{i}_{style}.png"))
        
        log_image_gen(interaction.user.id, interaction.guild.id, prompt, "variations")
        
        if files:
            await loading.delete()
            await interaction.followup.send(content=f"**4 variations of:** {prompt}\nStyles: {', '.join(styles)}", files=files)
        else:
            await loading.edit(content="Failed to generate!")
    
    # ========== FAQ ==========
    @bot.tree.command(name="faq_add", description="[Admin] Add an FAQ")
    async def faq_add_cmd(interaction: discord.Interaction, question: str, answer: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Server perm required!", ephemeral=True); return
        add_faq(interaction.guild.id, question, answer, interaction.user.id)
        await interaction.response.send_message(embed=discord.Embed(title="FAQ Added",
            description=f"**Q:** {question}\n**A:** {answer}", color=discord.Color.green()), ephemeral=True)
    
    @bot.tree.command(name="faq_list", description="View server FAQs")
    async def faq_list_cmd(interaction: discord.Interaction):
        faqs = get_all_faqs(interaction.guild.id)
        if not faqs:
            await interaction.response.send_message("No FAQs yet!", ephemeral=True); return
        embed = discord.Embed(title=f"{interaction.guild.name} FAQs", description=f"Total: {len(faqs)}\nAsk me questions naturally - I auto-detect FAQ matches!", color=discord.Color.blue())
        for f in faqs[:10]:
            embed.add_field(name=f"Q: {f['question'][:100]}",
                value=f"A: {f['answer'][:200]}\n*ID: {f['id']} • Used {f.get('usage_count', 0)}x*", inline=False)
        if len(faqs) > 10: embed.set_footer(text=f"Showing 10/{len(faqs)}")
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="faq_delete", description="[Admin] Delete an FAQ")
    async def faq_delete_cmd(interaction: discord.Interaction, faq_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Admin only!", ephemeral=True); return
        delete_faq(faq_id, interaction.guild.id)
        await interaction.response.send_message(f"FAQ #{faq_id} deleted!", ephemeral=True)
    
    @bot.tree.command(name="ask", description="Ask about this server")
    async def ask_cmd(interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        answer, _ = await answer_with_faq(question, interaction.guild.id, interaction.guild.name)
        if answer:
            embed = discord.Embed(title="FAQ Match", description=answer, color=discord.Color.green())
            embed.add_field(name="You asked", value=question[:200], inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=discord.Embed(title="No FAQ Match",
                description=f"Question: {question}\n\nAsk an admin to add it!", color=discord.Color.orange()))
    
    # ========== TRANSLATION ==========
    @bot.tree.command(name="translate", description="Translate text")
    @app_commands.describe(text="Text to translate", language="Target language")
    async def translate_cmd(interaction: discord.Interaction, text: str, language: str = "English"):
        await interaction.response.defer()
        result = await translate_text(text, language)
        if result:
            embed = discord.Embed(title=f"Translation to {language}", description=result[:2000], color=discord.Color.blue())
            embed.add_field(name="Original", value=text[:500], inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Failed to translate.")
    
    @bot.tree.command(name="detect_language", description="Detect what language text is in")
    async def detect_lang_cmd(interaction: discord.Interaction, text: str):
        await interaction.response.defer()
        lang = await detect_language(text)
        if lang:
            await interaction.followup.send(f"Detected: **{lang}**")
        else:
            await interaction.followup.send("Couldn't detect language.")
    
    # ========== MOOD ==========
    @bot.tree.command(name="mood", description="Check current server mood")
    async def mood_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db_func()
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=6)).isoformat()
        c.execute("SELECT content FROM message_archive WHERE guild_id=? AND timestamp > ? LIMIT 50", (str(interaction.guild.id), cutoff))
        messages = [r["content"] for r in c.fetchall()]
        conn.close()
        if len(messages) < 5:
            await interaction.followup.send("Not enough activity!"); return
        mood_data = await analyze_mood(messages)
        if not mood_data:
            await interaction.followup.send("Couldn't analyze."); return
        mood = mood_data.get("overall_mood", "neutral")
        emoji = MOOD_EMOJIS.get(mood, "💭")
        embed = discord.Embed(title=f"{emoji} Server Mood", description=f"**{mood.title()}**\n*{mood_data.get('vibe_summary', '')}*", color=discord.Color.purple())
        embed.add_field(name="Emotions", value=", ".join(mood_data.get("top_emotions", ["mixed"])[:3]).title(), inline=True)
        embed.add_field(name="Energy", value=mood_data.get("energy_level", "medium").title(), inline=True)
        embed.add_field(name="Sample", value=f"{len(messages)} msgs", inline=True)
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="mood_history", description="See mood over past week")
    async def mood_history_cmd(interaction: discord.Interaction):
        history = get_mood_history(interaction.guild.id, 7)
        if not history:
            await interaction.response.send_message("No history!", ephemeral=True); return
        graph = build_mood_graph(history)
        embed = discord.Embed(title="7-Day Mood History", description=f"```{graph}```", color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)
    
    # ========== RECAP ==========
    @bot.tree.command(name="recap", description="Today's server recap")
    async def recap_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        today = datetime.now().date().isoformat()
        conn = get_db_func()
        c = conn.cursor()
        c.execute("SELECT * FROM daily_summaries WHERE guild_id=? AND date=?", (str(interaction.guild.id), today))
        existing = c.fetchone()
        conn.close()
        if existing:
            data = json.loads(existing["summary"])
            embed = discord.Embed(title=data.get('title', 'Daily Recap'), description=data.get("summary", ""), color=discord.Color.gold())
            if data.get("highlights"):
                embed.add_field(name="Highlights", value="\n".join(f"• {h}" for h in data["highlights"]), inline=False)
            if data.get("fun_stat"):
                embed.add_field(name="Fun Stat", value=data["fun_stat"], inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Generating...")
            result = await generate_daily_summary(interaction.guild)
            if not result: await interaction.followup.send("Not enough activity!")
    
    # ========== AI CHAT THREAD ==========
    @bot.tree.command(name="thread", description="Start an AI chat thread")
    @app_commands.describe(topic="What to chat about")
    async def thread_cmd(interaction: discord.Interaction, topic: str):
        settings = get_ai_settings(interaction.guild.id)
        if not settings.get("ai_threads_enabled", 1):
            await interaction.response.send_message("AI threads disabled here.", ephemeral=True); return
        await interaction.response.send_message(f"Creating thread about: **{topic}**...", ephemeral=True)
        # Get the followup message
        msg = await interaction.followup.send(f"Starting AI thread about **{topic}**")
        thread = await create_ai_thread(msg, topic)
        if thread:
            await interaction.followup.send(f"Thread created: {thread.mention}", ephemeral=True)
    
    # ========== GAMES ==========
    @bot.tree.command(name="wordchain", description="Start a word chain game")
    async def wordchain_cmd(interaction: discord.Interaction, starter: str = None):
        if not starter:
            starter = random.choice(["apple", "tiger", "rocket", "music", "ocean", "fire", "snow", "cloud"])
        await interaction.response.send_message(f"Starting word chain with: **{starter}**")
        await start_word_chain(interaction.channel, starter)
    
    @bot.tree.command(name="20questions", description="Play 20 questions - I'll try to guess what you're thinking")
    @app_commands.describe(thing="What you're thinking of (kept secret from others)")
    async def twenty_q_cmd(interaction: discord.Interaction, thing: str):
        await interaction.response.send_message("Game started! Check the channel.", ephemeral=True)
        await play_20_questions(interaction.channel, interaction.user, thing)
    
    @bot.tree.command(name="game_stop", description="Stop the current game in this channel")
    async def stop_game_cmd(interaction: discord.Interaction):
        if interaction.channel.id in game_sessions:
            del game_sessions[interaction.channel.id]
            await interaction.response.send_message("Game ended!")
        else:
            await interaction.response.send_message("No game running here.", ephemeral=True)
    
    # ========== FUN AI ==========
    @bot.tree.command(name="dream", description="Interpret a dream")
    @app_commands.describe(dream="Describe your dream")
    async def dream_cmd(interaction: discord.Interaction, dream: str):
        await interaction.response.defer()
        result = await interpret_dream(dream)
        if not result:
            await interaction.followup.send("Couldn't interpret."); return
        embed = discord.Embed(title="🌙 Dream Interpretation", description=result.get("interpretation", ""), color=discord.Color.dark_purple())
        if result.get("symbols"):
            symbols_text = "\n".join(f"• **{s['symbol']}**: {s['meaning']}" for s in result["symbols"][:5])
            embed.add_field(name="Symbols", value=symbols_text[:1024], inline=False)
        if result.get("mood"):
            embed.add_field(name="Mood", value=result["mood"], inline=True)
        if result.get("advice"):
            embed.add_field(name="Advice", value=result["advice"], inline=False)
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="recipe", description="Get a recipe from ingredients")
    @app_commands.describe(ingredients="Ingredients you have (comma separated)")
    async def recipe_cmd(interaction: discord.Interaction, ingredients: str):
        await interaction.response.defer()
        result = await generate_recipe(ingredients)
        if not result:
            await interaction.followup.send("Couldn't create recipe."); return
        embed = discord.Embed(title=f"🍳 {result.get('name', 'Recipe')}", description=result.get("description", ""), color=discord.Color.orange())
        embed.add_field(name="Prep Time", value=result.get("prep_time", "?"), inline=True)
        embed.add_field(name="Cook Time", value=result.get("cook_time", "?"), inline=True)
        embed.add_field(name="Difficulty", value=result.get("difficulty", "?").title(), inline=True)
        if result.get("ingredients"):
            embed.add_field(name="Ingredients", value="\n".join(f"• {i}" for i in result["ingredients"][:10])[:1024], inline=False)
        if result.get("steps"):
            embed.add_field(name="Steps", value="\n".join(f"{i+1}. {s}" for i, s in enumerate(result["steps"][:8]))[:1024], inline=False)
        if result.get("tips"):
            embed.add_field(name="Tip", value=result["tips"], inline=False)
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="story", description="Start or continue a collaborative story")
    @app_commands.describe(story="The story so far (or starting prompt)")
    async def story_cmd(interaction: discord.Interaction, story: str):
        await interaction.response.defer()
        continuation = await continue_story(story)
        if not continuation:
            await interaction.followup.send("Couldn't continue."); return
        embed = discord.Embed(title="📖 Story Continues...", description=continuation[:4000], color=discord.Color.dark_blue())
        embed.set_footer(text="Run /story again with the new version to keep it going!")
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="recommend", description="Get AI recommendations")
    @app_commands.describe(category="What to recommend", request="What you're looking for")
    @app_commands.choices(category=[
        app_commands.Choice(name="Movies", value="movies"),
        app_commands.Choice(name="Books", value="books"),
        app_commands.Choice(name="Games", value="games"),
        app_commands.Choice(name="Music", value="music"),
        app_commands.Choice(name="Anime", value="anime"),
        app_commands.Choice(name="TV Shows", value="TV shows"),
    ])
    async def recommend_cmd(interaction: discord.Interaction, category: app_commands.Choice[str], request: str):
        await interaction.response.defer()
        # Mock a message for recommend_content
        class FakeMsg:
            content = request
        result = await recommend_content(FakeMsg(), category.value)
        if not result:
            await interaction.followup.send("Couldn't get recommendations."); return
        embed = discord.Embed(title=f"🎯 {category.name} Recommendations", description=f"*{result.get('vibe', '')}*", color=discord.Color.green())
        for rec in result.get("recommendations", [])[:3]:
            embed.add_field(name=f"{rec.get('rating', '?')} - {rec.get('name', '?')}", value=rec.get("description", ""), inline=False)
        await interaction.followup.send(embed=embed)
    
    # ========== SETTINGS ==========
    @bot.tree.command(name="ai_settings", description="[Admin] View AI features settings")
    async def ai_settings_cmd(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only!", ephemeral=True); return
        s = get_ai_settings(interaction.guild.id)
        embed = discord.Embed(title="AI Features Settings", color=discord.Color.blue())
        features = [
            ("Image Gen", "image_gen_enabled"), ("Translate", "translate_enabled"),
            ("Mood Track", "mood_tracking_enabled"), ("Daily Recap", "daily_summary_enabled"),
            ("Auto-FAQ", "auto_faq_enabled"), ("AI Threads", "ai_threads_enabled"),
            ("Conv Starters", "conversation_starter_enabled"), ("Sentiment Alerts", "sentiment_alerts_enabled"),
        ]
        for name, key in features:
            embed.add_field(name=name, value="ON" if s.get(key, 1) else "OFF", inline=True)
        embed.add_field(name="Mood Channel", value=f"#{s.get('mood_channel', 'general')}", inline=True)
        embed.add_field(name="Recap Channel", value=f"#{s.get('summary_channel', 'general')}", inline=True)
        embed.set_footer(text="Use /ai_toggle to enable/disable")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="ai_toggle", description="[Admin] Toggle AI features")
    @app_commands.choices(feature=[
        app_commands.Choice(name="Image Gen", value="image_gen_enabled"),
        app_commands.Choice(name="Translate", value="translate_enabled"),
        app_commands.Choice(name="Mood Track", value="mood_tracking_enabled"),
        app_commands.Choice(name="Daily Recap", value="daily_summary_enabled"),
        app_commands.Choice(name="Auto-FAQ", value="auto_faq_enabled"),
        app_commands.Choice(name="AI Threads", value="ai_threads_enabled"),
        app_commands.Choice(name="Conv Starters", value="conversation_starter_enabled"),
        app_commands.Choice(name="Sentiment Alerts", value="sentiment_alerts_enabled"),
    ])
    @app_commands.choices(state=[app_commands.Choice(name="ON", value="on"), app_commands.Choice(name="OFF", value="off")])
    async def ai_toggle_cmd(interaction: discord.Interaction, feature: app_commands.Choice[str], state: app_commands.Choice[str]):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only!", ephemeral=True); return
        update_ai_setting(interaction.guild.id, feature.value, 1 if state.value == "on" else 0)
        await interaction.response.send_message(f"{feature.name} → **{state.name}**", ephemeral=True)
    
    @bot.tree.command(name="ai_channel", description="[Admin] Set channel for AI reports")
    @app_commands.choices(report_type=[
        app_commands.Choice(name="Mood Reports", value="mood_channel"),
        app_commands.Choice(name="Daily Recaps", value="summary_channel"),
    ])
    async def ai_channel_cmd(interaction: discord.Interaction, report_type: app_commands.Choice[str], channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only!", ephemeral=True); return
        update_ai_setting(interaction.guild.id, report_type.value, channel.name)
        await interaction.response.send_message(f"{report_type.name} → {channel.mention}", ephemeral=True)
    
    @bot.tree.command(name="ai_limit", description="[Admin] Set image generation limit")
    @app_commands.describe(limit="Max images per window", window_minutes="Time window in minutes")
    async def ai_limit_cmd(interaction: discord.Interaction, limit: int, window_minutes: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only!", ephemeral=True); return
        limit = max(1, min(limit, 50))
        window_minutes = max(1, min(window_minutes, 1440))
        update_ai_setting(interaction.guild.id, "image_gen_limit", limit)
        update_ai_setting(interaction.guild.id, "image_gen_window", window_minutes)
        await interaction.response.send_message(f"Image limit: **{limit}** per **{window_minutes}min**", ephemeral=True)

# ============================================
# EVENT HANDLERS
# ============================================

def register_events():
    # Store original on_raw_reaction_add if exists
    @bot.event
    async def on_raw_reaction_add(payload):
        if payload.user_id == bot.user.id: return
        emoji = str(payload.emoji)
        if emoji not in FLAG_TO_LANG: return
        target_lang = FLAG_TO_LANG[emoji]
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        settings = get_ai_settings(guild.id)
        if not settings.get("translate_enabled", 1): return
        channel = guild.get_channel(payload.channel_id)
        if not channel: return
        try: message = await channel.fetch_message(payload.message_id)
        except: return
        if not message.content or len(message.content) < 3: return
        for reaction in message.reactions:
            if str(reaction.emoji) == "✅" and reaction.me: return
        translation = await translate_text(message.content, target_lang)
        if not translation: return
        user = guild.get_member(payload.user_id)
        embed = discord.Embed(title=f"{emoji} Translated to {target_lang}", description=translation[:2000], color=discord.Color.blue())
        embed.add_field(name="Original", value=message.content[:500], inline=False)
        embed.set_footer(text=f"By {user.display_name if user else 'someone'}")
        try:
            await message.reply(embed=embed, mention_author=False)
            await message.add_reaction("✅")
        except Exception as e:
            print(f"Translate err: {e}")

# ============================================
# BACKGROUND TASKS
# ============================================

def start_tasks():
    @tasks.loop(hours=6)
    async def mood_tracker():
        for guild in bot.guilds:
            try:
                settings = get_ai_settings(guild.id)
                if not settings.get("mood_tracking_enabled", 1): continue
                await do_mood_report(guild)
                await asyncio.sleep(3)
            except Exception as e: print(f"Mood task err: {e}")
    
    @tasks.loop(hours=24)
    async def daily_recap_task():
        for guild in bot.guilds:
            try:
                settings = get_ai_settings(guild.id)
                if not settings.get("daily_summary_enabled", 1): continue
                await generate_daily_summary(guild)
                await asyncio.sleep(3)
            except Exception as e: print(f"Recap err: {e}")
    
    @tasks.loop(hours=3)
    async def conversation_starter_task():
        for guild in bot.guilds:
            try:
                settings = get_ai_settings(guild.id)
                if not settings.get("conversation_starter_enabled", 0): continue
                # Check last starter time
                conn = get_db_func()
                c = conn.cursor()
                c.execute("SELECT last_sent FROM conversation_starters WHERE guild_id=? ORDER BY id DESC LIMIT 1", (str(guild.id),))
                row = c.fetchone()
                conn.close()
                hours_setting = settings.get("conversation_starter_hours", 6)
                if row:
                    last = datetime.fromisoformat(row["last_sent"])
                    if (datetime.now() - last).total_seconds() < hours_setting * 3600:
                        continue
                await generate_conversation_starter(guild)
                # Log
                conn = get_db_func()
                c = conn.cursor()
                c.execute("INSERT INTO conversation_starters (guild_id, topic, last_sent) VALUES (?, ?, ?)",
                          (str(guild.id), "auto", datetime.now().isoformat()))
                conn.commit()
                conn.close()
                await asyncio.sleep(3)
            except Exception as e: print(f"Starter task err: {e}")
    
    @tasks.loop(minutes=10)
    async def game_cleanup():
        """Clean up stale game sessions."""
        now = datetime.now()
        to_remove = []
        for ch_id, game in game_sessions.items():
            if (now - game.get("started", now)).total_seconds() > 600:
                to_remove.append(ch_id)
        for ch_id in to_remove:
            del game_sessions[ch_id]
    
    mood_tracker.start()
    daily_recap_task.start()
    conversation_starter_task.start()
    game_cleanup.start()

# ============================================
# PUBLIC FUNCTIONS (called from bot.py)
# ============================================

async def check_for_faq_question(message):
    """Auto-detect questions matching FAQs."""
    if not message.guild or message.author.bot: return False
    settings = get_ai_settings(message.guild.id)
    if not settings.get("auto_faq_enabled", 1): return False
    
    content = message.content.strip()
    if not (content.endswith("?") or content.lower().startswith(("how", "what", "where", "when", "why", "can ", "does ", "is ", "are ", "do "))):
        return False
    if len(content) < 10 or len(content) > 300: return False
    
    answer, _ = await answer_with_faq(content, str(message.guild.id), message.guild.name)
    if answer:
        embed = discord.Embed(description=f"💡 {answer}", color=discord.Color.blue())
        embed.set_footer(text="From server FAQ | /faq_list for all")
        try:
            await message.reply(embed=embed, mention_author=False)
            return True
        except: pass
    return False

async def handle_game_message(message):
    """Handle messages for active games."""
    if message.channel.id not in game_sessions: return False
    game = game_sessions[message.channel.id]
    
    if game["type"] == "wordchain":
        return await handle_word_chain(message)
    elif game["type"] == "20q":
        if message.author.id != game["host"]:
            response = message.content.lower().strip()
            if response in ["yes", "y", "no", "n", "kinda", "sometimes", "unknown"]:
                game["questions_asked"] += 1
                if game["questions_asked"] >= game["max_questions"]:
                    await message.channel.send(f"I give up! It was **{game['thing']}**!")
                    del game_sessions[message.channel.id]
                    return True
                prompt = f"""Playing 20 questions. They're thinking of: {game['thing']}
Last question response: {response}
Questions asked: {game['questions_asked']}/20

Ask your NEXT yes/no question to figure it out faster. Just the question."""
                next_q = await ask_groq_func(prompt, "20Q game master.")
                if next_q:
                    await message.channel.send(f"**Q{game['questions_asked']+1}/20:** {next_q}")
                return True
    return False

async def handle_thread_message(message):
    """Handle AI thread messages."""
    return await handle_ai_thread_message(message)
