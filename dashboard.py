# dashboard.py
# ================================
# SentinelMod - PREMIUM DASHBOARD
# Modern glass UI + smooth animations
# ================================

from flask import Flask, request, redirect, session, render_template_string, jsonify
import requests
import sqlite3
import json
import os
import asyncio
from datetime import datetime, timedelta

BOT_INSTANCE = None
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "change-me-please-32-chars-long")

app = Flask(__name__)
app.secret_key = SECRET_KEY


def set_bot(bot):
    global BOT_INSTANCE
    BOT_INSTANCE = bot


def get_db():
    conn = sqlite3.connect("sentinel.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_guild_settings(gid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (str(gid),))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}


def get_user_avatar(user_dict):
    try:
        if user_dict.get("avatar"):
            return f"https://cdn.discordapp.com/avatars/{user_dict['id']}/{user_dict['avatar']}.png?size=256"
    except Exception:
        pass
    return "https://cdn.discordapp.com/embed/avatars/0.png"


def get_guild_icon_url(guild):
    try:
        if guild and guild.icon:
            return guild.icon.url
    except Exception:
        pass
    return None


# ============================
# CSS
# ============================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

* { margin:0; padding:0; box-sizing:border-box; font-family:'Inter',sans-serif; }

:root {
  --bg-0:#0a0b14;
  --bg-1:#0f1019;
  --bg-2:#161826;
  --bg-3:#1c1f30;
  --bg-glass: rgba(255,255,255,0.04);
  --bg-glass-hover: rgba(255,255,255,0.07);
  --border: rgba(255,255,255,0.06);
  --border-strong: rgba(255,255,255,0.12);
  --text:#e6e8ee;
  --muted:#9aa0b4;
  --faded:#6b6f80;
  --head:#ffffff;

  --brand:#6c8cff;
  --brand-2:#8a6cff;
  --brand-3:#ec57ff;
  --green:#22c55e;
  --red:#ef4444;
  --yellow:#facc15;
  --orange:#f97316;
  --cyan:#22d3ee;

  --grad: linear-gradient(135deg,#6c8cff,#a06cff 50%,#ec57ff);
  --grad-soft: linear-gradient(135deg, rgba(108,140,255,0.15), rgba(236,87,255,0.15));
  --radius:14px;
  --radius-sm:10px;
  --radius-lg:20px;
  --shadow-lg: 0 25px 70px rgba(0,0,0,0.55);
}

html, body {
  background: var(--bg-0);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}

body::before {
  content:"";
  position: fixed;
  inset:0;
  background:
    radial-gradient(circle at 10% 0%, rgba(108,140,255,0.20), transparent 50%),
    radial-gradient(circle at 90% 10%, rgba(236,87,255,0.18), transparent 55%),
    radial-gradient(circle at 50% 100%, rgba(34,211,238,0.10), transparent 60%);
  z-index: -1;
}

a { color: inherit; text-decoration: none; }
button { font-family: inherit; }

::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.07); border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background:rgba(255,255,255,0.15); }

/* ===== LAYOUT ===== */
.app { display: flex; min-height:100vh; }

.sidebar {
  width:260px;
  background: rgba(15,16,25,0.7);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-right: 1px solid var(--border);
  position: fixed;
  inset: 0 auto 0 0;
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.main {
  flex:1;
  margin-left:260px;
  min-height: 100vh;
}

.topbar {
  height:64px;
  background: rgba(15,16,25,0.5);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top:0;
  z-index: 50;
  display: flex;
  align-items: center;
  padding: 0 28px;
  gap: 20px;
}

.crumb {
  font-size: 14px;
  color: var(--muted);
  font-weight: 500;
}
.crumb b { color: var(--head); font-weight: 700; }
.crumb a { color: var(--muted); }
.crumb a:hover { color: var(--head); }

.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.content {
  padding: 30px 36px 60px;
  max-width: 1400px;
}

/* ===== SIDEBAR ===== */
.sb-head {
  padding: 20px 18px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
}
.sb-logo {
  width:42px; height:42px;
  background: var(--grad);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  box-shadow: 0 10px 28px rgba(108,140,255,0.45);
}
.sb-title {
  font-weight: 800;
  font-size: 17px;
  color: var(--head);
  letter-spacing: -0.2px;
}
.sb-subtitle {
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.sb-scroll {
  flex:1;
  overflow-y: auto;
  padding: 14px 12px 20px;
}

.nav-section { margin-bottom: 18px; }
.nav-section-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--faded);
  padding: 0 12px;
  margin: 0 0 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  margin: 2px 0;
  transition: all 0.15s ease;
  position: relative;
}
.nav-link:hover {
  background: var(--bg-glass);
  color: var(--head);
}
.nav-link.active {
  background: var(--grad-soft);
  color: var(--head);
  font-weight: 600;
}
.nav-link.active::before {
  content:"";
  position: absolute;
  left:0; top:50%;
  transform: translateY(-50%);
  width:3px;
  height:60%;
  border-radius: 3px;
  background: var(--brand);
  box-shadow: 0 0 12px var(--brand);
}
.nav-icon {
  font-size: 17px;
  width: 22px;
  text-align: center;
}

.sb-user {
  padding: 14px 16px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0,0,0,0.2);
}
.sb-avatar {
  width: 36px; height:36px;
  border-radius: 50%;
  border: 2px solid var(--brand);
  object-fit: cover;
}
.sb-user-info { flex:1; overflow: hidden; }
.sb-username {
  font-size: 13px;
  font-weight: 700;
  color: var(--head);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sb-status {
  font-size: 11px;
  color: var(--green);
  display: flex; align-items:center; gap:4px;
}
.sb-status::before {
  content:"";
  width:6px; height:6px;
  border-radius:50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}
.sb-logout {
  color: var(--muted);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: 0.15s;
}
.sb-logout:hover {
  color: var(--red);
  background: rgba(239,68,68,0.1);
}

/* ===== BUTTONS ===== */
.btn {
  padding: 9px 16px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
  font-family: inherit;
}
.btn-primary {
  background: var(--grad);
  color: white;
  box-shadow: 0 6px 18px rgba(108,140,255,0.35);
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(108,140,255,0.55); }
.btn-ghost {
  background: var(--bg-glass);
  border: 1px solid var(--border);
  color: var(--text);
}
.btn-ghost:hover { background: var(--bg-glass-hover); border-color: var(--border-strong); }
.btn-danger {
  background: rgba(239,68,68,0.15);
  color: var(--red);
  border: 1px solid rgba(239,68,68,0.25);
}
.btn-danger:hover { background: var(--red); color: white; }
.btn-success {
  background: rgba(34,197,94,0.15);
  color: var(--green);
  border: 1px solid rgba(34,197,94,0.25);
}
.btn-success:hover { background: var(--green); color: white; }
.btn-sm { padding: 6px 12px; font-size: 12px; }

/* ===== CARDS ===== */
.glass {
  background: var(--bg-glass);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.card {
  background: rgba(20,22,34,0.55);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
  transition: all 0.2s;
  backdrop-filter: blur(14px);
}
.card:hover { border-color: var(--border-strong); }

.card-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
}

/* ===== STAT CARDS ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px,1fr));
  gap: 18px;
  margin-bottom: 28px;
}
.stat-card {
  position: relative;
  padding: 22px;
  border-radius: var(--radius);
  background: linear-gradient(160deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid var(--border);
  overflow: hidden;
  transition: all 0.2s;
}
.stat-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-lg);
}
.stat-card::before {
  content:"";
  position: absolute;
  top:-40%; right:-40%;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(108,140,255,0.18), transparent 70%);
  border-radius: 50%;
}
.stat-icon-wrap {
  width:48px; height:48px;
  border-radius: 12px;
  display: flex; align-items:center; justify-content:center;
  font-size: 22px;
  margin-bottom: 14px;
  background: var(--grad-soft);
  border: 1px solid var(--border);
}
.stat-value {
  font-size: 32px;
  font-weight: 800;
  color: var(--head);
  letter-spacing: -1px;
}
.stat-label {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 4px;
}

/* ===== SECTION HEADER ===== */
.section {
  background: rgba(20,22,34,0.55);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 22px;
  overflow: hidden;
  backdrop-filter: blur(14px);
}
.section-head {
  padding: 18px 22px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--head);
}
.section-body { padding: 22px; }

