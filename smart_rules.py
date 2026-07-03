# smart_rules.py
# ================================
# SentinelMod Smart Rules System
# - AI detects rules from ANY channel (text, embeds, bot messages, pinned)
# - AI understands rules even if weirdly formatted
# - Enforces rules automatically on all messages
# - Auto-hooks into bot.py
# ================================

import sqlite3
import asyncio
import threading
import time
import json
import re
import os
import aiohttp
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from discord import app_commands

# ============ CONFIG ============
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")

_bot_ref = None
_is_setup = False

# Cache: guild_id -> {"rules": str, "structured": list, "ts": float, "source_channel": str}
_rules_cache: dict[str, dict] = {}
CACHE_TTL = 3600  # 1 hour

# Track violation cooldown per user to avoid spam
_violation_cooldown: dict[str, float] = {}

# Track user violations to enable escalation
_user_violations: dict[str, list] = defaultdict(list)

RULES_CHANNEL_NAMES = [
    'rules', 'server-rules', 'rules-and-info', 'rules-info', 'server-info',
    'info', 'guidelines', 'code-of-conduct', 'conduct', 'tos', 'terms',
    'rules-and-regulations', 'regulations', 'policies', 'policy', 'handbook',
    'read-me', 'readme', 'read-first', 'start-here', 'welcome-rules'
]


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
            ("rules_channel", "TEXT DEFAULT ''"),
            ("rules_structured", "TEXT DEFAULT ''"),
            ("rules_enforcement", "INTEGER DEFAULT 1"),
        ]:
            try:
                c.execute(f"ALTER TABLE guild_settings ADD COLUMN {col} {definition}")
                conn.commit()
                print(f"[smart_rules] Added column: {col}")
            except sqlite3.OperationalError:
                pass
        conn.close()
    except Exception as e:
        print(f"[smart_rules] ensure columns err: {e}")


def _get_saved(guild_id, key):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(f"SELECT {key} FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()
        if row:
            val = row[key]
            return val if val is not None else ""
    except sqlite3.OperationalError:
        _ensure_columns()
    except:
        pass
    return ""


def _get_setting_int(guild_id, key, default=1):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(f"SELECT {key} FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()
        if row is None:
            return default
        return int(row[key]) if row[key] is not None else default
    except:
        return default


def _save(guild_id, key, value):
    try:
        _ensure_columns()
        conn = _get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
        c.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (value, str(guild_id)))
        conn.commit()
        conn.close()
        # Invalidate bot.py cache
        try:
            import sys
            for mod in sys.modules.values():
                if mod is None: continue
                if hasattr(mod, '_settings_cache'):
                    mod._settings_cache.pop(str(guild_id), None)
        except:
            pass
    except Exception as e:
        print(f"[smart_rules] save err: {e}")


def _add_warning(uid, gid, reason, severity, context=""):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO warnings (user_id,guild_id,reason,severity,ai_confidence,context,timestamp) VALUES (?,?,?,?,?,?,?)",
            (str(uid), str(gid), reason, severity, 1.0, context[:500], datetime.now().isoformat())
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


# ============ AI ============
async def ask_groq_json(prompt: str, system: str = "Respond only in valid JSON.") -> dict | None:
    if not GROQ_API_KEY:
        return None
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    for model in [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it"
    ]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    },
                    timeout=aiohttp.ClientTimeout(total=25)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["choices"][0]["message"]["content"].strip()
                        text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
                        match = re.search(r'\{.*\}', text, re.DOTALL)
                        if match:
                            try:
                                return json.loads(match.group())
                            except: pass
                    elif resp.status == 429:
                        await asyncio.sleep(2)
        except:
            continue
    return None


# ============ RULES EXTRACTION ============

