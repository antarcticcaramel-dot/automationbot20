# moderation.py
# ================================
# AI-powered moderation engine
# ================================

import discord
import time
import hashlib
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional


class ModerationEngine:
    """Handles AI-powered message moderation, spam detection, duplicate detection."""

    def __init__(self, db, ai):
        self.db = db
        self.ai = ai
        # These are set from bot.py after construction
        self.live_context = None
        self.user_message_patterns = None
        self.recent_actions = None
        self.server_rules_cache = None
        self.spam_tracker = None
        self.file_tracker = None
        self.bot = None

        # Internal tracking
        self._recent_hashes: dict[str, list] = defaultdict(list)  # guild:user → [hashes]
        self._link_tracker: dict[str, list] = defaultdict(list)

    async def check_message(self, message: discord.Message, settings: dict,
                             server_rules: str, log_fn, alert_fn, notify_fn) -> bool:
        """Check a message for violations. Returns True if action was taken."""

        content = message.content
        author = message.author
        guild = message.guild

        if not content and not message.attachments:
            return False

        # Phase 1: Fast heuristic checks
        action = self._fast_checks(message, settings)
        if action:
            await self._take_action(message, action, log_fn, alert_fn, notify_fn, settings)
            return True

        # Phase 2: Duplicate / copypasta detection
        if self._is_duplicate(message, guild.id, author.id):
            action = {
                "type": "DUPLICATE",
                "severity": "low",
                "reason": "Duplicate / copypasta message",
                "action": "delete",
            }
            await self._take_action(message, action, log_fn, alert_fn, notify_fn, settings)
            return True

        # Phase 3: Link spam
        urls = re.findall(r'https?://\S+', content)
        if urls:
            key = f"{guild.id}:{author.id}"
            now = time.time()
            self._link_tracker[key].append(now)
            self._link_tracker[key] = [t for t in self._link_tracker[key] if now - t < 30]
            if len(self._link_tracker[key]) >= 4:
                action = {
                    "type": "LINK_SPAM",
                    "severity": "medium",
                    "reason": "Rapid link posting",
                    "action": "mute",
                }
                await self._take_action(message, action, log_fn, alert_fn, notify_fn, settings)
                return True

        # Phase 4: AI moderation (slower, only if content is substantial)
        if len(content) >= 5:
            # Build context
            ctx_key = f"{guild.id}:{message.channel.id}"
            ctx_messages = list(self.live_context.get(ctx_key, []))[-5:] if self.live_context else []
            context_str = "\n".join(
                f"{m['author']}: {m['content'][:100]}" for m in ctx_messages
            ) if ctx_messages else ""

            result = await self.ai.moderate_text(content, server_rules, context_str)
            if result and result.get("is_violation") and result.get("confidence", 0) >= 0.7:
                action = {
                    "type": result.get("categories", ["VIOLATION"])[0].upper()
                            if result.get("categories") else "VIOLATION",
                    "severity": result.get("severity", "medium"),
                    "reason": result.get("reason", "AI-detected violation"),
                    "action": result.get("suggested_action", "warn"),
                    "confidence": result.get("confidence", 0.7),
                }
                await self._take_action(message, action, log_fn, alert_fn, notify_fn, settings)
                return True

        return False

    def _fast_checks(self, message: discord.Message, settings: dict) -> Optional[dict]:
        """Fast regex/heuristic checks that don't need AI."""
        content = message.content

        # Mass mentions
        if len(message.mentions) >= 6:
            return {
                "type": "MASS_MENTION",
                "severity": "high",
                "reason": f"Mass mentioning ({len(message.mentions)} users)",
                "action": "mute",
            }

        # @everyone / @here spam (if no permission)
        if message.mention_everyone and not message.author.guild_permissions.mention_everyone:
            return {
                "type": "EVERYONE_PING",
                "severity": "medium",
                "reason": "Unauthorized @everyone/@here",
                "action": "delete",
            }

        # Excessive caps (> 70% caps in messages > 15 chars)
        if len(content) > 15:
            alpha = [c for c in content if c.isalpha()]
            if alpha and sum(1 for c in alpha if c.isupper()) / len(alpha) > 0.7:
                return {
                    "type": "CAPS",
                    "severity": "low",
                    "reason": "Excessive caps",
                    "action": "warn_soft",
                }

        # Discord invite links
        invite_pattern = r"(?:discord\.gg|discord\.com/invite)/\S+"
        if re.search(invite_pattern, content, re.I):
            return {
                "type": "INVITE_LINK",
                "severity": "medium",
                "reason": "Unauthorized Discord invite link",
                "action": "delete",
            }

        # Zalgo text
        if any(ord(c) > 0x0300 and ord(c) < 0x036F for c in content) and \
           sum(1 for c in content if 0x0300 <= ord(c) <= 0x036F) > 10:
            return {
                "type": "ZALGO",
                "severity": "low",
                "reason": "Zalgo / glitch text",
                "action": "delete",
            }

        # Wall of text (> 2000 chars of repetitive content)
        if len(content) > 1500:
            words = content.split()
            if words:
                unique_ratio = len(set(w.lower() for w in words)) / len(words)
                if unique_ratio < 0.15:
                    return {
                        "type": "WALL_OF_TEXT",
                        "severity": "low",
                        "reason": "Repetitive wall of text",
                        "action": "delete",
                    }

        return None

    def _is_duplicate(self, message: discord.Message, guild_id, user_id) -> bool:
        """Check if message is a duplicate/copypasta."""
        content = message.content.strip().lower()
        if len(content) < 20:
            return False

        content_hash = hashlib.md5(content.encode()).hexdigest()
        key = f"{guild_id}:{user_id}"
        now = time.time()

        # Clean old entries
        self._recent_hashes[key] = [
            (h, t) for h, t in self._recent_hashes[key] if now - t < 300
        ]

        # Check for duplicates
        duplicate_count = sum(1 for h, _ in self._recent_hashes[key] if h == content_hash)
        self._recent_hashes[key].append((content_hash, now))

        return duplicate_count >= 2  # Same message 3+ times in 5 minutes

    async def _take_action(self, message: discord.Message, action: dict,
                            log_fn, alert_fn, notify_fn, settings: dict):
        """Execute a moderation action."""
        author = message.author
        guild = message.guild
        severity = action.get("severity", "low")
        reason = action.get("reason", "Violation")
        action_type = action.get("action", "warn")

        # Always try to delete the offending message
        if action_type in ("delete", "warn", "mute", "kick", "ban"):
            try:
                await message.delete()
            except:
                pass

        # Soft warn: just notify in channel
        if action_type == "warn_soft":
            try:
                await message.channel.send(
                    f"⚠️ {author.mention} — {reason}. Please stop.",
                    delete_after=10
                )
            except:
                pass
            return

        # Add warning to DB
        wc, wid = self.db.add_warning(
            author.id, guild.id, reason, severity,
            action.get("confidence", 0.8),
            message.content[:200]
        )

        log_fn(guild.id, action["type"], author.display_name,
               f"{reason} (W#{wc})", f"conf={action.get('confidence', 'N/A')}")

        # Action based on severity / type
        if action_type == "mute" or severity in ("high", "critical"):
            dur = settings.get("mute_duration", 10)
            try:
                await author.timeout(
                    datetime.now(timezone.utc) + timedelta(minutes=dur),
                    reason=reason
                )
            except:
                pass

        if action_type == "kick" or wc >= settings.get("warn_threshold_kick", 5):
            try:
                await author.kick(reason=f"{reason} ({wc} warnings)")
            except:
                pass

        if action_type == "ban" or wc >= settings.get("warn_threshold_ban", 8):
            try:
                await author.ban(reason=f"{reason} ({wc} warnings)",
                                 delete_message_days=1)
            except:
                pass

        # Notify in channel
        try:
            await message.channel.send(
                f"🛡️ {author.mention} — {reason} (Warning #{wc})",
                delete_after=15
            )
        except:
            pass

        # Alert mods
        from components_v2 import build_mod_action_container
        embed = build_mod_action_container(action["type"], author, reason, wc)
        await alert_fn(guild, embed)

        # Critical = notify owner
        if severity == "critical":
            await notify_fn("WARN", f"🚨 Critical violation in **{guild.name}** by "
                           f"{author} — {reason}", guild=guild, urgent=True)
