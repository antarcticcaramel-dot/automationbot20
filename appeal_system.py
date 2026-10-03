# appeal_system.py
# ================================
# SentinelMod v9.0 — Advanced Appeal System (AI judge)
# Flow:
#   user DMs bot → find ban/timeout across shared guilds
#   → session → user writes statement → AI judge scores it
#   → auto-approve/deny at high confidence, else mods get an
#     interactive Components-V2 review card (Approve / Deny / Statement)
#   → everything logged to the `appeals` table (auto-created)
# Wired in bot.py:  handle_appeal_dm(message, bot, db, ai, alert_mods)
# ================================

import re
import time
import asyncio
import discord
from datetime import datetime, timedelta

from utils import (sanitize_bot_response, truncate, safe_send,
                   BOT_IDENTITY, MOD_LOG_CHANNEL, MOD_ROLE_NAME)

# ---------- defensive config ----------
try:
    import core_config as _core
except Exception:
    _core = None

# ---------- tunables ----------
SESSION_TTL        = 15 * 60          # DM session expires after 15 min
STATEMENT_MIN      = 20
STATEMENT_MAX      = 1200
REAPPLY_COOLDOWN   = timedelta(hours=24)
AUTO_APPROVE_CONF  = 0.85             # AI auto-lifts punishment at ≥ this
AUTO_DENY_CONF     = 0.92             # AI auto-denies at ≥ this
MAX_GUILD_SCAN     = 40               # guilds scanned for bans per request
SCAN_DELAY         = 0.10             # politeness delay between fetch_ban calls

# Components V2 available? (discord.py ≥ 2.6). Everything falls back
# to classic embeds/views on older versions.
HAS_V2 = hasattr(discord.ui, "LayoutView") and hasattr(discord.ui, "Container")

# ---------- runtime state ----------
_sessions: dict[int, dict] = {}       # user_id → active appeal session
_hint_gate: dict[int, float] = {}     # DM hint rate-limit

_APPEAL_RE = re.compile(
    r"\b(appeal|unban|unbanned|banned|ban|mute[d]?|timeout|time\s?out|pardon|unmute)\b", re.I
)


# ==================================================================
# DB LAYER (all guarded — works even if your database.py differs)
# ==================================================================