async def extract_all_content_from_channel(channel: discord.TextChannel, limit: int = 50) -> str:
    """Extract EVERYTHING from a channel - text, embeds, bot messages, pinned messages."""
    content_parts = []
    
    # 1. Get pinned messages first (usually most important)
    try:
        pins = await channel.pins()
        for msg in pins:
            content_parts.append(f"[PINNED by {msg.author.display_name}]")
            if msg.content:
                content_parts.append(msg.content)
            for embed in msg.embeds:
                if embed.title:
                    content_parts.append(f"**{embed.title}**")
                if embed.description:
                    content_parts.append(embed.description)
                for field in embed.fields:
                    content_parts.append(f"**{field.name}**\n{field.value}")
                if embed.footer and embed.footer.text:
                    content_parts.append(f"_{embed.footer.text}_")
    except Exception as e:
        print(f"[smart_rules] pins err: {e}")
    
    # 2. Get regular messages (oldest first - rules usually posted first)
    try:
        async for msg in channel.history(limit=limit, oldest_first=True):
            author_label = f"[{msg.author.display_name}]"
            if msg.author.bot:
                author_label += " (BOT)"
            
            if msg.content and len(msg.content.strip()) > 5:
                content_parts.append(f"{author_label}: {msg.content}")
            
            for embed in msg.embeds:
                embed_text = []
                if embed.title:
                    embed_text.append(f"**{embed.title}**")
                if embed.description:
                    embed_text.append(embed.description)
                for field in embed.fields:
                    embed_text.append(f"**{field.name}**\n{field.value}")
                if embed.footer and embed.footer.text:
                    embed_text.append(f"_{embed.footer.text}_")
                if embed_text:
                    content_parts.append(f"{author_label} [EMBED]:\n" + "\n".join(embed_text))
    except Exception as e:
        print(f"[smart_rules] history err: {e}")
    
    # Dedupe consecutive duplicates (pinned may show twice)
    deduped = []
    seen = set()
    for part in content_parts:
        h = hashlib.md5(part.encode()).hexdigest()
        if h not in seen:
            deduped.append(part)
            seen.add(h)
    
    combined = "\n\n".join(deduped)
    return combined[:8000]  # Cap for AI context


async def ai_extract_rules(raw_content: str, guild_name: str) -> dict:
    """Use AI to extract structured rules from raw channel content."""
    if not raw_content or len(raw_content.strip()) < 20:
        return {"rules": [], "summary": ""}
    
    prompt = f"""You are analyzing a Discord server's rules channel. Extract ALL rules from the content below.

The content may include:
- Regular text messages
- Bot-posted embeds (very common for rules)
- Pinned messages
- Multiple rules across multiple messages
- Numbered lists, bullet points, or plain text
- Emojis and formatting

Your job: extract EVERY rule, no matter how it's formatted.

SERVER: {guild_name}

CONTENT:
{raw_content}

Return JSON with this exact structure:
{{
  "rules": [
    {{
      "number": 1,
      "title": "short rule title",
      "description": "full rule text",
      "keywords": ["word1", "word2", "word3"],
      "severity": "low|medium|high|critical",
      "examples_of_violations": ["example1", "example2"]
    }}
  ],
  "summary": "brief 1-2 sentence overview of what this server allows/forbids",
  "server_type": "gaming|community|art|study|nsfw|other",
  "strict_level": "chill|normal|strict|very_strict"
}}

RULES for extraction:
- If you see "1. No spam" and "2. Be nice", extract BOTH as separate rules
- If rules are in an embed with fields, each field is likely a separate rule
- Combine related sentences into one rule if they describe the same thing
- keywords should be words that would appear if someone violates that rule
- severity: "critical" for slurs/threats/NSFW, "high" for harassment/spam, "medium" for off-topic/caps, "low" for minor stuff
- examples_of_violations should be REAL example messages that would break that rule

If there are no actual rules in the content (just chat/announcements/welcome messages), return:
{{"rules": [], "summary": "No rules found", "server_type": "other", "strict_level": "normal"}}

Return ONLY valid JSON."""

    result = await ask_groq_json(prompt, "You are an expert at extracting structured rules from Discord content.")
    
    if not result:
        return {"rules": [], "summary": "AI unavailable"}
    
    # Normalize
    if "rules" not in result or not isinstance(result["rules"], list):
        result["rules"] = []
    
    for rule in result["rules"]:
        if "keywords" not in rule or not isinstance(rule.get("keywords"), list):
            rule["keywords"] = []
        if "examples_of_violations" not in rule:
            rule["examples_of_violations"] = []
        if "severity" not in rule:
            rule["severity"] = "medium"
    
    return result