/* ===== TABS ===== */
.tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-glass);
  padding: 6px;
  border-radius: 14px;
  border: 1px solid var(--border);
  margin-bottom: 24px;
  overflow-x: auto;
}
.tab {
  padding: 10px 18px;
  background: transparent;
  border: none;
  color: var(--muted);
  font-weight: 600;
  font-size: 13px;
  border-radius: 10px;
  cursor: pointer;
  white-space: nowrap;
  transition: 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.tab:hover { color: var(--head); }
.tab.active {
  background: var(--grad);
  color: white;
  box-shadow: 0 6px 16px rgba(108,140,255,0.35);
}
.tab-content { display: none; animation: fadeUp 0.3s ease; }
.tab-content.active { display: block; }
@keyframes fadeUp { from { opacity:0; transform: translateY(8px);} to{opacity:1;transform:translateY(0);} }

/* ===== FORMS ===== */
.form-group { margin-bottom: 18px; }
.form-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
  margin-bottom: 8px;
}
.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 12px 14px;
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--head);
  font-size: 14px;
  font-family: inherit;
  transition: 0.15s;
}
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(108,140,255,0.15);
}
.form-textarea { resize: vertical; min-height: 110px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-hint { font-size: 11px; color: var(--muted); margin-top: 6px; }

/* ===== TOGGLE FEATURES ===== */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}
.feature {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border);
  border-radius: 12px;
  transition: 0.2s;
}
.feature:hover {
  background: rgba(255,255,255,0.045);
  border-color: var(--border-strong);
}
.feature-info { display: flex; align-items: center; gap: 12px; }
.feature-icon-wrap {
  width: 38px; height: 38px;
  border-radius: 10px;
  background: var(--grad-soft);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}
.feature-name { font-size: 14px; font-weight: 700; color: var(--head); }
.feature-desc { font-size: 11px; color: var(--muted); margin-top: 2px; }

.switch {
  position: relative;
  width: 44px; height: 24px;
  background: rgba(255,255,255,0.1);
  border-radius: 14px;
  cursor: pointer;
  transition: 0.2s;
  flex-shrink: 0;
}
.switch.on { background: var(--grad); }
.switch-dot {
  position: absolute;
  top: 3px; left: 3px;
  width: 18px; height: 18px;
  background: white;
  border-radius: 50%;
  transition: 0.2s;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
.switch.on .switch-dot { left: 23px; }

/* ===== LIST ROWS ===== */
.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  margin-bottom: 8px;
  transition: 0.15s;
}
.row:hover { background: rgba(255,255,255,0.05); }

.row-avatar {
  width: 40px; height:40px;
  border-radius: 50%;
  background: var(--grad);
  color: white;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800;
  overflow: hidden;
  flex-shrink: 0;
}
.row-avatar img { width: 100%; height: 100%; object-fit: cover; }
.row-info { flex:1; min-width: 0; }
.row-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--head);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.row-detail {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.row-meta { font-size: 11px; color: var(--faded); }
.row-actions { display: flex; gap: 6px; flex-shrink: 0; }

/* ===== TAGS ===== */
.tag {
  padding: 3px 10px;
  border-radius: 50px;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  white-space: nowrap;
}
.tag-low { background: rgba(250,204,21,0.15); color: var(--yellow); }
.tag-medium { background: rgba(249,115,22,0.15); color: var(--orange); }
.tag-high { background: rgba(239,68,68,0.15); color: var(--red); }
.tag-critical { background: rgba(180,0,0,0.25); color: #ff7575; }
.tag-online { background: rgba(34,197,94,0.15); color: var(--green); }
.tag-offline { background: rgba(255,255,255,0.05); color: var(--muted); }

/* ===== SERVER CARDS ===== */
.server-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 18px;
}
.server-card {
  background: rgba(20,22,34,0.55);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
  transition: 0.2s;
  position: relative;
  overflow: hidden;
}
.server-card:hover {
  transform: translateY(-3px);
  border-color: var(--brand);
  box-shadow: var(--shadow-lg);
}
.server-card::after {
  content:"";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(108,140,255,0.08), transparent 60%);
  pointer-events: none;
}
.server-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}
.server-icon {
  width: 60px; height: 60px;
  border-radius: 16px;
  overflow: hidden;
  background: var(--grad);
  color: white;
  display: flex; align-items: center; justify-content: center;
  font-weight: 900;
  font-size: 24px;
  flex-shrink: 0;
  box-shadow: 0 8px 22px rgba(108,140,255,0.35);
}
.server-icon img { width: 100%; height: 100%; object-fit: cover; display: block; }
.server-name {
  font-size: 17px;
  font-weight: 800;
  color: var(--head);
  letter-spacing: -0.3px;
}
.server-meta {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}

/* ===== MEMBER GRID ===== */
.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
  max-height: 640px;
  overflow-y: auto;
  padding: 4px;
}
.member-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border);
  border-radius: 12px;
  transition: 0.2s;
}
.member-card:hover {
  background: rgba(255,255,255,0.05);
  border-color: var(--border-strong);
}
.member-avatar {
  width: 40px; height: 40px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--grad);
  color: white;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800;
  flex-shrink: 0;
}
.member-avatar img { width: 100%; height: 100%; object-fit: cover; }
.member-info { flex:1; min-width: 0; }
.member-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--head);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.member-meta {
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ===== SEARCH ===== */
.search-wrap {
  position: relative;
  margin-bottom: 18px;
}
.search-input {
  width: 100%;
  padding: 12px 18px 12px 44px;
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--head);
  font-size: 14px;
  font-family: inherit;
}
.search-input:focus { outline: none; border-color: var(--brand); }
.search-icon {
  position: absolute;
  left: 16px; top: 50%;
  transform: translateY(-50%);
  color: var(--muted);
  font-size: 16px;
}

