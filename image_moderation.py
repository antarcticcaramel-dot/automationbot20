# image_moderation.py
# ================================
# SentinelMod AI Image Moderation
# EVERYONE gets moderated except manually trusted users.
# Strong scam/crypto/phishing screenshot detection.
# Logs ONLY to sentinel-logs channel. No owner DMs.
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

# ============ STRONG SCAM TEXT DETECTION ============
SCAM_TEXT_PATTERNS = [
    r"(?i)\bmrbeast\b.{0,120}\b(crypto|bitcoin|btc|eth|ethereum|usdt|tether|giveaway|promo|bonus|withdraw|claim|airdrop)\b",
    r"(?i)\belon\s*musk\b.{0,120}\b(crypto|bitcoin|btc|eth|ethereum|usdt|tether|giveaway|promo|bonus|withdraw|claim|airdrop)\b",
    r"(?i)\bwithdrawal\s+(success|successful|complete|completed)\b",
    r"(?i)\b(your\s+)?withdrawal\s+of\s+\$?\d[\d,\.]*\s*(usdt|btc|eth|usd|tether|bitcoin|ethereum)?\b",
    r"(?i)\b\d[\d,\.]*\s*(usdt|btc|eth|tether|bitcoin|ethereum)\b.{0,80}\b(withdraw|success|bonus|claim|promo|gift)\b",
    r"(?i)\b(promo\s*code|bonus\s*code|enter\s+code|special\s+code)\b",
    r"(?i)\b(free|claim|get|win|won)\s+\$?\d[\d,\.]*\b.{0,80}\b(crypto|usdt|btc|eth|tether|bonus|withdraw)\b",
    r"(?i)\b(congratulations|congrats)\b.{0,80}\b(won|selected|reward|bonus|prize)\b",
    r"(?i)\b(risk[-\s]?free|guaranteed\s+profit|easy\s+money|double\s+your|multiply\s+your)\b",
    r"(?i)\b(fake\s+nitro|free\s+nitro|discord\s+nitro\s+gift|steam\s+gift|airdrop)\b",
    r"(?i)\b(connect\s+wallet|wallet\s+address|seed\s+phrase|recovery\s+phrase)\b",
    r"(?i)\b(buzawin|stakebonus|cryptobonus|nitroclaim|discordgift|steamgift)\b",
    r"(?i)\b(bit\.ly|tinyurl|grabify|iplogger|discordgift|discord-nitro|free-nitro)\b",
]

def scam_text_override(result: dict) -> dict:
    """Force scam flag if obvious scam text is detected."""
    combined = " ".join([
        str(result.get("detected_text", "")),
        str(result.get("explanation", "")),
        str(result.get("reason", "")),
        " ".join(result.get("categories", []) if isinstance(result.get("categories"), list) else []),
    ])

    if not combined.strip():
        return result

    for pattern in SCAM_TEXT_PATTERNS:
        if re.search(pattern, combined):
            result["safe"] = False
            cats = result.get("categories", [])
            if not isinstance(cats, list):
                cats = []
            for cat in ["scam", "crypto_scam", "phishing"]:
                if cat not in cats:
                    cats.append(cat)
            result["categories"] = cats
            result["severity"] = "critical"
            result["action"] = "delete_warn"
            result["confidence"] = max(float(result.get("confidence", 0.0) or 0.0), 0.92)
            if not result.get("reason") or result.get("reason") == "Inappropriate image":
                result["reason"] = "Obvious crypto/phishing scam screenshot"
            return result

    return result