# ============ FIND RULES CHANNEL ============
async def find_rules_channel(guild) -> discord.TextChannel | None:
    """Find the rules channel - manual > common names > topic > AI guess."""
    # 1. Manually saved
    saved = _get_saved(guild.id, "rules_channel")
    if saved:
        ch = discord.utils.get(guild.text_channels, name=saved)
        if ch:
            try:
                if ch.permissions_for(guild.me).read_messages:
                    return ch
            except: pass
    
    # 2. Common names
    for name in RULES_CHANNEL_NAMES:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            try:
                if ch.permissions_for(guild.me).read_messages:
                    return ch
            except: pass
    
    # 3. Contains "rule" or "guideline" in name/topic
    for ch in guild.text_channels:
        try:
            if not ch.permissions_for(guild.me).read_messages:
                continue
            if 'rule' in ch.name.lower() or 'guideline' in ch.name.lower():
                return ch
            if ch.topic and ('rule' in ch.topic.lower() or 'guideline' in ch.topic.lower()):
                return ch
        except: pass
    
    # 4. Discord's official rules_channel setting
    try:
        if hasattr(guild, 'rules_channel') and guild.rules_channel:
            return guild.rules_channel
    except: pass
    
    return None


async def load_and_extract_rules(guild, force_refresh: bool = False) -> dict:
    """Load rules from cache or extract fresh."""
    gid = str(guild.id)
    
    # Check cache
    if not force_refresh and gid in _rules_cache:
        cached = _rules_cache[gid]
        if time.time() - cached.get("ts", 0) < CACHE_TTL:
            return cached
    
    ch = await find_rules_channel(guild)
    if not ch:
        result = {
            "rules": [],
            "summary": "No rules channel found",
            "raw": "",
            "structured": {"rules": []},
            "source_channel": None,
            "ts": time.time()
        }
        _rules_cache[gid] = result
        return result
    
    print(f"[smart_rules] Extracting rules from #{ch.name} in {guild.name}")
    raw = await extract_all_content_from_channel(ch)
    
    if not raw or len(raw.strip()) < 20:
        result = {
            "rules": [],
            "summary": "Rules channel is empty",
            "raw": "",
            "structured": {"rules": []},
            "source_channel": ch.name,
            "ts": time.time()
        }
        _rules_cache[gid] = result
        return result
    
    structured = await ai_extract_rules(raw, guild.name)
    
    result = {
        "rules": structured.get("rules", []),
        "summary": structured.get("summary", ""),
        "raw": raw,
        "structured": structured,
        "source_channel": ch.name,
        "ts": time.time()
    }
    
    _rules_cache[gid] = result
    
    # Save structured rules to DB for persistence
    try:
        _save(guild.id, "rules_structured", json.dumps(structured)[:8000])
    except: pass
    
    print(f"[smart_rules] Extracted {len(result['rules'])} rules for {guild.name}")
    return result


# ============ ENFORCEMENT ============

