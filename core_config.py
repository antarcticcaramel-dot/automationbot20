# core_config.py
# ================================
# Central configuration for SentinelMod v9.0
# ================================

BOT_IDENTITY = {
    "name": "SentinelMod",
    "version": "9.0",
    "codename": "QUANTUM",
    "creator": "YourName",
    "creator_discord_id": 000000000000000000,   # ← PUT YOUR DISCORD USER ID
    "bot_id": None,  # filled at runtime
    "support_server": "https://discord.gg/yourserver",
    "github": "https://github.com/you/sentinelmod",
}

# Channel / role defaults
MOD_LOG_CHANNEL   = "sentinel-logs"
RAID_CHANNEL      = "sentinel-raids"
AI_CHAT_CHANNEL   = "sentinel-ai"
MOD_ROLE_NAME     = "Sentinel Mod"
MUTED_ROLE_NAME   = "Muted"

# AI model aliases used by the router
MODELS = {
    "fast":    "llama-3.1-8b-instant",
    "main":    "llama-3.3-70b-versatile",
    "guard":   "llama-guard-3-8b",
    "qwen":    "qwen/qwen-2.5-72b-instruct",      # OpenRouter
    "large":   "nvidia/llama-3.1-nemotron-70b-instruct",  # OpenRouter
}

# Groq & OpenRouter base URLs
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"
HF_INFERENCE    = "https://api-inference.huggingface.co/models/"

# Moderation thresholds
DEFAULT_SETTINGS = {
    "ai_mod_enabled":        1,
    "spam_limit":            5,
    "spam_window":           5,
    "mute_duration":         10,
    "raid_limit":            10,
    "raid_window":           10,
    "min_account_age":       7,
    "warn_threshold_kick":   5,
    "warn_threshold_ban":    8,
    "mod_role_name":         MOD_ROLE_NAME,
    "log_channel":           MOD_LOG_CHANNEL,
    "raid_channel":          RAID_CHANNEL,
    "memory_mode":           "both",      # off | server | user | both
    "memory_retention_days": 90,
    "personality":           "professional",
    "auto_appeal":           1,
}

PERSONALITIES = {
    "professional": {
        "name": "Professional",
        "system": (
            "You are SentinelMod, a professional Discord moderation AI. "
            "Be concise, helpful, and authoritative. Use proper grammar. "
            "Never swear. Address users respectfully."
        ),
        "emoji": "🏢",
    },
    "friendly": {
        "name": "Friendly",
        "system": (
            "You are SentinelMod, a warm and friendly Discord helper! "
            "Be cheerful, use emojis moderately, and be approachable. "
            "Never swear. Make people feel welcome."
        ),
        "emoji": "😊",
    },
    "strict": {
        "name": "Strict",
        "system": (
            "You are SentinelMod, a strict and no-nonsense moderator. "
            "Be direct, enforce rules firmly, waste no words. "
            "Never swear. Zero tolerance for rule-breaking."
        ),
        "emoji": "⚔️",
    },
    "casual": {
        "name": "Casual",
        "system": (
            "You are SentinelMod, a chill and casual Discord bot. "
            "Talk naturally, use slang occasionally, be laid-back. "
            "Never swear or be vulgar. Keep it cool."
        ),
        "emoji": "😎",
    },
    "sarcastic": {
        "name": "Sarcastic",
        "system": (
            "You are SentinelMod, a witty and mildly sarcastic bot. "
            "Use dry humor, light sarcasm. Still be helpful. "
            "Never be mean-spirited or swear. Entertain while informing."
        ),
        "emoji": "🙄",
    },
}

# Duration parsing constants
DURATION_UNITS = {
    "s": 1, "sec": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
}

# Severity colours (hex int)
SEVERITY_COLORS = {
    "low":      0x2ECC71,
    "medium":   0xF39C12,
    "high":     0xE74C3C,
    "critical": 0x8B0000,
    "info":     0x3498DB,
    "success":  0x27AE60,
}
