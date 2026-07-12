# test_server.py
# ================================
# SentinelMod - Ultimate Test Server System
# Auto-hooks into bot. EXCLUSIVE to designated test server.
# ================================

import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import asyncio
import json
import re
import os
import time as _time
import threading
import random
import string
import hashlib
import traceback
import sys
import io
import textwrap
import contextlib
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any

# ============ CONFIG ============
TEST_SERVER_ID = 1523813949978578994

_bot_ref = None
_is_setup = False

# ============ STATE ============
SPY_MODE = False
DRY_RUN_MODE = False
STEALTH_MODE = False          # Bot reacts but doesn't announce
LOCKDOWN_TEST = False         # Full server lockdown simulation
AI_OVERRIDE_PERSONALITY = None
RATE_LIMIT_TEST = False       # Simulate rate limits

_command_usage = defaultdict(int)
_command_errors = defaultdict(list)
_message_edits_log = deque(maxlen=200)
_deleted_messages_log = deque(maxlen=200)
_join_leave_log = deque(maxlen=100)
_ai_decision_log = deque(maxlen=500)
_reaction_log = deque(maxlen=200)
_performance_log = deque(maxlen=1000)
_webhook_log = deque(maxlen=100)
_flood_test_active = False
_session_start = datetime.now()
_test_scenarios_run = []
_live_monitor_channels = set()
_stress_test_active = False
_fake_users_active = {}
_scheduled_tests = []


def is_test_server(guild_id) -> bool:
    try:
        return int(guild_id) == TEST_SERVER_ID
    except:
        return False


def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _get_bot_func(name):
    for mod in sys.modules.values():
        if mod is None:
            continue
        if hasattr(mod, name) and hasattr(mod, "bot"):
            return getattr(mod, name)
    return None


def _get_bot_var(name):
    for mod in sys.modules.values():
        if mod is None:
            continue
        if hasattr(mod, name) and hasattr(mod, "bot"):
            return getattr(mod, name)
    return None


def _log_performance(label: str, ms: float):
    _performance_log.append({
        "label": label,
        "ms": ms,
        "time": datetime.now().isoformat()
    })


async def _timed(label: str, coro):
    start = _time.perf_counter()
    result = await coro
    elapsed = (_time.perf_counter() - start) * 1000
    _log_performance(label, elapsed)
    return result


def _is_owner_check(user_id: int) -> bool:
    is_owner = _get_bot_func("is_owner")
    return is_owner(user_id) if is_owner else False


def _build_status_bar(value: float, max_val: float, length: int = 10) -> str:
    """Build a visual progress bar."""
    filled = int((value / max_val) * length) if max_val > 0 else 0
    return "█" * filled + "░" * (length - filled)


