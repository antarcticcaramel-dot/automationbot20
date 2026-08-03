# volaris_guard.py
# Auto-setup version - just add `import volaris_guard` to bot.py

import aiohttp
import asyncio
import json
import os
import time
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands

# ============ CONFIG ============
VOLARIS_API_KEY = os.getenv("VOLARIS_API_KEY", "").strip()
VOLARIS_URL = "https://api.volarishq.uk/guard/moderate"

_cache = {}
_last_call = [0.0]
_is_setup = False

DEFAULT_POLICY = """# Discord Server Rules

## VIOLATES
- Slurs (racial, homophobic, transphobic, ableist)
- Sexual content in non-NSFW channels
- CSAM or sexualization of minors
- Threats of violence, death threats
- Doxxing (sharing personal info)
- Scams (crypto scams, fake giveaways, phishing, fake nitro)
- Malicious links (IP grabbers, token loggers)
- Hate speech
- Predatory behavior toward users
- Self-harm encouragement

## ALLOWED
- Normal chat, memes, gaming
- Strong opinions
- Mild profanity

Return "flagged" for clear violations.
Return "safe" otherwise."""


# ============ DATABASE ============
def _db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_col():
    try:
        conn = _db()
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE guild_settings ADD COLUMN volaris_enabled INTEGER DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.close()
    except: pass


def _enabled(gid):
    try:
        conn = _db()
        c = conn.cursor()
        c.execute("SELECT volaris_enabled FROM guild_settings WHERE guild_id=?", (str(gid),))
        row = c.fetchone()
        conn.close()
        return True if row is None else bool(row["volaris_enabled"])
    except:
        _ensure_col()
        return True


def _set_enabled(gid, val):
    try:
        _ensure_col()
        conn = _db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(gid),))
        c.execute("UPDATE guild_settings SET volaris_enabled=? WHERE guild_id=?", (int(val), str(gid)))
        conn.commit()
        conn.close()
    except: pass


def _trusted(uid, gid):
    try:
        conn = _db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM trusted_users WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
        r = c.fetchone()
        conn.close()
        return r is not None
    except:
        return False


def _add_warn(uid, gid, reason, severity):
    try:
        conn = _db()
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


# ============ API CALL ============
async def call_api(text=None, image_url=None):
    if not VOLARIS_API_KEY:
        print("[volaris] ❌ VOLARIS_API_KEY is empty!")
        return None
    if not text and not image_url:
        return None
    
    key = hashlib.md5(f"{text or ''}|{image_url or ''}".encode()).hexdigest()
    if key in _cache:
        cached, ts = _cache[key]
        if time.time() - ts < 3600:
            return cached
    
    since = time.time() - _last_call[0]
    if since < 0.8:
        await asyncio.sleep(0.8 - since)
    _last_call[0] = time.time()
    
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
                text_body = await resp.text()
                
                if resp.status == 200:
                    try:
                        data = json.loads(text_body)
                        _cache[key] = (data, time.time())
                        if len(_cache) > 500:
                            oldest = min(_cache.keys(), key=lambda k: _cache[k][1])
                            del _cache[oldest]
                        return data
                    except json.JSONDecodeError as e:
                        print(f"[volaris] ❌ JSON parse error: {e}")
                        return None
                elif resp.status == 401:
                    print(f"[volaris] ❌ 401 Invalid API key. Body: {text_body[:300]}")
                elif resp.status == 402:
                    print(f"[volaris] ❌ 402 Out of credits!")
                elif resp.status == 403:
                    print(f"[volaris] ❌ 403 Forbidden. Body: {text_body[:300]}")
                elif resp.status == 429:
                    print(f"[volaris] ⏳ 429 Rate limited")
                    await asyncio.sleep(3)
                else:
                    print(f"[volaris] ❌ HTTP {resp.status}: {text_body[:300]}")
    except asyncio.TimeoutError:
        print(f"[volaris] ⏱️ Timeout")
    except Exception as e:
        print(f"[volaris] ❌ Exception: {type(e).__name__}: {e}")
    
    return None