async def check_message_against_rules(content: str, author_name: str, guild) -> dict:
    """Use AI to check if a message violates the server rules."""
    rules_data = await load_and_extract_rules(guild)
    rules = rules_data.get("rules", [])
    
    if not rules:
        return {"violates": False}
    
    # Quick keyword pre-check to save API calls
    content_lower = content.lower()
    potentially_relevant = []
    for rule in rules:
        keywords = rule.get("keywords", [])
        if any(kw.lower() in content_lower for kw in keywords if kw):
            potentially_relevant.append(rule)
    
    # If no keyword hits, still run AI check but with lower depth for common violations
    rules_to_check = potentially_relevant if potentially_relevant else rules[:10]
    
    rules_text = json.dumps([{
        "number": r.get("number"),
        "title": r.get("title"),
        "description": r.get("description"),
        "severity": r.get("severity", "medium")
    } for r in rules_to_check], indent=2)
    
    prompt = f"""Check if this Discord message violates the server's rules.

SERVER RULES:
{rules_text}

MESSAGE from {author_name}: "{content[:500]}"

Analyze carefully. Only flag CLEAR violations of EXPLICIT rules.

Return JSON:
{{
  "violates": true/false,
  "rule_number": null_or_number,
  "rule_title": "which rule",
  "reason": "brief explanation of why it violates",
  "severity": "low|medium|high|critical",
  "confidence": 0.0-1.0
}}

Be CONSERVATIVE - if you're not sure, say false.
Do NOT flag:
- Greetings, casual chat, memes
- Strong opinions (unless they attack someone)
- Swears in general (unless a rule specifically bans them)
- Anything that only slightly resembles a violation

DO flag:
- Direct attacks on users
- Sharing content the rules explicitly ban
- Spamming/self-promotion if banned
- Clear violations with high confidence"""

    result = await ask_groq_json(prompt, "You are a fair Discord rule enforcer. Only flag CLEAR violations.")
    
    if not result:
        return {"violates": False}
    
    # Confidence threshold
    if result.get("confidence", 0) < 0.7:
        return {"violates": False}
    
    return result