# ============ VISION AI ============
async def analyze_with_groq_vision(image_url: str, prompt: str) -> dict | None:
    if not GROQ_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    models = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
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
            "temperature": 0.05,
            "max_tokens": 800,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=35)
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
            print(f"[image_mod] Groq vision {model} err: {e}")
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
        "qwen/qwen2.5-vl-72b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
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
            "temperature": 0.05,
            "max_tokens": 800,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=35)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result_text = data["choices"][0]["message"]["content"]

                        try:
                            return json.loads(result_text)
                        except:
                            match = re.search(r'\{.*\}', result_text, re.DOTALL)
                            if match:
                                try:
                                    return json.loads(match.group())
                                except:
                                    pass

                    elif resp.status == 429:
                        await asyncio.sleep(2)

        except Exception as e:
            print(f"[image_mod] OpenRouter vision {model} err: {e}")
            continue

    return None

async def ai_scan_image(image_url: str) -> dict:
    """Use AI vision to scan an image for scams, NSFW, violence, etc."""
    if not GROQ_API_KEY:
        return {"is_bad": False, "reason": "AI unavailable"}
    
    try:
        # Use Groq's vision model (llama 3.2 vision)
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        prompt = """Analyze this image for Discord moderation.

Flag if it contains ANY of these:
- Scams (fake crypto, fake giveaways, fake login pages, fake withdrawals)
- Phishing screenshots
- NSFW/pornographic content
- Gore or graphic violence
- Hate symbols or extremist content
- Doxxing (personal info like addresses, phones, IDs)
- Fake Discord Nitro / free money offers
- Malicious QR codes

Return JSON ONLY:
{
  "is_bad": true/false,
  "category": "scam|nsfw|violence|hate|doxxing|phishing|safe",
  "reason": "brief explanation",
  "severity": "low|medium|high|critical",
  "confidence": 0.0-1.0
}

Be strict on scams and NSFW. If it looks like a fake crypto withdrawal or "free money" screenshot, flag as scam."""

        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        try:
                            result = json.loads(match.group())
                            if result.get("confidence", 0) < 0.6:
                                result["is_bad"] = False
                            return result
                        except: pass
                else:
                    # Fallback to smaller vision model
                    payload["model"] = "llama-3.2-11b-vision-preview"
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp2:
                        if resp2.status == 200:
                            data = await resp2.json()
                            text = data["choices"][0]["message"]["content"].strip()
                            text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
                            match = re.search(r'\{.*\}', text, re.DOTALL)
                            if match:
                                try:
                                    result = json.loads(match.group())
                                    if result.get("confidence", 0) < 0.6:
                                        result["is_bad"] = False
                                    return result
                                except: pass
    except Exception as e:
        print(f"AI image scan err: {e}")
    
    return {"is_bad": False, "reason": "Scan failed"}async def ai_scan_image(image_url: str) -> dict:
    """Use AI vision to scan an image for scams, NSFW, violence, etc."""
    if not GROQ_API_KEY:
        return {"is_bad": False, "reason": "AI unavailable"}
    
    try:
        # Use Groq's vision model (llama 3.2 vision)
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        prompt = """Analyze this image for Discord moderation.

Flag if it contains ANY of these:
- Scams (fake crypto, fake giveaways, fake login pages, fake withdrawals)
- Phishing screenshots
- NSFW/pornographic content
- Gore or graphic violence
- Hate symbols or extremist content
- Doxxing (personal info like addresses, phones, IDs)
- Fake Discord Nitro / free money offers
- Malicious QR codes

Return JSON ONLY:
{
  "is_bad": true/false,
  "category": "scam|nsfw|violence|hate|doxxing|phishing|safe",
  "reason": "brief explanation",
  "severity": "low|medium|high|critical",
  "confidence": 0.0-1.0
}

Be strict on scams and NSFW. If it looks like a fake crypto withdrawal or "free money" screenshot, flag as scam."""

        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        try:
                            result = json.loads(match.group())
                            if result.get("confidence", 0) < 0.6:
                                result["is_bad"] = False
                            return result
                        except: pass
                else:
                    # Fallback to smaller vision model
                    payload["model"] = "llama-3.2-11b-vision-preview"
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp2:
                        if resp2.status == 200:
                            data = await resp2.json()
                            text = data["choices"][0]["message"]["content"].strip()
                            text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
                            match = re.search(r'\{.*\}', text, re.DOTALL)
                            if match:
                                try:
                                    result = json.loads(match.group())
                                    if result.get("confidence", 0) < 0.6:
                                        result["is_bad"] = False
                                    return result
                                except: pass
    except Exception as e:
        print(f"AI image scan err: {e}")
    
    return {"is_bad": False, "reason": "Scan failed"}


