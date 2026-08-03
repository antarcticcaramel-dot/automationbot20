# volaris_guard.py
# ================================
# Volaris Guard AI Moderation Integration
# Uses Volaris Guard API for text + image moderation
# Auto-hooks into bot.py alongside existing moderation
# ================================

import aiohttp
import asyncio
import json
import os
import re
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from discord import app_commands

# ============ CONFIG ============
VOLARIS_API_KEY = os.getenv("VOLARIS_API_KEY", "")
VOLARIS_BASE_URL = os.getenv("VOLARIS_BASE_URL", "https://volarishq.uk/guard/api/v1")

_bot_ref = None
_is_setup = False

# Cache to save credits
_verdict_cache: dict[str, tuple] = {}
CACHE_TTL = 3600

# Rate limiting to avoid hitting per-IP limits
_last_call = [0.0]
CALL_DELAY = 0.5  # 500ms between calls


# ============ DB HELPERS ============
def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column():
    try:
        conn = _get_db()
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE guild_settings ADD COLUMN volaris_enabled INTEGER DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.close()
    except: pass


def _get_setting(guild_id):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT volaris_enabled FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()
        if row is None:
            return True
        return bool(row["volaris_enabled"])
    except sqlite3.OperationalError:
        _ensure_column()
        return True
    except:
        return True


def _save_setting(guild_id, value):
    try:
        _ensure_column()
        conn = _get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
        c.execute("UPDATE guild_settings SET volaris_enabled=? WHERE guild_id=?", (int(value), str(guild_id)))
        conn.commit()
        conn.close()
    except: pass


def _is_trusted(uid, gid):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM trusted_users WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
        r = c.fetchone()
        conn.close()
        return r is not None
    except:
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
    except:
        return 0


