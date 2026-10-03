import aiohttp
import os
import json
import re

async def scan_image(image_url: str) -> dict:
    """Uses Vision AI to scan images for bad content, text scams, and NSFW."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"is_bad": False, "reason": "No API Key"}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = """Analyze this image. You are a strict Discord Trust & Safety bot.
Flag if it contains ANY of these:
- Scams / Free Nitro / Phishing URLs
- Explicit NSFW / Nudity / Pornography
- Gore or graphic violence
- Hate symbols (Swastikas, etc.)
- Personal Info (Doxxing/IPs)

Return ONLY valid JSON in this format:
{"is_bad": true/false, "category": "scam|nsfw|violence|hate|doxxing|safe", "reason": "Short explanation", "confidence": 0.0-1.0}"""

    payload = {
        "model": "llama-3.2-90b-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 300
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Extract JSON from output
                    match = re.search(r'\{.*\}', content.replace('\n', ''), re.DOTALL)
                    if match:
                        result = json.loads(match.group())
                        # Enforce high confidence threshold to prevent false positives
                        if result.get("confidence", 0) < 0.75:
                            result["is_bad"] = False
                        return result
    except Exception as e:
        print(f"[Image Mod] Scan error: {e}")

    return {"is_bad": False, "reason": "Scan failed"}