# ============ PARSE ============
def parse(data):
    if not data:
        return None
    
    verdict = str(data.get("verdict", "safe")).lower()
    score = float(data.get("score", 0))
    cats_raw = data.get("categories", {})
    reasoning = str(data.get("reasoning", ""))
    
    flagged = verdict == "flagged"
    
    flagged_cats = []
    if isinstance(cats_raw, dict):
        for name, info in cats_raw.items():
            if isinstance(info, dict) and info.get("flagged"):
                flagged_cats.append(name)
    
    severity = "none"
    if flagged:
        cat_lower = " ".join(flagged_cats).lower()
        if "csam" in cat_lower or "child" in cat_lower:
            severity = "critical"
        elif any(c in cat_lower for c in ["nsfw", "hate", "violence", "doxxing", "phishing", "scam", "self_harm"]):
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
    author = message.author
    guild = message.guild
    
    severity = verdict["severity"]
    cats = verdict["categories"]
    reasoning = verdict["reasoning"] or "Policy violation"
    cat_str = ", ".join(cats) if cats else "content"
    full_reason = f"Volaris ({source}): {cat_str} - {reasoning}"
    
    try:
        await message.delete()
    except: pass
    
    can_punish = False
    try:
        if isinstance(author, discord.Member):
            if author.id != guild.owner_id and author.top_role < guild.me.top_role:
                can_punish = True
    except: pass
    
    if severity == "critical" and can_punish:
        try:
            await guild.ban(author, reason=full_reason[:500], delete_message_days=1)
            await log_msg(guild, embed_for(author, verdict, source, "AUTO-BAN", discord.Color.dark_red()))
            return
        except: pass
    
    wc = _add_warn(author.id, guild.id, full_reason, severity)
    
    try:
        await message.channel.send(
            f"{author.mention} Flagged: **{reasoning[:120]}** | Warning #{wc}",
            delete_after=5
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
    
    await log_msg(guild, embed_for(author, verdict, source, "Flagged", color, wc, message.content))


def embed_for(author, verdict, source, action, color, wnum=None, content=""):
    e = discord.Embed(title=f"🛡️ Volaris - {action}", color=color, timestamp=datetime.now())
    e.add_field(name="User", value=getattr(author, "mention", str(author)), inline=True)
    e.add_field(name="Source", value=source, inline=True)
    e.add_field(name="Severity", value=verdict["severity"], inline=True)
    if wnum:
        e.add_field(name="Warning #", value=str(wnum), inline=True)
    e.add_field(name="Score", value=f"{verdict['score']:.0%}", inline=True)
    e.add_field(name="Credits", value=str(verdict.get("credits", "?")), inline=True)
    e.add_field(name="Categories", value=", ".join(verdict["categories"]) or "None", inline=False)
    e.add_field(name="Reason", value=(verdict["reasoning"] or "None")[:1000], inline=False)
    if content:
        e.add_field(name="Message", value=f"||{content[:500]}||", inline=False)
    return e


async def log_msg(guild, embed):
    for name in ["sentinel-logs", "mod-logs", "logs"]:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            try:
                await ch.send(embed=embed)
                return
            except: pass


# ============ MAIN CHECK ============
async def check_message(message):
    if not message.guild or message.author.bot:
        return
    if not _enabled(message.guild.id):
        return
    if _trusted(message.author.id, message.guild.id):
        return
    
    text = message.content or ""
    
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
    
    if not text.strip() and not image_url:
        return
    if text and len(text.strip()) < 3 and not image_url:
        return
    
    result = await call_api(text=text if text.strip() else None, image_url=image_url)
    if not result:
        return
    
    verdict = parse(result)
    if not verdict or not verdict["flagged"]:
        return
    
    source = "text+image" if (text.strip() and image_url) else ("image" if image_url else "text")
    await take_action(message, verdict, source)


# ============ SETUP (called automatically) ============
def _setup_bot(bot):
    global _is_setup
    if _is_setup:
        return
    _is_setup = True
    
    print("=" * 50)
    print("[volaris] SETUP STARTED")
    print(f"[volaris] API key set: {bool(VOLARIS_API_KEY)}")
    if VOLARIS_API_KEY:
        print(f"[volaris] Key preview: {VOLARIS_API_KEY[:15]}...")
        print(f"[volaris] Key length: {len(VOLARIS_API_KEY)}")
    print(f"[volaris] Endpoint: {VOLARIS_URL}")
    
    _ensure_col()
    
    @bot.listen("on_message")
    async def volaris_msg(message):
        try:
            await check_message(message)
        except Exception as e:
            print(f"[volaris] listener err: {e}")
    
    @bot.tree.command(name="volaris", description="[Admin] Toggle Volaris Guard")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def cmd_toggle(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True); return
        _set_enabled(i.guild.id, 1 if state.value == "on" else 0)
        await i.response.send_message(f"🛡️ Volaris **{state.name}**", ephemeral=True)
    
    @bot.tree.command(name="volaris_debug", description="[Admin] Debug Volaris connection")
    async def cmd_debug(i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True); return
        
        await i.response.defer(ephemeral=True)
        
        info = []
        info.append(f"**API key set:** {'✅ YES' if VOLARIS_API_KEY else '❌ NO'}")
        if VOLARIS_API_KEY:
            info.append(f"**Preview:** `{VOLARIS_API_KEY[:15]}...`")
            info.append(f"**Length:** {len(VOLARIS_API_KEY)}")
        info.append(f"**Endpoint:** `{VOLARIS_URL}`")
        info.append("")
        info.append("**Making test request...**")
        
        try:
            headers = {"x-api-key": VOLARIS_API_KEY, "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    VOLARIS_URL,
                    headers=headers,
                    json={"text": "hello"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    info.append(f"**Status:** `{resp.status}`")
                    body = await resp.text()
                    info.append(f"**Body:**\n```{body[:1200]}```")
        except Exception as e:
            info.append(f"**Exception:** `{type(e).__name__}: {e}`")
        
        await i.followup.send("\n".join(info)[:2000], ephemeral=True)
    
    @bot.tree.command(name="volaris_test", description="[Admin] Test Volaris with a message")
    @app_commands.describe(text="Text to check")
    async def cmd_test(i: discord.Interaction, text: str):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True); return
        
        await i.response.defer(ephemeral=True)
        
        result = await call_api(text=text)
        if not result:
            await i.followup.send("❌ No response. Run `/volaris_debug` first.", ephemeral=True)
            return
        
        v = parse(result)
        embed = discord.Embed(
            title="🧪 Volaris Test",
            color=discord.Color.red() if v["flagged"] else discord.Color.green()
        )
        embed.add_field(name="Text", value=f"```{text[:500]}```", inline=False)
        embed.add_field(name="Flagged", value="YES ❌" if v["flagged"] else "NO ✅", inline=True)
        embed.add_field(name="Severity", value=v["severity"], inline=True)
        embed.add_field(name="Score", value=f"{v['score']:.0%}", inline=True)
        embed.add_field(name="Categories", value=", ".join(v["categories"]) or "None", inline=False)
        embed.add_field(name="Reasoning", value=(v["reasoning"] or "None")[:1000], inline=False)
        embed.add_field(name="Credits", value=str(v["credits"]), inline=True)
        
        await i.followup.send(embed=embed, ephemeral=True)
    
    print("[volaris] ✅ SETUP COMPLETE")
    print("[volaris] Commands: /volaris /volaris_debug /volaris_test")
    print("=" * 50)


# ============ AUTO HOOK ============
def _find_and_setup():
    """Aggressively find the bot instance and setup."""
    import sys
    for module_name, module in list(sys.modules.items()):
        if module is None:
            continue
        try:
            for attr_name in dir(module):
                if attr_name.startswith('_'):
                    continue
                try:
                    attr = getattr(module, attr_name)
                    if isinstance(attr, commands.Bot):
                        _setup_bot(attr)
                        return True
                except:
                    continue
        except:
            continue
    return False


def _delayed_hook():
    """Keep trying to hook for 60 seconds."""
    for attempt in range(60):
        time.sleep(1)
        try:
            if _find_and_setup():
                return
        except:
            pass
    print("[volaris] ⚠️ Auto-hook FAILED after 60 seconds.")
    print("[volaris] ⚠️ Add `volaris_guard._setup_bot(bot)` after creating your bot in bot.py")


# Start hooking thread on import
threading.Thread(target=_delayed_hook, daemon=True).start()