def _log_action(uid, gid, action, reason):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO mod_actions (user_id,guild_id,action,reason,mod_id,timestamp) VALUES (?,?,?,?,?,?)",
            (str(uid), str(gid), action, reason[:500],
             str(_bot_ref.user.id) if _bot_ref and _bot_ref.user else "bot",
             datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except: pass


# ============ RATE LIMIT ============
async def _rate_limit():
    now = time.time()
    elapsed = now - _last_call[0]
    if elapsed < CALL_DELAY:
        await asyncio.sleep(CALL_DELAY - elapsed)
    _last_call[0] = time.time()


# ============ VOLARIS API CALLS ============
async def moderate_text(text: str) -> dict | None:
    """Moderate text content via Volaris Guard."""
    if not VOLARIS_API_KEY or not text:
        return None
    
    # Check cache
    import hashlib
    cache_key = f"text:{hashlib.md5(text.encode()).hexdigest()}"
    if cache_key in _verdict_cache:
        cached, ts = _verdict_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached
    
    await _rate_limit()
    
    # Try common endpoint paths
    endpoints = [
        f"{VOLARIS_BASE_URL}/moderate/text",
        f"{VOLARIS_BASE_URL}/moderate",
        f"{VOLARIS_BASE_URL}/text",
        f"{VOLARIS_BASE_URL}/check/text",
    ]
    
    # Try both auth header styles
    header_variants = [
        {"Authorization": f"Bearer {VOLARIS_API_KEY}", "Content-Type": "application/json"},
        {"X-API-Key": VOLARIS_API_KEY, "Content-Type": "application/json"},
        {"Authorization": VOLARIS_API_KEY, "Content-Type": "application/json"},
    ]
    
    for endpoint in endpoints:
        for headers in header_variants:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint,
                        headers=headers,
                        json={"text": text[:50000], "content": text[:50000]},  # try both keys
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            _verdict_cache[cache_key] = (data, time.time())
                            if len(_verdict_cache) > 1000:
                                oldest = min(_verdict_cache.keys(), key=lambda k: _verdict_cache[k][1])
                                del _verdict_cache[oldest]
                            return data
                        elif resp.status == 401 or resp.status == 403:
                            # Auth failed, try next header
                            continue
                        elif resp.status == 404:
                            # Wrong endpoint, try next
                            break
                        elif resp.status == 429:
                            # Rate limited
                            await asyncio.sleep(2)
            except Exception as e:
                print(f"[volaris] text err {endpoint}: {e}")
                continue
    
    return None


async def moderate_image(image_url: str) -> dict | None:
    """Moderate image via Volaris Guard."""
    if not VOLARIS_API_KEY or not image_url:
        return None
    
    import hashlib
    cache_key = f"img:{hashlib.md5(image_url.encode()).hexdigest()}"
    if cache_key in _verdict_cache:
        cached, ts = _verdict_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached
    
    await _rate_limit()
    
    endpoints = [
        f"{VOLARIS_BASE_URL}/moderate/image",
        f"{VOLARIS_BASE_URL}/image",
        f"{VOLARIS_BASE_URL}/check/image",
    ]
    
    header_variants = [
        {"Authorization": f"Bearer {VOLARIS_API_KEY}", "Content-Type": "application/json"},
        {"X-API-Key": VOLARIS_API_KEY, "Content-Type": "application/json"},
    ]
    
    for endpoint in endpoints:
        for headers in header_variants:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint,
                        headers=headers,
                        json={"image_url": image_url, "url": image_url, "image": image_url},
                        timeout=aiohttp.ClientTimeout(total=25)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            _verdict_cache[cache_key] = (data, time.time())
                            return data
                        elif resp.status in [401, 403]:
                            continue
                        elif resp.status == 404:
                            break
                        elif resp.status == 429:
                            await asyncio.sleep(2)
            except Exception as e:
                print(f"[volaris] image err {endpoint}: {e}")
                continue
    
    return None


# ============ PARSE VERDICT ============
def _parse_verdict(data: dict) -> dict:
    """Normalize Volaris response into consistent format."""
    if not data:
        return {"flagged": False}
    
    # Try many possible response formats
    flagged = (
        data.get("flagged") or
        data.get("violation") or
        data.get("is_flagged") or
        not data.get("safe", True) or
        data.get("verdict") == "flagged" or
        data.get("verdict") == "unsafe" or
        data.get("status") == "flagged"
    )
    
    categories = (
        data.get("categories") or
        data.get("labels") or
        data.get("tags") or
        data.get("violations") or
        []
    )
    if isinstance(categories, dict):
        # Convert {"hate": 0.9, "spam": 0.1} to ["hate"]
        categories = [k for k, v in categories.items() if v > 0.5]
    
    severity = (
        data.get("severity") or
        data.get("level") or
        ("critical" if flagged and any(c in str(categories).lower() for c in ["csam", "child", "extreme"]) else
         "high" if flagged else "none")
    )
    
    confidence = (
        data.get("confidence") or
        data.get("score") or
        data.get("probability") or
        (0.8 if flagged else 0.0)
    )
    
    reason = (
        data.get("reason") or
        data.get("explanation") or
        data.get("message") or
        (", ".join(str(c) for c in categories) if categories else "Flagged by Volaris")
    )
    
    return {
        "flagged": bool(flagged),
        "categories": categories if isinstance(categories, list) else [str(categories)],
        "severity": str(severity).lower(),
        "confidence": float(confidence) if confidence else 0.0,
        "reason": str(reason)[:300],
        "raw": data
    }


# ============ MODERATION HANDLER ============
async def _handle_text_moderation(message):
    """Check message text via Volaris."""
    if not message.guild or message.author.bot:
        return False
    
    if not _get_setting(message.guild.id):
        return False
    
    if _is_trusted(message.author.id, message.guild.id):
        return False
    
    content = message.content
    if not content or len(content.strip()) < 5:
        return False
    
    # Skip if only URLs / mentions / emojis
    stripped = re.sub(r'<[@#!:&][^>]+>|https?://\S+|:\w+:', '', content).strip()
    if len(stripped) < 5:
        return False
    
    result = await moderate_text(content)
    if not result:
        return False
    
    verdict = _parse_verdict(result)
    
    if not verdict.get("flagged"):
        return False
    
    if verdict.get("confidence", 0) < 0.7:
        return False
    
    await _take_action(message, verdict, "text")
    return True


async def _handle_image_moderation(message):
    """Check images via Volaris."""
    if not message.guild or message.author.bot:
        return False
    
    if not _get_setting(message.guild.id):
        return False
    
    if _is_trusted(message.author.id, message.guild.id):
        return False
    
    # Get image URLs
    urls = []
    for att in message.attachments:
        try:
            if att.content_type and att.content_type.startswith("image/"):
                urls.append(att.url)
            elif att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                urls.append(att.url)
        except: pass
    
    for embed in message.embeds:
        try:
            if embed.image and embed.image.url:
                urls.append(embed.image.url)
        except: pass
    
    if not urls:
        return False
    
    # Check each image (max 3 to save credits)
    for url in urls[:3]:
        result = await moderate_image(url)
        if not result:
            continue
        
        verdict = _parse_verdict(result)
        if verdict.get("flagged") and verdict.get("confidence", 0) >= 0.7:
            await _take_action(message, verdict, "image")
            return True
    
    return False


async def _take_action(message, verdict: dict, source: str):
    """Delete message and warn based on Volaris verdict."""
    author = message.author
    guild = message.guild
    
    severity = verdict.get("severity", "medium").lower()
    reason = verdict.get("reason", "Flagged by Volaris")
    categories = verdict.get("categories", [])
    confidence = verdict.get("confidence", 0)
    
    cat_str = ", ".join(str(c) for c in categories) if categories else "content"
    full_reason = f"Volaris ({source}): {cat_str} - {reason}"
    
    # Delete
    try:
        await message.delete()
    except: pass
    
    # Ban for critical
    if severity in ["critical", "ban", "extreme", "severe"] or any(c in str(cat_str).lower() for c in ["csam", "child"]):
        try:
            can_punish = (
                isinstance(author, discord.Member) and
                author.id != guild.owner_id and
                author.top_role < guild.me.top_role
            )
            if can_punish:
                await guild.ban(author, reason=full_reason[:500], delete_message_days=1)
                _log_action(author.id, guild.id, "VOLARIS BAN", full_reason)
                await _alert_mods(guild, discord.Embed(
                    title="🚨 Volaris Auto-Ban",
                    description=f"**{author}** — {reason}",
                    color=discord.Color.dark_red()
                ).add_field(name="Categories", value=cat_str[:1000], inline=False)
                 .add_field(name="Source", value=source, inline=True)
                 .add_field(name="Confidence", value=f"{confidence:.0%}", inline=True))
                return
        except: pass
    
    # Warn + delete
    wc = _add_warning(author.id, guild.id, full_reason, severity)
    _log_action(author.id, guild.id, f"VOLARIS DELETE ({source})", full_reason)
    
    try:
        await message.channel.send(
            f"{author.mention} That was flagged: **{reason}** | Warning #{wc}",
            delete_after=6
        )
    except: pass
    
    # Timeout on high severity
    if severity in ["high", "critical"]:
        try:
            if isinstance(author, discord.Member) and author.id != guild.owner_id:
                if author.top_role < guild.me.top_role:
                    await author.timeout(
                        datetime.now() + timedelta(minutes=30 if severity == "high" else 60),
                        reason=full_reason[:500]
                    )
        except: pass
    
    # Log to mod channel
    embed = discord.Embed(
        title=f"🛡️ Volaris Guard - {source.upper()} Flagged",
        color=discord.Color.red() if severity in ["high", "critical"] else discord.Color.orange()
    )
    embed.add_field(name="User", value=author.mention, inline=True)
    embed.add_field(name="Severity", value=severity, inline=True)
    embed.add_field(name="Warning #", value=str(wc), inline=True)
    embed.add_field(name="Categories", value=cat_str[:1000], inline=False)
    embed.add_field(name="Reason", value=reason[:1000], inline=False)
    embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
    if source == "text":
        embed.add_field(name="Message", value=f"||{message.content[:500]}||", inline=False)
    await _alert_mods(guild, embed)


async def _alert_mods(guild, embed):
    for ch_name in ["sentinel-logs", "mod-logs", "logs"]:
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if ch:
            try:
                await ch.send(embed=embed)
                return
            except: pass


# ============ COMMANDS ============
def _register_commands(bot):
    
    @bot.tree.command(name="volaris", description="[Admin] Toggle Volaris Guard moderation")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def volaris_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        _save_setting(i.guild.id, 1 if state.value == "on" else 0)
        await i.response.send_message(f"🛡️ Volaris Guard **{state.name}**", ephemeral=True)
    
    
    @bot.tree.command(name="volaris_test", description="[Admin] Test Volaris Guard with a message")
    @app_commands.describe(message="Text to check")
    async def volaris_test_cmd(i: discord.Interaction, message: str):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        if not VOLARIS_API_KEY:
            await i.followup.send("❌ VOLARIS_API_KEY not set!", ephemeral=True)
            return
        
        result = await moderate_text(message)
        
        if not result:
            await i.followup.send(
                "❌ Volaris API didn't respond. Check:\n"
                "- Your VOLARIS_API_KEY is set correctly\n"
                "- The VOLARIS_BASE_URL is correct\n"
                "- Check console for error details",
                ephemeral=True
            )
            return
        
        verdict = _parse_verdict(result)
        
        embed = discord.Embed(
            title="🛡️ Volaris Guard Test",
            color=discord.Color.red() if verdict["flagged"] else discord.Color.green()
        )
        embed.add_field(name="Message", value=f"```{message[:500]}```", inline=False)
        embed.add_field(name="Flagged?", value="YES ❌" if verdict["flagged"] else "NO ✅", inline=True)
        embed.add_field(name="Severity", value=verdict.get("severity", "?"), inline=True)
        embed.add_field(name="Confidence", value=f"{verdict.get('confidence', 0):.0%}", inline=True)
        embed.add_field(name="Categories", value=", ".join(str(c) for c in verdict.get("categories", [])) or "None", inline=False)
        embed.add_field(name="Reason", value=verdict.get("reason", "None")[:1000], inline=False)
        embed.add_field(name="Raw Response", value=f"```json\n{json.dumps(verdict.get('raw', {}), indent=2)[:800]}\n```", inline=False)
        
        await i.followup.send(embed=embed, ephemeral=True)


# ============ LISTENER ============
def _register_listener(bot):
    @bot.listen("on_message")
    async def _volaris_listener(message):
        try:
            if message.author.bot: return
            if not message.guild: return
            
            # Try text moderation
            if message.content and len(message.content.strip()) > 5:
                if await _handle_text_moderation(message):
                    return
            
            # Try image moderation
            if message.attachments or any(e.image for e in message.embeds):
                await _handle_image_moderation(message)
        except Exception as e:
            print(f"[volaris] listener err: {e}")


# ============ SETUP ============
def setup(bot):
    global _bot_ref, _is_setup
    if _is_setup: return
    _bot_ref = bot
    _is_setup = True
    
    _ensure_column()
    _register_commands(bot)
    _register_listener(bot)
    
    if VOLARIS_API_KEY:
        print(f"[volaris] ✅ Loaded with API key. Base URL: {VOLARIS_BASE_URL}")
    else:
        print("[volaris] ⚠️ VOLARIS_API_KEY not set! Set it in env vars.")


# ============ AUTO HOOK ============
def _auto_hook():
    import sys
    for module_name, module in list(sys.modules.items()):
        if module is None: continue
        if hasattr(module, "bot") and isinstance(getattr(module, "bot", None), commands.Bot):
            bot_obj = module.bot
            setup(bot_obj)
            return True
    return False

def _delayed_hook():
    for attempt in range(30):
        time.sleep(1)
        try:
            if _auto_hook():
                return
        except: pass
    print("[volaris] ⚠️ Could not auto-hook. Add `import volaris_guard` to bot.py.")

threading.Thread(target=_delayed_hook, daemon=True).start()
