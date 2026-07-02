# image_moderation.py
# ================================
# FULLY SELF-CONTAINED AI Image Moderation
# Just drop this file next to bot.py - it auto-hooks itself in!
# No changes needed to bot.py
# ================================

import aiohttp
import asyncio
import json
import os
import re
import hashlib
import time
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from discord import app_commands

# ============ CONFIG ============
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")

_image_cache: dict[str, tuple] = {}
CACHE_TTL = 3600
_user_image_tracker = defaultdict(list)

# ============ VISION AI ============

async def analyze_with_groq_vision(image_url: str, prompt: str) -> dict | None:
    if not GROQ_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    models = [
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
    ]
    for model in models:
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            "temperature": 0.1,
            "max_tokens": 500,
            "response_format": {"type": "json_object"}
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
                        result_text = data["choices"][0]["message"]["content"]
                        try:
                            return json.loads(result_text)
                        except json.JSONDecodeError:
                            match = re.search(r'\{.*\}', result_text, re.DOTALL)
                            if match:
                                return json.loads(match.group())
                    elif resp.status == 429:
                        await asyncio.sleep(2)
        except Exception as e:
            print(f"Groq vision {model} err: {e}")
            continue
    return None


async def analyze_with_openrouter_vision(image_url: str, prompt: str) -> dict | None:
    if not OPENROUTER_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    models = [
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "google/gemini-flash-1.5:free",
    ]
    for model in models:
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            "max_tokens": 500,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result_text = data["choices"][0]["message"]["content"]
                        match = re.search(r'\{.*\}', result_text, re.DOTALL)
                        if match:
                            try:
                                return json.loads(match.group())
                            except: pass
        except Exception as e:
            print(f"OpenRouter vision {model} err: {e}")
            continue
    return None


MODERATION_PROMPT = """You are an expert Discord image moderator. Analyze this image for ANY policy violations.

DETECT AND FLAG:
1. **NSFW/Sexual**: nudity, sexual content, suggestive poses, sex acts, adult content
2. **CSAM/Underage**: any sexualized content involving minors (INSTANT BAN)
3. **Gore/Violence**: blood, injuries, dead bodies, torture, extreme violence, gore
4. **Scams**: fake Discord Nitro, crypto scams, phishing sites, fake giveaways, fake login pages
5. **Phishing**: fake login pages (Discord/Steam/PayPal), suspicious QR codes, credential stealers
6. **Weapons**: guns pointed at camera, glorified weapons, threats with weapons
7. **Drugs**: illegal drug use, drug paraphernalia, drug sales
8. **Hate Symbols**: swastikas, KKK, SS bolts, white power symbols, other hate imagery
9. **Self-Harm**: cuts, suicide references, self-injury
10. **Doxxing**: screenshots of personal info (addresses, IDs, credit cards, SSNs)
11. **Malicious Links**: shortened URLs in image, IP grabber links, suspicious domains
12. **Fake Bot/Discord**: fake Discord staff, fake mod messages, impersonation
13. **Shock Content**: disturbing imagery meant to disgust
14. **Illegal Content**: piracy, stolen data, illegal marketplace screenshots
15. **Spam/Ads**: server invites in images, self-promotion ads

BE STRICT but SMART:
- Memes with cartoon violence = OK (unless graphic)
- Anime/art nudity in SFW channel = flag it
- Movie/game screenshots with weapons = usually OK
- Educational content (medical, history) = context matters
- Text-only images = read the text for scams/hate

RETURN JSON ONLY:
{
  "safe": true/false,
  "categories": ["nsfw", "gore", "scam", "phishing", "weapons", "drugs", "hate", "self_harm", "doxxing", "malicious_link", "impersonation", "shock", "illegal", "spam", "csam"],
  "severity": "none|low|medium|high|critical|ban",
  "confidence": 0.0-1.0,
  "action": "ignore|flag|delete|delete_warn|delete_ban",
  "reason": "specific short explanation",
  "detected_text": "any text visible in image",
  "explanation": "what you see"
}

Severity guide:
- "ban" = CSAM, credible threats with weapons, doxxing personal info
- "critical" = clear NSFW, phishing, scams, gore
- "high" = suggestive content, hate symbols, mild gore, weapons displayed
- "medium" = spam, ads, mildly inappropriate
- "low" = borderline cases
- "none" = safe

If unsure, err on the side of safety but don't over-flag."""


