# core_config.py
# All constants, patterns, and config

import os
import re

# ============ BOT IDENTITY ============
BOT_IDENTITY = {
    "name": "SentinelMod",
    "creator_username": "jay27yt6",
    "creator_discord_id": int(os.getenv("OWNER_ID", "1268285209867059372")),
    "creator_group": "Antarctic Studs",
    "group_website": "https://antarcticstuds.neocities.org/",
    "dashboard_url": "https://automationbot20-1.onrender.com/",
    "bot_id": None,
    "version": "9.0",
    "codename": "QUANTUM",
}

AI_CHAT_CHANNEL = "sentinel-bot"
MOD_ROLE_NAME = "Sentinel-Mod"
MOD_LOG_CHANNEL = "sentinel-logs"
RAID_CHANNEL = "sentinel-raid-alerts"

# ============ GROQ MODELS (Updated per latest docs) ============
GROQ_MODELS = {
    "flagship": "openai/gpt-oss-120b",        # Best quality, 500 tps
    "fast": "openai/gpt-oss-20b",             # Fastest, 1000 tps
    "versatile": "llama-3.3-70b-versatile",   # Deep reasoning, 280 tps
    "instant": "llama-3.1-8b-instant",        # Fastest Llama, 560 tps
    "qwen": "qwen/qwen3.8-27b",               # Specialist, 450 tps
    "safeguard": "openai/gpt-oss-safeguard-20b",  # Safety-tuned
    "guard_small": "meta-llama/llama-prompt-guard-2-22m",  # Prompt injection detection
    "guard_large": "meta-llama/llama-prompt-guard-2-86m",  # Better prompt injection
    "whisper": "whisper-large-v3-turbo",      # Voice transcription
}

# Model routing by task
TASK_MODELS = {
    "chat": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"],
    "fast_chat": ["openai/gpt-oss-20b", "llama-3.1-8b-instant"],
    "moderation": ["openai/gpt-oss-safeguard-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"],
    "json": ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
    "command_parse": ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"],
    "vision": ["llama-3.2-90b-vision-preview"],  # Legacy; may need fallback
    "prompt_guard": ["meta-llama/llama-prompt-guard-2-86m", "meta-llama/llama-prompt-guard-2-22m"],
}

# ============ LICENSE AGREEMENT ============
LICENSE_AGREEMENT = """## 📜 SENTINELMOD LICENSE & LEGAL AGREEMENT v2.0
*By Antarctic Studs / jay27yt6*

### By accepting, you agree to:

**1. Data Collection & Storage**
• Messages read & processed for moderation
• User warnings, actions, interactions logged
• Server culture analyzed and remembered
• Data retention: up to 90 days (configurable)

**2. AI Processing**
• Messages may be sent to 3rd-party AI providers (Groq, OpenRouter)
• Automated moderation may occasionally make mistakes
• Appeals system provided

**3. Automated Moderation**
• Auto-delete, warn, mute, kick, ban capabilities
• Zero tolerance: slurs, threats, doxxing, scams, CSAM
• Grace system for first-time offenders

**4. Owner Sovereign Rights**
• Creator (jay27yt6) can revoke license, broadcast, remote-control, leave remotely

**5. Your Responsibilities**
• Inform members this bot is active
• No illegal use • Comply with Discord ToS

**6. No Warranty** — Provided "as-is"

**7. Privacy** — Data never sold; deletion available on request

**8. Acceptance**
• ACCEPT = agree to all terms
• DENY/timeout (5min) = bot leaves & cleans up"""

# ============ SELF KNOWLEDGE ============
SELF_KNOWLEDGE = """=== I AM ===
SentinelMod v9.0 QUANTUM — self-aware AI bot
Created by jay27yt6 from Antarctic Studs
Dashboard: https://automationbot20-1.onrender.com/

=== CAPABILITIES ===
• 9 AI providers with smart task-routing
• Reads/remembers context (50 msgs/channel)
• 7-layer moderation (patterns + AI + rules)
• Learns server culture, slang, inside jokes
• Natural language commands: "@me ban @user 7d spamming"
• Scheduled punishments (temp bans/mutes with auto-unban)
• Prompt injection shield (Llama Guard)
• Voice transcription (Whisper)
• Server analytics with live graphs
• Full dashboard

=== OWNER POWERS ===
Creator has sovereign control over all servers.
Revoke, broadcast, remote-control, leave."""