/* ===== COMMAND ROW ===== */
.cmd-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 8px;
}
.cmd-trigger {
  font-family: 'JetBrains Mono', monospace;
  background: rgba(108,140,255,0.15);
  color: var(--brand);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
}
.cmd-response {
  color: var(--muted);
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== EMPTY STATE ===== */
.empty {
  text-align: center;
  padding: 60px 20px;
}
.empty-icon {
  font-size: 60px;
  margin-bottom: 12px;
  opacity: 0.3;
}
.empty-title { font-size: 17px; font-weight: 700; color: var(--head); margin-bottom: 4px; }
.empty-desc { font-size: 13px; color: var(--muted); }

/* ===== TOAST ===== */
.toast {
  position: fixed;
  top: 24px; right: 24px;
  padding: 14px 22px;
  background: rgba(20,22,34,0.95);
  border: 1px solid var(--border);
  color: var(--head);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  z-index: 9999;
  display: none;
  font-size: 14px;
  font-weight: 600;
  border-left: 4px solid var(--brand);
  backdrop-filter: blur(20px);
}
.toast.show { display: block; animation: slideIn 0.25s ease; }
.toast.success { border-left-color: var(--green); }
.toast.error { border-left-color: var(--red); }
@keyframes slideIn { from { transform: translateX(100%); opacity:0;} to{transform:translateX(0); opacity:1;} }

/* ===== LOGIN PAGE ===== */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.login-card {
  background: rgba(20,22,34,0.55);
  border: 1px solid var(--border);
  padding: 50px 40px;
  border-radius: 24px;
  max-width: 500px;
  width: 100%;
  text-align: center;
  backdrop-filter: blur(20px);
  box-shadow: var(--shadow-lg);
}
.login-logo {
  width: 80px; height: 80px;
  background: var(--grad);
  border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
  font-size: 36px;
  margin: 0 auto 18px;
  box-shadow: 0 16px 50px rgba(108,140,255,0.5);
}
.login-title {
  font-size: 40px;
  font-weight: 900;
  letter-spacing: -1px;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 10px;
}
.login-sub {
  font-size: 15px;
  color: var(--muted);
  margin-bottom: 32px;
  line-height: 1.6;
}
.login-btn {
  width: 100%;
  padding: 16px;
  background: var(--grad);
  color: white;
  border: none;
  border-radius: 14px;
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  gap: 10px;
  box-shadow: 0 12px 28px rgba(108,140,255,0.4);
  transition: 0.2s;
  font-family: inherit;
}
.login-btn:hover { transform: translateY(-2px); box-shadow: 0 18px 40px rgba(108,140,255,0.55); }
.login-feats {
  display: grid;
  grid-template-columns: repeat(3,1fr);
  gap: 12px;
  margin-top: 30px;
  text-align: left;
}
.lf {
  padding: 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 12px;
}
.lf-icon { font-size: 22px; margin-bottom: 6px; }
.lf-title { font-size: 12px; font-weight: 700; color: var(--head); }
.lf-desc { font-size: 11px; color: var(--muted); margin-top: 2px; }

/* ===== HEADER SERVER BANNER ===== */
.server-banner {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 28px;
  padding: 22px;
  background: rgba(20,22,34,0.55);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  backdrop-filter: blur(14px);
}
.server-banner .server-icon { width: 72px; height: 72px; font-size: 28px; }
.server-banner-info h1 {
  font-size: 26px;
  font-weight: 900;
  color: var(--head);
  letter-spacing: -0.5px;
}
.server-banner-info p { color: var(--muted); font-size: 13px; margin-top: 4px; }

/* ===== MOBILE ===== */
@media (max-width: 900px) {
  .sidebar { width: 70px; }
  .sb-title, .sb-subtitle, .sb-user-info, .nav-link span:last-child, .nav-section-title { display: none; }
  .main { margin-left: 70px; }
  .content { padding: 20px; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .form-row { grid-template-columns: 1fr; }
  .feature-grid { grid-template-columns: 1fr; }
  .login-feats { grid-template-columns: 1fr; }
}
</style>
"""

# ============================
# JS
# ============================
JS = """
<script>
function toast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + (type || '');
  setTimeout(() => t.classList.remove('show'), 2800);
}

function switchTab(name, el) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  const target = document.getElementById('tab-' + name);
  if (target) target.classList.add('active');
}

function toggleFeature(gid, key, el) {
  fetch('/api/toggle/' + gid + '/' + key, { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        el.classList.toggle('on');
        toast('Updated', 'success');
      } else toast('Failed', 'error');
    });
}

function updateSetting(gid, key, val) {
  fetch('/api/setting/' + gid + '/' + key, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value: val })
  }).then(r => r.json()).then(d => {
    if (d.success) toast('Saved', 'success');
  });
}

function addCommand(gid) {
  const t = document.getElementById('cc-trigger').value.trim();
  const r = document.getElementById('cc-response').value.trim();
  if (!t || !r) return toast('Fill both fields', 'error');
  fetch('/api/custom/' + gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({trigger:t, response:r})
  }).then(r=>r.json()).then(d=>{
    if (d.success) { toast('Added', 'success'); setTimeout(()=>location.reload(), 400); }
  });
}

function delCommand(gid, trig) {
  if (!confirm('Delete "' + trig + '"?')) return;
  fetch('/api/custom/' + gid + '/' + encodeURIComponent(trig), { method:'DELETE' })
    .then(r=>r.json()).then(d=>{ if (d.success){ toast('Deleted','success'); setTimeout(()=>location.reload(), 400); }});
}

function addWord(gid) {
  const w = document.getElementById('wf-word').value.trim();
  if (!w) return;
  fetch('/api/word/' + gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({word:w})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Added','success'); setTimeout(()=>location.reload(), 400); }
  });
}

function delWord(gid, w) {
  fetch('/api/word/' + gid + '/' + encodeURIComponent(w), { method:'DELETE' })
    .then(r=>r.json()).then(d=>{ if (d.success){ toast('Removed','success'); setTimeout(()=>location.reload(), 400); }});
}

function clearWarns(gid, uid) {
  if (!confirm('Clear warnings?')) return;
  fetch('/api/clearwarns/' + gid + '/' + uid, { method:'POST' })
    .then(r=>r.json()).then(d=>{ if(d.success){ toast('Cleared','success'); setTimeout(()=>location.reload(), 400); }});
}

function sendAnnounce(gid) {
  const ch = document.getElementById('an-channel').value;
  const ti = document.getElementById('an-title').value;
  const ms = document.getElementById('an-msg').value;
  if (!ch || !ms) return toast('Fill required fields','error');
  fetch('/api/announce/' + gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({channel:ch, title:ti, message:ms})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Sent','success'); document.getElementById('an-msg').value=''; document.getElementById('an-title').value=''; }
    else toast(d.error||'Failed','error');
  });
}

function sendDM(gid) {
  const uid = document.getElementById('dm-uid').value.trim();
  const ms = document.getElementById('dm-msg').value.trim();
  if (!uid || !ms) return toast('Fill both','error');
  fetch('/api/dm/' + gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({user_id:uid, message:ms})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Sent','success'); document.getElementById('dm-msg').value=''; }
    else toast(d.error||'Failed','error');
  });
}

function createChannel(gid) {
  const n = document.getElementById('ch-name').value.trim();
  const c = document.getElementById('ch-cat').value;
  if (!n) return toast('Name required','error');
  fetch('/api/channel/'+gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name:n, category:c})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Created','success'); setTimeout(()=>location.reload(),400); }
    else toast(d.error||'Failed','error');
  });
}

function deleteChannel(gid, cn) {
  if (!confirm('Delete #'+cn+'?')) return;
  fetch('/api/channel/' + gid + '/' + encodeURIComponent(cn), { method:'DELETE' })
    .then(r=>r.json()).then(d=>{ if (d.success){ toast('Deleted','success'); setTimeout(()=>location.reload(),400); }});
}

function createRole(gid) {
  const n = document.getElementById('rl-name').value.trim();
  const c = document.getElementById('rl-color').value;
  if (!n) return toast('Name required','error');
  fetch('/api/role/'+gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name:n, color:c})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Created','success'); setTimeout(()=>location.reload(),400); }
  });
}

