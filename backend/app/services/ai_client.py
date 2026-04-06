import os
import logging
import re
from groq import AsyncGroq
import time

logger = logging.getLogger(__name__)


def is_ai_unavailable_response(content: str | None) -> bool:
    """
    True when the chat layer did not return usable model text (disabled API, error, or empty).
    Safe repair: central guard so json.loads never runs on AI_DISABLED / empty — use route-specific fallbacks.
    """
    if content is None:
        return True
    c = str(content).strip()
    return c == "" or c == "AI_DISABLED"


class AIClient:
    def __init__(self):
        # Safe repair — unified Groq key: primary get_settings().groq_keys[0] (matches interviews transcribe guard);
        # fallback os.getenv("GROQ_API_KEY") for process-env-only deployments. No prompt/scoring changes.
        self.api_key = ""
        try:
            from app.core.config import get_settings

            keys = get_settings().groq_keys
            if keys:
                self.api_key = keys[0]
        except Exception as e:
            logger.debug("Groq key from Settings unavailable: %s", e)
        if not self.api_key:
            self.api_key = (os.getenv("GROQ_API_KEY", "") or "").strip()

        self.disabled = False
        self.client = None

        if not self.api_key:
            logger.warning("AI features disabled - GROQ_API_KEY not set in environment.")
            self.disabled = True
        else:
            try:
                timeout_s = float(os.getenv("AI_TIMEOUT_SECONDS", "15") or "15")
                self.client = AsyncGroq(api_key=self.api_key, timeout=timeout_s)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}. AI features disabled.")
                self.disabled = True

    async def generate(self, prompt: str, system_instr: str = "You are a helpful assistant", model: str = "llama-3.3-70b-versatile") -> str:
        """Centralized generator that will never crash the calling thread if config is missing."""
        if self.disabled:
            logger.warning("AI Disabled - Returning graceful fallback response.")
            return "AI_DISABLED"
            
        t0 = time.perf_counter()
        try:
            logger.debug(
                "AI generate start",
                extra={
                    "model": model,
                    "prompt_len": len(prompt or ""),
                    "system_len": len(system_instr or ""),
                },
            )
        except Exception:
            pass

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instr},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content
            if raw is None or not str(raw).strip():
                logger.warning("Groq returned empty message content (treating as AI_DISABLED).")
                return "AI_DISABLED"
            content = str(raw).strip()
            try:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                logger.debug(
                    "AI generate ok",
                    extra={
                        "model": model,
                        "elapsed_ms": elapsed_ms,
                        "content_len": len(content or ""),
                    },
                )
            except Exception:
                pass
            return content
        except Exception as e:
            try:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                logger.error(
                    "Groq API Error (returning AI_DISABLED)",
                    extra={
                        "model": model,
                        "elapsed_ms": elapsed_ms,
                        "error_type": type(e).__name__,
                        "error": str(e)[:200],
                    },
                )
            except Exception:
                logger.error(f"Groq API Error: {e}")
            return "AI_DISABLED"

# Singleton instance to be imported globally
ai_client = AIClient()

def clean_json(text: str) -> str:
    """Clean markdown code blocks from JSON string and extract first JSON object"""
    # Remove markdown code blocks
    text = text.replace("```json", "").replace("```", "").strip()
    
    # Try to find JSON object with regex if it's not clean
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
        
    match_list = re.search(r'(\[.*\])', text, re.DOTALL)
    if match_list:
        return match_list.group(1)

    return text
