# command_parser.py
# ================================
# Natural language command parser
# @bot ban @user 7d spam  →  {"command": "ban_user", "target": ..., "duration": "7d", ...}
# ================================

import re
import discord
from typing import Optional


class NaturalCommandParser:
    """Parses natural language into structured commands via regex + AI fallback."""

    # Quick-match patterns: (regex, command_name, groups → param mapping)
    PATTERNS = [
        # Ban
        (r"(?:temp\s*)?ban\s+<?@?!?(\d+)>?\s*(?:for\s+)?(\d+[smhdw](?:\w*)?)?\s*(.*)?",
         "ban_user", {"target_id": 1, "duration": 2, "reason": 3}),
        # Kick
        (r"kick\s+<?@?!?(\d+)>?\s*(.*)?",
         "kick_user", {"target_id": 1, "reason": 2}),
        # Mute / timeout
        (r"(?:mute|timeout)\s+<?@?!?(\d+)>?\s*(?:for\s+)?(\d+[smhdw](?:\w*)?)?\s*(.*)?",
         "mute_user", {"target_id": 1, "duration": 2, "reason": 3}),
        # Unmute
        (r"unmute\s+<?@?!?(\d+)>?\s*(.*)?",
         "unmute_user", {"target_id": 1, "reason": 2}),
        # Warn
        (r"warn\s+<?@?!?(\d+)>?\s*(.*)?",
         "warn_user", {"target_id": 1, "reason": 2}),
        # Purge
        (r"(?:purge|clear|clean)\s+(\d+)\s*(.*)?",
         "purge", {"count": 1, "reason": 2}),
        # Lockdown
        (r"lock(?:down)?\s*(?:the\s+)?(?:channel|server|#?\w+)?\s*(.*)?",
         "lockdown", {"reason": 1}),
        # Unlock
        (r"unlock\s*(?:the\s+)?(?:channel|server|#?\w+)?\s*(.*)?",
         "unlock", {"reason": 1}),
        # Slowmode
        (r"slowmode\s+(\d+)\s*(.*)?",
         "slowmode", {"seconds": 1}),
        # Check warnings
        (r"(?:check\s*)?warnings?\s+(?:for\s+)?<?@?!?(\d+)>?",
         "check_warnings", {"target_id": 1}),
        # Clear warnings
        (r"clear\s*warnings?\s+(?:for\s+)?<?@?!?(\d+)>?",
         "clear_warnings", {"target_id": 1}),
        # AFK
        (r"(?:set\s*)?afk\s*(.*)?",
         "set_afk", {"reason": 1}),
        # Remind
        (r"remind\s+(?:me\s+)?(?:in\s+)?(\d+[smhdw](?:\w*)?)\s+(.*)",
         "remind", {"duration": 1, "reminder": 2}),
        # Trivia
        (r"trivia\s*(.*)?", "trivia", {"category": 1}),
        # 8ball
        (r"(?:8ball|magic\s*8\s*ball|eightball)\s+(.*)",
         "eightball", {"question": 1}),
        # Roast
        (r"roast\s+<?@?!?(\d+)>?",
         "roast", {"target_id": 1}),
        # Compliment
        (r"compliment\s+<?@?!?(\d+)>?",
         "compliment", {"target_id": 1}),
        # Dad joke
        (r"(?:dad\s*joke|dadjoke)", "dadjoke", {}),
        # Ship
        (r"ship\s+<?@?!?(\d+)>?\s+(?:and\s+)?<?@?!?(\d+)>?",
         "ship", {"target1_id": 1, "target2_id": 2}),
        # Rate
        (r"rate\s+(.*)", "rate", {"thing": 1}),
        # Fact
        (r"(?:random\s*)?fact", "fact", {}),
        # Story
        (r"(?:tell\s+(?:me\s+)?a\s+)?story\s*(.*)?",
         "story", {"topic": 1}),
        # Riddle
        (r"riddle", "riddle", {}),
        # Rep
        (r"rep\s+<?@?!?(\d+)>?", "rep", {"target_id": 1}),
        # Poll
        (r"poll\s+(.+)", "create_poll", {"raw": 1}),
        # Summarize
        (r"summarize?\s*(\d+)?\s*(.*)?",
         "summarize", {"count": 1, "topic": 2}),
        # Translate
        (r"translate\s+(?:to\s+)?(\w+)\s+(.*)",
         "translate", {"language": 1, "text": 2}),
        # Help
        (r"^help$", "help", {}),
        # Server health
        (r"(?:server\s*)?health", "server_health", {}),
        # Activity / stats
        (r"(?:activity|stats)", "activity_stats", {}),
        # Rules
        (r"(?:read\s*|show\s*)?rules?", "read_rules", {}),
        # Refresh rules
        (r"refresh\s*rules?", "refresh_rules", {}),
        # Balance
        (r"balance|wallet|coins", "balance", {}),
        # Profile
        (r"profile\s*<?@?!?(\d*)>?",
         "profile", {"target_id": 1}),
        # Memory
        (r"(?:server\s*)?memory", "memory_view", {}),
        # Setup
        (r"setup\s*(?:server)?", "setup_server", {}),
        # Server info
        (r"server\s*info", "server_info", {}),
        # User info
        (r"(?:user|who)\s*info\s+<?@?!?(\d+)>?",
         "user_info", {"target_id": 1}),
        # Giveaway
        (r"giveaway\s+(.+)",
         "giveaway", {"raw": 1}),
        # Leave server (owner only)
        (r"leave\s*(?:this\s*)?server", "leave_server", {}),
        # Revoke license (owner only)
        (r"revoke\s*(?:license)?\s*(\d+)?",
         "revoke_license", {"guild_id": 1}),
        # Set personality
        (r"(?:set\s*)?personality\s+(\w+)",
         "set_personality", {"personality": 1}),
    ]

    DANGEROUS_COMMANDS = {
        "ban_user", "kick_user", "lockdown", "purge", "delete_channel",
        "delete_role", "delete_category", "revoke_license", "leave_server",
        "mass_ban", "mass_kick", "clear_warnings",
    }

    def __init__(self, ai, bot):
        self.ai = ai
        self.bot = bot
        self._compiled = [(re.compile(p, re.IGNORECASE), cmd, mapping)
                          for p, cmd, mapping in self.PATTERNS]

    def likely_command(self, content: str) -> bool:
        """Fast check: does this look like a command?"""
        content_lower = content.lower().strip()
        cmd_words = [
            "ban", "kick", "mute", "unmute", "warn", "purge", "clear",
            "lock", "unlock", "slowmode", "timeout", "setup", "help",
            "trivia", "8ball", "eightball", "roast", "compliment", "dadjoke",
            "ship", "rate", "fact", "story", "riddle", "remind", "afk",
            "rep", "poll", "summarize", "translate", "health", "stats",
            "rules", "refresh", "balance", "wallet", "profile", "memory",
            "giveaway", "leave", "revoke", "personality", "server", "user",
            "delete", "create", "set", "check", "warnings",
        ]
        first_word = content_lower.split()[0] if content_lower else ""
        return any(first_word.startswith(w) or w in content_lower[:60]
                   for w in cmd_words)

    async def parse(self, content: str, guild, author,
                    is_owner_user: bool = False) -> Optional[dict]:
        """Parse natural language into a command dict."""
        content = content.strip()

        # Phase 1: regex matching
        for pattern, cmd_name, mapping in self._compiled:
            m = pattern.search(content)
            if m:
                result = {"command": cmd_name, "confidence": 0.90, "raw": content}
                for param, group in mapping.items():
                    val = m.group(group) if group <= len(m.groups()) else None
                    if val:
                        val = val.strip()
                    result[param] = val or ""

                # Resolve user mentions
                result = await self._resolve_targets(result, guild)
                result["needs_confirmation"] = cmd_name in self.DANGEROUS_COMMANDS
                return result

        # Phase 2: AI-based parsing for complex commands
        return await self._ai_parse(content, guild, author, is_owner_user)

    async def _ai_parse(self, content, guild, author, is_owner_user) -> Optional[dict]:
        """Use AI to parse ambiguous commands."""
        commands_list = (
            "ban_user, kick_user, mute_user, unmute_user, warn_user, purge, "
            "lockdown, unlock, slowmode, check_warnings, clear_warnings, "
            "set_afk, remind, trivia, eightball, roast, compliment, dadjoke, "
            "ship, rate, fact, story, riddle, rep, create_poll, summarize, "
            "translate, help, server_health, activity_stats, read_rules, "
            "refresh_rules, balance, profile, memory_view, setup_server, "
            "server_info, user_info, giveaway, leave_server, revoke_license, "
            "set_personality, chat"
        )
        prompt = f"""Parse this Discord command into structured JSON.
Available commands: {commands_list}

User message: "{content[:500]}"
User: {author.display_name} (owner: {is_owner_user})

JSON format:
{{
  "command": "command_name",
  "confidence": 0.0-1.0,
  "target": "username or null",
  "target_id": "user_id or null",
  "duration": "duration string or null",
  "reason": "reason or null",
  "extra": {{}}
}}

If it's just conversation (not a command), use {{"command":"chat","confidence":0.9}}"""

        result = await self.ai.ask_json(prompt, prefer="fast")
        if not result:
            return {"command": "chat", "confidence": 0.5, "raw": content}

        result["raw"] = content
        result["needs_confirmation"] = result.get("command", "") in self.DANGEROUS_COMMANDS

        # Resolve targets
        if result.get("target") and not result.get("target_id"):
            result = await self._resolve_targets(result, guild)

        return result

    async def _resolve_targets(self, result: dict, guild) -> dict:
        """Resolve target_id to member and vice versa."""
        if result.get("target_id"):
            tid = result["target_id"]
            # Clean Discord mention format
            tid = re.sub(r"[<@!>]", "", str(tid)).strip()
            if tid.isdigit():
                result["target_id"] = int(tid)
                member = guild.get_member(int(tid))
                if member:
                    result["target"] = member.display_name
                    result["target_member"] = member
        elif result.get("target"):
            # Try to find by name
            name = result["target"].lower().strip()
            member = discord.utils.find(
                lambda m: m.display_name.lower() == name or m.name.lower() == name,
                guild.members
            )
            if member:
                result["target_id"] = member.id
                result["target_member"] = member
        return result