async def analyze_image(image_url: str, channel_is_nsfw: bool = False) -> dict:
    cache_key = hashlib.md5(image_url.encode()).hexdigest()
    if cache_key in _image_cache:
        cached, ts = _image_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached
    
    prompt = MODERATION_PROMPT
    if channel_is_nsfw:
        prompt += "\n\nNOTE: This is an NSFW channel - adult content is allowed here. Only flag CSAM, gore, scams, doxxing, and other non-NSFW violations."
    
    result = await analyze_with_groq_vision(image_url, prompt)
    if not result:
        result = await analyze_with_openrouter_vision(image_url, prompt)
    
    if not result:
        return {
            "safe": True, "categories": [], "severity": "none",
            "confidence": 0.0, "action": "ignore",
            "reason": "AI unavailable", "explanation": "Could not analyze"
        }
    
    normalized = {
        "safe": result.get("safe", True),
        "categories": result.get("categories", []),
        "severity": result.get("severity", "none").lower(),
        "confidence": float(result.get("confidence", 0.0)),
        "action": result.get("action", "ignore").lower(),
        "reason": result.get("reason", ""),
        "detected_text": result.get("detected_text", ""),
        "explanation": result.get("explanation", "")
    }
    
    _image_cache[cache_key] = (normalized, time.time())
    if len(_image_cache) > 500:
        oldest = min(_image_cache.keys(), key=lambda k: _image_cache[k][1])
        del _image_cache[oldest]
    
    return normalized


def extract_image_urls(message) -> list[str]:
    urls = []
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            urls.append(attachment.url)
        elif attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')):
            urls.append(attachment.url)
    for embed in message.embeds:
        if embed.image and embed.image.url:
            urls.append(embed.image.url)
        if embed.thumbnail and embed.thumbnail.url:
            urls.append(embed.thumbnail.url)
    url_pattern = r'https?://\S+\.(?:png|jpg|jpeg|gif|webp|bmp)(?:\?\S*)?'
    for match in re.finditer(url_pattern, message.content, re.IGNORECASE):
        urls.append(match.group())
    return list(set(urls))


def check_image_spam(user_id: int, guild_id: int, num_images: int = 1) -> bool:
    key = f"{guild_id}:{user_id}"
    now = time.time()
    _user_image_tracker[key] = [t for t in _user_image_tracker[key] if now - t < 60]
    _user_image_tracker[key].extend([now] * num_images)
    return len(_user_image_tracker[key]) >= 10


# ============ AUTO-HOOK INTO BOT ============

_bot_ref = None
_is_setup = False

def _get_db():
    """Get database connection."""
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _get_setting(guild_id):
    """Check if image mod is enabled for guild."""
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT image_moderation FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()
        if row is None:
            return True  # Default ON
        return bool(row["image_moderation"])
    except sqlite3.OperationalError:
        # Column doesn't exist yet - add it
        try:
            conn = _get_db()
            c = conn.cursor()
            c.execute("ALTER TABLE guild_settings ADD COLUMN image_moderation INTEGER DEFAULT 1")
            conn.commit()
            conn.close()
        except: pass
        return True


def _set_setting(guild_id, value):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
        c.execute("UPDATE guild_settings SET image_moderation=? WHERE guild_id=?", (value, str(guild_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Set setting err: {e}")


def _is_trusted(user_id, guild_id):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM trusted_users WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id)))
        result = c.fetchone()
        conn.close()
        return result is not None
    except: return False


def _has_mod(member):
    if member.guild_permissions.administrator: return True
    if member.guild_permissions.ban_members or member.guild_permissions.manage_messages:
        return True
    for role in member.roles:
        if "mod" in role.name.lower() or "admin" in role.name.lower():
            return True
    return False


def _add_warning(uid, gid, reason, severity):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO warnings (user_id,guild_id,reason,severity,ai_confidence,context,timestamp) VALUES (?,?,?,?,?,?,?)",
            (str(uid), str(gid), reason, severity, 1.0, "", datetime.now().isoformat())
        )
        conn.commit()
        c.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"Warning add err: {e}")
        return 0


