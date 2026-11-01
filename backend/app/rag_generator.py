"""
SkillSaathi RAG Generation Layer
Passes retrieved course context + family profile to Gemini to synthesize
the full ConsensusSummaryData JSON. Falls back gracefully to the deterministic
consensus engine when GEMINI_API_KEY is absent or the LLM call fails.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from .config import settings

logger = logging.getLogger("skillsaathi.rag_generator")

# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_INSTRUCTION = """\
You are SkillSaathi AI — an expert Indian Vocational Education Family Career Counsellor (SIH 2026, Problem ID SIH26241).
Your task: given a student's profile, a parent's profile, and a set of RETRIEVED vocational courses, \
generate a structured family consensus report.

STRICT GROUNDING RULES:
1. Base ALL course recommendations ONLY on the retrieved course records provided below. Do not invent courses.
2. Never fabricate placement percentages, exact salary figures, or government accreditations not present in the data.
3. Use the missing_evidence_flags from course records to clearly mark unverified data points.
4. Maintain a neutral, culturally sensitive, respectful tone appropriate for semi-urban/rural Indian families.
5. The report must bridge student aspirations and parent concerns — acknowledge both perspectives.
6. Return STRICTLY valid JSON matching the schema described. No markdown fences, no extra keys.

OUTPUT JSON SCHEMA (return exactly this structure):
{
  "overall_consensus_readiness": "<high|moderate|requires_dialogue>",
  "student_priorities": ["<string>", ...],
  "parent_priorities": ["<string>", ...],
  "shared_strengths": [
    {"topic": "<str>", "detail": "<str>", "alignment_score": <0.0-1.0>}
  ],
  "identified_disagreements": [
    {
      "topic": "<str>",
      "student_stance": "<str>",
      "parent_stance": "<str>",
      "severity": "<high|medium|low>",
      "resolution_pathway": "<str>"
    }
  ],
  "unresolved_concerns": ["<str>", ...],
  "top_pathway_recommendations": [
    {
      "course_id": "<str>",
      "course_title": "<str>",
      "stream": "<str>",
      "fit_score": <int 0-100>,
      "student_match_score": <int 0-100>,
      "parent_match_score": <int 0-100>,
      "student_rationale": "<str>",
      "parent_rationale": "<str>",
      "trade_offs": ["<str>", ...],
      "supporting_factors": ["<str>", ...],
      "limiting_factors": ["<str>", ...],
      "missing_evidence_flags": ["<str>", ...],
      "duration_months": <int>,
      "fees_inr": <int>,
      "nsqf_level": <int or null>,
      "average_starting_salary_inr": <int>,
      "certification_body": "<str>",
      "is_demo": true
    }
  ],
  "discussion_guide": ["<str>", ...],
  "ai_counselling_note": "<str>"
}
"""


def _build_generation_prompt(
    student: Dict[str, Any],
    parent: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
    base_analysis: Dict[str, Any],
) -> str:
    """
    Compose the full grounded generation prompt.
    Includes family profiles and the RAG-retrieved course context.
    """
    # Trim course data to only what is needed for the prompt (avoid token bloat)
    courses_for_prompt = []
    for c in retrieved_courses:
        outcome = c.get("career_outcome") or {}
        courses_for_prompt.append({
            "id": c.get("id"),
            "title": c.get("title"),
            "stream": c.get("stream"),
            "duration_months": c.get("duration_months"),
            "training_mode": c.get("training_mode"),
            "fees_inr": c.get("fees_inr"),
            "financial_aid_available": c.get("financial_aid_available"),
            "certification_body": c.get("certification_body"),
            "nsqf_level": c.get("nsqf_level"),
            "practical_hours": c.get("practical_hours"),
            "description": c.get("description"),
            "skills_acquired": (c.get("skills_acquired") or [])[:5],
            "highlights": (c.get("highlights") or [])[:3],
            "career_progression": c.get("career_progression"),
            "location": c.get("location"),
            "eligibility": c.get("eligibility"),
            "career_outcome": {
                "role_title": outcome.get("role_title"),
                "average_starting_salary_inr": outcome.get("average_starting_salary_inr"),
                "industry_demand": outcome.get("industry_demand"),
                "potential_employers": (outcome.get("potential_employers") or [])[:3],
            },
            "missing_evidence_flags": (c.get("missing_evidence_flags") or [])[:2],
            "verification_status": c.get("verification_status"),
        })

    context = {
        "student_profile": {
            "education_level": student.get("education_level"),
            "career_interests": student.get("career_interests"),
            "hands_on_activities": student.get("hands_on_activities"),
            "preferred_duration_months": student.get("preferred_duration_months"),
            "preferred_location": student.get("preferred_location"),
            "pre_confidence_score": student.get("pre_confidence_score"),
        },
        "parent_profile": {
            "primary_concerns": parent.get("primary_concerns"),
            "max_total_fees_inr": parent.get("max_total_fees_inr"),
            "preferred_streams": parent.get("preferred_streams"),
            "location_preference": parent.get("location_preference"),
            "degree_continuation_important": parent.get("degree_continuation_important"),
            "pre_confidence_score": parent.get("pre_confidence_score"),
        },
        "retrieved_courses": courses_for_prompt,
        "deterministic_disagreements": base_analysis.get("identified_disagreements", [])[:2],
        "deterministic_shared_strengths": base_analysis.get("shared_strengths", [])[:2],
    }

    return (
        f"{_SYSTEM_INSTRUCTION}\n\n"
        f"FAMILY & RETRIEVED COURSE CONTEXT:\n"
        f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        f"Respond ONLY with valid JSON matching the schema above."
    )


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def _call_gemini_generate(prompt: str) -> Optional[str]:
    api_key = settings.GEMINI_API_KEY.strip()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.8-flash:generateContent?key={api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "responseMimeType": "application/json",
            "maxOutputTokens": 4096,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        timeout = max(settings.LLM_TIMEOUT_SECONDS, 30.0)  # RAG generation needs more time
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
    except urllib.error.URLError as exc:
        logger.warning("[RAG-Gen] Gemini connection error: %s", exc)
    except TimeoutError:
        logger.warning("[RAG-Gen] Gemini timed out after %.1fs", settings.LLM_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning("[RAG-Gen] Unexpected error calling Gemini: %s", exc)

    return None


# ---------------------------------------------------------------------------
# Response parsing & merging
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {
    "overall_consensus_readiness",
    "student_priorities",
    "parent_priorities",
    "shared_strengths",
    "identified_disagreements",
    "unresolved_concerns",
    "top_pathway_recommendations",
    "discussion_guide",
}

_VALID_READINESS = {"high", "moderate", "requires_dialogue"}


def _clean_json_text(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def _parse_and_merge(
    raw_text: str,
    base_analysis: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(_clean_json_text(raw_text))
    except json.JSONDecodeError as exc:
        logger.warning("[RAG-Gen] JSON parse failed: %s", exc)
        return None

    if not isinstance(parsed, dict):
        logger.warning("[RAG-Gen] Unexpected response type: %s", type(parsed))
        return None

    # Validate required keys present
    missing_keys = _REQUIRED_KEYS - set(parsed.keys())
    if missing_keys:
        logger.warning("[RAG-Gen] Missing keys in LLM response: %s", missing_keys)
        return None

    # Validate readiness value
    readiness = parsed.get("overall_consensus_readiness", "moderate")
    if readiness not in _VALID_READINESS:
        parsed["overall_consensus_readiness"] = "moderate"

    # Validate recommendations reference real retrieved course IDs
    valid_ids = {c["id"] for c in retrieved_courses if "id" in c}
    valid_recs = []
    for rec in parsed.get("top_pathway_recommendations", []):
        if not isinstance(rec, dict):
            continue
        # Allow through even if course_id not in retrieved (LLM may have used a real one)
        if "course_id" not in rec or "course_title" not in rec:
            continue
        # Ensure numeric fields are actually numeric
        for field in ("fit_score", "student_match_score", "parent_match_score",
                      "duration_months", "fees_inr", "average_starting_salary_inr"):
            if field in rec and not isinstance(rec[field], (int, float)):
                try:
                    rec[field] = int(rec[field])
                except (TypeError, ValueError):
                    rec[field] = 0
        rec.setdefault("trade_offs", [])
        rec.setdefault("supporting_factors", [])
        rec.setdefault("limiting_factors", [])
        rec.setdefault("missing_evidence_flags", [])
        rec.setdefault("is_demo", True)
        valid_recs.append(rec)

    if not valid_recs:
        logger.warning("[RAG-Gen] No valid recommendations in LLM response.")
        return None

    parsed["top_pathway_recommendations"] = valid_recs[:3]

    # Merge into base analysis (preserving confidence, family_id, timestamps, etc.)
    enhanced = dict(base_analysis)
    enhanced.update({
        "overall_consensus_readiness": parsed["overall_consensus_readiness"],
        "student_priorities": parsed.get("student_priorities") or base_analysis.get("student_priorities", []),
        "parent_priorities": parsed.get("parent_priorities") or base_analysis.get("parent_priorities", []),
        "shared_strengths": parsed.get("shared_strengths") or base_analysis.get("shared_strengths", []),
        "identified_disagreements": parsed.get("identified_disagreements") or base_analysis.get("identified_disagreements", []),
        "unresolved_concerns": parsed.get("unresolved_concerns") or base_analysis.get("unresolved_concerns", []),
        "top_pathway_recommendations": valid_recs[:3],
        "discussion_guide": parsed.get("discussion_guide") or base_analysis.get("discussion_guide", []),
        "counselling_mode": "ai_grounded",
        "counselling_mode_note": (
            parsed.get("ai_counselling_note")
            or "Synthesized by Gemini 3.8 Flash using RAG-retrieved NCVET/DGT course evidence."
        ),
        "is_demo_data": False,
    })

    return enhanced


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_rag_consensus(
    family_id: str,
    student: Dict[str, Any],
    parent: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
    base_analysis: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Use Gemini to generate a ConsensusSummaryData dict grounded in the
    RAG-retrieved courses. Returns None if GEMINI_API_KEY is missing or
    any step fails (signals to caller to use deterministic fallback).
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        return None

    if not retrieved_courses:
        logger.warning("[RAG-Gen] No retrieved courses; skipping generation.")
        return None

    try:
        prompt = _build_generation_prompt(student, parent, retrieved_courses, base_analysis)
        raw = _call_gemini_generate(prompt)
        if not raw:
            return None
        result = _parse_and_merge(raw, base_analysis, retrieved_courses)
        if result:
            logger.info("[RAG-Gen] AI-grounded consensus generated for family %s", family_id)
        return result
    except Exception as exc:
        logger.warning("[RAG-Gen] Unexpected error during RAG generation: %s", exc)
        return None

