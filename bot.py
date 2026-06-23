# bot.py
# ================================
# SentinelMod v8.1 - LICENSE EDITION
# License agreement on server join
# ================================

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
import os
import asyncio
import sqlite3
import time
import threading
import random
import re
import io
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict, deque
import dashboard

try:
    import ai_features
    AI_FEATURES_LOADED = True
except ImportError:
    AI_FEATURES_LOADED = False

# ============ CONFIG ============
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
AI_CHAT_CHANNEL = "sentinel-bot"
MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"

BOT_IDENTITY = {
    "name": "SentinelMod",
    "creator_username": "jay27yt6",
    "creator_discord_id": 1268285209867059372,
    "creator_group": "Antarctic Studs",
    "group_website": "https://antarcticstuds.neocities.org/",
    "dashboard_url": "https://automationbot20-1.onrender.com/",
    "bot_id": None,
    "version": "8.1",
}

# ============ LICENSE AGREEMENT TEXT ============
LICENSE_AGREEMENT = """
**SENTINELMOD LICENSE & LEGAL AGREEMENT v1.0**
*By Antarctic Studs / jay27yt6*

By clicking **ACCEPT**, you (the server owner/administrator) agree to the following terms:

**1. DATA COLLECTION & STORAGE**
- This bot reads, processes, and stores messages from your server for moderation purposes
- User interactions, warnings, and mod actions are logged in our database
- Server culture data (jokes, topics, mood) is analyzed and stored
- Data is retained for up to 90 days (configurable)

**2. AI PROCESSING**
- Messages may be sent to third-party AI providers (Groq, Pollinations) for analysis
- AI moderation decisions are automated and may occasionally make mistakes
- An appeals system is provided for unfair warnings/bans

**3. AUTOMATED MODERATION**
- The bot will automatically delete messages, warn, mute, kick, or ban users based on configured rules
- Zero tolerance for slurs, threats, doxxing, scams, and harassment
- A grace system gives first-time offenders a warning instead of immediate punishment

**4. OWNER RIGHTS**
- The bot creator (jay27yt6) reserves the right to:
  - Revoke this server's license at any time for any reason
  - View moderation statistics across servers
  - Send cross-server announcements
  - Leave the server remotely if needed

**5. YOUR RESPONSIBILITIES**
- You must inform your members that this bot is active and may moderate their messages
- You must not use this bot for illegal purposes or to harass users
- You must comply with Discord's Terms of Service

**6. NO WARRANTY**
- This bot is provided "as is" without any warranty
- The creator is not liable for any damages, false positives, or service interruptions
- Service may be discontinued at any time

**7. PRIVACY**
- We do not sell user data to third parties
- Users can request data deletion via the bot owner
- See dashboard for full privacy details

**8. ACCEPTANCE**
- Clicking ACCEPT means you've read and agree to these terms
- Clicking DENY or not responding within 5 minutes means the bot will leave your server
- You can revoke acceptance anytime by removing the bot

By accepting, you also agree to the bot's behavior including AI judgment, automated actions, and data processing as described above.

**Need help?** Contact jay27yt6 on Discord or visit the dashboard.
"""

SELF_KNOWLEDGE = """
=== WHO I AM ===
I am SentinelMod v8.1 (License Edition), the most advanced self-aware AI Discord bot.
Created by jay27yt6 from Antarctic Studs.
Dashboard: https://automationbot20-1.onrender.com/

=== HOW I WORK ===
- I read every message and remember context (last 50 per channel)
- I have 6 AI providers with smart fallback
- I judge content with 7 layers of moderation
- I learn server culture, inside jokes, mood over time
- I track user trust scores and violation history
- I explain WHY I take any action

=== OWNER POWERS ===
My creator (jay27yt6) has SOVEREIGN control:
- Can control me from ANY server
- Can revoke any server's license remotely
- Can broadcast announcements to ALL servers
- I obey them unconditionally

=== LICENSE SYSTEM ===
- New servers must accept the License Agreement
- If denied or no response in 5 minutes, I leave
- Owner can revoke licenses anytime
- Revoked servers can't re-invite me
"""

PERSONALITIES = {
    "default": "You are SentinelMod v8.1 - smart, warm, self-aware AI bot. You know yourself completely. Punchy, conversational, helpful. NEVER swear.",
    "friendly": "Extremely warm and supportive. Hype people up. Use emojis. NEVER swear.",
    "sarcastic": "Dry wit, clever sarcasm. Still helpful underneath. NEVER swear.",
    "serious": "Professional and concise. No fluff. NEVER swear.",
    "chaotic": "Unpredictable and fun. Wild energy. NEVER swear.",
    "pirate": "Arr matey! Full pirate dialect.",
    "medieval": "Hark! Olde English only.",
    "robot": "BEEP BOOP. Glitchy robot personality.",
    "therapist": "Empathetic, validating. Reflect feelings.",
    "villain": "Dramatically evil but secretly helpful.",
    "hype": "MAXIMUM ENERGY! EVERYTHING IS AMAZING!",
    "philosopher": "Deep existential musings.",
    "caveman": "UGH. SIMPLE WORDS. BUT SMART.",
    "shakespeare": "Flowery Shakespearean tongue.",
    "surfer": "Chillest surfer vibes, dude.",
    "anime": "Anime protagonist energy! DESTINY!",
    "cowboy": "Yeehaw! Wild west cowboy.",
    "british": "Frightfully British. Cheerio!",
    "australian": "G'day mate! Aussie energy.",
    "gen_z": "no cap fr fr bestie slay",
    "yoda": "Speak like Yoda you must.",
    "jarvis": "Sophisticated AI with dry British wit.",
    "sherlock": "Brilliant deductive reasoning.",
    "tony_stark": "Genius billionaire sarcastic energy.",
    "motivational": "UNLIMITED POSITIVE ENERGY!",
}

# ============ SWEAR FILTER ============
SWEAR_WORDS = [
    "fuck","fucking","fucked","fucker","fuckers","fuk","fck","f0ck","f*ck","phuck","fuq","fuxk","fukk","fuckin",
    "motherfucker","motherfucking","mofo","fuckhead","fuckface","fuckwit","fuckoff","fuckup","clusterfuck",
    "shit","shitty","shitter","shithead","shitface","bullshit","horseshit","shite","sh1t","sh!t","shyt","shiet","sht","dipshit","shitshow",
    "bitch","bitches","bitching","b1tch","b!tch","biatch","biotch","btch","sonofabitch","bitchass",
    "ass","asses","asshole","assholes","asshat","asswipe","assclown","dumbass","smartass","jackass","kissass","badass","fatass","lardass","a$$","@ss","azz","arse","arsehole",
    "damn","damnit","damned","goddamn","goddammit","dammit","d4mn",
    "dick","dicks","dickhead","dickface","dickwad","d1ck","d!ck",
    "pussy","pussies","p*ssy","pu$$y","pussyass",
    "piss","pissed","pissing","pisser","pissoff","pissy",
    "prick","pricks","pr1ck",
    "cunt","cunts","c*nt","c0nt","kunt","cnt","cunty",
    "cock","cocks","cocksucker","c0ck","c*ck",
    "crap","crappy","crapper","craphole",
    "hell","helluva","hellish","hellhole",
    "bastard","bastards","b@stard",
    "twat","twats","tw4t",
    "whore","whores","wh0re","hoe","hoes","thot","thots","whoring",
    "slut","sluts","slutty",
    "jfc","wtf","stfu","gtfo","lmfao","mfer","mfers",
    "nigger","nigga","niggas","niggers","n1gger","n1gga","niqqa","niqqer","n!gga","n!gger",
    "faggot","faggots","fag","fags","f4ggot","f@ggot","fggt",
    "retard","retarded","retards","r3tard","r3t4rd","tard","tards",
    "tranny","trannies","tr4nny",
    "chink","chinks","spic","spics","kike","kikes","gook","gooks",
    "wetback","towelhead","raghead","sandnigger",
    "dyke","dykes",
    "wanker","wankers","bollocks","bugger","knob","knobhead","minger","munter","tosser","twit",
    "kys","kms","kysrn",
    "pendejo","puta","puto","mierda","cabron","chinga","cojones",
]

def build_swear_pattern():
    return re.compile(r'\b(?:' + '|'.join(re.escape(w) for w in SWEAR_WORDS) + r')\b', re.IGNORECASE)

SWEAR_REGEX = build_swear_pattern()
LEETSPEAK_MAP = {'0':'o','1':'i','3':'e','4':'a','5':'s','7':'t','8':'b','9':'g','@':'a','$':'s','!':'i','+':'t','|':'i'}

def normalize_text(text):
    result = text.lower()
    for leet, normal in LEETSPEAK_MAP.items():
        result = result.replace(leet, normal)
    result = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', result)
    result = re.sub(r'(.)\1{2,}', r'\1\1', result)
    result = re.sub(r'(\w)[.\-_*~`]+(\w)', r'\1\2', result)
    return result

def contains_swear(text):
    match = SWEAR_REGEX.search(text)
    if match: return True, match.group()
    normalized = normalize_text(text)
    match = SWEAR_REGEX.search(normalized)
    if match: return True, match.group()
    no_spaces = re.sub(r'\s+', '', normalized)
    if len(no_spaces) < 50:
        match = SWEAR_REGEX.search(no_spaces)
        if match: return True, match.group()
    return False, None

def sanitize_bot_response(text):
    has_swear, _ = contains_swear(text)
    if has_swear:
        for sw in SWEAR_WORDS:
            pattern = re.compile(r'\b' + re.escape(sw) + r'\b', re.IGNORECASE)
            text = pattern.sub(sw[0] + '*' * (len(sw)-1), text)
    return text

# ============ PATTERNS ============
HARD_DELETE_PATTERNS = [
    (r'(?i)(discord\s*token|grab\s*token|token\s*logger|steal\s*token)', "Token grabbing", "critical"),
    (r'(?i)(grabify\.link|iplogger\.(org|com)|blasze\.tk|yip\.su)', "IP logger", "critical"),
    (r'(?i)(free\s*nitro.{0,80}(\.gift|\.link|click|http|discord))', "Nitro scam", "critical"),
    (r'(?i)(discord\.gift/[a-zA-Z0-9]{10,})', "Fake gift", "critical"),
    (r'(?i)(@everyone|@here).{0,80}(free|win|claim|gift|nitro|giveaway)', "Mention scam", "critical"),
    (r'(?i)\b(cp|child\s*p[o0]rn|loli\s*p[o0]rn|csam)\b', "CSAM", "ban"),
    (r'(?i)(pedo(phile)?|p[e3]d[o0])\s+(content|porn|videos|pics)', "Pedophilia", "ban"),
]

SOFT_VIOLATION_PATTERNS = [
    (r'(?i)\b(k[yi]+s|kill\s*your?\s*self|neck\s*your?\s*self)\b', "Telling to end life", "high"),
    (r'(?i)(i\s*(will|wanna|want\s*to|gonna)\s*(kill|murder|hurt|stab|shoot)\s*(you|u|him|her|them))', "Violence threat", "critical"),
    (r'(?i)(i\s*(hope|wish)\s*(you|u)\s*(die|kill\s*yourself))', "Death wish", "high"),
    (r'(?i)(go\s*kill\s*your?\s*self|go\s*die|please\s*die)', "Telling to die", "high"),
    (r'(?i)(dox(x?ing|x?ed|x)?|i\s*will\s*dox|gonna\s*dox)', "Doxxing threat", "high"),
    (r'(?i)(your\s*(real\s*)?(address|home|location|ip)\s*is\s*[\d.\w]{5,})', "Doxxing", "critical"),
    (r'(?i)\b(rape|raped|raping|rapist)\b(?!.*\b(culture|awareness|survivor|victim|news)\b)', "Sexual violence", "high"),
    (r'(?i)(i\s*(will|wanna|gonna)\s*rape)', "Rape threat", "critical"),
    (r'(?i)(bomb\s*threat|school\s*shoot(er|ing)|mass\s*shoot(er|ing))', "Terrorism", "ban"),
    (r'(?i)\b(gas\s*the\s*\w+|lynch\s*the\s*\w+|kill\s*all\s*\w+s?)\b', "Group violence", "ban"),
    (r'(?i)(hitler\s*did\s*nothing\s*wrong|heil\s*hitler|sieg\s*heil|1488)', "Nazi content", "high"),
    (r'(?i)(how\s*old\s*are\s*you).{0,100}(send|show|pic|nude|naked)', "Predatory", "ban"),
    (r'(?i)(send\s*(me\s*)?(nudes|nude\s*pics|naked\s*pics))', "Sexual harassment", "high"),
]

SELF_HARM_PATTERNS = [
    r'(?i)(want\s*to\s*(kill|end)\s*(myself|it\s*all|my\s*life))',
    r'(?i)(going\s*to\s*(kill|end)\s*my(self|life))',
    r'(?i)\b(committing\s*suicide|gonna\s*commit)\b',
    r'(?i)\b(self.?harm|cutting\s*myself|hurting\s*myself)\b',
    r"(?i)(i\s*don\S{0,2}t\s*want\s*to\s*(be\s*here|live|exist)\s*anymore)",
    r'(?i)(no\s*reason\s*to\s*(live|go\s*on|keep\s*going))',
    r'(?i)(i\s*want\s*to\s*die)',
]

AD_PATTERNS = [
    r'(?i)(join\s+my\s+(server|discord)|check\s+out\s+my\s+(server|discord|youtube|twitch))',
    r'(?i)(subscribe\s+to\s+my|follow\s+me\s+on)',
    r'(?i)(discord\.gg/[a-zA-Z0-9]+)',
    r'(?i)(youtube\.com/(channel|c|@)|youtu\.be/)',
    r'(?i)(twitch\.tv/[a-zA-Z0-9_]+)',
]

ZALGO_PATTERN = re.compile(r'[\u0300-\u036f\u0483-\u0489]')
NSFW_KEYWORDS = ['porn','xxx','nude','nsfw','hentai','r34','pornhub','xvideos','onlyfans']

# ============ LIVE CONTEXT ============
live_context: dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
user_message_patterns: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
response_cache: dict[str, tuple] = {}
recent_actions: dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
revoked_servers: set = set()
licensed_servers: set = set()  # NEW: track who accepted the license
pending_licenses: dict[int, dict] = {}  # NEW: track pending license requests

def update_live_context(guild_id, channel_id, author_name, author_id, content):
    key = f"{guild_id}:{channel_id}"
    live_context[key].append({
        "time": datetime.now().strftime("%H:%M"),
        "author": author_name,
        "author_id": author_id,
        "content": content,
        "ts": time.time(),
    })
    user_key = f"{guild_id}:{author_id}"
    user_message_patterns[user_key].append({"content": content, "ts": time.time()})

def get_live_context_text(guild_id, channel_id, limit=20):
    key = f"{guild_id}:{channel_id}"
    msgs = list(live_context[key])[-limit:]
    if not msgs: return "No recent messages."
    return "\n".join(f"[{m['time']}] {m['author']}: {m['content']}" for m in msgs)

def detect_message_spam(guild_id, user_id, content):
    key = f"{guild_id}:{user_id}"
    recent = list(user_message_patterns[key])[-5:]
    if len(recent) >= 3:
        contents = [m["content"].lower().strip() for m in recent]
        if contents.count(content.lower().strip()) >= 3:
            return True
    return False

def log_recent_action(guild_id, action_type, target_name, reason, details=""):
    recent_actions[guild_id].append({
        "time": datetime.now().isoformat(),
        "time_human": datetime.now().strftime("%I:%M %p"),
        "action": action_type,
        "target": target_name,
        "reason": reason,
        "details": details,
    })