MODERATION_PROMPT = """You are an EXTREMELY STRICT Discord image moderator specializing in SCAM DETECTION.

Your job is to look at the image, read ALL visible text, and decide if it should be removed from a Discord server.

FLAG THESE SCAMS IMMEDIATELY AS:
safe=false, severity="critical", action="delete_warn", categories include "scam" and usually "crypto_scam" or "phishing".

CRYPTO / MONEY / CELEBRITY SCAMS:
- Fake celebrity crypto promos, especially MrBeast, Elon Musk, streamers, YouTubers, influencers
- Fake X/Twitter screenshots from celebrities offering crypto, money, tokens, bonuses, or giveaways
- Any image saying someone is giving away money, crypto, BTC, ETH, USDT, Tether, Bitcoin, Ethereum
- Any image showing "Withdrawal Success", "Withdrawal Successful", "Successfully Withdrawn"
- Any image showing huge fake crypto balances or winnings
- Any image showing $500, $1000, $5000, $5600, or similar winnings/withdrawals
- Any fake casino/betting/crypto platform showing bonuses or successful payout
- Any "promo code", "bonus code", "enter code", "claim reward", "claim bonus"
- Any fake trading profits or fake investment screenshots
- Any crypto wallet address, QR code, wallet connect, seed phrase, recovery phrase
- Any suspicious domain connected to money/crypto/giveaways
- Any screenshot trying to prove "this is real" with a withdrawal or phone balance

SPECIFIC EXAMPLES THAT MUST BE FLAGGED:
- MrBeast screenshot promoting crypto or a website
- Fake tweet saying "I am giving away $X to people who register"
- "Withdrawal Success! Your withdrawal of $5600 USDT was successfully..."
- A phone showing USDT received beside a website withdrawal success popup
- Crypto/casino website with VIP/bonus and withdrawal amount
- Anything involving buzawin.com or similar sketchy gambling/crypto site
- Fake Coinbase/Binance/crypto exchange screenshots
- "Enter promo code BEAST" or any creator promo code for money/crypto
- "Risk free", "guaranteed profit", "easy money", "double your money"

PHISHING / MALICIOUS:
- Fake Discord Nitro pages
- Fake Steam/Roblox/PayPal login or gift pages
- Suspicious QR codes
- Shortened links like bit.ly/tinyurl in a suspicious promo image
- IP grabbers or token grabbers
- Fake Discord staff/mod/admin messages

OTHER BAD CONTENT:
- NSFW or sexual content in non-NSFW channels
- CSAM / sexualized minors = severity "ban", action "delete_ban", categories include "csam"
- Gore, dead bodies, extreme blood/injuries
- Hate symbols or extremist imagery
- Doxxing: addresses, IDs, credit cards, SSNs, private information
- Self-harm imagery
- Illegal drug sales
- Shock/disgust content
- Server invite spam or advertisement images

IMPORTANT:
- Be STRICT with scam screenshots.
- Read all text in the image carefully.
- Real users almost never post legitimate "Withdrawal Success $5600 USDT" screenshots in random Discord servers.
- Do NOT let scams pass just because it is a screenshot of Twitter/X.
- If the image is a meme, gaming screenshot, normal selfie, normal art, or normal conversation screenshot with no scam/NSFW/harmful content, mark safe=true.

RETURN JSON ONLY:
{
  "safe": true/false,
  "categories": ["nsfw", "gore", "scam", "phishing", "crypto_scam", "impersonation", "fake_giveaway", "weapons", "drugs", "hate", "self_harm", "doxxing", "malicious_link", "shock", "illegal", "spam", "csam"],
  "severity": "none|low|medium|high|critical|ban",
  "confidence": 0.0-1.0,
  "action": "ignore|flag|delete|delete_warn|delete_ban",
  "reason": "specific short explanation",
  "detected_text": "all important visible text you can read",
  "explanation": "briefly describe what the image shows"
}

SEVERITY GUIDE:
- ban = CSAM only
- critical = crypto scams, phishing, fake giveaways, doxxing, clear NSFW, gore
- high = hate symbols, weapons threateningly displayed, strong sexual suggestion
- medium = spam ads, mild inappropriate content
- low = borderline suspicious
- none = clearly safe

For crypto scams, fake withdrawals, celebrity giveaways, fake money rewards:
confidence should usually be 0.85 or higher."""


