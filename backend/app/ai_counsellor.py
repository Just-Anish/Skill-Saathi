"""
SkillSaathi AI Counsellor Provider Adapter
Grounded, evidence-aware LLM integration with automatic deterministic fallback.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .config import settings

logger = logging.getLogger("skillsaathi.ai_counsellor")

class AICounsellorAdapter:
    """
    Server-side adapter for grounded generative AI career counselling.
    Only activates if GEMINI_API_KEY is configured in the environment.
    Guarantees strict fallback to the deterministic engine on missing keys,
    network timeouts, or unparseable responses.
    """

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    @classmethod
    def enhance_analysis(
        cls,
        base_analysis: Dict[str, Any],
        student: Dict[str, Any],
        parent: Dict[str, Any],
        courses: list
    ) -> Optional[Dict[str, Any]]:
        """
        Enhance the deterministic analysis with grounded LLM synthesis if configured.
        Returns None on any error to signal fallback.
        """
        if not cls.is_configured():
            return None

        try:
            prompt = cls._build_grounded_prompt(base_analysis, student, parent, courses)
            raw_response = cls._call_provider(prompt)
            if not raw_response:
                return None

            enhanced = cls._parse_and_validate_response(raw_response, base_analysis)
            return enhanced
        except Exception as e:
            # Never log the API key or raw sensitive tokens
            logger.warning("[SkillSaathi AI] AI provider call skipped or failed: %s. Safe deterministic fallback active.", str(e))
            return None

    @classmethod
    def _build_grounded_prompt(
        cls,
        base: Dict[str, Any],
        student: Dict[str, Any],
        parent: Dict[str, Any],
        courses: list
    ) -> str:
        simplified_courses = [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "stream": c.get("stream"),
                "duration_months": c.get("duration_months"),
                "fees_inr": c.get("fees_inr"),
                "certification_body": c.get("certification_body"),
                "nsqf_level": c.get("nsqf_level"),
                "practical_hours": c.get("practical_hours"),
                "average_starting_salary_inr": c.get("career_outcome", {}).get("average_starting_salary_inr"),
                "location": c.get("location")
            }
            for c in courses[:4]
        ]

        system_instruction = (
            "You are SkillSaathi AI Family Career Counsellor for Indian Vocational Education (SIH26241).\n"
            "Your duty is to bridge differences between student aspirations and parent concerns objectively.\n\n"
            "STRICT RULES:\n"
            "1. Ground all recommendations ONLY in the provided course records and stated family profile.\n"
            "2. Never fabricate placement percentages, starting salaries, or government accreditations.\n"
            "3. Clearly distinguish verified course facts from local prototype demo data.\n"
            "4. Maintain a neutral, supportive, respectful tone. Never infer hidden psychological complexes or make personality diagnoses.\n"
            "5. Return STRICTLY valid JSON with keys: 'discussion_guide', 'unresolved_concerns', 'key_trade_off_summary', 'ai_counselling_note'."
        )

        user_content = json.dumps({
            "student_profile": student,
            "parent_profile": parent,
            "identified_disagreements": base.get("identified_disagreements", []),
            "shared_strengths": base.get("shared_strengths", []),
            "top_courses": simplified_courses
        }, indent=2)

        return f"{system_instruction}\n\nFAMILY INPUTS AND VERIFIED COURSES:\n{user_content}\n\nRespond ONLY in valid JSON format."

    @classmethod
    def _call_provider(cls, prompt: str) -> Optional[str]:
        api_key = settings.GEMINI_API_KEY.strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts:
                            return content_parts[0].get("text", "")
        except urllib.error.URLError as e:
            logger.warning("[SkillSaathi AI] Provider connection error: %s", str(e.reason if hasattr(e, 'reason') else e))
            return None
        except TimeoutError:
            logger.warning("[SkillSaathi AI] Provider request timed out after %s seconds", settings.LLM_TIMEOUT_SECONDS)
            return None
        except Exception as e:
            logger.warning("[SkillSaathi AI] Provider unexpected error: %s", str(e))
            return None

        return None

    @classmethod
    def _parse_and_validate_response(
        cls,
        raw_text: str,
        base_analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        try:
            # Clean possible markdown fences
            clean = raw_text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            parsed = json.loads(clean)
            if not isinstance(parsed, dict):
                return None

            # Merge safely without destroying baseline structure
            enhanced = dict(base_analysis)
            if "discussion_guide" in parsed and isinstance(parsed["discussion_guide"], list) and len(parsed["discussion_guide"]) > 0:
                enhanced["discussion_guide"] = parsed["discussion_guide"]

            if "unresolved_concerns" in parsed and isinstance(parsed["unresolved_concerns"], list):
                enhanced["unresolved_concerns"] = parsed["unresolved_concerns"]

            if "key_trade_off_summary" in parsed and isinstance(parsed["key_trade_off_summary"], str) and enhanced.get("pathway_comparison"):
                enhanced["pathway_comparison"]["key_trade_off_summary"] = parsed["key_trade_off_summary"]

            enhanced["counselling_mode"] = "ai_grounded"
            enhanced["counselling_mode_note"] = (
                parsed.get("ai_counselling_note") or
                "Synthesized via Gemini Grounded AI using verified course records and stated family constraints."
            )
            return enhanced
        except json.JSONDecodeError:
            logger.warning("[SkillSaathi AI] Failed to parse JSON from AI response. Falling back.")
            return None