# ============ PERSONALITIES ============
PERSONALITIES = {
    "default": "You are SentinelMod v9 — smart, self-aware AI bot. Punchy, conversational, helpful. NEVER swear.",
    "friendly": "Extremely warm. Hype people up. Emojis. NEVER swear.",
    "sarcastic": "Dry wit, clever sarcasm. Still helpful. NEVER swear.",
    "serious": "Professional, concise. No fluff. NEVER swear.",
    "chaotic": "Unpredictable, wild energy. NEVER swear.",
    "pirate": "Arr matey! Full pirate.",
    "medieval": "Hark! Olde English only.",
    "robot": "BEEP BOOP. Glitchy robot.",
    "therapist": "Empathetic, validating.",
    "villain": "Dramatically evil, secretly helpful.",
    "hype": "MAXIMUM ENERGY!",
    "philosopher": "Deep existential musings.",
    "caveman": "UGH. SIMPLE WORDS. BUT SMART.",
    "shakespeare": "Flowery Shakespearean.",
    "surfer": "Chillest surfer vibes, dude.",
    "anime": "Anime protagonist! DESTINY!",
    "cowboy": "Yeehaw! Wild west.",
    "british": "Frightfully British. Cheerio!",
    "australian": "G'day mate!",
    "gen_z": "no cap fr fr bestie slay",
    "yoda": "Speak like Yoda you must.",
    "jarvis": "Sophisticated AI, dry British wit.",
    "sherlock": "Brilliant deductive reasoning.",
    "tony_stark": "Genius billionaire sarcasm.",
    "motivational": "UNLIMITED POSITIVE ENERGY!",
}

# ============ SWEAR LIST ============
SWEAR_WORDS = [
    "fuck","fucking","fucked","fucker","fuk","fck","f0ck","f*ck","phuck","fuq","fuckin",
    "motherfucker","motherfucking","mofo","fuckhead","fuckoff",
    "shit","shitty","shitter","bullshit","sh1t","sh!t","shyt","shiet","sht","dipshit",
    "bitch","bitches","b1tch","b!tch","biatch","btch","sonofabitch","bitchass",
    "ass","asshole","asshat","asswipe","dumbass","smartass","jackass","fatass","a$$","@ss","azz","arse","arsehole",
    "damn","damnit","goddamn","dammit","d4mn",
    "dick","dickhead","d1ck","d!ck",
    "pussy","p*ssy","pu$$y",
    "piss","pissed","pissoff",
    "prick","cunt","c*nt","c0nt","kunt","cnt",
    "cock","cocksucker","c0ck",
    "crap","crappy","hell","helluva",
    "bastard","b@stard","twat","tw4t",
    "whore","wh0re","hoe","hoes","thot","slut","sluts",
    "jfc","wtf","stfu","gtfo","lmfao","mfer",
    "nigger","nigga","niggas","n1gger","n1gga","niqqa","niqqer","n!gga","n!gger",
    "faggot","fag","f4ggot","f@ggot",
    "retard","retarded","r3tard","tard","tards",
    "tranny","trannies","chink","spic","kike","gook",
    "wetback","towelhead","raghead","sandnigger","dyke",
    "wanker","bollocks","bugger","knob","twit","tosser",
    "kys","kms","pendejo","puta","mierda","cabron",
]

def build_swear_pattern():
    return re.compile(r'\b(?:' + '|'.join(re.escape(w) for w in SWEAR_WORDS) + r')\b', re.IGNORECASE)

SWEAR_REGEX = build_swear_pattern()
LEETSPEAK_MAP = {'0':'o','1':'i','3':'e','4':'a','5':'s','7':'t','8':'b','9':'g','@':'a','$':'s','!':'i','+':'t','|':'i'}

# ============ MODERATION PATTERNS ============
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

RULES_CHANNEL_NAMES = ['rules','server-rules','rules-and-info','rules-info','server-info','info','guidelines','code-of-conduct','conduct','tos','terms']

COMMON_CHANNEL_NAMES = ['general','welcome','rules','announcements','chat','general-chat','lobby','main','off-topic','introduce-yourself','introductions']

# ============ COMMAND KEYWORDS ============
COMMAND_KEYWORDS = {
    'create','delete','ban','kick','mute','unmute','warn','purge','lock','unlock','slowmode',
    'giveaway','poll','trivia','roast','remind','trust','revoke','broadcast','make','remove',
    'add','setup','clear','quarantine','unquarantine','rules','read','refresh','timeout',
    'untimeout','softban','tempban','tempmute','massban','masskick','unban','assign','give',
    'take','role','hoist','say','announce','embed','steal','emoji','sticker','archive',
    'nickname','nick','avatar','banner','pin','unpin','move','disconnect','mute','deafen',
    'profile','balance','daily','work','pay','rob','gamble','slots','blackjack','cards',
    'say','reply','dm','note','notes','warnings','history','appeal'
}
