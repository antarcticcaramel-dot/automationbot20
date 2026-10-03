# command_executor.py
# ================================
# Executes 50+ parsed natural-language commands
# ================================

import discord
import random
import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from components_v2 import (
    _embed, HelpView, WarningsView, PollView, SettingsView,
    build_profile_embed, build_server_health_embed, build_mod_action_container,
)
from utils import parse_duration, sanitize_bot_response
from core_config import BOT_IDENTITY, PERSONALITIES


async def execute(
    parsed: dict,
    message: discord.Message,
    guild: discord.Guild,
    author: discord.Member,
    bot,
    db,
    ai,
    log_recent_action,
    notify_owner,
    alert_mods,
    cleanup_and_leave,
    setup_server,
    read_server_rules,
    find_rules_channel,
    server_rules_cache: dict,
    voice_sessions: dict,
    licensed_servers: set,
    revoked_servers: set,
    schedule_unpunish,
    is_owner,
    trivia_sessions: dict,
) -> Optional[Union[str, discord.ui.View, discord.Embed]]:
    """Execute a parsed command. Returns response text, View, Embed, or None."""

    cmd = parsed.get("command", "")
    target_member: Optional[discord.Member] = parsed.get("target_member")
    target_id = parsed.get("target_id")
    reason = parsed.get("reason", "") or "No reason provided"
    duration_str = parsed.get("duration", "")

    # Resolve target if needed
    if target_id and not target_member:
        tid = int(target_id) if str(target_id).isdigit() else 0
        target_member = guild.get_member(tid)

    # ------------------------------------------------------------------
    # MODERATION COMMANDS
    # ------------------------------------------------------------------

    if cmd == "ban_user":
        if not target_member and not target_id:
            return "❌ Please specify a user to ban."
        target = target_member
        if not target:
            try:
                user = await bot.fetch_user(int(target_id))
                await guild.ban(user, reason=reason, delete_message_days=1)
                log_recent_action(guild.id, "BAN", str(user), reason)
                if duration_str:
                    secs = parse_duration(duration_str)
                    if secs:
                        when = (datetime.now() + timedelta(seconds=secs)).isoformat()
                        await schedule_unpunish(guild.id, user.id, "unban", when)
                        return f"🔨 Banned **{user}** for {duration_str}. Reason: {reason}"
                return f"🔨 Banned **{user}**. Reason: {reason}"
            except Exception as e:
                return f"❌ Ban failed: {e}"

        if target.guild_permissions.administrator:
            return "❌ Cannot ban an administrator."
        try:
            await target.ban(reason=reason, delete_message_days=1)
            log_recent_action(guild.id, "BAN", target.display_name, reason)
            if duration_str:
                secs = parse_duration(duration_str)
                if secs:
                    when = (datetime.now() + timedelta(seconds=secs)).isoformat()
                    await schedule_unpunish(guild.id, target.id, "unban", when)
                    return f"🔨 Temp-banned **{target.display_name}** for {duration_str}. Reason: {reason}"
            await alert_mods(guild, build_mod_action_container("BAN", target, reason))
            return f"🔨 Banned **{target.display_name}**. Reason: {reason}"
        except discord.Forbidden:
            return "❌ I don't have permission to ban that user."
        except Exception as e:
            return f"❌ Ban failed: {e}"

    elif cmd == "kick_user":
        if not target_member:
            return "❌ Please specify a user to kick."
        if target_member.guild_permissions.administrator:
            return "❌ Cannot kick an administrator."
        try:
            await target_member.kick(reason=reason)
            log_recent_action(guild.id, "KICK", target_member.display_name, reason)
            await alert_mods(guild, build_mod_action_container("KICK", target_member, reason))
            return f"👢 Kicked **{target_member.display_name}**. Reason: {reason}"
        except discord.Forbidden:
            return "❌ I don't have permission to kick that user."
        except Exception as e:
            return f"❌ Kick failed: {e}"

    elif cmd in ("mute_user", "timeout_user"):
        if not target_member:
            return "❌ Please specify a user to mute."
        secs = parse_duration(duration_str) if duration_str else 600
        try:
            until = datetime.now(timezone.utc) + timedelta(seconds=secs)
            await target_member.timeout(until, reason=reason)
            log_recent_action(guild.id, "MUTE", target_member.display_name, reason)
            human_dur = duration_str or "10m"
            if secs:
                when = (datetime.now() + timedelta(seconds=secs)).isoformat()
                await schedule_unpunish(guild.id, target_member.id, "unmute", when)
            return f"🔇 Muted **{target_member.display_name}** for {human_dur}. Reason: {reason}"
        except discord.Forbidden:
            return "❌ I don't have permission to timeout that user."
        except Exception as e:
            return f"❌ Mute failed: {e}"

    elif cmd == "unmute_user":
        if not target_member:
            return "❌ Please specify a user to unmute."
        try:
            await target_member.timeout(None, reason=reason)
            log_recent_action(guild.id, "UNMUTE", target_member.display_name, reason)
            return f"🔊 Unmuted **{target_member.display_name}**."
        except Exception as e:
            return f"❌ Unmute failed: {e}"

    elif cmd == "warn_user":
        if not target_member:
            return "❌ Please specify a user to warn."
        wc, wid = db.add_warning(target_member.id, guild.id, reason, "medium",
                                  moderator=str(author.id))
        log_recent_action(guild.id, "WARN", target_member.display_name,
                          f"{reason} (#{wc})")
        s = db.get_guild_settings(guild.id)
        response = f"⚠️ Warned **{target_member.display_name}** — #{wc}. Reason: {reason}"
        if wc >= s.get("warn_threshold_ban", 8):
            try:
                await target_member.ban(reason=f"Auto-ban: {wc} warnings")
                response += f"\n🔨 **AUTO-BANNED** ({wc} warnings reached threshold)"
            except:
                response += f"\n⚠️ Threshold reached but ban failed."
        elif wc >= s.get("warn_threshold_kick", 5):
            try:
                await target_member.kick(reason=f"Auto-kick: {wc} warnings")
                response += f"\n👢 **AUTO-KICKED** ({wc} warnings reached threshold)"
            except:
                pass
        await alert_mods(guild, build_mod_action_container("WARN", target_member, reason, wc))
        return response

    elif cmd == "check_warnings":
        if not target_member and target_id:
            target_member = guild.get_member(int(target_id)) if str(target_id).isdigit() else None
        if not target_member:
            return "❌ Specify a user."
        warns = db.get_warnings(target_member.id, guild.id)
        if not warns:
            return f"✅ **{target_member.display_name}** has no warnings."
        view = WarningsView(warns, target_member.display_name)
        embed = view.build_embed()
        return embed  # Caller will handle sending

    elif cmd == "clear_warnings":
        if not target_member and target_id:
            target_member = guild.get_member(int(target_id)) if str(target_id).isdigit() else None
        if not target_member:
            return "❌ Specify a user."
        count = db.clear_warnings(target_member.id, guild.id)
        log_recent_action(guild.id, "CLEAR_WARNS", target_member.display_name,
                          f"Cleared {count} warnings")
        return f"✅ Cleared **{count}** warnings for **{target_member.display_name}**."

    elif cmd == "purge":
        count = int(parsed.get("count", 10))
        count = min(count, 500)
        try:
            deleted = await message.channel.purge(limit=count + 1)
            log_recent_action(guild.id, "PURGE", message.channel.name,
                              f"{len(deleted)} messages")
            return f"🗑️ Purged **{len(deleted)}** messages."
        except Exception as e:
            return f"❌ Purge failed: {e}"

    elif cmd == "lockdown":
        try:
            await message.channel.set_permissions(
                guild.default_role, send_messages=False,
                reason=f"Lockdown by {author.display_name}: {reason}"
            )
            log_recent_action(guild.id, "LOCKDOWN", message.channel.name, reason)
            return f"🔒 Channel locked. Reason: {reason}"
        except Exception as e:
            return f"❌ Lockdown failed: {e}"

    elif cmd == "unlock":
        try:
            await message.channel.set_permissions(
                guild.default_role, send_messages=None,
                reason=f"Unlock by {author.display_name}"
            )
            log_recent_action(guild.id, "UNLOCK", message.channel.name, reason)
            return "🔓 Channel unlocked."
        except Exception as e:
            return f"❌ Unlock failed: {e}"

    elif cmd == "slowmode":
        secs = int(parsed.get("seconds", 5))
        secs = min(secs, 21600)
        try:
            await message.channel.edit(slowmode_delay=secs)
            return f"🐢 Slowmode set to **{secs}s**." if secs else "🐢 Slowmode disabled."
        except Exception as e:
            return f"❌ Slowmode failed: {e}"

    # ------------------------------------------------------------------
    # FUN / UTILITY COMMANDS
    # ------------------------------------------------------------------

    elif cmd == "trivia":
        prompt = "Generate a trivia question with 4 options. JSON: {\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"correct\":0,\"correct_answer\":\"...\"}"
        data = await ai.ask_json(prompt, prefer="fast")
        if not data:
            return "❌ Couldn't generate trivia."
        q = data.get("question", "?")
        opts = data.get("options", ["A", "B", "C", "D"])
        correct_idx = data.get("correct", 0)
        emojis = ["🇦", "🇧", "🇨", "🇩"]
        text = f"🧠 **Trivia Time!**\n\n{q}\n\n"
        for i, o in enumerate(opts[:4]):
            text += f"{emojis[i]} {o}\n"
        msg_sent = await message.channel.send(text)
        for i in range(min(len(opts), 4)):
            await msg_sent.add_reaction(emojis[i])
        trivia_sessions[msg_sent.id] = {
            "correct_emoji": emojis[correct_idx],
            "correct_answer": data.get("correct_answer", opts[correct_idx]),
            "answered": [],
        }
        return None

    elif cmd == "eightball":
        question = parsed.get("question", "")
        responses = [
            "🎱 It is certain.", "🎱 Without a doubt.", "🎱 Yes, definitely.",
            "🎱 Reply hazy, try again.", "🎱 Ask again later.",
            "🎱 Better not tell you now.", "🎱 Don't count on it.",
            "🎱 My sources say no.", "🎱 Very doubtful.", "🎱 Outlook not so good.",
            "🎱 Signs point to yes.", "🎱 Most likely.", "🎱 Outlook good.",
            "🎱 Yes.", "🎱 My reply is no.", "🎱 Cannot predict now.",
        ]
        return f"**Q:** {question}\n{random.choice(responses)}"

    elif cmd == "roast":
        target_name = parsed.get("target", "someone")
        if target_member:
            target_name = target_member.display_name
        roast = await ai.chat(
            f"Write a short, funny, light-hearted roast (1-2 sentences) for someone named '{target_name}'. "
            "Be playful, NEVER offensive, racist, or vulgar. No swearing.",
            max_tokens=150, prefer="fast"
        )
        return f"🔥 {sanitize_bot_response(roast or 'You are... something.')}"

    elif cmd == "compliment":
        target_name = parsed.get("target", "someone")
        if target_member:
            target_name = target_member.display_name
        comp = await ai.chat(
            f"Write a warm, genuine compliment (1-2 sentences) for '{target_name}'. Be creative.",
            max_tokens=150, prefer="fast"
        )
        return f"💖 {sanitize_bot_response(comp or 'You are awesome!')}"

    elif cmd == "dadjoke":
        joke = await ai.chat(
            "Tell a single short dad joke. Just the joke, nothing else.",
            max_tokens=150, prefer="fast"
        )
        return f"👨 {sanitize_bot_response(joke or 'I am reading a book about anti-gravity. Impossible to put down!')}"

    elif cmd == "ship":
        t1 = parsed.get("target1_id", "")
        t2 = parsed.get("target2_id", "")
        m1 = guild.get_member(int(t1)) if str(t1).isdigit() else None
        m2 = guild.get_member(int(t2)) if str(t2).isdigit() else None
        n1 = m1.display_name if m1 else "Person 1"
        n2 = m2.display_name if m2 else "Person 2"
        pct = random.randint(0, 100)
        bar = "💖" * (pct // 10) + "🖤" * (10 - pct // 10)
        return f"💕 **{n1}** × **{n2}**\n{bar} **{pct}%**"

    elif cmd == "rate":
        thing = parsed.get("thing", "that")
        rating = random.randint(0, 10)
        stars = "⭐" * rating + "☆" * (10 - rating)
        return f"I rate **{thing}** a **{rating}/10**\n{stars}"

    elif cmd == "fact":
        fact = await ai.chat(
            "Tell me one interesting random fact. Just the fact, 1-2 sentences.",
            max_tokens=150, prefer="fast"
        )
        return f"🧠 {sanitize_bot_response(fact or 'Honey never spoils.')}"

    elif cmd == "story":
        topic = parsed.get("topic", "adventure")
        story = await ai.chat(
            f"Write a very short story (3-5 sentences) about: {topic or 'a random adventure'}",
            max_tokens=300, prefer="auto"
        )
        return f"📖 {sanitize_bot_response(story or 'Once upon a time...')}"

    elif cmd == "riddle":
        riddle = await ai.chat(
            "Tell a riddle with the answer hidden in a spoiler tag using ||answer||. Format: Riddle then Answer.",
            max_tokens=200, prefer="fast"
        )
        return f"🤔 {sanitize_bot_response(riddle or 'What has keys but no locks? ||A piano||')}"

    elif cmd == "remind":
        dur_str = parsed.get("duration", "1h")
        reminder_text = parsed.get("reminder", "Reminder!")
        secs = parse_duration(dur_str) or 3600
        remind_time = (datetime.now() + timedelta(seconds=secs)).isoformat()
        db.execute(
            "INSERT INTO reminders (user_id,guild_id,channel_id,reminder,remind_time) VALUES (?,?,?,?,?)",
            (str(author.id), str(guild.id), str(message.channel.id),
             reminder_text, remind_time)
        )
        return f"⏰ I'll remind you in **{dur_str}**: {reminder_text}"

    elif cmd == "set_afk":
        afk_reason = parsed.get("reason", "AFK") or "AFK"
        db.execute(
            "INSERT OR REPLACE INTO afk_users (user_id,guild_id,reason) VALUES (?,?,?)",
            (str(author.id), str(guild.id), afk_reason)
        )
        return f"💤 You're now AFK: *{afk_reason}*"

    elif cmd == "rep":
        if not target_member:
            # View own rep
            rep = db.get_rep(author.id, guild.id)
            return f"⭐ Your reputation: **{rep}** points"
        if target_member.id == author.id:
            return "❌ You can't rep yourself!"
        new_rep = db.add_rep(target_member.id, guild.id, 1)
        return f"⭐ +1 rep to **{target_member.display_name}** (now **{new_rep}**)"

    elif cmd == "create_poll":
        raw = parsed.get("raw", "")
        # Parse: "Question? | option1 | option2 | option3"
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) < 3:
            return "❌ Format: `poll Question? | option1 | option2 | ...`"
        question = parts[0]
        options = parts[1:][:5]
        cur = db.execute(
            "INSERT INTO polls (guild_id,channel_id,question,options) VALUES (?,?,?,?)",
            (str(guild.id), str(message.channel.id), question, json.dumps(options))
        )
        poll_id = cur.lastrowid
        embed = _embed(f"📊 {question}", "", color=0x3498DB)
        view = PollView(options, poll_id, db)
        msg_sent = await message.channel.send(embed=embed, view=view)
        db.execute("UPDATE polls SET message_id=? WHERE id=?",
                   (str(msg_sent.id), poll_id))
        return None

    elif cmd == "summarize":
        count = int(parsed.get("count", 50) or 50)
        count = min(count, 200)
        msgs = []
        async for m in message.channel.history(limit=count):
            if not m.author.bot and m.content:
                msgs.append(f"{m.author.display_name}: {m.content[:200]}")
        msgs.reverse()
        if len(msgs) < 3:
            return "❌ Not enough messages to summarize."
        summary = await ai.chat(
            f"Summarize this Discord conversation concisely (3-8 bullet points):\n\n"
            + "\n".join(msgs[-50:]),
            max_tokens=500, prefer="auto"
        )
        return f"📝 **Summary:**\n{sanitize_bot_response(summary or 'Could not summarize.')}"

    elif cmd == "translate":
        lang = parsed.get("language", "English")
        text = parsed.get("text", "")
        if not text:
            return "❌ Specify text to translate."
        result = await ai.chat(
            f"Translate the following to {lang}. Only output the translation:\n\n{text[:1000]}",
            max_tokens=500, prefer="auto"
        )
        return f"🌐 **{lang}:** {sanitize_bot_response(result or text)}"

    elif cmd == "help":
        pages = _build_help_pages()
        view = HelpView(pages)
        await message.reply(embed=pages[0], view=view)
        return None

    elif cmd == "server_health":
        from datetime import timedelta as td
        week_ago = (datetime.now() - td(days=7)).date().isoformat()
        rows = db.query(
            "SELECT SUM(messages) as m, SUM(mod_actions) as a, SUM(joins) as j "
            "FROM daily_stats WHERE guild_id=? AND date>=?",
            (str(guild.id), week_ago)
        )
        stats = rows[0] if rows else {}
        stats = {
            "messages_7d": stats.get("m", 0) or 0,
            "mod_actions_7d": stats.get("a", 0) or 0,
            "joins_7d": stats.get("j", 0) or 0,
        }
        embed = build_server_health_embed(guild, stats)
        return embed

    elif cmd == "activity_stats":
        ms = db.query_one(
            "SELECT count, last_msg FROM message_stats WHERE user_id=? AND guild_id=?",
            (str(author.id), str(guild.id))
        )
        count = ms["count"] if ms else 0
        return f"📊 **{author.display_name}** — **{count}** messages in this server."

    elif cmd == "read_rules":
        rules = await read_server_rules(guild)
        if rules:
            return f"📜 **Server Rules:**\n{rules[:1900]}"
        return "❌ No rules found. Ask a mod to set up a rules channel."

    elif cmd == "refresh_rules":
        server_rules_cache.pop(str(guild.id), None)
        rules = await read_server_rules(guild)
        return f"🔄 Rules refreshed! ({len(rules)} chars)" if rules else "❌ No rules found."

    elif cmd == "balance":
        bal = db.get_balance(author.id, guild.id)
        return f"💰 **{author.display_name}** — Wallet: **{bal['balance']}** | Bank: **{bal['bank']}**"

    elif cmd == "profile":
        target = target_member or author
        warns = db.get_warnings(target.id, guild.id)
        rep = db.get_rep(target.id, guild.id)
        bal = db.get_balance(target.id, guild.id)
        ms = db.query_one(
            "SELECT count FROM message_stats WHERE user_id=? AND guild_id=?",
            (str(target.id), str(guild.id))
        )
        msg_count = ms["count"] if ms else 0
        joined = discord.utils.format_dt(target.joined_at, "R") if target.joined_at else "Unknown"
        embed = build_profile_embed(target, len(warns), rep, bal["balance"],
                                     msg_count, joined)
        return embed

    elif cmd == "memory_view":
        mem = db.get_server_memory(guild.id)
        lines = [
            f"**Mood:** {mem.get('server_mood', '?')}",
            f"**Topics:** {', '.join(mem.get('popular_topics', [])[:5]) or 'None'}",
            f"**Interactions:** {mem.get('total_interactions', 0)}",
        ]
        jokes = mem.get("inside_jokes", [])
        if jokes:
            lines.append(f"**Inside jokes:** {len(jokes)}")
        return f"🧠 **Server Memory:**\n" + "\n".join(lines)

    elif cmd == "setup_server":
        results = await setup_server(guild)
        return "⚙️ **Setup Results:**\n" + "\n".join(results[:20])

    elif cmd == "server_info":
        e = _embed(
            f"ℹ️ {guild.name}",
            guild.description or "",
            color=0x3498DB,
            fields=[
                ("Owner", str(guild.owner), True),
                ("Members", str(guild.member_count), True),
                ("Channels", str(len(guild.channels)), True),
                ("Roles", str(len(guild.roles)), True),
                ("Created", discord.utils.format_dt(guild.created_at, "R"), True),
                ("Boost Level", str(guild.premium_tier), True),
            ],
            thumbnail=guild.icon.url if guild.icon else None,
        )
        return e

    elif cmd == "user_info":
        target = target_member or author
        e = _embed(
            f"👤 {target}",
            "",
            color=target.color.value or 0x3498DB,
            fields=[
                ("ID", str(target.id), True),
                ("Joined", discord.utils.format_dt(target.joined_at, "R") if target.joined_at else "?", True),
                ("Created", discord.utils.format_dt(target.created_at, "R"), True),
                ("Roles", str(len(target.roles) - 1), True),
                ("Top Role", target.top_role.name, True),
            ],
        )
        if target.display_avatar:
            e.set_thumbnail(url=target.display_avatar.url)
        return e

    elif cmd == "giveaway":
        raw = parsed.get("raw", "")
        # Format: prize | duration | winners
        parts = [p.strip() for p in raw.split("|")]
        prize = parts[0] if parts else "Mystery Prize"
        dur_str = parts[1] if len(parts) > 1 else "1h"
        num_winners = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        secs = parse_duration(dur_str) or 3600
        end_time = (datetime.now() + timedelta(seconds=secs)).isoformat()

        embed = _embed(
            "🎉 GIVEAWAY 🎉",
            f"**Prize:** {prize}\n**Winners:** {num_winners}\n"
            f"**Ends:** <t:{int((datetime.now() + timedelta(seconds=secs)).timestamp())}:R>\n\n"
            "React with 🎉 to enter!",
            color=0xF1C40F,
        )
        msg_sent = await message.channel.send(embed=embed)
        await msg_sent.add_reaction("🎉")
        db.execute(
            "INSERT INTO giveaways (guild_id,channel_id,message_id,prize,winners,end_time,host_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(guild.id), str(message.channel.id), str(msg_sent.id),
             prize, num_winners, end_time, str(author.id))
        )
        return None

    elif cmd == "leave_server":
        if not is_owner(author.id):
            return "❌ Only the bot owner can do this."
        await notify_owner("INFO", f"Leaving **{guild.name}** by command", guild=guild)
        await cleanup_and_leave(guild)
        return None

    elif cmd == "revoke_license":
        if not is_owner(author.id):
            return "❌ Only the bot owner can do this."
        target_gid = parsed.get("guild_id")
        if target_gid:
            gid = int(target_gid)
            revoked_servers.add(gid)
            db.revoke_license(gid, f"Revoked by owner")
            licensed_servers.discard(gid)
            g = bot.get_guild(gid)
            if g:
                await cleanup_and_leave(g)
            return f"🔒 License revoked for guild {gid}."
        revoked_servers.add(int(guild.id))
        db.revoke_license(guild.id, "Revoked by owner")
        licensed_servers.discard(int(guild.id))
        await cleanup_and_leave(guild)
        return None

    elif cmd == "set_personality":
        p = parsed.get("personality", "").lower()
        if p not in PERSONALITIES:
            opts = ", ".join(PERSONALITIES.keys())
            return f"❌ Unknown personality. Options: {opts}"
        db.update_guild_setting(guild.id, "personality", p)
        info = PERSONALITIES[p]
        return f"{info['emoji']} Personality set to **{info['name']}**!"

    # ------------------------------------------------------------------
    # FALLBACK: unknown command → treat as chat
    # ------------------------------------------------------------------
    return None


