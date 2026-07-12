# welcome_system.py
# ================================
# Sapphire-style Welcome System
# ================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import io
import json
import sqlite3
import asyncio
import os
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

_bot_ref = None
_is_setup = False


def _get_db():
    conn = sqlite3.connect("sentinel.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_tables():
    conn = _get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS welcome_config (
        guild_id TEXT PRIMARY KEY,
        enabled INTEGER DEFAULT 1,
        channel_name TEXT DEFAULT 'welcome',
        card_enabled INTEGER DEFAULT 1,
        dm_enabled INTEGER DEFAULT 1,
        ai_mode INTEGER DEFAULT 1,
        custom_message TEXT DEFAULT '',
        custom_dm TEXT DEFAULT '',
        card_bg_url TEXT DEFAULT '',
        card_color TEXT DEFAULT '#5865F2',
        auto_role TEXT DEFAULT '',
        show_rules INTEGER DEFAULT 1,
        server_description TEXT DEFAULT ''
    )""")
    conn.commit()
    conn.close()


def get_welcome_config(gid):
    conn = _get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM welcome_config WHERE guild_id=?", (str(gid),))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "guild_id": str(gid), "enabled": 1, "channel_name": "welcome",
        "card_enabled": 1, "dm_enabled": 1, "ai_mode": 1,
        "custom_message": "", "custom_dm": "", "card_bg_url": "",
        "card_color": "#5865F2", "auto_role": "", "show_rules": 1,
        "server_description": ""
    }


def save_welcome_config(gid, key, value):
    conn = _get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO welcome_config (guild_id) VALUES (?)", (str(gid),))
    c.execute(f"UPDATE welcome_config SET {key}=? WHERE guild_id=?", (value, str(gid)))
    conn.commit()
    conn.close()


# ============ AI WELCOME GENERATION ============
async def generate_ai_welcome(member, guild, config):
    """Generate a personalized welcome message using AI."""
    if not GROQ_API_KEY:
        return f"Welcome to {guild.name}, {member.display_name}!"
    
    try:
        # Gather server context
        server_desc = config.get("server_description", "")
        if not server_desc and guild.description:
            server_desc = guild.description
        
        # Get channel names for context
        channels = [ch.name for ch in guild.text_channels[:15]]
        
        prompt = f"""Generate a warm, personalized welcome message for a new Discord member.

SERVER: {guild.name}
SERVER DESCRIPTION: {server_desc or 'A Discord community'}
MEMBER COUNT: {guild.member_count}
CHANNELS (sample): {', '.join(channels[:8])}
NEW MEMBER: {member.display_name}
ACCOUNT AGE: {(datetime.now() - member.created_at.replace(tzinfo=None)).days} days

Write a 2-3 sentence welcome that:
- Feels warm and personal (not robotic)
- References what the server is about
- Makes them feel excited to be here
- Uses emojis naturally
- NEVER swears
- Doesn't sound like a generic template

Just write the welcome message, nothing else."""

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a friendly Discord community welcomer. Be warm, personal, and enthusiastic."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.9,
            "max_tokens": 200
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    text = re.sub(r'^["\']|["\']$', '', text)  # Remove surrounding quotes
                    return text
    except Exception as e:
        print(f"AI welcome err: {e}")
    
    return f"Welcome to **{guild.name}**, {member.display_name}! 🎉 We're excited to have you here!"


async def generate_ai_dm(member, guild, config):
    """Generate a personalized DM welcome."""
    if not GROQ_API_KEY:
        return f"Welcome to {guild.name}! Check out the rules channel to get started."
    
    try:
        server_desc = config.get("server_description", "") or guild.description or ""
        
        # Find rules channel
        rules_ch = None
        for name in ['rules', 'server-rules', 'guidelines']:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                rules_ch = ch
                break
        
        prompt = f"""Write a friendly welcome DM for a new Discord server member.

SERVER: {guild.name}
DESCRIPTION: {server_desc or 'A Discord community'}
NEW MEMBER: {member.display_name}

Write a warm 3-4 sentence DM that:
- Welcomes them personally
- Briefly explains what the server is about
- Tells them to check the rules
- Encourages them to introduce themselves
- Uses emojis but not too many
- Feels genuine, not robotic

Just write the DM text, nothing else."""

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a warm Discord welcomer sending a personal DM. NEVER swear."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.85,
            "max_tokens": 250
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"AI DM err: {e}")
    
    return f"Welcome to **{guild.name}**! 🎉\n\nWe're glad you're here! Make sure to check out the rules channel and feel free to introduce yourself in general chat!"


# ============ WELCOME CARD GENERATION ============
async def generate_welcome_card(member, guild, config):
    """Generate a Sapphire-style welcome card image."""
    try:
        # Card dimensions
        WIDTH, HEIGHT = 1000, 400
        
        # Parse color
        color_hex = config.get("card_color", "#5865F2").lstrip("#")
        accent_color = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
        
        # Create base image
        card = Image.new("RGB", (WIDTH, HEIGHT), (43, 45, 49))  # Discord dark
        
        # Try loading custom background
        bg_url = config.get("card_bg_url", "")
        if bg_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(bg_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            bg_data = await resp.read()
                            bg = Image.open(io.BytesIO(bg_data)).convert("RGB")
                            bg = bg.resize((WIDTH, HEIGHT))
                            # Darken it a bit
                            darken = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
                            card = Image.blend(bg, darken, 0.4)
            except: pass
        else:
            # Create gradient background
            for y in range(HEIGHT):
                # Gradient from dark to accent color
                ratio = y / HEIGHT
                r = int(43 + (accent_color[0] - 43) * ratio * 0.3)
                g = int(45 + (accent_color[1] - 45) * ratio * 0.3)
                b = int(49 + (accent_color[2] - 49) * ratio * 0.3)
                for x in range(WIDTH):
                    card.putpixel((x, y), (r, g, b))
        
        draw = ImageDraw.Draw(card)
        
        # Load fonts (fallback to default if not found)
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            try:
                font_large = ImageFont.truetype("arial.ttf", 60)
                font_medium = ImageFont.truetype("arial.ttf", 32)
                font_small = ImageFont.truetype("arial.ttf", 24)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
        
        # Fetch avatar
        avatar_size = 200
        avatar_x = 60
        avatar_y = (HEIGHT - avatar_size) // 2
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(member.display_avatar.url), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    avatar_data = await resp.read()
                    avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                    avatar = avatar.resize((avatar_size, avatar_size))
                    
                    # Create circular mask
                    mask = Image.new("L", (avatar_size, avatar_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                    
                    # Create circular avatar
                    circular_avatar = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
                    circular_avatar.paste(avatar, (0, 0), mask)
                    
                    # Draw glow/border ring
                    ring_size = avatar_size + 20
                    ring_x = avatar_x - 10
                    ring_y = avatar_y - 10
                    draw.ellipse(
                        (ring_x, ring_y, ring_x + ring_size, ring_y + ring_size),
                        outline=accent_color, width=6
                    )
                    
                    card.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
        except Exception as e:
            print(f"Avatar err: {e}")
        
        # Text area
        text_x = avatar_x + avatar_size + 60
        
        # "WELCOME" title
        draw.text((text_x, 100), "WELCOME", fill=accent_color, font=font_medium)
        
        # Member name
        name = member.display_name
        if len(name) > 20:
            name = name[:20] + "..."
        draw.text((text_x, 140), name, fill=(255, 255, 255), font=font_large)
        
        # Server name
        server_name = f"to {guild.name}"
        if len(server_name) > 30:
            server_name = server_name[:30] + "..."
        draw.text((text_x, 220), server_name, fill=(180, 190, 200), font=font_medium)
        
        # Member count
        count_text = f"You are member #{guild.member_count}"
        draw.text((text_x, 280), count_text, fill=(150, 160, 170), font=font_small)
        
        # Save to bytes
        buf = io.BytesIO()
        card.save(buf, format="PNG")
        buf.seek(0)
        return buf
    
    except Exception as e:
        print(f"Card gen err: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============ MAIN WELCOME HANDLER ============
async def handle_welcome(member):
    """Handle new member join - send welcome message, card, DM."""
    guild = member.guild
    config = get_welcome_config(guild.id)
    
    if not config.get("enabled", 1):
        return
    
    # Auto-role
    if config.get("auto_role"):
        role = discord.utils.get(guild.roles, name=config["auto_role"])
        if role:
            try:
                await member.add_roles(role, reason="Auto-role on join")
            except: pass
    
    # Find welcome channel
    ch_name = config.get("channel_name", "welcome")
    welcome_ch = discord.utils.get(guild.text_channels, name=ch_name)
    if not welcome_ch:
        # Fallback to system channel
        welcome_ch = guild.system_channel
    
    # Generate welcome message
    if config.get("custom_message"):
        msg_text = config["custom_message"].format(
            user=member.mention,
            username=member.display_name,
            server=guild.name,
            count=guild.member_count
        )
    elif config.get("ai_mode", 1):
        msg_text = await generate_ai_welcome(member, guild, config)
    else:
        msg_text = f"Welcome to **{guild.name}**, {member.mention}! 🎉"
    
    # Send welcome to channel
    if welcome_ch:
        try:
            embed = discord.Embed(
                description=msg_text,
                color=int(config.get("card_color", "#5865F2").lstrip("#"), 16),
                timestamp=datetime.now()
            )
            embed.set_author(
                name=f"Welcome, {member.display_name}!",
                icon_url=member.display_avatar.url
            )
            embed.add_field(name="👤 Member #", value=f"{guild.member_count}", inline=True)
            embed.add_field(name="📅 Account Age", value=f"{(datetime.now() - member.created_at.replace(tzinfo=None)).days} days", inline=True)
            
            # Find rules channel for reference
            rules_ch = None
            for rn in ['rules', 'server-rules', 'guidelines']:
                r = discord.utils.get(guild.text_channels, name=rn)
                if r:
                    rules_ch = r
                    break
            
            if rules_ch and config.get("show_rules", 1):
                embed.add_field(name="📋 Rules", value=rules_ch.mention, inline=True)
            
            embed.set_footer(text=f"{guild.name}", icon_url=guild.icon.url if guild.icon else None)
            
            # Send card if enabled
            file = None
            if config.get("card_enabled", 1):
                card = await generate_welcome_card(member, guild, config)
                if card:
                    file = discord.File(card, filename="welcome.png")
                    embed.set_image(url="attachment://welcome.png")
            
            if file:
                await welcome_ch.send(content=member.mention, embed=embed, file=file)
            else:
                await welcome_ch.send(content=member.mention, embed=embed)
        except Exception as e:
            print(f"Welcome send err: {e}")
    
    # Send DM
    if config.get("dm_enabled", 1):
        try:
            if config.get("custom_dm"):
                dm_text = config["custom_dm"].format(
                    user=member.mention,
                    username=member.display_name,
                    server=guild.name,
                    count=guild.member_count
                )
            elif config.get("ai_mode", 1):
                dm_text = await generate_ai_dm(member, guild, config)
            else:
                dm_text = f"Welcome to **{guild.name}**! 🎉 We're glad to have you!"
            
            dm_embed = discord.Embed(
                title=f"🎉 Welcome to {guild.name}!",
                description=dm_text,
                color=int(config.get("card_color", "#5865F2").lstrip("#"), 16)
            )
            if guild.icon:
                dm_embed.set_thumbnail(url=guild.icon.url)
            dm_embed.set_footer(text=f"Member #{guild.member_count} • You joined {guild.name}")
            
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # DMs closed
        except Exception as e:
            print(f"DM err: {e}")


# ============ SLASH COMMANDS ============
def _register_commands(bot):
    
    @bot.tree.command(name="welcome_setup", description="[Admin] Configure the welcome system")
    async def welcome_setup(i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        config = get_welcome_config(i.guild.id)
        
        embed = discord.Embed(
            title="👋 Welcome System Setup",
            description="Configure how new members are welcomed to your server.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="✅ Enabled", value="Yes" if config["enabled"] else "No", inline=True)
        embed.add_field(name="📺 Channel", value=f"#{config['channel_name']}", inline=True)
        embed.add_field(name="🎨 Welcome Card", value="✅" if config["card_enabled"] else "❌", inline=True)
        embed.add_field(name="📨 DM Welcome", value="✅" if config["dm_enabled"] else "❌", inline=True)
        embed.add_field(name="🤖 AI Mode", value="✅" if config["ai_mode"] else "❌", inline=True)
        embed.add_field(name="🎭 Auto-Role", value=config["auto_role"] or "None", inline=True)
        embed.add_field(
            name="🎨 Color", value=config["card_color"], inline=True
        )
        embed.add_field(
            name="📝 Server Description",
            value=config.get("server_description") or "*Not set - using AI defaults*",
            inline=False
        )
        embed.set_footer(text="Use /welcome_config to change settings")
        
        await i.response.send_message(embed=embed, ephemeral=True)
    
    
    @bot.tree.command(name="welcome_config", description="[Admin] Change a welcome setting")
    @app_commands.choices(setting=[
        app_commands.Choice(name="Enable/Disable System", value="enabled"),
        app_commands.Choice(name="Welcome Channel", value="channel_name"),
        app_commands.Choice(name="Enable/Disable Card", value="card_enabled"),
        app_commands.Choice(name="Enable/Disable DM", value="dm_enabled"),
        app_commands.Choice(name="AI Mode (auto-generate)", value="ai_mode"),
        app_commands.Choice(name="Custom Welcome Message", value="custom_message"),
        app_commands.Choice(name="Custom DM Message", value="custom_dm"),
        app_commands.Choice(name="Card Background URL", value="card_bg_url"),
        app_commands.Choice(name="Card Color (hex)", value="card_color"),
        app_commands.Choice(name="Auto Role", value="auto_role"),
        app_commands.Choice(name="Server Description (for AI)", value="server_description"),
    ])
    @app_commands.describe(
        setting="Which setting to change",
        value="New value (for on/off use 'on' or 'off', for messages use {user}, {username}, {server}, {count} as placeholders)"
    )
    async def welcome_config(i: discord.Interaction, setting: app_commands.Choice[str], value: str):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        key = setting.value
        
        # Handle boolean toggles
        if key in ["enabled", "card_enabled", "dm_enabled", "ai_mode"]:
            new_val = 1 if value.lower() in ["on", "true", "yes", "1", "enable"] else 0
            save_welcome_config(i.guild.id, key, new_val)
            await i.response.send_message(
                f"✅ **{setting.name}** set to **{'ON' if new_val else 'OFF'}**",
                ephemeral=True
            )
        else:
            save_welcome_config(i.guild.id, key, value)
            await i.response.send_message(
                f"✅ **{setting.name}** updated!",
                ephemeral=True
            )
    
    
    @bot.tree.command(name="welcome_test", description="[Admin] Test the welcome message")
    async def welcome_test(i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("Admin only!", ephemeral=True)
            return
        
        await i.response.defer(ephemeral=True)
        await handle_welcome(i.user)
        await i.followup.send("✅ Test welcome sent!", ephemeral=True)
    
    
    @bot.tree.command(name="welcome_preview", description="Preview what the welcome card will look like")
    async def welcome_preview(i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        config = get_welcome_config(i.guild.id)
        card = await generate_welcome_card(i.user, i.guild, config)
        if card:
            file = discord.File(card, filename="preview.png")
            await i.followup.send("🎨 Card preview:", file=file, ephemeral=True)
        else:
            await i.followup.send("❌ Failed to generate card", ephemeral=True)


# ============ LISTENER ============
def _register_listener(bot):
    @bot.listen("on_member_join")
    async def _welcome_listener(member):
        try:
            await handle_welcome(member)
        except Exception as e:
            print(f"Welcome listener err: {e}")


# ============ SETUP ============
def setup(bot):
    global _bot_ref, _is_setup
    if _is_setup:
        return
    _bot_ref = bot
    _is_setup = True
    _init_tables()
    _register_commands(bot)
    _register_listener(bot)
    print("[welcome_system] ✅ Loaded")


# ============ AUTO HOOK ============
import threading
import time as _time

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