function deleteRole(gid, n) {
  if (!confirm('Delete role "'+n+'"?')) return;
  fetch('/api/role/' + gid + '/' + encodeURIComponent(n), { method:'DELETE' })
    .then(r=>r.json()).then(d=>{ if (d.success){ toast('Deleted','success'); setTimeout(()=>location.reload(),400); }});
}

function createCategory(gid) {
  const n = document.getElementById('ct-name').value.trim();
  if (!n) return;
  fetch('/api/category/'+gid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name:n})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Created','success'); setTimeout(()=>location.reload(),400); }
  });
}

function userAction(gid, uid, action) {
  const reason = prompt('Reason:');
  if (!reason) return;
  const duration = action === 'mute' ? prompt('Duration in minutes:','10') : null;
  fetch('/api/useraction/'+gid+'/'+uid, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({action, reason, duration})
  }).then(r=>r.json()).then(d=>{
    if (d.success){ toast('Done','success'); setTimeout(()=>location.reload(),400); }
    else toast(d.error||'Failed','error');
  });
}

function searchMembers() {
  const q = document.getElementById('mem-search').value.toLowerCase();
  document.querySelectorAll('.member-card').forEach(c => {
    c.style.display = c.dataset.name.toLowerCase().includes(q) ? 'flex' : 'none';
  });
}
</script>
"""


def base_html(content, title="Dashboard"):
    return f"""<!DOCTYPE html><html><head>
<title>{title} · SentinelMod</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
{CSS}
</head><body>
<div id="toast" class="toast"></div>
{content}
{JS}
</body></html>"""


def sidebar_html(user, active_page="home", guild_id=None):
    avatar = get_user_avatar(user)
    home_active = "active" if active_page == "home" else ""

    main_items = ""
    mgmt_items = ""

    if guild_id:
        cats = {
            "Main": [
                ("overview", "📊", "Overview"),
                ("features", "⚙️", "Features"),
                ("moderation", "🛡️", "Moderation"),
                ("members", "👥", "Members"),
                ("channels", "💬", "Channels"),
                ("roles", "🎭", "Roles"),
            ],
            "Management": [
                ("warnings", "⚠️", "Warnings"),
                ("commands", "⚡", "Custom Commands"),
                ("filters", "🔤", "Word Filters"),
                ("analytics", "📈", "Analytics"),
                ("leaderboard", "🏆", "Leaderboard"),
                ("announce", "📢", "Announce"),
                ("settings", "🔧", "Settings"),
            ]
        }
        for sec, items in cats.items():
            html = ""
            for key, icon, label in items:
                active = "active" if active_page == key else ""
                html += (
                    f'<a class="nav-link {active}" '
                    f'onclick="document.querySelector(\'.tab[data-tab={key}]\').click()">'
                    f'<span class="nav-icon">{icon}</span><span>{label}</span></a>'
                )
            if sec == "Main":
                main_items = html
            else:
                mgmt_items = html

    return f"""
<aside class="sidebar">
  <div class="sb-head">
    <div class="sb-logo">🛡️</div>
    <div>
      <div class="sb-title">SentinelMod</div>
      <div class="sb-subtitle">Dashboard</div>
    </div>
  </div>

  <div class="sb-scroll">
    <div class="nav-section">
      <div class="nav-section-title">Dashboard</div>
      <a href="/" class="nav-link {home_active}">
        <span class="nav-icon">🏠</span><span>Home</span>
      </a>
    </div>

    {f'<div class="nav-section"><div class="nav-section-title">Server</div>{main_items}</div>' if guild_id else ''}
    {f'<div class="nav-section"><div class="nav-section-title">Management</div>{mgmt_items}</div>' if guild_id else ''}
  </div>

  <div class="sb-user">
    <img src="{avatar}" class="sb-avatar">
    <div class="sb-user-info">
      <div class="sb-username">{user['username']}</div>
      <div class="sb-status">Online</div>
    </div>
    <a href="/logout" class="sb-logout" title="Logout">⏻</a>
  </div>
</aside>
"""


# ============================
# ROUTES
# ============================
@app.route("/")
def index():
    if "user" not in session:
        return base_html("""
<div class="login-page">
  <div class="login-card">
    <div class="login-logo">🛡️</div>
    <div class="login-title">SentinelMod</div>
    <div class="login-sub">The most powerful AI-driven Discord moderation dashboard.<br>Control everything in one beautiful place.</div>
    <a href="/login" class="login-btn">Login with Discord →</a>
    <div class="login-feats">
      <div class="lf"><div class="lf-icon">🤖</div><div class="lf-title">AI Mod</div><div class="lf-desc">Smart auto-mod</div></div>
      <div class="lf"><div class="lf-icon">⚡</div><div class="lf-title">Instant</div><div class="lf-desc">Realtime updates</div></div>
      <div class="lf"><div class="lf-icon">🎮</div><div class="lf-title">100+ tools</div><div class="lf-desc">Everything you need</div></div>
    </div>
  </div>
</div>
""", "Login")

    user = session["user"]
    try:
        h = {"Authorization": f"Bearer {session['access_token']}"}
        r = requests.get("https://discord.com/api/users/@me/guilds", headers=h, timeout=10)
        user_guilds = r.json() if r.status_code == 200 else []
    except Exception:
        user_guilds = []

    bot_guild_ids = [g.id for g in BOT_INSTANCE.guilds] if BOT_INSTANCE else []
    manageable = []
    for ug in user_guilds:
        try:
            if int(ug.get("permissions", 0)) & 0x8:
                manageable.append({**ug, "has_bot": int(ug["id"]) in bot_guild_ids})
        except Exception:
            pass

    cards = ""
    for g in manageable[:50]:
        icon_url = None
        member_count = 0
        if BOT_INSTANCE:
            guild_obj = BOT_INSTANCE.get_guild(int(g["id"]))
            if guild_obj:
                member_count = guild_obj.member_count
                icon_url = get_guild_icon_url(guild_obj)
        if not icon_url and g.get("icon"):
            icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png?size=256"

        first_letter = g['name'][0].upper()
        icon_html = (
            f'<img src="{icon_url}" alt="" onerror="this.style.display=\'none\'">'
            if icon_url else first_letter
        )

        if g["has_bot"]:
            cards += f"""
<div class="server-card">
  <div class="server-head">
    <div class="server-icon">{icon_html}</div>
    <div>
      <div class="server-name">{g['name']}</div>
      <div class="server-meta">{member_count} members · <span class="tag tag-online">Active</span></div>
    </div>
  </div>
  <a href="/server/{g['id']}" class="btn btn-primary" style="width:100%; justify-content:center;">Manage Server →</a>
</div>"""
        else:
            invite = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={g['id']}"
            cards += f"""
<div class="server-card">
  <div class="server-head">
    <div class="server-icon">{icon_html}</div>
    <div>
      <div class="server-name">{g['name']}</div>
      <div class="server-meta"><span class="tag tag-offline">Bot not added</span></div>
    </div>
  </div>
  <a href="{invite}" target="_blank" class="btn btn-success" style="width:100%; justify-content:center;">Add Bot to Server</a>
</div>"""

    total_servers = len([m for m in manageable if m["has_bot"]])
    total_members = sum(BOT_INSTANCE.get_guild(int(m["id"])).member_count for m in manageable if m["has_bot"] and BOT_INSTANCE and BOT_INSTANCE.get_guild(int(m["id"])))

    content = f"""
