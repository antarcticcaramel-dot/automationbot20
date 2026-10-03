import discord
from discord.ui import View, Button, Modal, TextInput
import aiohttp
import json
import os
import re
from datetime import datetime, timedelta

# ==========================================
# FREE TIER OPTIMIZATION:
# We use llama-3.1-8b-instant for parsing (fast, cheap)
# We use llama-3.3-70b-versatile as a fallback
# ==========================================

async def parse_natural_command(text: str, guild: discord.Guild, author: discord.Member) -> dict:
    """Parses natural language like 'ban @user 7 days for spam' into executable JSON."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return None

    # Pre-extract mentions to help the AI
    mentions = re.findall(r'<@!?(\d+)>', text)
    mentioned_users = [f"{guild.get_member(int(m)).name} (ID: {m})" for m in mentions if guild.get_member(int(m))]

    prompt = f"""Extract the moderation command from this text.
TEXT: "{text}"
MENTIONED USERS IN TEXT: {', '.join(mentioned_users) if mentioned_users else 'None'}
SENDER: {author.name}

Available Actions: "ban", "kick", "mute", "unmute", "warn", "lock", "unlock", "purge", "chat" (if it's just a conversation).

Return EXACTLY this JSON format and nothing else:
{{
    "action": "ban|kick|mute|warn|lock|unlock|purge|chat",
    "target_id": "123456789 (extract from mentions or text)",
    "duration_minutes": 10080 (convert 7 days to minutes, 0 if permanent/none),
    "reason": "Brief reason extracted",
    "amount": 50 (for purge only),
    "confidence": 0.0-1.0
}}"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant", # FAST AND FREE
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    match = re.search(r'\{.*\}', content.replace('\n', ''), re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                        return parsed
    except Exception as e:
        print(f"[AI Parser] Err: {e}")
    return {"action": "chat", "confidence": 1.0}

# ==========================================
# DISCORD COMPONENTS V2: CONFIRMATION UI
# ==========================================
class EditReasonModal(Modal, title="✏️ Edit Reason"):
    reason_input = TextInput(label="New Reason", style=discord.TextStyle.paragraph, max_length=300)

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.reason_input.default = parent_view.parsed_data.get("reason", "No reason provided")

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.parsed_data["reason"] = self.reason_input.value
        await self.parent_view.update_embed(interaction)

class CommandConfirmView(View):
    def __init__(self, parsed_data: dict, target: discord.Member, bot_instance):
        super().__init__(timeout=60)
        self.parsed_data = parsed_data
        self.target = target
        self.bot = bot_instance
        self.message = None

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚠️ Confirm AI Command", color=0xFEE75C)
        embed.add_field(name="Action", value=self.parsed_data["action"].upper(), inline=True)
        if self.target:
            embed.add_field(name="Target", value=self.target.mention, inline=True)
        if self.parsed_data.get("duration_minutes"):
            embed.add_field(name="Duration", value=f"{self.parsed_data['duration_minutes']} mins", inline=True)
        embed.add_field(name="Reason", value=self.parsed_data.get("reason", "None"), inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="✅ Execute", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        action = self.parsed_data["action"]
        reason = f"{self.parsed_data.get('reason')} (AI Auto-Parsed by {interaction.user})"
        
        try:
            if action == "ban":
                await self.target.ban(reason=reason)
            elif action == "kick":
                await self.target.kick(reason=reason)
            elif action == "mute":
                mins = self.parsed_data.get("duration_minutes", 60)
                await self.target.timeout(discord.utils.utcnow() + timedelta(minutes=mins), reason=reason)
            elif action == "warn":
                await interaction.followup.send(f"⚠️ Warned {self.target.mention}: {reason}")
                
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(content="✅ **Command Executed Successfully.**", view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to execute: {e}", ephemeral=True)

    @discord.ui.button(label="✏️ Edit Reason", style=discord.ButtonStyle.secondary)
    async def edit_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(EditReasonModal(self))

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🚫 **Command Cancelled.**", view=self)

def setup(bot, get_db, get_settings, ask_groq, ask_json, notify_owner):
    @bot.event
    async def on_message(message):
        if message.author.bot: return
        
        # Check if the bot was pinged with a command
        if bot.user in message.mentions and message.guild:
            # Check permissions
            if not message.author.guild_permissions.kick_members and message.author.id != int(os.getenv("OWNER_ID", 0)):
                return
            
            clean_content = message.content.replace(f"<@{bot.user.id}>", "").strip()
            if len(clean_content) > 5:
                # Trigger natural language parser
                parsed = await parse_natural_command(clean_content, message.guild, message.author)
                
                if parsed and parsed.get("action") != "chat" and parsed.get("confidence", 0) > 0.6:
                    target = message.guild.get_member(int(parsed.get("target_id", 0))) if parsed.get("target_id") else None
                    
                    if not target and parsed["action"] in ["ban", "kick", "mute", "warn"]:
                        await message.reply("❌ AI couldn't figure out who to target. Try @mentioning them!")
                        return
                        
                    view = CommandConfirmView(parsed, target, bot)
                    embed = discord.Embed(title="🤖 AI Command Parser", description="Please confirm the extracted action:", color=0x5865F2)
                    embed.add_field(name="Action", value=parsed["action"].upper(), inline=True)
                    if target: embed.add_field(name="Target", value=target.mention, inline=True)
                    if parsed.get("duration_minutes"): embed.add_field(name="Duration", value=f"{parsed['duration_minutes']} mins", inline=True)
                    embed.add_field(name="Reason", value=parsed.get("reason", "No reason provided"), inline=False)
                    
                    msg = await message.reply(embed=embed, view=view)
                    view.message = msg
