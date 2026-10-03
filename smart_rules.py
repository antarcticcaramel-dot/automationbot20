import discord
from discord.ui import View, Button
import aiohttp
import json
import os

_rules_cache = {}

async def load_and_extract_rules(guild: discord.Guild) -> dict:
    """Reads the server's rules channel and uses AI to structure them beautifully."""
    gid = str(guild.id)
    if gid in _rules_cache:
        return _rules_cache[gid]

    # Find the rules channel
    rules_ch = discord.utils.find(lambda c: "rule" in c.name.lower() or "guideline" in c.name.lower(), guild.text_channels)
    if not rules_ch:
        return {"rules": [], "raw": ""}

    raw_text = []
    async for msg in rules_ch.history(limit=20, oldest_first=True):
        if msg.content: raw_text.append(msg.content)
        for e in msg.embeds:
            if e.description: raw_text.append(e.description)

    combined_text = "\n".join(raw_text)[:4000]
    if not combined_text.strip():
        return {"rules": [], "raw": ""}

    # Use AI to format rules
    api_key = os.getenv("GROQ_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = f"""Read these messy server rules and format them into a clean JSON array.
RULES:
{combined_text}

OUTPUT JSON ONLY:
{{"summary": "1 sentence summary of server vibe", "rules": [{{"number": 1, "title": "Rule title", "description": "Rule description"}}]}}"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    json_data = json.loads(content[start:end])
                    json_data["raw"] = combined_text
                    _rules_cache[gid] = json_data
                    return json_data
    except Exception as e:
        print(f"[Smart Rules] Extraction err: {e}")

    return {"rules": [], "raw": combined_text}

class RuleAcceptView(View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="✅ I Accept the Rules", style=discord.ButtonStyle.success, custom_id="accept_rules_btn")
    async def accept(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(self.role_role)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ You've accepted the rules and gained access to the server!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Configuration error: Role not found.", ephemeral=True)

def setup(bot):
    pass # Hooked by main bot