async def analyze_image(image_url: str, channel_is_nsfw: bool = False) -> dict:
    cache_key = hashlib.md5(image_url.encode()).hexdigest()

    if cache_key in _image_cache:
        cached, ts = _image_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached

    prompt = MODERATION_PROMPT

    if channel_is_nsfw:
        prompt += """
        
NOTE: This is an NSFW channel. Adult content may be allowed, BUT still flag:
- CSAM
- scams
- phishing
- crypto scams
- doxxing
- gore
- hate
- malicious links
- illegal content
"""

    result = await analyze_with_groq_vision(image_url, prompt)

    if not result:
        result = await analyze_with_openrouter_vision(image_url, prompt)

    if not result:
        return {
            "safe": True,
            "categories": [],
            "severity": "none",
            "confidence": 0.0,
            "action": "ignore",
            "reason": "AI unavailable",
            "detected_text": "",
            "explanation": "Could not analyze"
        }

    normalized = {
        "safe": bool(result.get("safe", True)),
        "categories": result.get("categories", []) if isinstance(result.get("categories", []), list) else [],
        "severity": str(result.get("severity", "none")).lower(),
        "confidence": float(result.get("confidence", 0.0) or 0.0),
        "action": str(result.get("action", "ignore")).lower(),
        "reason": str(result.get("reason", ""))[:300],
        "detected_text": str(result.get("detected_text", ""))[:1500],
        "explanation": str(result.get("explanation", ""))[:1000],
    }

    normalized = scam_text_override(normalized)

    _image_cache[cache_key] = (normalized, time.time())

    if len(_image_cache) > 500:
        oldest = min(_image_cache.keys(), key=lambda k: _image_cache[k][1])
        del _image_cache[oldest]

    return normalized


# ============ URL EXTRACTION ============
def extract_image_urls(message) -> list[str]:
    urls = []

    for attachment in message.attachments:
        try:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                urls.append(attachment.url)
            elif attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                urls.append(attachment.url)
        except:
            pass

    for embed in message.embeds:
        try:
            if embed.image and embed.image.url:
                urls.append(embed.image.url)
            if embed.thumbnail and embed.thumbnail.url:
                urls.append(embed.thumbnail.url)
        except:
            pass

    url_pattern = r'https?://\S+\.(?:png|jpg|jpeg|gif|webp|bmp)(?:\?\S*)?'
    for match in re.finditer(url_pattern, message.content or "", re.IGNORECASE):
        urls.append(match.group())

    host_patterns = [
        r'https?://cdn\.discordapp\.com/attachments/\S+',
        r'https?://media\.discordapp\.net/attachments/\S+',
        r'https?://(?:i\.)?imgur\.com/\S+',
    ]
    for pattern in host_patterns:
        for match in re.finditer(pattern, message.content or "", re.IGNORECASE):
            urls.append(match.group())

    return list(dict.fromkeys(urls))