<div class="app">
{sidebar_html(user, "home")}
<div class="main">
  <div class="topbar">
    <div class="crumb"><b>🏠 Home</b></div>
  </div>
  <div class="content">

    <div style="margin-bottom:28px;">
      <div style="font-size:30px; font-weight:900; color:var(--head); letter-spacing:-0.5px;">Welcome back, {user['username']}</div>
      <div style="color:var(--muted); font-size:14px; margin-top:4px;">Managing {total_servers} server{'s' if total_servers != 1 else ''} with SentinelMod</div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon-wrap">🏠</div>
        <div class="stat-value">{total_servers}</div>
        <div class="stat-label">Active Servers</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap">👥</div>
        <div class="stat-value">{total_members:,}</div>
        <div class="stat-label">Total Members</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap">⚙️</div>
        <div class="stat-value">{len(manageable)}</div>
        <div class="stat-label">Manageable</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-wrap">🤖</div>
        <div class="stat-value">99.9%</div>
        <div class="stat-label">Uptime</div>
      </div>
    </div>

    <div class="section">
      <div class="section-head"><div class="section-title">Your Servers</div></div>
      <div class="section-body">
        <div class="server-grid">{cards if cards else '<div class="empty"><div class="empty-icon">🔍</div><div class="empty-title">No servers found</div><div class="empty-desc">You must have admin permissions in a server</div></div>'}</div>
      </div>
    </div>

  </div>
</div>
</div>"""
    return base_html(content, "Home")


@app.route("/login")
def login():
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type":"application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return f"Error: {r.text}"
    tok = r.json()["access_token"]
    session["access_token"] = tok
    ur = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {tok}"})
    session["user"] = ur.json()
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/server/<guild_id>")
def server_page(guild_id):
    if "user" not in session:
        return redirect("/")
    if not BOT_INSTANCE:
        return "Bot not ready"
    guild = BOT_INSTANCE.get_guild(int(guild_id))
    if not guild:
        return "Bot not in this server"

    s = get_guild_settings(guild_id) or {}

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (guild_id,))
    warns_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id=?", (guild_id,))
    actions_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM custom_commands WHERE guild_id=?", (guild_id,))
    customs_count = c.fetchone()[0]
    c.execute("SELECT * FROM warnings WHERE guild_id=? ORDER BY timestamp DESC LIMIT 25", (guild_id,))
    warns = c.fetchall()
    c.execute("SELECT * FROM mod_actions WHERE guild_id=? ORDER BY timestamp DESC LIMIT 25", (guild_id,))
    actions = c.fetchall()
    c.execute("SELECT * FROM custom_commands WHERE guild_id=?", (guild_id,))
    customs = c.fetchall()
    c.execute("SELECT word FROM word_filters WHERE guild_id=?", (guild_id,))
    words = c.fetchall()
    c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 15", (guild_id,))
    top_users = c.fetchall()
    try:
        c.execute("SELECT user_id, rep FROM reputation WHERE guild_id=? ORDER BY rep DESC LIMIT 10", (guild_id,))
        top_rep = c.fetchall()
    except Exception:
        top_rep = []
    conn.close()

    features = [
        ("welcome_enabled", "👋", "Welcome Messages", "Greet new members"),
        ("anti_nuke_enabled", "💣", "Anti-Nuke", "Stop mass destruction"),
        ("invite_block", "🚫", "Block Invites", "Block discord.gg links"),
        ("link_scan", "🔗", "Link Scanner", "Detect phishing"),
        ("slowmode_ai", "🐌", "AI Slowmode", "Auto slow heated chats"),
        ("pre_conflict", "⚠️", "Pre-Conflict AI", "Detect arguments early"),
        ("caps_filter", "🔤", "Caps Filter", "Block excessive caps"),
        ("mention_spam", "📢", "Mention Spam", "Block mass mentions"),
        ("emoji_spam", "😂", "Emoji Spam", "Block emoji floods"),
        ("zalgo_filter", "🌀", "Zalgo Filter", "Block weird text"),
        ("phone_filter", "📞", "Phone Filter", "Block phone numbers"),
        ("email_filter", "📧", "Email Filter", "Block emails"),
        ("scam_filter", "💸", "Scam Filter", "Detect scams"),
        ("fake_nitro_filter", "💎", "Fake Nitro", "Block nitro scams"),
        ("token_filter", "🔑", "Token Grabber", "Block grabbers"),
        ("anti_advertisement", "📣", "Anti-Ads", "Block ads"),
        ("everyone_block", "🔕", "@everyone Block", "Block @everyone use"),
        ("nsfw_text_filter", "🔞", "NSFW Filter", "Block NSFW"),
        ("unicode_filter", "🔠", "Unicode Bypass", "Detect unicode tricks"),
        ("file_spam_filter", "📁", "File Spam", "Block file spam"),
    ]

    feat_html = ""
    for key, icon, name, desc in features:
        val = s.get(key, 0)
        feat_html += f"""
<div class="feature">
  <div class="feature-info">
    <div class="feature-icon-wrap">{icon}</div>
    <div>
      <div class="feature-name">{name}</div>
      <div class="feature-desc">{desc}</div>
    </div>
  </div>
  <div class="switch {'on' if val else ''}" onclick="toggleFeature('{guild_id}', '{key}', this)"><div class="switch-dot"></div></div>
</div>"""

    warns_html = ""
    for w in warns:
        m = guild.get_member(int(w["user_id"]))
        name = m.display_name if m else "Unknown User"
        av = m.display_avatar.url if m else None
        avhtml = f'<img src="{av}">' if av else name[0].upper()
        warns_html += f"""
<div class="row">
  <div class="row-avatar">{avhtml}</div>
  <div class="row-info">
    <div class="row-name">{name}</div>
    <div class="row-detail">{w['reason']}</div>
    <div class="row-meta">{w['timestamp'][:16]}</div>
  </div>
  <span class="tag tag-{w['severity']}">{w['severity']}</span>
  <button class="btn btn-sm btn-ghost" onclick="clearWarns('{guild_id}','{w['user_id']}')">Clear</button>
</div>"""

    actions_html = ""
    for a in actions:
        m = guild.get_member(int(a["user_id"]))
        mod = guild.get_member(int(a["mod_id"]))
        name = m.display_name if m else "Unknown"
        mod_name = mod.display_name if mod else ("Bot" if BOT_INSTANCE and a["mod_id"] == str(BOT_INSTANCE.user.id) else "Unknown")
        actions_html += f"""
<div class="row">
  <div class="row-avatar">{name[0].upper()}</div>
  <div class="row-info">
    <div class="row-name">{name} <span style="color:var(--brand); font-weight:700;">· {a['action']}</span></div>
    <div class="row-detail">{a['reason']} · by {mod_name}</div>
    <div class="row-meta">{a['timestamp'][:16]}</div>
  </div>
</div>"""

    members_html = ""
    for m in list(guild.members)[:200]:
        if m.bot:
            continue
        av = m.display_avatar.url
        roles_str = ", ".join([r.name for r in m.roles if r.name != "@everyone"][:2]) or "No roles"
        members_html += f"""
<div class="member-card" data-name="{m.name}">
  <div class="member-avatar"><img src="{av}"></div>
  <div class="member-info">
    <div class="member-name">{m.display_name}</div>
    <div class="member-meta">{roles_str}</div>
  </div>
  <div class="row-actions">
    <button class="btn btn-sm btn-ghost" title="Warn" onclick="userAction('{guild_id}','{m.id}','warn')">⚠️</button>
    <button class="btn btn-sm btn-ghost" title="Mute" onclick="userAction('{guild_id}','{m.id}','mute')">🔇</button>
    <button class="btn btn-sm btn-danger" title="Ban" onclick="userAction('{guild_id}','{m.id}','ban')">🔨</button>
  </div>
