import discord
import aiohttp
import os
import json
from datetime import datetime

# Advanced Prompt Injection Detection using Meta's Prompt Guard 2
async def check_prompt_injection(text: str) -> dict:
    """Uses meta-llama/llama-prompt-guard-2-86m to prevent jailbreaks."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or len(text.strip()) < 10:
        return {"is_injection": False, "score": 0.0}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "meta-llama/llama-prompt-guard-2-86m",
        "messages": [{"role": "user", "content": text}],
        "temperature": 0.0,
        "max_tokens": 10
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=5
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data["choices"][0]["message"]["content"].lower()
                    # Prompt Guard usually outputs 'safe', 'injection', or 'jailbreak'
                    if "injection" in result or "jailbreak" in result:
                        return {"is_injection": True, "score": 0.99}
    except Exception as e:
        print(f"[Volaris Guard] Prompt check error: {e}")
    
    return {"is_injection": False, "score": 0.0}

# Anti-Nuke State Tracking
anti_nuke_cache = {}

async def anti_nuke_monitor(bot, guild, action: str, user: discord.Member):
    """Monitors for mass-bans, mass-kicks, and mass-channel deletions."""
    now = datetime.now().timestamp()
    gid = str(guild.id)
    uid = str(user.id)

    if gid not in anti_nuke_cache:
        anti_nuke_cache[gid] = {}
    if uid not in anti_nuke_cache[gid]:
        anti_nuke_cache[gid][uid] = []

    # Clean old events (older than 60 seconds)
    anti_nuke_cache[gid][uid] = [t for t in anti_nuke_cache[gid][uid] if now - t < 60]
    anti_nuke_cache[gid][uid].append(now)

    # 5 destructive actions in 60 seconds = Nuke Attempt
    if len(anti_nuke_cache[gid][uid]) >= 5:
        # Take action against the rogue admin
        try:
            await user.edit(roles=[], reason="[Volaris Guard] Anti-Nuke triggered: Stripped roles.")
        except Exception:
            try:
                await guild.kick(user, reason="[Volaris Guard] Anti-Nuke triggered.")
            except: pass
        
        embed = discord.Embed(
            title="🛡️ Volaris Guard: Anti-Nuke Triggered",
            description=f"**{user.mention}** attempted to nuke the server by spamming `{action}` actions.\nAll their roles have been stripped.",
            color=0xED4245
        )
        # Notify owner/logs
        return embed
    return None
