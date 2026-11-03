"""
SkillSaathi RAG Generation Layer — LangGraph Self-Correction Architecture
=========================================================================
Replaces the linear pipeline with a stateful LangGraph graph that:

  1. Generator Node  — calls ChatGoogleGenerativeAI (Gemini) with the full
                       grounding prompt. On retry iterations it appends the
                       prior ValidationError string so the model can correct
                       its own JSON schema mistakes.

  2. Evaluator Node  — validates the raw LLM text against the existing
                       ConsensusSummaryResponse Pydantic model.
                       • Success → writes `final_parsed_response`, routes to END.
                       • Failure → appends ValidationError to `errors`,
                                   increments `generation_attempts`.

  3. Conditional Edge — if attempts >= MAX_RETRIES → Fallback Node (safe
                        deterministic defaults).
                        Otherwise → back to Generator Node.

  4. Fallback Node   — returns the deterministic base_analysis dict untouched,
                       tagged as counselling_mode='deterministic'.

Public surface:
  generate_rag_consensus(family_id, student, parent, retrieved_courses,
                          base_analysis, model_name) -> (dict | None, str | None)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import ValidationError

from .config import settings
from .schemas import ConsensusSummaryResponse

# LangGraph / LangChain imports
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("skillsaathi.rag_generator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 3  # after 3 failed attempts → deterministic fallback

_VALID_READINESS = {"high", "moderate", "requires_dialogue"}

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

# ---------------------------------------------------------------------------
# LangGraph State
# ---------------------------------------------------------------------------

class ConsensusState(TypedDict):
    """Mutable state passed between every node in the LangGraph graph."""
    # Input context (set once at graph invocation)
    student_profile: Dict[str, Any]
    parent_profile: Dict[str, Any]
    retrieved_courses: List[Dict[str, Any]]
    base_analysis: Dict[str, Any]
    model_name: str
    family_id: str

    # Self-correction bookkeeping
    generation_attempts: int
    errors: List[str]

    # Output
    raw_llm_text: Optional[str]
    final_parsed_response: Optional[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Prompt helpers  (preserved from original pipeline)
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

_CORRECTION_PREAMBLE = """\
Your PREVIOUS response contained JSON schema errors that failed Pydantic validation.
You MUST fix ALL of the following errors in your next response.
Every field that requires a plain string must be a string — never a dict or list.
Return ONLY the corrected JSON object with no markdown fences.

