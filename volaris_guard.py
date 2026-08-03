# volaris_guard.py
# ================================
# Volaris Guard v2.2 Integration
# Text + Image moderation with per-server custom policies
# Auto-uses your server rules as inline policy
# ================================

import aiohttp
import asyncio
import json
import os
import re
import time
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from discord import app_commands

# ============ CONFIG ============
VOLARIS_API_KEY = os.getenv("VOLARIS_API_KEY", "")
VOLARIS_URL = "https://api.volarishq.uk/guard/moderate"
VOLARIS_BATCH_URL = "https://api.volarishq.uk/guard/moderate"  # same endpoint, use "items" key

_bot_ref = None
_is_setup = False

# Caches
_verdict_cache: dict[str, tuple] = {}
CACHE_TTL = 3600

# Rate limiting (60/min = 1/sec, we'll do 0.8s to be safe)
_last_call = [0.0]
CALL_DELAY = 0.8


# ============ DB ============
def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns():
    try:
        conn = _get_db()
        c = conn.cursor()
        for col, definition in [
            ("volaris_enabled", "INTEGER DEFAULT 1"),
            ("volaris_policy_id", "TEXT DEFAULT ''"),
            ("volaris_custom_policy", "TEXT DEFAULT ''"),
            ("volaris_use_server_rules", "INTEGER DEFAULT 1"),
        ]:
            try:
                c.execute(f"ALTER TABLE guild_settings ADD COLUMN {col} {definition}")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        conn.close()
    except Exception as e:
        print(f"[volaris] ensure columns err: {e}")


