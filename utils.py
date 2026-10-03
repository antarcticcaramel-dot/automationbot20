# utils.py
# ================================
# SentinelMod v9.0 — Utility Toolkit
# Shared helpers used everywhere via `from utils import *`:
#   • sanitize_bot_response  — bot output safety (no pings, never swears)
#   • parse_duration / format_duration / clamp_timeout
#   • chunk_text / truncate / human_list / progress_bar
#   • safe_send / safe_reply — never-crash Discord IO
#   • misc: hashes, channel-name cleaning, time helpers, config re-exports
# ================================

import re
import time
import random
import hashlib
import discord
from datetime import datetime, timedelta, timezone
from typing import Optional

# ---------- defensive config import (never hard-crash) ----------
try:
    import core_config as _core
except Exception:
    _core = None


def _cfg(name, default):
    try:
        return getattr(_core, name, default)
    except Exception:
        return default


BOT_IDENTITY: dict   = _cfg("BOT_IDENTITY", {"version": "9.0", "creator_discord_id": 0, "bot_id": 0})
MOD_ROLE_NAME: str   = _cfg("MOD_ROLE_NAME", "SentinelMod")
MOD_LOG_CHANNEL: str = _cfg("MOD_LOG_CHANNEL", "sentinel-logs")
RAID_CHANNEL: str    = _cfg("RAID_CHANNEL", "raid-alerts")
AI_CHAT_CHANNEL: str = _cfg("AI_CHAT_CHANNEL", "ai-chat")
PERSONALITIES        = _cfg("PERSONALITIES", {})


# ==================================================================
# OUTPUT SANITIZING — the bot never pings, never swears, never leaks
# ==================================================================

_PROFANITY = {
    "fuck", "fucking", "fuk", "fck", "shit", "bitch", "bastard", "asshole",
    "dick", "cock", "cunt", "motherfucker", "whore", "slut", "wanker",
    "twat", "bollocks", "prick", "pussy", "damn", "goddamn", "douche",
    "douchebag", "jackass", "ass",
}
_SEVERE = {
    "nigger", "nigga", "faggot", "kike", "tranny", "chink", "spic",
}

_SEVERE_RE = re.compile(r"\b(" + "|".join(sorted(_SEVERE, key=len, reverse=True)) + r")\b", re.I)
_PROF_RE = re.compile(r"\b(" + "|".join(sorted(_PROFANITY, key=len, reverse=True)) + r")\b", re.I)


def _censor_word(m: "re.Match") -> str:
    w = m.group(0)
    if len(w) <= 2:
        return "*" * len(w)
    return w[0] + "*" * (len(w) - 1)


def sanitize_bot_response(text: str, max_len: int = 1900) -> str:
    """Make any AI/text output safe to post as the bot."""
    if not text:
        return ""
    text = str(text)

    # 1) strip leading speaker labels models sometimes add
    text = re.sub(r"^\s*(?:sentinelmod|sentinel|bot|ai|assistant)\s*[:\-—>]+\s*", "", text, flags=re.I)

    # 2) unwrap if the whole response came back quoted
    s = text.strip()
    if s.startswith('"""') and s.endswith('"""') and len(s) > 6:
        text = s[3:-3].strip()
    elif s.startswith('"') and s.endswith('"') and len(s) > 2 and "\n" not in s:
        text = s[1:-1].strip()

    # 3) neutralize pings — @everyone/@here and raw mention markup
    text = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    text = re.sub(r"<(@|@!|@&|#)(\d+)>", lambda m: "<\u200b" + m.group(0)[1:], text)

    # 4) the bot NEVER swears — censor profanity
    text = _SEVERE_RE.sub("[censored]", text)
    text = _PROF_RE.sub(_censor_word, text)

    # 5) redact obvious prompt-leak lines
    text = re.sub(r"(?im)^\s*(system|developer|instructions|api[_ ]?key)\s*[:=\]].*$", "[redacted]", text)

    # 6) tidy whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # 7) hard length cap
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


# ==================================================================
# DURATION PARSING / FORMATTING
# ==================================================================

_UNIT_SECONDS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
    "mo": 2592000, "mon": 2592000, "month": 2592000, "months": 2592000,
    "y": 31536000, "yr": 31536000, "year": 31536000, "years": 31536000,
}
_FOREVER_WORDS = {"forever", "permanent", "perma", "indefinite", "infinite"}
_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "couple": 2, "few": 3, "dozen": 12, "half": 0.5,
}

MAX_TIMEOUT = timedelta(days=28)          # Discord hard limit
_PERMANENT = timedelta(days=36500)


def _resolve_unit(u: str) -> Optional[int]:
    if u in _UNIT_SECONDS:
        return _UNIT_SECONDS[u]
    if u.endswith("s") and u[:-1] in _UNIT_SECONDS:
        return _UNIT_SECONDS[u[:-1]]
    return None


