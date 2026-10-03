# database.py
# ================================
# SQLite database with all tables for SentinelMod v9.0
# ================================

import sqlite3
import json
import time
from datetime import datetime
from typing import Optional
from core_config import DEFAULT_SETTINGS


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    # ------------------------------------------------------------------
    # SCHEMA
    # ------------------------------------------------------------------
    def init_schema(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id       TEXT PRIMARY KEY,
            ai_mod_enabled INTEGER DEFAULT 1,
            spam_limit     INTEGER DEFAULT 5,
            spam_window    INTEGER DEFAULT 5,
            mute_duration  INTEGER DEFAULT 10,
            raid_limit     INTEGER DEFAULT 10,
            raid_window    INTEGER DEFAULT 10,
            min_account_age INTEGER DEFAULT 7,
            warn_threshold_kick INTEGER DEFAULT 5,
            warn_threshold_ban  INTEGER DEFAULT 8,
            mod_role_name  TEXT DEFAULT 'Sentinel Mod',
            log_channel    TEXT DEFAULT 'sentinel-logs',
            raid_channel   TEXT DEFAULT 'sentinel-raids',
            memory_mode    TEXT DEFAULT 'both',
            memory_retention_days INTEGER DEFAULT 90,
            personality    TEXT DEFAULT 'professional',
            auto_appeal    INTEGER DEFAULT 1,
            created_channels TEXT DEFAULT '[]',
            created_roles    TEXT DEFAULT '[]',
            created_categories TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS accepted_licenses (
            guild_id  TEXT PRIMARY KEY,
            owner_id  TEXT,
            accepted  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS revoked_licenses (
            guild_id  TEXT PRIMARY KEY,
            reason    TEXT,
            revoked   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS warnings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT NOT NULL,
            guild_id  TEXT NOT NULL,
            reason    TEXT,
            severity  TEXT DEFAULT 'low',
            confidence REAL DEFAULT 0.0,
            content   TEXT,
            moderator TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_warn_user ON warnings(user_id, guild_id);

        CREATE TABLE IF NOT EXISTS message_archive (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id   TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            user_id    TEXT NOT NULL,
            content    TEXT,
            timestamp  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_archive_guild ON message_archive(guild_id, timestamp);

        CREATE TABLE IF NOT EXISTS message_stats (
            user_id  TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            count    INTEGER DEFAULT 0,
            last_msg TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        );

        CREATE TABLE IF NOT EXISTS conversation_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id  TEXT,
            user_id   TEXT,
            channel_id TEXT,
            role      TEXT,
            content   TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_conv ON conversation_history(guild_id, user_id, timestamp);

        CREATE TABLE IF NOT EXISTS afk_users (
            user_id  TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            reason   TEXT DEFAULT 'AFK',
            since    TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        );

        CREATE TABLE IF NOT EXISTS custom_commands (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id     TEXT NOT NULL,
            trigger_word TEXT NOT NULL,
            response     TEXT NOT NULL,
            creator_id   TEXT,
            created      TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cc ON custom_commands(guild_id, trigger_word);

        CREATE TABLE IF NOT EXISTS daily_stats (
            guild_id    TEXT NOT NULL,
            date        TEXT NOT NULL,
            messages    INTEGER DEFAULT 0,
            joins       INTEGER DEFAULT 0,
            leaves      INTEGER DEFAULT 0,
            mod_actions INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, date)
        );

        CREATE TABLE IF NOT EXISTS giveaways (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id   TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message_id TEXT,
            prize      TEXT NOT NULL,
            winners    INTEGER DEFAULT 1,
            end_time   TEXT NOT NULL,
            host_id    TEXT,
            active     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            guild_id    TEXT,
            channel_id  TEXT NOT NULL,
            reminder    TEXT NOT NULL,
            remind_time TEXT NOT NULL,
            active      INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS server_memory (
            guild_id TEXT PRIMARY KEY,
            data     TEXT DEFAULT '{}',
            updated  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_memory (
            user_id  TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            data     TEXT DEFAULT '{}',
            updated  TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        );

        CREATE TABLE IF NOT EXISTS scheduled_punishments (
            id       TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            user_id  TEXT NOT NULL,
            action   TEXT NOT NULL,
            run_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS appeals (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT NOT NULL,
            guild_id  TEXT NOT NULL,
            reason    TEXT,
            status    TEXT DEFAULT 'pending',
            ai_review TEXT,
            reviewer  TEXT,
            warning_id INTEGER,
            created   TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved  TEXT
        );

        CREATE TABLE IF NOT EXISTS reputation (
            user_id  TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            points   INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        );

        CREATE TABLE IF NOT EXISTS economy (
            user_id  TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            balance  INTEGER DEFAULT 100,
            bank     INTEGER DEFAULT 0,
            last_daily TEXT,
            PRIMARY KEY (user_id, guild_id)
        );

        CREATE TABLE IF NOT EXISTS mod_actions_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id  TEXT NOT NULL,
            mod_id    TEXT,
            target_id TEXT,
            action    TEXT,
            reason    TEXT,
            details   TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS polls (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id   TEXT NOT NULL,
            channel_id TEXT,
            message_id TEXT,
            question   TEXT,
            options    TEXT DEFAULT '[]',
            votes      TEXT DEFAULT '{}',
            end_time   TEXT,
            active     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS auto_responses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            trigger  TEXT NOT NULL,
            response TEXT NOT NULL,
            match_type TEXT DEFAULT 'contains'
        );
        """)
        self.conn.commit()
        print("✓ Database schema initialized")

    # ------------------------------------------------------------------
    # GENERIC HELPERS
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur
        except sqlite3.Error as e:
            print(f"DB execute error: {e}\nSQL: {sql}")
            return self.conn.cursor()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        try:
            cur = self.conn.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            print(f"DB query error: {e}")
            return []

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        try:
            cur = self.conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"DB query_one error: {e}")
            return None

    # ------------------------------------------------------------------
    # GUILD SETTINGS
    # ------------------------------------------------------------------
    def get_guild_settings(self, guild_id) -> dict:
        row = self.query_one("SELECT * FROM guild_settings WHERE guild_id=?", (str(guild_id),))
        if row:
            return row
        return dict(DEFAULT_SETTINGS)

    def init_guild_settings(self, guild_id):
        self.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
            (str(guild_id),)
        )

    def update_guild_setting(self, guild_id, key: str, value):
        allowed = [c for c in DEFAULT_SETTINGS.keys()] + [
            "created_channels", "created_roles", "created_categories"
        ]
        if key not in allowed:
            return
        self.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?",
                     (value, str(guild_id)))

    # ------------------------------------------------------------------
    # TRACKING CREATED RESOURCES
    # ------------------------------------------------------------------
    def _append_json_list(self, guild_id, column: str, value: str):
        row = self.query_one("SELECT {} FROM guild_settings WHERE guild_id=?".format(column),
                             (str(guild_id),))
        lst = json.loads(row[column]) if row and row.get(column) else []
        if value not in lst:
            lst.append(value)
        self.execute(f"UPDATE guild_settings SET {column}=? WHERE guild_id=?",
                     (json.dumps(lst), str(guild_id)))

    def track_created_channel(self, guild_id, name: str):
        self._append_json_list(guild_id, "created_channels", name)

    def track_created_role(self, guild_id, name: str):
        self._append_json_list(guild_id, "created_roles", name)

    def track_created_category(self, guild_id, name: str):
        self._append_json_list(guild_id, "created_categories", name)

    # ------------------------------------------------------------------
    # MESSAGES
    # ------------------------------------------------------------------
    def update_message_stats(self, user_id, guild_id):
        self.execute(
            """INSERT INTO message_stats (user_id, guild_id, count, last_msg)
               VALUES (?,?,1,CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, guild_id)
               DO UPDATE SET count=count+1, last_msg=CURRENT_TIMESTAMP""",
            (str(user_id), str(guild_id))
        )
        # Also bump daily stats
        today = datetime.now().date().isoformat()
        self.execute(
            """INSERT INTO daily_stats (guild_id, date, messages)
               VALUES (?,?,1)
               ON CONFLICT(guild_id, date)
               DO UPDATE SET messages=messages+1""",
            (str(guild_id), today)
        )

   def archive_message(self, guild_id, channel_id, user_id, content: str):
    if not content or len(content.strip()) < 2:
        return
    self.execute(
        "INSERT INTO message_archive (guild_id,channel_id,user_id,content) VALUES (?,?,?,?)",
        (str(guild_id), str(channel_id), str(user_id), content[:2000])
    )

    # ------------------------------------------------------------------
    # WARNINGS
    # ------------------------------------------------------------------
    def add_warning(self, user_id, guild_id, reason: str, severity: str = "low",
                    confidence: float = 0.0, content: str = None,
                    moderator: str = None) -> tuple[int, int]:
        """Add a warning. Returns (total_warning_count, new_warning_id)."""
        cur = self.execute(
            """INSERT INTO warnings (user_id,guild_id,reason,severity,confidence,content,moderator)
               VALUES (?,?,?,?,?,?,?)""",
            (str(user_id), str(guild_id), reason, severity, confidence,
             (content or "")[:500], moderator)
        )
        wid = cur.lastrowid or 0
        count_row = self.query_one(
            "SELECT COUNT(*) as c FROM warnings WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        )
        count = count_row["c"] if count_row else 1
        return count, wid

    def get_warnings(self, user_id, guild_id) -> list[dict]:
        return self.query(
            "SELECT * FROM warnings WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC",
            (str(user_id), str(guild_id))
        )

    def clear_warnings(self, user_id, guild_id) -> int:
        rows = self.query(
            "SELECT id FROM warnings WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        )
        self.execute(
            "DELETE FROM warnings WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        )
        return len(rows)

    # ------------------------------------------------------------------
    # SCHEDULED PUNISHMENTS
    # ------------------------------------------------------------------
    def add_scheduled_punishment(self, pid: str, guild_id, user_id,
                                 action: str, run_at: str):
        self.execute(
            "INSERT OR REPLACE INTO scheduled_punishments (id,guild_id,user_id,action,run_at) VALUES (?,?,?,?,?)",
            (pid, str(guild_id), str(user_id), action, run_at)
        )

    def get_due_punishments(self, now_iso: str) -> list[dict]:
        return self.query(
            "SELECT * FROM scheduled_punishments WHERE run_at<=?",
            (now_iso,)
        )

    def remove_scheduled_punishment(self, pid: str):
        self.execute("DELETE FROM scheduled_punishments WHERE id=?", (pid,))

    # ------------------------------------------------------------------
    # SERVER MEMORY
    # ------------------------------------------------------------------
    def get_server_memory(self, guild_id) -> dict:
        row = self.query_one("SELECT data FROM server_memory WHERE guild_id=?",
                             (str(guild_id),))
        if row and row.get("data"):
            try:
                return json.loads(row["data"])
            except:
                pass
        return {
            "server_culture": {},
            "inside_jokes": [],
            "popular_topics": [],
            "common_phrases": [],
            "server_mood": "chill",
            "total_interactions": 0,
        }

    def save_server_memory(self, guild_id, data: dict):
        self.execute(
            """INSERT INTO server_memory (guild_id, data, updated)
               VALUES (?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(guild_id)
               DO UPDATE SET data=?, updated=CURRENT_TIMESTAMP""",
            (str(guild_id), json.dumps(data), json.dumps(data))
        )

    # ------------------------------------------------------------------
    # USER MEMORY
    # ------------------------------------------------------------------
    def get_user_memory(self, user_id, guild_id) -> dict:
        row = self.query_one(
            "SELECT data FROM user_memory WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        )
        if row and row.get("data"):
            try:
                return json.loads(row["data"])
            except:
                pass
        return {"facts": [], "preferences": {}, "interactions": 0}

    def save_user_memory(self, user_id, guild_id, data: dict):
        self.execute(
            """INSERT INTO user_memory (user_id, guild_id, data, updated)
               VALUES (?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, guild_id)
               DO UPDATE SET data=?, updated=CURRENT_TIMESTAMP""",
            (str(user_id), str(guild_id), json.dumps(data), json.dumps(data))
        )

    # ------------------------------------------------------------------
    # CONVERSATION HISTORY
    # ------------------------------------------------------------------
    def add_conversation(self, guild_id, user_id, channel_id, role, content):
        self.execute(
            """INSERT INTO conversation_history
               (guild_id,user_id,channel_id,role,content) VALUES (?,?,?,?,?)""",
            (str(guild_id), str(user_id), str(channel_id), role, content[:2000])
        )

    def get_conversation(self, guild_id, user_id, channel_id=None,
                          limit: int = 20) -> list[dict]:
        if channel_id:
            return self.query(
                """SELECT role, content FROM conversation_history
                   WHERE guild_id=? AND user_id=? AND channel_id=?
                   ORDER BY timestamp DESC LIMIT ?""",
                (str(guild_id), str(user_id), str(channel_id), limit)
            )[::-1]
        return self.query(
            """SELECT role, content FROM conversation_history
               WHERE guild_id=? AND user_id=?
               ORDER BY timestamp DESC LIMIT ?""",
            (str(guild_id), str(user_id), limit)
        )[::-1]

    # ------------------------------------------------------------------
    # REPUTATION
    # ------------------------------------------------------------------
    def get_rep(self, user_id, guild_id) -> int:
        row = self.query_one(
            "SELECT points FROM reputation WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        )
        return row["points"] if row else 0

    def add_rep(self, user_id, guild_id, amount: int = 1) -> int:
        self.execute(
            """INSERT INTO reputation (user_id,guild_id,points) VALUES (?,?,?)
               ON CONFLICT(user_id,guild_id) DO UPDATE SET points=points+?""",
            (str(user_id), str(guild_id), amount, amount)
        )
        return self.get_rep(user_id, guild_id)

    # ------------------------------------------------------------------
    # ECONOMY
    # ------------------------------------------------------------------
    def get_balance(self, user_id, guild_id) -> dict:
        row = self.query_one(
            "SELECT * FROM economy WHERE user_id=? AND guild_id=?",
            (str(user_id), str(guild_id))
        )
        if row:
            return dict(row)
        self.execute(
            "INSERT OR IGNORE INTO economy (user_id,guild_id) VALUES (?,?)",
            (str(user_id), str(guild_id))
        )
        return {"user_id": str(user_id), "guild_id": str(guild_id),
                "balance": 100, "bank": 0, "last_daily": None}

    # ------------------------------------------------------------------
    # APPEALS
    # ------------------------------------------------------------------
    def create_appeal(self, user_id, guild_id, reason, warning_id=None) -> int:
        cur = self.execute(
            """INSERT INTO appeals (user_id,guild_id,reason,warning_id)
               VALUES (?,?,?,?)""",
            (str(user_id), str(guild_id), reason, warning_id)
        )
        return cur.lastrowid or 0

    def get_pending_appeals(self, guild_id) -> list[dict]:
        return self.query(
            "SELECT * FROM appeals WHERE guild_id=? AND status='pending' ORDER BY created DESC",
            (str(guild_id),)
        )

    def resolve_appeal(self, appeal_id, status, reviewer=None, ai_review=None):
        self.execute(
            """UPDATE appeals SET status=?, reviewer=?, ai_review=?,
               resolved=CURRENT_TIMESTAMP WHERE id=?""",
            (status, reviewer, ai_review, appeal_id)
        )

    # ------------------------------------------------------------------
    # LICENSES
    # ------------------------------------------------------------------
    def accept_license(self, guild_id, owner_id):
        self.execute(
            "INSERT OR REPLACE INTO accepted_licenses (guild_id,owner_id) VALUES (?,?)",
            (str(guild_id), str(owner_id))
        )

    def revoke_license(self, guild_id, reason=""):
        self.execute(
            "INSERT OR REPLACE INTO revoked_licenses (guild_id,reason) VALUES (?,?)",
            (str(guild_id), reason)
        )
        self.execute("DELETE FROM accepted_licenses WHERE guild_id=?",
                     (str(guild_id),))

    def close(self):
        self.conn.close()