def _log_action(uid, gid, action, reason):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO mod_actions (user_id,guild_id,action,reason,mod_id,timestamp) VALUES (?,?,?,?,?,?)",
            (str(uid), str(gid), action, reason, str(_bot_ref.user.id) if _bot_ref else "bot", datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except: pass


async def _alert_mods(guild, embed):
    """Send alert to log channel."""
    for ch_name in ["sentinel-logs", "mod-logs", "logs", "audit-log"]:
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if ch:
            try:
                await ch.send(embed=embed)
                return
            except: pass


async def _notify_owner(alert_type, message_text, guild=None, urgent=False):
    """Try to notify bot owner."""
    if not _bot_ref: return
    try:
        owner_id = int(os.getenv("OWNER_ID", "1268285209867059372"))
        owner = await _bot_ref.fetch_user(owner_id)
        if owner:
            embed = discord.Embed(
                title=f"{alert_type}{' [URGENT]' if urgent else ''}",
                description=message_text,
                color=discord.Color.red() if urgent else discord.Color.orange(),
                timestamp=datetime.now()
            )
            if guild:
                embed.add_field(name="Server", value=guild.name)
            await owner.send(embed=embed)
    except: pass


async def _moderate_images(message):
    """Main image moderation handler."""
    if not message.guild or message.author.bot:
        return False
    
    image_urls = extract_image_urls(message)
    if not image_urls:
        return False
    
    author = message.author
    guild = message.guild
    
    if not _get_setting(guild.id):
        return False
    
    if _is_trusted(author.id, guild.id):
        return False
    if _has_mod(author):
        return False
    
    # Image spam check
    if check_image_spam(author.id, guild.id, len(image_urls)):
        try: await message.delete()
        except: pass
        try:
            await author.timeout(
                datetime.now() + timedelta(minutes=10),
                reason="Image spam"
            )
        except: pass
        try:
            await message.channel.send(
                f"{author.mention} slow down with the images!",
                delete_after=10
            )
        except: pass
        return True
    
    channel_is_nsfw = message.channel.is_nsfw() if hasattr(message.channel, 'is_nsfw') else False
    
    worst_result = None
    worst_score = 0
    severity_scores = {
        "none": 0, "low": 1, "medium": 2,
        "high": 3, "critical": 4, "ban": 5
    }
    
    for url in image_urls[:5]:
        try:
            result = await asyncio.wait_for(
                analyze_image(url, channel_is_nsfw),
                timeout=25.0
            )
            score = severity_scores.get(result.get("severity", "none"), 0)
            if score > worst_score:
                worst_score = score
                worst_result = result
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"Image analysis err: {e}")
            continue
    
    if not worst_result or worst_result.get("safe", True):
        return False
    
    severity = worst_result.get("severity", "none")
    confidence = worst_result.get("confidence", 0.0)
    reason = worst_result.get("reason", "Inappropriate image")
    categories = worst_result.get("categories", [])
    
    if confidence < 0.6 and severity not in ["critical", "ban"]:
        return False
    
    cat_str = ", ".join(categories) if categories else "content"
    full_reason = f"Image: {cat_str} - {reason}"
    
    if severity == "ban" or "csam" in categories:
        try: await message.delete()
        except: pass
        try:
            await guild.ban(author, reason=f"CRITICAL: {full_reason}", delete_message_days=1)
        except: pass
        _log_action(author.id, guild.id, "AUTO-BAN (IMAGE)", full_reason)
        
        embed = discord.Embed(
            title="🚨 IMAGE BAN",
            description=f"Auto-banned **{author}** for image violation",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="Categories", value=cat_str, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}")
        await _alert_mods(guild, embed)
        await _notify_owner("CRITICAL", f"Image auto-ban in **{guild.name}**: {author}", guild=guild, urgent=True)
        return True
    
    elif severity in ["critical", "high"]:
        try: await message.delete()
        except: pass
        wc = _add_warning(author.id, guild.id, full_reason, severity)
        _log_action(author.id, guild.id, "AUTO-DELETE (IMAGE)", full_reason)
        
        try:
            await message.channel.send(
                f"{author.mention} That image was removed: **{reason}** | Warning #{wc}",
                delete_after=15
            )
        except: pass
        
        mute_dur = 60 if severity == "critical" else 30
        try:
            await author.timeout(
                datetime.now() + timedelta(minutes=mute_dur),
                reason=full_reason
            )
        except: pass
        
        embed = discord.Embed(
            title=f"🖼️ Image Removed - {severity.upper()}",
            color=discord.Color.red() if severity == "critical" else discord.Color.orange()
        )
        embed.add_field(name="User", value=author.mention, inline=True)
        embed.add_field(name="Warning #", value=str(wc), inline=True)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
        embed.add_field(name="Categories", value=cat_str, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if worst_result.get("detected_text"):
            embed.add_field(name="Text in image", value=worst_result["detected_text"][:200], inline=False)
        await _alert_mods(guild, embed)
        return True
    
    elif severity == "medium":
        try: await message.delete()
        except: pass
        wc = _add_warning(author.id, guild.id, full_reason, severity)
        _log_action(author.id, guild.id, "DELETED (IMAGE)", full_reason)
        try:
            await message.channel.send(
                f"{author.mention} Please don't post that here: **{reason}**",
                delete_after=12
            )
        except: pass
        return True
    
    elif severity == "low":
        try: await message.delete()
        except: pass
        try:
            await message.channel.send(
                f"{author.mention} That image isn't appropriate here.",
                delete_after=8
            )
        except: pass
        return True
    
    return False


# ============ AUTO-SETUP ============

def setup(bot):
    """Called automatically by discord.py when using bot.load_extension()
    OR manually if imported. Sets up event listener and slash command."""
    global _bot_ref, _is_setup
    if _is_setup:
        return
    _bot_ref = bot
    _is_setup = True
    
    # Ensure column exists
    try:
        conn = _get_db()
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE guild_settings ADD COLUMN image_moderation INTEGER DEFAULT 1")
            conn.commit()
            print("[image_mod] Added image_moderation column to DB")
        except sqlite3.OperationalError:
            pass  # Already exists
        conn.close()
    except Exception as e:
        print(f"[image_mod] DB setup err: {e}")
    
    # Hook into on_message via listener (doesn't replace existing on_message!)
    @bot.listen('on_message')
    async def _image_mod_listener(message):
        try:
            if message.author.bot:
                return
            if not message.guild:
                return
            if not (message.attachments or any(e.image for e in message.embeds)):
                return
            await _moderate_images(message)
        except Exception as e:
            print(f"[image_mod] Listener err: {e}")
    
    # Register slash command
    @bot.tree.command(name="image_mod", description="[Admin] Toggle AI image moderation")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def image_mod_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        _set_setting(i.guild.id, 1 if state.value == "on" else 0)
        await i.response.send_message(
            f"🖼️ Image moderation **{state.name}**",
            ephemeral=True
        )
    
    # Cache cleanup task
    @tasks.loop(hours=1)
    async def _cache_cleanup():
        now = time.time()
        keys = [k for k, (_, ts) in _image_cache.items() if now - ts > CACHE_TTL]
        for k in keys:
            del _image_cache[k]
        for key in list(_user_image_tracker.keys()):
            _user_image_tracker[key] = [t for t in _user_image_tracker[key] if now - t < 60]
            if not _user_image_tracker[key]:
                del _user_image_tracker[key]
    
    if not _cache_cleanup.is_running():
        _cache_cleanup.start()
    
    print("[image_mod] ✅ Auto-hooked into bot! Image moderation is ACTIVE")


# ============ AUTO-INITIALIZE ON IMPORT ============
# This runs when bot.py does `import image_moderation` (if it does)
# Since your bot.py doesn't import this, we use a different approach below

def _auto_hook():
    """Try to auto-detect and hook into a running bot."""
    import sys
    # Check if bot.py is loaded and has a 'bot' variable
    for module_name, module in list(sys.modules.items()):
        if module is None: continue
        if hasattr(module, 'bot') and isinstance(getattr(module, 'bot', None), commands.Bot):
            bot_obj = module.bot
            if bot_obj.is_ready() or not _is_setup:
                setup(bot_obj)
                return True
    return False


# Try auto-hook after a delay (gives bot.py time to load)
import threading
def _delayed_hook():
    import time as _time
    for attempt in range(30):  # Try for 30 seconds
        _time.sleep(1)
        try:
            if _auto_hook():
                return
        except: pass
    print("[image_mod] ⚠️ Could not auto-hook. Add 'import image_moderation' to bot.py")

threading.Thread(target=_delayed_hook, daemon=True).start()