def parse_duration(text, default_unit: Optional[str] = None) -> Optional[timedelta]:
    """
    Parse '7d', '2h30m', '1.5 hours', 'two weeks', 'forever' → timedelta.
    Bare numbers use default_unit ('m', 'h', 'd', …) if given, else None.
    """
    if text is None:
        return None
    raw = str(text).strip().lower()
    if not raw:
        return None
    if raw in _FOREVER_WORDS:
        return _PERMANENT

    tokens = re.findall(r"(\d+(?:\.\d+)?|[a-z]+)", raw)
    total, pending, found = 0.0, None, False
    for tok in tokens:
        if re.fullmatch(r"\d+(?:\.\d+)?", tok):
            pending = float(tok)
            continue
        if tok in _FOREVER_WORDS:
            return _PERMANENT
        if tok in _WORD_NUMBERS and pending is None:
            pending = float(_WORD_NUMBERS[tok])
            continue
        sec = _resolve_unit(tok)
        if sec and pending is not None:
            total += pending * sec
            pending, found = None, True

    if not found and pending is not None and default_unit:
        sec = _resolve_unit(default_unit)
        if sec:
            total += pending * sec
            found = True

    if not found and any(t in _FOREVER_WORDS for t in tokens):
        return _PERMANENT
    if found and total > 0:
        return timedelta(seconds=total)
    return None


def format_duration(td: Optional[timedelta]) -> str:
    if td is None:
        return "permanent"
    s = int(td.total_seconds())
    if s <= 0:
        return "0s"
    if s >= int(_PERMANENT.total_seconds()):
        return "permanent"
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    mins, s = divmod(s, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    if s and not days:
        parts.append(f"{s}s")
    return " ".join(parts) or "0s"


def clamp_timeout(td: Optional[timedelta]) -> Optional[timedelta]:
    """Clamp to Discord's 28-day timeout limit."""
    if td is None or td <= timedelta(0):
        return td
    return min(td, MAX_TIMEOUT)


# ==================================================================
# TEXT / FORMATTING HELPERS
# ==================================================================

def chunk_text(text: str, limit: int = 2000) -> list:
    """Split text into Discord-safe chunks, preferring line breaks."""
    text = str(text or "")
    out, cur = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if cur:
                out.append(cur)
                cur = ""
            out.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) > limit:
            out.append(cur)
            cur = line
        else:
            cur += line
    if cur:
        out.append(cur)
    return out or [""]


def truncate(text, limit: int = 100, suffix: str = "…") -> str:
    t = str(text or "")
    if len(t) <= limit:
        return t
    return t[: max(0, limit - len(suffix))].rstrip() + suffix


def human_list(items, bold: bool = False) -> str:
    vals = [f"**{i}**" if bold else str(i) for i in items]
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    return ", ".join(vals[:-1]) + " and " + vals[-1]


def progress_bar(cur, mx, size: int = 10, full: str = "█", empty: str = "░") -> str:
    try:
        cur, mx = float(cur), float(mx)
        ratio = 0.0 if mx <= 0 else max(0.0, min(1.0, cur / mx))
    except Exception:
        ratio = 0.0
    filled = round(ratio * size)
    return full * filled + empty * (size - filled)


def pct(x, nd: int = 0) -> str:
    try:
        return f"{float(x) * 100:.{nd}f}%"
    except Exception:
        return "0%"


def clamp(n, lo, hi):
    try:
        return max(lo, min(hi, n))
    except Exception:
        return n


def pick(seq, default=None):
    try:
        return random.choice(list(seq))
    except Exception:
        return default


def safe_channel_name(name: str) -> str:
    name = re.sub(r"[^\w\-/]+", "-", str(name).strip().lower()).strip("-")
    name = re.sub(r"-{2,}", "-", name)
    return (name or "channel")[:90]


def extract_user_id(text) -> Optional[int]:
    if text is None:
        return None
    s = str(text).strip()
    m = re.search(r"<@!?(\d+)>", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return None


def short_hash(text, n: int = 10) -> str:
    return hashlib.sha1(str(text).encode("utf-8", "ignore")).hexdigest()[:n]


def parse_bool(v, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "on", "y", "enable", "enabled"}:
        return True
    if s in {"0", "false", "no", "off", "n", "disable", "disabled"}:
        return False
    return default


# ==================================================================
# TIME HELPERS
# ==================================================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return datetime.now().isoformat()


def ago(ts) -> str:
    try:
        d = max(0.0, time.time() - float(ts))
    except Exception:
        return "?"
    if d < 60:
        return f"{int(d)}s ago"
    if d < 3600:
        return f"{int(d // 60)}m ago"
    if d < 86400:
        return f"{int(d // 3600)}h ago"
    return f"{int(d // 86400)}d ago"


def account_age_days(member) -> int:
    try:
        return max(0, (now_utc() - member.created_at).days)
    except Exception:
        return 0


# ==================================================================
# SAFE DISCORD IO — never raises
# ==================================================================

async def safe_send(dest, content=None, **kwargs):
    try:
        return await dest.send(content=content, **kwargs)
    except discord.Forbidden:
        return None
    except discord.HTTPException:
        return None
    except Exception:
        return None


async def safe_reply(message, content=None, **kwargs):
    try:
        return await message.reply(content=content, **kwargs)
    except Exception:
        return None


def make_embed(title=None, description=None, color=0x5865F2, **kw) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color, **kw)
    e.set_footer(text=f"SentinelMod v{BOT_IDENTITY.get('version', '9.0')}")
    return e


__all__ = [
    "BOT_IDENTITY", "MOD_ROLE_NAME", "MOD_LOG_CHANNEL", "RAID_CHANNEL",
    "AI_CHAT_CHANNEL", "PERSONALITIES",
    "sanitize_bot_response", "parse_duration", "format_duration", "clamp_timeout",
    "MAX_TIMEOUT", "chunk_text", "truncate", "human_list", "progress_bar",
    "pct", "clamp", "pick", "safe_channel_name", "extract_user_id",
    "short_hash", "parse_bool", "now_utc", "iso_now", "ago", "account_age_days",
    "safe_send", "safe_reply", "make_embed",
]