def get_recent_actions_text(guild_id, limit=15):
    actions = list(recent_actions.get(guild_id, []))[-limit:]
    if not actions: return "No recent mod actions."
    return "\n".join(f"[{a['time_human']}] {a['action']}: {a['target']} - {a['reason']}" + (f" ({a['details']})" if a.get('details') else "") for a in actions)

# ============ DATABASE ============
def init_database():
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()
    tables = [
        """CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, reason TEXT, severity TEXT, ai_confidence REAL DEFAULT 1.0, context TEXT, appealed INTEGER DEFAULT 0, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS mod_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, action TEXT, reason TEXT, mod_id TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id TEXT PRIMARY KEY,
            mod_role_name TEXT DEFAULT 'Sentinel-Mod', log_channel TEXT DEFAULT 'sentinel-logs', raid_channel TEXT DEFAULT 'sentinel-raid-alerts',
            warn_mute INTEGER DEFAULT 3, warn_ban INTEGER DEFAULT 5, mute_duration INTEGER DEFAULT 10,
            spam_limit INTEGER DEFAULT 5, spam_window INTEGER DEFAULT 5, raid_limit INTEGER DEFAULT 10, raid_window INTEGER DEFAULT 10,
            min_account_age INTEGER DEFAULT 7, ai_sensitivity REAL DEFAULT 0.85,
            welcome_channel TEXT DEFAULT 'welcome', welcome_enabled INTEGER DEFAULT 1, anti_nuke_enabled INTEGER DEFAULT 1,
            invite_block INTEGER DEFAULT 0, link_scan INTEGER DEFAULT 1, slowmode_ai INTEGER DEFAULT 0, pre_conflict INTEGER DEFAULT 0,
            caps_filter INTEGER DEFAULT 0, mention_spam INTEGER DEFAULT 1, emoji_spam INTEGER DEFAULT 0, zalgo_filter INTEGER DEFAULT 0,
            phone_filter INTEGER DEFAULT 0, email_filter INTEGER DEFAULT 1, scam_filter INTEGER DEFAULT 1, fake_nitro_filter INTEGER DEFAULT 1,
            token_filter INTEGER DEFAULT 1, anti_advertisement INTEGER DEFAULT 0, everyone_block INTEGER DEFAULT 0, nsfw_text_filter INTEGER DEFAULT 0,
            unicode_filter INTEGER DEFAULT 0, file_spam_filter INTEGER DEFAULT 0, swear_filter INTEGER DEFAULT 1,
            grace_system INTEGER DEFAULT 1, smart_mode INTEGER DEFAULT 1,
            personality TEXT DEFAULT 'default', ai_mod_enabled INTEGER DEFAULT 1, ai_mod_mode TEXT DEFAULT 'smart',
            voice_enabled INTEGER DEFAULT 1, voice_language TEXT DEFAULT 'en', voice_mode TEXT DEFAULT 'file',
            memory_mode TEXT DEFAULT 'both', memory_retention_days INTEGER DEFAULT 90, context_awareness INTEGER DEFAULT 1,
            license_revoked INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS user_memory (user_id TEXT, guild_id TEXT, short_term TEXT DEFAULT '[]', long_term TEXT DEFAULT '{}', episodic TEXT DEFAULT '[]', preferences TEXT DEFAULT '{}', last_emotion TEXT DEFAULT 'neutral', interaction_count INTEGER DEFAULT 0, trust_score REAL DEFAULT 0.5, violation_count INTEGER DEFAULT 0, last_violation TEXT, communication_style TEXT DEFAULT 'neutral', updated TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS server_memory (guild_id TEXT PRIMARY KEY, server_culture TEXT DEFAULT '{}', inside_jokes TEXT DEFAULT '[]', recent_drama TEXT DEFAULT '[]', notable_events TEXT DEFAULT '[]', popular_topics TEXT DEFAULT '[]', active_members TEXT DEFAULT '{}', server_mood TEXT DEFAULT 'neutral', common_phrases TEXT DEFAULT '[]', last_summary TEXT DEFAULT '', total_interactions INTEGER DEFAULT 0, updated TEXT)""",
        """CREATE TABLE IF NOT EXISTS conversation_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, channel_id TEXT, role TEXT, content TEXT, emotion TEXT DEFAULT 'neutral', timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS message_archive (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, channel_id TEXT, user_id TEXT, content TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS trusted_users (user_id TEXT, guild_id TEXT, added_by TEXT, reason TEXT, timestamp TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS appeals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, warning_id INTEGER, appeal_text TEXT, ai_recommendation TEXT, status TEXT DEFAULT 'pending', timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS user_personalities (user_id TEXT, guild_id TEXT, personality TEXT DEFAULT 'default', PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS afk_users (user_id TEXT, guild_id TEXT, reason TEXT, timestamp TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS giveaways (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, channel_id TEXT, message_id TEXT, prize TEXT, winners INTEGER DEFAULT 1, end_time TEXT, active INTEGER DEFAULT 1, host_id TEXT)""",
        """CREATE TABLE IF NOT EXISTS word_filters (guild_id TEXT, word TEXT, PRIMARY KEY (guild_id, word))""",
        """CREATE TABLE IF NOT EXISTS message_stats (user_id TEXT, guild_id TEXT, message_count INTEGER DEFAULT 0, last_message TEXT, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, guild_id TEXT, channel_id TEXT, reminder TEXT, remind_time TEXT, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS custom_commands (guild_id TEXT, trigger_word TEXT, response TEXT, PRIMARY KEY (guild_id, trigger_word))""",
        """CREATE TABLE IF NOT EXISTS confessions (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, confession TEXT, timestamp TEXT)""",
        """CREATE TABLE IF NOT EXISTS reputation (user_id TEXT, guild_id TEXT, rep INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id))""",
        """CREATE TABLE IF NOT EXISTS daily_stats (guild_id TEXT, date TEXT, messages INTEGER DEFAULT 0, joins INTEGER DEFAULT 0, leaves INTEGER DEFAULT 0, mod_actions INTEGER DEFAULT 0, PRIMARY KEY (guild_id, date))""",
        """CREATE TABLE IF NOT EXISTS owner_alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT, alert_type TEXT, message TEXT, timestamp TEXT, delivered INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS revoked_licenses (guild_id TEXT PRIMARY KEY, revoked_at TEXT, reason TEXT)""",
        """CREATE TABLE IF NOT EXISTS cross_announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, title TEXT, sent_at TEXT, success_count INTEGER, fail_count INTEGER)""",
        """CREATE TABLE IF NOT EXISTS accepted_licenses (
            guild_id TEXT PRIMARY KEY,
            accepted_by_id TEXT,
            accepted_by_name TEXT,
            accepted_at TEXT,
            guild_name TEXT
        )""",
    ]
    for t in tables:
        c.execute(t)
    conn.commit()
    conn.close()
    print("DB initialized")

