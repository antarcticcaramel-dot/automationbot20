# volaris_guard.py
# Simple Volaris Guard integration for SentinelMod

import aiohttp
import asyncio
import json
import os
import time
import sqlite3
import hashlib
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands

# ============ CONFIG ============
VOLARIS_API_KEY = os.getenv("VOLARIS_API_KEY", "")
VOLARIS_URL = "https://api.volarishq.uk/guard/moderate"

_verdict_cache = {}
CACHE_TTL = 3600
_last_call = [0.0]


# ============ DB ============
def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_col():
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


def _get_enabled(guild_id):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT volaris_enabled FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()
        if row is None:
            return True
        return bool(row["volaris_enabled"])
    except:
        _ensure_col()
        return True


def _set_enabled(guild_id, value):
    try:
        _ensure_col()
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


# ============ DEFAULT POLICY ============
DEFAULT_POLICY = """# Discord Community Rules

## VIOLATES
- Slurs (racial, homophobic, transphobic, ableist)
- Sexual content in non-NSFW channels
- CSAM (sexualization of minors)
- Threats of violence or death threats
- Doxxing (sharing personal info)
- Scams (crypto scams, fake giveaways, phishing)
- Fake nitro links, malicious URLs
- Hate speech
- Predatory behavior
- Self-harm encouragement

## ALLOWED
- Normal chat, memes, gaming talk
- Strong opinions (not attacking anyone)
- Mild profanity

Return "flagged" for clear violations.
Return "review" for borderline cases.
Return "safe" otherwise."""


