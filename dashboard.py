# dashboard.py
# ================================
# SentinelMod - Ultimate Dashboard
# Full Discord-themed control panel
# ================================

from flask import Flask, request, redirect, session, render_template_string, jsonify
import requests
import sqlite3
import json
import os
import asyncio
from datetime import datetime, timedelta

# Will be set from bot.py
BOT_INSTANCE = None
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "change-this-secret-key")

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

# ============ CSS - DISCORD EXACT THEME ============
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter','gg sans','Noto Sans',sans-serif}
:root{
--bg-primary:#313338;--bg-secondary:#2b2d31;--bg-tertiary:#1e1f22;
--bg-floating:#111214;--bg-input:#1e1f22;--bg-modifier:rgba(78,80,88,0.3);
--text-normal:#dbdee1;--text-muted:#949ba4;--text-faded:#6d6f78;
--header-primary:#f2f3f5;--header-secondary:#b5bac1;
--brand:#5865f2;--brand-hover:#4752c4;--brand-light:rgba(88,101,242,0.1);
--green:#23a559;--green-hover:#1a8047;--green-light:rgba(35,165,89,0.1);
--red:#f23f43;--red-hover:#c93538;--red-light:rgba(242,63,67,0.1);
--yellow:#f0b232;--yellow-light:rgba(240,178,50,0.1);
--orange:#e67e22;--white:#fff;
--border:rgba(255,255,255,0.06);--border-hover:rgba(255,255,255,0.12);
--sidebar-w:260px;--header-h:50px;
}
body{background:var(--bg-tertiary);color:var(--text-normal);min-height:100vh;overflow-x:hidden}
::-webkit-scrollbar{width:8px;height:8px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--bg-tertiary);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:#1a1b1e}
a{color:inherit;text-decoration:none}

/* LAYOUT */
.app{display:flex;min-height:100vh}
.sidebar{width:var(--sidebar-w);background:var(--bg-secondary);display:flex;flex-direction:column;position:fixed;height:100vh;z-index:50;border-right:1px solid var(--border)}
.main{flex:1;margin-left:var(--sidebar-w);min-height:100vh}
.topbar{height:var(--header-h);background:var(--bg-primary);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;position:sticky;top:0;z-index:40;backdrop-filter:blur(10px)}
.content{padding:24px;max-width:1400px}