VALIDATION ERRORS FROM PREVIOUS ATTEMPT:
"""


def _build_courses_for_prompt(retrieved_courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    return courses_for_prompt


def _build_generation_prompt(
    student: Dict[str, Any],
    parent: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
    base_analysis: Dict[str, Any],
    prior_errors: Optional[List[str]] = None,
) -> str:
    """
    Compose the full grounded generation prompt.
    When prior_errors is non-empty the prompt is prepended with a correction
    instruction listing the exact Pydantic ValidationError messages.
    """
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
        "retrieved_courses": _build_courses_for_prompt(retrieved_courses),
        "deterministic_disagreements": base_analysis.get("identified_disagreements", [])[:2],
        "deterministic_shared_strengths": base_analysis.get("shared_strengths", [])[:2],
    }

    prefix = ""
    if prior_errors:
        error_block = "\n".join(f"  - {e}" for e in prior_errors)
        prefix = f"{_CORRECTION_PREAMBLE}{error_block}\n\n"

    return (
        f"{prefix}{_SYSTEM_INSTRUCTION}\n\n"
        f"FAMILY & RETRIEVED COURSE CONTEXT:\n"
        f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        f"Respond ONLY with valid JSON matching the schema above."
    )


# ---------------------------------------------------------------------------
# JSON text cleaning  (preserved from original)
# ---------------------------------------------------------------------------

def _clean_json_text(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


# ---------------------------------------------------------------------------
# Recommendation coercion helper
# ---------------------------------------------------------------------------

def _coerce_recommendations(recs: Any) -> List[Dict[str, Any]]:
    """
    Coerce each recommendation's numeric fields to int and set list defaults.
    Returns only structurally valid recommendation dicts.
    """
    if not isinstance(recs, list):
        return []

    valid: List[Dict[str, Any]] = []
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        if "course_id" not in rec or "course_title" not in rec:
            continue
        for field in (
            "fit_score", "student_match_score", "parent_match_score",
            "duration_months", "fees_inr", "average_starting_salary_inr",
        ):
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
        valid.append(rec)

    return valid


# ---------------------------------------------------------------------------
# LangGraph Node: Generator
# ---------------------------------------------------------------------------

def generator_node(state: ConsensusState) -> ConsensusState:
    """
    Calls ChatGoogleGenerativeAI with the grounding prompt.
    On retry iterations (errors non-empty) prepends a correction preamble
    so the model knows exactly what schema mistakes to fix.
    """
    model_name = state["model_name"]
    prior_errors = state.get("errors") or []

    logger.info(
        "[LangGraph][Generator] Attempt %d for family %s using %s",
        state["generation_attempts"] + 1,
        state["family_id"],
        model_name,
    )

    prompt_text = _build_generation_prompt(
        student=state["student_profile"],
        parent=state["parent_profile"],
        retrieved_courses=state["retrieved_courses"],
        base_analysis=state["base_analysis"],
        prior_errors=prior_errors if state["generation_attempts"] > 0 else None,
    )

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.25,
            max_output_tokens=4096,
        )
        response = llm.invoke([
            SystemMessage(content="You are a precise JSON-only generation assistant. Never output markdown fences."),
            HumanMessage(content=prompt_text),
        ])
        raw_text: Optional[str] = response.content if response and response.content else None
    except Exception as exc:
        logger.warning("[LangGraph][Generator] LLM call failed: %s", exc)
        raw_text = None
        new_errors = list(state.get("errors") or [])
        new_errors.append(f"LLM call failed on attempt {state['generation_attempts'] + 1}: {str(exc)}")
        return {
            **state,
            "raw_llm_text": None,
            "generation_attempts": state["generation_attempts"] + 1,
            "errors": new_errors,
        }

    return {
        **state,
        "raw_llm_text": raw_text,
        "generation_attempts": state["generation_attempts"] + 1,
    }


# ---------------------------------------------------------------------------
# LangGraph Node: Evaluator
# ---------------------------------------------------------------------------

def evaluator_node(state: ConsensusState) -> ConsensusState:
    """
    Validates the raw LLM text by:
      1. JSON-parsing it.
      2. Coercing recommendation numeric fields.
      3. Merging with base_analysis to produce a full ConsensusSummaryResponse dict.
      4. Running pydantic model_validate() — catches hallucinated field types.

    On success  → writes `final_parsed_response`.
    On failure  → appends error string to `errors`.
    """
    raw_text = state.get("raw_llm_text")
    base_analysis = state["base_analysis"]
    model_name = state["model_name"]

    if not raw_text:
        new_errors = list(state.get("errors") or [])
        new_errors.append("Generator returned empty response.")
        return {**state, "errors": new_errors}

    # ── Step 1: Parse JSON ─────────────────────────────────────────────────
    try:
        parsed = json.loads(_clean_json_text(raw_text))
    except json.JSONDecodeError as exc:
        new_errors = list(state.get("errors") or [])
        new_errors.append(f"JSON parse error: {exc}")
        logger.warning("[LangGraph][Evaluator] JSON parse failed: %s", exc)
        return {**state, "errors": new_errors}

    if not isinstance(parsed, dict):
        new_errors = list(state.get("errors") or [])
        new_errors.append(f"Expected JSON object (dict), got {type(parsed).__name__}.")
        return {**state, "errors": new_errors}

    # ── Step 2: Structural key check ───────────────────────────────────────
    missing_keys = _REQUIRED_KEYS - set(parsed.keys())
    if missing_keys:
        new_errors = list(state.get("errors") or [])
        new_errors.append(f"LLM response missing required keys: {', '.join(sorted(missing_keys))}")
        logger.warning("[LangGraph][Evaluator] Missing keys: %s", missing_keys)
        return {**state, "errors": new_errors}

    # ── Step 3: Coerce recommendations ─────────────────────────────────────
    valid_recs = _coerce_recommendations(parsed.get("top_pathway_recommendations", []))
    if not valid_recs:
        new_errors = list(state.get("errors") or [])
        new_errors.append(
            "top_pathway_recommendations is empty or all entries are structurally invalid. "
            "Each recommendation must have 'course_id' and 'course_title' as plain strings."
        )
        return {**state, "errors": new_errors}

    # Fix readiness enum
    if parsed.get("overall_consensus_readiness") not in _VALID_READINESS:
        parsed["overall_consensus_readiness"] = "moderate"

    # ── Step 4: Merge with base_analysis ───────────────────────────────────
    candidate = dict(base_analysis)
    candidate.update({
        "overall_consensus_readiness": parsed["overall_consensus_readiness"],
        "student_priorities": parsed.get("student_priorities") or base_analysis.get("student_priorities", []),
        "parent_priorities": parsed.get("parent_priorities") or base_analysis.get("parent_priorities", []),
        "shared_strengths": parsed.get("shared_strengths") or base_analysis.get("shared_strengths", []),
        "identified_disagreements": parsed.get("identified_disagreements") or base_analysis.get("identified_disagreements", []),
        "unresolved_concerns": parsed.get("unresolved_concerns") or base_analysis.get("unresolved_concerns", []),
        "top_pathway_recommendations": valid_recs[:3],
        "discussion_guide": parsed.get("discussion_guide") or base_analysis.get("discussion_guide", []),
        "counselling_mode": "ai_grounded",
        "counselling_model": model_name,
        "counselling_mode_note": (
            parsed.get("ai_counselling_note")
            or f"Synthesized by {model_name} using RAG-retrieved NCVET/DGT course evidence."
        ),
        "is_demo_data": False,
    })

    # ── Step 5: Pydantic validation ─────────────────────────────────────────
    try:
        ConsensusSummaryResponse.model_validate(candidate)
    except ValidationError as exc:
        # Extract human-readable error strings for the correction prompt
        error_strings: List[str] = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            msg = error["msg"]
            error_strings.append(f"Field '{loc}': {msg}")

        new_errors = list(state.get("errors") or [])
        new_errors.extend(error_strings)
        logger.warning(
            "[LangGraph][Evaluator] Pydantic validation failed (%d errors): %s",
            len(error_strings),
            "; ".join(error_strings[:3]),
        )
        return {**state, "errors": new_errors}

    # ── Success ────────────────────────────────────────────────────────────
    logger.info(
        "[LangGraph][Evaluator] Validation passed on attempt %d for family %s",
        state["generation_attempts"],
        state["family_id"],
    )
    return {**state, "final_parsed_response": candidate}


# ---------------------------------------------------------------------------
# LangGraph Node: Fallback
# ---------------------------------------------------------------------------

def fallback_node(state: ConsensusState) -> ConsensusState:
    """
    Invoked when MAX_RETRIES is exhausted.
    Tags the deterministic base_analysis as the safe fallback output.
    """
    logger.warning(
        "[LangGraph][Fallback] Max retries (%d) reached for family %s. "
        "Returning deterministic base_analysis. Accumulated errors: %s",
        MAX_RETRIES,
        state["family_id"],
        state.get("errors"),
    )
    fallback = dict(state["base_analysis"])
    fallback.update({
        "counselling_mode": "deterministic",
        "counselling_model": None,
        "counselling_mode_note": (
            "AI generation exhausted after self-correction retries. "
            "Evaluated using SkillSaathi Evidence-Grounded Consensus Engine."
        ),
        "is_demo_data": True,
    })
    return {**state, "final_parsed_response": fallback}


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def _route_after_evaluator(state: ConsensusState) -> str:
    """
    Routing logic after the Evaluator node:
      • Parsed successfully          → END
      • Attempts exhausted           → "fallback"
      • Otherwise                    → "generator"  (retry)
    """
    if state.get("final_parsed_response") is not None:
        return END
    if state["generation_attempts"] >= MAX_RETRIES:
        return "fallback"
    return "generator"


# ---------------------------------------------------------------------------
# Graph compilation  (module-level singleton)
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    graph = StateGraph(ConsensusState)

    graph.add_node("generator", generator_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("generator")
    graph.add_edge("generator", "evaluator")
    graph.add_conditional_edges("evaluator", _route_after_evaluator, {
        END: END,
        "generator": "generator",
        "fallback": "fallback",
    })
    graph.add_edge("fallback", END)

    return graph.compile()


_consensus_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_rag_consensus(
    family_id: str,
    student: Dict[str, Any],
    parent: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
    base_analysis: Dict[str, Any],
    model_name: str = "gemini-3.8-flash",
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Invoke the LangGraph self-correction pipeline.

    Returns:
        (result_dict, None)        on success (ai_grounded or deterministic fallback)
        (None, error_string)       only if GEMINI_API_KEY is missing or courses empty
                                   (pre-flight failures; graph is never invoked)
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        return None, "GEMINI_API_KEY is not configured in backend/.env"

    if not retrieved_courses:
        logger.warning("[LangGraph] No retrieved courses; skipping RAG generation.")
        return None, "No relevant courses retrieved from vector store."

    initial_state: ConsensusState = {
        "student_profile": student,
        "parent_profile": parent,
        "retrieved_courses": retrieved_courses,
        "base_analysis": base_analysis,
        "model_name": model_name,
        "family_id": family_id,
        "generation_attempts": 0,
        "errors": [],
        "raw_llm_text": None,
        "final_parsed_response": None,
    }

    try:
        final_state: ConsensusState = _consensus_graph.invoke(initial_state)
    except Exception as exc:
        logger.warning("[LangGraph] Graph invocation failed: %s", exc)
        return None, f"Unexpected error during RAG generation: {str(exc)}"

    result = final_state.get("final_parsed_response")
    if result is not None:
        logger.info(
            "[LangGraph] Consensus generated for family %s (mode=%s, attempts=%d)",
            family_id,
            result.get("counselling_mode"),
            final_state["generation_attempts"],
        )
        return result, None

    # Should never reach here (fallback_node always sets final_parsed_response)
    accumulated_errors = "; ".join(final_state.get("errors") or [])
    return None, f"RAG generation failed after {MAX_RETRIES} attempts: {accumulated_errors}"
