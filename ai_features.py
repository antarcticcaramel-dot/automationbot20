# ai_features.py
# ================================
# Advanced AI Features Module
# - AI Image Generation
# - Server FAQ AI
# - Auto-Translate (reaction)
# - Mood Tracking
# - Daily AI Summaries
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
from datetime import datetime, timedelta
from collections import Counter

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

# Translation flags (emoji → language)
FLAG_TO_LANG = {
    "🇺🇸": "English", "🇬🇧": "English", "🇪🇸": "Spanish", "🇫🇷": "French",
    "🇩🇪": "German", "🇮🇹": "Italian", "🇵🇹": "Portuguese", "🇧🇷": "Portuguese",
    "🇯🇵": "Japanese", "🇰🇷": "Korean", "🇨🇳": "Chinese", "🇷🇺": "Russian",
    "🇸🇦": "Arabic", "🇮🇳": "Hindi", "🇳🇱": "Dutch", "🇵🇱": "Polish",
    "🇹🇷": "Turkish", "🇻🇳": "Vietnamese", "🇹🇭": "Thai", "🇮🇩": "Indonesian",
    "🇬🇷": "Greek", "🇸🇪": "Swedish", "🇳🇴": "Norwegian", "🇩🇰": "Danish",
    "🇫🇮": "Finnish", "🇨🇿": "Czech", "🇭🇺": "Hungarian", "🇷🇴": "Romanian",
    "🇺🇦": "Ukrainian", "🇮🇱": "Hebrew",
}

# Will be set by bot.py
bot = None
get_db_func = None
get_guild_settings_func = None
ask_groq_func = None
ask_groq_json_func = None
notify_owner_func = None

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
    print("✅ AI Features module loaded")

def init_tables():
    """Create necessary tables."""
    conn = get_db_func()
    c = conn.cursor()
    tables = [
        # Server FAQ entries
        """CREATE TABLE IF NOT EXISTS server_faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            question TEXT,
            answer TEXT,
            added_by TEXT,
            timestamp TEXT
        )""",
        # Mood tracking
        """CREATE TABLE IF NOT EXISTS mood_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            date TEXT,
            mood TEXT,
            confidence REAL,
            sample_size INTEGER,
            top_emotions TEXT,
            timestamp TEXT
        )""",
        # Daily summaries
        """CREATE TABLE IF NOT EXISTS daily_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            date TEXT UNIQUE,
            summary TEXT,
            highlights TEXT,
            top_users TEXT,
            generated_at TEXT
        )""",
        # AI feature settings
        """CREATE TABLE IF NOT EXISTS ai_features_settings (
            guild_id TEXT PRIMARY KEY,
            faq_channel TEXT DEFAULT 'general',
            mood_tracking_enabled INTEGER DEFAULT 1,
            mood_channel TEXT DEFAULT 'general',
            mood_report_time TEXT DEFAULT '20:00',
            daily_summary_enabled INTEGER DEFAULT 1,
            summary_channel TEXT DEFAULT 'general',
            summary_time TEXT DEFAULT '23:00',
            translate_enabled INTEGER DEFAULT 1,
            image_gen_enabled INTEGER DEFAULT 1
        )""",
        # Track image generations (rate limit)
        """CREATE TABLE IF NOT EXISTS image_gen_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            guild_id TEXT,
            prompt TEXT,
            timestamp TEXT
        )""",
    ]
    for t in tables:
        c.execute(t)
    conn.commit()
    conn.close()

def get_ai_settings(gid):
    """Get AI feature settings for guild."""
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
    get_ai_settings(gid)  # ensure exists
    c.execute(f"UPDATE ai_features_settings SET {key}=? WHERE guild_id=?", (value, str(gid)))
    conn.commit()
    conn.close()

# ============================================
# 🎨 FEATURE 1: AI IMAGE GENERATION
# ============================================

async def generate_image_pollinations(prompt: str) -> bytes | None:
    """
    Generate image using Pollinations.ai - 100% FREE, no API key needed!
    """
    try:
        # Clean prompt
        clean_prompt = re.sub(r'[^\w\s,.-]', '', prompt)[:200]
        
        # Pollinations.ai free image gen
        url = f"https://image.pollinations.ai/prompt/{aiohttp.helpers.quote(clean_prompt)}?width=1024&height=1024&nologo=true&enhance=true"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    print(f"Image gen status: {resp.status}")
    except asyncio.TimeoutError:
        print("Image gen timeout")
    except Exception as e:
        print(f"Image gen err: {e}")
    return None