/* SIDEBAR */
.sb-head{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;height:var(--header-h)}
.sb-logo{width:32px;height:32px;background:linear-gradient(135deg,#5865f2,#7289da);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;box-shadow:0 2px 8px rgba(88,101,242,0.4)}
.sb-title{font-weight:700;font-size:15px;color:var(--header-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb-nav{flex:1;overflow-y:auto;padding:10px 8px}
.nav-sec{margin-bottom:16px}
.nav-sec-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-muted);padding:0 10px;margin-bottom:6px}
.nav-link{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:4px;color:var(--text-muted);cursor:pointer;font-size:14px;font-weight:500;transition:all 0.15s;margin:1px 0}
.nav-link:hover{background:rgba(255,255,255,0.04);color:var(--text-normal)}
.nav-link.active{background:rgba(88,101,242,0.15);color:var(--white)}
.nav-icon{font-size:18px;width:24px;text-align:center;flex-shrink:0}
.sb-foot{padding:10px 12px;border-top:1px solid var(--border);background:var(--bg-tertiary);display:flex;align-items:center;gap:10px}
.sb-avatar{width:32px;height:32px;border-radius:50%;border:2px solid var(--brand)}
.sb-user{flex:1;overflow:hidden}
.sb-username{font-size:13px;font-weight:600;color:var(--header-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb-status{font-size:11px;color:var(--green)}
.sb-logout{color:var(--text-muted);cursor:pointer;font-size:18px;padding:4px}
.sb-logout:hover{color:var(--red)}

/* TOPBAR */
.crumb{font-size:14px;color:var(--text-muted);font-weight:500}
.crumb b{color:var(--header-primary);font-weight:700}
.tb-right{margin-left:auto;display:flex;gap:8px;align-items:center}

/* CARDS */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:var(--bg-primary);padding:20px;border-radius:8px;border:1px solid var(--border);transition:all 0.2s}
.stat-card:hover{border-color:var(--border-hover);transform:translateY(-2px)}
.stat-icon{width:44px;height:44px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:12px}
.icon-brand{background:var(--brand-light);color:var(--brand)}
.icon-green{background:var(--green-light);color:var(--green)}
.icon-red{background:var(--red-light);color:var(--red)}
.icon-yellow{background:var(--yellow-light);color:var(--yellow)}
.stat-value{font-size:28px;font-weight:800;color:var(--header-primary);line-height:1}
.stat-label{font-size:12px;color:var(--text-muted);margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}
.stat-trend{font-size:11px;margin-top:6px}
.trend-up{color:var(--green)}
.trend-down{color:var(--red)}

/* PANELS */
.panel{background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);margin-bottom:16px;overflow:hidden}
.panel-head{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.panel-title{font-size:13px;font-weight:700;color:var(--header-primary);text-transform:uppercase;letter-spacing:0.5px}
.panel-body{padding:20px}
.panel-foot{padding:12px 20px;border-top:1px solid var(--border);background:rgba(0,0,0,0.1)}

/* BUTTONS */
.btn{padding:8px 16px;border-radius:4px;border:none;cursor:pointer;font-weight:600;font-size:13px;transition:all 0.15s;display:inline-flex;align-items:center;gap:6px;font-family:inherit}
.btn-sm{padding:5px 12px;font-size:12px}
.btn-brand{background:var(--brand);color:var(--white)}
.btn-brand:hover{background:var(--brand-hover)}
.btn-green{background:var(--green);color:var(--white)}
.btn-green:hover{background:var(--green-hover)}
.btn-red{background:var(--red);color:var(--white)}
.btn-red:hover{background:var(--red-hover)}
.btn-ghost{background:transparent;color:var(--text-muted);border:1px solid var(--border)}
.btn-ghost:hover{background:rgba(255,255,255,0.04);color:var(--text-normal);border-color:var(--border-hover)}

/* FORMS */
.fg{margin-bottom:16px}
.flbl{display:block;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:var(--header-secondary);margin-bottom:8px}
.finp,.fsel,.ftxa{width:100%;padding:10px 12px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;color:var(--text-normal);font-size:14px;transition:border-color 0.15s;font-family:inherit}
.finp:focus,.fsel:focus,.ftxa:focus{outline:none;border-color:var(--brand)}
.ftxa{resize:vertical;min-height:100px;font-family:inherit}
.frow{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.fhint{font-size:11px;color:var(--text-muted);margin-top:4px}

/* TOGGLES */
.feat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px}
.feat{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:var(--bg-secondary);border-radius:6px;transition:background 0.15s;border:1px solid transparent}
.feat:hover{background:rgba(255,255,255,0.03);border-color:var(--border-hover)}
.feat-info{display:flex;align-items:center;gap:12px}
.feat-icon{font-size:20px;width:32px;text-align:center;flex-shrink:0}
.feat-text{flex:1}
.feat-name{font-size:14px;font-weight:600;color:var(--text-normal)}
.feat-desc{font-size:11px;color:var(--text-muted);margin-top:2px}
.switch{position:relative;width:42px;height:24px;background:#72767d;border-radius:12px;cursor:pointer;transition:0.2s;flex-shrink:0}
.switch.on{background:var(--green)}
.switch-dot{position:absolute;top:3px;left:3px;width:18px;height:18px;background:var(--white);border-radius:50%;transition:0.2s;box-shadow:0 1px 3px rgba(0,0,0,0.3)}
.switch.on .switch-dot{left:21px}

/* LIST ROW */
.row{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:6px;transition:background 0.15s;margin-bottom:4px}
.row:hover{background:rgba(255,255,255,0.03)}
.row-avatar{width:36px;height:36px;border-radius:50%;background:var(--brand);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0;overflow:hidden;color:var(--white)}
.row-avatar img{width:100%;height:100%;object-fit:cover}
.row-info{flex:1;min-width:0}
.row-name{font-size:14px;font-weight:600;color:var(--text-normal);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row-detail{font-size:12px;color:var(--text-muted);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row-meta{font-size:11px;color:var(--text-faded)}
.row-actions{display:flex;gap:6px;flex-shrink:0}

/* TAGS */
.tag{padding:2px 8px;border-radius:50px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap}
.tag-low{background:var(--yellow-light);color:var(--yellow)}
.tag-medium{background:rgba(230,126,34,0.15);color:var(--orange)}
.tag-high{background:var(--red-light);color:var(--red)}
.tag-critical{background:rgba(150,0,0,0.2);color:#ff6b6b}
.tag-online{background:var(--green-light);color:var(--green)}
.tag-bot{background:var(--brand-light);color:var(--brand)}

/* TABS */
.tabs{display:flex;gap:2px;padding:4px;background:var(--bg-tertiary);border-radius:8px;margin-bottom:20px;overflow-x:auto}
.tab{padding:8px 16px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;border-radius:4px;font-size:13px;font-weight:600;transition:0.15s;white-space:nowrap;font-family:inherit}
.tab.active{background:var(--bg-primary);color:var(--white)}
.tab:hover:not(.active){color:var(--text-normal)}
.panel-content{display:none}
.panel-content.active{display:block;animation:fadeUp 0.2s}
@keyframes fadeUp{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}

/* CMD ROW */
.cmd-row{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:var(--bg-secondary);border-radius:6px;margin-bottom:6px;gap:12px}
.cmd-trigger{font-family:'Consolas','Monaco',monospace;background:rgba(88,101,242,0.15);color:var(--brand);padding:3px 8px;border-radius:4px;font-size:13px;flex-shrink:0}
.cmd-resp{color:var(--text-muted);font-size:13px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* CHART */
.chart{height:200px;display:flex;align-items:flex-end;gap:3px;padding:16px 0;border-bottom:1px solid var(--border);margin-bottom:8px}
.bar{flex:1;background:linear-gradient(180deg,var(--brand) 0%,#7289da 100%);border-radius:3px 3px 0 0;min-height:4px;transition:all 0.3s;position:relative;cursor:pointer}
.bar:hover{background:linear-gradient(180deg,#7289da 0%,var(--brand) 100%)}
.bar:hover::after{content:attr(data-value);position:absolute;top:-26px;left:50%;transform:translateX(-50%);background:var(--bg-floating);color:var(--white);padding:3px 8px;border-radius:4px;font-size:11px;white-space:nowrap;z-index:10}
.bar-labels{display:flex;gap:3px}
.bar-lbl{flex:1;text-align:center;font-size:10px;color:var(--text-faded)}

/* EMPTY */
.empty{text-align:center;padding:48px 20px}
.empty-icon{font-size:48px;margin-bottom:12px;opacity:0.3}
.empty-title{font-size:16px;font-weight:600;color:var(--header-primary);margin-bottom:4px}
.empty-desc{font-size:13px;color:var(--text-muted)}

/* TOAST */
.toast{position:fixed;top:20px;right:20px;padding:14px 20px;background:var(--bg-floating);color:var(--white);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.5);z-index:9999;display:none;font-size:14px;border-left:4px solid var(--brand);max-width:350px;font-weight:500}
.toast.show{display:block;animation:slideIn 0.2s}
.toast.success{border-left-color:var(--green)}
.toast.error{border-left-color:var(--red)}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* MODAL */
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;backdrop-filter:blur(5px)}
.modal.active{display:flex}
.modal-box{background:var(--bg-primary);border-radius:8px;border:1px solid var(--border);max-width:500px;width:90%;max-height:80vh;overflow-y:auto;animation:scaleUp 0.2s}
@keyframes scaleUp{from{transform:scale(0.95);opacity:0}to{transform:scale(1);opacity:1}}
.modal-head{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.modal-title{font-size:16px;font-weight:700;color:var(--header-primary)}
.modal-close{background:none;border:none;color:var(--text-muted);font-size:24px;cursor:pointer;padding:4px;line-height:1}
.modal-close:hover{color:var(--text-normal)}
.modal-body{padding:20px}
.modal-foot{padding:12px 20px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:8px}

/* LOGIN */
.login-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(ellipse at top,#1a1b3e 0%,var(--bg-tertiary) 50%);padding:20px}
.login-card{background:var(--bg-primary);padding:40px;border-radius:16px;border:1px solid var(--border);max-width:480px;width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.3)}
.login-logo{font-size:72px;margin-bottom:16px;animation:bounce 2s infinite}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
.login-title{font-size:32px;font-weight:900;color:var(--header-primary);margin-bottom:8px;background:linear-gradient(135deg,#5865f2,#eb459e);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.login-subtitle{font-size:15px;color:var(--text-muted);margin-bottom:32px;line-height:1.5}
.login-btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:14px;background:var(--brand);color:var(--white);border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:0.15s;font-family:inherit}
.login-btn:hover{background:var(--brand-hover);transform:translateY(-2px);box-shadow:0 10px 30px rgba(88,101,242,0.4)}
.login-feats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:32px;text-align:left}
.lf{padding:12px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border)}
.lf-icon{font-size:20px;margin-bottom:6px}
.lf-title{font-size:12px;font-weight:700;color:var(--header-primary)}
.lf-desc{font-size:11px;color:var(--text-muted)}

/* SERVER CARDS */
.servers{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.srv{background:var(--bg-primary);padding:20px;border-radius:8px;border:1px solid var(--border);transition:all 0.2s}
.srv:hover{border-color:var(--brand);transform:translateY(-2px)}
.srv-head{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.srv-icon{width:56px;height:56px;border-radius:16px;background:linear-gradient(135deg,#5865f2,#eb459e);display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:800;overflow:hidden;flex-shrink:0;color:var(--white)}
.srv-icon img{width:100%;height:100%;object-fit:cover}
.srv-name{font-size:16px;font-weight:700;color:var(--header-primary)}
.srv-info{font-size:12px;color:var(--text-muted);margin-top:2px}

/* MEMBER GRID */
.mem-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px;max-height:600px;overflow-y:auto}
.mem-card{display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg-secondary);border-radius:6px;cursor:pointer;transition:0.15s;border:1px solid transparent}
.mem-card:hover{background:rgba(255,255,255,0.04);border-color:var(--border-hover)}
.mem-avatar{width:36px;height:36px;border-radius:50%;background:var(--brand);display:flex;align-items:center;justify-content:center;font-weight:700;overflow:hidden;flex-shrink:0;color:var(--white)}
.mem-avatar img{width:100%;height:100%;object-fit:cover}
.mem-info{flex:1;min-width:0}
.mem-name{font-size:13px;font-weight:600;color:var(--text-normal);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mem-meta{font-size:11px;color:var(--text-muted)}

/* CHANNEL LIST */
.ch-list{max-height:400px;overflow-y:auto}
.ch-item{display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--bg-secondary);border-radius:6px;margin-bottom:4px;transition:0.15s}
.ch-item:hover{background:rgba(255,255,255,0.04)}
.ch-icon{font-size:16px;color:var(--text-muted)}
.ch-name{flex:1;font-size:13px;color:var(--text-normal)}
.ch-cat{font-size:11px;color:var(--text-faded)}

/* COLOR PICKER */
.color-input{height:40px;cursor:pointer;border-radius:4px}

/* SEARCH */
.search-wrap{position:relative;margin-bottom:16px}
.search-input{width:100%;padding:10px 16px 10px 40px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;color:var(--text-normal);font-size:14px;font-family:inherit}
.search-input:focus{outline:none;border-color:var(--brand)}
.search-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--text-muted);font-size:14px}

/* RESPONSIVE */
@media(max-width:768px){
.sidebar{width:60px}
.sb-title,.sb-username,.sb-status,.nav-link span,.nav-sec-title,.sb-user{display:none}
.main{margin-left:60px}
.stats-grid{grid-template-columns:repeat(2,1fr)}
.frow{grid-template-columns:1fr}
.feat-grid{grid-template-columns:1fr}
.login-feats{grid-template-columns:1fr}
}
</style>
"""

# ============ JS ============
JS = """
<script>
function toast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show ' + (type || '');
    setTimeout(() => t.classList.remove('show'), 3000);
}
function switchTab(name, el) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel-content').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('tab-' + name).classList.add('active');
}
function toggleFeature(gid, key, el) {
    fetch('/api/toggle/' + gid + '/' + key, {method:'POST'})
    .then(r => r.json()).then(d => {
        if (d.success) { el.classList.toggle('on'); toast('✅ Updated!', 'success'); }
        else toast('❌ Failed', 'error');
    });
}
function updateSetting(gid, key, val) {
    fetch('/api/setting/' + gid + '/' + key, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({value: val})
    }).then(r => r.json()).then(d => {
        if (d.success) toast('✅ Saved!', 'success');
    });
}
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function addCommand(gid) {
    const t = document.getElementById('cc-trig').value;
    const r = document.getElementById('cc-resp').value;
    if (!t || !r) { toast('Fill both fields!', 'error'); return; }
    fetch('/api/custom/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({trigger:t, response:r})
    }).then(res => res.json()).then(d => {
        if (d.success) { toast('✅ Added!', 'success'); setTimeout(() => location.reload(), 500); }
    });
}
function delCommand(gid, trig) {
    if (!confirm('Delete "' + trig + '"?')) return;
    fetch('/api/custom/' + gid + '/' + encodeURIComponent(trig), {method:'DELETE'})
    .then(r => r.json()).then(d => { if (d.success) { toast('Deleted!', 'success'); setTimeout(() => location.reload(), 500); }});
}
function addWord(gid) {
    const w = document.getElementById('wf-word').value;
    if (!w) return;
    fetch('/api/word/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({word:w})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('Added!', 'success'); setTimeout(() => location.reload(), 500); }
    });
}
function delWord(gid, w) {
    fetch('/api/word/' + gid + '/' + encodeURIComponent(w), {method:'DELETE'})
    .then(r => r.json()).then(d => { if (d.success) { toast('Removed!', 'success'); setTimeout(() => location.reload(), 500); }});
}
function clearUserWarns(gid, uid) {
    if (!confirm('Clear all warnings?')) return;
    fetch('/api/clearwarns/' + gid + '/' + uid, {method:'POST'})
    .then(r => r.json()).then(d => { if (d.success) { toast('Cleared!', 'success'); setTimeout(() => location.reload(), 500); }});
}
function sendAnnounce(gid) {
    const ch = document.getElementById('ann-ch').value;
    const msg = document.getElementById('ann-msg').value;
    const title = document.getElementById('ann-title').value;
    if (!ch || !msg) { toast('Fill required fields!', 'error'); return; }
    fetch('/api/announce/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({channel:ch, message:msg, title:title})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('📤 Sent!', 'success'); document.getElementById('ann-msg').value = ''; document.getElementById('ann-title').value = ''; }
        else toast('❌ ' + (d.error || 'Failed'), 'error');
    });
}
function sendDM(gid) {
    const uid = document.getElementById('dm-uid').value;
    const msg = document.getElementById('dm-msg').value;
    if (!uid || !msg) { toast('Fill both!', 'error'); return; }
    fetch('/api/dm/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({user_id:uid, message:msg})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('📨 DM sent!', 'success'); document.getElementById('dm-msg').value = ''; }
        else toast('❌ ' + (d.error || 'Failed'), 'error');
    });
}
function createChannel(gid) {
    const name = document.getElementById('ch-name').value;
    const cat = document.getElementById('ch-cat').value;
    if (!name) return;
    fetch('/api/channel/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name:name, category:cat})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('✅ Created!', 'success'); setTimeout(() => location.reload(), 500); }
        else toast('❌ ' + (d.error || 'Failed'), 'error');
    });
}
function deleteChannel(gid, chname) {
    if (!confirm('Delete #' + chname + '?')) return;
    fetch('/api/channel/' + gid + '/' + encodeURIComponent(chname), {method:'DELETE'})
    .then(r => r.json()).then(d => { if (d.success) { toast('Deleted!', 'success'); setTimeout(() => location.reload(), 500); }});
}
function createRole(gid) {
    const name = document.getElementById('rl-name').value;
    const color = document.getElementById('rl-color').value;
    if (!name) return;
    fetch('/api/role/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name:name, color:color})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('✅ Created!', 'success'); setTimeout(() => location.reload(), 500); }
    });
}
function deleteRole(gid, name) {
    if (!confirm('Delete role "' + name + '"?')) return;
    fetch('/api/role/' + gid + '/' + encodeURIComponent(name), {method:'DELETE'})
    .then(r => r.json()).then(d => { if (d.success) { toast('Deleted!', 'success'); setTimeout(() => location.reload(), 500); }});
}
function createCategory(gid) {
    const name = document.getElementById('cat-name').value;
    if (!name) return;
    fetch('/api/category/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name:name})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('✅ Created!', 'success'); setTimeout(() => location.reload(), 500); }
    });
}
function userAction(gid, uid, action) {
    const reason = prompt('Reason:');
    if (!reason) return;
    const duration = action === 'mute' ? prompt('Duration in minutes:', '10') : null;
    fetch('/api/useraction/' + gid + '/' + uid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({action:action, reason:reason, duration:duration})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('✅ Done!', 'success'); setTimeout(() => location.reload(), 500); }
        else toast('❌ ' + (d.error || 'Failed'), 'error');
    });
}
function createGiveaway(gid) {
    const prize = document.getElementById('gw-prize').value;
    const ch = document.getElementById('gw-ch').value;
    const dur = document.getElementById('gw-dur').value;
    const wins = document.getElementById('gw-wins').value;
    if (!prize || !ch) { toast('Fill prize and channel!', 'error'); return; }
    fetch('/api/giveaway/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({prize:prize, channel:ch, duration:dur, winners:wins})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('🎉 Started!', 'success'); setTimeout(() => location.reload(), 500); }
    });
}
function createPoll(gid) {
    const q = document.getElementById('pl-q').value;
    const ch = document.getElementById('pl-ch').value;
    const opts = document.getElementById('pl-opts').value;
    if (!q || !ch || !opts) { toast('Fill all fields!', 'error'); return; }
    fetch('/api/poll/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({question:q, channel:ch, options:opts.split(',')})
    }).then(r => r.json()).then(d => {
        if (d.success) { toast('📊 Posted!', 'success'); }
    });
}
function changePersonality(gid) {
    const p = document.getElementById('personality-sel').value;
    fetch('/api/personality/' + gid, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({personality:p})
    }).then(r => r.json()).then(d => {
        if (d.success) toast('✅ Personality changed!', 'success');
    });
}
function searchMembers() {
    const q = document.getElementById('mem-search').value.toLowerCase();
    document.querySelectorAll('.mem-card').forEach(c => {
        const name = c.dataset.name.toLowerCase();
        c.style.display = name.includes(q) ? 'flex' : 'none';
    });
}
</script>
"""

# ============ TEMPLATES ============
def base_html(content, title="Dashboard"):
    return f"""<!DOCTYPE html>