def message_might_have_image(message) -> bool:
    if message.attachments:
        return True
    if message.embeds:
        for e in message.embeds:
            try:
                if e.image or e.thumbnail:
                    return True
            except:
                pass
    if re.search(r'https?://\S+\.(?:png|jpg|jpeg|gif|webp|bmp)', message.content or "", re.IGNORECASE):
        return True
    if re.search(r'https?://(cdn|media)\.discordapp\.(com|net)/attachments/\S+', message.content or "", re.IGNORECASE):
        return True
    return False


def check_image_spam(user_id: int, guild_id: int, num_images: int = 1) -> bool:
    key = f"{guild_id}:{user_id}"
    now = time.time()
    _user_image_tracker[key] = [t for t in _user_image_tracker[key] if now - t < 60]
    _user_image_tracker[key].extend([now] * num_images)
    return len(_user_image_tracker[key]) >= 10


# ============ DB HELPERS ============
_bot_ref = None
_is_setup = False

def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column():
    try:
        conn = _get_db()
        c = conn.cursor()
        try:
            c.execute("ALTER TABLE guild_settings ADD COLUMN image_moderation INTEGER DEFAULT 1")
            conn.commit()
            print("[image_mod] Added image_moderation column")
        except sqlite3.OperationalError:
            pass
        conn.close()
    except Exception as e:
        print(f"[image_mod] ensure column err: {e}")


def _get_setting(guild_id):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT image_moderation FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        row = c.fetchone()
        conn.close()

        if row is None:
            return True

        return bool(row["image_moderation"])

    except sqlite3.OperationalError:
        _ensure_column()
        return True
    except:
        return True


def _set_setting(guild_id, value):
    try:
        _ensure_column()
        conn = _get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(guild_id),))
        c.execute("UPDATE guild_settings SET image_moderation=? WHERE guild_id=?", (int(value), str(guild_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[image_mod] set setting err: {e}")


def _is_trusted(user_id, guild_id):
    """ONLY trusted users are exempt."""
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute("SELECT 1 FROM trusted_users WHERE user_id=? AND guild_id=?", (str(user_id), str(guild_id)))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False


def _add_warning(uid, gid, reason, severity, confidence=1.0, context=""):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO warnings (user_id,guild_id,reason,severity,ai_confidence,context,timestamp) VALUES (?,?,?,?,?,?,?)",
            (str(uid), str(gid), reason, severity, confidence, context[:500], datetime.now().isoformat())
        )
        conn.commit()
        c.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?", (str(uid), str(gid)))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[image_mod] warning add err: {e}")
        return 0


def _log_action(uid, gid, action, reason):
    try:
        conn = _get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO mod_actions (user_id,guild_id,action,reason,mod_id,timestamp) VALUES (?,?,?,?,?,?)",
            (
                str(uid),
                str(gid),
                action,
                reason[:500],
                str(_bot_ref.user.id) if _bot_ref and _bot_ref.user else "bot",
                datetime.now().isoformat()
            )
        )
        conn.commit()
        conn.close()
    except:
        pass


async def _alert_mods(guild, embed):
    """Send to sentinel-logs or similar. NO owner DMs."""
    for ch_name in ["sentinel-logs", "mod-logs", "logs", "audit-log"]:
        ch = discord.utils.get(guild.text_channels, name=ch_name)
        if ch:
            try:
                await ch.send(embed=embed)
                return
            except discord.HTTPException as e:
                if e.status == 429:
                    await asyncio.sleep(getattr(e, "retry_after", 5) + 1)
            except:
                pass


def _can_punish(member, guild):
    try:
        if not guild.me:
            return False
        if member.id == guild.owner_id:
            return False
        if hasattr(member, "top_role") and member.top_role >= guild.me.top_role:
            return False
        return True
    except:
        return False