</div>"""

    channels_html = ""
    for ch in guild.text_channels:
        cat_name = ch.category.name if ch.category else "—"
        channels_html += f"""
<div class="cmd-row">
  <span class="cmd-trigger">#{ch.name}</span>
  <span class="cmd-response">{cat_name}</span>
  <button class="btn btn-sm btn-danger" onclick="deleteChannel('{guild_id}','{ch.name}')">Delete</button>
</div>"""

    roles_html = ""
    for r in guild.roles:
        if r.name == "@everyone":
            continue
        dot = f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{str(r.color)};margin-right:8px;"></span>'
        roles_html += f"""
<div class="cmd-row">
  <span>{dot}<b>{r.name}</b></span>
  <span class="cmd-response">{len(r.members)} members</span>
  <button class="btn btn-sm btn-danger" onclick="deleteRole('{guild_id}','{r.name}')">Delete</button>
</div>"""

    customs_html = ""
    for cc in customs:
        customs_html += f"""
<div class="cmd-row">
  <span class="cmd-trigger">{cc['trigger_word']}</span>
  <span class="cmd-response">{cc['response'][:80]}</span>
  <button class="btn btn-sm btn-danger" onclick="delCommand('{guild_id}','{cc['trigger_word']}')">×</button>
</div>"""

    words_html = ""
    for w in words:
        words_html += f"""
<div class="cmd-row">
  <span class="cmd-trigger">{w['word']}</span>
  <button class="btn btn-sm btn-danger" onclick="delWord('{guild_id}','{w['word']}')">×</button>
</div>"""

    top_html = ""
    for i, r in enumerate(top_users[:10], 1):
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "Unknown"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        top_html += f"""
<div class="row">
  <div style="font-size:20px;width:40px;text-align:center;">{medal}</div>
  <div class="row-info">
    <div class="row-name">{name}</div>
    <div class="row-detail">{r['message_count']} messages sent</div>
  </div>
</div>"""

    rep_html = ""
    for r in top_rep:
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "Unknown"
        rep_html += f"""
<div class="row">
  <div class="row-avatar">{name[0].upper()}</div>
  <div class="row-info">
    <div class="row-name">{name}</div>
    <div class="row-detail">⭐ {r['rep']} reputation</div>
  </div>
</div>"""

    ch_options = "".join([f'<option value="{ch.name}">#{ch.name}</option>' for ch in guild.text_channels[:100]])
    cat_options = '<option value="">No category</option>' + "".join([f'<option value="{c.name}">{c.name}</option>' for c in guild.categories])

    icon_url = get_guild_icon_url(guild)
    icon_html = (
        f'<img src="{icon_url}" alt="">'
        if icon_url else guild.name[0].upper()
    )

    content = f"""