def _get_col(guild_id, col, default=None):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(f"SELECT {col} FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()
        if row is None:
            return default
        val = row[col]
        return val if val is not None else default
    except sqlite3.OperationalError:
        _ensure_columns()
        return default
    except:
        return default


def _save_col(guild_id, col, value):
    try:
        _ensure_columns()
        conn = _get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
        c.execute(f"UPDATE guild_settings SET {col}=? WHERE guild_id=?", (value, str(guild_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[volaris] save err: {e}")


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


# ============ POLICY BUILDER ============
def _build_policy_for_guild(guild_id) -> str:
    """Build inline policy for a guild - uses server rules if available."""
    # Custom policy override
    custom = _get_col(guild_id, "volaris_custom_policy", "") or ""
    if custom.strip():
        return custom[:9000]
    
    # Try to get server rules from smart_rules cache
    if _get_col(guild_id, "volaris_use_server_rules", 1):
        try:
            import sys
            for mod in sys.modules.values():
                if mod is None: continue
                if hasattr(mod, '_rules_cache'):
                    cache = mod._rules_cache
                    if str(guild_id) in cache:
                        rules_data = cache[str(guild_id)]
                        rules = rules_data.get("rules", [])
                        if rules:
                            policy_lines = ["# Server Rules Policy\n\n## VIOLATES\n"]
                            for r in rules:
                                num = r.get("number", "?")
                                title = r.get("title", "Rule")
                                desc = r.get("description", "")
                                policy_lines.append(f"- Rule {num} ({title}): {desc[:300]}")
                            policy_lines.append("\n## ALLOWED\n")
                            policy_lines.append("- Normal friendly chat, memes, gaming talk")
                            policy_lines.append("- Casual conversation and greetings")
                            policy_lines.append("\nReturn 'flagged' if any VIOLATES rule matches with high confidence.")
                            policy_lines.append("Return 'review' for borderline cases.")
                            policy_lines.append("Return 'safe' otherwise.")
                            return "\n".join(policy_lines)[:9000]
        except: pass
    
    # Default policy
    return """# Discord Community Policy

## VIOLATES
- Slurs (racial, homophobic, transphobic, ableist)
- Sexual content or nudity in SFW channels
- CSAM or any sexualization of minors
- Threats of violence or death threats
- Doxxing (sharing personal info like addresses, IDs, credit cards)
- Scams (crypto scams, fake giveaways, phishing)
- Malicious links (IP grabbers, token loggers, fake nitro)
- Hate speech targeting groups
- Predatory behavior toward users
- Self-harm encouragement

## ALLOWED
- Normal chat, jokes, memes
- Strong opinions (unless attacking someone)
- Gaming talk (in-game violence discussions)
- Mild profanity in casual conversation

Return "flagged" for clear violations.
Return "review" for borderline cases.
Return "safe" otherwise."""


# ============ API CALL ============
async def call_volaris(text: str = None, image_url: str = None, policy: str = None, policy_id: str = None) -> dict | None:
    """Call Volaris Guard moderate endpoint."""
    if not VOLARIS_API_KEY:
        return None
    if not text and not image_url:
        return None
    
    # Cache key
    key_parts = [text or "", image_url or "", policy_id or ""]
    if policy:
        key_parts.append(hashlib.md5(policy.encode()).hexdigest()[:8])
    cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
    
    if cache_key in _verdict_cache:
        cached, ts = _verdict_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached
    
    await _rate_limit()
    
    body = {}
    if text:
        body["text"] = text[:50000]
    if image_url:
        body["image_url"] = image_url
    if policy_id:
        body["policy_id"] = policy_id
    elif policy:
        body["policy"] = policy[:10000]
    
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
                    if len(_verdict_cache) > 1000:
                        oldest = min(_verdict_cache.keys(), key=lambda k: _verdict_cache[k][1])
                        del _verdict_cache[oldest]
                    return data
                elif resp.status == 401:
                    print("[volaris] ❌ 401 - Invalid API key")
                elif resp.status == 402:
                    print("[volaris] ❌ 402 - Out of credits!")
                elif resp.status == 403:
                    print("[volaris] ❌ 403 - Account inactive or scope missing")
                elif resp.status == 429:
                    retry_after = resp.headers.get("Retry-After", "5")
                    print(f"[volaris] ⏳ 429 - Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(float(retry_after))
                elif resp.status == 400:
                    err_text = await resp.text()
                    print(f"[volaris] ❌ 400 - Bad request: {err_text[:200]}")
                else:
                    err_text = await resp.text()
                    print(f"[volaris] ❌ {resp.status}: {err_text[:200]}")
    except asyncio.TimeoutError:
        print("[volaris] ⏱️ Request timed out")
    except Exception as e:
        print(f"[volaris] ❌ Request err: {e}")
    
    return None


# ============ VERDICT PARSE ============
def _parse_verdict(data: dict) -> dict:
    """Parse Volaris response into our standard format."""
    if not data:
        return {"flagged": False, "review": False}
    
    verdict = str(data.get("verdict", "safe")).lower()
    score = float(data.get("score", 0.0))
    categories_raw = data.get("categories", {})
    reasoning = data.get("reasoning", "")
    
    flagged = verdict == "flagged"
    review = verdict == "review"
    
    # Extract categories that are flagged
    flagged_categories = []
    if isinstance(categories_raw, dict):
        for cat_name, cat_data in categories_raw.items():
            if isinstance(cat_data, dict):
                if cat_data.get("flagged"):
                    flagged_categories.append(cat_name)
            elif cat_data:
                flagged_categories.append(cat_name)
    elif isinstance(categories_raw, list):
        flagged_categories = [str(c) for c in categories_raw]
    
    # Determine severity based on categories + score
    severity = "none"
    if flagged:
        critical_cats = ["csam", "child", "child_sexual", "terrorism", "extreme"]
        high_cats = ["nsfw", "hate", "violence", "self_harm", "doxxing", "harassment", "phishing", "scam", "crypto_scam"]
        
        if any(c in str(flagged_categories).lower() for c in critical_cats):
            severity = "critical"
        elif any(c in str(flagged_categories).lower() for c in high_cats):
            severity = "high"
        elif score > 0.8:
            severity = "high"
        elif score > 0.6:
            severity = "medium"
        else:
            severity = "low"
    elif review:
        severity = "low"
    
    return {
        "flagged": flagged,
        "review": review,
        "score": score,
        "categories": flagged_categories,
        "severity": severity,
        "reasoning": reasoning[:500] if reasoning else "",
        "raw": data,
        "credits_used": data.get("credits_used", 0)
    }


# ============ MODERATION HANDLERS ============
async def _handle_message(message):
    """Main moderation logic."""
    if not message.guild or message.author.bot:
        return False
    
    if not _get_col(message.guild.id, "volaris_enabled", 1):
        return False
    
    if _is_trusted(message.author.id, message.guild.id):
        return False
    
    text = message.content or ""
    
    # Get image URLs
    image_urls = []
    for att in message.attachments:
        try:
            if att.content_type and att.content_type.startswith("image/"):
                image_urls.append(att.url)
            elif att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                image_urls.append(att.url)
        except: pass
    for embed in message.embeds:
        try:
            if embed.image and embed.image.url:
                image_urls.append(embed.image.url)
        except: pass
    
    # Skip if nothing to check
    if not text.strip() and not image_urls:
        return False
    if text and len(text.strip()) < 3 and not image_urls:
        return False
    
    # Get policy for this guild
    policy_id = _get_col(message.guild.id, "volaris_policy_id", "") or None
    policy = None if policy_id else _build_policy_for_guild(message.guild.id)
    
    # Check text + first image together (saves credits, more accurate)
    checked = False
    first_image = image_urls[0] if image_urls else None
    
    if text.strip() or first_image:
        result = await call_volaris(
            text=text if text.strip() else None,
            image_url=first_image,
            policy=policy,
            policy_id=policy_id
        )
        if result:
            checked = True
            verdict = _parse_verdict(result)
            if verdict.get("flagged"):
                await _take_action(message, verdict, "text+image" if first_image else "text")
                return True
    
    # Check remaining images individually if there are more
    if len(image_urls) > 1:
        for url in image_urls[1:3]:  # Max 2 more (3 total)
            result = await call_volaris(image_url=url, policy=policy, policy_id=policy_id)
            if result:
                verdict = _parse_verdict(result)
                if verdict.get("flagged"):
                    await _take_action(message, verdict, "image")
                    return True
    
    return False


async def _take_action(message, verdict: dict, source: str):
    """Take moderation action."""
    author = message.author
    guild = message.guild
    
    severity = verdict.get("severity", "medium")
    categories = verdict.get("categories", [])
    reasoning = verdict.get("reasoning", "Volaris flagged this")
    score = verdict.get("score", 0)
    
    cat_str = ", ".join(categories) if categories else "policy violation"
    full_reason = f"Volaris ({source}): {cat_str} - {reasoning}"
    
    # Delete
    try:
        await message.delete()
    except: pass
    
    # Check if we can punish
    can_punish = False
    try:
        if isinstance(author, discord.Member):
            if author.id != guild.owner_id and author.top_role < guild.me.top_role:
                can_punish = True
    except: pass
    
    # BAN for critical + CSAM
    if severity == "critical" or any(c in str(cat_str).lower() for c in ["csam", "child"]):
        if can_punish:
            try:
                await guild.ban(author, reason=full_reason[:500], delete_message_days=1)
                _log_action(author.id, guild.id, "VOLARIS BAN", full_reason)
                await _alert_mods(guild, _make_embed(author, verdict, source, "AUTO-BAN", discord.Color.dark_red()))
                return
            except: pass
    
    # WARN + timeout
    wc = _add_warning(author.id, guild.id, full_reason, severity)
    _log_action(author.id, guild.id, f"VOLARIS ({source.upper()})", full_reason)
    
    try:
        await message.channel.send(
            f"{author.mention} That was flagged: **{reasoning[:150]}** | Warning #{wc}",
            delete_after=6
        )
    except: pass
    
    if can_punish and severity in ["high", "critical"]:
        try:
            dur = 60 if severity == "critical" else 30
            await author.timeout(datetime.now() + timedelta(minutes=dur), reason=full_reason[:500])
        except: pass
    
    # Log
    color = {
        "critical": discord.Color.dark_red(),
        "high": discord.Color.red(),
        "medium": discord.Color.orange(),
        "low": discord.Color.yellow()
    }.get(severity, discord.Color.orange())
    
    await _alert_mods(guild, _make_embed(author, verdict, source, "Flagged", color, warning_num=wc, message_content=message.content))


def _make_embed(author, verdict, source, action, color, warning_num=None, message_content=""):
    embed = discord.Embed(
        title=f"🛡️ Volaris Guard - {action}",
        color=color,
        timestamp=datetime.now()
    )
    embed.add_field(name="User", value=getattr(author, "mention", str(author)), inline=True)
    embed.add_field(name="Source", value=source, inline=True)
    embed.add_field(name="Severity", value=verdict.get("severity", "?"), inline=True)
    if warning_num:
        embed.add_field(name="Warning #", value=str(warning_num), inline=True)
    embed.add_field(name="Score", value=f"{verdict.get('score', 0):.0%}", inline=True)
    embed.add_field(name="Credits", value=str(verdict.get("credits_used", "?")), inline=True)
    embed.add_field(name="Categories", value=", ".join(verdict.get("categories", [])) or "None", inline=False)
    embed.add_field(name="Reasoning", value=verdict.get("reasoning", "")[:1000] or "None", inline=False)
    if message_content:
        embed.add_field(name="Message", value=f"||{message_content[:500]}||", inline=False)
    return embed


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
    
    @bot.tree.command(name="volaris", description="[Admin] Toggle Volaris Guard")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def volaris_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        _save_col(i.guild.id, "volaris_enabled", 1 if state.value == "on" else 0)
        await i.response.send_message(f"🛡️ Volaris Guard **{state.name}**", ephemeral=True)
    
    
    @bot.tree.command(name="volaris_test", description="[Admin] Test Volaris with text or image URL")
    @app_commands.describe(text="Text to check", image_url="Image URL to check (optional)")
    async def volaris_test_cmd(i: discord.Interaction, text: str = None, image_url: str = None):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        if not text and not image_url:
            await i.response.send_message("Provide text or image_url!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        if not VOLARIS_API_KEY:
            await i.followup.send("❌ VOLARIS_API_KEY not set!", ephemeral=True)
            return
        
        policy = _build_policy_for_guild(i.guild.id)
        result = await call_volaris(text=text, image_url=image_url, policy=policy)
        
        if not result:
            await i.followup.send("❌ Volaris returned no response. Check console for errors.", ephemeral=True)
            return
        
        verdict = _parse_verdict(result)
        
        embed = discord.Embed(
            title="🧪 Volaris Test",
            color=discord.Color.red() if verdict["flagged"] else (
                discord.Color.orange() if verdict.get("review") else discord.Color.green()
            )
        )
        if text:
            embed.add_field(name="Text", value=f"```{text[:500]}```", inline=False)
        if image_url:
            embed.add_field(name="Image URL", value=image_url[:500], inline=False)
            embed.set_image(url=image_url)
        
        embed.add_field(name="Verdict", value=result.get("verdict", "?"), inline=True)
        embed.add_field(name="Score", value=f"{verdict.get('score', 0):.0%}", inline=True)
        embed.add_field(name="Severity", value=verdict.get("severity", "?"), inline=True)
        embed.add_field(name="Credits Used", value=str(verdict.get("credits_used", "?")), inline=True)
        embed.add_field(name="Categories", value=", ".join(verdict.get("categories", [])) or "None", inline=False)
        embed.add_field(name="Reasoning", value=verdict.get("reasoning", "None")[:1000], inline=False)
        embed.add_field(
            name="Raw Response",
            value=f"```json\n{json.dumps(result, indent=2)[:800]}\n```",
            inline=False
        )
        
        await i.followup.send(embed=embed, ephemeral=True)
    
    
    @bot.tree.command(name="volaris_set_policy_id", description="[Admin] Set saved policy ID from Volaris dashboard")
    @app_commands.describe(policy_id="Policy UUID (leave empty to clear)")
    async def volaris_policy_id_cmd(i: discord.Interaction, policy_id: str = ""):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        _save_col(i.guild.id, "volaris_policy_id", policy_id.strip())
        if policy_id.strip():
            await i.response.send_message(f"✅ Policy ID set: `{policy_id}`", ephemeral=True)
        else:
            await i.response.send_message("✅ Policy ID cleared. Using inline policy.", ephemeral=True)
    
    
    @bot.tree.command(name="volaris_use_rules", description="[Admin] Use server rules as Volaris policy")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def volaris_use_rules_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        _save_col(i.guild.id, "volaris_use_server_rules", 1 if state.value == "on" else 0)
        await i.response.send_message(
            f"📜 Volaris will {'use' if state.value == 'on' else 'NOT use'} server rules as policy.",
            ephemeral=True
        )
    
    
    @bot.tree.command(name="volaris_show_policy", description="[Admin] Show current Volaris policy")
    async def volaris_show_policy_cmd(i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        policy_id = _get_col(i.guild.id, "volaris_policy_id", "")
        policy = _build_policy_for_guild(i.guild.id)
        
        embed = discord.Embed(title="🛡️ Current Volaris Policy", color=discord.Color.blue())
        if policy_id:
            embed.add_field(name="Policy ID (overrides inline)", value=f"`{policy_id}`", inline=False)
        else:
            embed.add_field(name="Policy Type", value="Inline (per-request)", inline=False)
            preview = policy[:1000] + ("..." if len(policy) > 1000 else "")
            embed.add_field(name="Policy Content", value=f"```{preview}```", inline=False)
        
        await i.response.send_message(embed=embed, ephemeral=True)


# ============ LISTENER ============
def _register_listener(bot):
    @bot.listen("on_message")
    async def _volaris_listener(message):
        try:
            await _handle_message(message)
        except Exception as e:
            print(f"[volaris] listener err: {e}")


# ============ SETUP ============
def setup(bot):
    global _bot_ref, _is_setup
    if _is_setup: return
    _bot_ref = bot
    _is_setup = True
    
    _ensure_columns()
    _register_commands(bot)
    _register_listener(bot)
    
    if VOLARIS_API_KEY:
        print(f"[volaris] ✅ Loaded. Endpoint: {VOLARIS_URL}")
    else:
        print("[volaris] ⚠️ VOLARIS_API_KEY not set!")


# ============ AUTO HOOK ============
def _auto_hook():
    import sys
    for module_name, module in list(sys.modules.items()):
        if module is None: continue
        if hasattr(module, "bot") and isinstance(getattr(module, "bot", None), commands.Bot):
            setup(module.bot)
            return True
    return False

def _delayed_hook():
    for attempt in range(30):
        time.sleep(1)
        try:
            if _auto_hook():
                return
        except: pass
    print("[volaris] ⚠️ Could not auto-hook.")

threading.Thread(target=_delayed_hook, daemon=True).start()