def _ensure_tables(db):
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, username TEXT, guild_id TEXT,
            ptype TEXT, ban_reason TEXT, statement TEXT,
            verdict TEXT, confidence REAL, ai_reasoning TEXT,
            status TEXT DEFAULT 'pending', reviewed_by TEXT,
            created_at TEXT, decided_at TEXT)""")
    except Exception as e:
        print(f"[appeals] table init: {e}")


def _as_dict(row):
    try:
        return dict(row) if not isinstance(row, dict) else row
    except Exception:
        return {}


def _last_appeal(db, uid, gid):
    try:
        return db.query_one(
            "SELECT * FROM appeals WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT 1",
            (str(uid), str(gid)))
    except Exception:
        return None


def _recent(last_row) -> bool:
    try:
        t = datetime.fromisoformat(str(last_row["created_at"]))
        return datetime.now() - t < REAPPLY_COOLDOWN
    except Exception:
        return False


def _insert_appeal(db, user, guild, ptype, ban_reason, statement, verdict) -> int:
    try:
        db.execute(
            "INSERT INTO appeals (user_id, username, guild_id, ptype, ban_reason, statement,"
            " verdict, confidence, ai_reasoning, status, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (str(user.id), str(user), str(guild.id), ptype, (ban_reason or "")[:500],
             statement, str(verdict.get("verdict") or "review"),
             float(verdict.get("confidence") or 0),
             str(verdict.get("reasoning") or "")[:800], "pending",
             datetime.now().isoformat()))
        row = db.query_one(
            "SELECT id FROM appeals WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT 1",
            (str(user.id), str(guild.id)))
        return int(row["id"]) if row else 0
    except Exception as e:
        print(f"[appeals] insert: {e}")
        return 0


def _decide(db, appeal_id, status, reviewer):
    if not appeal_id:
        return
    try:
        db.execute(
            "UPDATE appeals SET status=?, reviewed_by=?, decided_at=? WHERE id=?",
            (status, reviewer or "moderator", datetime.now().isoformat(), appeal_id))
    except Exception:
        pass


def _user_warnings(db, user, guild):
    rows, total = [], 0
    try:
        rows = [_as_dict(r) for r in db.query(
            "SELECT reason, severity FROM warnings WHERE user_id=? AND guild_id=?"
            " ORDER BY id DESC LIMIT 8", (str(user.id), str(guild.id)))]
    except Exception:
        rows = []
    try:
        r = _as_dict(db.query_one(
            "SELECT COUNT(*) AS c FROM warnings WHERE user_id=? AND guild_id=?",
            (str(user.id), str(guild.id))))
        total = int(r.get("c") or 0)
    except Exception:
        total = len(rows)
    return rows, total


# ==================================================================
# UI HELPERS — Components V2 when available, embed fallback otherwise
# ==================================================================

def _new_container(accent=0x5865F2):
    if not HAS_V2:
        return None
    try:
        return discord.ui.Container(accent_colour=discord.Color(accent))
    except TypeError:
        try:
            return discord.ui.Container(accent_color=discord.Color(accent))
        except TypeError:
            return discord.ui.Container()


def _panel(title, lines, accent=0x5865F2):
    """Build a sendable panel: LayoutView (V2) or Embed (classic)."""
    lines = [str(l) for l in lines if l]
    if HAS_V2:
        view = discord.ui.LayoutView(timeout=600)
        cont = _new_container(accent) or discord.ui.Container()
        cont.add_item(discord.ui.TextDisplay(f"## {title}"))
        for l in lines:
            cont.add_item(discord.ui.TextDisplay(l))
        view.add_item(cont)
        return view
    e = discord.Embed(title=title, description="\n\n".join(lines)[:4000] or "—", color=accent)
    e.set_footer(text=f"SentinelMod v{BOT_IDENTITY.get('version', '9.0')} • appeals")
    return e


async def _dispatch(dest, payload, content=None):
    if payload is None:
        return await safe_send(dest, content)
    if isinstance(payload, discord.Embed):
        return await safe_send(dest, content, embed=payload)
    return await safe_send(dest, content, view=payload)


async def _send_to_logs(guild, db, payload) -> bool:
    """Deterministic direct send to the mod-log (independent of alert_mods)."""
    try:
        s = db.get_guild_settings(guild.id)
    except Exception:
        s = {}
    if not isinstance(s, dict):
        s = {}
    ch = discord.utils.get(guild.text_channels, name=s.get("log_channel", MOD_LOG_CHANNEL))
    if not ch:
        return False
    mr = discord.utils.get(guild.roles, name=s.get("mod_role_name", MOD_ROLE_NAME))
    try:
        if isinstance(payload, discord.Embed):
            await ch.send(content=mr.mention if mr else None, embed=payload)
        else:
            await ch.send(content=mr.mention if mr else None, view=payload)
        return True
    except Exception:
        return False


# ==================================================================
# ACTIONS
# ==================================================================

async def _lift(guild, user, ptype, reason):
    """Remove a ban or timeout. Returns (ok, note)."""
    try:
        if ptype == "ban":
            await guild.unban(discord.Object(id=user.id), reason=reason)
            return True, "user unbanned"
        m = guild.get_member(user.id)
        if m:
            await m.timeout(None, reason=reason)
            return True, "timeout removed"
        return False, "member not in server (timeout already expired?)"
    except discord.Forbidden:
        return False, "missing permissions"
    except Exception as e:
        return False, truncate(str(e), 80)


async def _dm_user_result(user, guild, approved, note=""):
    if approved:
        title = f"✅ Appeal approved — {guild.name}"
        lines = ["Good news — your appeal was **approved** and the punishment has been lifted.",
                 "Welcome back. Keep it clean! 🌟"]
        accent = 0x57F287
    else:
        title = f"❌ Appeal denied — {guild.name}"
        lines = ["Your appeal was **reviewed** and the punishment stays in place.",
                 "You can appeal again — cooldown is 24h between appeals."]
        accent = 0xED4245
    if note:
        lines.append(f"**Message from the staff/AI:** {truncate(note, 500)}")
    await _dispatch(user, _panel(title, lines, accent))


# ==================================================================
# INTERACTIVE CARDS (shared mixin → works in V2 and classic mode)
# ==================================================================

def _button_specs(mode):
    if mode == "undo":            # AI auto-approved — mods can revert
        return [("↩️", "Re-ban (undo)", discord.ButtonStyle.danger, "do_undo"),
                ("📄", "Statement", discord.ButtonStyle.secondary, "do_statement")]
    if mode == "approve_anyway":  # AI auto-denied — mods can override
        return [("✅", "Lift punishment", discord.ButtonStyle.success, "do_approve"),
                ("📄", "Statement", discord.ButtonStyle.secondary, "do_statement")]
    return [("✅", "Approve", discord.ButtonStyle.success, "do_approve"),
            ("⛔", "Deny", discord.ButtonStyle.danger, "do_deny"),
            ("📄", "Statement", discord.ButtonStyle.secondary, "do_statement")]


class _AppealActions:
    def _init_common(self, bot, db, guild, user, ptype, appeal_id,
                     ban_reason, statement, ai_reasoning):
        self.bot, self.db = bot, db
        self.guild, self.user = guild, user
        self.ptype, self.appeal_id = ptype, appeal_id
        self.ban_reason = ban_reason or ""
        self.statement = statement or ""
        self.ai_reasoning = ai_reasoning or ""
        self._btns = []

    def _disable(self):
        for b in self._btns:
            try:
                b.disabled = True
            except Exception:
                pass

    async def _gate(self, interaction) -> bool:
        perms = getattr(interaction.user, "guild_permissions", None)
        if perms and (perms.administrator or perms.ban_members or perms.manage_guild):
            return True
        try:
            await interaction.response.send_message("🚫 Mods only.", ephemeral=True)
        except Exception:
            pass
        return False

    async def do_approve(self, interaction: discord.Interaction):
        if not await self._gate(interaction):
            return
        await interaction.response.defer()
        ok, note = await _lift(self.guild, self.user, self.ptype,
                               f"Appeal approved by {interaction.user}")
        _decide(self.db, self.appeal_id, "approved" if ok else "failed", str(interaction.user))
        if ok:
            await _dm_user_result(self.user, self.guild, True,
                                  self.ai_reasoning or "Your appeal was approved.")
        self._disable()
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass
        try:
            await interaction.followup.send(("✅ " if ok else "⚠️ ") + note, ephemeral=True)
        except Exception:
            pass

    async def do_deny(self, interaction: discord.Interaction):
        if not await self._gate(interaction):
            return
        await interaction.response.defer()
        _decide(self.db, self.appeal_id, "denied", str(interaction.user))
        await _dm_user_result(self.user, self.guild, False,
                              self.ai_reasoning or
                              "The moderation team reviewed your appeal and kept the punishment.")
        self._disable()
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass
        try:
            await interaction.followup.send("⛔ Appeal denied — user notified.", ephemeral=True)
        except Exception:
            pass

    async def do_undo(self, interaction: discord.Interaction):
        if not await self._gate(interaction):
            return
        await interaction.response.defer()
        try:
            await self.guild.ban(discord.Object(id=self.user.id),
                                 reason=f"Appeal approval reverted by {interaction.user}")
            _decide(self.db, self.appeal_id, "reverted", str(interaction.user))
            note = "↩️ Approval reverted — user re-banned."
        except discord.Forbidden:
            note = "Re-ban failed: missing permissions."
        except Exception as e:
            note = f"Re-ban failed: {truncate(str(e), 80)}"
        self._disable()
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass
        try:
            await interaction.followup.send(note, ephemeral=True)
        except Exception:
            pass

    async def do_statement(self, interaction: discord.Interaction):
        if not await self._gate(interaction):
            return
        body = self.statement[:1500] or "(no statement recorded)"
        extra = f"\n\n**Punishment reason:** {truncate(self.ban_reason, 300)}" if self.ban_reason else ""
        try:
            await interaction.response.send_message(
                f"**Appeal statement**\n>>> {body}{extra}", ephemeral=True)
        except Exception:
            pass


class AppealCardV2(_AppealActions, discord.ui.LayoutView):
    def __init__(self, *, bot, db, guild, user, ptype, appeal_id, ban_reason,
                 statement, ai_reasoning, lines, mode="review", accent=0xFEE75C):
        discord.ui.LayoutView.__init__(self, timeout=900)
        self._init_common(bot, db, guild, user, ptype, appeal_id,
                          ban_reason, statement, ai_reasoning)
        cont = _new_container(accent) or discord.ui.Container()
        for line in lines:
            cont.add_item(discord.ui.TextDisplay(line))
        row = discord.ui.ActionRow()
        for emoji, label, style, meth in _button_specs(mode):
            b = discord.ui.Button(label=label, style=style, emoji=emoji)
            b.callback = getattr(self, meth)
            row.add_item(b)
            self._btns.append(b)
        cont.add_item(row)
        self.add_item(cont)


class AppealCardClassic(_AppealActions, discord.ui.View):
    def __init__(self, *, bot, db, guild, user, ptype, appeal_id, ban_reason,
                 statement, ai_reasoning, mode="review"):
        discord.ui.View.__init__(self, timeout=900)
        self._init_common(bot, db, guild, user, ptype, appeal_id,
                          ban_reason, statement, ai_reasoning)
        for emoji, label, style, meth in _button_specs(mode):
            b = discord.ui.Button(label=label, style=style, emoji=emoji)
            b.callback = getattr(self, meth)
            self.add_item(b)
            self._btns.append(b)


class GuildSelectView(discord.ui.LayoutView):
    """When a user is punished in multiple servers — pick which to appeal."""
    def __init__(self, user_id: int, choices):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.choices = choices  # list[(guild, ptype, ban_reason)]
        opts = []
        for i, (g, p, _r) in enumerate(choices[:25]):
            opts.append(discord.SelectOption(
                label=truncate(g.name, 90),
                value=str(i),
                description=f"{p} • {g.member_count or '?'} members"[:100],
            ))
        self.select = discord.ui.Select(placeholder="Pick the server to appeal…", options=opts)
        self.select.callback = self.on_pick
        row = discord.ui.ActionRow()
        row.add_item(self.select)
        cont = _new_container(0x5865F2) or discord.ui.Container()
        cont.add_item(discord.ui.TextDisplay("## 📨 Appeal — choose a server"))
        cont.add_item(row)
        self.add_item(cont)

    async def on_pick(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This menu isn't yours — run your own appeal in DMs.", ephemeral=True)
            return
        try:
            idx = int(self.select.values[0])
            guild, ptype, ban_reason = self.choices[idx]
        except Exception:
            await interaction.response.send_message("Invalid selection.", ephemeral=True)
            return
        _sessions[self.user_id] = {
            "guild": guild, "ptype": ptype, "ban_reason": ban_reason,
            "stage": "statement", "started": time.time(), "retries": 0,
        }
        await interaction.response.send_message(_session_intro(guild, ptype))
        self.stop()


# ==================================================================
# FINDING PUNISHMENTS
# ==================================================================

async def _find_punishable(bot, user):
    """Scan shared guilds for active bans/timeouts → [(guild, ptype, reason)]."""
    found = []
    for g in list(bot.guilds)[:MAX_GUILD_SCAN]:
        try:
            entry = await g.fetch_ban(user)   # raises NotFound if clean
            found.append((g, "ban", entry.reason or ""))
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass  # can't manage bans there → can't lift either
        except discord.HTTPException:
            pass
        m = g.get_member(user.id)
        if m and m.is_timed_out():
            found.append((g, "mute", ""))
        await asyncio.sleep(SCAN_DELAY)
    return found


# ==================================================================
# AI JUDGE
# ==================================================================

async def _ai_judge(ai, user, guild, ptype, ban_reason, statement, warns, total):
    warn_lines = "\n".join(
        f"- {w.get('severity', '?')}: {w.get('reason', '?')}" for w in warns
    ) or "- (none on record)"
    kind = "ban" if ptype == "ban" else "timeout (mute)"

    prompt = f"""You are an impartial, fair-but-not-naive appeal judge for the Discord server "{guild.name}".