<html><head><title>{title} - SentinelMod</title>
{CSS}
</head><body>
<div id="toast" class="toast"></div>
{content}
{JS}
</body></html>"""

def login_page():
    return base_html(f"""
<div class="login-page">
<div class="login-card">
<div class="login-logo">🛡️</div>
<h1 class="login-title">SentinelMod</h1>
<p class="login-subtitle">The ultimate AI-powered Discord moderation and management dashboard. Control everything from one beautiful place.</p>
<a href="/login" class="login-btn">🚀 Login with Discord</a>
<div class="login-feats">
<div class="lf"><div class="lf-icon">🤖</div><div class="lf-title">AI Powered</div><div class="lf-desc">Smart moderation</div></div>
<div class="lf"><div class="lf-icon">⚡</div><div class="lf-title">Instant</div><div class="lf-desc">Real-time updates</div></div>
<div class="lf"><div class="lf-icon">🎮</div><div class="lf-title">100+ Features</div><div class="lf-desc">Everything you need</div></div>
</div>
</div>
</div>""", "Login")

def sidebar_html(user, active_page="home", guild_id=None):
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png"
    home_active = "active" if active_page == "home" else ""

    nav_items = ""
    if guild_id:
        items = [
            ("overview", "📊", "Overview"),
            ("features", "⚙️", "Features"),
            ("moderation", "🛡️", "Moderation"),
            ("members", "👥", "Members"),
            ("channels", "💬", "Channels"),
            ("roles", "🎭", "Roles"),
            ("warnings", "⚠️", "Warnings"),
            ("commands", "⚡", "Commands"),
            ("filters", "🔤", "Word Filters"),
            ("analytics", "📈", "Analytics"),
            ("leaderboard", "🏆", "Leaderboards"),
            ("events", "🎉", "Events"),
            ("personality", "🎭", "AI Personality"),
            ("announce", "📢", "Announcements"),
            ("settings", "🔧", "Settings"),
        ]
        for key, icon, label in items:
            active = "active" if active_page == key else ""
            nav_items += f'<a class="nav-link {active}" onclick="document.querySelector(\'.tab[data-tab=\\'{key}\\']\').click()"><span class="nav-icon">{icon}</span><span>{label}</span></a>'

    return f"""