# ------------------------------------------------------------------
# HELP PAGES
# ------------------------------------------------------------------
def _build_help_pages() -> list[discord.Embed]:
    pages = []

    pages.append(_embed(
        f"📖 SentinelMod v{BOT_IDENTITY['version']} — Help (1/4)",
        "**Moderation Commands** (mention me + command)\n\n"
        "• `ban @user [duration] [reason]`\n"
        "• `kick @user [reason]`\n"
        "• `mute @user [duration] [reason]`\n"
        "• `unmute @user`\n"
        "• `warn @user [reason]`\n"
        "• `warnings @user` — check warnings\n"
        "• `clear warnings @user`\n"
        "• `purge [count]` — bulk delete\n"
        "• `lockdown` / `unlock`\n"
        "• `slowmode [seconds]`",
        color=0xE74C3C,
    ))

    pages.append(_embed(
        f"📖 Help (2/4) — Fun & Social",
        "• `trivia` — trivia question\n"
        "• `8ball [question]` — Magic 8-Ball\n"
        "• `roast @user` — playful roast\n"
        "• `compliment @user`\n"
        "• `dadjoke`\n"
        "• `ship @user1 @user2` — compatibility\n"
        "• `rate [thing]`\n"
        "• `fact` — random fact\n"
        "• `story [topic]`\n"
        "• `riddle`\n"
        "• `rep @user` — give reputation",
        color=0x3498DB,
    ))

    pages.append(_embed(
        f"📖 Help (3/4) — Utility",
        "• `remind [time] [message]` — set reminder\n"
        "• `afk [reason]` — set AFK\n"
        "• `poll Question | opt1 | opt2 | ...`\n"
        "• `summarize [count]` — summarise chat\n"
        "• `translate [lang] [text]`\n"
        "• `balance` — economy balance\n"
        "• `profile [@user]` — view profile\n"
        "• `giveaway prize | duration | winners`\n"
        "• `rules` / `refresh rules`\n"
        "• `server health` / `stats`",
        color=0x2ECC71,
    ))

    pages.append(_embed(
        f"📖 Help (4/4) — Admin",
        "• `setup server` — initial setup\n"
        "• `personality [name]` — change personality\n"
        "• `server info` / `user info @user`\n"
        "• `memory` — view server memory\n\n"
        "**AI Chat:** Talk to me in the AI channel or mention me!\n"
        "**Appeals:** DM me to appeal a warning.\n\n"
        f"Made with ❤️ by **{BOT_IDENTITY['creator']}**",
        color=0x9B59B6,
    ))

    return pages