def check_image_rate_limit(uid: str, gid: str, limit: int = 5, window_min: int = 10) -> bool:
    """Returns True if user is within limit."""
    conn = get_db_func()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(minutes=window_min)).isoformat()
    c.execute(
        "SELECT COUNT(*) FROM image_gen_log WHERE user_id=? AND guild_id=? AND timestamp > ?",
        (str(uid), str(gid), cutoff)
    )
    count = c.fetchone()[0]
    conn.close()
    return count < limit

def log_image_gen(uid, gid, prompt):
    conn = get_db_func()
    c = conn.cursor()
    c.execute(
        "INSERT INTO image_gen_log (user_id, guild_id, prompt, timestamp) VALUES (?, ?, ?, ?)",
        (str(uid), str(gid), prompt, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ============================================
# 📚 FEATURE 2: SERVER FAQ AI
# ============================================

def add_faq(gid, question, answer, added_by):
    conn = get_db_func()
    c = conn.cursor()
    c.execute(
        "INSERT INTO server_faq (guild_id, question, answer, added_by, timestamp) VALUES (?, ?, ?, ?, ?)",
        (str(gid), question, answer, str(added_by), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_all_faqs(gid):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("SELECT * FROM server_faq WHERE guild_id=? ORDER BY timestamp DESC", (str(gid),))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_faq(faq_id, gid):
    conn = get_db_func()
    c = conn.cursor()
    c.execute("DELETE FROM server_faq WHERE id=? AND guild_id=?", (faq_id, str(gid)))
    conn.commit()
    conn.close()

async def answer_with_faq(question: str, gid: str, guild_name: str) -> str | None:
    """Use AI to answer question based on stored FAQs."""
    faqs = get_all_faqs(gid)
    if not faqs:
        return None
    
    faq_text = "\n".join(f"Q: {f['question']}\nA: {f['answer']}" for f in faqs[:30])
    
    prompt = f"""You are the FAQ assistant for the **{guild_name}** Discord server.

Available FAQ knowledge:
{faq_text}

User question: "{question}"

Instructions:
- If the question matches ANY FAQ closely, answer using that info
- Combine multiple FAQs if relevant
- If no FAQ matches, respond: "NO_MATCH"
- Be friendly and use the server's name
- Keep response under 500 chars
- Don't make up info not in the FAQs

Answer:"""
    
    response = await ask_groq_func(prompt, "FAQ assistant. Be helpful but only use provided info.")
    
    if response and "NO_MATCH" not in response.upper():
        return response.strip()
    return None

# ============================================
# 🌍 FEATURE 3: AUTO-TRANSLATE (Reaction)
# ============================================

async def translate_text(text: str, target_lang: str) -> str | None:
    """Translate text using Groq."""
    if not text or len(text) < 2:
        return None
    
    prompt = f"""Translate this text to {target_lang}. Reply with ONLY the translation, no quotes, no explanation:

{text[:1500]}"""
    
    result = await ask_groq_func(prompt, "You are a precise translator. Output only translation.")
    return result.strip() if result else None

# ============================================
# 💭 FEATURE 4: MOOD TRACKING
# ============================================

async def analyze_mood(messages: list[str]) -> dict:
    """Analyze the collective mood of messages."""
    if len(messages) < 5:
        return None
    
    sample = "\n".join(messages[:50])
    
    prompt = f"""Analyze the overall MOOD of these Discord messages:

{sample[:2500]}

Return JSON:
{{
  "overall_mood": "happy/sad/excited/tense/chill/chaotic/wholesome/dramatic/bored/energetic/anxious/playful",
  "confidence": 0.0-1.0,
  "top_emotions": ["emotion1", "emotion2", "emotion3"],
  "energy_level": "low/medium/high",
  "vibe_summary": "one sentence describing the vibe"
}}"""
    
    result = await ask_groq_json_func(prompt, "Mood analyzer. JSON only.")
    return result

def save_mood(gid, mood_data, sample_size):
    conn = get_db_func()
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute(
        """INSERT INTO mood_log (guild_id, date, mood, confidence, sample_size, top_emotions, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            str(gid), today,
            mood_data.get("overall_mood", "neutral"),
            mood_data.get("confidence", 0.5),
            sample_size,
            json.dumps(mood_data.get("top_emotions", [])),
            datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()

def get_mood_history(gid, days=7):
    conn = get_db_func()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute(
        "SELECT * FROM mood_log WHERE guild_id=? AND timestamp > ? ORDER BY timestamp DESC",
        (str(gid), cutoff)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

MOOD_EMOJIS = {
    "happy": "😄", "sad": "😢", "excited": "🤩", "tense": "😬",
    "chill": "😎", "chaotic": "🤪", "wholesome": "🥰", "dramatic": "😱",
    "bored": "😴", "energetic": "⚡", "anxious": "😰", "playful": "😜",
    "neutral": "😐"
}

async def do_mood_report(guild):
    """Generate and send mood report for a guild."""
    try:
        conn = get_db_func()
        c = conn.cursor()
        # Get last 24h of messages
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        c.execute(
            "SELECT content FROM message_archive WHERE guild_id=? AND timestamp > ? ORDER BY timestamp DESC LIMIT 100",
            (str(guild.id), cutoff)
        )
        messages = [r["content"] for r in c.fetchall()]
        conn.close()
        
        if len(messages) < 5:
            return
        
        mood_data = await analyze_mood(messages)
        if not mood_data:
            return
        
        save_mood(guild.id, mood_data, len(messages))
        
        settings = get_ai_settings(guild.id)
        ch_name = settings.get("mood_channel", "general")
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if not ch:
            ch = guild.system_channel
        if not ch:
            return
        
        mood = mood_data.get("overall_mood", "neutral")
        emoji = MOOD_EMOJIS.get(mood, "💭")
        
        # Get mood history for trend
        history = get_mood_history(guild.id, 7)
        trend = ""
        if len(history) >= 2:
            recent_moods = [h["mood"] for h in history[:3]]
            mood_counts = Counter(recent_moods)
            trend = f"\n📈 **Recent trend:** {', '.join(f'{m} ({c}x)' for m, c in mood_counts.most_common())}"
        
        embed = discord.Embed(
            title=f"{emoji} Daily Server Mood",
            description=f"**Today's Vibe:** {mood.title()}\n\n*{mood_data.get('vibe_summary', '')}*",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="🎭 Top Emotions",
            value=", ".join(mood_data.get("top_emotions", ["mixed"])[:3]).title(),
            inline=True
        )
        embed.add_field(
            name="⚡ Energy",
            value=mood_data.get("energy_level", "medium").title(),
            inline=True
        )
        embed.add_field(
            name="📊 Sample",
            value=f"{len(messages)} messages",
            inline=True
        )
        if trend:
            embed.add_field(name="📈 7-Day Trend", value=trend, inline=False)
        embed.set_footer(text=f"Mood confidence: {mood_data.get('confidence', 0.5):.0%}")
        
        await ch.send(embed=embed)
    except Exception as e:
        print(f"Mood report err: {e}")

# ============================================
# 📊 FEATURE 5: DAILY AI SUMMARIES
# ============================================

async def generate_daily_summary(guild):
    """Generate a fun daily recap of what happened in the server."""
    try:
        conn = get_db_func()
        c = conn.cursor()
        
        # Get today's messages
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        c.execute(
            """SELECT user_id, content, channel_id FROM message_archive 
               WHERE guild_id=? AND timestamp > ? ORDER BY timestamp ASC LIMIT 200""",
            (str(guild.id), today_start)
        )
        rows = c.fetchall()
        
        if len(rows) < 10:
            conn.close()
            return None
        
        # Get top users
        user_counts = Counter(r["user_id"] for r in rows)
        top_users = []
        for uid, count in user_counts.most_common(5):
            member = guild.get_member(int(uid))
            if member:
                top_users.append(f"{member.display_name} ({count} msgs)")
        
        # Get top channels
        channel_counts = Counter(r["channel_id"] for r in rows)
        top_channels = []
        for cid, count in channel_counts.most_common(3):
            ch = guild.get_channel(int(cid))
            if ch:
                top_channels.append(f"#{ch.name} ({count})")
        
        # Build message sample for AI
        msg_lines = []
        for r in rows[:80]:
            member = guild.get_member(int(r["user_id"]))
            name = member.display_name if member else "User"
            msg_lines.append(f"{name}: {r['content'][:120]}")
        
        sample = "\n".join(msg_lines)
        
        prompt = f"""Create a FUN daily recap of what happened in the **{guild.name}** Discord server today.

Top active members:
{', '.join(top_users[:5])}

Active channels:
{', '.join(top_channels)}

Sample of today's messages:
{sample[:2500]}

Generate JSON:
{{
  "title": "Catchy title for today's recap",
  "summary": "2-3 sentence fun summary of the day",
  "highlights": [
    "Highlight 1 (interesting moment)",
    "Highlight 2 (notable event)",
    "Highlight 3 (funny thing if any)"
  ],
  "fun_stat": "One fun random stat about today",
  "tomorrow_prediction": "Playful prediction for tomorrow"
}}

Be entertaining and reference actual things from the messages!"""
        
        result = await ask_groq_json_func(prompt, "Fun community recap writer.")
        
        if not result:
            conn.close()
            return None
        
        # Save summary
        today = datetime.now().date().isoformat()
        c.execute(
            """INSERT OR REPLACE INTO daily_summaries 
               (guild_id, date, summary, highlights, top_users, generated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(guild.id), today,
                json.dumps(result),
                json.dumps(result.get("highlights", [])),
                json.dumps(top_users),
                datetime.now().isoformat()
            )
        )
        conn.commit()
        conn.close()
        
        # Send to channel
        settings = get_ai_settings(guild.id)
        ch_name = settings.get("summary_channel", "general")
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if not ch:
            ch = guild.system_channel
        if not ch:
            return result
        
        embed = discord.Embed(
            title=f"📊 {result.get('title', 'Daily Recap')}",
            description=result.get("summary", "Another day in paradise!"),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        if result.get("highlights"):
            highlights_text = "\n".join(f"• {h}" for h in result["highlights"][:5])
            embed.add_field(name="✨ Highlights", value=highlights_text[:1024], inline=False)
        
        if top_users:
            embed.add_field(name="👑 MVPs", value="\n".join(f"🏆 {u}" for u in top_users[:3]), inline=True)
        
        if top_channels:
            embed.add_field(name="🔥 Hot Channels", value="\n".join(top_channels[:3]), inline=True)
        
        if result.get("fun_stat"):
            embed.add_field(name="🎲 Fun Stat", value=result["fun_stat"], inline=False)
        
        if result.get("tomorrow_prediction"):
            embed.add_field(name="🔮 Tomorrow's Forecast", value=result["tomorrow_prediction"], inline=False)
        
        embed.set_footer(text=f"📅 {today} • {len(rows)} messages analyzed")
        
        await ch.send(embed=embed)
        return result
    except Exception as e:
        print(f"Summary err: {e}")
        return None

# ============================================
# SLASH COMMANDS
# ============================================

def register_commands():
    
    # ========== IMAGE GEN ==========
    @bot.tree.command(name="imagine", description="🎨 Generate an AI image from a prompt")
    @app_commands.describe(prompt="Describe the image you want")
    async def imagine_cmd(interaction: discord.Interaction, prompt: str):
        # Rate limit check
        if not check_image_rate_limit(str(interaction.user.id), str(interaction.guild.id)):
            await interaction.response.send_message(
                "⏰ Slow down! Max 5 images per 10 minutes.",
                ephemeral=True
            )
            return
        
        settings = get_ai_settings(interaction.guild.id)
        if not settings.get("image_gen_enabled", 1):
            await interaction.response.send_message("❌ Image generation is disabled here.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Show progress
        loading_embed = discord.Embed(
            title="🎨 Generating your image...",
            description=f"**Prompt:** {prompt[:200]}\n\n*This takes 10-30 seconds...*",
            color=discord.Color.blurple()
        )
        loading_msg = await interaction.followup.send(embed=loading_embed)
        
        # Generate
        image_bytes = await generate_image_pollinations(prompt)
        
        if image_bytes:
            log_image_gen(interaction.user.id, interaction.guild.id, prompt)
            
            file = discord.File(io.BytesIO(image_bytes), filename="ai_image.png")
            embed = discord.Embed(
                title="🎨 Image Generated!",
                description=f"**Prompt:** {prompt[:300]}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_image(url="attachment://ai_image.png")
            embed.set_footer(text=f"Generated by {interaction.user.display_name} • Pollinations AI")
            
            await loading_msg.delete()
            await interaction.followup.send(embed=embed, file=file)
        else:
            await loading_msg.edit(embed=discord.Embed(
                title="❌ Image Generation Failed",
                description="Couldn't generate the image. Try a different prompt!",
                color=discord.Color.red()
            ))
    
    # ========== FAQ ==========
    @bot.tree.command(name="faq_add", description="[Admin] Add an FAQ entry")
    @app_commands.describe(question="The question", answer="The answer")
    async def faq_add_cmd(interaction: discord.Interaction, question: str, answer: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Manage Server permission required!", ephemeral=True)
            return
        add_faq(interaction.guild.id, question, answer, interaction.user.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ FAQ Added!",
                description=f"**Q:** {question}\n**A:** {answer}",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
    
    @bot.tree.command(name="faq_list", description="View all server FAQs")
    async def faq_list_cmd(interaction: discord.Interaction):
        faqs = get_all_faqs(interaction.guild.id)
        if not faqs:
            await interaction.response.send_message("📭 No FAQs yet! Admins can add with `/faq_add`", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📚 {interaction.guild.name} FAQs",
            description=f"Total: {len(faqs)} entries\n\n💡 Just ask me questions in chat - I'll auto-detect FAQ matches!",
            color=discord.Color.blue()
        )
        for f in faqs[:10]:
            embed.add_field(
                name=f"❓ {f['question'][:100]}",
                value=f"💬 {f['answer'][:200]}\n*ID: {f['id']}*",
                inline=False
            )
        if len(faqs) > 10:
            embed.set_footer(text=f"Showing 10/{len(faqs)} FAQs")
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="faq_delete", description="[Admin] Delete an FAQ entry")
    @app_commands.describe(faq_id="The FAQ ID (from /faq_list)")
    async def faq_delete_cmd(interaction: discord.Interaction, faq_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ Manage Server required!", ephemeral=True)
            return
        delete_faq(faq_id, interaction.guild.id)
        await interaction.response.send_message(f"🗑️ FAQ #{faq_id} deleted!", ephemeral=True)
    
    @bot.tree.command(name="ask", description="📚 Ask a question about this server")
    @app_commands.describe(question="Your question about the server")
    async def ask_cmd(interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        answer = await answer_with_faq(question, interaction.guild.id, interaction.guild.name)
        if answer:
            embed = discord.Embed(
                title="💡 FAQ Match!",
                description=answer,
                color=discord.Color.green()
            )
            embed.add_field(name="❓ You asked", value=question[:200], inline=False)
            embed.set_footer(text="Use /faq_list to see all FAQs")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="🤷 No FAQ Match",
                    description=f"I don't have info about that yet.\n\n**Your question:** {question}\n\nAsk an admin to add it with `/faq_add`!",
                    color=discord.Color.orange()
                )
            )
    
    # ========== MOOD ==========
    @bot.tree.command(name="mood", description="💭 Check current server mood")
    async def mood_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get recent messages
        conn = get_db_func()
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=6)).isoformat()
        c.execute(
            "SELECT content FROM message_archive WHERE guild_id=? AND timestamp > ? LIMIT 50",
            (str(interaction.guild.id), cutoff)
        )
        messages = [r["content"] for r in c.fetchall()]
        conn.close()
        
        if len(messages) < 5:
            await interaction.followup.send("📊 Not enough recent activity to analyze mood. Chat more!")
            return
        
        mood_data = await analyze_mood(messages)
        if not mood_data:
            await interaction.followup.send("❌ Couldn't analyze mood right now.")
            return
        
        mood = mood_data.get("overall_mood", "neutral")
        emoji = MOOD_EMOJIS.get(mood, "💭")
        
        embed = discord.Embed(
            title=f"{emoji} Current Server Mood",
            description=f"**{mood.title()}**\n\n*{mood_data.get('vibe_summary', '')}*",
            color=discord.Color.purple()
        )
        embed.add_field(name="🎭 Top Emotions", value=", ".join(mood_data.get("top_emotions", ["mixed"])[:3]).title(), inline=True)
        embed.add_field(name="⚡ Energy", value=mood_data.get("energy_level", "medium").title(), inline=True)
        embed.add_field(name="📊 Sample", value=f"{len(messages)} msgs", inline=True)
        embed.set_footer(text=f"Confidence: {mood_data.get('confidence', 0.5):.0%}")
        
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="mood_history", description="See server mood over past week")
    async def mood_history_cmd(interaction: discord.Interaction):
        history = get_mood_history(interaction.guild.id, 7)
        if not history:
            await interaction.response.send_message("📭 No mood history yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📈 Mood History (7 days)",
            color=discord.Color.purple()
        )
        for h in history[:10]:
            mood = h["mood"]
            emoji = MOOD_EMOJIS.get(mood, "💭")
            date = h["date"]
            embed.add_field(
                name=f"{emoji} {date}",
                value=f"**{mood.title()}** ({h['sample_size']} msgs)",
                inline=True
            )
        await interaction.response.send_message(embed=embed)
    
    # ========== DAILY SUMMARY ==========
    @bot.tree.command(name="recap", description="📊 Get today's server recap")
    async def recap_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Check if we have today's summary
        today = datetime.now().date().isoformat()
        conn = get_db_func()
        c = conn.cursor()
        c.execute("SELECT * FROM daily_summaries WHERE guild_id=? AND date=?", (str(interaction.guild.id), today))
        existing = c.fetchone()
        conn.close()
        
        if existing:
            data = json.loads(existing["summary"])
            embed = discord.Embed(
                title=f"📊 {data.get('title', 'Daily Recap')}",
                description=data.get("summary", ""),
                color=discord.Color.gold()
            )
            if data.get("highlights"):
                embed.add_field(name="✨ Highlights", value="\n".join(f"• {h}" for h in data["highlights"]), inline=False)
            if data.get("fun_stat"):
                embed.add_field(name="🎲 Fun Stat", value=data["fun_stat"], inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("🔄 Generating fresh recap...")
            result = await generate_daily_summary(interaction.guild)
            if not result:
                await interaction.followup.send("❌ Not enough activity today to generate a recap!")
    
    # ========== SETTINGS ==========
    @bot.tree.command(name="ai_settings", description="[Admin] Configure AI features")
    async def ai_settings_cmd(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        s = get_ai_settings(interaction.guild.id)
        embed = discord.Embed(title="🤖 AI Features Settings", color=discord.Color.blue())
        embed.add_field(name="🎨 Image Gen", value="✅ ON" if s.get("image_gen_enabled", 1) else "❌ OFF", inline=True)
        embed.add_field(name="🌍 Translate", value="✅ ON" if s.get("translate_enabled", 1) else "❌ OFF", inline=True)
        embed.add_field(name="💭 Mood Track", value="✅ ON" if s.get("mood_tracking_enabled", 1) else "❌ OFF", inline=True)
        embed.add_field(name="📊 Daily Recap", value="✅ ON" if s.get("daily_summary_enabled", 1) else "❌ OFF", inline=True)
        embed.add_field(name="📢 Mood Channel", value=f"#{s.get('mood_channel', 'general')}", inline=True)
        embed.add_field(name="📢 Recap Channel", value=f"#{s.get('summary_channel', 'general')}", inline=True)
        embed.set_footer(text="Use /ai_toggle to enable/disable features")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="ai_toggle", description="[Admin] Toggle an AI feature on/off")
    @app_commands.choices(feature=[
        app_commands.Choice(name="🎨 Image Generation", value="image_gen_enabled"),
        app_commands.Choice(name="🌍 Translate Reactions", value="translate_enabled"),
        app_commands.Choice(name="💭 Mood Tracking", value="mood_tracking_enabled"),
        app_commands.Choice(name="📊 Daily Recap", value="daily_summary_enabled"),
    ])
    @app_commands.choices(state=[
        app_commands.Choice(name="✅ ON", value="on"),
        app_commands.Choice(name="❌ OFF", value="off"),
    ])
    async def ai_toggle_cmd(interaction: discord.Interaction, feature: app_commands.Choice[str], state: app_commands.Choice[str]):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        update_ai_setting(interaction.guild.id, feature.value, 1 if state.value == "on" else 0)
        await interaction.response.send_message(f"✅ {feature.name} → **{state.name}**", ephemeral=True)
    
    @bot.tree.command(name="ai_channel", description="[Admin] Set channel for AI reports")
    @app_commands.choices(report_type=[
        app_commands.Choice(name="💭 Mood Reports", value="mood_channel"),
        app_commands.Choice(name="📊 Daily Recaps", value="summary_channel"),
    ])
    async def ai_channel_cmd(interaction: discord.Interaction, report_type: app_commands.Choice[str], channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        update_ai_setting(interaction.guild.id, report_type.value, channel.name)
        await interaction.response.send_message(f"✅ {report_type.name} → {channel.mention}", ephemeral=True)

# ============================================
# EVENT HANDLERS
# ============================================

def register_events():
    @bot.event
    async def on_raw_reaction_add(payload):
        """Handle translation reactions."""
        if payload.user_id == bot.user.id:
            return
        
        emoji = str(payload.emoji)
        if emoji not in FLAG_TO_LANG:
            return
        
        target_lang = FLAG_TO_LANG[emoji]
        
        # Get the guild & check settings
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        settings = get_ai_settings(guild.id)
        if not settings.get("translate_enabled", 1):
            return
        
        # Get the message
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return
        
        if not message.content or len(message.content) < 3:
            return
        
        # Check we haven't already translated this
        for reaction in message.reactions:
            if str(reaction.emoji) == "✅" and reaction.me:
                return  # Already processed
        
        # Translate
        translation = await translate_text(message.content, target_lang)
        if not translation:
            return
        
        user = guild.get_member(payload.user_id)
        embed = discord.Embed(
            title=f"{emoji} Translation to {target_lang}",
            description=translation[:2000],
            color=discord.Color.blue()
        )
        embed.add_field(name="🔤 Original", value=message.content[:500], inline=False)
        embed.set_footer(text=f"Requested by {user.display_name if user else 'someone'}")
        
        try:
            await message.reply(embed=embed, mention_author=False)
            await message.add_reaction("✅")  # Mark as translated
        except Exception as e:
            print(f"Translate send err: {e}")

# ============================================
# BACKGROUND TASKS
# ============================================

def start_tasks():
    @tasks.loop(hours=6)
    async def mood_tracker():
        """Track mood every 6 hours."""
        for guild in bot.guilds:
            try:
                settings = get_ai_settings(guild.id)
                if not settings.get("mood_tracking_enabled", 1):
                    continue
                await do_mood_report(guild)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"Mood tracker err: {e}")
    
    @tasks.loop(hours=24)
    async def daily_recap_task():
        """Generate daily recap at end of day."""
        for guild in bot.guilds:
            try:
                settings = get_ai_settings(guild.id)
                if not settings.get("daily_summary_enabled", 1):
                    continue
                await generate_daily_summary(guild)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"Recap task err: {e}")
    
    mood_tracker.start()
    daily_recap_task.start()

# ============================================
# AUTO-FAQ DETECTION (called from bot.py)
# ============================================

async def check_for_faq_question(message):
    """
    Called from bot.py on_message to auto-detect questions
    that match FAQs.
    """
    if not message.guild or message.author.bot:
        return False
    
    content = message.content.strip()
    
    # Only respond to obvious questions
    if not (content.endswith("?") or content.lower().startswith(("how", "what", "where", "when", "why", "can ", "does ", "is "))):
        return False
    
    if len(content) < 10 or len(content) > 300:
        return False
    
    # Check FAQ
    faqs = get_all_faqs(message.guild.id)
    if not faqs:
        return False
    
    answer = await answer_with_faq(content, str(message.guild.id), message.guild.name)
    if answer:
        embed = discord.Embed(
            description=f"💡 {answer}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="📚 From server FAQ • Use /faq_list to see all")
        try:
            await message.reply(embed=embed, mention_author=False)
            return True
        except:
            pass
    return False