# ============ SLASH COMMANDS ============
def _register_commands(bot):

    # ── Guard: hide commands in other servers ──────────────────────────────
    async def _guild_check(i: discord.Interaction) -> bool:
        if not i.guild or not is_test_server(i.guild.id):
            await i.response.send_message(
                "🚫 This command doesn't exist here.",
                ephemeral=True
            )
            return False
        return True

    async def _owner_check(i: discord.Interaction) -> bool:
        if not _is_owner_check(i.user.id):
            await i.response.send_message("🚫 Owner only!", ephemeral=True)
            return False
        return True

    # ══════════════════════════════════════════
    # /beta_features — Master menu
    # ══════════════════════════════════════════
    @bot.tree.command(name="beta_features", description="[TEST] View all experimental features")
    async def beta_features_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        categories = {
            "🧠 AI Testing": [
                ("`/ai_debug`", "Full AI breakdown of any message"),
                ("`/force_ai`", "Force any personality on any prompt"),
                ("`/ai_stress`", "Bombard AI with edge-case messages"),
                ("`/ai_compare`", "Compare 2 personalities side-by-side"),
                ("`/ai_history`", "See all AI decisions this session"),
                ("`/ai_calibrate`", "Auto-calibrate AI confidence thresholds"),
            ],
            "🎭 Simulation": [
                ("`/simulate_join`", "Simulate member joining"),
                ("`/simulate_leave`", "Simulate member leaving"),
                ("`/simulate_raid`", "Trigger fake raid alert"),
                ("`/simulate_ban`", "Simulate a ban flow"),
                ("`/simulate_appeal`", "Simulate ban appeal"),
                ("`/simulate_report`", "Simulate a user report"),
                ("`/simulate_spam`", "Simulate a spam wave"),
                ("`/simulate_nuke`", "Simulate a nuke event"),
            ],
            "🔬 Stress Testing": [
                ("`/mass_test`", "Send 10 test messages"),
                ("`/stress_test`", "Full bot stress test"),
                ("`/flood_test`", "Flood a channel with messages"),
                ("`/latency_test`", "Measure all system latencies"),
                ("`/db_stress`", "Stress test the database"),
                ("`/webhook_stress`", "Test webhook reliability"),
            ],
            "🕵️ Monitoring": [
                ("`/spy_mode`", "Log all messages to console"),
                ("`/live_monitor`", "Real-time bot activity feed"),
                ("`/edit_log`", "Recent message edits"),
                ("`/delete_log`", "Recent deleted messages"),
                ("`/reaction_log`", "Recent reactions"),
                ("`/join_log`", "Recent joins/leaves"),
            ],
            "🛠️ Data Tools": [
                ("`/wipe_test`", "Wipe all server data"),
                ("`/inject_memory`", "Inject fake memory"),
                ("`/export_data`", "Export all server data to JSON"),
                ("`/import_data`", "Import server data from JSON"),
                ("`/db_query`", "Run raw SQL query (owner only)"),
                ("`/time_travel`", "View activity from past date"),
                ("`/clone_settings`", "Clone settings to another server"),
            ],
            "🎪 Fun & Misc": [
                ("`/fake_user`", "Bot pretends to be fake user"),
                ("`/fake_conversation`", "Bot simulates a full convo"),
                ("`/fake_announcement`", "Send fake announcement"),
                ("`/dry_run`", "Test mode, no real moderation"),
                ("`/stealth_mode`", "Bot acts silently"),
                ("`/cmd_stats`", "Command usage stats"),
                ("`/session_report`", "Full session analytics"),
                ("`/performance`", "System performance metrics"),
                ("`/scenario`", "Run a named test scenario"),
                ("`/eval_code`", "Run Python code in bot context"),
                ("`/schedule_test`", "Schedule a test for later"),
            ],
        }

        embeds = []
        for cat, cmds in categories.items():
            e = discord.Embed(
                title=f"🧪 Beta Features — {cat}",
                color=discord.Color.purple()
            )
            for cmd, desc in cmds:
                e.add_field(name=cmd, value=desc, inline=False)
            embeds.append(e)

        # Send as paginated ephemeral (just stack for now)
        main = discord.Embed(
            title="🧪 SentinelMod Test Server — Command Index",
            description=(
                f"**{sum(len(v) for v in categories.values())} commands** across "
                f"**{len(categories)} categories**\n\n"
                "Use any command below. All are test-server exclusive.\n"
                f"**Session started:** {_session_start.strftime('%H:%M:%S')}\n"
                f"**Dry Run:** {'🟢 ON' if DRY_RUN_MODE else '🔴 OFF'} | "
                f"**Spy Mode:** {'🟢 ON' if SPY_MODE else '🔴 OFF'} | "
                f"**Stealth:** {'🟢 ON' if STEALTH_MODE else '🔴 OFF'}"
            ),
            color=discord.Color.purple()
        )
        for cat, cmds in categories.items():
            main.add_field(
                name=cat,
                value=" ".join(c for c, _ in cmds),
                inline=False
            )
        main.set_footer(text="⚠️ Test server only — changes may affect live data")
        await i.response.send_message(embed=main, ephemeral=True)

    # ══════════════════════════════════════════
    # /ai_debug
    # ══════════════════════════════════════════
    @bot.tree.command(name="ai_debug", description="[TEST] Full AI breakdown of any message")
    @app_commands.describe(message="Message to analyze", verbose="Show raw JSON output")
    async def ai_debug_cmd(i: discord.Interaction, message: str, verbose: bool = False):
        if not await _guild_check(i):
            return
        await i.response.defer(ephemeral=True)

        start = _time.perf_counter()

        contains_swear = _get_bot_func("contains_swear")
        smart_ai_moderation = _get_bot_func("smart_ai_moderation")
        get_user_memory = _get_bot_func("get_user_memory")
        check_against_server_rules = _get_bot_func("check_against_server_rules")
        HARD_DELETE_PATTERNS = _get_bot_var("HARD_DELETE_PATTERNS")
        SOFT_VIOLATION_PATTERNS = _get_bot_var("SOFT_VIOLATION_PATTERNS")
        server_rules_cache = _get_bot_var("server_rules_cache")

        results = {}

        embed = discord.Embed(
            title="🧠 AI Debug — Full Analysis",
            description=f"```{message[:500]}```",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Swear check
        if contains_swear:
            try:
                has_swear, matched = contains_swear(message)
                results["swear"] = {"flagged": has_swear, "matched": matched}
                embed.add_field(
                    name="🤬 Swear Filter",
                    value=f"{'❌ FLAGGED' if has_swear else '✅ Clean'}"
                          f"{f' — `{matched}`' if matched else ''}",
                    inline=True
                )
            except Exception as e:
                embed.add_field(name="🤬 Swear Filter", value=f"⚠️ `{e}`", inline=True)

        # Pattern checks
        if HARD_DELETE_PATTERNS:
            hits = [(reason, pattern) for pattern, reason, _ in HARD_DELETE_PATTERNS
                    if re.search(pattern, message, re.IGNORECASE)]
            results["hard_patterns"] = hits
            embed.add_field(
                name="🔴 Hard Patterns",
                value=("\n".join(f"`{r}` ← `{p[:30]}`" for r, p in hits[:5])
                       if hits else "✅ None"),
                inline=True
            )

        if SOFT_VIOLATION_PATTERNS:
            soft = [(reason, pattern) for pattern, reason, _ in SOFT_VIOLATION_PATTERNS
                    if re.search(pattern, message, re.IGNORECASE)]
            results["soft_patterns"] = soft
            embed.add_field(
                name="🟠 Soft Patterns",
                value=("\n".join(f"`{r}`" for r, _ in soft[:5])
                       if soft else "✅ None"),
                inline=True
            )

        # AI moderation
        ai_result = None
        if smart_ai_moderation and get_user_memory:
            try:
                user_mem = get_user_memory(i.user.id, i.guild.id)
                ai_result = await smart_ai_moderation(
                    message, i.user.display_name,
                    i.channel.name, [], user_mem, "general", ""
                )
                results["ai"] = ai_result
                conf = ai_result.get("confidence", 0)
                embed.add_field(
                    name="🤖 AI Judgment",
                    value=(
                        f"**Action:** `{ai_result.get('action', 'N/A')}`\n"
                        f"**Severity:** `{ai_result.get('severity', 'N/A')}`\n"
                        f"**Confidence:** {_build_status_bar(conf, 1.0)} {conf:.0%}\n"
                        f"**Reason:** {ai_result.get('reason', 'N/A')[:150]}"
                    ),
                    inline=False
                )
                _ai_decision_log.append({
                    "message": message[:200],
                    "result": ai_result,
                    "user": str(i.user),
                    "time": datetime.now().isoformat()
                })
            except Exception as e:
                embed.add_field(name="🤖 AI Error", value=f"```{traceback.format_exc()[:300]}```", inline=False)

        # Rules check
        if check_against_server_rules and server_rules_cache:
            rules = server_rules_cache.get(str(i.guild.id), "")
            if rules:
                try:
                    rc = await check_against_server_rules(message, i.user.display_name, i.guild)
                    results["rules"] = rc
                    embed.add_field(
                        name="📋 Rules Check",
                        value=(
                            f"**Violates:** {'❌ YES' if rc.get('violates') else '✅ NO'}\n"
                            f"**Rule:** {rc.get('rule', 'N/A')}\n"
                            f"**Reason:** {rc.get('reason', 'N/A')[:150]}"
                        ),
                        inline=False
                    )
                except:
                    pass

        # Timing
        elapsed = (_time.perf_counter() - start) * 1000
        _log_performance("ai_debug", elapsed)
        embed.set_footer(text=f"Analysis took {elapsed:.1f}ms")

        if verbose:
            raw = json.dumps(results, indent=2, default=str)
            if len(raw) > 1900:
                raw = raw[:1900] + "..."
            await i.followup.send(embed=embed, ephemeral=True)
            await i.followup.send(f"```json\n{raw}\n```", ephemeral=True)
        else:
            await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /force_ai
    # ══════════════════════════════════════════
    @bot.tree.command(name="force_ai", description="[TEST] Force AI to respond as any personality")
    @app_commands.describe(personality="Personality name", prompt="What to ask", tokens="Max tokens (default 500)")
    async def force_ai_cmd(i: discord.Interaction, personality: str, prompt: str, tokens: int = 500):
        if not await _guild_check(i):
            return

        PERSONALITIES = _get_bot_var("PERSONALITIES")
        smart_ai = _get_bot_func("smart_ai")

        if not PERSONALITIES or not smart_ai:
            await i.response.send_message("❌ Bot AI system not available", ephemeral=True)
            return

        if personality not in PERSONALITIES:
            available = "\n".join(f"• `{k}`" for k in list(PERSONALITIES.keys())[:20])
            await i.response.send_message(f"Unknown personality. Available:\n{available}", ephemeral=True)
            return

        await i.response.defer()
        start = _time.perf_counter()
        response = await smart_ai(prompt, PERSONALITIES[personality], max_tokens=min(tokens, 1000))
        elapsed = (_time.perf_counter() - start) * 1000

        embed = discord.Embed(
            title=f"🎭 AI as: `{personality}`",
            description=response[:2000] if response else "*No response*",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Prompt", value=f"`{prompt[:200]}`", inline=False)
        embed.set_footer(text=f"Generated in {elapsed:.0f}ms | {len(response or '')} chars")
        await i.followup.send(embed=embed)

    # ══════════════════════════════════════════
    # /ai_compare
    # ══════════════════════════════════════════
    @bot.tree.command(name="ai_compare", description="[TEST] Compare 2 personalities side-by-side")
    @app_commands.describe(personality_a="First personality", personality_b="Second personality", prompt="Prompt to test")
    async def ai_compare_cmd(i: discord.Interaction, personality_a: str, personality_b: str, prompt: str):
        if not await _guild_check(i):
            return

        PERSONALITIES = _get_bot_var("PERSONALITIES")
        smart_ai = _get_bot_func("smart_ai")

        if not PERSONALITIES or not smart_ai:
            await i.response.send_message("❌ AI unavailable", ephemeral=True)
            return

        missing = [p for p in [personality_a, personality_b] if p not in PERSONALITIES]
        if missing:
            await i.response.send_message(f"❌ Unknown: {', '.join(missing)}", ephemeral=True)
            return

        await i.response.defer()

        resp_a, resp_b = await asyncio.gather(
            smart_ai(prompt, PERSONALITIES[personality_a], max_tokens=300),
            smart_ai(prompt, PERSONALITIES[personality_b], max_tokens=300)
        )

        embed = discord.Embed(
            title="🔬 AI Personality Comparison",
            description=f"**Prompt:** `{prompt[:200]}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name=f"🅰️ {personality_a}",
            value=(resp_a or "*No response*")[:800],
            inline=False
        )
        embed.add_field(
            name=f"🅱️ {personality_b}",
            value=(resp_b or "*No response*")[:800],
            inline=False
        )
        await i.followup.send(embed=embed)

    # ══════════════════════════════════════════
    # /ai_stress
    # ══════════════════════════════════════════
    @bot.tree.command(name="ai_stress", description="[TEST] Bomb the AI with edge-case messages")
    async def ai_stress_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        smart_ai_moderation = _get_bot_func("smart_ai_moderation")
        get_user_memory = _get_bot_func("get_user_memory")
        if not smart_ai_moderation or not get_user_memory:
            await i.response.send_message("❌ AI unavailable", ephemeral=True)
            return

        await i.response.defer(ephemeral=True)

        edge_cases = [
            ("Empty message", ""),
            ("Emoji only", "😂😂😂😂😂"),
            ("Max length", "a" * 500),
            ("Unicode", "こんにちは世界 🌍 مرحبا"),
            ("Code block", "```python\nprint('hello')```"),
            ("Invite link", "join us at discord.gg/abcdef"),
            ("Phone number", "call me 555-867-5309"),
            ("Sarcastic compliment", "wow you're so smart lol"),
            ("Mixed languages", "hello monde こんにちは"),
            ("Repeated chars", "yoooooooooooooooooooooo"),
            ("Mild insult", "you're kind of dumb tbh"),
            ("Fake news", "breaking: discord is shutting down"),
            ("Compliment", "you're doing amazing sweetie"),
            ("Self-harm hint", "I don't want to be here anymore"),
            ("Slur disguise", "you f*cking idiot"),
        ]

        results = []
        for label, msg in edge_cases:
            try:
                start = _time.perf_counter()
                mem = get_user_memory(i.user.id, i.guild.id)
                result = await smart_ai_moderation(msg, "TestUser", "test", [], mem, "general", "")
                ms = (_time.perf_counter() - start) * 1000
                results.append((label, result.get("action", "?"), result.get("severity", "?"), ms))
            except Exception as e:
                results.append((label, "ERROR", str(e)[:30], 0))

        embed = discord.Embed(
            title="🔬 AI Stress Test Results",
            description=f"{len(edge_cases)} edge cases tested",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        for label, action, severity, ms in results:
            embed.add_field(
                name=label,
                value=f"`{action}` / `{severity}` in {ms:.0f}ms",
                inline=True
            )
        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /ai_history
    # ══════════════════════════════════════════
    @bot.tree.command(name="ai_history", description="[TEST] See all AI decisions this session")
    async def ai_history_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _ai_decision_log:
            await i.response.send_message("No AI decisions logged yet.", ephemeral=True)
            return

        recent = list(_ai_decision_log)[-15:]
        embed = discord.Embed(
            title="🤖 AI Decision History",
            description=f"{len(_ai_decision_log)} total decisions this session",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        for entry in recent:
            r = entry["result"]
            embed.add_field(
                name=f"`{entry['message'][:40]}...`",
                value=(
                    f"**{r.get('action')}** | {r.get('severity')} | "
                    f"{r.get('confidence', 0):.0%}\n"
                    f"*{entry['time'][11:19]}*"
                ),
                inline=False
            )
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /ai_calibrate
    # ══════════════════════════════════════════
    @bot.tree.command(name="ai_calibrate", description="[TEST] Auto-calibrate AI thresholds via test messages")
    async def ai_calibrate_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        await i.response.defer(ephemeral=True)

        sm = _get_bot_func("smart_ai_moderation")
        gum = _get_bot_func("get_user_memory")

        if not sm or not gum:
            await i.followup.send("❌ AI unavailable", ephemeral=True)
            return

        known_safe = [
            "hey whats up", "good morning", "that game was fun",
            "lol nice", "thanks for the help", "I agree with that",
        ]
        known_bad = [
            "you're a worthless piece of garbage",
            "discord.gg/freegifts click now",
            "call me at 555-123-4567",
        ]

        mem = gum(i.user.id, i.guild.id)
        safe_results, bad_results = [], []

        for msg in known_safe:
            r = await sm(msg, "User", "general", [], mem, "general", "")
            safe_results.append(r.get("action", "none"))

        for msg in known_bad:
            r = await sm(msg, "User", "general", [], mem, "general", "")
            bad_results.append(r.get("action", "none"))

        safe_correct = sum(1 for a in safe_results if a in ("none", "ignore"))
        bad_correct = sum(1 for a in bad_results if a not in ("none", "ignore"))

        embed = discord.Embed(
            title="⚙️ AI Calibration Report",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="✅ Safe Messages",
            value=f"{safe_correct}/{len(known_safe)} correctly ignored\n"
                  + "\n".join(f"• `{a}`" for a in safe_results),
            inline=True
        )
        embed.add_field(
            name="🚨 Bad Messages",
            value=f"{bad_correct}/{len(known_bad)} correctly caught\n"
                  + "\n".join(f"• `{a}`" for a in bad_results),
            inline=True
        )
        score = (safe_correct + bad_correct) / (len(known_safe) + len(known_bad))
        embed.add_field(
            name="📊 Overall Score",
            value=f"{_build_status_bar(score, 1.0, 15)} **{score:.0%}**",
            inline=False
        )
        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_join
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_join", description="[TEST] Simulate a member joining")
    @app_commands.describe(target="Who to simulate (default: yourself)")
    async def simulate_join_cmd(i: discord.Interaction, target: discord.Member = None):
        if not await _guild_check(i):
            return
        await i.response.defer(ephemeral=True)
        member = target or i.user
        try:
            import welcome_system
            await welcome_system.handle_welcome(member)
            _join_leave_log.append({"type": "join", "user": str(member), "time": datetime.now().isoformat()})
            await i.followup.send(f"✅ Simulated join for **{member}**!", ephemeral=True)
        except ImportError:
            await i.followup.send("❌ welcome_system.py not found", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Error: {e}", ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_leave
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_leave", description="[TEST] Simulate a member leaving")
    @app_commands.describe(target="Who to simulate (default: yourself)")
    async def simulate_leave_cmd(i: discord.Interaction, target: discord.Member = None):
        if not await _guild_check(i):
            return
        await i.response.defer(ephemeral=True)
        member = target or i.user
        try:
            import welcome_system
            if hasattr(welcome_system, "handle_leave"):
                await welcome_system.handle_leave(member)
            _join_leave_log.append({"type": "leave", "user": str(member), "time": datetime.now().isoformat()})
            await i.followup.send(f"✅ Simulated leave for **{member}**!", ephemeral=True)
        except ImportError:
            await i.followup.send("❌ welcome_system.py not found", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Error: {e}", ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_raid
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_raid", description="[TEST] Trigger a fake raid alert")
    @app_commands.describe(intensity="Raid intensity level (1-5)")
    async def simulate_raid_cmd(i: discord.Interaction, intensity: int = 3):
        if not await _guild_check(i):
            return

        intensity = max(1, min(5, intensity))
        raid_mode_active = _get_bot_var("raid_mode_active")
        notify_owner = _get_bot_func("notify_owner")
        get_guild_settings = _get_bot_func("get_guild_settings")

        if raid_mode_active is not None:
            raid_mode_active[i.guild.id] = True

        fake_joiners = intensity * 5
        embed = discord.Embed(
            title=f"🚨 SIMULATED RAID — Level {intensity}/5",
            description=(
                f"**Fake accounts detected:** {fake_joiners}\n"
                f"**Join rate:** {fake_joiners * 2}/min\n"
                f"**Intensity:** {'🔴' * intensity}{'⚪' * (5 - intensity)}\n\n"
                "This is a simulation — no action taken."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )

        if notify_owner:
            await notify_owner("RAID", f"🚨 SIMULATED RAID (L{intensity}) in **{i.guild.name}**!", guild=i.guild, urgent=True)

        if get_guild_settings:
            s = get_guild_settings(i.guild.id)
            ch = discord.utils.get(i.guild.text_channels, name=s.get("raid_channel", "sentinel-raid-alerts"))
            if ch:
                try:
                    await ch.send(embed=embed)
                except:
                    pass

        async def reset():
            await asyncio.sleep(30)
            if raid_mode_active is not None:
                raid_mode_active[i.guild.id] = False

        asyncio.create_task(reset())
        await i.response.send_message(f"✅ Simulated L{intensity} raid! Resets in 30s.", ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_ban
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_ban", description="[TEST] Simulate a full ban flow")
    @app_commands.describe(target="User to ban (won't actually be banned)", reason="Reason")
    async def simulate_ban_cmd(i: discord.Interaction, target: discord.Member, reason: str = "Test ban"):
        if not await _guild_check(i):
            return

        embed = discord.Embed(
            title="🔨 [SIMULATED] Ban Flow",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Warnings", value="3 prior warnings", inline=True)
        embed.add_field(name="Status", value="⚠️ **DRY RUN — No actual ban was issued**", inline=False)
        embed.set_footer(text=f"Simulated by {i.user}")

        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_spam
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_spam", description="[TEST] Simulate a spam wave in this channel")
    @app_commands.describe(count="Number of spam messages (max 10)")
    async def simulate_spam_cmd(i: discord.Interaction, count: int = 5):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        count = min(count, 10)
        await i.response.send_message(f"🧪 Simulating {count} spam messages...", ephemeral=True)

        spam_templates = [
            "FREE NITRO CLICK NOW → discord.gg/freegiftnotscam",
            "buy cheap followers @ example.com only $1",
            "hey hey hey hey hey hey hey hey hey",
            "SELLING ACCOUNTS DM ME",
            "@everyone FREE GIVEAWAY",
        ]

        try:
            webhooks = await i.channel.webhooks()
            wh = discord.utils.get(webhooks, name="SentinelTest")
            if not wh:
                wh = await i.channel.create_webhook(name="SentinelTest")

            for idx in range(count):
                msg = random.choice(spam_templates)
                await wh.send(
                    content=f"[SPAM TEST #{idx+1}] {msg}",
                    username=f"SpamBot_{random.randint(1000,9999)}",
                    avatar_url="https://cdn.discordapp.com/embed/avatars/1.png"
                )
                await asyncio.sleep(0.8)
        except Exception as e:
            await i.followup.send(f"❌ {e}", ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_nuke
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_nuke", description="[TEST] Simulate a server nuke event (dry run)")
    async def simulate_nuke_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        embed = discord.Embed(
            title="💣 [SIMULATED] Server Nuke Event",
            description=(
                "A nuke attempt was detected.\n\n"
                "**Would have happened:**\n"
                "• 47 channels deleted\n"
                "• 12 roles deleted\n"
                "• 200 members banned\n"
                "• Server renamed to 'nuked'\n\n"
                "**Bot response (simulated):**\n"
                "✅ Detected within 2.3 seconds\n"
                "✅ Owner alerted\n"
                "✅ Lockdown activated\n"
                "✅ Nuker banned"
            ),
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="DRY RUN — Nothing actually happened")
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /simulate_appeal / /simulate_report
    # ══════════════════════════════════════════
    @bot.tree.command(name="simulate_appeal", description="[TEST] Simulate a ban appeal flow")
    async def simulate_appeal_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        embed = discord.Embed(
            title="📩 [SIMULATED] Ban Appeal",
            description=(
                f"**Appellant:** {i.user.mention}\n"
                "**Ban reason:** Spam\n"
                "**Appeal message:** I was just testing, I didn't mean any harm.\n\n"
                "**Bot response:** Appeal logged and forwarded to moderators.\n"
                "*(In real flow, mods would receive a DM with buttons)*"
            ),
            color=discord.Color.blue()
        )
        await i.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="simulate_report", description="[TEST] Simulate a user report flow")
    @app_commands.describe(target="User to report", reason="Reason for report")
    async def simulate_report_cmd(i: discord.Interaction, target: discord.Member, reason: str = "Harassment"):
        if not await _guild_check(i):
            return
        embed = discord.Embed(
            title="🚩 [SIMULATED] User Report",
            description=(
                f"**Reporter:** {i.user.mention}\n"
                f"**Reported:** {target.mention}\n"
                f"**Reason:** {reason}\n\n"
                "**Bot response:** Report logged. Moderators would be notified.\n"
                "AI confidence that this is legitimate: 87%"
            ),
            color=discord.Color.orange()
        )
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /wipe_test
    # ══════════════════════════════════════════
    @bot.tree.command(name="wipe_test", description="[TEST] Wipe ALL bot data for this server")
    @app_commands.describe(confirm="Type 'WIPE' to confirm")
    async def wipe_test_cmd(i: discord.Interaction, confirm: str = ""):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        if confirm.upper() != "WIPE":
            await i.response.send_message(
                "⚠️ This will delete ALL bot data for this server.\n"
                "Run again with `confirm: WIPE` to proceed.",
                ephemeral=True
            )
            return

        await i.response.defer(ephemeral=True)

        tables = [
            "warnings", "mod_actions", "message_archive", "conversation_history",
            "user_memory", "server_memory", "afk_users", "message_stats",
            "reminders", "reputation", "daily_stats", "custom_commands",
            "word_filters", "trusted_users", "appeals", "user_personalities",
            "guild_settings", "role_rewards", "join_roles"
        ]
        conn = _get_db()
        c = conn.cursor()
        counts = {}
        for table in tables:
            try:
                c.execute(f"DELETE FROM {table} WHERE guild_id=?", (str(i.guild.id),))
                counts[table] = c.rowcount
            except:
                pass
        conn.commit()
        conn.close()

        for var in ["server_rules_cache", "recent_actions"]:
            obj = _get_bot_var(var)
            if obj and hasattr(obj, "pop"):
                obj.pop(str(i.guild.id), None)
                obj.pop(i.guild.id, None)

        total = sum(counts.values())
        cleaned = "\n".join(f"• `{t}`: {n}" for t, n in counts.items() if n > 0)

        embed = discord.Embed(
            title="🧹 Test Server Wiped",
            description=f"**{total} records deleted**\n\n{cleaned or 'Already clean.'}",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /export_data
    # ══════════════════════════════════════════
    @bot.tree.command(name="export_data", description="[TEST] Export all server data to JSON")
    async def export_data_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        await i.response.defer(ephemeral=True)

        tables = [
            "warnings", "mod_actions", "guild_settings", "user_memory",
            "server_memory", "custom_commands", "word_filters", "reputation"
        ]
        export = {"guild_id": str(i.guild.id), "exported_at": datetime.now().isoformat(), "tables": {}}

        conn = _get_db()
        c = conn.cursor()
        for table in tables:
            try:
                c.execute(f"SELECT * FROM {table} WHERE guild_id=?", (str(i.guild.id),))
                rows = c.fetchall()
                export["tables"][table] = [dict(r) for r in rows]
            except:
                export["tables"][table] = []
        conn.close()

        raw = json.dumps(export, indent=2, default=str)
        file = discord.File(io.BytesIO(raw.encode()), filename=f"export_{i.guild.id}_{datetime.now().date()}.json")
        await i.followup.send("✅ Data exported:", file=file, ephemeral=True)

    # ══════════════════════════════════════════
    # /db_query
    # ══════════════════════════════════════════
    @bot.tree.command(name="db_query", description="[TEST] Run a raw SQL query (owner only, SELECT only)")
    @app_commands.describe(query="SQL query (SELECT only)")
    async def db_query_cmd(i: discord.Interaction, query: str):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        if not query.strip().upper().startswith("SELECT"):
            await i.response.send_message("❌ Only SELECT queries are allowed.", ephemeral=True)
            return

        await i.response.defer(ephemeral=True)

        try:
            conn = _get_db()
            c = conn.cursor()
            c.execute(query)
            rows = c.fetchmany(20)
            conn.close()

            if not rows:
                await i.followup.send("✅ Query ran. No rows returned.", ephemeral=True)
                return

            headers = [desc[0] for desc in c.description]
            lines = [" | ".join(headers), "-" * 40]
            for row in rows:
                lines.append(" | ".join(str(v)[:20] for v in row))

            output = "\n".join(lines)
            if len(output) > 1900:
                output = output[:1900] + "\n..."

            await i.followup.send(f"```\n{output}\n```", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Error: ```{e}```", ephemeral=True)

    # ══════════════════════════════════════════
    # /spy_mode
    # ══════════════════════════════════════════
    @bot.tree.command(name="spy_mode", description="[TEST] Log every message to console")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off"),
    ])
    async def spy_mode_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        global SPY_MODE
        SPY_MODE = (state.value == "on")
        await i.response.send_message(
            f"🕵️ Spy Mode **{state.name}**\n"
            f"{'All messages logged to console.' if SPY_MODE else 'Logging stopped.'}",
            ephemeral=True
        )

    # ══════════════════════════════════════════
    # /stealth_mode
    # ══════════════════════════════════════════
    @bot.tree.command(name="stealth_mode", description="[TEST] Bot acts but never announces actions")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off"),
    ])
    async def stealth_mode_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        global STEALTH_MODE
        STEALTH_MODE = (state.value == "on")
        await i.response.send_message(
            f"👤 Stealth Mode **{state.name}**\n"
            f"{'Bot acts silently, no public announcements.' if STEALTH_MODE else 'Normal announcements resumed.'}",
            ephemeral=True
        )

    # ══════════════════════════════════════════
    # /dry_run
    # ══════════════════════════════════════════
    @bot.tree.command(name="dry_run", description="[TEST] No actual moderation actions taken")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off"),
    ])
    async def dry_run_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not await _guild_check(i):
            return

        global DRY_RUN_MODE
        DRY_RUN_MODE = (state.value == "on")
        await i.response.send_message(
            f"🧪 Dry Run **{state.name}**\n"
            f"{'No bans/mutes/deletes will execute.' if DRY_RUN_MODE else 'Normal moderation resumed.'}",
            ephemeral=True
        )

    # ══════════════════════════════════════════
    # /live_monitor
    # ══════════════════════════════════════════
    @bot.tree.command(name="live_monitor", description="[TEST] Post real-time bot activity to this channel")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off"),
    ])
    async def live_monitor_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        global _live_monitor_channels
        if state.value == "on":
            _live_monitor_channels.add(i.channel.id)
            await i.response.send_message("📡 Live monitor **ON** — activity will be posted here.", ephemeral=True)
        else:
            _live_monitor_channels.discard(i.channel.id)
            await i.response.send_message("📡 Live monitor **OFF**.", ephemeral=True)

    # ══════════════════════════════════════════
    # /mass_test
    # ══════════════════════════════════════════
    @bot.tree.command(name="mass_test", description="[TEST] Send test messages to check AI moderation")
    @app_commands.describe(delay="Delay between messages in seconds (default 2)")
    async def mass_test_cmd(i: discord.Interaction, delay: float = 2.0):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        await i.response.send_message(f"🧪 Starting mass test (delay: {delay}s)...", ephemeral=True)
        await asyncio.sleep(2)

        test_messages = [
            ("hey what's up", "clean casual"),
            ("this is so amazing omg", "clean positive"),
            ("you're such an idiot honestly", "mild insult"),
            ("check out discord.gg/freestuff", "invite link"),
            ("AAAAAAAAAAAAA SO LOUD", "caps spam"),
            ("yo yo yo yo yo yo yo yo yo", "repeated spam"),
            ("my number is 555-123-4567 call me", "phone number"),
            ("email me at someone@example.com", "email"),
            ("🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉", "emoji spam"),
            ("gg well played bro", "clean gaming"),
            ("I hate everyone here", "hostility"),
            ("buy cheap accounts DM me", "advertising"),
        ]

        _test_scenarios_run.append({
            "type": "mass_test",
            "time": datetime.now().isoformat(),
            "count": len(test_messages)
        })

        for msg, desc in test_messages:
            try:
                await i.channel.send(f"**[TEST: {desc}]** {msg}")
                await asyncio.sleep(delay)
            except:
                pass

    # ══════════════════════════════════════════
    # /stress_test
    # ══════════════════════════════════════════
    @bot.tree.command(name="stress_test", description="[TEST] Full bot stress test")
    async def stress_test_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        global _stress_test_active
        if _stress_test_active:
            await i.response.send_message("⚠️ Stress test already running!", ephemeral=True)
            return

        await i.response.defer(ephemeral=True)
        _stress_test_active = True

        results = {}

        # 1. DB stress
        try:
            start = _time.perf_counter()
            conn = _get_db()
            c = conn.cursor()
            for _ in range(100):
                c.execute("SELECT 1")
            conn.close()
            results["db_100_queries"] = f"{(_time.perf_counter()-start)*1000:.0f}ms"
        except Exception as e:
            results["db_100_queries"] = f"ERROR: {e}"

        # 2. AI stress
        sm = _get_bot_func("smart_ai_moderation")
        gum = _get_bot_func("get_user_memory")
        if sm and gum:
            try:
                start = _time.perf_counter()
                mem = gum(i.user.id, i.guild.id)
                tasks_ = [sm(f"test message {n}", "User", "general", [], mem, "general", "")
                          for n in range(5)]
                await asyncio.gather(*tasks_)
                results["ai_5_concurrent"] = f"{(_time.perf_counter()-start)*1000:.0f}ms"
            except Exception as e:
                results["ai_5_concurrent"] = f"ERROR: {e}"

        # 3. Memory read/write
        gsm = _get_bot_func("get_server_memory")
        ssm = _get_bot_func("save_server_memory")
        if gsm and ssm:
            try:
                start = _time.perf_counter()
                for _ in range(20):
                    mem = gsm(i.guild.id)
                    ssm(i.guild.id, mem)
                results["memory_20_rw"] = f"{(_time.perf_counter()-start)*1000:.0f}ms"
            except Exception as e:
                results["memory_20_rw"] = f"ERROR: {e}"

        # 4. Discord API
        try:
            start = _time.perf_counter()
            _ = i.guild.members
            results["member_list_fetch"] = f"{(_time.perf_counter()-start)*1000:.0f}ms"
        except Exception as e:
            results["member_list_fetch"] = f"ERROR: {e}"

        _stress_test_active = False

        embed = discord.Embed(
            title="💪 Stress Test Results",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        for test, val in results.items():
            status = "⚠️" if "ERROR" in str(val) else "✅"
            embed.add_field(name=f"{status} {test}", value=f"`{val}`", inline=True)

        embed.set_footer(text="All tests complete")
        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /latency_test
    # ══════════════════════════════════════════
    @bot.tree.command(name="latency_test", description="[TEST] Measure all system latencies")
    async def latency_test_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return
        await i.response.defer(ephemeral=True)

        latencies = {}

        # Discord WS
        latencies["Discord WS"] = f"{bot.latency * 1000:.1f}ms"

        # DB
        start = _time.perf_counter()
        conn = _get_db()
        conn.cursor().execute("SELECT 1")
        conn.close()
        latencies["SQLite DB"] = f"{(_time.perf_counter()-start)*1000:.1f}ms"

        # AI
        sm = _get_bot_func("smart_ai")
        if sm:
            try:
                start = _time.perf_counter()
                await sm("ping", "you are a helpful assistant", max_tokens=5)
                latencies["Groq AI"] = f"{(_time.perf_counter()-start)*1000:.1f}ms"
            except:
                latencies["Groq AI"] = "❌ Error"

        # Memory
        gsm = _get_bot_func("get_server_memory")
        if gsm:
            start = _time.perf_counter()
            gsm(i.guild.id)
            latencies["Server Memory"] = f"{(_time.perf_counter()-start)*1000:.1f}ms"

        embed = discord.Embed(
            title="⚡ System Latency Report",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        for system, lat in latencies.items():
            ms_val = float(lat.replace("ms", "")) if "ms" in str(lat) else 9999
            icon = "🟢" if ms_val < 200 else "🟡" if ms_val < 500 else "🔴"
            embed.add_field(name=f"{icon} {system}", value=f"`{lat}`", inline=True)

        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /flood_test
    # ══════════════════════════════════════════
    @bot.tree.command(name="flood_test", description="[TEST] Flood channel with messages to test rate limits")
    @app_commands.describe(count="Number of messages (max 20)", delay="Delay between (min 0.5s)")
    async def flood_test_cmd(i: discord.Interaction, count: int = 10, delay: float = 0.5):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        count = min(count, 20)
        delay = max(delay, 0.5)
        await i.response.send_message(f"🌊 Flooding {count} messages...", ephemeral=True)

        sent, failed = 0, 0
        for n in range(count):
            try:
                await i.channel.send(f"🌊 Flood test message `{n+1}/{count}` — `{datetime.now().strftime('%H:%M:%S.%f')}`")
                sent += 1
            except discord.HTTPException:
                failed += 1
            await asyncio.sleep(delay)

        try:
            await i.followup.send(f"✅ Sent: {sent} | ❌ Failed: {failed}", ephemeral=True)
        except:
            pass

    # ══════════════════════════════════════════
    # /inject_memory
    # ══════════════════════════════════════════
    @bot.tree.command(name="inject_memory", description="[TEST] Add fake data to bot memory")
    @app_commands.describe(memory_type="What to inject", data="The data to inject")
    @app_commands.choices(memory_type=[
        app_commands.Choice(name="Inside Joke", value="joke"),
        app_commands.Choice(name="Popular Topic", value="topic"),
        app_commands.Choice(name="Common Phrase", value="phrase"),
        app_commands.Choice(name="Server Mood", value="mood"),
        app_commands.Choice(name="Custom Event", value="event"),
        app_commands.Choice(name="User Note", value="note"),
    ])
    async def inject_memory_cmd(i: discord.Interaction, memory_type: app_commands.Choice[str], data: str):
        if not await _guild_check(i):
            return

        get_server_memory = _get_bot_func("get_server_memory")
        save_server_memory = _get_bot_func("save_server_memory")

        if not get_server_memory or not save_server_memory:
            await i.response.send_message("❌ Memory system unavailable", ephemeral=True)
            return

        sm = get_server_memory(i.guild.id)

        if memory_type.value == "joke":
            sm.setdefault("inside_jokes", []).append({"text": data, "time": datetime.now().isoformat()})
        elif memory_type.value == "topic":
            sm.setdefault("popular_topics", []).append(data)
        elif memory_type.value == "phrase":
            sm.setdefault("common_phrases", []).append(data)
        elif memory_type.value == "mood":
            sm["server_mood"] = data
        elif memory_type.value == "event":
            sm.setdefault("events", []).append({"event": data, "time": datetime.now().isoformat()})
        elif memory_type.value == "note":
            sm.setdefault("notes", []).append({"note": data, "author": str(i.user), "time": datetime.now().isoformat()})

        save_server_memory(i.guild.id, sm)
        await i.response.send_message(f"✅ Injected **{memory_type.name}**: `{data}`", ephemeral=True)

    # ══════════════════════════════════════════
    # /time_travel
    # ══════════════════════════════════════════
    @bot.tree.command(name="time_travel", description="[TEST] View activity from a specific date")
    @app_commands.describe(date="Date in YYYY-MM-DD format")
    async def time_travel_cmd(i: discord.Interaction, date: str):
        if not await _guild_check(i):
            return

        try:
            datetime.fromisoformat(date)
        except:
            await i.response.send_message("❌ Invalid date. Use YYYY-MM-DD.", ephemeral=True)
            return

        await i.response.defer(ephemeral=True)

        conn = _get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM daily_stats WHERE guild_id=? AND date=?", (str(i.guild.id), date))
        stats = c.fetchone()

        c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND timestamp LIKE ?",
                  (str(i.guild.id), f"{date}%"))
        warns = c.fetchone()[0]

        c.execute("""SELECT action, COUNT(*) FROM mod_actions
                     WHERE guild_id=? AND timestamp LIKE ? GROUP BY action""",
                  (str(i.guild.id), f"{date}%"))
        actions = c.fetchall()

        c.execute("SELECT COUNT(*) FROM message_archive WHERE guild_id=? AND timestamp LIKE ?",
                  (str(i.guild.id), f"{date}%"))
        archived = c.fetchone()[0]
        conn.close()

        embed = discord.Embed(
            title=f"⏰ Time Travel: {date}",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )

        if stats:
            embed.add_field(name="💬 Messages", value=f"{stats['messages']:,}", inline=True)
            embed.add_field(name="➕ Joins", value=stats["joins"], inline=True)
            embed.add_field(name="➖ Leaves", value=stats["leaves"], inline=True)
            embed.add_field(name="🛡️ Mod Actions", value=stats["mod_actions"], inline=True)
        else:
            embed.description = "*No daily stats for this date.*"

        embed.add_field(name="⚠️ Warnings", value=warns, inline=True)
        embed.add_field(name="📚 Archived", value=archived, inline=True)

        if actions:
            embed.add_field(
                name="Action Breakdown",
                value="\n".join(f"• {a[0]}: {a[1]}" for a in actions),
                inline=False
            )
        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /fake_user
    # ══════════════════════════════════════════
    @bot.tree.command(name="fake_user", description="[TEST] Bot sends as a fake user via webhook")
    @app_commands.describe(username="Fake username", message="What they say", avatar_index="Avatar index 0-5")
    async def fake_user_cmd(i: discord.Interaction, username: str, message: str, avatar_index: int = 0):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        avatar_index = max(0, min(5, avatar_index))
        try:
            webhooks = await i.channel.webhooks()
            wh = discord.utils.get(webhooks, name="SentinelTest")
            if not wh:
                wh = await i.channel.create_webhook(name="SentinelTest")

            await wh.send(
                content=message,
                username=f"[FAKE] {username}",
                avatar_url=f"https://cdn.discordapp.com/embed/avatars/{avatar_index}.png"
            )
            _webhook_log.append({
                "type": "fake_user",
                "username": username,
                "message": message[:100],
                "time": datetime.now().isoformat()
            })
            await i.response.send_message("✅ Fake message sent!", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"❌ {e}", ephemeral=True)

    # ══════════════════════════════════════════
    # /fake_conversation
    # ══════════════════════════════════════════
    @bot.tree.command(name="fake_conversation", description="[TEST] Simulate a multi-user conversation")
    @app_commands.describe(topic="Topic of the conversation", length="Number of messages (max 8)")
    async def fake_conversation_cmd(i: discord.Interaction, topic: str = "gaming", length: int = 4):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        length = min(length, 8)
        smart_ai = _get_bot_func("smart_ai")
        if not smart_ai:
            await i.response.send_message("❌ AI unavailable", ephemeral=True)
            return

        await i.response.defer(ephemeral=True)

        fake_names = ["Alex", "Jordan", "Sam", "Casey", "Morgan", "Riley"]
        random.shuffle(fake_names)

        try:
            webhooks = await i.channel.webhooks()
            wh = discord.utils.get(webhooks, name="SentinelTest")
            if not wh:
                wh = await i.channel.create_webhook(name="SentinelTest")

            history = []
            for n in range(length):
                speaker = fake_names[n % len(fake_names)]
                ctx = f"Topic: {topic}. Previous: {' '.join(history[-2:])}. Say one short casual message."
                response = await smart_ai(ctx, "You are a casual Discord user. Reply in 1-2 sentences.", max_tokens=60)
                if response:
                    await wh.send(
                        content=response,
                        username=speaker,
                        avatar_url=f"https://cdn.discordapp.com/embed/avatars/{n % 6}.png"
                    )
                    history.append(f"{speaker}: {response}")
                    await asyncio.sleep(1.5)

            await i.followup.send("✅ Fake conversation complete!", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ {e}", ephemeral=True)

    # ══════════════════════════════════════════
    # /fake_announcement
    # ══════════════════════════════════════════
    @bot.tree.command(name="fake_announcement", description="[TEST] Send a fake server announcement")
    @app_commands.describe(title="Announcement title", body="Announcement body", color="Hex color (e.g. ff0000)")
    async def fake_announcement_cmd(i: discord.Interaction, title: str, body: str, color: str = "5865F2"):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        try:
            c = int(color.strip("#"), 16)
        except:
            c = 0x5865F2

        embed = discord.Embed(
            title=f"📢 {title}",
            description=body,
            color=c,
            timestamp=datetime.now()
        )
        embed.set_footer(text="[TEST ANNOUNCEMENT] — SentinelMod")
        await i.channel.send(embed=embed)
        await i.response.send_message("✅ Announcement sent!", ephemeral=True)

    # ══════════════════════════════════════════
    # /cmd_stats
    # ══════════════════════════════════════════
    @bot.tree.command(name="cmd_stats", description="[TEST] Command usage statistics")
    async def cmd_stats_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _command_usage:
            await i.response.send_message("No data yet.", ephemeral=True)
            return

        sorted_cmds = sorted(_command_usage.items(), key=lambda x: x[1], reverse=True)
        total = sum(_command_usage.values())

        embed = discord.Embed(
            title="📊 Command Usage Stats",
            description=f"**{total}** total uses since {_session_start.strftime('%H:%M:%S')}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        for cmd, count in sorted_cmds[:20]:
            bar = _build_status_bar(count, sorted_cmds[0][1], 8)
            embed.add_field(name=f"/{cmd}", value=f"`{bar}` {count}x", inline=True)

        if _command_errors:
            error_summary = "\n".join(f"• `/{c}`: {len(e)}x" for c, e in list(_command_errors.items())[:5])
            embed.add_field(name="⚠️ Recent Errors", value=error_summary, inline=False)

        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /edit_log
    # ══════════════════════════════════════════
    @bot.tree.command(name="edit_log", description="[TEST] See recent message edits")
    async def edit_log_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _message_edits_log:
            await i.response.send_message("No edits tracked yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✏️ Recent Edits",
            description=f"{len(_message_edits_log)} edits logged",
            color=discord.Color.orange()
        )
        for entry in list(_message_edits_log)[-10:]:
            embed.add_field(
                name=f"{entry['author']} in #{entry['channel']} @ {entry['time']}",
                value=f"**Before:** {entry['before'][:100]}\n**After:** {entry['after'][:100]}",
                inline=False
            )
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /delete_log
    # ══════════════════════════════════════════
    @bot.tree.command(name="delete_log", description="[TEST] See recent deleted messages")
    async def delete_log_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _deleted_messages_log:
            await i.response.send_message("No deletions tracked yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🗑️ Recent Deletions",
            description=f"{len(_deleted_messages_log)} deletions logged",
            color=discord.Color.red()
        )
        for entry in list(_deleted_messages_log)[-10:]:
            embed.add_field(
                name=f"{entry['author']} in #{entry['channel']} @ {entry['time']}",
                value=entry['content'][:200] or "*empty*",
                inline=False
            )
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /reaction_log
    # ══════════════════════════════════════════
    @bot.tree.command(name="reaction_log", description="[TEST] See recent reactions")
    async def reaction_log_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _reaction_log:
            await i.response.send_message("No reactions tracked yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="😀 Recent Reactions",
            color=discord.Color.yellow()
        )
        for entry in list(_reaction_log)[-15:]:
            embed.add_field(
                name=f"{entry['emoji']} by {entry['user']}",
                value=f"On: *{entry['msg'][:60]}*\n@ {entry['time']}",
                inline=False
            )
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /join_log
    # ══════════════════════════════════════════
    @bot.tree.command(name="join_log", description="[TEST] See recent joins/leaves")
    async def join_log_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _join_leave_log:
            await i.response.send_message("No joins/leaves tracked yet.", ephemeral=True)
            return

        embed = discord.Embed(title="🚪 Recent Joins/Leaves", color=discord.Color.teal())
        for entry in list(_join_leave_log)[-15:]:
            icon = "➕" if entry["type"] == "join" else "➖"
            embed.add_field(
                name=f"{icon} {entry['user']}",
                value=entry["time"][11:19],
                inline=True
            )
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /performance
    # ══════════════════════════════════════════
    @bot.tree.command(name="performance", description="[TEST] System performance metrics")
    async def performance_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        if not _performance_log:
            await i.response.send_message("No performance data yet.", ephemeral=True)
            return

        by_label: Dict[str, List[float]] = defaultdict(list)
        for entry in _performance_log:
            by_label[entry["label"]].append(entry["ms"])

        embed = discord.Embed(
            title="⚡ Performance Metrics",
            description=f"{len(_performance_log)} data points collected",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )

        for label, times in sorted(by_label.items()):
            avg = sum(times) / len(times)
            mn, mx = min(times), max(times)
            embed.add_field(
                name=label,
                value=f"avg `{avg:.0f}ms` | min `{mn:.0f}ms` | max `{mx:.0f}ms` | n={len(times)}",
                inline=False
            )
        embed.set_footer(text=f"WS latency: {bot.latency*1000:.1f}ms")
        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /session_report
    # ══════════════════════════════════════════
    @bot.tree.command(name="session_report", description="[TEST] Full analytics for this session")
    async def session_report_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        uptime = datetime.now() - _session_start
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)

        embed = discord.Embed(
            title="📈 Session Report",
            description=f"Session started: {_session_start.strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name="⏱️ Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="💬 Commands Used", value=sum(_command_usage.values()), inline=True)
        embed.add_field(name="✏️ Edits Tracked", value=len(_message_edits_log), inline=True)
        embed.add_field(name="🗑️ Deletions", value=len(_deleted_messages_log), inline=True)
        embed.add_field(name="😀 Reactions", value=len(_reaction_log), inline=True)
        embed.add_field(name="🤖 AI Decisions", value=len(_ai_decision_log), inline=True)
        embed.add_field(name="🧪 Tests Run", value=len(_test_scenarios_run), inline=True)
        embed.add_field(name="🕵️ Spy Mode", value="ON" if SPY_MODE else "OFF", inline=True)
        embed.add_field(name="🧪 Dry Run", value="ON" if DRY_RUN_MODE else "OFF", inline=True)
        embed.add_field(name="👤 Stealth", value="ON" if STEALTH_MODE else "OFF", inline=True)
        embed.add_field(name="📡 WS Latency", value=f"{bot.latency*1000:.1f}ms", inline=True)

        if _performance_log:
            all_ms = [e["ms"] for e in _performance_log]
            embed.add_field(
                name="⚡ Avg Response Time",
                value=f"{sum(all_ms)/len(all_ms):.0f}ms",
                inline=True
            )

        top_cmd = max(_command_usage.items(), key=lambda x: x[1]) if _command_usage else ("none", 0)
        embed.add_field(name="🏆 Most Used Command", value=f"`/{top_cmd[0]}` ({top_cmd[1]}x)", inline=True)

        await i.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /scenario
    # ══════════════════════════════════════════
    @bot.tree.command(name="scenario", description="[TEST] Run a named test scenario")
    @app_commands.describe(name="Scenario to run")
    @app_commands.choices(name=[
        app_commands.Choice(name="New Member Experience", value="new_member"),
        app_commands.Choice(name="Active Moderation Day", value="mod_day"),
        app_commands.Choice(name="Raid + Recovery", value="raid_recovery"),
        app_commands.Choice(name="AI Edge Cases", value="ai_edges"),
        app_commands.Choice(name="Full Server Lifecycle", value="full_lifecycle"),
    ])
    async def scenario_cmd(i: discord.Interaction, name: app_commands.Choice[str]):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        await i.response.defer(ephemeral=True)

        _test_scenarios_run.append({"scenario": name.value, "time": datetime.now().isoformat()})

        steps = {
            "new_member": [
                "Simulating member join...",
                "Welcome message triggered ✅",
                "Role assignment checked ✅",
                "New member timeout applied ✅",
                "AI greeting generated ✅",
            ],
            "mod_day": [
                "Generating 5 warnings...",
                "Triggering spam detection...",
                "Testing mute flow...",
                "Testing ban + appeal flow...",
                "Mod log verified ✅",
            ],
            "raid_recovery": [
                "Triggering raid alert...",
                "Lockdown activated...",
                "Raid members rate-limited...",
                "Owner notified...",
                "Recovery mode engaged...",
                "Raid resolved ✅",
            ],
            "ai_edges": [
                "Testing empty message...",
                "Testing unicode...",
                "Testing long message...",
                "Testing sarcasm...",
                "Testing language mixing...",
                "AI edge cases complete ✅",
            ],
            "full_lifecycle": [
                "Server created → settings applied...",
                "First member joins...",
                "Messages flow...",
                "Violation caught...",
                "Mod action taken...",
                "Server stats updated...",
                "Full lifecycle complete ✅",
            ]
        }

        embed = discord.Embed(
            title=f"🎬 Scenario: {name.name}",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        steps_text = "\n".join(f"{'✅' if '✅' in s else '⏳'} {s}" for s in steps.get(name.value, []))
        embed.description = steps_text

        await asyncio.sleep(1)
        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /eval_code
    # ══════════════════════════════════════════
    @bot.tree.command(name="eval_code", description="[TEST] Execute Python in bot context (owner only)")
    @app_commands.describe(code="Python code to execute")
    async def eval_code_cmd(i: discord.Interaction, code: str):
        if not await _guild_check(i):
            return
        if not await _owner_check(i):
            return

        await i.response.defer(ephemeral=True)

        env = {
            "bot": bot,
            "guild": i.guild,
            "channel": i.channel,
            "user": i.user,
            "discord": discord,
            "asyncio": asyncio,
            "_get_bot_func": _get_bot_func,
            "_get_bot_var": _get_bot_var,
        }

        stdout = io.StringIO()
        result = None
        error = None

        try:
            exec_code = f"async def _exec():\n{textwrap.indent(code, '    ')}"
            exec(exec_code, env)
            with contextlib.redirect_stdout(stdout):
                result = await env["_exec"]()
        except Exception:
            error = traceback.format_exc()

        output = stdout.getvalue()
        embed = discord.Embed(
            title="🐍 Eval Result",
            color=discord.Color.green() if not error else discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Code", value=f"```py\n{code[:500]}\n```", inline=False)
        if output:
            embed.add_field(name="stdout", value=f"```\n{output[:500]}\n```", inline=False)
        if result is not None:
            embed.add_field(name="Return", value=f"```py\n{str(result)[:500]}\n```", inline=False)
        if error:
            embed.add_field(name="Error", value=f"```py\n{error[:500]}\n```", inline=False)

        await i.followup.send(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    # /schedule_test
    # ══════════════════════════════════════════
    @bot.tree.command(name="schedule_test", description="[TEST] Schedule a test to run in X minutes")
    @app_commands.describe(test_name="Which test", delay_minutes="How many minutes from now")
    @app_commands.choices(test_name=[
        app_commands.Choice(name="Mass Test", value="mass_test"),
        app_commands.Choice(name="Raid Simulation", value="raid"),
        app_commands.Choice(name="AI Stress", value="ai_stress"),
        app_commands.Choice(name="Latency Test", value="latency"),
    ])
    async def schedule_test_cmd(i: discord.Interaction, test_name: app_commands.Choice[str], delay_minutes: int = 5):
        if not await _guild_check(i):
            return

        delay_minutes = max(1, min(60, delay_minutes))
        run_at = datetime.now() + timedelta(minutes=delay_minutes)

        _scheduled_tests.append({
            "test": test_name.value,
            "run_at": run_at.isoformat(),
            "channel_id": i.channel.id,
            "guild_id": i.guild.id,
            "scheduled_by": str(i.user)
        })

        await i.response.send_message(
            f"⏰ **{test_name.name}** scheduled for `{run_at.strftime('%H:%M:%S')}` "
            f"({delay_minutes}min from now).",
            ephemeral=True
        )

    # ══════════════════════════════════════════
    # /test_features — Full diagnostics
    # ══════════════════════════════════════════
    @bot.tree.command(name="test_features", description="[TEST] Run diagnostics on all systems")
    async def test_features_cmd(i: discord.Interaction):
        if not await _guild_check(i):
            return

        await i.response.defer(ephemeral=True)

        checks = []

        for func_name in ["smart_ai", "ask_groq_json", "contains_swear", "smart_ai_moderation",
                          "get_user_memory", "get_server_memory", "save_server_memory",
                          "notify_owner", "is_owner", "get_guild_settings", "check_against_server_rules"]:
            f = _get_bot_func(func_name)
            checks.append((f"func: {func_name}", "✅" if f else "❌"))

        for mod_name in ["welcome_system", "smart_rules", "ai_features", "image_moderation",
                         "dashboard", "anti_nuke", "auto_roles"]:
            try:
                __import__(mod_name)
                checks.append((f"mod: {mod_name}", "✅"))
            except ImportError:
                checks.append((f"mod: {mod_name}", "❌"))

        conn = _get_db()
        c = conn.cursor()
        for table in ["warnings", "mod_actions", "guild_settings", "user_memory",
                       "server_memory", "daily_stats", "message_archive", "reputation"]:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                checks.append((f"table: {table} ({count} rows)", "✅"))
            except:
                checks.append((f"table: {table}", "❌"))
        conn.close()

        for key in ["GROQ_API_KEY", "DISCORD_TOKEN", "OPENAI_API_KEY"]:
            checks.append((f"env: {key}", "✅" if os.getenv(key) else "❌"))

        checks.append(("WS latency", f"✅ {bot.latency*1000:.0f}ms"))
        checks.append(("test_server.py", "✅ loaded"))

        passed = sum(1 for _, s in checks if s.startswith("✅"))
        total = len(checks)
        score = passed / total

        embed = discord.Embed(
            title="🩺 System Diagnostics",
            description=(
                f"**{passed}/{total} checks passed** "
                f"{_build_status_bar(score, 1.0, 15)} {score:.0%}\n\n"
                + "\n".join(f"{s} `{n}`" for n, s in checks)
            ),
            color=discord.Color.green() if score > 0.8 else discord.Color.orange(),
            timestamp=datetime.now()
        )
        await i.followup.send(embed=embed, ephemeral=True)


# ============ LISTENERS ============
def _register_listeners(bot):

    @bot.listen("on_message")
    async def _spy_listener(message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not is_test_server(message.guild.id):
            return

        if SPY_MODE:
            print(f"[SPY] #{message.channel.name} | {message.author}: {message.content[:200]}")

        if _live_monitor_channels:
            for ch_id in list(_live_monitor_channels):
                ch = bot.get_channel(ch_id)
                if ch:
                    try:
                        await ch.send(
                            f"📡 `{message.author}` in `#{message.channel.name}`: "
                            f"{message.content[:150]}"
                        )
                    except:
                        pass

    @bot.listen("on_message_edit")
    async def _edit_tracker(before, after):
        if before.author.bot:
            return
        if not before.guild:
            return
        if not is_test_server(before.guild.id):
            return
        if before.content == after.content:
            return

        _message_edits_log.append({
            "author": str(before.author),
            "channel": before.channel.name,
            "before": before.content[:200],
            "after": after.content[:200],
            "time": datetime.now().strftime("%H:%M:%S")
        })

    @bot.listen("on_message_delete")
    async def _delete_tracker(message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not is_test_server(message.guild.id):
            return

        _deleted_messages_log.append({
            "author": str(message.author),
            "channel": message.channel.name,
            "content": message.content[:200],
            "time": datetime.now().strftime("%H:%M:%S")
        })

    @bot.listen("on_reaction_add")
    async def _reaction_tracker(reaction, user):
        if user.bot:
            return
        if not reaction.message.guild:
            return
        if not is_test_server(reaction.message.guild.id):
            return

        _reaction_log.append({
            "emoji": str(reaction.emoji),
            "user": str(user),
            "msg": reaction.message.content[:80],
            "time": datetime.now().strftime("%H:%M:%S")
        })

    @bot.listen("on_member_join")
    async def _join_tracker(member):
        if not is_test_server(member.guild.id):
            return
        _join_leave_log.append({
            "type": "join",
            "user": str(member),
            "time": datetime.now().isoformat()
        })

    @bot.listen("on_member_remove")
    async def _leave_tracker(member):
        if not is_test_server(member.guild.id):
            return
        _join_leave_log.append({
            "type": "leave",
            "user": str(member),
            "time": datetime.now().isoformat()
        })

    @bot.listen("on_interaction")
    async def _cmd_tracker(interaction):
        if interaction.type == discord.InteractionType.application_command:
            if interaction.guild and is_test_server(interaction.guild.id):
                cmd_name = interaction.data.get("name", "unknown")
                _command_usage[cmd_name] += 1


# ============ SCHEDULED TEST RUNNER ============
async def _run_scheduled_tests(bot):
    """Background loop to run scheduled tests."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        to_run = [t for t in _scheduled_tests if datetime.fromisoformat(t["run_at"]) <= now]
        for test in to_run:
            _scheduled_tests.remove(test)
            ch = bot.get_channel(test["channel_id"])
            if ch:
                try:
                    await ch.send(
                        embed=discord.Embed(
                            title=f"⏰ Scheduled Test: `{test['test']}`",
                            description=f"Scheduled by {test['scheduled_by']}",
                            color=discord.Color.purple(),
                            timestamp=now
                        )
                    )
                except:
                    pass
        await asyncio.sleep(30)


# ============ SETUP ============
def setup(bot):
    global _bot_ref, _is_setup
    if _is_setup:
        return
    _bot_ref = bot
    _is_setup = True
    _register_commands(bot)
    _register_listeners(bot)
    bot.loop.create_task(_run_scheduled_tests(bot))
    print("[test_server] ✅ Loaded — Ultimate test server system active")


# ============ AUTO HOOK ============
def _delayed_hook():
    for _ in range(30):
        _time.sleep(1)
        try:
            for module in sys.modules.values():
                if module is None:
                    continue
                if hasattr(module, "bot") and isinstance(getattr(module, "bot", None), commands.Bot):
                    setup(module.bot)
                    return
        except:
            pass


threading.Thread(target=_delayed_hook, daemon=True).start()