async def enforce_rule_violation(message, violation: dict):
    """Take action on a rule violation."""
    author = message.author
    guild = message.guild
    
    rule_title = violation.get("rule_title", "server rule")
    reason = violation.get("reason", "Violated server rules")
    severity = violation.get("severity", "medium")
    rule_num = violation.get("rule_number")
    
    full_reason = f"Rule {rule_num}: {rule_title} - {reason}" if rule_num else f"{rule_title}: {reason}"
    
    # Delete message
    try:
        await message.delete()
    except: pass
    
    # Add warning
    wc = _add_warning(author.id, guild.id, full_reason, severity, message.content[:200])
    _log_action(author.id, guild.id, "RULE VIOLATION", full_reason)
    
    # Notify user briefly
    try:
        rule_ref = f"Rule {rule_num}" if rule_num else "a rule"
        await message.channel.send(
            f"{author.mention} That broke {rule_ref} (**{rule_title}**) | Warning #{wc}",
            delete_after=8
        )
    except: pass
    
    # Timeout based on severity + warning count
    can_punish = False
    try:
        if isinstance(author, discord.Member):
            if author.id != guild.owner_id and author.top_role < guild.me.top_role:
                can_punish = True
    except: pass
    
    if can_punish:
        mute_dur = None
        if severity == "critical":
            mute_dur = 60
        elif severity == "high":
            mute_dur = 30
        elif wc >= 3:
            mute_dur = 10
        
        if mute_dur:
            try:
                await author.timeout(
                    datetime.now() + timedelta(minutes=mute_dur),
                    reason=full_reason
                )
            except: pass
    
    # Log to mod channel
    for ch_name in ["sentinel-logs", "mod-logs", "logs"]:
        log_ch = discord.utils.get(guild.text_channels, name=ch_name)
        if log_ch:
            try:
                embed = discord.Embed(
                    title=f"📜 Rule Enforcement - {severity.upper()}",
                    color=discord.Color.orange() if severity in ["low", "medium"] else discord.Color.red()
                )
                embed.add_field(name="User", value=author.mention, inline=True)
                embed.add_field(name="Rule", value=f"#{rule_num}: {rule_title}" if rule_num else rule_title, inline=True)
                embed.add_field(name="Warning #", value=str(wc), inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Message", value=f"||{message.content[:500]}||", inline=False)
                embed.add_field(name="Confidence", value=f"{violation.get('confidence', 0):.0%}", inline=True)
                await log_ch.send(embed=embed)
                break
            except: pass


# ============ HELPER ============
def _should_check_message(message) -> bool:
    """Quick filter to decide if a message needs AI rule check."""
    if message.author.bot: return False
    if not message.guild: return False
    if not message.content or len(message.content.strip()) < 3: return False
    
    # Cooldown check - don't check same user too often
    key = f"{message.guild.id}:{message.author.id}"
    now = time.time()
    if key in _violation_cooldown:
        if now - _violation_cooldown[key] < 3:  # 3 second cooldown per user
            return False
    _violation_cooldown[key] = now
    
    return True


# ============ SLASH COMMANDS ============

def _register_commands(bot):

    @bot.tree.command(
        name="set_rules_channel",
        description="[Admin] Set which channel contains your server rules"
    )
    @app_commands.describe(channel="The channel that contains your server rules")
    async def set_rules_channel_cmd(i: discord.Interaction, channel: discord.TextChannel):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        try:
            perms = channel.permissions_for(i.guild.me)
            if not perms.read_messages:
                await i.response.send_message(
                    f"❌ I can't see {channel.mention}! Give me View Channel permission there first.",
                    ephemeral=True
                )
                return
            if not perms.read_message_history:
                await i.response.send_message(
                    f"❌ I can't read history in {channel.mention}!",
                    ephemeral=True
                )
                return
        except Exception as e:
            await i.response.send_message(f"Error: {e}", ephemeral=True)
            return
        
        _save(i.guild.id, "rules_channel", channel.name)
        # Clear caches
        _rules_cache.pop(str(i.guild.id), None)
        
        await i.response.defer(ephemeral=True)
        
        # Extract rules immediately
        rules_data = await load_and_extract_rules(i.guild, force_refresh=True)
        rules = rules_data.get("rules", [])
        
        embed = discord.Embed(
            title="✅ Rules Channel Set!",
            description=f"Rules channel: {channel.mention}",
            color=discord.Color.green()
        )
        
        if rules:
            embed.add_field(name="Rules Extracted", value=f"**{len(rules)}** rules found", inline=True)
            embed.add_field(name="Server Type", value=rules_data.get("structured", {}).get("server_type", "unknown"), inline=True)
            embed.add_field(name="Strictness", value=rules_data.get("structured", {}).get("strict_level", "normal"), inline=True)
            
            preview = "\n".join([
                f"**{r.get('number', '?')}.** {r.get('title', 'Rule')}"
                for r in rules[:8]
            ])
            if len(rules) > 8:
                preview += f"\n_...and {len(rules) - 8} more_"
            
            embed.add_field(name="Rules Preview", value=preview[:1024], inline=False)
            embed.add_field(name="Summary", value=rules_data.get("summary", "")[:1024], inline=False)
        else:
            embed.add_field(
                name="⚠️ Warning",
                value="No rules could be extracted from that channel. Make sure it has actual rule content!",
                inline=False
            )
        
        await i.followup.send(embed=embed, ephemeral=True)


    @bot.tree.command(
        name="view_rules",
        description="View the extracted server rules"
    )
    async def view_rules_cmd(i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        
        rules_data = await load_and_extract_rules(i.guild)
        rules = rules_data.get("rules", [])
        source = rules_data.get("source_channel")
        
        if not rules:
            await i.followup.send(
                "❌ No rules extracted yet. Use `/set_rules_channel` first!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📜 Server Rules ({len(rules)})",
            description=rules_data.get("summary", ""),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Source: #{source}" if source else "Source: auto-detected")
        
        for rule in rules[:15]:
            num = rule.get("number", "?")
            title = rule.get("title", "Rule")
            desc = rule.get("description", "")
            severity = rule.get("severity", "medium")
            
            emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(severity, "⚪")
            
            embed.add_field(
                name=f"{emoji} Rule {num}: {title}",
                value=desc[:200] + ("..." if len(desc) > 200 else ""),
                inline=False
            )
        
        if len(rules) > 15:
            embed.add_field(name="...", value=f"And {len(rules) - 15} more rules", inline=False)
        
        await i.followup.send(embed=embed, ephemeral=True)


    @bot.tree.command(
        name="reload_rules",
        description="[Admin] Re-read and re-analyze the rules channel"
    )
    async def reload_rules_cmd(i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        _rules_cache.pop(str(i.guild.id), None)
        rules_data = await load_and_extract_rules(i.guild, force_refresh=True)
        rules = rules_data.get("rules", [])
        source = rules_data.get("source_channel")
        
        if rules:
            await i.followup.send(
                f"✅ Reloaded! Extracted **{len(rules)}** rules from #{source}",
                ephemeral=True
            )
        else:
            await i.followup.send(
                f"⚠️ Reloaded but no rules found. Check #{source if source else 'the rules channel'}",
                ephemeral=True
            )


    @bot.tree.command(
        name="rules_enforcement",
        description="[Admin] Toggle automatic rule enforcement"
    )
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def rules_enforcement_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        _save(i.guild.id, "rules_enforcement", 1 if state.value == "on" else 0)
        
        await i.response.send_message(
            f"📜 Rule enforcement **{state.name}**",
            ephemeral=True
        )


    @bot.tree.command(
        name="test_rule_check",
        description="[Admin] Test if a message would violate rules"
    )
    @app_commands.describe(message="The message text to test")
    async def test_rule_check_cmd(i: discord.Interaction, message: str):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        result = await check_message_against_rules(message, i.user.display_name, i.guild)
        
        embed = discord.Embed(
            title="🧪 Rule Check Test",
            color=discord.Color.red() if result.get("violates") else discord.Color.green()
        )
        embed.add_field(name="Message", value=f"```{message[:500]}```", inline=False)
        embed.add_field(name="Violates?", value="YES ❌" if result.get("violates") else "NO ✅", inline=True)
        
        if result.get("violates"):
            embed.add_field(name="Rule", value=f"{result.get('rule_number', '?')}: {result.get('rule_title', 'Unknown')}", inline=True)
            embed.add_field(name="Severity", value=result.get("severity", "?"), inline=True)
            embed.add_field(name="Reason", value=result.get("reason", ""), inline=False)
            embed.add_field(name="Confidence", value=f"{result.get('confidence', 0):.0%}", inline=True)
        
        await i.followup.send(embed=embed, ephemeral=True)


# ============ LISTENER ============
def _register_listener(bot):
    @bot.listen("on_message")
    async def _rules_listener(message):
        try:
            if not _should_check_message(message):
                return
            
            # Check if enforcement is on
            if not _get_setting_int(message.guild.id, "rules_enforcement", 1):
                return
            
            # Skip trusted users
            if _is_trusted(message.author.id, message.guild.id):
                return
            
            # Skip mods/admins for now (or you can remove this if you want everyone checked)
            # Uncomment to skip admins:
            # if isinstance(message.author, discord.Member):
            #     if message.author.guild_permissions.administrator:
            #         return
            
            # Check message
            violation = await check_message_against_rules(
                message.content,
                message.author.display_name,
                message.guild
            )
            
            if violation.get("violates"):
                await enforce_rule_violation(message, violation)
        
        except Exception as e:
            print(f"[smart_rules] listener err: {e}")


# ============ BACKGROUND ============
def _register_tasks(bot):
    @tasks.loop(hours=6)
    async def _refresh_rules():
        """Periodically refresh rules cache for all servers."""
        for guild in bot.guilds:
            try:
                await load_and_extract_rules(guild, force_refresh=True)
                await asyncio.sleep(3)
            except: pass
    
    @tasks.loop(minutes=15)
    async def _cleanup_cooldowns():
        now = time.time()
        keys_to_delete = [k for k, ts in _violation_cooldown.items() if now - ts > 60]
        for k in keys_to_delete:
            del _violation_cooldown[k]
    
    if not _refresh_rules.is_running():
        _refresh_rules.start()
    if not _cleanup_cooldowns.is_running():
        _cleanup_cooldowns.start()


# ============ SETUP ============
def setup(bot):
    global _bot_ref, _is_setup
    if _is_setup:
        return
    _bot_ref = bot
    _is_setup = True
    
    _ensure_columns()
    _register_commands(bot)
    _register_listener(bot)
    _register_tasks(bot)
    
    print("[smart_rules] ✅ Loaded. AI reads rules from text/embeds/bots/pinned. Enforces automatically.")


# ============ AUTO HOOK ============
def _auto_hook():
    import sys
    for module_name, module in list(sys.modules.items()):
        if module is None:
            continue
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
    print("[smart_rules] ⚠️ Could not auto-hook. Add `import smart_rules` to bot.py.")

threading.Thread(target=_delayed_hook, daemon=True).start()