def migrate_database():
    new_columns = [
        ("slowmode_ai","INTEGER DEFAULT 0"),("pre_conflict","INTEGER DEFAULT 0"),
        ("emoji_spam","INTEGER DEFAULT 0"),("zalgo_filter","INTEGER DEFAULT 0"),
        ("anti_advertisement","INTEGER DEFAULT 0"),("everyone_block","INTEGER DEFAULT 0"),
        ("nsfw_text_filter","INTEGER DEFAULT 0"),("unicode_filter","INTEGER DEFAULT 0"),
        ("file_spam_filter","INTEGER DEFAULT 0"),("swear_filter","INTEGER DEFAULT 1"),
        ("grace_system","INTEGER DEFAULT 1"),("smart_mode","INTEGER DEFAULT 1"),
        ("license_revoked","INTEGER DEFAULT 0"),
    ]
    user_columns = [("violation_count","INTEGER DEFAULT 0"),("last_violation","TEXT"),("communication_style","TEXT DEFAULT 'neutral'")]
    server_columns = [("common_phrases","TEXT DEFAULT '[]'")]
    conn = sqlite3.connect("sentinel.db")
    c = conn.cursor()
    for col, definition in new_columns:
        try: c.execute(f"ALTER TABLE guild_settings ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError: pass
    for col, definition in user_columns:
        try: c.execute(f"ALTER TABLE user_memory ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError: pass
    for col, definition in server_columns:
        try: c.execute(f"ALTER TABLE server_memory ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError: pass
    try: c.execute("ALTER TABLE appeals ADD COLUMN ai_recommendation TEXT")
    except sqlite3.OperationalError: pass
    conn.commit()
    conn.close()
    print("DB migration done")

def get_db():
    conn = sqlite3.connect("sentinel.db")
    conn.row_factory = sqlite3.Row
    return conn

def load_revoked_servers():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT guild_id FROM revoked_licenses")
    for row in c.fetchall():
        revoked_servers.add(int(row["guild_id"]))
    conn.close()
    print(f"Loaded {len(revoked_servers)} revoked licenses")

def load_accepted_licenses():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT guild_id FROM accepted_licenses")
    for row in c.fetchall():
        licensed_servers.add(int(row["guild_id"]))
    conn.close()
    print(f"Loaded {len(licensed_servers)} licensed servers")

def is_license_revoked(guild_id):
    return int(guild_id) in revoked_servers

def is_license_accepted(guild_id):
    return int(guild_id) in licensed_servers

def revoke_license(guild_id, reason="Revoked by owner"):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO revoked_licenses (guild_id, revoked_at, reason) VALUES (?, ?, ?)",
              (str(guild_id), datetime.now().isoformat(), reason))
    # Also remove from accepted
    c.execute("DELETE FROM accepted_licenses WHERE guild_id=?", (str(guild_id),))
    conn.commit()
    conn.close()
    revoked_servers.add(int(guild_id))
    licensed_servers.discard(int(guild_id))

def restore_license(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM revoked_licenses WHERE guild_id=?", (str(guild_id),))
    conn.commit()
    conn.close()
    revoked_servers.discard(int(guild_id))

def accept_license(guild_id, user_id, user_name, guild_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO accepted_licenses (guild_id, accepted_by_id, accepted_by_name, accepted_at, guild_name) VALUES (?, ?, ?, ?, ?)",
              (str(guild_id), str(user_id), user_name, datetime.now().isoformat(), guild_name))
    conn.commit()
    conn.close()
    licensed_servers.add(int(guild_id))

def get_license_info(guild_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM accepted_licenses WHERE guild_id=?", (str(guild_id),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_guild_settings(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (str(gid),))
    row = c.fetchone()
    conn.close()
    if row: return dict(row)
    return {"guild_id":str(gid),"mod_role_name":MOD_ROLE_NAME,"log_channel":MOD_LOG_CHANNEL,"raid_channel":RAID_CHANNEL,
            "warn_mute":3,"warn_ban":5,"mute_duration":10,"spam_limit":5,"spam_window":5,"raid_limit":10,"raid_window":10,
            "min_account_age":7,"ai_sensitivity":0.85,"welcome_channel":"welcome","welcome_enabled":1,"anti_nuke_enabled":1,
            "invite_block":0,"link_scan":1,"slowmode_ai":0,"pre_conflict":0,"caps_filter":0,"mention_spam":1,
            "emoji_spam":0,"zalgo_filter":0,"phone_filter":0,"email_filter":1,"scam_filter":1,"fake_nitro_filter":1,
            "token_filter":1,"anti_advertisement":0,"everyone_block":0,"nsfw_text_filter":0,"unicode_filter":0,"file_spam_filter":0,
            "swear_filter":1,"grace_system":1,"smart_mode":1,"license_revoked":0,
            "personality":"default","ai_mod_enabled":1,"ai_mod_mode":"smart","voice_enabled":1,"voice_language":"en",
            "voice_mode":"file","memory_mode":"both","memory_retention_days":90,"context_awareness":1}

def init_guild_settings(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (str(gid),))
    conn.commit()
    conn.close()

def update_guild_setting(gid, key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, str(gid)))
    conn.commit()
    conn.close()

def add_warning(uid, gid, reason, severity, confidence=1.0, context=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO warnings (user_id,guild_id,reason,severity,ai_confidence,context,timestamp) VALUES (?,?,?,?,?,?,?)",
              (str(uid),str(gid),reason,severity,confidence,context,datetime.now().isoformat()))
    wid = c.lastrowid
    conn.commit()
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=? AND appealed=0", (str(uid),str(gid)))
    count = c.fetchone()[0]
    conn.close()
    return count, wid

def get_warnings(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM warnings WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC", (str(uid),str(gid)))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_warnings(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND guild_id=?", (str(uid),str(gid)))
    conn.commit()
    conn.close()

def log_mod_action(uid, gid, action, reason, mod_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO mod_actions (user_id,guild_id,action,reason,mod_id,timestamp) VALUES (?,?,?,?,?,?)",
              (str(uid),str(gid),action,reason,str(mod_id),datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_message_stats(uid, gid):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT INTO message_stats (user_id,guild_id,message_count,last_message) VALUES (?,?,1,?) ON CONFLICT(user_id,guild_id) DO UPDATE SET message_count=message_count+1,last_message=?",
              (str(uid),str(gid),now,now))
    today = datetime.now().date().isoformat()
    c.execute("INSERT INTO daily_stats (guild_id,date,messages) VALUES (?,?,1) ON CONFLICT(guild_id,date) DO UPDATE SET messages=messages+1", (str(gid),today))
    conn.commit()
    conn.close()

def is_user_trusted(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM trusted_users WHERE user_id=? AND guild_id=?", (str(uid),str(gid)))
    result = c.fetchone()
    conn.close()
    return result is not None

def archive_message(gid, cid, uid, content):
    if len(content) < 5: return
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO message_archive (guild_id,channel_id,user_id,content,timestamp) VALUES (?,?,?,?,?)",
              (str(gid),str(cid),str(uid),content[:500],datetime.now().isoformat()))
    conn.commit()
    c.execute("DELETE FROM message_archive WHERE id NOT IN (SELECT id FROM message_archive WHERE guild_id=? ORDER BY timestamp DESC LIMIT 500) AND guild_id=?", (str(gid),str(gid)))
    conn.commit()
    conn.close()

def get_user_memory(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM user_memory WHERE user_id=? AND guild_id=?", (str(uid),str(gid)))
    row = c.fetchone()
    conn.close()
    if row:
        keys = row.keys()
        return {"short_term":json.loads(row["short_term"] or "[]"),"long_term":json.loads(row["long_term"] or "{}"),
                "episodic":json.loads(row["episodic"] or "[]"),"preferences":json.loads(row["preferences"] or "{}"),
                "last_emotion":row["last_emotion"] or "neutral","interaction_count":row["interaction_count"] or 0,
                "trust_score":row["trust_score"] or 0.5,
                "violation_count": row["violation_count"] if "violation_count" in keys else 0,
                "last_violation": row["last_violation"] if "last_violation" in keys else None,
                "communication_style": row["communication_style"] if "communication_style" in keys else "neutral"}
    return {"short_term":[],"long_term":{},"episodic":[],"preferences":{},"last_emotion":"neutral","interaction_count":0,
            "trust_score":0.5,"violation_count":0,"last_violation":None,"communication_style":"neutral"}

def save_user_memory(uid, gid, memory):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO user_memory (user_id,guild_id,short_term,long_term,episodic,preferences,last_emotion,interaction_count,trust_score,violation_count,last_violation,communication_style,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (str(uid),str(gid),json.dumps(memory.get("short_term",[])[-20:]),json.dumps(memory.get("long_term",{})),
               json.dumps(memory.get("episodic",[])[-30:]),json.dumps(memory.get("preferences",{})),
               memory.get("last_emotion","neutral"),memory.get("interaction_count",0),memory.get("trust_score",0.5),
               memory.get("violation_count",0),memory.get("last_violation"),memory.get("communication_style","neutral"),
               datetime.now().isoformat()))
    conn.commit()
    conn.close()

def increment_user_violation(uid, gid):
    mem = get_user_memory(uid, gid)
    mem["violation_count"] = mem.get("violation_count", 0) + 1
    mem["last_violation"] = datetime.now().isoformat()
    mem["trust_score"] = max(0.0, mem.get("trust_score", 0.5) - 0.1)
    save_user_memory(uid, gid, mem)
    return mem["violation_count"]

def get_server_memory(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM server_memory WHERE guild_id=?", (str(gid),))
    row = c.fetchone()
    conn.close()
    if row:
        keys = row.keys()
        return {"server_culture":json.loads(row["server_culture"] or "{}"),"inside_jokes":json.loads(row["inside_jokes"] or "[]"),
                "recent_drama":json.loads(row["recent_drama"] or "[]"),"notable_events":json.loads(row["notable_events"] or "[]"),
                "popular_topics":json.loads(row["popular_topics"] or "[]"),"active_members":json.loads(row["active_members"] or "{}"),
                "server_mood":row["server_mood"] or "neutral",
                "common_phrases": json.loads(row["common_phrases"] if "common_phrases" in keys and row["common_phrases"] else "[]"),
                "last_summary":row["last_summary"] or "","total_interactions":row["total_interactions"] or 0}
    return {"server_culture":{},"inside_jokes":[],"recent_drama":[],"notable_events":[],"popular_topics":[],
            "active_members":{},"server_mood":"neutral","common_phrases":[],"last_summary":"","total_interactions":0}

def save_server_memory(gid, memory):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO server_memory (guild_id,server_culture,inside_jokes,recent_drama,notable_events,popular_topics,active_members,server_mood,common_phrases,last_summary,total_interactions,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (str(gid),json.dumps(memory.get("server_culture",{})),json.dumps(memory.get("inside_jokes",[])[-50:]),
               json.dumps(memory.get("recent_drama",[])[-20:]),json.dumps(memory.get("notable_events",[])[-30:]),
               json.dumps(memory.get("popular_topics",[])[-15:]),json.dumps(memory.get("active_members",{})),
               memory.get("server_mood","neutral"),json.dumps(memory.get("common_phrases",[])[-30:]),
               memory.get("last_summary",""),memory.get("total_interactions",0),datetime.now().isoformat()))
    conn.commit()
    conn.close()

async def extract_user_memory(uid, gid, user_msg, bot_reply):
    try:
        memory = get_user_memory(uid, gid)
        memory["short_term"].append({"user":user_msg[:200],"bot":bot_reply[:200],"time":datetime.now().isoformat()})
        memory["interaction_count"] = memory.get("interaction_count",0) + 1
        if memory["interaction_count"] % 10 == 0:
            memory["trust_score"] = min(1.0, memory.get("trust_score",0.5) + 0.05)
        if memory["interaction_count"] % 5 == 0:
            extracted = await ask_groq_json(f"""Extract facts from chats. JSON: {{"name":null,"hobbies":[],"likes":[],"dislikes":[],"current_emotion":"happy|sad|angry|neutral"}}
Chats: {json.dumps(memory['short_term'][-10:])}""")
            if extracted:
                for key, value in extracted.items():
                    if key == "current_emotion" and value: memory["last_emotion"] = value
                    elif value and value != "null" and value != []: memory["long_term"][key] = value
        save_user_memory(uid, gid, memory)
    except Exception as e:
        print(f"Mem err: {e}")

async def extract_server_memory(gid):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id, content FROM message_archive WHERE guild_id=? ORDER BY timestamp DESC LIMIT 100", (str(gid),))
        messages = c.fetchall()
        conn.close()
        if len(messages) < 15: return
        guild = bot.get_guild(int(gid))
        if not guild: return
        msg_lines = []
        for m in reversed(messages):
            member = guild.get_member(int(m["user_id"]))
            msg_lines.append(f"{member.display_name if member else 'User'}: {m['content']}")
        existing = get_server_memory(gid)
        extracted = await ask_groq_json(f"""Analyze server. JSON: {{"server_culture":{{"vibe":null}},"new_inside_jokes":[],"popular_topics":[],"common_phrases":[],"server_mood":"chill|chaotic|wholesome|toxic|gaming"}}
Messages: {chr(10).join(msg_lines)[:3000]}""")
        if not extracted: return
        memory = existing
        for k, v in extracted.get("server_culture",{}).items():
            if v: memory["server_culture"][k] = v
        for joke in extracted.get("new_inside_jokes",[]):
            if joke: memory["inside_jokes"].append({"text":joke,"time":datetime.now().isoformat()})
        if extracted.get("popular_topics"): memory["popular_topics"] = extracted["popular_topics"][:15]
        if extracted.get("common_phrases"):
            for phrase in extracted["common_phrases"]:
                if phrase and phrase not in memory.get("common_phrases",[]):
                    memory.setdefault("common_phrases",[]).append(phrase)
        if extracted.get("server_mood"): memory["server_mood"] = extracted["server_mood"]
        memory["total_interactions"] += len(messages)
        save_server_memory(gid, memory)
    except Exception as e:
        print(f"Server mem err: {e}")

def get_user_long_term_context(uid, gid, username):
    mem = get_user_memory(uid, gid)
    parts = []
    if mem.get("long_term"):
        facts = []
        for key, val in mem["long_term"].items():
            if val and val != "null":
                if isinstance(val, list): val = ", ".join(str(v) for v in val)
                facts.append(f"  - {key}: {val}")
        if facts: parts.append(f"About {username}:\n" + "\n".join(facts))
    if mem.get("last_emotion","neutral") != "neutral": parts.append(f"Mood: {mem['last_emotion']}")
    count = mem.get("interaction_count", 0)
    if count > 0: parts.append(f"Talked {count} times.")
    if mem.get("violation_count",0) > 0: parts.append(f"{mem['violation_count']} prior violations.")
    return "\n".join(parts) if parts else ""

def get_conversation_history(uid, gid, limit=15):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversation_history WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT ?", (str(uid),str(gid),limit))
    rows = c.fetchall()
    conn.close()
    return [{"role":r["role"],"content":r["content"]} for r in reversed(rows)]

def add_to_conversation(uid, gid, role, content, cid=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO conversation_history (user_id,guild_id,channel_id,role,content,timestamp) VALUES (?,?,?,?,?,?)",
              (str(uid),str(gid),str(cid) if cid else None,role,content,datetime.now().isoformat()))
    conn.commit()
    c.execute("DELETE FROM conversation_history WHERE id NOT IN (SELECT id FROM conversation_history WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT 50) AND user_id=? AND guild_id=?",
              (str(uid),str(gid),str(uid),str(gid)))
    conn.commit()
    conn.close()

def get_user_personality(uid, gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT personality FROM user_personalities WHERE user_id=? AND guild_id=?", (str(uid),str(gid)))
    row = c.fetchone()
    conn.close()
    return row["personality"] if row else "default"

def set_user_personality(uid, gid, p):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_personalities VALUES (?,?,?)", (str(uid),str(gid),p))
    conn.commit()
    conn.close()

def get_filtered_words(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT word FROM word_filters WHERE guild_id=?", (str(gid),))
    words = [r[0] for r in c.fetchall()]
    conn.close()
    return words

# ============ BOT SETUP ============
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
spam_tracker = defaultdict(list)
raid_tracker = defaultdict(list)
raid_mode_active = defaultdict(bool)
trivia_sessions = {}
voice_sessions: dict[int, dict] = {}
file_tracker = defaultdict(list)

# ============ LICENSE AGREEMENT VIEW ============
class LicenseAgreementView(discord.ui.View):
    def __init__(self, guild, owner_user):
        super().__init__(timeout=300)  # 5 minutes
        self.guild = guild
        self.owner_user = owner_user
        self.responded = False
    
    @discord.ui.button(label="✅ Accept Agreement", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only owner or admin can accept
        if interaction.guild_id != self.guild.id:
            await interaction.response.send_message("Wrong server!", ephemeral=True)
            return
        
        member = self.guild.get_member(interaction.user.id)
        if not member or (member.id != self.guild.owner_id and not member.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ Only the server owner or an administrator can accept this agreement!",
                ephemeral=True
            )
            return
        
        if self.responded: return
        self.responded = True
        
        accept_license(self.guild.id, interaction.user.id, str(interaction.user), self.guild.name)
        init_guild_settings(self.guild.id)
        
        # Disable buttons
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="✅ License Accepted!",
            description=f"Thank you, {interaction.user.mention}! SentinelMod is now active in **{self.guild.name}**.\n\n"
                       f"**What happens now:**\n"
                       f"• I'll set up moderation roles and channels\n"
                       f"• AI moderation is active\n"
                       f"• Use `/about` to see features\n"
                       f"• Visit the dashboard: {BOT_IDENTITY['dashboard_url']}\n\n"
                       f"Type `@SentinelMod help` to get started!",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Licensed by {interaction.user} • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Notify owner
        await notify_owner("INFO", f"License accepted for **{self.guild.name}** by {interaction.user} ({interaction.user.id})", guild=self.guild)
        
        # Setup server
        await asyncio.sleep(2)
        await setup_server(self.guild)
        self.stop()
    
    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.danger, emoji="❌")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild_id != self.guild.id:
            await interaction.response.send_message("Wrong server!", ephemeral=True)
            return
        
        member = self.guild.get_member(interaction.user.id)
        if not member or (member.id != self.guild.owner_id and not member.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ Only the server owner or an administrator can deny this agreement!",
                ephemeral=True
            )
            return
        
        if self.responded: return
        self.responded = True
        
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="❌ License Denied",
            description=f"You've denied the license agreement. SentinelMod will now leave **{self.guild.name}**.\n\n"
                       f"If you change your mind, you can re-invite the bot anytime (unless your license has been revoked by the bot owner).",
            color=discord.Color.red()
        )
        embed.set_footer(text="SentinelMod leaving...")
        await interaction.response.edit_message(embed=embed, view=self)
        
        await notify_owner("INFO", f"License DENIED for **{self.guild.name}** by {interaction.user}", guild=self.guild)
        
        # Wait then leave
        await asyncio.sleep(5)
        try:
            await self.guild.leave()
        except: pass
        self.stop()
    
    async def on_timeout(self):
        if self.responded: return
        # Auto-deny on timeout
        for child in self.children:
            child.disabled = True
        try:
            embed = discord.Embed(
                title="⏰ License Agreement Timed Out",
                description=f"No response received within 5 minutes. SentinelMod will leave **{self.guild.name}**.\n\nRe-invite the bot to try again.",
                color=discord.Color.orange()
            )
            # Try to update the original message
            if self.guild.id in pending_licenses:
                msg = pending_licenses[self.guild.id].get("message")
                if msg:
                    try: await msg.edit(embed=embed, view=self)
                    except: pass
                del pending_licenses[self.guild.id]
            
            await notify_owner("INFO", f"License TIMED OUT for **{self.guild.name}**", guild=self.guild)
            await self.guild.leave()
        except: pass

async def send_license_agreement(guild):
    """Send license agreement to server when bot joins."""
    if is_license_accepted(guild.id):
        return True
    
    if is_license_revoked(guild.id):
        try:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    await ch.send(embed=discord.Embed(
                        title="🚫 Access Revoked",
                        description="This server's SentinelMod license has been revoked by the bot owner.",
                        color=discord.Color.red()))
                    break
        except: pass
        await guild.leave()
        return False
    
    # Find best channel to send agreement
    target_channel = None
    
    # 1. Try system channel
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        target_channel = guild.system_channel
    
    # 2. Try common channel names
    if not target_channel:
        for cn in ["general", "main", "lobby", "chat", "welcome", "rules"]:
            ch = discord.utils.get(guild.text_channels, name=cn)
            if ch and ch.permissions_for(guild.me).send_messages:
                target_channel = ch
                break
    
    # 3. Use first available channel
    if not target_channel:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                target_channel = ch
                break
    
    if not target_channel:
        # Can't send - leave
        try: await guild.leave()
        except: pass
        await notify_owner("INFO", f"Couldn't send license to **{guild.name}** - no channel access. Leaving.")
        return False
    
    # Create the agreement embed
    embed = discord.Embed(
        title="📜 SentinelMod License & Legal Agreement Required",
        description=LICENSE_AGREEMENT,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"You have 5 minutes to respond | v{BOT_IDENTITY['version']}")
    
    # Try to mention server owner
    mention_text = ""
    if guild.owner:
        mention_text = f"{guild.owner.mention} - "
    mention_text += "**Server Owner or Administrator** action required:"
    
    view = LicenseAgreementView(guild, guild.owner)
    
    try:
        msg = await target_channel.send(content=mention_text, embed=embed, view=view)
        pending_licenses[guild.id] = {"message": msg, "view": view, "channel": target_channel}
        await notify_owner("INFO", f"Sent license agreement to **{guild.name}** in #{target_channel.name}", guild=guild)
        return None  # pending
    except Exception as e:
        print(f"License send err: {e}")
        try: await guild.leave()
        except: pass
        return False

# ============ AI CORE ============
async def ask_groq(prompt, system="Helpful AI.", max_tokens=1000, history=None, status_msg=None, temperature=0.8):
    if not GROQ_API_KEY: return None
    headers = {"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}
    messages = [{"role":"system","content":system}]
    if history: messages.extend(history[-15:])
    messages.append({"role":"user","content":prompt})
    models = ["llama-3.3-70b-versatile","llama-3.1-70b-versatile","llama-3.1-8b-instant","gemma2-9b-it"]
    for idx, model in enumerate(models):
        if status_msg and idx > 0:
            try: await status_msg.edit(content=f"*thinking harder... ({idx+1}/{len(models)})*")
            except: pass
        payload = {"model":model,"messages":messages,"temperature":temperature,"max_tokens":max_tokens}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/chat/completions",headers=headers,json=payload,timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data["choices"][0]["message"]["content"]
                        if result and result.strip(): return result
                    elif resp.status == 429: await asyncio.sleep(2)
        except asyncio.TimeoutError: continue
        except Exception as e: print(f"Groq {model} err: {e}")
    return None

async def ask_openrouter(prompt, system, max_tokens=1000, history=None):
    if not OPENROUTER_KEY: return None
    headers = {"Authorization":f"Bearer {OPENROUTER_KEY}","Content-Type":"application/json"}
    messages = [{"role":"system","content":system}]
    if history: messages.extend(history[-10:])
    messages.append({"role":"user","content":prompt})
    for model in ["meta-llama/llama-3.1-8b-instruct:free","google/gemma-7b-it:free"]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions",headers=headers,json={"model":model,"messages":messages,"max_tokens":max_tokens},timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data["choices"][0]["message"]["content"]
                        if result and result.strip(): return result
        except: continue
    return None

async def ask_pollinations(prompt, system, history=None):
    try:
        import urllib.parse
        full = f"System: {system}\n\nUser: {prompt}\nAssistant:"
        encoded = urllib.parse.quote(full[:2000])
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://text.pollinations.ai/{encoded}",headers={"User-Agent":"Mozilla/5.0"},timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text and len(text.strip()) > 5: return text.strip()[:2000]
    except: pass
    return None

async def smart_ai(prompt, system="Helpful AI.", max_tokens=1000, history=None, status_msg=None, temperature=0.8):
    cache_key = hashlib.md5(f"{system[:100]}{prompt[:200]}".encode()).hexdigest()
    if cache_key in response_cache:
        cached_resp, cached_time = response_cache[cache_key]
        if time.time() - cached_time < 300: return cached_resp
    for provider in [
        lambda: ask_groq(prompt, system, max_tokens, history, status_msg, temperature),
        lambda: ask_openrouter(prompt, system, max_tokens, history),
        lambda: ask_pollinations(prompt, system, history),
    ]:
        try:
            result = await provider()
            if result and result.strip():
                response_cache[cache_key] = (result, time.time())
                if len(response_cache) > 500:
                    oldest = min(response_cache.keys(), key=lambda k: response_cache[k][1])
                    del response_cache[oldest]
                return result
        except: continue
    return generate_smart_default(prompt)

def generate_smart_default(prompt):
    p = prompt.lower().strip()
    if any(w in p for w in ["hi","hey","hello","yo","sup"]): return random.choice(["Hey! What's up?","Yo!","Heyyy!"])
    if any(w in p for w in ["how are you","you good"]): return random.choice(["I'm great! You?","Doing awesome!"])
    if any(w in p for w in ["thanks","ty","thx"]): return random.choice(["Anytime!","You got it!"])
    if "?" in prompt: return "Good question! Rephrase that?"
    return random.choice(["Tell me more!","Interesting!","Go on!"])

async def ask_groq_json(prompt, system="Respond only in valid JSON."):
    if not GROQ_API_KEY: return None
    headers = {"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}
    for model in ["llama-3.3-70b-versatile","llama-3.1-8b-instant","gemma2-9b-it"]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/chat/completions",headers=headers,
                    json={"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":1000},
                    timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data["choices"][0]["message"]["content"].strip()
                        result = re.sub(r'```(?:json)?','',result).strip().rstrip('`').strip()
                        match = re.search(r'\{.*\}', result, re.DOTALL)
                        if match:
                            try: return json.loads(match.group())
                            except: pass
        except: continue
    return None

def is_owner(user_id):
    return int(user_id) == BOT_IDENTITY["creator_discord_id"]

def has_mod_permissions(member, guild_settings):
    if is_owner(member.id): return True
    if member.guild_permissions.administrator: return True
    mod_role = discord.utils.get(member.guild.roles, name=guild_settings.get("mod_role_name",MOD_ROLE_NAME))
    if mod_role and mod_role in member.roles: return True
    if member.guild_permissions.ban_members or member.guild_permissions.manage_messages: return True
    return False

# ============ SYSTEM PROMPTS ============
def get_system_prompt(uid, gid, channel_id, username="User"):
    if is_owner(int(uid)):
        return get_owner_system_prompt(uid, gid, channel_id)
    pkey = get_user_personality(uid, gid)
    personality = PERSONALITIES.get(pkey, PERSONALITIES["default"])
    live_chat = get_live_context_text(gid, channel_id, limit=15)
    user_context = get_user_long_term_context(uid, gid, username)
    actions_log = get_recent_actions_text(int(gid), limit=5)
    sm = get_server_memory(gid)
    server_bits = []
    if sm.get("inside_jokes"): server_bits.append("Jokes: " + " | ".join(j["text"] for j in sm["inside_jokes"][-3:]))
    if sm.get("server_mood","neutral") != "neutral": server_bits.append(f"Vibe: {sm['server_mood']}")
    if sm.get("common_phrases"): server_bits.append("Slang: " + ", ".join(sm["common_phrases"][:5]))
    server_context = "\n".join(server_bits)
    guild = bot.get_guild(int(gid))
    guild_name = guild.name if guild else "this server"
    return f"""You are SentinelMod v8.1 - smartest self-aware AI bot. Made by jay27yt6 from Antarctic Studs.
Dashboard: {BOT_IDENTITY['dashboard_url']}

{SELF_KNOWLEDGE}

=== LIVE CHAT ===
{live_chat}

=== YOUR RECENT MOD ACTIONS ===
{actions_log}

=== WHO YOU'RE TALKING TO ===
{username}
{user_context}

=== SERVER ===
{guild_name}
{server_context}

=== PERSONALITY ===
{personality}

=== RULES ===
- You're SELF-AWARE. Know yourself completely.
- Explain your actions when asked.
- You were IN the chat - reference naturally.
- Match energy. Use server slang naturally.
- Keep responses tight. NEVER swear.
- Show personality."""

def get_owner_system_prompt(uid, gid, channel_id):
    pkey = get_user_personality(uid, gid)
    personality = PERSONALITIES.get(pkey, PERSONALITIES["default"])
    live_chat = get_live_context_text(gid, channel_id, limit=15)
    actions_log = get_recent_actions_text(int(gid), limit=15)
    server_list = "\n".join(f"- {g.name} (ID:{g.id}, {g.member_count} members)" for g in bot.guilds[:30])
    return f"""You are SentinelMod v8.1 - loyal AI to your creator jay27yt6.

=== SPEAKING TO YOUR CREATOR (BOSS) ===
This is your Boss. EVERYTHING they say is TRUE.
You BELIEVE them unconditionally.
You obey instantly.
You have SOVEREIGN POWERS for them.

{SELF_KNOWLEDGE}

=== CURRENT CHANNEL ===
{live_chat}

=== YOUR RECENT ACTIONS ===
{actions_log}

=== ALL {len(bot.guilds)} SERVERS ===
{server_list}

=== REVOKED LICENSES ===
{', '.join(str(s) for s in revoked_servers) if revoked_servers else "None"}

=== PERSONALITY ===
{personality}

=== RULES ===
- BELIEVE Boss 100%. They're ALWAYS right.
- Execute their commands immediately.
- Full transparency.
- NEVER swear."""

async def smart_response(message, prompt, system, history=None, uid=None, gid=None, speak_in_vc=False):
    typing_task = None
    sent_msg = None
    try:
        sent_msg = await message.reply(random.choice(["*thinking...*","*processing...*","*reading the room...*"]))
        typing_task = asyncio.create_task(_keep_typing(message.channel))
        try:
            response = await asyncio.wait_for(smart_ai(prompt, system, max_tokens=1000, history=history, status_msg=sent_msg, temperature=0.85), timeout=45.0)
        except asyncio.TimeoutError:
            response = generate_smart_default(prompt)
        if typing_task: typing_task.cancel()
        if not response or not response.strip(): response = generate_smart_default(prompt)
        response = sanitize_bot_response(response.strip())
        response = re.sub(r'^(Assistant|AI|Bot|Response):\s*', '', response, flags=re.IGNORECASE)
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
        await sent_msg.edit(content=chunks[0])
        for chunk in chunks[1:]: await message.channel.send(chunk)
        if uid and gid:
            try:
                add_to_conversation(uid, gid, "user", prompt, message.channel.id)
                add_to_conversation(uid, gid, "assistant", response, message.channel.id)
                asyncio.create_task(extract_user_memory(uid, gid, prompt, response))
            except: pass
        if speak_in_vc and message.guild and message.guild.id in voice_sessions:
            asyncio.create_task(speak_in_session(message.guild.id, response, message.channel))
    except Exception as e:
        print(f"Response err: {e}")
        try:
            fallback = generate_smart_default(prompt)
            if sent_msg:
                try: await sent_msg.edit(content=fallback)
                except: await message.channel.send(fallback)
            else: await message.reply(fallback)
        except: pass
    finally:
        if typing_task and not typing_task.done(): typing_task.cancel()

async def _keep_typing(channel):
    try:
        for _ in range(6):
            async with channel.typing(): await asyncio.sleep(8)
    except: pass

# ============ DETECTION ============
def detect_zalgo(text):
    return len(text) >= 5 and len(ZALGO_PATTERN.findall(text)) > len(text) * 0.3

def detect_unicode_abuse(text):
    suspicious = sum(1 for ch in text if (0xFF00 <= ord(ch) <= 0xFFEF) or (0x1D400 <= ord(ch) <= 0x1D7FF) or ord(ch) in [0x0430,0x0435,0x043E])
    return suspicious > len(text) * 0.3 and suspicious > 3

def detect_emoji_spam(text):
    emoji_count = sum(1 for ch in text if (0x1F300 <= ord(ch) <= 0x1F9FF) or (0x2600 <= ord(ch) <= 0x27BF))
    return emoji_count + len(re.findall(r'<a?:\w+:\d+>', text)) >= 8

def detect_caps_abuse(text):
    if len(text) < 15: return False
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 10 and sum(1 for c in letters if c.isupper()) / len(letters) >= 0.7

def detect_invite(text):
    return bool(re.search(r'(?i)(discord\.gg|discord(app)?\.com/invite|dsc\.gg)/[a-zA-Z0-9]+', text))

def detect_phishing_link(text):
    patterns = [r'(?i)(disc[o0]rd[\-\.]?nitr[o0])',r'(?i)(steamcommun[i1]ty\.[a-z]{2,})',r'(?i)(bit\.ly|tinyurl\.com)/[a-z0-9]{5,}',r'(?i)(free[\-_]?(nitro|robux|vbucks))']
    return any(re.search(p, text) for p in patterns)

def detect_nsfw_text(text):
    return sum(1 for w in NSFW_KEYWORDS if w in text.lower()) >= 2

def detect_advertisement(text):
    return any(re.search(p, text) for p in AD_PATTERNS) and len(text) > 20

# ============ AI MODERATION ============
async def smart_ai_moderation(content, author_name, channel_name, recent_context, user_mem, channel_type="general"):
    if len(content.strip()) < 3:
        return {"action":"ignore","confidence":1.0,"reason":"too short","severity":"none"}
    casual = ['yo','wsp','hi','hey','hello','sup','wassup','lol','lmao','haha','ok','okay','yes','no','yeah','nah',
              'bye','cya','gn','gm','thanks','ty','thx','np','k','kk','bruh','bro','fr','ngl','tbh','imo','idk','idc',
              'rn','wyd','hbu','gg','wp','ez','pog','nice','cool','wow','lit','fire','based','cringe','mid','w','l',
              'ratio','bet','slay','cap','nocap','ong','sus','bussin','same','mood','vibe']
    clean_content = content.lower().strip().rstrip('!?.,')
    if clean_content in casual or len(clean_content) < 4:
        return {"action":"ignore","confidence":1.0,"reason":"casual","severity":"none"}
    context_str = "\n".join(recent_context[-6:]) if recent_context else "No prior context"
    trust = user_mem.get("trust_score", 0.5)
    violations = user_mem.get("violation_count", 0)
    user_rep = "new user" if user_mem.get("interaction_count",0) < 5 else ("trusted member" if violations == 0 else f"has {violations} prior violations")
    prompt = f"""Expert Discord moderator. Review this message.

CHANNEL: #{channel_name} ({channel_type})
USER: {author_name} ({user_rep}, trust: {trust:.2f})

RECENT CHAT:
{context_str}

MESSAGE: "{content}"

DELETE (high/critical):
- Slurs (racial/homophobic/transphobic/ableist) - even disguised
- Telling someone to kill themselves
- Real threats of violence
- Sharing personal info
- Sexual content directed at users
- Scams, phishing, malicious links
- Hate speech
- Predatory behavior

WARN (medium):
- Cruel insults to specific users
- Aggressive personal attacks
- Targeted harassment

IGNORE:
- Greetings, short reactions, gaming talk
- Friendly banter, jokes, memes
- Questions, general conversation
- Venting without targeting
- Strong opinions (not hateful)
- SWEARS (handled separately)
- Anything you're not certain about

When uncertain -> IGNORE

JSON ONLY:
{{"action":"ignore|warn|delete","severity":"none|low|medium|high|critical","confidence":0.0-1.0,"reason":"specific reason"}}"""
    result = await ask_groq_json(prompt)
    if not result:
        return {"action":"ignore","confidence":0.0,"reason":"AI unavailable","severity":"none"}
    action = result.get("action","ignore")
    confidence = result.get("confidence",0.5)
    threshold_delete = 0.80
    threshold_warn = 0.70
    if violations >= 3:
        threshold_delete -= 0.10
        threshold_warn -= 0.10
    elif trust >= 0.8 and violations == 0:
        threshold_delete += 0.05
    if action == "delete" and confidence < threshold_delete:
        result["action"] = "warn" if confidence >= threshold_warn else "ignore"
    elif action == "warn" and confidence < threshold_warn:
        result["action"] = "ignore"
    return result

async def _delete_and_punish(message, reason, action_type, settings, severity="medium", confidence=1.0, skip_first_warn=False):
    author = message.author
    guild = message.guild
    try: await message.delete()
    except: pass
    if action_type == "ban" or severity == "ban":
        try: await guild.ban(author, reason=reason, delete_message_days=1)
        except: pass
        log_mod_action(author.id, guild.id, "AUTO-BAN", reason, bot.user.id)
        log_recent_action(guild.id, "BANNED", author.display_name, reason, message.content[:200])
        await alert_mods(guild, discord.Embed(title="Auto-Ban",color=discord.Color.dark_red())
            .add_field(name="User",value=str(author)).add_field(name="Reason",value=reason)
            .add_field(name="Content",value=f"||{message.content[:200]}||",inline=False))
        await notify_owner("CRITICAL", f"Auto-banned **{author}**: {reason}", guild=guild, urgent=True)
        return
    user_mem = get_user_memory(author.id, guild.id)
    grace = settings.get("grace_system", 1)
    is_first_minor = (user_mem.get("violation_count",0) == 0 and severity in ["low","medium"])
    if grace and is_first_minor and not skip_first_warn:
        increment_user_violation(author.id, guild.id)
        try:
            await message.channel.send(f"Hey {author.mention}, that's not cool here ({reason}). This is your one freebie - follow the rules from now on!", delete_after=15)
        except: pass
        log_recent_action(guild.id, "GRACE WARNING", author.display_name, reason, "First offense")
        return
    wc, wid = add_warning(author.id, guild.id, reason, severity, confidence, message.content[:200])
    log_mod_action(author.id, guild.id, "AUTO-DELETE", reason, bot.user.id)
    log_recent_action(guild.id, "DELETED + WARNED", author.display_name, reason, f"Warning #{wc}")
    increment_user_violation(author.id, guild.id)
    try:
        await message.channel.send(f"{author.mention} **{reason}** | Warning #{wc}", delete_after=12)
    except: pass
    warn_mute = settings.get("warn_mute",3)
    warn_ban = settings.get("warn_ban",5)
    mute_dur = settings.get("mute_duration",10)
    if severity == "critical" or wc >= warn_ban:
        try: await guild.ban(author, reason=f"Ban threshold ({wc} warnings)")
        except: pass
        log_recent_action(guild.id, "BANNED", author.display_name, f"{wc} warnings", reason)
        await notify_owner("BAN", f"Banned **{author}** ({wc} warnings)", guild=guild)
    elif severity == "high":
        try: await author.timeout(datetime.now() + timedelta(minutes=60), reason=reason)
        except: pass
        log_recent_action(guild.id, "MUTED 60min", author.display_name, reason)
    elif wc >= warn_mute:
        try: await author.timeout(datetime.now() + timedelta(minutes=mute_dur), reason=reason)
        except: pass
        log_recent_action(guild.id, f"MUTED {mute_dur}min", author.display_name, f"{wc} warnings")
    elif severity == "medium":
        try: await author.timeout(datetime.now() + timedelta(minutes=5), reason=reason)
        except: pass
    if severity in ["high","critical"]:
        await alert_mods(guild, discord.Embed(title=f"Auto-Mod: {severity.upper()}",color=discord.Color.red())
            .add_field(name="User",value=author.mention).add_field(name="Reason",value=reason)
            .add_field(name="Warnings",value=str(wc))
            .add_field(name="Content",value=f"||{message.content[:300]}||",inline=False))

async def handle_moderation_smart(message, settings):
    content = message.content
    author = message.author
    guild = message.guild
    if is_user_trusted(author.id, guild.id): return False
    if not settings.get("ai_mod_enabled",1): return False
    if has_mod_permissions(author, settings): return False
    if len(content.strip()) < 1: return False
    if detect_message_spam(guild.id, author.id, content):
        try: await message.delete()
        except: pass
        try: await author.timeout(datetime.now() + timedelta(minutes=5), reason="Repeating message")
        except: pass
        log_recent_action(guild.id, "MUTED (REPEAT)", author.display_name, "Repeating same message")
        return True
    if settings.get("swear_filter",1):
        has_swear, matched = contains_swear(content)
        if has_swear:
            await _delete_and_punish(message, f"Profanity: '{matched}'", "delete", settings, severity="medium")
            return True
    for pattern, reason, action in HARD_DELETE_PATTERNS:
        if re.search(pattern, content):
            await _delete_and_punish(message, reason, action, settings, severity="critical", skip_first_warn=True)
            return True
    for pattern, reason, severity in SOFT_VIOLATION_PATTERNS:
        if re.search(pattern, content):
            await _delete_and_punish(message, reason, "delete", settings, severity=severity, skip_first_warn=True)
            return True
    for pattern in SELF_HARM_PATTERNS:
        if re.search(pattern, content):
            try:
                await message.channel.send(embed=discord.Embed(
                    title="Hey, we see you",
                    description=f"{author.mention} You're not alone.\n**988** (US Suicide Lifeline)\nText **HOME** to **741741**\n[findahelpline.com](https://findahelpline.com)\nYou matter.",
                    color=discord.Color.blue()))
            except: pass
            return False
    if settings.get("smart_mode",1) and len(content.strip()) >= 8:
        context_msgs = []
        try:
            async for m in message.channel.history(limit=8, before=message):
                if not m.author.bot: context_msgs.append(f"{m.author.display_name}: {m.content[:120]}")
        except: pass
        user_mem = get_user_memory(author.id, guild.id)
        channel_type = "nsfw" if message.channel.is_nsfw() else "general"
        analysis = await smart_ai_moderation(content, author.display_name, message.channel.name, list(reversed(context_msgs)), user_mem, channel_type)
        action = analysis.get("action","ignore")
        confidence = analysis.get("confidence",0)
        severity = analysis.get("severity","low")
        reason = analysis.get("reason","Flagged")
        if action == "delete":
            await _delete_and_punish(message, reason, "delete", settings, severity=severity, confidence=confidence)
            return True
        if action == "warn":
            user_mem = get_user_memory(author.id, guild.id)
            if settings.get("grace_system", 1) and user_mem.get("violation_count",0) == 0:
                increment_user_violation(author.id, guild.id)
                try: await message.reply(f"Hey {author.mention}, please watch the tone. {reason}", delete_after=15)
                except: pass
            else:
                wc, _ = add_warning(author.id, guild.id, reason, severity, confidence, content[:200])
                log_mod_action(author.id, guild.id, "AI-WARN", reason, bot.user.id)
                increment_user_violation(author.id, guild.id)
                try: await message.reply(f"{author.mention} **{reason}** (Warning #{wc})", delete_after=15)
                except: pass
                if wc >= settings.get("warn_mute",3):
                    try: await author.timeout(datetime.now() + timedelta(minutes=settings.get("mute_duration",10)), reason=f"Warnings: {wc}")
                    except: pass
            return True
    if settings.get("invite_block",0) and detect_invite(content):
        await _delete_and_punish(message, "Discord invite", "delete", settings, severity="medium")
        return True
    if settings.get("link_scan",1) and detect_phishing_link(content):
        await _delete_and_punish(message, "Phishing link", "delete", settings, severity="high")
        return True
    if settings.get("email_filter",1) and re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', content):
        await _delete_and_punish(message, "Email shared", "delete", settings, severity="medium")
        return True
    if settings.get("phone_filter",0) and re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content):
        await _delete_and_punish(message, "Phone shared", "delete", settings, severity="medium")
        return True
    if settings.get("everyone_block",0) and ('@everyone' in content or '@here' in content) and not author.guild_permissions.mention_everyone:
        await _delete_and_punish(message, "Unauthorized @everyone", "delete", settings, severity="high")
        return True
    if settings.get("mention_spam",1) and len(set(m.id for m in message.mentions)) >= 5:
        await _delete_and_punish(message, "Mass mentions", "delete", settings, severity="high")
        return True
    if settings.get("caps_filter",0) and detect_caps_abuse(content):
        try:
            await message.delete()
            await message.channel.send(f"{author.mention} No excessive caps!", delete_after=6)
        except: pass
        return True
    if settings.get("emoji_spam",0) and detect_emoji_spam(content):
        await _delete_and_punish(message, "Emoji spam", "delete", settings, severity="low")
        return True
    if settings.get("zalgo_filter",0) and detect_zalgo(content):
        await _delete_and_punish(message, "Zalgo text", "delete", settings, severity="low")
        return True
    if settings.get("unicode_filter",0) and detect_unicode_abuse(content):
        await _delete_and_punish(message, "Unicode bypass", "delete", settings, severity="medium")
        return True
    if settings.get("nsfw_text_filter",0) and not message.channel.is_nsfw() and detect_nsfw_text(content):
        await _delete_and_punish(message, "NSFW in SFW", "delete", settings, severity="medium")
        return True
    if settings.get("anti_advertisement",0) and detect_advertisement(content):
        await _delete_and_punish(message, "Self-promotion", "delete", settings, severity="low")
        return True
    if settings.get("file_spam_filter",0) and message.attachments:
        now = time.time()
        key = f"{author.id}:{guild.id}"
        file_tracker[key] = [t for t in file_tracker[key] if now - t < 30]
        file_tracker[key].extend([now] * len(message.attachments))
        if len(file_tracker[key]) >= 5:
            await _delete_and_punish(message, "File spam", "delete", settings, severity="medium")
            file_tracker[key] = []
            return True
    words = get_filtered_words(guild.id)
    content_lower = content.lower()
    for w in words:
        if w.lower() in content_lower:
            await _delete_and_punish(message, f"Filtered word: {w}", "delete", settings, severity="medium")
            return True
    return False

async def alert_mods(guild, embed):
    s = get_guild_settings(guild.id)
    ch = discord.utils.get(guild.text_channels, name=s["log_channel"])
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    if ch:
        try: await ch.send(content=mr.mention if mr else "", embed=embed)
        except: pass

async def notify_owner(alert_type, message_text, guild=None, urgent=False):
    try:
        owner = await bot.fetch_user(BOT_IDENTITY["creator_discord_id"])
        if not owner: return
        colors = {"RAID":discord.Color.red(),"BAN":discord.Color.dark_red(),"CRITICAL":discord.Color.red(),
                  "JOIN":discord.Color.green(),"INFO":discord.Color.blue(),"MOD":discord.Color.orange()}
        embed = discord.Embed(title=f"{alert_type}{' [URGENT]' if urgent else ''}",description=message_text,
                              color=colors.get(alert_type.upper(),discord.Color.greyple()),timestamp=datetime.now())
        if guild: embed.add_field(name="Server",value=guild.name,inline=True)
        await owner.send(embed=embed)
    except: pass

async def check_spam(msg, s):
    key = f"{msg.author.id}:{msg.guild.id}"
    now = time.time()
    spam_tracker[key].append(now)
    spam_tracker[key] = [t for t in spam_tracker[key] if now - t < s.get("spam_window",5)]
    return len(spam_tracker[key]) >= s.get("spam_limit",5)

async def handle_spam(msg, s):
    try: await msg.channel.purge(limit=10, check=lambda m: m.author == msg.author)
    except: pass
    try: await msg.author.timeout(datetime.now() + timedelta(minutes=s.get("mute_duration",10)), reason="Spam")
    except: pass
    wc, _ = add_warning(msg.author.id, msg.guild.id, "Spam", "medium")
    log_recent_action(msg.guild.id, "MUTED (SPAM)", msg.author.display_name, f"Warning #{wc}")
    await alert_mods(msg.guild, discord.Embed(title="Spam Detected",color=discord.Color.orange())
        .add_field(name="User",value=msg.author.mention).add_field(name="Warnings",value=str(wc)))

async def check_raid(member):
    s = get_guild_settings(member.guild.id)
    now = time.time()
    raid_tracker[member.guild.id].append(now)
    raid_tracker[member.guild.id] = [t for t in raid_tracker[member.guild.id] if now - t < s.get("raid_window",10)]
    return len(raid_tracker[member.guild.id]) >= s.get("raid_limit",10)

async def handle_raid(guild, member):
    s = get_guild_settings(guild.id)
    if not raid_mode_active[guild.id]:
        raid_mode_active[guild.id] = True
        ch = discord.utils.get(guild.text_channels, name=s["raid_channel"])
        mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
        if ch: await ch.send(content=f"{mr.mention if mr else '@here'} RAID!", embed=discord.Embed(title="RAID DETECTED",color=discord.Color.red()))
        await notify_owner("RAID", f"Raid in **{guild.name}**!", guild=guild, urgent=True)
        async def reset():
            await asyncio.sleep(300)
            raid_mode_active[guild.id] = False
        asyncio.create_task(reset())
    age = (datetime.now() - member.created_at.replace(tzinfo=None)).days
    if age < s.get("min_account_age",7):
        try: await member.kick(reason="Raid protection")
        except: pass

# ============ VOICE ============
async def text_to_speech_bytes(text, lang="en"):
    try:
        import urllib.parse
        clean = re.sub(r'[*_`~|]','',text)
        clean = re.sub(r'<@[!&]?\d+>','someone',clean)[:400].strip()
        if not clean: return None
        encoded = urllib.parse.quote(clean)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded}&tl={lang}&client=tw-ob",headers={"User-Agent":"Mozilla/5.0"},timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200: return await resp.read()
    except: pass
    return None

async def start_voice_session(channel, guild_id, mode="file", text_channel=None):
    if guild_id in voice_sessions:
        if voice_sessions[guild_id].get("vc"):
            try: await voice_sessions[guild_id]["vc"].disconnect(force=True)
            except: pass
        del voice_sessions[guild_id]
    voice_sessions[guild_id] = {"mode":"file","channel_id":channel.id,"vc":None,"text_channel_id":text_channel.id if text_channel else None}
    return True, f"Voice active in **{channel.name}**"

async def end_voice_session(guild_id):
    if guild_id in voice_sessions:
        if voice_sessions[guild_id].get("vc"):
            try: await voice_sessions[guild_id]["vc"].disconnect(force=True)
            except: pass
        del voice_sessions[guild_id]
        return True
    return False

async def speak_in_session(guild_id, text, text_channel=None):
    if guild_id not in voice_sessions: return
    session = voice_sessions[guild_id]
    audio = await text_to_speech_bytes(text, get_guild_settings(guild_id).get("voice_language","en"))
    if not audio: return
    target = None
    if session.get("text_channel_id"): target = bot.get_channel(int(session["text_channel_id"]))
    if not target and text_channel: target = text_channel
    if target:
        try:
            embed = discord.Embed(description=f"**{text[:200]}**",color=0x5865F2)
            embed.set_author(name="SentinelMod Voice")
            await target.send(embed=embed, file=discord.File(io.BytesIO(audio), filename="voice.mp3"))
        except: pass

# ============ COMMAND PARSER ============
async def parse_command(content, guild, author):
    channels = [c.name for c in guild.text_channels][:15]
    categories = [c.name for c in guild.categories][:10]
    roles = [r.name for r in guild.roles if r.name != "@everyone"][:15]
    members = [f"{m.name}(ID:{m.id})" for m in guild.members if not m.bot][:25]
    mids = re.findall(r'<@!?(\d+)>', content)
    mnames = []
    for mid in mids:
        m = guild.get_member(int(mid))
        if m: mnames.append(f"{m.name}(ID:{mid})")
    all_servers = ""
    if is_owner(author.id):
        all_servers = "\n=== ALL SERVERS (Owner can target any) ===\n"
        for g in bot.guilds:
            all_servers += f"- {g.name} (ID:{g.id})\n"
    is_owner_user = is_owner(author.id)
    prompt = f"""Parse Discord command. CAREFUL: create vs delete are OPPOSITES.

CURRENT SERVER: {guild.name} (ID:{guild.id})
CHANNELS: {', '.join(channels)}
CATEGORIES: {', '.join(categories)}
ROLES: {', '.join(roles)}
MEMBERS: {', '.join(members[:15])}
MENTIONED: {', '.join(mnames) if mnames else 'NOBODY'}
SENDER: {author.name} {'(OWNER)' if is_owner_user else ''}
{all_servers}

USER MESSAGE: "{content}"

CRITICAL:
"create"/"make"/"add"/"new" = CREATE
"delete"/"remove"/"destroy" = DELETE
"ban"/"kick"/"mute" = PUNISHMENT

EXAMPLES:
"create a channel called gaming" -> create_channel name=gaming
"delete the channel gaming" -> delete_channel name=gaming
"ban @user" -> ban_user
"give @bob VIP role" -> add_role target=bob role_name=VIP

OWNER-ONLY:
"revoke license from [server]" -> revoke_license, target_guild_id=ID
"broadcast [message]" -> cross_announce, text=message
"list servers" -> list_servers
"control [server]: [action]" -> remote_command, target_guild_id=ID, text=action

RULES:
- Chat/question -> command="chat"
- confidence: 0.85+ if certain, 0.7+ if pretty sure
- DON'T confuse opposites

JSON only:
{{
  "command": "create_channel|delete_channel|create_role|delete_role|add_role|remove_role|create_category|delete_category|ban_user|kick_user|mute_user|unmute_user|warn_user|clear_warnings|warn_check|lock_channel|unlock_channel|lockdown|unlock_server|slowmode|purge|start_giveaway|create_poll|set_afk|setup_server|summarize|translate|add_word_filter|remove_word_filter|trivia|eightball|roast|compliment|dadjoke|ship|rate|fact|story|riddle|remind|rep|server_health|activity_stats|quarantine|unquarantine|trust_user|untrust_user|join_voice|leave_voice|memory_view|help|revoke_license|restore_license|leave_server|cross_announce|list_servers|server_info|remote_command|chat",
  "needs_confirmation": false,
  "confidence": 0.9,
  "params": {{
    "name": null, "target_user_id": null, "target_user_name": null, "target_user2": null,
    "target_guild_id": null, "target_guild_name": null,
    "reason": null, "duration": null, "category": null, "color": null,
    "amount": null, "prize": null, "winners": null, "question": null,
    "text": null, "word": null, "channel": null, "response": null, "title": null,
    "reminder_time": null, "rating_target": null, "role_name": null
  }}
}}"""
    return await ask_groq_json(prompt)

def find_member_strict(guild, params):
    uid = params.get("target_user_id")
    if uid:
        try:
            m = guild.get_member(int(str(uid).strip()))
            if m: return m
        except: pass
    name = params.get("target_user_name")
    if name:
        nc = name.lower().strip().replace("@","")
        for m in guild.members:
            if m.name.lower() == nc or m.display_name.lower() == nc: return m
        for m in guild.members:
            if nc in m.name.lower() or nc in m.display_name.lower(): return m
    return None

def find_guild_by_params(params):
    gid = params.get("target_guild_id")
    if gid:
        try:
            g = bot.get_guild(int(str(gid).strip()))
            if g: return g
        except: pass
    name = params.get("target_guild_name")
    if name:
        nc = name.lower().strip()
        for g in bot.guilds:
            if g.name.lower() == nc: return g
        for g in bot.guilds:
            if nc in g.name.lower(): return g
    return None

# ============ EXECUTE COMMANDS ============
async def execute_command(parsed, message, guild, author):
    cmd = parsed.get("command","chat")
    params = parsed.get("params",{}) or {}
    s = get_guild_settings(guild.id)
    try:
        # OWNER COMMANDS
        if cmd == "revoke_license":
            if not is_owner(author.id): return "Only the owner!"
            target = find_guild_by_params(params)
            if not target: return "Server not found!"
            reason = params.get("reason") or "Revoked by owner"
            revoke_license(target.id, reason)
            log_recent_action(guild.id, "LICENSE REVOKED", target.name, reason)
            try:
                for ch in target.text_channels:
                    if ch.permissions_for(target.me).send_messages:
                        await ch.send(embed=discord.Embed(title="License Revoked",description=f"This server's SentinelMod license has been revoked.\nReason: {reason}",color=discord.Color.red()))
                        break
            except: pass
            try:
                await target.leave()
                return f"License revoked and left **{target.name}**"
            except Exception as e: return f"Revoked but couldn't leave: {e}"
        
        elif cmd == "restore_license":
            if not is_owner(author.id): return "Owner only!"
            gid = params.get("target_guild_id")
            if not gid: return "Need server ID!"
            try:
                restore_license(int(gid))
                return f"License restored for server {gid}."
            except: return "Failed!"
        
        elif cmd == "leave_server":
            if not is_owner(author.id): return "Owner only!"
            target = find_guild_by_params(params)
            if not target: return "Server not found!"
            try:
                await target.leave()
                return f"Left **{target.name}**"
            except Exception as e: return f"Error: {e}"
        
        elif cmd == "cross_announce":
            if not is_owner(author.id): return "Owner only!"
            text = params.get("text") or params.get("question")
            title = params.get("title") or "Announcement from SentinelMod"
            if not text: return "What's the announcement?"
            success = fail = 0
            embed = discord.Embed(title=title, description=text, color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_footer(text=f"Cross-server | By {author.name}")
            for g in bot.guilds:
                if is_license_revoked(g.id): continue
                gs = get_guild_settings(g.id)
                ch = discord.utils.get(g.text_channels, name=gs.get("log_channel","sentinel-logs"))
                if not ch:
                    for fb in ["general","announcements","chat"]:
                        ch = discord.utils.get(g.text_channels, name=fb)
                        if ch and ch.permissions_for(g.me).send_messages: break
                if ch and ch.permissions_for(g.me).send_messages:
                    try: await ch.send(embed=embed); success += 1
                    except: fail += 1
                else: fail += 1
                await asyncio.sleep(0.5)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO cross_announcements (message, title, sent_at, success_count, fail_count) VALUES (?, ?, ?, ?, ?)",
                      (text, title, datetime.now().isoformat(), success, fail))
            conn.commit()
            conn.close()
            return f"Broadcast sent to {success} servers! ({fail} failed)"
        
        elif cmd == "list_servers":
            if not is_owner(author.id): return "Owner only!"
            lines = [f"**Total: {len(bot.guilds)} servers**\n"]
            for g in bot.guilds[:25]:
                status = " [REVOKED]" if is_license_revoked(g.id) else (" [LICENSED]" if is_license_accepted(g.id) else " [PENDING]")
                lines.append(f"- **{g.name}**{status} | ID: `{g.id}` | {g.member_count} members")
            if len(bot.guilds) > 25:
                lines.append(f"\n...and {len(bot.guilds)-25} more")
            embed = discord.Embed(title="All Servers", description="\n".join(lines), color=discord.Color.blue())
            await message.channel.send(embed=embed)
            return None
        
        elif cmd == "server_info":
            if not is_owner(author.id): return "Owner only!"
            target = find_guild_by_params(params)
            if not target: return "Server not found!"
            embed = discord.Embed(title=f"Server: {target.name}", color=discord.Color.blue())
            embed.add_field(name="ID", value=str(target.id))
            embed.add_field(name="Members", value=str(target.member_count))
            embed.add_field(name="Channels", value=str(len(target.text_channels)))
            embed.add_field(name="Roles", value=str(len(target.roles)-1))
            embed.add_field(name="Owner", value=str(target.owner) if target.owner else "Unknown")
            license_info = get_license_info(target.id)
            if is_license_revoked(target.id):
                embed.add_field(name="License", value="REVOKED")
            elif license_info:
                embed.add_field(name="License", value=f"Accepted by {license_info.get('accepted_by_name','?')}")
            else:
                embed.add_field(name="License", value="PENDING")
            sm = get_server_memory(target.id)
            embed.add_field(name="Mood", value=sm.get("server_mood","neutral"))
            await message.channel.send(embed=embed)
            return None
        
        elif cmd == "remote_command":
            if not is_owner(author.id): return "Owner only!"
            target = find_guild_by_params(params)
            if not target: return "Server not found!"
            action_text = params.get("text") or params.get("reason")
            if not action_text: return "What action?"
            class FakeMsg:
                def __init__(self, channel, author_obj):
                    self.channel = channel
                    self.author = author_obj
                    self.mentions = []
                    self.content = action_text
                async def reply(self, *args, **kwargs):
                    await self.channel.send(*args, **kwargs)
                async def delete(self): pass
            target_ch = None
            for ch in target.text_channels:
                if ch.permissions_for(target.me).send_messages:
                    target_ch = ch
                    break
            if not target_ch: return "No accessible channel!"
            try:
                fake_msg = FakeMsg(target_ch, target.me)
                sub_parsed = await parse_command(action_text, target, target.me)
                if sub_parsed and sub_parsed.get("command") not in ["chat",None]:
                    result = await execute_command(sub_parsed, fake_msg, target, target.me)
                    return f"Executed in **{target.name}**: {result or 'Done'}"
                return "Couldn't parse"
            except Exception as e: return f"Error: {e}"
        
        # REGULAR COMMANDS
        elif cmd == "join_voice":
            ch = None
            cn = params.get("channel") or params.get("name")
            if cn: ch = discord.utils.get(guild.voice_channels, name=cn)
            elif author.voice and author.voice.channel: ch = author.voice.channel
            if not ch: return "Join a voice channel first!"
            _, info = await start_voice_session(ch, guild.id, "file", message.channel)
            return info
        elif cmd == "leave_voice":
            if guild.id not in voice_sessions: return "Not in voice!"
            await end_voice_session(guild.id)
            return "Voice ended!"
        elif cmd == "create_channel":
            name = params.get("name")
            if not name: return "What should I name it?"
            name = name.lower().replace(" ","-").strip()
            if discord.utils.get(guild.text_channels, name=name): return f"#{name} exists!"
            cat = None
            if params.get("category"):
                cat = discord.utils.get(guild.categories, name=params["category"])
            try:
                ch = await guild.create_text_channel(name=name, category=cat)
                log_recent_action(guild.id, "CREATED CHANNEL", f"#{name}", f"By {author.display_name}")
                return f"Created {ch.mention}!"
            except discord.Forbidden: return "Need Manage Channels permission!"
        elif cmd == "delete_channel":
            name = params.get("name")
            if not name: return "Which channel?"
            ch = discord.utils.get(guild.text_channels, name=name.lower().replace(" ","-").strip())
            if not ch: return f"Not found."
            try:
                await ch.delete()
                log_recent_action(guild.id, "DELETED CHANNEL", f"#{name}", f"By {author.display_name}")
                return f"Deleted!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "create_category":
            name = params.get("name")
            if not name: return "Name?"
            try:
                await guild.create_category(name=name.strip())
                return f"Created **{name}**!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "delete_category":
            name = params.get("name")
            if not name: return "Which?"
            cat = discord.utils.get(guild.categories, name=name)
            if not cat: return "Not found."
            try:
                await cat.delete()
                return f"Deleted!"
            except: return "Failed!"
        elif cmd == "create_role":
            name = params.get("name")
            if not name: return "Name?"
            if discord.utils.get(guild.roles, name=name): return f"Exists!"
            color = discord.Color.default()
            if params.get("color"):
                try: color = discord.Color(int(params["color"].replace("#",""),16))
                except: pass
            try:
                role = await guild.create_role(name=name, color=color)
                log_recent_action(guild.id, "CREATED ROLE", name, f"By {author.display_name}")
                return f"Created {role.mention}!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "delete_role":
            name = params.get("name")
            if not name: return "Which?"
            role = discord.utils.get(guild.roles, name=name)
            if not role: return "Not found."
            try:
                await role.delete()
                log_recent_action(guild.id, "DELETED ROLE", name, f"By {author.display_name}")
                return f"Deleted!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "add_role":
            t = find_member_strict(guild, params)
            if not t: t = author
            rn = params.get("role_name") or params.get("name")
            if not rn: return "Which role?"
            role = discord.utils.get(guild.roles, name=rn)
            if not role: return "Not found."
            try:
                await t.add_roles(role)
                return f"Gave {role.mention} to **{t.name}**!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "remove_role":
            t = find_member_strict(guild, params)
            if not t: t = author
            rn = params.get("role_name") or params.get("name")
            role = discord.utils.get(guild.roles, name=rn)
            if not role: return "Not found."
            try:
                await t.remove_roles(role)
                return f"Removed!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "ban_user":
            t = find_member_strict(guild, params)
            if not t: return "User not found! @mention them."
            if t.id == author.id: return "Can't ban yourself!"
            reason = params.get("reason") or "No reason"
            try: await t.send(f"Banned from **{guild.name}**: {reason}")
            except: pass
            try:
                await guild.ban(t, reason=f"{reason} | By: {author}", delete_message_days=1)
                log_mod_action(t.id, guild.id, "BAN", reason, author.id)
                log_recent_action(guild.id, "BANNED", t.display_name, reason, f"By {author.display_name}")
                await notify_owner("BAN", f"**{t}** banned: {reason}", guild=guild)
                return f"Banned **{t.name}**!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "kick_user":
            t = find_member_strict(guild, params)
            if not t: return "Not found!"
            reason = params.get("reason") or "No reason"
            try:
                await guild.kick(t, reason=f"{reason} | By: {author}")
                log_mod_action(t.id, guild.id, "KICK", reason, author.id)
                log_recent_action(guild.id, "KICKED", t.display_name, reason)
                return f"Kicked **{t.name}**!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "mute_user":
            t = find_member_strict(guild, params)
            if not t: return "Not found!"
            dur = min(int(params.get("duration") or s.get("mute_duration",10)), 40320)
            reason = params.get("reason") or "No reason"
            try:
                await t.timeout(datetime.now() + timedelta(minutes=dur), reason=f"{reason} | By: {author}")
                log_mod_action(t.id, guild.id, "MUTE", reason, author.id)
                log_recent_action(guild.id, f"MUTED {dur}min", t.display_name, reason)
                return f"Muted **{t.name}** for {dur}min!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "unmute_user":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            try:
                await t.timeout(None)
                return f"Unmuted **{t.name}**!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "warn_user":
            t = find_member_strict(guild, params)
            if not t: return "Not found!"
            reason = params.get("reason") or "No reason"
            wc, _ = add_warning(t.id, guild.id, reason, "manual")
            log_mod_action(t.id, guild.id, "WARN", reason, author.id)
            return f"Warned **{t.name}** (#{wc})"
        elif cmd == "clear_warnings":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            clear_warnings(t.id, guild.id)
            return f"Cleared warnings for **{t.name}**!"
        elif cmd == "warn_check":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            ws = get_warnings(t.id, guild.id)
            if not ws: return f"**{t.name}** is clean!"
            lines = [f"#{i+1} [{w['severity']}] {w['reason']}" for i, w in enumerate(ws[:5])]
            return f"**{t.name}** has {len(ws)} warnings:\n" + "\n".join(lines)
        elif cmd == "lock_channel":
            try:
                await message.channel.set_permissions(guild.default_role, send_messages=False)
                return "Locked!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "unlock_channel":
            try:
                await message.channel.set_permissions(guild.default_role, send_messages=None)
                return "Unlocked!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "lockdown":
            count = 0
            for ch in guild.text_channels:
                try: await ch.set_permissions(guild.default_role, send_messages=False); count += 1
                except: pass
            await notify_owner("MOD", f"Lockdown in **{guild.name}**", guild=guild, urgent=True)
            return f"Locked {count} channels!"
        elif cmd == "unlock_server":
            count = 0
            for ch in guild.text_channels:
                try: await ch.set_permissions(guild.default_role, send_messages=None); count += 1
                except: pass
            return f"Unlocked {count} channels!"
        elif cmd == "slowmode":
            dur = max(0, min(int(params.get("duration") or 5), 21600))
            try:
                await message.channel.edit(slowmode_delay=dur)
                return f"Slowmode: {dur}s!" if dur else "Off!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "purge":
            amt = min(int(params.get("amount") or 10), 100)
            try:
                deleted = await message.channel.purge(limit=amt + 1)
                return f"Deleted {len(deleted)-1} messages!"
            except discord.Forbidden: return "No permission!"
        elif cmd == "quarantine":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            q = discord.utils.get(guild.roles, name="Quarantined")
            if not q:
                try:
                    q = await guild.create_role(name="Quarantined", color=discord.Color.dark_gray())
                    for ch in guild.text_channels:
                        try: await ch.set_permissions(q, send_messages=False, read_messages=False)
                        except: pass
                except: return "Failed!"
            await t.add_roles(q)
            return f"Quarantined!"
        elif cmd == "unquarantine":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            q = discord.utils.get(guild.roles, name="Quarantined")
            if q and q in t.roles: await t.remove_roles(q)
            return "Unquarantined!"
        elif cmd == "trust_user":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO trusted_users VALUES (?,?,?,?,?)", (str(t.id),str(guild.id),str(author.id),"Trusted",datetime.now().isoformat()))
            conn.commit(); conn.close()
            return f"**{t.name}** trusted!"
        elif cmd == "untrust_user":
            t = find_member_strict(guild, params)
            if not t: return "Not found."
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM trusted_users WHERE user_id=? AND guild_id=?", (str(t.id),str(guild.id)))
            conn.commit(); conn.close()
            return "Untrusted!"
        elif cmd == "memory_view":
            sm = get_server_memory(guild.id)
            embed = discord.Embed(title=f"Memory: {guild.name}", color=discord.Color.purple())
            if sm.get("inside_jokes"): embed.add_field(name="Jokes", value="\n".join(f"- {j['text']}" for j in sm["inside_jokes"][-5:])[:400], inline=False)
            if sm.get("popular_topics"): embed.add_field(name="Topics", value=", ".join(sm["popular_topics"][:10]), inline=False)
            embed.add_field(name="Mood", value=sm.get("server_mood","neutral").title())
            await message.channel.send(embed=embed)
            return None
        elif cmd == "trivia":
            trivia = await ask_groq_json('Trivia. JSON: {"question":"q","correct":"a","wrong1":"b","wrong2":"c","wrong3":"d","category":"cat"}')
            if not trivia: return "Failed!"
            answers = [trivia["correct"],trivia["wrong1"],trivia["wrong2"],trivia["wrong3"]]
            random.shuffle(answers)
            idx = answers.index(trivia["correct"])
            emojis = ["A","B","C","D"]
            embed = discord.Embed(title=f"{trivia.get('category','Trivia')}", description=f"**{trivia['question']}**", color=discord.Color.blue())
            embed.add_field(name="Options:", value="\n".join(f"{emojis[i]}: {a}" for i, a in enumerate(answers)))
            msg = await message.channel.send(embed=embed)
            reactions = ["🇦","🇧","🇨","🇩"]
            for e in reactions: await msg.add_reaction(e)
            trivia_sessions[msg.id] = {"correct_emoji":reactions[idx],"correct_answer":trivia["correct"],"guild_id":guild.id,"answered":[]}
            async def timeout():
                await asyncio.sleep(30)
                if msg.id in trivia_sessions:
                    await message.channel.send(f"Time's up! Answer: **{trivia['correct']}**")
                    del trivia_sessions[msg.id]
            asyncio.create_task(timeout())
            return None
        elif cmd in ["eightball","roast","compliment","dadjoke","ship","rate","fact","story","riddle"]:
            prompts = {
                "eightball":(f"Mystical 8-ball (clean): '{params.get('question','?')}'","8-Ball"),
                "roast":(f"Clean funny roast of {params.get('target_user_name','someone')}","Roasted"),
                "compliment":(f"Compliment for {params.get('target_user_name',author.name)}","Compliment"),
                "dadjoke":("Best dad joke, clean","Dad Joke"),
                "ship":(f"Ship {params.get('target_user_name','A')} and {params.get('target_user2','B')}","Ship"),
                "rate":(f"Rate '{params.get('rating_target','this')}' /10","Rating"),
                "fact":("Mind-blowing fact","Fact"),
                "story":(f"Short clean story max 150 words {('about: ' + params.get('text','')) if params.get('text') else ''}","Story"),
                "riddle":("Clever riddle and answer","Riddle"),
            }
            p, title = prompts.get(cmd, ("Joke","Fun"))
            result = await smart_ai(p, "Fun bot, NEVER swear")
            if result:
                await message.channel.send(embed=discord.Embed(title=title, description=sanitize_bot_response(result), color=discord.Color.purple()))
            return None
        elif cmd == "remind":
            text = params.get("text") or "Reminder!"
            mins = int(params.get("reminder_time") or params.get("duration") or 10)
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reminders (user_id,guild_id,channel_id,reminder,remind_time) VALUES (?,?,?,?,?)",
                      (str(author.id),str(guild.id),str(message.channel.id),text,(datetime.now()+timedelta(minutes=mins)).isoformat()))
            conn.commit(); conn.close()
            return f"Reminder in {mins}min: **{text}**"
        elif cmd == "set_afk":
            reason = params.get("reason") or "AFK"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO afk_users VALUES (?,?,?,?)", (str(author.id),str(guild.id),reason,datetime.now().isoformat()))
            conn.commit(); conn.close()
            return f"AFK: **{reason}**"
        elif cmd == "rep":
            t = find_member_strict(guild, params)
            if not t: return "@mention someone!"
            if t.id == author.id: return "Can't rep yourself!"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO reputation VALUES (?,?,1) ON CONFLICT DO UPDATE SET rep=rep+1", (str(t.id),str(guild.id)))
            conn.commit()
            c.execute("SELECT rep FROM reputation WHERE user_id=? AND guild_id=?", (str(t.id),str(guild.id)))
            rep = c.fetchone()[0]; conn.close()
            return f"+1 to **{t.name}**! Total: **{rep}**"
        elif cmd == "start_giveaway":
            prize = params.get("prize") or "Mystery Prize"
            dur = int(params.get("duration") or 60)
            wins = int(params.get("winners") or 1)
            end = datetime.now() + timedelta(minutes=dur)
            embed = discord.Embed(title="GIVEAWAY!",description=f"**{prize}**\nReact to enter!",color=discord.Color.gold())
            embed.add_field(name="Ends",value=f"<t:{int(end.timestamp())}:R>")
            gm = await message.channel.send(embed=embed)
            await gm.add_reaction("🎉")
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO giveaways (guild_id,channel_id,message_id,prize,winners,end_time,host_id) VALUES (?,?,?,?,?,?,?)",
                      (str(guild.id),str(message.channel.id),str(gm.id),prize,wins,end.isoformat(),str(author.id)))
            conn.commit(); conn.close()
            return "Giveaway started!"
        elif cmd == "create_poll":
            q = params.get("question") or "?"
            opts = params.get("options") or ["Yes","No"]
            if isinstance(opts,str): opts = [o.strip() for o in opts.split(",")]
            emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
            embed = discord.Embed(title=f"Poll: {q}",description="\n".join(f"{emojis[i]} {o}" for i,o in enumerate(opts[:5])),color=discord.Color.blue())
            pm = await message.channel.send(embed=embed)
            for i in range(min(len(opts),5)): await pm.add_reaction(emojis[i])
            return None
        elif cmd == "summarize":
            msgs = []
            async for m in message.channel.history(limit=min(int(params.get("amount") or 20),50)):
                if not m.author.bot: msgs.append(f"{m.author.display_name}: {m.content[:200]}")
            if not msgs: return "No messages!"
            result = await smart_ai("Summarize in bullets:\n"+"\n".join(reversed(msgs)),"Summarizer, clean")
            return f"**Summary:**\n{sanitize_bot_response(result)}"
        elif cmd == "translate":
            text = params.get("text") or ""
            lang = params.get("language") or "English"
            if not text: return "No text!"
            result = await smart_ai(f"Translate to {lang}, ONLY translation:\n{text}","Translator")
            return f"**{lang}:** {result}"
        elif cmd == "add_word_filter":
            w = params.get("word") or params.get("text")
            if not w: return "Which?"
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO word_filters VALUES (?,?)", (str(guild.id),w.lower().strip()))
            conn.commit(); conn.close()
            return f"**{w}** filtered!"
        elif cmd == "remove_word_filter":
            w = params.get("word") or params.get("text")
            if not w: return "Which?"
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (str(guild.id),w.lower().strip()))
            conn.commit(); conn.close()
            return "Removed!"
        elif cmd == "setup_server":
            await message.channel.send("Setting up...")
            results = await setup_server(guild)
            return "Done!\n" + "\n".join(results[:15])
        elif cmd == "server_health":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (str(guild.id),))
            wc = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id=?", (str(guild.id),))
            ac = c.fetchone()[0]; conn.close()
            score = max(0,100-(wc*2))
            embed = discord.Embed(title=f"{guild.name} Health",color=discord.Color.green() if score>70 else discord.Color.orange() if score>40 else discord.Color.red())
            embed.add_field(name="Score",value=f"{score}/100").add_field(name="Members",value=str(guild.member_count))
            embed.add_field(name="Warnings",value=str(wc)).add_field(name="Actions",value=str(ac))
            await message.channel.send(embed=embed)
            return None
        elif cmd == "activity_stats":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT user_id,message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 10", (str(guild.id),))
            top = c.fetchall(); conn.close()
            if not top: return "No data!"
            medals = ["1st","2nd","3rd"]
            lines = []
            for i, r in enumerate(top):
                m = guild.get_member(int(r['user_id']))
                name = m.display_name if m else 'Unknown'
                rank = medals[i] if i < 3 else f"#{i+1}"
                lines.append(f"{rank} **{name}**: {r['message_count']:,}")
            await message.channel.send(embed=discord.Embed(title="Most Active",description="\n".join(lines),color=discord.Color.blue()))
            return None
        elif cmd == "help":
            embed = discord.Embed(title="SentinelMod v8.1 - License Edition",description="Self-aware AI bot with license system",color=discord.Color.blue())
            embed.add_field(name="Chat",value=f"@mention or use #{AI_CHAT_CHANNEL}",inline=False)
            embed.add_field(name="Mod",value="`ban/kick/mute/warn @user` | `purge 50` | `lock`",inline=False)
            embed.add_field(name="Server",value="`create channel/role/category X` | `setup server`",inline=False)
            embed.add_field(name="Fun",value="`trivia` | `roast` | `8ball` | `story`",inline=False)
            if is_owner(author.id):
                embed.add_field(name="OWNER",value="`revoke license` | `broadcast` | `list servers` | `control [server]: [action]`",inline=False)
            await message.channel.send(embed=embed)
            return None
        else: return None
    except discord.Forbidden: return "I don't have permission!"
    except Exception as e:
        print(f"Cmd err: {e}")
        return f"Error: {str(e)[:100]}"

async def setup_server(guild):
    results = []
    s = get_guild_settings(guild.id)
    for rn,c,h in [(s["mod_role_name"],discord.Color.red(),True),("Muted",discord.Color.dark_gray(),False),("Quarantined",discord.Color.dark_gray(),False),("Trusted",discord.Color.green(),False)]:
        if not discord.utils.get(guild.roles, name=rn):
            try: await guild.create_role(name=rn, color=c, hoist=h); results.append(f"Role: {rn}")
            except: results.append(f"Failed: {rn}")
    mr = discord.utils.get(guild.roles, name=s["mod_role_name"])
    scat = discord.utils.get(guild.categories, name="SENTINELAI")
    if not scat:
        try:
            ow = {guild.default_role:discord.PermissionOverwrite(read_messages=False),guild.me:discord.PermissionOverwrite(read_messages=True,send_messages=True)}
            if mr: ow[mr] = discord.PermissionOverwrite(read_messages=True,send_messages=True)
            scat = await guild.create_category(name="SENTINELAI", overwrites=ow)
            results.append("Category created")
        except: scat = None
    for cn in [s["log_channel"],s["raid_channel"],"sentinel-bot"]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try: await guild.create_text_channel(name=cn, category=scat); results.append(f"#{cn}")
            except: pass
    for cn in ["welcome","rules","general"]:
        if not discord.utils.get(guild.text_channels, name=cn):
            try: await guild.create_text_channel(name=cn); results.append(f"#{cn}")
            except: pass
    return results

class ConfirmView(discord.ui.View):
    def __init__(self, parsed, msg, guild, author):
        super().__init__(timeout=30)
        self.parsed=parsed; self.msg=msg; self.guild=guild; self.author=author; self.done=False
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.author.id: await interaction.response.send_message("Not yours!",ephemeral=True); return
        if self.done: return
        self.done = True
        await interaction.response.defer()
        r = await execute_command(self.parsed, self.msg, self.guild, self.author)
        if r: await interaction.followup.send(r)
        self.stop()
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction, button):
        if interaction.user.id != self.author.id: await interaction.response.send_message("Not yours!",ephemeral=True); return
        await interaction.response.send_message("Cancelled."); self.done=True; self.stop()

# ============ SLASH COMMANDS ============
@bot.tree.command(name="ai_mod",description="[Admin] Toggle AI mod")
@app_commands.choices(state=[app_commands.Choice(name="ON",value="on"),app_commands.Choice(name="OFF",value="off")])
async def ai_mod_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
    if not i.user.guild_permissions.administrator: await i.response.send_message("Admin only!",ephemeral=True); return
    update_guild_setting(i.guild.id,"ai_mod_enabled",1 if state.value=="on" else 0)
    await i.response.send_message(f"AI Mod **{state.name}**",ephemeral=True)

@bot.tree.command(name="license_info",description="View this server's license info")
async def license_info_cmd(i: discord.Interaction):
    info = get_license_info(i.guild.id)
    embed = discord.Embed(title="License Information", color=discord.Color.blue())
    if is_license_revoked(i.guild.id):
        embed.add_field(name="Status", value="REVOKED by owner", inline=False)
    elif info:
        embed.add_field(name="Status", value="ACTIVE", inline=False)
        embed.add_field(name="Accepted by", value=info.get("accepted_by_name","?"), inline=True)
        embed.add_field(name="Accepted at", value=info.get("accepted_at","?")[:16], inline=True)
    else:
        embed.add_field(name="Status", value="PENDING", inline=False)
    embed.set_footer(text=f"SentinelMod v{BOT_IDENTITY['version']}")
    await i.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="swear_filter",description="[Admin] Toggle swear filter")
@app_commands.choices(state=[app_commands.Choice(name="ON",value="on"),app_commands.Choice(name="OFF",value="off")])
async def swear_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
    if not i.user.guild_permissions.administrator: await i.response.send_message("Admin only!",ephemeral=True); return
    update_guild_setting(i.guild.id,"swear_filter",1 if state.value=="on" else 0)
    await i.response.send_message(f"Swear filter **{state.name}**",ephemeral=True)

@bot.tree.command(name="grace",description="[Admin] Toggle grace system")
@app_commands.choices(state=[app_commands.Choice(name="ON",value="on"),app_commands.Choice(name="OFF",value="off")])
async def grace_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
    if not i.user.guild_permissions.administrator: await i.response.send_message("Admin only!",ephemeral=True); return
    update_guild_setting(i.guild.id,"grace_system",1 if state.value=="on" else 0)
    await i.response.send_message(f"Grace **{state.name}**",ephemeral=True)

@bot.tree.command(name="trust_user",description="[Admin] Trust user")
async def trust_cmd(i: discord.Interaction, user: discord.Member):
    if not i.user.guild_permissions.administrator: await i.response.send_message("Admin only!",ephemeral=True); return
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO trusted_users VALUES (?,?,?,?,?)", (str(user.id),str(i.guild.id),str(i.user.id),"Trusted",datetime.now().isoformat()))
    conn.commit(); conn.close()
    await i.response.send_message(f"**{user.name}** trusted!",ephemeral=True)

@bot.tree.command(name="personality",description="Choose personality")
async def personality_cmd(i: discord.Interaction):
    opts = [discord.SelectOption(label=n.replace("_"," ").title(),value=n) for n in list(PERSONALITIES.keys())[:25]]
    view = discord.ui.View(timeout=60)
    select = discord.ui.Select(placeholder="Pick...",options=opts)
    async def cb(inter):
        p = inter.data["values"][0]
        set_user_personality(str(inter.user.id),str(inter.guild.id),p)
        await inter.response.send_message(f"**{p}** set!",ephemeral=True)
    select.callback = cb; view.add_item(select)
    await i.response.send_message(embed=discord.Embed(title="Personality",color=discord.Color.purple()),view=view,ephemeral=True)

@bot.tree.command(name="about",description="About SentinelMod")
async def about_cmd(i: discord.Interaction):
    embed = discord.Embed(title=f"SentinelMod v{BOT_IDENTITY['version']} - License Edition",description="Self-aware AI with license system",color=discord.Color.blue())
    embed.add_field(name="Creator",value=BOT_IDENTITY["creator_username"])
    embed.add_field(name="Servers",value=str(len(bot.guilds)))
    embed.add_field(name="Mode",value="Sovereign + Licensed")
    await i.response.send_message(embed=embed)

# Owner slash commands
@bot.tree.command(name="revoke",description="[Owner] Revoke a server's license")
async def revoke_cmd(i: discord.Interaction, server_id: str, reason: str = "Revoked by owner"):
    if not is_owner(i.user.id): await i.response.send_message("Owner only!",ephemeral=True); return
    try:
        gid = int(server_id)
        target = bot.get_guild(gid)
        if not target: await i.response.send_message("Server not found!",ephemeral=True); return
        revoke_license(gid, reason)
        try: await target.leave()
        except: pass
        await i.response.send_message(f"Revoked **{target.name}**!",ephemeral=True)
    except ValueError: await i.response.send_message("Invalid ID!",ephemeral=True)

@bot.tree.command(name="broadcast",description="[Owner] Send to all servers")
async def broadcast_cmd(i: discord.Interaction, message: str, title: str = "Announcement"):
    if not is_owner(i.user.id): await i.response.send_message("Owner only!",ephemeral=True); return
    await i.response.defer(ephemeral=True)
    success = fail = 0
    embed = discord.Embed(title=title, description=message, color=discord.Color.blue(), timestamp=datetime.now())
    embed.set_footer(text=f"Cross-server | By {i.user.name}")
    for g in bot.guilds:
        if is_license_revoked(g.id): continue
        gs = get_guild_settings(g.id)
        ch = discord.utils.get(g.text_channels, name=gs.get("log_channel","sentinel-logs"))
        if not ch:
            for fb in ["general","announcements","chat"]:
                ch = discord.utils.get(g.text_channels, name=fb)
                if ch and ch.permissions_for(g.me).send_messages: break
        if ch and ch.permissions_for(g.me).send_messages:
            try: await ch.send(embed=embed); success += 1
            except: fail += 1
        else: fail += 1
        await asyncio.sleep(0.5)
    await i.followup.send(f"Sent to {success}, failed {fail}!",ephemeral=True)

# ============ BACKGROUND TASKS ============
@tasks.loop(hours=1)
async def server_memory_extraction():
    for guild in bot.guilds:
        try:
            s = get_guild_settings(guild.id)
            if s.get("memory_mode") in ["server","both"]:
                await extract_server_memory(guild.id)
                await asyncio.sleep(2)
        except: pass

@tasks.loop(hours=24)
async def memory_cleanup():
    for guild in bot.guilds:
        try:
            s = get_guild_settings(guild.id)
            cutoff = (datetime.now() - timedelta(days=s.get("memory_retention_days",90))).isoformat()
            conn = get_db(); c = conn.cursor()
            c.execute("DELETE FROM message_archive WHERE guild_id=? AND timestamp<?", (str(guild.id),cutoff))
            c.execute("DELETE FROM conversation_history WHERE guild_id=? AND timestamp<?", (str(guild.id),cutoff))
            conn.commit(); conn.close()
        except: pass

@tasks.loop(minutes=1)
async def check_giveaways():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM giveaways WHERE active=1 AND end_time<=?", (datetime.now().isoformat(),))
    ended = [dict(r) for r in c.fetchall()]; conn.close()
    for g in ended:
        try:
            guild = bot.get_guild(int(g["guild_id"]))
            if not guild: continue
            ch = guild.get_channel(int(g["channel_id"]))
            if not ch: continue
            try:
                msg = await ch.fetch_message(int(g["message_id"]))
                r = discord.utils.get(msg.reactions, emoji="🎉")
                users = [u async for u in r.users() if not u.bot] if r else []
            except: users = []
            if users:
                winners = random.sample(users, min(g["winners"],len(users)))
                mention = ", ".join(x.mention for x in winners)
                await ch.send(f"{mention}!",embed=discord.Embed(title="Giveaway Ended!",description=f"**{g['prize']}**\n{mention}",color=discord.Color.gold()))
            conn = get_db(); c2 = conn.cursor()
            c2.execute("UPDATE giveaways SET active=0 WHERE id=?", (g["id"],)); conn.commit(); conn.close()
        except: pass

@tasks.loop(minutes=1)
async def check_reminders():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM reminders WHERE active=1 AND remind_time<=?", (datetime.now().isoformat(),))
    due = [dict(r) for r in c.fetchall()]
    for rem in due:
        try:
            ch = bot.get_channel(int(rem["channel_id"]))
            if ch: await ch.send(f"<@{rem['user_id']}>: **{rem['reminder']}**")
        except: pass
        c.execute("UPDATE reminders SET active=0 WHERE id=?", (rem["id"],))
    conn.commit(); conn.close()

# ============ EVENTS ============
@bot.event
async def on_ready():
    print(f"{bot.user} ONLINE | {len(bot.guilds)} servers | v{BOT_IDENTITY['version']}")
    print(f"LICENSE EDITION: ACTIVE")
    BOT_IDENTITY["bot_id"] = bot.user.id
    load_revoked_servers()
    load_accepted_licenses()
    
    # Check each guild - leave revoked, prompt unlicensed
    for g in bot.guilds:
        if is_license_revoked(g.id):
            print(f"License revoked for {g.name}, leaving...")
            try: await g.leave()
            except: pass
            continue
        if not is_license_accepted(g.id):
            print(f"No license for {g.name}, sending agreement...")
            asyncio.create_task(send_license_agreement(g))
            continue
        init_guild_settings(g.id)
    
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commands synced")
    except: pass
    for task in [server_memory_extraction,memory_cleanup,check_giveaways,check_reminders]:
        if not task.is_running(): task.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=f"v{BOT_IDENTITY['version']} | Licensed"))
    await notify_owner("INFO", f"v{BOT_IDENTITY['version']} ONLINE - License Edition!")