PUNISHMENT: {kind}
STAFF-GIVEN REASON: {ban_reason or "(not recorded)"}
PRIOR WARNINGS ({total} total):
{warn_lines}

APPEAL STATEMENT from {user.name}:
\"\"\"{statement}\"\"\"

Evaluate honesty, acceptance of responsibility, understanding of the rules, and repeat risk.
Respond with JSON exactly like:
{{"verdict": "approve" or "deny" or "review", "confidence": 0.0-1.0, "reasoning": "1-3 sentences for the mods", "message_to_user": "1-2 kind sentences aimed at the user"}}

Approve ONLY for genuine remorse + low repeat risk + minor history. Toxic repeat offenders → deny. Unsure → review."""
    try:
        res = await ai.ask_json(prompt)
        if isinstance(res, dict) and res.get("verdict"):
            return res
    except Exception as e:
        print(f"[appeals] judge: {e}")
    return {"verdict": "review", "confidence": 0.0,
            "reasoning": "AI judge unavailable — manual review required.",
            "message_to_user": ""}


# ==================================================================
# FLOW
# ==================================================================

def _session_intro(guild, ptype) -> str:
    what = "ban" if ptype == "ban" else "mute/timeout"
    return (f"**Appeal for {guild.name}** ({what})\n\n"
            "In your own words, explain:\n"
            "• what happened\n"
            "• why it won't happen again\n\n"
            f"Send it as **one message** ({STATEMENT_MIN}–{STATEMENT_MAX} characters).\n"
            "Type `cancel` anytime to abort.")


async def _send_status(db, channel, user):
    try:
        rows = [_as_dict(r) for r in db.query(
            "SELECT guild_id, ptype, status, created_at FROM appeals"
            " WHERE user_id=? ORDER BY id DESC LIMIT 5", (str(user.id),))]
    except Exception:
        rows = []
    if not rows:
        await _dispatch(channel, _panel(
            "📋 Your appeals",
            ["No appeals on record. If you're banned or timed out, send `appeal` to start one."],
            0x5865F2))
        return
    lines = [f"• `{r.get('status') or 'pending'}` — {r.get('ptype', '?')} in server"
             f" `{r.get('guild_id', '?')}` • {str(r.get('created_at', ''))[:16]}"
             for r in rows]
    await _dispatch(channel, _panel("📋 Your recent appeals", lines, 0x5865F2))


async def _pick_stage(message, sess):
    m = re.match(r"^\s*(\d+)\s*$", message.content or "")
    if m and 1 <= int(m.group(1)) <= len(sess["choices"]):
        guild, ptype, ban_reason = sess["choices"][int(m.group(1)) - 1]
        sess.update(guild=guild, ptype=ptype, ban_reason=ban_reason,
                    stage="statement", started=time.time(), retries=0)
        await safe_send(message.channel, _session_intro(guild, ptype))
    else:
        await safe_send(message.channel,
                        "Reply with the **number** next to the server, or type `cancel`.")


async def _collect_statement(message, bot, db, ai, alert_mods, sess):
    user = message.author
    guild, ptype = sess["guild"], sess["ptype"]
    text = (message.content or "").strip()

    if len(text) < STATEMENT_MIN:
        sess["retries"] += 1
        if sess["retries"] >= 3:
            _sessions.pop(user.id, None)
            await safe_send(message.channel,
                            "Several attempts came in too short — appeal cancelled.\n"
                            "DM `appeal` again when you're ready to write it out.")
        else:
            await safe_send(message.channel,
                            f"Add a little more detail ({STATEMENT_MIN}+ characters). "
                            f"**{3 - sess['retries']}** tries left, or `cancel`.")
        return

    last = _last_appeal(db, user.id, guild.id)
    if last and _recent(last):
        _sessions.pop(user.id, None)
        await safe_send(message.channel,
                        "⏳ An appeal for that server was submitted in the last 24h — cooldown active.")
        return

    text = text[:STATEMENT_MAX]
    _sessions.pop(user.id, None)

    ban_reason = sess.get("ban_reason") or ""
    warns, total = _user_warnings(db, user, guild)

    async with message.channel.typing():
        verdict = await _ai_judge(ai, user, guild, ptype, ban_reason, text, warns, total)

    try:
        conf = float(verdict.get("confidence") or 0)
    except Exception:
        conf = 0.0
    v = str(verdict.get("verdict") or "review").lower()
    reasoning = sanitize_bot_response(str(verdict.get("reasoning") or ""))
    to_user = sanitize_bot_response(str(verdict.get("message_to_user") or ""))
    appeal_id = _insert_appeal(db, user, guild, ptype, ban_reason, text, verdict)

    if v.startswith("approve") and conf >= AUTO_APPROVE_CONF:
        ok, note = await _lift(guild, user, ptype,
                               f"Appeal auto-approved by AI judge ({conf:.0%})")
        _decide(db, appeal_id, "approved" if ok else "failed", "AI (auto)")
        if ok:
            await _dm_user_result(user, guild, True,
                                  to_user or "Approved based on your appeal. 🌟")
        await _notify_mods(alert_mods, bot, db, guild, user, ptype, text, verdict,
                           appeal_id, ban_reason, auto="approved" if ok else None, note=note)
    elif v.startswith("deny") and conf >= AUTO_DENY_CONF:
        _decide(db, appeal_id, "denied", "AI (auto)")
        await _dm_user_result(user, guild, False, to_user or reasoning)
        await _notify_mods(alert_mods, bot, db, guild, user, ptype, text, verdict,
                           appeal_id, ban_reason, auto="denied", note="")
    else:
        await _notify_mods(alert_mods, bot, db, guild, user, ptype, text, verdict,
                           appeal_id, ban_reason, auto=None, note="")
        await safe_send(message.channel,
                        "📬 Appeal forwarded to the staff with an AI recommendation.\n"
                        "You'll get a DM here once they decide. Check anytime with `status`.")


async def _notify_mods(alert_mods, bot, db, guild, user, ptype, statement,
                       verdict, appeal_id, ban_reason, auto=None, note=""):
    try:
        conf = float(verdict.get("confidence") or 0)
    except Exception:
        conf = 0.0
    v = str(verdict.get("verdict") or "review")
    reasoning = sanitize_bot_response(str(verdict.get("reasoning") or ""))
    kind = "Ban" if ptype == "ban" else "Timeout"
    head = {"approved": "✅ AUTO-APPROVED", "denied": "⛔ AUTO-DENIED"}.get(auto, "🧑‍⚖️ MOD REVIEW NEEDED")

    lines = [
        f"{head} — **{kind} appeal**",
        f"**User:** {user.mention} (`{user.id}`)",
        f"**AI verdict:** `{v}` @ {conf:.0%}",
        f"**AI reasoning:** {truncate(reasoning, 350)}",
        f"**Punishment reason:** {truncate(ban_reason or '—', 200)}",
        f"**Appeal statement:**\n>>> {truncate(statement, 700)}",
    ]
    if note:
        lines.append(f"**Action note:** {note}")

    if auto == "approved":
        mode, accent = "undo", 0x57F287
    elif auto == "denied":
        mode, accent = "approve_anyway", 0xED4245
    else:
        mode, accent = "review", 0xFEE75C

    card = embed = None
    sent = False
    if HAS_V2:
        card = AppealCardV2(bot=bot, db=db, guild=guild, user=user, ptype=ptype,
                            appeal_id=appeal_id, ban_reason=ban_reason,
                            statement=statement, ai_reasoning=reasoning,
                            lines=lines, mode=mode, accent=accent)
        sent = await _send_to_logs(guild, db, card)
    else:
        embed = discord.Embed(title=f"{head} — {kind} Appeal",
                              description="\n\n".join(lines)[:4000], color=accent)
        embed.set_footer(text=f"User ID: {user.id} • Appeal #{appeal_id or '?'}")
        sent = await _send_to_logs(guild, db, embed)
        if sent:
            await _send_to_logs(guild, db, AppealCardClassic(
                bot=bot, db=db, guild=guild, user=user, ptype=ptype,
                appeal_id=appeal_id, ban_reason=ban_reason, statement=statement,
                ai_reasoning=reasoning, mode=mode))

    if not sent:  # last-resort: bot.py's alert_mods helper
        try:
            await alert_mods(guild, card if HAS_V2 else embed)
        except Exception:
            pass


async def _start_flow(message, bot, db, ai, alert_mods):
    user = message.author
    async with message.channel.typing():
        found = await _find_punishable(bot, user)

    if not found:
        await _dispatch(message.channel, _panel(
            "🔍 No punishments found",
            ["I checked the servers we share and found no active **ban** or **timeout** for you.",
             "If you were punished in a server that removed this bot, contact that server's staff directly."],
            0xFEE75C))
        return

    if len(found) == 1:
        guild, ptype, ban_reason = found[0]
        last = _last_appeal(db, user.id, guild.id)
        if last and _recent(last):
            await safe_send(message.channel,
                            "⏳ You already appealed there recently — the cooldown is 24h between appeals.")
            return
        _sessions[user.id] = {"guild": guild, "ptype": ptype, "ban_reason": ban_reason,
                              "stage": "statement", "started": time.time(), "retries": 0}
        await safe_send(message.channel, _session_intro(guild, ptype))
        return

    choices = found[:10]
    _sessions[user.id] = {"choices": choices, "stage": "pick",
                          "started": time.time(), "retries": 0}
    lines = [f"**{i + 1}.** {g.name} — *{p}*" for i, (g, p, _r) in enumerate(choices)]
    await _dispatch(message.channel, _panel("📨 Multiple punishments found — pick one", lines, 0x5865F2))
    if HAS_V2:
        try:
            await message.channel.send(view=GuildSelectView(user.id, choices))
        except Exception:
            pass  # numbered fallback already sent above


# ==================================================================
# ENTRY POINT (wired from bot.py on_message DM branch)
# ==================================================================

async def handle_appeal_dm(message, bot, db, ai, alert_mods):
    user = message.author
    text = (message.content or "").strip()
    if not text and not message.attachments:
        return

    _ensure_tables(db)
    low = text.lower()

    sess = _sessions.get(user.id)
    if sess and time.time() - sess["started"] > SESSION_TTL:
        _sessions.pop(user.id, None)
        sess = None
        await safe_send(message.channel, "⌛ Appeal session expired — send `appeal` to start over.")

    # ----- continue an active session -----
    if sess:
        if low in {"cancel", "stop", "abort", "quit"}:
            _sessions.pop(user.id, None)
            await safe_send(message.channel, "❌ Appeal cancelled.")
            return
        if low == "status":
            await _send_status(db, message.channel, user)
            return
        stage = sess.get("stage")
        if stage == "pick":
            await _pick_stage(message, sess)
            return
        if stage == "statement":
            await _collect_statement(message, bot, db, ai, alert_mods, sess)
            return

    # ----- new DMs -----
    if low in {"status", "appeal status", "my appeals"}:
        await _send_status(db, message.channel, user)
        return

    if low == "appeal" or _APPEAL_RE.search(low):
        await _start_flow(message, bot, db, ai, alert_mods)
        return

    # anything else: gentle hint, rate-limited
    if time.time() - _hint_gate.get(user.id, 0) > 30:
        _hint_gate[user.id] = time.time()
        await safe_send(
            message.channel,
            "👋 This inbox is for **punishment appeals**.\n"
            "Banned or timed out? Send something like: *\"I want to appeal my ban\"*.\n"
            "Check status anytime with `status`.")
