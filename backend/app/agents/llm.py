"""
SkillSaathi LLM Provider Configuration
Configures LangChain ChatGoogleGenerativeAI with resilient error handling and timeouts.
"""

import logging
from typing import Optional, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from ..config import settings

logger = logging.getLogger("skillsaathi.agents.llm")

# gemini-flash-lite-latest has active unexhausted free tier quota.
DEFAULT_MODEL = "gemini-flash-lite-latest"

def is_llm_available() -> bool:
    """Returns True if a valid Gemini API key is present in settings."""
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

def extract_text_content(content: Any) -> str:
    """
    Safely extract plain text from Gemini responses, handling both
    traditional string outputs and Gemini 3.x list-of-parts structures.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "".join(parts)
    return str(content)

def get_chat_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
    streaming: bool = False,
    timeout: Optional[float] = None
) -> ChatGoogleGenerativeAI:
    """
    Factory function returning a configured ChatGoogleGenerativeAI instance.
    Enforces Google's minimum API deadline requirement (>= 15s).
    """
    if not is_llm_available():
        raise ValueError(
            "GEMINI_API_KEY is not configured in environment. "
            "Please check backend/.env or configure your key."
        )

    selected_model = model or DEFAULT_MODEL
    # Normalize model string if user passed prefix or deprecated alias
    if selected_model.startswith("models/"):
        selected_model = selected_model.replace("models/", "")
    if "2.5-flash" in selected_model:
        logger.info("[LLM] Mapping discontinued gemini-2.5-flash -> %s", DEFAULT_MODEL)
        selected_model = DEFAULT_MODEL

    # Google API requires a minimum deadline >= 10s; default to 25s
    raw_timeout = timeout or settings.LLM_TIMEOUT_SECONDS or 25.0
    request_timeout = max(15.0, float(raw_timeout))

    return ChatGoogleGenerativeAI(
        model=selected_model,
        google_api_key=settings.GEMINI_API_KEY.strip(),
        temperature=temperature,
        timeout=request_timeout,
        max_retries=2,
        streaming=streaming,
    )