<aside class="sidebar">
<div class="sb-head">
<div class="sb-logo">🛡️</div>
<div class="sb-title">SentinelMod</div>
</div>
<div class="sb-nav">
<div class="nav-sec">
<div class="nav-sec-title">Main</div>
<a href="/" class="nav-link {home_active}"><span class="nav-icon">🏠</span><span>Home</span></a>
</div>
{f'<div class="nav-sec"><div class="nav-sec-title">Server</div>{nav_items}</div>' if guild_id else ''}
</div>
<div class="sb-foot">
<img src="{avatar}" class="sb-avatar">
<div class="sb-user">
<div class="sb-username">{user['username']}</div>
<div class="sb-status">● Online</div>
</div>
<a href="/logout" class="sb-logout" title="Logout">⏻</a>
</div>
</aside>"""

# ============ ROUTES ============
@app.route("/")
def index():
    if "user" not in session:
        return login_page()

    user = session["user"]
    try:
        headers = {"Authorization": f"Bearer {session['access_token']}"}
        r = requests.get("https://discord.com/api/users/@me/guilds", headers=headers, timeout=10)
        user_guilds = r.json() if r.status_code == 200 else []
    except:
        user_guilds = []

    bot_guild_ids = [g.id for g in BOT_INSTANCE.guilds] if BOT_INSTANCE else []
    managable = []
    for ug in user_guilds:
        try:
            if int(ug.get("permissions", 0)) & 0x8:
                managable.append({**ug, "has_bot": int(ug["id"]) in bot_guild_ids})
        except:
            pass

    cards = ""
    for g in managable[:50]:
        icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None
        icon_html = f'<img src="{icon_url}">' if icon_url else g['name'][0].upper()
        member_count = 0
        if g["has_bot"] and BOT_INSTANCE:
            guild_obj = BOT_INSTANCE.get_guild(int(g['id']))
            if guild_obj:
                member_count = guild_obj.member_count

        if g["has_bot"]:
            cards += f'''
<div class="srv">
<div class="srv-head">
<div class="srv-icon">{icon_html}</div>
<div>
<div class="srv-name">{g['name']}</div>
<div class="srv-info">{member_count} members · <span class="tag tag-online">● Online</span></div>
</div>
</div>
<a href="/server/{g['id']}" class="btn btn-brand" style="width:100%;justify-content:center;">⚙️ Manage</a>
</div>'''
        else:
            invite = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands&guild_id={g['id']}"
            cards += f'''
<div class="srv">
<div class="srv-head">
<div class="srv-icon">{icon_html}</div>
<div>
<div class="srv-name">{g['name']}</div>
<div class="srv-info"><span class="tag" style="background:rgba(255,255,255,0.05);color:var(--text-muted);">○ Not added</span></div>
</div>
</div>
<a href="{invite}" target="_blank" class="btn btn-green" style="width:100%;justify-content:center;">➕ Add Bot</a>
</div>'''

    total_servers = len([m for m in managable if m["has_bot"]])
    total_members = sum(BOT_INSTANCE.get_guild(int(m["id"])).member_count for m in managable if m["has_bot"] and BOT_INSTANCE and BOT_INSTANCE.get_guild(int(m["id"])))

    content = f"""
<div class="app">
{sidebar_html(user, "home")}
<div class="main">
<div class="topbar">
<div class="crumb"><b>🏠 Home</b></div>
</div>
<div class="content">
<h1 style="font-size:24px;font-weight:800;color:var(--header-primary);margin-bottom:8px;">Welcome back, {user['username']}!</h1>
<p style="color:var(--text-muted);margin-bottom:24px;">You're managing {total_servers} server(s) with SentinelMod.</p>

<div class="stats-grid">
<div class="stat-card"><div class="stat-icon icon-brand">🏠</div><div class="stat-value">{total_servers}</div><div class="stat-label">Active Servers</div></div>
<div class="stat-card"><div class="stat-icon icon-green">👥</div><div class="stat-value">{total_members:,}</div><div class="stat-label">Total Members</div></div>
<div class="stat-card"><div class="stat-icon icon-yellow">⚙️</div><div class="stat-value">{len(managable)}</div><div class="stat-label">Manageable</div></div>
<div class="stat-card"><div class="stat-icon icon-red">🤖</div><div class="stat-value">99.9%</div><div class="stat-label">Uptime</div></div>
</div>

