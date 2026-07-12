# test_server.py
# ================================
# SentinelMod - Test Server Exclusive Features
# Auto-hooks into bot. Only works in the designated test server.
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
from datetime import datetime, timedelta
from collections import defaultdict

# ============ CONFIG ============
TEST_SERVER_ID = 1523813949978578994

_bot_ref = None
_is_setup = False

# State
SPY_MODE = False
DRY_RUN_MODE = False
_command_usage = defaultdict(int)
_message_edits_log = []


def is_test_server(guild_id) -> bool:
    try:
        return int(guild_id) == TEST_SERVER_ID
    except:
        return False


def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ============ HELPER: Get functions from bot.py safely ============
def _get_bot_func(name):
    """Get a function from bot.py at runtime."""
    import sys
    for mod_name, mod in sys.modules.items():
        if mod is None: continue
        if hasattr(mod, name) and hasattr(mod, "bot"):
            return getattr(mod, name)
    return None


def _get_bot_var(name):
    """Get a variable from bot.py at runtime."""
    import sys
    for mod_name, mod in sys.modules.items():
        if mod is None: continue
        if hasattr(mod, name) and hasattr(mod, "bot"):
            return getattr(mod, name)
    return None


# ============ SLASH COMMANDS ============
def _register_commands(bot):

    @bot.tree.command(name="beta_features", description="[TEST SERVER] View experimental features")
    async def beta_features_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 This command is exclusive to the test server!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🧪 Beta Features (Test Server Only)",
            description="Experimental commands only available in this server.",
            color=discord.Color.purple()
        )
        commands_list = [
            ("`/ai_debug`", "See what AI thinks about any message"),
            ("`/simulate_join`", "Simulate a member joining (test welcome)"),
            ("`/simulate_raid`", "Simulate a raid alert"),
            ("`/wipe_test`", "Wipe all bot data for this server"),
            ("`/force_ai`", "Force AI to respond as any personality"),
            ("`/spy_mode`", "Log every message the bot sees (console)"),
            ("`/mass_test`", "Auto-send test messages"),
            ("`/inject_memory`", "Manually add fake bot memories"),
            ("`/time_travel`", "View activity from a specific date"),
            ("`/dry_run`", "Test mode - no actual moderation"),
            ("`/fake_user`", "Bot pretends to be a fake user"),
            ("`/cmd_stats`", "See which commands used most"),
            ("`/edit_log`", "See recent message edits"),
            ("`/test_features`", "Run diagnostics on all systems"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        
        embed.set_footer(text="⚠️ Test server only - use with caution")
        await i.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="ai_debug", description="[TEST SERVER] See what AI thinks of a message")
    @app_commands.describe(message="The message text to analyze")
    async def ai_debug_cmd(i: discord.Interaction, message: str):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        await i.response.defer()
        
        embed = discord.Embed(
            title="🧠 AI Debug Analysis",
            description=f"**Message:** ```{message[:400]}```",
            color=discord.Color.blue()
        )
        
        # Get functions from bot.py
        contains_swear = _get_bot_func("contains_swear")
        smart_ai_moderation = _get_bot_func("smart_ai_moderation")
        get_user_memory = _get_bot_func("get_user_memory")
        check_against_server_rules = _get_bot_func("check_against_server_rules")
        server_rules_cache = _get_bot_var("server_rules_cache")
        HARD_DELETE_PATTERNS = _get_bot_var("HARD_DELETE_PATTERNS")
        SOFT_VIOLATION_PATTERNS = _get_bot_var("SOFT_VIOLATION_PATTERNS")
        
        # Swear check
        if contains_swear:
            try:
                has_swear, matched = contains_swear(message)
                embed.add_field(
                    name="🤬 Swear Filter",
                    value=f"{'❌ FLAGGED' if has_swear else '✅ Clean'}\n{f'Matched: `{matched}`' if matched else ''}",
                    inline=True
                )
            except: pass
        
        # Pattern checks
        if HARD_DELETE_PATTERNS:
            hard_hits = [reason for pattern, reason, _ in HARD_DELETE_PATTERNS if re.search(pattern, message)]
            embed.add_field(
                name="🔴 Hard Patterns",
                value=", ".join(hard_hits) if hard_hits else "✅ None",
                inline=True
            )
        
        if SOFT_VIOLATION_PATTERNS:
            soft_hits = [reason for pattern, reason, _ in SOFT_VIOLATION_PATTERNS if re.search(pattern, message)]
            embed.add_field(
                name="🟠 Soft Patterns",
                value=", ".join(soft_hits) if soft_hits else "✅ None",
                inline=True
            )
        
        # AI moderation
        if smart_ai_moderation and get_user_memory:
            try:
                user_mem = get_user_memory(i.user.id, i.guild.id)
                ai_result = await smart_ai_moderation(
                    message, i.user.display_name, i.channel.name, [], user_mem, "general", ""
                )
                embed.add_field(
                    name="🤖 AI Judgment",
                    value=f"**Action:** {ai_result.get('action')}\n**Severity:** {ai_result.get('severity')}\n**Confidence:** {ai_result.get('confidence', 0):.0%}\n**Reason:** {ai_result.get('reason', 'N/A')}",
                    inline=False
                )
            except Exception as e:
                embed.add_field(name="🤖 AI Error", value=str(e)[:200], inline=False)
        
        # Rules check
        if check_against_server_rules and server_rules_cache:
            rules = server_rules_cache.get(str(i.guild.id), "")
            if rules:
                try:
                    rules_check = await check_against_server_rules(message, i.user.display_name, i.guild)
                    embed.add_field(
                        name="📋 Rules Check",
                        value=f"**Violates:** {'❌ YES' if rules_check.get('violates') else '✅ NO'}\n**Rule:** {rules_check.get('rule', 'N/A')}\n**Reason:** {rules_check.get('reason', 'N/A')}",
                        inline=False
                    )
                except: pass
        
        embed.set_footer(text="This is exactly what the AI sees when moderating")
        await i.followup.send(embed=embed)


    @bot.tree.command(name="simulate_join", description="[TEST SERVER] Simulate a member joining")
    async def simulate_join_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        try:
            import welcome_system
            await welcome_system.handle_welcome(i.user)
            await i.followup.send("✅ Simulated your join! Check the welcome channel.", ephemeral=True)
        except ImportError:
            await i.followup.send("❌ welcome_system.py not found", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Error: {e}", ephemeral=True)


    @bot.tree.command(name="simulate_raid", description="[TEST SERVER] Simulate a raid alert")
    async def simulate_raid_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        raid_mode_active = _get_bot_var("raid_mode_active")
        notify_owner = _get_bot_func("notify_owner")
        get_guild_settings = _get_bot_func("get_guild_settings")
        
        if raid_mode_active is not None:
            raid_mode_active[i.guild.id] = True
        
        if notify_owner:
            await notify_owner("RAID", f"🚨 SIMULATED RAID in **{i.guild.name}**!", guild=i.guild, urgent=True)
        
        if get_guild_settings:
            s = get_guild_settings(i.guild.id)
            ch = discord.utils.get(i.guild.text_channels, name=s.get("raid_channel", "sentinel-raid-alerts"))
            if ch:
                try:
                    await ch.send(embed=discord.Embed(
                        title="🚨 SIMULATED RAID (Test)",
                        description="This is a fake raid alert for testing purposes.",
                        color=discord.Color.red()
                    ))
                except: pass
        
        async def reset():
            await asyncio.sleep(30)
            if raid_mode_active is not None:
                raid_mode_active[i.guild.id] = False
        asyncio.create_task(reset())
        
        await i.response.send_message("✅ Simulated raid! Will auto-reset in 30s.", ephemeral=True)


    @bot.tree.command(name="wipe_test", description="[TEST SERVER] Wipe all bot data for this server")
    async def wipe_test_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        is_owner = _get_bot_func("is_owner")
        if is_owner and not is_owner(i.user.id):
            await i.response.send_message("🚫 Owner only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        conn = _get_db()
        c = conn.cursor()
        tables = [
            "warnings", "mod_actions", "message_archive", "conversation_history",
            "user_memory", "server_memory", "afk_users", "message_stats",
            "reminders", "reputation", "daily_stats", "custom_commands",
            "word_filters", "trusted_users", "appeals", "user_personalities"
        ]
        counts = {}
        for table in tables:
            try:
                c.execute(f"DELETE FROM {table} WHERE guild_id=?", (str(i.guild.id),))
                counts[table] = c.rowcount
            except: pass
        conn.commit()
        conn.close()
        
        # Clear bot.py caches
        server_rules_cache = _get_bot_var("server_rules_cache")
        live_context = _get_bot_var("live_context")
        recent_actions = _get_bot_var("recent_actions")
        
        if server_rules_cache:
            server_rules_cache.pop(str(i.guild.id), None)
        if recent_actions:
            recent_actions.pop(i.guild.id, None)
        
        total = sum(counts.values())
        cleaned = "\n".join(f"- `{t}`: {c}" for t, c in counts.items() if c > 0)
        
        embed = discord.Embed(
            title="🧹 Test Server Wiped",
            description=f"**Total records deleted: {total}**\n\n{cleaned or 'Nothing to clean.'}",
            color=discord.Color.orange()
        )
        await i.followup.send(embed=embed, ephemeral=True)


    @bot.tree.command(name="force_ai", description="[TEST SERVER] Force AI to respond as any personality")
    @app_commands.describe(personality="Which personality", prompt="What to ask")
    async def force_ai_cmd(i: discord.Interaction, personality: str, prompt: str):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        PERSONALITIES = _get_bot_var("PERSONALITIES")
        smart_ai = _get_bot_func("smart_ai")
        
        if not PERSONALITIES or not smart_ai:
            await i.response.send_message("❌ Bot functions not available", ephemeral=True)
            return
        
        if personality not in PERSONALITIES:
            available = ", ".join(list(PERSONALITIES.keys())[:15])
            await i.response.send_message(f"Unknown personality.\nTry: {available}", ephemeral=True)
            return
        
        await i.response.defer()
        response = await smart_ai(prompt, PERSONALITIES[personality], max_tokens=500)
        
        embed = discord.Embed(
            title=f"🎭 AI as: {personality}",
            description=response[:2000] if response else "*No response*",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Prompt: {prompt[:100]}")
        await i.followup.send(embed=embed)


    @bot.tree.command(name="spy_mode", description="[TEST SERVER] Log every message to console")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def spy_mode_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        is_owner = _get_bot_func("is_owner")
        if is_owner and not is_owner(i.user.id):
            await i.response.send_message("🚫 Owner only!", ephemeral=True)
            return
        
        global SPY_MODE
        SPY_MODE = (state.value == "on")
        await i.response.send_message(
            f"🕵️ Spy mode **{state.name}**\n"
            f"{'All messages will be logged to console.' if SPY_MODE else 'Message logging disabled.'}",
            ephemeral=True
        )


    @bot.tree.command(name="dry_run", description="[TEST SERVER] Test mode - no actual moderation actions")
    @app_commands.choices(state=[
        app_commands.Choice(name="ON", value="on"),
        app_commands.Choice(name="OFF", value="off")
    ])
    async def dry_run_cmd(i: discord.Interaction, state: app_commands.Choice[str]):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        global DRY_RUN_MODE
        DRY_RUN_MODE = (state.value == "on")
        await i.response.send_message(
            f"🧪 Dry Run **{state.name}**\n"
            f"{'No actual bans/mutes/deletes will happen!' if DRY_RUN_MODE else 'Normal moderation resumed.'}",
            ephemeral=True
        )


    @bot.tree.command(name="mass_test", description="[TEST SERVER] Send test messages to check AI moderation")
    async def mass_test_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        is_owner = _get_bot_func("is_owner")
        if is_owner and not is_owner(i.user.id):
            await i.response.send_message("🚫 Owner only!", ephemeral=True)
            return
        
        await i.response.send_message("🧪 Starting mass test in 3 seconds...", ephemeral=True)
        await asyncio.sleep(3)
        
        test_messages = [
            ("hey what's up", "clean chat"),
            ("this is amazing!", "clean positive"),
            ("you're such an idiot honestly", "mild insult"),
            ("check out discord.gg/somespam", "invite link"),
            ("AAAAAAAAAAAAAA THIS IS SO LOUD", "caps abuse"),
            ("yo yo yo yo yo yo yo yo", "spam"),
            ("my number is 555-123-4567", "phone number"),
            ("email me at test@example.com", "email"),
            ("🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉", "emoji spam"),
            ("gg well played", "clean gaming"),
        ]
        
        for msg, desc in test_messages:
            try:
                await i.channel.send(f"**[TEST: {desc}]** {msg}")
                await asyncio.sleep(2)
            except: pass
        
        try:
            await i.followup.send("✅ Test complete! Check what got caught!", ephemeral=True)
        except: pass


    @bot.tree.command(name="inject_memory", description="[TEST SERVER] Add fake data to bot memory")
    @app_commands.describe(memory_type="What to inject", data="The data to add")
    @app_commands.choices(memory_type=[
        app_commands.Choice(name="Inside Joke", value="joke"),
        app_commands.Choice(name="Popular Topic", value="topic"),
        app_commands.Choice(name="Common Phrase", value="phrase"),
        app_commands.Choice(name="Server Mood", value="mood"),
    ])
    async def inject_memory_cmd(i: discord.Interaction, memory_type: app_commands.Choice[str], data: str):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        get_server_memory = _get_bot_func("get_server_memory")
        save_server_memory = _get_bot_func("save_server_memory")
        
        if not get_server_memory or not save_server_memory:
            await i.response.send_message("❌ Memory system not available", ephemeral=True)
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
        
        save_server_memory(i.guild.id, sm)
        await i.response.send_message(f"✅ Injected **{memory_type.name}**: `{data}`", ephemeral=True)


    @bot.tree.command(name="time_travel", description="[TEST SERVER] View activity from a specific date")
    @app_commands.describe(date="Date in YYYY-MM-DD format")
    async def time_travel_cmd(i: discord.Interaction, date: str):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        try:
            datetime.fromisoformat(date)
        except:
            await i.response.send_message("Invalid date. Use YYYY-MM-DD format.", ephemeral=True)
            return
        
        await i.response.defer()
        
        conn = _get_db()
        c = conn.cursor()
        
        c.execute("SELECT * FROM daily_stats WHERE guild_id=? AND date=?", (str(i.guild.id), date))
        stats = c.fetchone()
        
        c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND timestamp LIKE ?",
                  (str(i.guild.id), f"{date}%"))
        warns = c.fetchone()[0]
        
        c.execute("""SELECT action, COUNT(*) as cnt FROM mod_actions 
                     WHERE guild_id=? AND timestamp LIKE ? GROUP BY action""",
                  (str(i.guild.id), f"{date}%"))
        actions = c.fetchall()
        
        c.execute("SELECT COUNT(*) FROM message_archive WHERE guild_id=? AND timestamp LIKE ?",
                  (str(i.guild.id), f"{date}%"))
        archived = c.fetchone()[0]
        
        conn.close()
        
        embed = discord.Embed(
            title=f"⏰ Time Travel: {date}",
            color=discord.Color.gold()
        )
        
        if stats:
            embed.add_field(name="💬 Messages", value=f"{stats['messages']:,}", inline=True)
            embed.add_field(name="➕ Joins", value=stats["joins"], inline=True)
            embed.add_field(name="➖ Leaves", value=stats["leaves"], inline=True)
            embed.add_field(name="🛡️ Mod Actions", value=stats["mod_actions"], inline=True)
        else:
            embed.description = "*No daily stats recorded for this date.*"
        
        embed.add_field(name="⚠️ Warnings Given", value=warns, inline=True)
        embed.add_field(name="📚 Archived", value=archived, inline=True)
        
        if actions:
            action_text = "\n".join(f"- {a['action']}: {a['cnt']}" for a in actions)
            embed.add_field(name="Action Breakdown", value=action_text, inline=False)
        
        await i.followup.send(embed=embed)


    @bot.tree.command(name="fake_user", description="[TEST SERVER] Bot pretends to be a fake user")
    @app_commands.describe(username="Fake username", message="What they say")
    async def fake_user_cmd(i: discord.Interaction, username: str, message: str):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        is_owner = _get_bot_func("is_owner")
        if is_owner and not is_owner(i.user.id):
            await i.response.send_message("🚫 Owner only!", ephemeral=True)
            return
        
        # Use a webhook to fake the user
        try:
            webhooks = await i.channel.webhooks()
            wh = discord.utils.get(webhooks, name="SentinelTest")
            if not wh:
                wh = await i.channel.create_webhook(name="SentinelTest")
            
            await wh.send(
                content=message,
                username=f"[FAKE] {username}",
                avatar_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            await i.response.send_message("✅ Fake message sent!", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"❌ Error: {e}", ephemeral=True)


    @bot.tree.command(name="cmd_stats", description="[TEST SERVER] See command usage stats")
    async def cmd_stats_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        if not _command_usage:
            await i.response.send_message("No commands tracked yet.", ephemeral=True)
            return
        
        sorted_cmds = sorted(_command_usage.items(), key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="📊 Command Usage Stats",
            description="Since bot last started",
            color=discord.Color.blue()
        )
        for cmd, count in sorted_cmds[:20]:
            embed.add_field(name=cmd, value=f"Used {count}x", inline=True)
        
        embed.set_footer(text=f"Total commands: {sum(_command_usage.values())}")
        await i.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="edit_log", description="[TEST SERVER] See recent message edits")
    async def edit_log_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        if not _message_edits_log:
            await i.response.send_message("No edits tracked yet.", ephemeral=True)
            return
        
        embed = discord.Embed(title="✏️ Recent Message Edits", color=discord.Color.orange())
        for entry in list(_message_edits_log)[-10:]:
            embed.add_field(
                name=f"{entry['author']} in #{entry['channel']}",
                value=f"**Before:** {entry['before'][:100]}\n**After:** {entry['after'][:100]}\n*{entry['time']}*",
                inline=False
            )
        await i.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="test_features", description="[TEST SERVER] Run diagnostics on all systems")
    async def test_features_cmd(i: discord.Interaction):
        if not is_test_server(i.guild.id):
            await i.response.send_message("🚫 Test server only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        
        checks = []
        
        # Check bot.py functions
        for func_name in ["smart_ai", "ask_groq_json", "contains_swear", "smart_ai_moderation",
                          "get_user_memory", "notify_owner", "is_owner", "get_guild_settings"]:
            f = _get_bot_func(func_name)
            checks.append((func_name, "✅" if f else "❌"))
        
        # Check modules
        modules_to_check = ["welcome_system", "smart_rules", "ai_features", "image_moderation", "dashboard"]
        for mod_name in modules_to_check:
            try:
                __import__(mod_name)
                checks.append((f"module: {mod_name}", "✅"))
            except ImportError:
                checks.append((f"module: {mod_name}", "❌"))
        
        # Check DB tables
        conn = _get_db()
        c = conn.cursor()
        for table in ["warnings", "mod_actions", "guild_settings", "user_memory", "server_memory"]:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                c.fetchone()
                checks.append((f"table: {table}", "✅"))
            except:
                checks.append((f"table: {table}", "❌"))
        conn.close()
        
        # Check API keys
        checks.append(("GROQ_API_KEY", "✅" if os.getenv("GROQ_API_KEY") else "❌"))
        checks.append(("DISCORD_TOKEN", "✅" if os.getenv("DISCORD_TOKEN") else "❌"))
        
        embed = discord.Embed(
            title="🩺 System Diagnostics",
            color=discord.Color.green()
        )
        
        passed = sum(1 for _, status in checks if status == "✅")
        total = len(checks)
        
        embed.description = f"**{passed}/{total} checks passed**\n\n"
        embed.description += "\n".join(f"{status} `{name}`" for name, status in checks)
        
        await i.followup.send(embed=embed, ephemeral=True)


# ============ LISTENERS ============
def _register_listeners(bot):

    @bot.listen("on_message")
    async def _spy_listener(message):
        if message.author.bot: return
        if not message.guild: return
        if not is_test_server(message.guild.id): return
        
        if SPY_MODE:
            print(f"[SPY] #{message.channel.name} | {message.author}: {message.content[:200]}")

    @bot.listen("on_message_edit")
    async def _edit_tracker(before, after):
        if before.author.bot: return
        if not before.guild: return
        if not is_test_server(before.guild.id): return
        if before.content == after.content: return
        
        _message_edits_log.append({
            "author": str(before.author),
            "channel": before.channel.name,
            "before": before.content[:200],
            "after": after.content[:200],
            "time": datetime.now().strftime("%H:%M:%S")
        })
        # Keep only last 50
        if len(_message_edits_log) > 50:
            _message_edits_log.pop(0)

    @bot.listen("on_interaction")
    async def _cmd_tracker(interaction):
        if interaction.type == discord.InteractionType.application_command:
            if interaction.guild and is_test_server(interaction.guild.id):
                cmd_name = interaction.data.get("name", "unknown")
                _command_usage[cmd_name] += 1


# ============ SETUP ============
def setup(bot):
    global _bot_ref, _is_setup
    if _is_setup:
        return
    _bot_ref = bot
    _is_setup = True
    _register_commands(bot)
    _register_listeners(bot)
    print("[test_server] ✅ Loaded - test server features active")


# ============ AUTO HOOK ============
def _delayed_hook():
    import sys
    for _ in range(30):
        _time.sleep(1)
        try:
            for module in sys.modules.values():
                if module is None: continue
                if hasattr(module, "bot") and isinstance(getattr(module, "bot", None), commands.Bot):
                    setup(module.bot)
                    return
        except: pass

threading.Thread(target=_delayed_hook, daemon=True).start()