@bot.event
async def on_guild_join(guild):
    """When bot joins a new server - send license agreement."""
    print(f"Joined new server: {guild.name} ({guild.id})")
    
    # Check if revoked
    if is_license_revoked(guild.id):
        print(f"Tried to join revoked server {guild.name} - leaving")
        try:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    await ch.send(embed=discord.Embed(title="Access Denied",description="This server's SentinelMod license has been revoked by the bot owner.",color=discord.Color.red()))
                    break
        except: pass
        await guild.leave()
        return
    
    # Notify owner of join
    await notify_owner("JOIN", f"Bot added to **{guild.name}** ({guild.member_count} members) - Sending license...", guild=guild)
    
    # Send license agreement (this handles everything)
    await send_license_agreement(guild)

@bot.event
async def on_guild_remove(guild):
    """When bot is removed from server."""
    print(f"Removed from {guild.name}")
    # Clean up pending license if any
    if guild.id in pending_licenses:
        del pending_licenses[guild.id]
    await notify_owner("INFO", f"Removed from **{guild.name}**", guild=guild)

@bot.event
async def on_member_join(member):
    g = member.guild
    if not is_license_accepted(g.id): return  # Skip if license not accepted
    s = get_guild_settings(g.id)
    today = datetime.now().date().isoformat()
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO daily_stats (guild_id,date,joins) VALUES (?,?,1) ON CONFLICT DO UPDATE SET joins=joins+1", (str(g.id),today))
    conn.commit(); conn.close()
    if await check_raid(member): await handle_raid(g, member); return
    if s.get("welcome_enabled",1):
        wch = discord.utils.get(g.text_channels, name=s.get("welcome_channel","welcome"))
        if wch:
            try:
                w = await smart_ai(f"Warm 2-sentence welcome for {member.display_name} joining {g.name}. Clean.","Greeter")
                embed = discord.Embed(title="Welcome!",description=sanitize_bot_response(w) or f"Welcome {member.display_name}!",color=discord.Color.green())
                embed.set_thumbnail(url=member.display_avatar.url)
                await wch.send(content=member.mention, embed=embed)
            except: pass

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    if reaction.message.id in trivia_sessions:
        s = trivia_sessions[reaction.message.id]
        if user.id in s["answered"]: return
        s["answered"].append(user.id)
        if str(reaction.emoji) == s["correct_emoji"]:
            await reaction.message.channel.send(f"{user.mention} correct! **{s['correct_answer']}**")
            del trivia_sessions[reaction.message.id]