<div class="panel">
<div class="panel-head"><div class="panel-title">Your Servers</div></div>
<div class="panel-body">
<div class="servers">{cards if cards else '<div class="empty"><div class="empty-icon">🔍</div><div class="empty-title">No servers found</div><div class="empty-desc">You need admin permissions in a Discord server</div></div>'}</div>
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
    data = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return f"Error: {r.text}"
    token = r.json()["access_token"]
    session["access_token"] = token
    ur = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token}"})
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
        return "Bot not in this server!"

    s = get_guild_settings(guild_id)
    if not s:
        s = {}

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (guild_id,))
    warns_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM mod_actions WHERE guild_id=?", (guild_id,))
    actions_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM custom_commands WHERE guild_id=?", (guild_id,))
    customs_count = c.fetchone()[0]
    c.execute("SELECT * FROM warnings WHERE guild_id=? ORDER BY timestamp DESC LIMIT 30", (guild_id,))
    warns = c.fetchall()
    c.execute("SELECT * FROM mod_actions WHERE guild_id=? ORDER BY timestamp DESC LIMIT 30", (guild_id,))
    actions = c.fetchall()
    c.execute("SELECT * FROM custom_commands WHERE guild_id=?", (guild_id,))
    customs = c.fetchall()
    c.execute("SELECT word FROM word_filters WHERE guild_id=?", (guild_id,))
    words = c.fetchall()
    c.execute("SELECT user_id, message_count FROM message_stats WHERE guild_id=? ORDER BY message_count DESC LIMIT 20", (guild_id,))
    top_users = c.fetchall()
    try:
        c.execute("SELECT user_id, rep FROM reputation WHERE guild_id=? ORDER BY rep DESC LIMIT 10", (guild_id,))
        top_rep = c.fetchall()
    except:
        top_rep = []
    try:
        c.execute("SELECT * FROM giveaways WHERE guild_id=? AND active=1", (guild_id,))
        giveaways = c.fetchall()
    except:
        giveaways = []
    try:
        c.execute("SELECT * FROM reminders WHERE guild_id=? AND active=1", (guild_id,))
        reminders = c.fetchall()
    except:
        reminders = []
    conn.close()

    # Features
    features = [
        ("welcome_enabled", "👋", "Welcome Messages", "Greet new members"),
        ("anti_nuke_enabled", "💣", "Anti-Nuke", "Stop mass destruction"),
        ("invite_block", "🚫", "Block Invites", "Block discord.gg links"),
        ("link_scan", "🔗", "Link Scanner", "Detect phishing links"),
        ("slowmode_ai", "🐌", "AI Slowmode", "Auto slow heated chats"),
        ("pre_conflict", "⚠️", "Pre-Conflict AI", "Detect arguments early"),
        ("caps_filter", "🔤", "Caps Filter", "Block excessive caps"),
        ("mention_spam", "📢", "Mention Spam", "Block mass mentions"),
        ("emoji_spam", "😂", "Emoji Spam", "Block emoji floods"),
        ("zalgo_filter", "🌀", "Zalgo Filter", "Block weird text"),
        ("phone_filter", "📞", "Phone Filter", "Block phone numbers"),
        ("email_filter", "📧", "Email Filter", "Block email addresses"),
        ("scam_filter", "💸", "Scam Filter", "Detect scam patterns"),
        ("fake_nitro_filter", "💎", "Fake Nitro", "Block nitro scams"),
        ("token_filter", "🔑", "Token Grabber", "Block token grabbers"),
        ("anti_advertisement", "📣", "Anti-Ads", "Block advertisements"),
        ("everyone_block", "🔕", "@everyone Block", "Block @everyone usage"),
        ("nsfw_text_filter", "🔞", "NSFW Filter", "Block NSFW text"),
        ("unicode_filter", "🔠", "Unicode Bypass", "Detect unicode tricks"),
        ("file_spam_filter", "📁", "File Spam", "Block file spam"),
    ]
    feat_html = ""
    for key, icon, name, desc in features:
        val = s.get(key, 0)
        feat_html += f'''
<div class="feat">
<div class="feat-info">
<div class="feat-icon">{icon}</div>
<div class="feat-text"><div class="feat-name">{name}</div><div class="feat-desc">{desc}</div></div>
</div>
<div class="switch {'on' if val else ''}" onclick="toggleFeature('{guild_id}', '{key}', this)"><div class="switch-dot"></div></div>
</div>'''

    # Warnings list
    warns_html = ""
    for w in warns:
        m = guild.get_member(int(w["user_id"]))
        name = m.display_name if m else f"User {w['user_id']}"
        avatar = m.display_avatar.url if m else None
        av_html = f'<img src="{avatar}">' if avatar else name[0].upper()
        warns_html += f'''
<div class="row">
<div class="row-avatar">{av_html}</div>
<div class="row-info"><div class="row-name">{name}</div><div class="row-detail">{w['reason']}</div><div class="row-meta">{w['timestamp'][:16]}</div></div>
<span class="tag tag-{w['severity']}">{w['severity']}</span>
<button class="btn btn-sm btn-ghost" onclick="clearUserWarns('{guild_id}', '{w['user_id']}')">Clear</button>
</div>'''

    # Actions list
    actions_html = ""
    for a in actions:
        m = guild.get_member(int(a["user_id"]))
        mod = guild.get_member(int(a["mod_id"]))
        name = m.display_name if m else "Unknown"
        mod_name = mod.display_name if mod else ("Bot" if BOT_INSTANCE and a["mod_id"] == str(BOT_INSTANCE.user.id) else "Unknown")
        actions_html += f'''
<div class="row">
<div class="row-avatar">{name[0].upper()}</div>
<div class="row-info"><div class="row-name">{name} <span style="color:var(--brand);font-weight:700;">[{a['action']}]</span></div><div class="row-detail">{a['reason']} · by {mod_name}</div><div class="row-meta">{a['timestamp'][:16]}</div></div>
</div>'''

    # Members
    mem_html = ""
    for m in list(guild.members)[:200]:
        if m.bot:
            continue
        avatar = m.display_avatar.url
        roles_str = ", ".join([r.name for r in m.roles if r.name != "@everyone"][:3]) or "No roles"
        mem_html += f'''
<div class="mem-card" data-name="{m.name}">
<div class="mem-avatar"><img src="{avatar}"></div>
<div class="mem-info"><div class="mem-name">{m.display_name}</div><div class="mem-meta">{roles_str}</div></div>
<div style="display:flex;gap:4px;">
<button class="btn btn-sm btn-ghost" title="Warn" onclick="userAction('{guild_id}','{m.id}','warn')">⚠️</button>
<button class="btn btn-sm btn-ghost" title="Mute" onclick="userAction('{guild_id}','{m.id}','mute')">🔇</button>
<button class="btn btn-sm btn-red" title="Ban" onclick="userAction('{guild_id}','{m.id}','ban')">🔨</button>
</div>
</div>'''

    # Channels
    ch_html = ""
    for ch in guild.text_channels:
        cat_name = ch.category.name if ch.category else "No category"
        ch_html += f'''
<div class="ch-item">
<span class="ch-icon">#</span>
<span class="ch-name">{ch.name}</span>
<span class="ch-cat">{cat_name}</span>
<button class="btn btn-sm btn-red" onclick="deleteChannel('{guild_id}', '{ch.name}')">Delete</button>
</div>'''

    # Roles
    roles_html = ""
    for r in guild.roles:
        if r.name == "@everyone":
            continue
        color_dot = f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{str(r.color)};margin-right:8px;"></span>'
        roles_html += f'''
<div class="ch-item">
{color_dot}
<span class="ch-name">{r.name}</span>
<span class="ch-cat">{len(r.members)} members</span>
<button class="btn btn-sm btn-red" onclick="deleteRole('{guild_id}', '{r.name}')">Delete</button>
</div>'''

    # Custom commands
    cmd_html = ""
    for cc in customs:
        cmd_html += f'''
<div class="cmd-row">
<span class="cmd-trigger">{cc['trigger_word']}</span>
<span class="cmd-resp">{cc['response'][:80]}</span>
<button class="btn btn-sm btn-red" onclick="delCommand('{guild_id}', '{cc['trigger_word']}')">×</button>
</div>'''

    # Words
    words_html = ""
    for w in words:
        words_html += f'''
<div class="cmd-row">
<span class="cmd-trigger">{w['word']}</span>
<button class="btn btn-sm btn-red" onclick="delWord('{guild_id}', '{w['word']}')">×</button>
</div>'''

    # Top users
    top_html = ""
    for i, r in enumerate(top_users[:10], 1):
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "Unknown"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        top_html += f'''
<div class="row">
<div style="font-size:20px;width:36px;text-align:center;">{medal}</div>
<div class="row-info"><div class="row-name">{name}</div><div class="row-detail">{r['message_count']} messages</div></div>
</div>'''

    # Rep
    rep_html = ""
    for i, r in enumerate(top_rep, 1):
        m = guild.get_member(int(r["user_id"]))
        name = m.display_name if m else "Unknown"
        rep_html += f'''
<div class="row">
<div class="row-avatar">{name[0].upper()}</div>
<div class="row-info"><div class="row-name">{name}</div><div class="row-detail">⭐ {r['rep']} reputation</div></div>
</div>'''

    # Giveaways
    gw_html = ""
    for gw in giveaways:
        gw_html += f'<div class="row"><div style="font-size:24px;">🎉</div><div class="row-info"><div class="row-name">{gw["prize"]}</div><div class="row-detail">{gw["winners"]} winner(s) · Ends {gw["end_time"][:16]}</div></div></div>'

    # Reminders
    rem_html = ""
    for r in reminders:
        m = guild.get_member(int(r["user_id"]))
        nm = m.display_name if m else "?"
        rem_html += f'<div class="row"><div style="font-size:24px;">⏰</div><div class="row-info"><div class="row-name">{nm}: {r["reminder"]}</div><div class="row-detail">At {r["remind_time"][:16]}</div></div></div>'

    # Channel options
    ch_opts = "".join([f'<option value="{ch.name}">#{ch.name}</option>' for ch in guild.text_channels[:100]])
    cat_opts = '<option value="">No category</option>' + "".join([f'<option value="{c.name}">{c.name}</option>' for c in guild.categories])

    # Personalities
    personalities_list = ["friendly","sarcastic","serious","chaotic","pirate","medieval","robot","therapist","villain","hype","philosopher","caveman","shakespeare","surfer","anime","cowboy","british","australian","valley_girl","gen_z","yoda","jarvis","deadpool","sherlock","gandalf","tony_stark","groot","gollum","darth_vader","michael_scott","dwight_schrute","motivational","pessimist","optimist","ninja","samurai","fairy","vampire","oracle","mad_hatter","wizard","superhero","gamer","boomer","professor","chef","detective","alien","time_traveler","ghost","dragon","nerd"]
    current_pers = s.get('personality', 'default')
    pers_opts = "".join([f'<option value="{p}" {"selected" if p == current_pers else ""}>{p.replace("_"," ").title()}</option>' for p in personalities_list])

    server_icon = f"https://cdn.discordapp.com/icons/{guild.id}/{guild.icon}.png" if guild.icon else None
    icon_html = f'<img src="{server_icon}">' if server_icon else guild.name[0].upper()

    content = f"""
<div class="app">
{sidebar_html(session["user"], "overview", guild_id)}
<div class="main">
<div class="topbar">
<div class="crumb"><a href="/">Home</a> <span class="crumb-sep">›</span> <b>{guild.name}</b></div>
</div>
<div class="content">

<div style="display:flex;align-items:center;gap:16px;margin-bottom:24px;">
<div class="srv-icon" style="width:64px;height:64px;font-size:28px;">{icon_html}</div>
<div>
<h1 style="font-size:24px;font-weight:800;color:var(--header-primary);">{guild.name}</h1>
<p style="color:var(--text-muted);font-size:14px;">{guild.member_count} members · {len(guild.text_channels)} channels · {len(guild.roles)} roles</p>
</div>
</div>

<div class="stats-grid">
<div class="stat-card"><div class="stat-icon icon-brand">👥</div><div class="stat-value">{guild.member_count:,}</div><div class="stat-label">Members</div></div>
<div class="stat-card"><div class="stat-icon icon-yellow">⚠️</div><div class="stat-value">{warns_count}</div><div class="stat-label">Warnings</div></div>
<div class="stat-card"><div class="stat-icon icon-red">🔨</div><div class="stat-value">{actions_count}</div><div class="stat-label">Mod Actions</div></div>
<div class="stat-card"><div class="stat-icon icon-green">⚡</div><div class="stat-value">{customs_count}</div><div class="stat-label">Custom Commands</div></div>
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
<button class="tab" data-tab="events" onclick="switchTab('events',this)">🎉 Events</button>
<button class="tab" data-tab="personality" onclick="switchTab('personality',this)">🎭 AI Personality</button>
<button class="tab" data-tab="announce" onclick="switchTab('announce',this)">📢 Announce</button>
<button class="tab" data-tab="settings" onclick="switchTab('settings',this)">🔧 Settings</button>
</div>

<div id="tab-overview" class="panel-content active">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
<div class="panel"><div class="panel-head"><div class="panel-title">Recent Warnings</div></div><div class="panel-body">{warns_html if warns_html else '<div class="empty"><div class="empty-icon">✅</div><div class="empty-title">All clean!</div></div>'}</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">Recent Actions</div></div><div class="panel-body">{actions_html if actions_html else '<div class="empty"><div class="empty-icon">📋</div><div class="empty-title">No actions yet</div></div>'}</div></div>
</div>
</div>

<div id="tab-features" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Bot Features ({len(features)} available)</div></div><div class="panel-body"><div class="feat-grid">{feat_html}</div></div></div>
</div>

<div id="tab-moderation" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Moderation Settings</div></div><div class="panel-body">
<div class="frow">
<div class="fg"><label class="flbl">Warnings → Mute</label><input type="number" class="finp" value="{s.get('warn_mute', 3)}" onchange="updateSetting('{guild_id}','warn_mute',this.value)"><div class="fhint">Auto-mute after this many warnings</div></div>
<div class="fg"><label class="flbl">Warnings → Ban</label><input type="number" class="finp" value="{s.get('warn_ban', 5)}" onchange="updateSetting('{guild_id}','warn_ban',this.value)"><div class="fhint">Auto-ban after this many warnings</div></div>
</div>
<div class="frow">
<div class="fg"><label class="flbl">Mute Duration (min)</label><input type="number" class="finp" value="{s.get('mute_duration', 10)}" onchange="updateSetting('{guild_id}','mute_duration',this.value)"></div>
<div class="fg"><label class="flbl">AI Sensitivity</label><input type="number" step="0.1" min="0" max="1" class="finp" value="{s.get('ai_sensitivity', 0.7)}" onchange="updateSetting('{guild_id}','ai_sensitivity',this.value)"><div class="fhint">0.0 = loose, 1.0 = strict</div></div>
</div>
<div class="frow">
<div class="fg"><label class="flbl">Spam Message Limit</label><input type="number" class="finp" value="{s.get('spam_limit', 5)}" onchange="updateSetting('{guild_id}','spam_limit',this.value)"></div>
<div class="fg"><label class="flbl">Spam Window (sec)</label><input type="number" class="finp" value="{s.get('spam_window', 5)}" onchange="updateSetting('{guild_id}','spam_window',this.value)"></div>
</div>
<div class="frow">
<div class="fg"><label class="flbl">Raid Join Limit</label><input type="number" class="finp" value="{s.get('raid_limit', 10)}" onchange="updateSetting('{guild_id}','raid_limit',this.value)"></div>
<div class="fg"><label class="flbl">Min Account Age (days)</label><input type="number" class="finp" value="{s.get('min_account_age', 7)}" onchange="updateSetting('{guild_id}','min_account_age',this.value)"></div>
</div>
</div></div>
</div>

<div id="tab-members" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Members ({guild.member_count})</div></div><div class="panel-body">
<div class="search-wrap"><span class="search-icon">🔍</span><input type="text" id="mem-search" class="search-input" placeholder="Search members..." oninput="searchMembers()"></div>
<div class="mem-grid">{mem_html}</div>
</div></div>
</div>

<div id="tab-channels" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Create Channel</div></div><div class="panel-body">
<div class="frow">
<div class="fg"><label class="flbl">Channel Name</label><input type="text" id="ch-name" class="finp" placeholder="gaming-chat"></div>
<div class="fg"><label class="flbl">Category</label><select id="ch-cat" class="fsel">{cat_opts}</select></div>
</div>
<button class="btn btn-brand" onclick="createChannel('{guild_id}')">➕ Create Channel</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">All Channels ({len(guild.text_channels)})</div></div><div class="panel-body">{ch_html}</div></div>
</div>

<div id="tab-roles" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Create Role</div></div><div class="panel-body">
<div class="frow">
<div class="fg"><label class="flbl">Role Name</label><input type="text" id="rl-name" class="finp" placeholder="VIP"></div>
<div class="fg"><label class="flbl">Color</label><input type="color" id="rl-color" class="finp color-input" value="#5865f2"></div>
</div>
<button class="btn btn-brand" onclick="createRole('{guild_id}')">➕ Create Role</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">Create Category</div></div><div class="panel-body">
<div class="fg"><label class="flbl">Category Name</label><input type="text" id="cat-name" class="finp" placeholder="Gaming Zone"></div>
<button class="btn btn-brand" onclick="createCategory('{guild_id}')">➕ Create Category</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">All Roles ({len(guild.roles)-1})</div></div><div class="panel-body">{roles_html}</div></div>
</div>

<div id="tab-warnings" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">All Warnings ({warns_count})</div></div><div class="panel-body">{warns_html if warns_html else '<div class="empty"><div class="empty-icon">✅</div><div class="empty-title">No warnings!</div></div>'}</div></div>
</div>

<div id="tab-commands" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Add Custom Command</div></div><div class="panel-body">
<div class="frow">
<div class="fg"><label class="flbl">Trigger</label><input type="text" id="cc-trig" class="finp" placeholder="hello"></div>
<div class="fg"><label class="flbl">Response</label><input type="text" id="cc-resp" class="finp" placeholder="Hi there!"></div>
</div>
<button class="btn btn-brand" onclick="addCommand('{guild_id}')">➕ Add</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">Custom Commands ({customs_count})</div></div><div class="panel-body">{cmd_html if cmd_html else '<div class="empty"><div class="empty-icon">⚡</div><div class="empty-title">No commands</div></div>'}</div></div>
</div>

<div id="tab-filters" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Add Word Filter</div></div><div class="panel-body">
<div style="display:flex;gap:10px;">
<input type="text" id="wf-word" class="finp" placeholder="Enter word..." style="flex:1;">
<button class="btn btn-brand" onclick="addWord('{guild_id}')">➕ Add</button>
</div>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">Filtered Words</div></div><div class="panel-body">{words_html if words_html else '<div class="empty"><div class="empty-icon">🔤</div><div class="empty-title">No filtered words</div></div>'}</div></div>
</div>

<div id="tab-analytics" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">Server Overview</div></div><div class="panel-body">
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
<div><div class="stat-value" style="color:var(--brand);">{guild.member_count}</div><div class="stat-label">Total Members</div></div>
<div><div class="stat-value" style="color:var(--green);">{sum(1 for m in guild.members if not m.bot)}</div><div class="stat-label">Humans</div></div>
<div><div class="stat-value" style="color:var(--yellow);">{sum(1 for m in guild.members if m.bot)}</div><div class="stat-label">Bots</div></div>
</div>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">Stats</div></div><div class="panel-body">
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
<div><div class="stat-value">{len(guild.text_channels)}</div><div class="stat-label">Text Channels</div></div>
<div><div class="stat-value">{len(guild.voice_channels)}</div><div class="stat-label">Voice Channels</div></div>
<div><div class="stat-value">{len(guild.categories)}</div><div class="stat-label">Categories</div></div>
<div><div class="stat-value">{len(guild.roles)}</div><div class="stat-label">Roles</div></div>
</div>
</div></div>
</div>

<div id="tab-leaderboard" class="panel-content">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
<div class="panel"><div class="panel-head"><div class="panel-title">💬 Most Active</div></div><div class="panel-body">{top_html if top_html else '<div class="empty"><div class="empty-icon">📊</div><div class="empty-title">No data</div></div>'}</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">⭐ Top Reputation</div></div><div class="panel-body">{rep_html if rep_html else '<div class="empty"><div class="empty-icon">⭐</div><div class="empty-title">No rep yet</div></div>'}</div></div>
</div>
</div>

<div id="tab-events" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">🎉 Create Giveaway</div></div><div class="panel-body">
<div class="frow">
<div class="fg"><label class="flbl">Prize</label><input type="text" id="gw-prize" class="finp" placeholder="Discord Nitro"></div>
<div class="fg"><label class="flbl">Channel</label><select id="gw-ch" class="fsel">{ch_opts}</select></div>
</div>
<div class="frow">
<div class="fg"><label class="flbl">Duration (min)</label><input type="number" id="gw-dur" class="finp" value="60"></div>
<div class="fg"><label class="flbl">Winners</label><input type="number" id="gw-wins" class="finp" value="1"></div>
</div>
<button class="btn btn-brand" onclick="createGiveaway('{guild_id}')">🎉 Start Giveaway</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">Active Giveaways</div></div><div class="panel-body">{gw_html if gw_html else '<div class="empty"><div class="empty-icon">🎁</div><div class="empty-title">No active giveaways</div></div>'}</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">📊 Create Poll</div></div><div class="panel-body">
<div class="fg"><label class="flbl">Question</label><input type="text" id="pl-q" class="finp" placeholder="Best pizza topping?"></div>
<div class="frow">
<div class="fg"><label class="flbl">Channel</label><select id="pl-ch" class="fsel">{ch_opts}</select></div>
<div class="fg"><label class="flbl">Options (comma separated)</label><input type="text" id="pl-opts" class="finp" placeholder="Cheese, Pepperoni, Mushroom"></div>
</div>
<button class="btn btn-brand" onclick="createPoll('{guild_id}')">📊 Create Poll</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">⏰ Pending Reminders</div></div><div class="panel-body">{rem_html if rem_html else '<div class="empty"><div class="empty-icon">⏰</div><div class="empty-title">No reminders</div></div>'}</div></div>
</div>

<div id="tab-personality" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">🎭 AI Personality</div></div><div class="panel-body">
<p style="color:var(--text-muted);margin-bottom:16px;">Change how SentinelMod talks to your server members!</p>
<div class="fg"><label class="flbl">Personality</label>
<select id="personality-sel" class="fsel">{pers_opts}</select>
</div>
<button class="btn btn-brand" onclick="changePersonality('{guild_id}')">✅ Apply</button>
</div></div>
</div>

<div id="tab-announce" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">📢 Send Announcement</div></div><div class="panel-body">
<div class="fg"><label class="flbl">Channel</label><select id="ann-ch" class="fsel">{ch_opts}</select></div>
<div class="fg"><label class="flbl">Title (optional)</label><input type="text" id="ann-title" class="finp" placeholder="Important Update"></div>
<div class="fg"><label class="flbl">Message</label><textarea id="ann-msg" class="ftxa" placeholder="Type your announcement..."></textarea></div>
<button class="btn btn-brand" onclick="sendAnnounce('{guild_id}')">📤 Send Announcement</button>
</div></div>
<div class="panel"><div class="panel-head"><div class="panel-title">📨 Send DM to User</div></div><div class="panel-body">
<div class="fg"><label class="flbl">User ID</label><input type="text" id="dm-uid" class="finp" placeholder="123456789012345678"></div>
<div class="fg"><label class="flbl">Message</label><textarea id="dm-msg" class="ftxa" placeholder="Your DM..."></textarea></div>
<button class="btn btn-brand" onclick="sendDM('{guild_id}')">📨 Send DM</button>
</div></div>
</div>

<div id="tab-settings" class="panel-content">
<div class="panel"><div class="panel-head"><div class="panel-title">General Settings</div></div><div class="panel-body">
<div class="fg"><label class="flbl">Mod Role Name</label><input type="text" class="finp" value="{s.get('mod_role_name', 'Sentinel-Mod')}" onchange="updateSetting('{guild_id}','mod_role_name',this.value)"></div>
<div class="frow">
<div class="fg"><label class="flbl">Log Channel</label><input type="text" class="finp" value="{s.get('log_channel', 'sentinel-logs')}" onchange="updateSetting('{guild_id}','log_channel',this.value)"></div>
<div class="fg"><label class="flbl">Raid Channel</label><input type="text" class="finp" value="{s.get('raid_channel', 'sentinel-raid-alerts')}" onchange="updateSetting('{guild_id}','raid_channel',this.value)"></div>
</div>
<div class="fg"><label class="flbl">Welcome Channel</label><input type="text" class="finp" value="{s.get('welcome_channel', 'welcome')}" onchange="updateSetting('{guild_id}','welcome_channel',this.value)"></div>
</div></div>
</div>

</div>
</div>
</div>"""
    return base_html(content, guild.name)

