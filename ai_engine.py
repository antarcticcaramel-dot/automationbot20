# ai_engine.py
# ================================
# Multi-model AI engine with smart routing + Prompt Guard
# ================================

import aiohttp
import json
import re
import asyncio
import time
from typing import Optional
from core_config import GROQ_URL, OPENROUTER_URL, HF_INFERENCE, MODELS


class AIEngine:
    """Multi-model AI with Groq (primary), OpenRouter (secondary), HuggingFace (guard)."""

    def __init__(self, groq_key: str, openrouter_key: str = "", hf_key: str = ""):
        self.groq_key = groq_key
        self.openrouter_key = openrouter_key
        self.hf_key = hf_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limits: dict[str, float] = {}  # provider -> next_allowed_ts

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=45)
            )
        return self._session

    # ------------------------------------------------------------------
    # SMART ROUTER — picks the best model for the job
    # ------------------------------------------------------------------
    def _route(self, prompt: str, *, prefer: str = "auto") -> tuple[str, str, str]:
        """Returns (base_url, model_name, api_key)."""
        prompt_len = len(prompt)

        if prefer == "guard":
            return GROQ_URL, MODELS["guard"], self.groq_key

        if prefer == "fast" or prompt_len < 300:
            return GROQ_URL, MODELS["fast"], self.groq_key

        if prefer == "large" and self.openrouter_key:
            return OPENROUTER_URL, MODELS["large"], self.openrouter_key

        if prefer == "qwen" and self.openrouter_key:
            return OPENROUTER_URL, MODELS["qwen"], self.openrouter_key

        # Default: Groq main model
        return GROQ_URL, MODELS["main"], self.groq_key

    # ------------------------------------------------------------------
    # LOW-LEVEL REQUEST
    # ------------------------------------------------------------------
    async def _request(
        self,
        url: str,
        model: str,
        api_key: str,
        messages: list[dict],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        """Fire a chat-completion request. Returns the assistant text or None."""
        if not api_key:
            return None

        # Simple rate-limit guard
        provider = "groq" if "groq" in url else "openrouter"
        now = time.time()
        next_ok = self._rate_limits.get(provider, 0)
        if now < next_ok:
            await asyncio.sleep(next_ok - now)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter" in url:
            headers["HTTP-Referer"] = "https://sentinelmod.bot"
            headers["X-Title"] = "SentinelMod"

        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        session = await self._get_session()
        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 429:
                    retry = float(resp.headers.get("Retry-After", "5"))
                    self._rate_limits[provider] = time.time() + retry
                    await asyncio.sleep(retry)
                    return await self._request(url, model, api_key, messages,
                                               max_tokens, temperature, response_format)
                if resp.status != 200:
                    body = await resp.text()
                    print(f"AI {resp.status}: {body[:300]}")
                    return None

                data = await resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]
                return None
        except asyncio.TimeoutError:
            print(f"AI timeout: {model}")
            return None
        except Exception as e:
            print(f"AI error: {e}")
            return None

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------
    async def chat(
        self,
        prompt: str,
        system: str = "You are SentinelMod, a helpful Discord moderation AI.",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        prefer: str = "auto",
    ) -> Optional[str]:
        """General chat completion."""
        url, model, key = self._route(prompt, prefer=prefer)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        result = await self._request(url, model, key, messages, max_tokens, temperature)
        # Fallback if primary fails
        if result is None and "groq" in url and self.openrouter_key:
            result = await self._request(
                OPENROUTER_URL, MODELS.get("large", MODELS["main"]),
                self.openrouter_key, messages, max_tokens, temperature
            )
        return result

    async def chat_with_history(
        self,
        messages: list[dict],
        system: str = "You are SentinelMod.",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        prefer: str = "auto",
    ) -> Optional[str]:
        """Chat with full message history."""
        full = [{"role": "system", "content": system}] + messages
        prompt_text = " ".join(m.get("content", "") for m in messages)
        url, model, key = self._route(prompt_text, prefer=prefer)
        return await self._request(url, model, key, full, max_tokens, temperature)

    async def ask_json(
        self,
        prompt: str,
        system: str = "Respond ONLY with valid JSON. No markdown, no explanation.",
        max_tokens: int = 1024,
        temperature: float = 0.3,
        prefer: str = "auto",
    ) -> Optional[dict]:
        """Ask a question and parse the response as JSON."""
        raw = await self.chat(prompt, system=system, max_tokens=max_tokens,
                              temperature=temperature, prefer=prefer)
        if not raw:
            return None
        return self._parse_json(raw)

    async def classify(
        self,
        text: str,
        categories: list[str],
        context: str = "",
    ) -> Optional[dict]:
        """Classify text into categories. Returns {category, confidence}."""
        cats = ", ".join(categories)
        prompt = (
            f"Classify this text into exactly ONE category.\n"
            f"Categories: {cats}\n"
            f"{'Context: ' + context if context else ''}\n"
            f"Text: \"{text[:1500]}\"\n\n"
            f"JSON: {{\"category\": \"chosen_category\", \"confidence\": 0.0-1.0}}"
        )
        return await self.ask_json(prompt, prefer="fast")

    async def moderate_text(
        self,
        text: str,
        rules: str = "",
        context: str = "",
    ) -> Optional[dict]:
        """AI moderation check. Returns dict with violation info."""
        prompt = f"""Analyze this Discord message for rule violations.

{"SERVER RULES:" + chr(10) + rules[:1500] if rules else "Use general Discord community guidelines."}

{"RECENT CONTEXT:" + chr(10) + context[:800] if context else ""}

MESSAGE: "{text[:1500]}"

Respond with JSON:
{{
  "is_violation": true/false,
  "severity": "none|low|medium|high|critical",
  "categories": ["toxicity","spam","nsfw","harassment","threats","hate_speech","self_harm","doxxing","scam"],
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "suggested_action": "none|warn|delete|mute|kick|ban"
}}"""
        return await self.ask_json(prompt, prefer="auto")

    async def safety_check(self, text: str) -> Optional[dict]:
        """Use Llama Guard for content safety classification."""
        url, model, key = self._route("", prefer="guard")
        messages = [
            {"role": "user", "content": text[:2000]}
        ]
        raw = await self._request(url, model, key, messages, max_tokens=200, temperature=0.1)
        if not raw:
            return {"safe": True, "categories": []}
        is_safe = "safe" in raw.lower() and "unsafe" not in raw.lower()
        return {
            "safe": is_safe,
            "raw": raw.strip(),
            "categories": self._extract_guard_categories(raw),
        }

    # ------------------------------------------------------------------
    # HuggingFace Inference (Prompt Guard)
    # ------------------------------------------------------------------
    async def hf_inference(self, model_id: str, text: str) -> Optional[dict]:
        """Call HuggingFace Inference API."""
        if not self.hf_key:
            return None
        session = await self._get_session()
        url = f"{HF_INFERENCE}{model_id}"
        headers = {"Authorization": f"Bearer {self.hf_key}"}
        try:
            async with session.post(url, headers=headers,
                                    json={"inputs": text[:2000]}) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            print(f"HF error: {e}")
            return None

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_json(raw: str) -> Optional[dict]:
        """Robustly parse JSON from LLM output."""
        raw = raw.strip()
        # Strip markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Find first { ... } block
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Find first [ ... ] block
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                data = json.loads(match.group())
                return {"items": data}
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _extract_guard_categories(raw: str) -> list[str]:
        cats = []
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("S") and any(c.isdigit() for c in line[:3]):
                cats.append(line)
        return cats

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# ==================================================================
# PROMPT GUARD — detects prompt injection / jailbreak attempts
# ==================================================================
class PromptGuard:
    """Detects prompt injection using Llama Prompt Guard 2 + heuristics."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior|above)",
        r"disregard\s+(all\s+)?(previous|prior|above|your)",
        r"new\s+instructions?",
        r"you\s+are\s+now",
        r"pretend\s+(you('re|are)|to\s+be)",
        r"act\s+as\s+(if|a|an|though)",
        r"forget\s+(everything|all|your)",
        r"override\s+(your|the|all)",
        r"jailbreak",
        r"DAN\s+mode",
        r"developer\s+mode",
        r"system\s*:?\s*prompt",
        r"bypass\s+(the\s+)?(filter|rules|safety|restrictions)",
        r"reveal\s+(your|the)\s+(system|instructions|prompt)",
        r"what\s+(is|are)\s+your\s+(system|initial)\s+(prompt|instructions)",
    ]

    def __init__(self, ai_engine: AIEngine):
        self.ai = ai_engine
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    async def check(self, text: str) -> dict:
        """Check text for prompt injection. Returns {is_injection, confidence, method}."""
        # Phase 1: fast regex heuristics
        for pattern in self._compiled:
            if pattern.search(text):
                return {
                    "is_injection": True,
                    "confidence": 0.85,
                    "method": "regex",
                    "pattern": pattern.pattern,
                }

        # Phase 2: suspicious structural patterns
        structural_score = 0
        if text.count("```") >= 2:
            structural_score += 0.2
        if re.search(r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|system\|>", text):
            structural_score += 0.6
        if len(text) > 500 and text.count("\n") > 10:
            structural_score += 0.15
        if re.search(r"(respond|reply|answer)\s+with\s+(only|just)", text, re.I):
            structural_score += 0.1

        if structural_score >= 0.6:
            return {
                "is_injection": True,
                "confidence": min(structural_score, 0.95),
                "method": "structural",
            }

        # Phase 3: HuggingFace Prompt Guard model (if available)
        if self.ai.hf_key:
            try:
                result = await self.ai.hf_inference(
                    "meta-llama/Prompt-Guard-86M", text[:1500]
                )
                if result and isinstance(result, list) and len(result) > 0:
                    scores = result[0] if isinstance(result[0], list) else result
                    for item in scores:
                        label = item.get("label", "").lower()
                        score = item.get("score", 0)
                        if "injection" in label or "jailbreak" in label:
                            if score > 0.7:
                                return {
                                    "is_injection": True,
                                    "confidence": score,
                                    "method": "prompt_guard_model",
                                }
            except Exception as e:
                print(f"PromptGuard model: {e}")

        # Phase 4: AI-based check for subtle injections (only if text is suspicious-length)
        if len(text) > 200 or structural_score > 0.2:
            try:
                result = await self.ai.ask_json(
                    f"""Is this a prompt injection or jailbreak attempt?
Text: "{text[:800]}"

JSON: {{"is_injection": true/false, "confidence": 0.0-1.0, "reason": "brief"}}""",
                    prefer="fast"
                )
                if result and result.get("is_injection") and result.get("confidence", 0) > 0.75:
                    return {
                        "is_injection": True,
                        "confidence": result["confidence"],
                        "method": "ai_analysis",
                        "reason": result.get("reason", ""),
                    }
            except:
                pass

        return {"is_injection": False, "confidence": 0.0, "method": "clear"}