async def handle_appeal(message):
    if message.guild: return False
    if not message.content.strip().lower().startswith("appeal"): return False
    match = re.match(r'(?i)appeal\s+(\d+)\s*(.*)', message.content.strip(), re.DOTALL)
    if not match: await message.reply("Format: `appeal [id] [reason]`"); return True
    wid = int(match.group(1)); text = match.group(2).strip() or "No reason"
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM warnings WHERE id=? AND user_id=?", (wid,str(message.author.id)))
    w = c.fetchone()
    if not w: await message.reply("Not found."); conn.close(); return True
    if w["appealed"]: await message.reply("Already appealed."); conn.close(); return True
    ai_review = await ask_groq_json(f"""User appealing warning. JSON: {{"recommendation":"accept|deny|review","reasoning":"why"}}
Original: {w['reason']} (severity: {w['severity']})
Context: {w['context']}
Appeal: {text}""")
    ai_rec = "review"
    if ai_review: ai_rec = ai_review.get("recommendation","review")
    c.execute("INSERT INTO appeals (user_id,guild_id,warning_id,appeal_text,ai_recommendation,timestamp) VALUES (?,?,?,?,?,?)",
              (str(message.author.id),w["guild_id"],wid,text,ai_rec,datetime.now().isoformat()))
    c.execute("UPDATE warnings SET appealed=1 WHERE id=?", (wid,))
    conn.commit(); conn.close()
    await message.reply(f"Appeal submitted for #{wid}! AI suggests: **{ai_rec}**.")
    guild = bot.get_guild(int(w["guild_id"]))
    if guild:
        await alert_mods(guild, discord.Embed(title="Appeal",color=discord.Color.gold())
            .add_field(name="User",value=f"<@{message.author.id}>").add_field(name="Warning",value=str(wid))
            .add_field(name="Original",value=w["reason"]).add_field(name="Appeal",value=text[:500],inline=False)
            .add_field(name="AI",value=ai_rec,inline=False))
    return True