# ============ API CALL ============
async def call_volaris(text=None, image_url=None):
    """Call Volaris Guard API."""
    if not VOLARIS_API_KEY:
        print("[volaris] No API key set")
        return None
    if not text and not image_url:
        return None
    
    # Cache
    cache_key = hashlib.md5(f"{text or ''}|{image_url or ''}".encode()).hexdigest()
    if cache_key in _verdict_cache:
        cached, ts = _verdict_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached
    
    # Rate limit
    elapsed = time.time() - _last_call[0]
    if elapsed < 0.8:
        await asyncio.sleep(0.8 - elapsed)
    _last_call[0] = time.time()
    
    # Build request
    body = {"policy": DEFAULT_POLICY}
    if text:
        body["text"] = text[:50000]
    if image_url:
        body["image_url"] = image_url
    
    headers = {
        "x-api-key": VOLARIS_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                VOLARIS_URL,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _verdict_cache[cache_key] = (data, time.time())
                    return data
                else:
                    err = await resp.text()
                    print(f"[volaris] HTTP {resp.status}: {err[:300]}")
                    return None
    except Exception as e:
        print(f"[volaris] Request error: {e}")
        return None


# ============ PARSE ============
def parse_verdict(data):
    """Parse Volaris response."""
    if not data:
        return None
    
    verdict = str(data.get("verdict", "safe")).lower()
    score = float(data.get("score", 0.0))
    categories_raw = data.get("categories", {})
    reasoning = data.get("reasoning", "")
    
    flagged = verdict == "flagged"
    
    flagged_cats = []
    if isinstance(categories_raw, dict):
        for name, info in categories_raw.items():
            if isinstance(info, dict) and info.get("flagged"):
                flagged_cats.append(name)
    
    severity = "none"
    if flagged:
        cat_str = " ".join(flagged_cats).lower()
        if "csam" in cat_str or "child" in cat_str:
            severity = "critical"
        elif any(c in cat_str for c in ["nsfw", "hate", "violence", "doxxing", "phishing", "scam", "self_harm"]):
            severity = "high"
        elif score > 0.75:
            severity = "high"
        elif score > 0.5:
            severity = "medium"
        else:
            severity = "low"
    
    return {
        "flagged": flagged,
        "score": score,
        "categories": flagged_cats,
        "severity": severity,
        "reasoning": reasoning,
        "credits": data.get("credits_used", 0)
    }


# ============ ACTION ============
async def take_action(message, verdict, source):
    """Delete + warn based on verdict."""
    author = message.author
    guild = message.guild
    
    severity = verdict["severity"]
    cats = verdict["categories"]
    reasoning = verdict["reasoning"] or "Policy violation"
    cat_str = ", ".join(cats) if cats else "content"
    full_reason = f"Volaris ({source}): {cat_str} - {reasoning}"
    
    # Delete
    try:
        await message.delete()
    except: pass
    
    # Can we punish?
    can_punish = False
    try:
        if isinstance(author, discord.Member):
            if author.id != guild.owner_id and author.top_role < guild.me.top_role:
                can_punish = True
    except: pass
    
    # Ban for critical
    if severity == "critical" and can_punish:
        try:
            await guild.ban(author, reason=full_reason[:500], delete_message_days=1)
            await log_to_channel(guild, make_embed(author, verdict, source, "AUTO-BAN", discord.Color.dark_red()))
            return
        except: pass
    
    # Warn + timeout
    wc = _add_warning(author.id, guild.id, full_reason, severity)
    
    try:
        await message.channel.send(
            f"{author.mention} That was flagged: **{reasoning[:120]}** | Warning #{wc}",
            delete_after=6
        )
    except: pass
    
    if can_punish and severity in ["high", "critical"]:
        try:
            dur = 60 if severity == "critical" else 30
            await author.timeout(datetime.now() + timedelta(minutes=dur), reason=full_reason[:500])
        except: pass
    
    color = {
        "critical": discord.Color.dark_red(),
        "high": discord.Color.red(),
        "medium": discord.Color.orange(),
        "low": discord.Color.yellow()
    }.get(severity, discord.Color.orange())
    
    await log_to_channel(guild, make_embed(author, verdict, source, "Flagged", color, wc, message.content))


def make_embed(author, verdict, source, action, color, warning_num=None, msg_content=""):
    embed = discord.Embed(
        title=f"🛡️ Volaris - {action}",
        color=color,
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=getattr(author, "mention", str(author)), inline=True)
    embed.add_field(name="Source", value=source, inline=True)
    embed.add_field(name="Severity", value=verdict["severity"], inline=True)
    if warning_num:
        embed.add_field(name="Warning #", value=str(warning_num), inline=True)
    embed.add_field(name="Score", value=f"{verdict['score']:.0%}", inline=True)
    embed.add_field(name="Credits", value=str(verdict.get("credits", "?")), inline=True)
    embed.add_field(name="Categories", value=", ".join(verdict["categories"]) or "None", inline=False)
    embed.add_field(name="Reason", value=verdict["reasoning"][:1000] or "None", inline=False)
    if msg_content:
        embed.add_field(name="Message", value=f"||{msg_content[:500]}||", inline=False)
    return embed


async def log_to_channel(guild, embed):
    for name in ["sentinel-logs", "mod-logs", "logs"]:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            try:
                await ch.send(embed=embed)
                return
            except: pass


# ============ MAIN CHECK ============
async def check_message(message):
    """Check a message with Volaris."""
    if not message.guild or message.author.bot:
        return False
    
    if not _get_enabled(message.guild.id):
        return False
    
    if _is_trusted(message.author.id, message.guild.id):
        return False
    
    text = message.content or ""
    
    # Get first image
    image_url = None
    for att in message.attachments:
        try:
            if att.content_type and att.content_type.startswith("image/"):
                image_url = att.url
                break
            elif att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                image_url = att.url
                break
        except: pass
    
    if not image_url:
        for embed in message.embeds:
            try:
                if embed.image and embed.image.url:
                    image_url = embed.image.url
                    break
            except: pass
    
    # Skip empty
    if not text.strip() and not image_url:
        return False
    if text and len(text.strip()) < 3 and not image_url:
        return False
    
    # Call API
    result = await call_volaris(text=text if text.strip() else None, image_url=image_url)
    if not result:
        return False
    
    verdict = parse_verdict(result)
    if not verdict or not verdict["flagged"]:
        return False
    
    source = "text+image" if (text.strip() and image_url) else ("image" if image_url else "text")
    await take_action(message, verdict, source)
    return True


# ============ SETUP FUNCTION ============
def setup(bot):
    """Call this from bot.py to register everything."""
    print("[volaris] Setting up...")
    _ensure_col()
    
    # Register listener
    @bot.listen("on_message")
    async def _volaris_msg_listener(message):
        try:
            await check_message(message)
        except Exception as e:
            print(f"[volaris] listener err: {e}")
    
    # Register commands
    @bot.tree.command(name="volaris", description="[Admin] Toggle Volaris Guard")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def volaris_toggle(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        _set_enabled(i.guild.id, 1 if state.value == "on" else 0)
        await i.response.send_message(f"🛡️ Volaris **{state.name}**", ephemeral=True)
    
    
    @bot.tree.command(name="volaris_test", description="[Admin] Test Volaris API")
    @app_commands.describe(text="Text to check")
    async def volaris_test(i: discord.Interaction, text: str):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        if not VOLARIS_API_KEY:
            await i.followup.send("❌ VOLARIS_API_KEY not set in env vars!", ephemeral=True)
            return
        
        result = await call_volaris(text=text)
        
        if not result:
            await i.followup.send(
                "❌ No response. Check console for `[volaris]` errors.\n"
                f"Key set: {bool(VOLARIS_API_KEY)}\n"
                f"Key preview: `{VOLARIS_API_KEY[:15]}...`" if VOLARIS_API_KEY else "Key: NOT SET",
                ephemeral=True
            )
            return
        
        verdict = parse_verdict(result)
        
        embed = discord.Embed(
            title="🧪 Volaris Test",
            color=discord.Color.red() if verdict["flagged"] else discord.Color.green()
        )
        embed.add_field(name="Text", value=f"```{text[:500]}```", inline=False)
        embed.add_field(name="Flagged?", value="YES ❌" if verdict["flagged"] else "NO ✅", inline=True)
        embed.add_field(name="Score", value=f"{verdict['score']:.0%}", inline=True)
        embed.add_field(name="Severity", value=verdict["severity"], inline=True)
        embed.add_field(name="Categories", value=", ".join(verdict["categories"]) or "None", inline=False)
        embed.add_field(name="Reasoning", value=verdict["reasoning"][:1000] or "None", inline=False)
        embed.add_field(name="Credits", value=str(verdict["credits"]), inline=True)
        embed.add_field(name="Raw", value=f"```json\n{json.dumps(result, indent=2)[:600]}\n```", inline=False)
        
        await i.followup.send(embed=embed, ephemeral=True)
    
    
    @bot.tree.command(name="volaris_debug", description="[Admin] Debug Volaris")
    async def volaris_debug(i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        info = [
            f"**Key set:** {'✅' if VOLARIS_API_KEY else '❌'}",
            f"**Endpoint:** `{VOLARIS_URL}`",
        ]
        if VOLARIS_API_KEY:
            info.append(f"**Key preview:** `{VOLARIS_API_KEY[:15]}...`")
            info.append(f"**Key length:** {len(VOLARIS_API_KEY)}")
        
        info.append("\n**Testing raw request...**")
        
        try:
            headers = {"x-api-key": VOLARIS_API_KEY, "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    VOLARIS_URL,
                    headers=headers,
                    json={"text": "test message"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    info.append(f"**Status:** {resp.status}")
                    body = await resp.text()
                    info.append(f"**Body:**\n```{body[:1500]}```")
        except Exception as e:
            info.append(f"**Exception:** `{e}`")
        
        await i.followup.send("\n".join(info)[:2000], ephemeral=True)
    
    print("[volaris] ✅ Setup complete! Commands: /volaris /volaris_test /volaris_debug")