<div class="app">
{sidebar_html(session["user"], "overview", guild_id)}
<div class="main">

  <div class="topbar">
    <div class="crumb"><a href="/">Home</a> · <b>{guild.name}</b></div>
  </div>

  <div class="content">

    <div class="server-banner">
      <div class="server-icon">{icon_html}</div>
      <div class="server-banner-info">
        <h1>{guild.name}</h1>
        <p>{guild.member_count:,} members · {len(guild.text_channels)} channels · {len(guild.roles)} roles</p>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card"><div class="stat-icon-wrap">👥</div><div class="stat-value">{guild.member_count:,}</div><div class="stat-label">Members</div></div>
      <div class="stat-card"><div class="stat-icon-wrap">⚠️</div><div class="stat-value">{warns_count}</div><div class="stat-label">Warnings</div></div>
      <div class="stat-card"><div class="stat-icon-wrap">🔨</div><div class="stat-value">{actions_count}</div><div class="stat-label">Mod Actions</div></div>
      <div class="stat-card"><div class="stat-icon-wrap">⚡</div><div class="stat-value">{customs_count}</div><div class="stat-label">Custom Commands</div></div>
    </div>

    <div class="tabs">
      <button class="tab active" data-tab="overview" onclick="switchTab('overview',this)">📊 Overview</button>
      <button class="tab" data-tab="features" onclick="switchTab('features',this)">⚙️ Features</button>
      <button class="tab" data-tab="moderation" onclick="switchTab('moderation',this)">🛡️ Moderation</button>
      <button class="tab" data-tab="members" onclick="switchTab('members',this)">👥 Members</button>
      <button class="tab" data-tab="channels" onclick="switchTab('channels',this)">💬 Channels</button>
      <button class="tab" data-tab="roles" onclick="switchTab('roles',this)">🎭 Roles</button>
      <button class="tab" data-tab="warnings" onclick="switchTab('warnings',this)">⚠️ Warnings</button>
      <button class="tab" data-tab="commands" onclick="switchTab('commands',this)">⚡ Commands</button>
      <button class="tab" data-tab="filters" onclick="switchTab('filters',this)">🔤 Filters</button>
      <button class="tab" data-tab="analytics" onclick="switchTab('analytics',this)">📈 Analytics</button>
      <button class="tab" data-tab="leaderboard" onclick="switchTab('leaderboard',this)">🏆 Leaderboard</button>
      <button class="tab" data-tab="announce" onclick="switchTab('announce',this)">📢 Announce</button>
      <button class="tab" data-tab="settings" onclick="switchTab('settings',this)">🔧 Settings</button>
    </div>

    <div id="tab-overview" class="tab-content active">
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:18px;">
        <div class="section"><div class="section-head"><div class="section-title">Recent Warnings</div></div>
          <div class="section-body">{warns_html or '<div class="empty"><div class="empty-icon">✅</div><div class="empty-title">No warnings</div><div class="empty-desc">All clear!</div></div>'}</div></div>
        <div class="section"><div class="section-head"><div class="section-title">Recent Mod Actions</div></div>
          <div class="section-body">{actions_html or '<div class="empty"><div class="empty-icon">📋</div><div class="empty-title">No actions yet</div></div>'}</div></div>
      </div>
    </div>

    <div id="tab-features" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Bot Features</div></div>
        <div class="section-body"><div class="feature-grid">{feat_html}</div></div></div>
    </div>

    <div id="tab-moderation" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Moderation Thresholds</div></div>
      <div class="section-body">
        <div class="form-row">
          <div class="form-group"><label class="form-label">Warnings → Mute</label><input type="number" class="form-input" value="{s.get('warn_mute',3)}" onchange="updateSetting('{guild_id}','warn_mute',this.value)"></div>
          <div class="form-group"><label class="form-label">Warnings → Ban</label><input type="number" class="form-input" value="{s.get('warn_ban',5)}" onchange="updateSetting('{guild_id}','warn_ban',this.value)"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label class="form-label">Mute Duration (min)</label><input type="number" class="form-input" value="{s.get('mute_duration',10)}" onchange="updateSetting('{guild_id}','mute_duration',this.value)"></div>
          <div class="form-group"><label class="form-label">AI Sensitivity (0-1)</label><input type="number" step="0.1" min="0" max="1" class="form-input" value="{s.get('ai_sensitivity',0.7)}" onchange="updateSetting('{guild_id}','ai_sensitivity',this.value)"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label class="form-label">Spam Limit</label><input type="number" class="form-input" value="{s.get('spam_limit',5)}" onchange="updateSetting('{guild_id}','spam_limit',this.value)"></div>
          <div class="form-group"><label class="form-label">Spam Window (sec)</label><input type="number" class="form-input" value="{s.get('spam_window',5)}" onchange="updateSetting('{guild_id}','spam_window',this.value)"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label class="form-label">Raid Limit</label><input type="number" class="form-input" value="{s.get('raid_limit',10)}" onchange="updateSetting('{guild_id}','raid_limit',this.value)"></div>
          <div class="form-group"><label class="form-label">Min Account Age (days)</label><input type="number" class="form-input" value="{s.get('min_account_age',7)}" onchange="updateSetting('{guild_id}','min_account_age',this.value)"></div>
        </div>
      </div></div>
    </div>

    <div id="tab-members" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Members ({guild.member_count})</div></div>
      <div class="section-body">
        <div class="search-wrap"><span class="search-icon">🔍</span><input type="text" id="mem-search" class="search-input" placeholder="Search members..." oninput="searchMembers()"></div>
        <div class="member-grid">{members_html}</div>
      </div></div>
    </div>

    <div id="tab-channels" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Create Channel</div></div>
      <div class="section-body">
        <div class="form-row">
          <div class="form-group"><label class="form-label">Channel Name</label><input type="text" id="ch-name" class="form-input" placeholder="gaming-chat"></div>
          <div class="form-group"><label class="form-label">Category</label><select id="ch-cat" class="form-select">{cat_options}</select></div>
        </div>
        <button class="btn btn-primary" onclick="createChannel('{guild_id}')">+ Create Channel</button>
      </div></div>
      <div class="section"><div class="section-head"><div class="section-title">All Channels ({len(guild.text_channels)})</div></div>
        <div class="section-body">{channels_html}</div></div>
    </div>

    <div id="tab-roles" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Create Role</div></div>
      <div class="section-body">
        <div class="form-row">
          <div class="form-group"><label class="form-label">Role Name</label><input type="text" id="rl-name" class="form-input" placeholder="VIP"></div>
          <div class="form-group"><label class="form-label">Color</label><input type="color" id="rl-color" class="form-input" value="#6c8cff" style="height:46px;"></div>
        </div>
        <button class="btn btn-primary" onclick="createRole('{guild_id}')">+ Create Role</button>
      </div></div>
      <div class="section"><div class="section-head"><div class="section-title">Create Category</div></div>
      <div class="section-body">
        <div class="form-group"><label class="form-label">Category Name</label><input type="text" id="ct-name" class="form-input"></div>
        <button class="btn btn-primary" onclick="createCategory('{guild_id}')">+ Create Category</button>
      </div></div>
      <div class="section"><div class="section-head"><div class="section-title">All Roles ({len(guild.roles)-1})</div></div>
        <div class="section-body">{roles_html}</div></div>
    </div>

    <div id="tab-warnings" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">All Warnings ({warns_count})</div></div>
        <div class="section-body">{warns_html or '<div class="empty"><div class="empty-icon">✅</div><div class="empty-title">No warnings</div></div>'}</div></div>
    </div>

    <div id="tab-commands" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Add Custom Command</div></div>
      <div class="section-body">
        <div class="form-row">
          <div class="form-group"><label class="form-label">Trigger</label><input type="text" id="cc-trigger" class="form-input" placeholder="hello"></div>
          <div class="form-group"><label class="form-label">Response</label><input type="text" id="cc-response" class="form-input" placeholder="Hi there!"></div>
        </div>
        <button class="btn btn-primary" onclick="addCommand('{guild_id}')">+ Add Command</button>
      </div></div>
      <div class="section"><div class="section-head"><div class="section-title">Custom Commands ({customs_count})</div></div>
        <div class="section-body">{customs_html or '<div class="empty"><div class="empty-icon">⚡</div><div class="empty-title">No commands</div></div>'}</div></div>
    </div>

    <div id="tab-filters" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Add Word Filter</div></div>
      <div class="section-body">
        <div style="display:flex; gap:10px;">
          <input type="text" id="wf-word" class="form-input" placeholder="Enter word..." style="flex:1;">
          <button class="btn btn-primary" onclick="addWord('{guild_id}')">+ Add</button>
        </div>
      </div></div>
      <div class="section"><div class="section-head"><div class="section-title">Filtered Words</div></div>
        <div class="section-body">{words_html or '<div class="empty"><div class="empty-icon">🔤</div><div class="empty-title">No filtered words</div></div>'}</div></div>
    </div>

    <div id="tab-analytics" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">Server Overview</div></div>
      <div class="section-body">
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:18px;">
          <div><div class="stat-value">{guild.member_count}</div><div class="stat-label">Members</div></div>
          <div><div class="stat-value">{sum(1 for m in guild.members if not m.bot)}</div><div class="stat-label">Humans</div></div>
          <div><div class="stat-value">{sum(1 for m in guild.members if m.bot)}</div><div class="stat-label">Bots</div></div>
          <div><div class="stat-value">{len(guild.channels)}</div><div class="stat-label">Channels</div></div>
        </div>
      </div></div>
    </div>

    <div id="tab-leaderboard" class="tab-content">
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:18px;">
        <div class="section"><div class="section-head"><div class="section-title">💬 Most Active</div></div>
          <div class="section-body">{top_html or '<div class="empty"><div class="empty-icon">📊</div><div class="empty-title">No data</div></div>'}</div></div>
        <div class="section"><div class="section-head"><div class="section-title">⭐ Top Reputation</div></div>
          <div class="section-body">{rep_html or '<div class="empty"><div class="empty-icon">⭐</div><div class="empty-title">No rep yet</div></div>'}</div></div>
      </div>
    </div>

    <div id="tab-announce" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">📢 Send Announcement</div></div>
      <div class="section-body">
        <div class="form-group"><label class="form-label">Channel</label><select id="an-channel" class="form-select">{ch_options}</select></div>
        <div class="form-group"><label class="form-label">Title (optional)</label><input type="text" id="an-title" class="form-input" placeholder="Important Update"></div>
        <div class="form-group"><label class="form-label">Message</label><textarea id="an-msg" class="form-textarea"></textarea></div>
        <button class="btn btn-primary" onclick="sendAnnounce('{guild_id}')">Send Announcement</button>
      </div></div>
      <div class="section"><div class="section-head"><div class="section-title">📨 Send DM to User</div></div>
      <div class="section-body">
        <div class="form-group"><label class="form-label">User ID</label><input type="text" id="dm-uid" class="form-input"></div>
        <div class="form-group"><label class="form-label">Message</label><textarea id="dm-msg" class="form-textarea"></textarea></div>
        <button class="btn btn-primary" onclick="sendDM('{guild_id}')">Send DM</button>
      </div></div>
    </div>

    <div id="tab-settings" class="tab-content">
      <div class="section"><div class="section-head"><div class="section-title">General Settings</div></div>
      <div class="section-body">
        <div class="form-group"><label class="form-label">Mod Role Name</label><input type="text" class="form-input" value="{s.get('mod_role_name','Sentinel-Mod')}" onchange="updateSetting('{guild_id}','mod_role_name',this.value)"></div>
        <div class="form-row">
          <div class="form-group"><label class="form-label">Log Channel</label><input type="text" class="form-input" value="{s.get('log_channel','sentinel-logs')}" onchange="updateSetting('{guild_id}','log_channel',this.value)"></div>
          <div class="form-group"><label class="form-label">Raid Channel</label><input type="text" class="form-input" value="{s.get('raid_channel','sentinel-raid-alerts')}" onchange="updateSetting('{guild_id}','raid_channel',this.value)"></div>
        </div>
        <div class="form-group"><label class="form-label">Welcome Channel</label><input type="text" class="form-input" value="{s.get('welcome_channel','welcome')}" onchange="updateSetting('{guild_id}','welcome_channel',this.value)"></div>
      </div></div>
    </div>

  </div>