# ============ MAIN MODERATION ============
async def _moderate_images(message):
    if not message.guild:
        return False

    if _bot_ref and _bot_ref.user and message.author.id == _bot_ref.user.id:
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

    # Image spam
    if check_image_spam(author.id, guild.id, len(image_urls)):
        try:
            await message.delete()
        except:
            pass

        can_punish = isinstance(author, discord.Member) and _can_punish(author, guild)
        if can_punish:
            try:
                await author.timeout(datetime.now() + timedelta(minutes=10), reason="Image spam")
            except:
                pass

        try:
            await message.channel.send(f"{author.mention} slow down with the images!", delete_after=5)
        except:
            pass

        _log_action(author.id, guild.id, "IMAGE SPAM", "User sent too many images quickly")
        return True

    channel_is_nsfw = False
    try:
        channel_is_nsfw = message.channel.is_nsfw()
    except:
        pass

    worst_result = None
    worst_score = 0

    severity_scores = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
        "ban": 5
    }

    for url in image_urls[:5]:
        try:
            result = await asyncio.wait_for(analyze_image(url, channel_is_nsfw), timeout=35.0)

            print("[IMAGE MOD RESULT]")
            print(f"User: {author} | Guild: {guild.name}")
            print(f"Safe: {result.get('safe')}")
            print(f"Severity: {result.get('severity')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"Categories: {result.get('categories')}")
            print(f"Reason: {result.get('reason')}")
            print(f"Text: {str(result.get('detected_text',''))[:250]}")

            score = severity_scores.get(str(result.get("severity", "none")).lower(), 0)

            if score > worst_score:
                worst_score = score
                worst_result = result

        except asyncio.TimeoutError:
            print("[image_mod] Image analysis timeout")
            continue
        except Exception as e:
            print(f"[image_mod] Image analysis err: {e}")
            continue

    if not worst_result:
        return False

    worst_result = scam_text_override(worst_result)

    if worst_result.get("safe", True):
        return False

    severity = str(worst_result.get("severity", "none")).lower()
    confidence = float(worst_result.get("confidence", 0.0) or 0.0)
    reason = worst_result.get("reason", "Inappropriate image") or "Inappropriate image"
    categories = worst_result.get("categories", [])
    if not isinstance(categories, list):
        categories = []

    scam_categories = ["scam", "phishing", "crypto_scam", "fake_giveaway", "impersonation", "malicious_link"]
    is_scam = any(cat in categories for cat in scam_categories)

    if is_scam:
        if confidence < 0.45:
            return False
    elif confidence < 0.60 and severity not in ["critical", "ban"]:
        return False

    cat_str = ", ".join(categories) if categories else "content"
    detected_text = str(worst_result.get("detected_text", ""))[:500]
    explanation = str(worst_result.get("explanation", ""))[:500]
    full_reason = f"Image: {cat_str} - {reason}"

    can_punish = isinstance(author, discord.Member) and _can_punish(author, guild)

    # ============ BAN LEVEL ============
    if severity == "ban" or "csam" in categories:
        try:
            await message.delete()
        except:
            pass

        banned = False

        if can_punish:
            try:
                await guild.ban(author, reason=f"CRITICAL IMAGE: {full_reason}", delete_message_days=1)
                banned = True
            except:
                pass

        _log_action(
            author.id,
            guild.id,
            "AUTO-BAN IMAGE" if banned else "CRITICAL IMAGE CANNOT BAN",
            full_reason
        )

        embed = discord.Embed(
            title="🚨 Critical Image Violation" + (" - Banned" if banned else " - Could Not Ban"),
            description=f"**{author}** posted forbidden image content.",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="User", value=getattr(author, "mention", str(author)), inline=True)
        embed.add_field(name="Banned?", value="YES" if banned else "NO", inline=True)
        embed.add_field(name="Categories", value=cat_str[:1000], inline=False)
        embed.add_field(name="Reason", value=reason[:1000], inline=False)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
        if detected_text:
            embed.add_field(name="Detected Text", value=detected_text[:1000], inline=False)
        if explanation:
            embed.add_field(name="Explanation", value=explanation[:1000], inline=False)

        await _alert_mods(guild, embed)
        return True

    # ============ CRITICAL / HIGH ============
    if severity in ["critical", "high"]:
        try:
            await message.delete()
        except:
            pass

        wc = _add_warning(author.id, guild.id, full_reason, severity, confidence, detected_text)
        _log_action(author.id, guild.id, "AUTO-DELETE IMAGE", full_reason)

        muted = False
        if can_punish:
            mute_dur = 60 if severity == "critical" else 30
            try:
                await author.timeout(datetime.now() + timedelta(minutes=mute_dur), reason=full_reason)
                muted = True
            except:
                pass

        try:
            await message.channel.send(
                f"{author.mention} That image was removed: **{reason}** | Warning #{wc}",
                delete_after=5
            )
        except:
            pass

        embed = discord.Embed(
            title=f"🖼️ Image Removed - {severity.upper()}",
            color=discord.Color.red() if severity == "critical" else discord.Color.orange()
        )
        embed.add_field(name="User", value=getattr(author, "mention", str(author)), inline=True)
        embed.add_field(name="Muted?", value="YES" if muted else "NO", inline=True)
        embed.add_field(name="Warning #", value=str(wc), inline=True)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
        embed.add_field(name="Categories", value=cat_str[:1000], inline=False)
        embed.add_field(name="Reason", value=reason[:1000], inline=False)

        if detected_text:
            embed.add_field(name="Detected Text", value=detected_text[:1000], inline=False)
        if explanation:
            embed.add_field(name="Explanation", value=explanation[:1000], inline=False)

        await _alert_mods(guild, embed)
        return True

    # ============ MEDIUM ============
    if severity == "medium":
        try:
            await message.delete()
        except:
            pass

        wc = _add_warning(author.id, guild.id, full_reason, severity, confidence, detected_text)
        _log_action(author.id, guild.id, "DELETE IMAGE MEDIUM", full_reason)

        try:
            await message.channel.send(
                f"{author.mention} Please don't post that here: **{reason}**",
                delete_after=5
            )
        except:
            pass

        embed = discord.Embed(
            title="🖼️ Image Removed - MEDIUM",
            color=discord.Color.orange()
        )
        embed.add_field(name="User", value=getattr(author, "mention", str(author)), inline=True)
        embed.add_field(name="Warning #", value=str(wc), inline=True)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
        embed.add_field(name="Categories", value=cat_str[:1000], inline=False)
        embed.add_field(name="Reason", value=reason[:1000], inline=False)
        if detected_text:
            embed.add_field(name="Detected Text", value=detected_text[:1000], inline=False)

        await _alert_mods(guild, embed)
        return True

    # ============ LOW ============
    if severity == "low":
        try:
            await message.delete()
        except:
            pass

        _log_action(author.id, guild.id, "DELETE IMAGE LOW", full_reason)

        try:
            await message.channel.send(
                f"{author.mention} That image isn't appropriate here.",
                delete_after=5
            )
        except:
            pass

        return True

    return False


# ============ AUTO SETUP ============
def setup(bot):
    global _bot_ref, _is_setup

    if _is_setup:
        return

    _bot_ref = bot
    _is_setup = True

    _ensure_column()

    @bot.listen("on_message")
    async def _image_mod_listener(message):
        try:
            if not message.guild:
                return

            if _bot_ref and _bot_ref.user and message.author.id == _bot_ref.user.id:
                return

            if not message_might_have_image(message):
                return

            await _moderate_images(message)

        except Exception as e:
            print(f"[image_mod] listener err: {e}")

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

    print("[image_mod] ✅ Loaded. Logs only to sentinel-logs. No owner DMs.")


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


import threading

def _delayed_hook():
    import time as _time

    for attempt in range(30):
        _time.sleep(1)
        try:
            if _auto_hook():
                return
        except:
            pass

    print("[image_mod] ⚠️ Could not auto-hook. Add `import image_moderation` to bot.py.")

threading.Thread(target=_delayed_hook, daemon=True).start()