# ============ API ROUTES ============
@app.route("/api/toggle/<gid>/<feat>", methods=["POST"])
def api_toggle(gid, feat):
    if "user" not in session:
        return jsonify({"success": False})
    valid = ["welcome_enabled","anti_nuke_enabled","invite_block","link_scan","slowmode_ai","pre_conflict","caps_filter","mention_spam","emoji_spam","zalgo_filter","phone_filter","email_filter","scam_filter","fake_nitro_filter","token_filter","anti_advertisement","everyone_block","nsfw_text_filter","unicode_filter","file_spam_filter"]
    if feat not in valid:
        return jsonify({"success": False})
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
    if "user" not in session:
        return jsonify({"success": False})
    valid = ["warn_mute","warn_ban","mute_duration","ai_sensitivity","spam_limit","spam_window","raid_limit","min_account_age","mod_role_name","log_channel","raid_channel","welcome_channel"]
    if key not in valid:
        return jsonify({"success": False})
    data = request.get_json()
    val = data.get("value")
    try:
        if key in ["warn_mute","warn_ban","mute_duration","spam_limit","spam_window","raid_limit","min_account_age"]:
            val = int(val)
        elif key == "ai_sensitivity":
            val = float(val)
    except:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (val, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/custom/<gid>", methods=["POST"])
def api_add_custom(gid):
    if "user" not in session:
        return jsonify({"success": False})
    data = request.get_json()
    t = data.get("trigger", "").lower().strip()
    r = data.get("response", "").strip()
    if not t or not r:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO custom_commands (guild_id, trigger_word, response) VALUES (?, ?, ?)", (gid, t, r))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/custom/<gid>/<trig>", methods=["DELETE"])