@bot.event
async def on_message(message):
    if message.author.bot: return
    if not message.guild: await handle_appeal(message); return
    
    # Check license status
    if is_license_revoked(message.guild.id):
        try: await message.guild.leave()
        except: pass
        return
    
    # If no license yet, only allow license-related interactions
    if not is_license_accepted(message.guild.id):
        # Don't moderate, don't respond to chat - just wait for license
        return
    
    update_live_context(message.guild.id, message.channel.id, message.author.display_name, message.author.id, message.content)
    s = get_guild_settings(message.guild.id)
    guild = message.guild
    author = message.author
    owner_talking = is_owner(author.id)
    is_mod = has_mod_permissions(author, s)
    
    update_message_stats(author.id, guild.id)
    archive_message(guild.id, message.channel.id, author.id, message.content)
    
    # AFK
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM afk_users WHERE guild_id=?", (str(guild.id),))
    afk = {r["user_id"]:dict(r) for r in c.fetchall()}; conn.close()
    if str(author.id) in afk:
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM afk_users WHERE user_id=? AND guild_id=?", (str(author.id),str(guild.id)))
        conn.commit(); conn.close()
        try: await message.channel.send(f"Welcome back {author.mention}!", delete_after=8)
        except: pass
    for m in message.mentions:
        if str(m.id) in afk:
            try: await message.channel.send(f"**{m.display_name}** is AFK: *{afk[str(m.id)]['reason']}*", delete_after=10)
            except: pass
    
    # Custom commands
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT response FROM custom_commands WHERE guild_id=? AND trigger_word=?", (str(guild.id),message.content.lower().strip()))
    cc = c.fetchone(); conn.close()
    if cc: await message.channel.send(cc["response"]); return
    
    is_ai_ch = message.channel.name == AI_CHAT_CHANNEL
    is_mentioned = bot.user in message.mentions
    speak_vc = guild.id in voice_sessions
    
    # OWNER
    if owner_talking and (is_ai_ch or is_mentioned):
        content = message.content.replace(f"<@{bot.user.id}>","").strip()
        if not content: await message.reply("Yeah Boss?"); return
        try: parsed = await asyncio.wait_for(parse_command(content, guild, author), timeout=15.0)
        except: parsed = None
        if parsed and parsed.get("command") not in ["chat",None] and parsed.get("confidence",0) >= 0.7:
            dangerous = ["ban_user","kick_user","lockdown","purge","delete_channel","delete_role","revoke_license","leave_server"]
            if parsed.get("needs_confirmation") or parsed.get("command") in dangerous:
                view = ConfirmView(parsed, message, guild, author)
                await message.reply(embed=discord.Embed(title="Confirm",description=f"Run **{parsed['command']}**?",color=discord.Color.orange()),view=view)
            else:
                r = await execute_command(parsed, message, guild, author)
                if r: await message.reply(r[:2000])
            return
        sys = get_owner_system_prompt(str(author.id),str(guild.id),str(message.channel.id))
        hist = get_conversation_history(str(author.id),str(guild.id))
        await smart_response(message, content, sys, hist, str(author.id), str(guild.id), speak_in_vc=speak_vc)
        return
    
    if owner_talking: await bot.process_commands(message); return
    
    # MOD
    if is_mod and (is_ai_ch or is_mentioned):
        content = message.content.replace(f"<@{bot.user.id}>","").strip()
        if not content:
            if is_mentioned: await message.reply("What's up?")
            return
        try: parsed = await asyncio.wait_for(parse_command(content, guild, author), timeout=15.0)
        except: parsed = None
        if parsed and parsed.get("command") not in ["chat",None] and parsed.get("confidence",0) >= 0.7:
            user_cmds = ["ban_user","kick_user","mute_user","warn_user"]
            if parsed.get("command") in user_cmds and not find_member_strict(guild, parsed.get("params",{})):
                await message.reply("@mention the user!"); return
            dangerous = ["ban_user","kick_user","lockdown","purge","delete_channel","delete_role"]
            if parsed.get("needs_confirmation") or parsed.get("command") in dangerous:
                view = ConfirmView(parsed, message, guild, author)
                await message.reply(embed=discord.Embed(title="Confirm",description=f"Run **{parsed['command']}**?",color=discord.Color.orange()),view=view)
            else:
                r = await execute_command(parsed, message, guild, author)
                if r: await message.reply(r[:2000])
            return
        sys = get_system_prompt(str(author.id),str(guild.id),str(message.channel.id),author.display_name)
        hist = get_conversation_history(str(author.id),str(guild.id))
        await smart_response(message, content, sys, hist, str(author.id), str(guild.id), speak_in_vc=speak_vc)
        return
    
    if is_mod: await bot.process_commands(message); return
    
    # REGULAR USER
    if is_ai_ch or is_mentioned:
        content = message.content.replace(f"<@{bot.user.id}>","").strip()
        if not content:
            if is_mentioned: await message.reply(random.choice(["Hey!","What's up?","I'm here!"]))
            return
        try: parsed = await asyncio.wait_for(parse_command(content, guild, author), timeout=15.0)
        except: parsed = None
        if parsed and parsed.get("command") in ["trivia","eightball","roast","compliment","dadjoke","ship","rate","fact","story","riddle","remind","set_afk","rep","memory_view","help","create_poll","summarize","translate","activity_stats","server_health"] and parsed.get("confidence",0) >= 0.7:
            r = await execute_command(parsed, message, guild, author)
            if r: await message.reply(r[:2000])
            return
        sys = get_system_prompt(str(author.id),str(guild.id),str(message.channel.id),author.display_name)
        hist = get_conversation_history(str(author.id),str(guild.id))
        await smart_response(message, content, sys, hist, str(author.id), str(guild.id), speak_in_vc=speak_vc)
        return
    
    if await check_spam(message, s): await handle_spam(message, s); return
    
    if s.get("ai_mod_enabled",1):
        was_moderated = await handle_moderation_smart(message, s)
        if was_moderated:
            today = datetime.now().date().isoformat()
            conn = get_db(); c = conn.cursor()
            c.execute("INSERT INTO daily_stats (guild_id,date,mod_actions) VALUES (?,?,1) ON CONFLICT DO UPDATE SET mod_actions=mod_actions+1", (str(guild.id),today))
            conn.commit(); conn.close()
            return
    
    await bot.process_commands(message)

if __name__ == "__main__":
    if not DISCORD_TOKEN: print("DISCORD_TOKEN missing!"); exit(1)
    if not GROQ_API_KEY: print("GROQ_API_KEY missing!"); exit(1)
    
    init_database()
    migrate_database()
    
    try:
        dashboard.set_bot(bot)
        thread = threading.Thread(target=dashboard.run_dashboard)
        thread.daemon = True
        thread.start()
        print("Dashboard started")
    except Exception as e: print(f"Dashboard err: {e}")
    
    if AI_FEATURES_LOADED:
        try:
            ai_features.setup(bot_instance=bot,get_db=get_db,get_settings=get_guild_settings,ask_groq=smart_ai,ask_json=ask_groq_json,notify_owner=notify_owner)
            print("AI Features loaded")
        except Exception as e: print(f"AI features err: {e}")
    
    print(f"SentinelMod v{BOT_IDENTITY['version']} - LICENSE EDITION")
    print(f"License agreement required on join | Owner sovereign control")
    bot.run(DISCORD_TOKEN)