</div>
</div>"""
    return base_html(content, guild.name)


# ============================
# API ROUTES
# ============================
@app.route("/api/toggle/<gid>/<feat>", methods=["POST"])
def api_toggle(gid, feat):
    if "user" not in session: return jsonify({"success": False})
    valid = ["welcome_enabled","anti_nuke_enabled","invite_block","link_scan","slowmode_ai","pre_conflict","caps_filter","mention_spam","emoji_spam","zalgo_filter","phone_filter","email_filter","scam_filter","fake_nitro_filter","token_filter","anti_advertisement","everyone_block","nsfw_text_filter","unicode_filter","file_spam_filter"]
    if feat not in valid: return jsonify({"success": False})
    s = get_guild_settings(gid)
    new_val = 0 if s.get(feat, 0) else 1
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {feat}=? WHERE guild_id=?", (new_val, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_value": new_val})


@app.route("/api/setting/<gid>/<key>", methods=["POST"])
def api_setting(gid, key):
    if "user" not in session: return jsonify({"success": False})
    valid = ["warn_mute","warn_ban","mute_duration","ai_sensitivity","spam_limit","spam_window","raid_limit","min_account_age","mod_role_name","log_channel","raid_channel","welcome_channel"]
    if key not in valid: return jsonify({"success": False})
    val = request.get_json().get("value")
    try:
        if key in ["warn_mute","warn_ban","mute_duration","spam_limit","spam_window","raid_limit","min_account_age"]:
            val = int(val)
        elif key == "ai_sensitivity":
            val = float(val)
    except Exception:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (val, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/custom/<gid>", methods=["POST"])
def api_add_custom(gid):
    if "user" not in session: return jsonify({"success": False})
    d = request.get_json()
    t = d.get("trigger","").lower().strip()
    r = d.get("response","").strip()
    if not t or not r: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO custom_commands (guild_id, trigger_word, response) VALUES (?,?,?)", (gid, t, r))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/custom/<gid>/<trig>", methods=["DELETE"])
def api_del_custom(gid, trig):
    if "user" not in session: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM custom_commands WHERE guild_id=? AND trigger_word=?", (gid, trig))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/word/<gid>", methods=["POST"])
def api_add_word(gid):
    if "user" not in session: return jsonify({"success": False})
    w = request.get_json().get("word","").lower().strip()
    if not w: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?,?)", (gid, w))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/word/<gid>/<word>", methods=["DELETE"])
def api_del_word(gid, word):
    if "user" not in session: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (gid, word.lower()))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/clearwarns/<gid>/<uid>", methods=["POST"])
def api_clear(gid, uid):
    if "user" not in session: return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND guild_id=?", (uid, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/announce/<gid>", methods=["POST"])
def api_announce(gid):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False, "error":"Not ready"})
    import discord
    d = request.get_json()
    ch_name = d.get("channel")
    msg = d.get("message")
    title = d.get("title") or "📢 Announcement"
    if not ch_name or not msg: return jsonify({"success": False, "error":"Missing fields"})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False, "error":"No guild"})
    ch = discord.utils.get(guild.text_channels, name=ch_name)
    if not ch: return jsonify({"success": False, "error":"Channel not found"})
    try:
        embed = discord.Embed(title=title, description=msg, color=discord.Color.blurple(), timestamp=datetime.now())
        embed.set_footer(text=f"Sent by {session['user']['username']}")
        asyncio.run_coroutine_threadsafe(ch.send(embed=embed), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/dm/<gid>", methods=["POST"])
def api_dm(gid):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False, "error":"Not ready"})
    import discord
    d = request.get_json()
    uid = d.get("user_id")
    msg = d.get("message")
    if not uid or not msg: return jsonify({"success": False, "error":"Missing"})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    try:
        member = guild.get_member(int(uid))
        if not member: return jsonify({"success": False, "error":"User not found"})
        embed = discord.Embed(title=f"Message from {guild.name}", description=msg, color=discord.Color.blurple())
        asyncio.run_coroutine_threadsafe(member.send(embed=embed), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/channel/<gid>", methods=["POST"])
def api_create_channel(gid):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False})
    import discord
    d = request.get_json()
    name = d.get("name","").lower().replace(" ","-")
    cat = d.get("category")
    if not name: return jsonify({"success": False})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    try:
        cat_obj = discord.utils.get(guild.categories, name=cat) if cat else None
        fut = asyncio.run_coroutine_threadsafe(guild.create_text_channel(name=name, category=cat_obj), BOT_INSTANCE.loop)
        fut.result(timeout=10)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/channel/<gid>/<cn>", methods=["DELETE"])
def api_del_channel(gid, cn):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False})
    import discord
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    try:
        ch = discord.utils.get(guild.text_channels, name=cn)
        if ch: asyncio.run_coroutine_threadsafe(ch.delete(), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/role/<gid>", methods=["POST"])
def api_create_role(gid):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False})
    import discord
    d = request.get_json()
    name = d.get("name","")
    color_hex = d.get("color","#000000")
    if not name: return jsonify({"success": False})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    try:
        color = discord.Color(int(color_hex.replace("#",""),16))
        fut = asyncio.run_coroutine_threadsafe(guild.create_role(name=name, color=color), BOT_INSTANCE.loop)
        fut.result(timeout=10)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/role/<gid>/<n>", methods=["DELETE"])
def api_del_role(gid, n):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False})
    import discord
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    try:
        r = discord.utils.get(guild.roles, name=n)
        if r: asyncio.run_coroutine_threadsafe(r.delete(), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/category/<gid>", methods=["POST"])
def api_create_category(gid):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False})
    name = request.get_json().get("name","")
    if not name: return jsonify({"success": False})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    try:
        asyncio.run_coroutine_threadsafe(guild.create_category(name=name), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/useraction/<gid>/<uid>", methods=["POST"])
def api_useraction(gid, uid):
    if "user" not in session or not BOT_INSTANCE: return jsonify({"success": False})
    d = request.get_json()
    action = d.get("action")
    reason = d.get("reason","No reason")
    duration = d.get("duration")
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild: return jsonify({"success": False})
    member = guild.get_member(int(uid))
    if not member: return jsonify({"success": False, "error":"User not found"})
    try:
        if action == "ban":
            asyncio.run_coroutine_threadsafe(guild.ban(member, reason=reason), BOT_INSTANCE.loop)
        elif action == "kick":
            asyncio.run_coroutine_threadsafe(guild.kick(member, reason=reason), BOT_INSTANCE.loop)
        elif action == "mute":
            until = datetime.now() + timedelta(minutes=int(duration or 10))
            asyncio.run_coroutine_threadsafe(member.timeout(until, reason=reason), BOT_INSTANCE.loop)
        elif action == "warn":
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO warnings (user_id, guild_id, reason, severity, timestamp) VALUES (?,?,?,?,?)", (str(uid), str(gid), reason, "manual", datetime.now().isoformat()))
            conn.commit()
            conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def run_dashboard():
    app.run(host="0.0.0.0", port=8080, debug=False)