def api_del_custom(gid, trig):
    if "user" not in session:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM custom_commands WHERE guild_id=? AND trigger_word=?", (gid, trig))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/word/<gid>", methods=["POST"])
def api_add_word(gid):
    if "user" not in session:
        return jsonify({"success": False})
    data = request.get_json()
    w = data.get("word", "").lower().strip()
    if not w:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO word_filters (guild_id, word) VALUES (?, ?)", (gid, w))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/word/<gid>/<word>", methods=["DELETE"])
def api_del_word(gid, word):
    if "user" not in session:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM word_filters WHERE guild_id=? AND word=?", (gid, word.lower()))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/clearwarns/<gid>/<uid>", methods=["POST"])
def api_clear_warns(gid, uid):
    if "user" not in session:
        return jsonify({"success": False})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE user_id=? AND guild_id=?", (uid, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/announce/<gid>", methods=["POST"])
def api_announce(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False, "error": "Not ready"})
    data = request.get_json()
    ch_name = data.get("channel")
    msg = data.get("message")
    title = data.get("title", "📢 Announcement")
    if not ch_name or not msg:
        return jsonify({"success": False, "error": "Missing fields"})
    import discord
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False, "error": "Guild not found"})
    ch = discord.utils.get(guild.text_channels, name=ch_name)
    if not ch:
        return jsonify({"success": False, "error": "Channel not found"})
    try:
        embed = discord.Embed(title=title, description=msg, color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_footer(text=f"Sent by {session['user']['username']} via Dashboard")
        asyncio.run_coroutine_threadsafe(ch.send(embed=embed), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/dm/<gid>", methods=["POST"])
def api_dm(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False, "error": "Not ready"})
    data = request.get_json()
    uid = data.get("user_id")
    msg = data.get("message")
    if not uid or not msg:
        return jsonify({"success": False, "error": "Missing fields"})
    import discord
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False, "error": "Guild not found"})
    try:
        member = guild.get_member(int(uid))
        if not member:
            return jsonify({"success": False, "error": "User not found"})
        embed = discord.Embed(title=f"Message from {guild.name}", description=msg, color=discord.Color.blue())
        asyncio.run_coroutine_threadsafe(member.send(embed=embed), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/channel/<gid>", methods=["POST"])
def api_create_channel(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    data = request.get_json()
    name = data.get("name", "").lower().replace(" ", "-")
    cat_name = data.get("category")
    if not name:
        return jsonify({"success": False})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    try:
        cat = None
        if cat_name:
            cat = discord.utils.get(guild.categories, name=cat_name)
        future = asyncio.run_coroutine_threadsafe(guild.create_text_channel(name=name, category=cat), BOT_INSTANCE.loop)
        future.result(timeout=10)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/channel/<gid>/<chname>", methods=["DELETE"])
def api_del_channel(gid, chname):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    try:
        ch = discord.utils.get(guild.text_channels, name=chname)
        if ch:
            asyncio.run_coroutine_threadsafe(ch.delete(), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/role/<gid>", methods=["POST"])
def api_create_role(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    data = request.get_json()
    name = data.get("name", "")
    color_hex = data.get("color", "#000000")
    if not name:
        return jsonify({"success": False})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    try:
        color = discord.Color(int(color_hex.replace("#", ""), 16))
        future = asyncio.run_coroutine_threadsafe(guild.create_role(name=name, color=color), BOT_INSTANCE.loop)
        future.result(timeout=10)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/role/<gid>/<name>", methods=["DELETE"])
def api_del_role(gid, name):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    try:
        role = discord.utils.get(guild.roles, name=name)
        if role:
            asyncio.run_coroutine_threadsafe(role.delete(), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/category/<gid>", methods=["POST"])
def api_create_category(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    data = request.get_json()
    name = data.get("name", "")
    if not name:
        return jsonify({"success": False})
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    try:
        asyncio.run_coroutine_threadsafe(guild.create_category(name=name), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/useraction/<gid>/<uid>", methods=["POST"])
def api_user_action(gid, uid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    data = request.get_json()
    action = data.get("action")
    reason = data.get("reason", "No reason")
    duration = data.get("duration")
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    member = guild.get_member(int(uid))
    if not member:
        return jsonify({"success": False, "error": "User not found"})
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
            c.execute("INSERT INTO warnings (user_id, guild_id, reason, severity, timestamp) VALUES (?, ?, ?, ?, ?)", (str(uid), str(gid), reason, "manual", datetime.now().isoformat()))
            conn.commit()
            conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/giveaway/<gid>", methods=["POST"])
def api_giveaway(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    data = request.get_json()
    prize = data.get("prize")
    ch_name = data.get("channel")
    duration = int(data.get("duration", 60))
    winners = int(data.get("winners", 1))
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    ch = discord.utils.get(guild.text_channels, name=ch_name)
    if not ch:
        return jsonify({"success": False, "error": "Channel not found"})
    try:
        end_time = datetime.now() + timedelta(minutes=duration)
        embed = discord.Embed(title="🎉 GIVEAWAY!", description=f"**Prize:** {prize}\nReact 🎉!", color=discord.Color.gold(), timestamp=end_time)
        embed.add_field(name="Winners", value=str(winners))
        embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>")
        future = asyncio.run_coroutine_threadsafe(ch.send(embed=embed), BOT_INSTANCE.loop)
        msg = future.result(timeout=10)
        asyncio.run_coroutine_threadsafe(msg.add_reaction("🎉"), BOT_INSTANCE.loop)
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, host_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(gid), str(ch.id), str(msg.id), prize, winners, end_time.isoformat(), session['user']['id']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/poll/<gid>", methods=["POST"])
def api_poll(gid):
    if "user" not in session or not BOT_INSTANCE:
        return jsonify({"success": False})
    import discord
    data = request.get_json()
    q = data.get("question")
    ch_name = data.get("channel")
    opts = data.get("options", [])
    guild = BOT_INSTANCE.get_guild(int(gid))
    if not guild:
        return jsonify({"success": False})
    ch = discord.utils.get(guild.text_channels, name=ch_name)
    if not ch:
        return jsonify({"success": False})
    try:
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
        embed = discord.Embed(title=f"📊 {q}", color=discord.Color.blue())
        for i, o in enumerate(opts[:5]):
            embed.add_field(name=f"{emojis[i]} {o.strip()}", value="\u200b", inline=False)
        future = asyncio.run_coroutine_threadsafe(ch.send(embed=embed), BOT_INSTANCE.loop)
        msg = future.result(timeout=10)
        for i in range(min(len(opts), 5)):
            asyncio.run_coroutine_threadsafe(msg.add_reaction(emojis[i]), BOT_INSTANCE.loop)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/personality/<gid>", methods=["POST"])
def api_personality(gid):
    if "user" not in session:
        return jsonify({"success": False})
    data = request.get_json()
    p = data.get("personality")
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE guild_settings SET personality=? WHERE guild_id=?", (p, gid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

def run_dashboard():
    app.run(host="0.0.0.0", port=8080, debug=False)
