"""
ProfFinder — LLM Client Architecture
Centralizes OpenAI and Groq instantiation to provide automatic fallback
capabilities if one service hits a rate limit or 401 error.
"""

import json
from openai import AsyncOpenAI
import traceback
from app.config import get_settings


async def generate_json(
    messages: list[dict], 
    temperature: float = 0.1, 
    max_tokens: int = None,
    force_model: str = None
) -> dict:
    """
    Generates a guaranteed JSON response using either OpenAI (first choice)
    or Groq (fallback if OpenAI fails or has no key).
    """
    settings = get_settings()
    
    # ── 1. Attempt OpenAI ─────────────────────────────────
    if settings.openai_api_key:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        model = force_model or settings.openai_extraction_model
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"[LLM] OpenAI failed ({model}): {e}. Attempting Groq fallback...")
            # If we fail here, we fall through to Groq
    
    # ── 2. Attempt Groq ───────────────────────────────────
    if settings.groq_api_key:
        # Note: Groq is fully compatible with the OpenAI Python SDK
        # We just need to change the base URL and the model name.
        groq_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key
        )
        model = settings.groq_model
        
        try:
            response = await groq_client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"[LLM] Groq failed ({model}): {e}")
            traceback.print_exc()
            raise ValueError(f"Both OpenAI and Groq failed. Final error: {e}")
            
    # ── 3. No Keys Configured ──
    if "e" in locals():  # If it failed from OpenAI earlier
        final_err = f"OpenAI Failed ({settings.openai_extraction_model}): {e}. No Groq key found to try fallback."
        print(f"[LLM] CRITICAL: {final_err}")
        raise ValueError(final_err)
    else:
        raise ValueError("Missing LLM API Keys! Please configure either OPENAI_API_KEY or GROQ_API_KEY.")
