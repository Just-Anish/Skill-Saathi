"""
SkillSaathi RAG Generation Layer — Multi-Agent Debate + LangGraph Self-Correction
==================================================================================
Graph topology (Phase 2: multi-agent debate wired into Phase 1 self-correction loop):

  START
    │
    ├──► student_advocate_node   ──┐
    │                              ├──► master_counselor_node ──► evaluator_node ──► END
    └──► parent_advocate_node   ──┘                                │
                                                                    ├──► generator_node (retry)
                                                                    └──► fallback_node  (exhausted)

Node responsibilities
─────────────────────
  student_advocate_node   — Calls student_advocate_agent(); writes state["student_argument"].
  parent_advocate_node    — Calls parent_advocate_agent();  writes state["parent_argument"].
  master_counselor_node   — Receives both advocate arguments + full context; produces raw JSON
                            (raw_llm_text) that the existing evaluator validates.
  generator_node          — Retry node: re-generates JSON on schema failure, injecting
                            accumulated Pydantic error strings into the prompt.
  evaluator_node          — Validates raw JSON against ConsensusSummaryResponse Pydantic model.
                            On success writes final_parsed_response; on failure appends errors.
  fallback_node           — Reached when generation_attempts >= MAX_RETRIES; returns safe
                            deterministic base_analysis tagged counselling_mode='deterministic'.

Public surface (unchanged):
  generate_rag_consensus(family_id, student, parent, retrieved_courses,
                          base_analysis, model_name) -> (dict | None, str | None)
"""

from __future__ import annotations

from langchain_ollama import ChatOllama

import json
import logging
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import ValidationError

from .config import settings
from .schemas import ConsensusSummaryResponse
from .agents import student_advocate_agent, parent_advocate_agent

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
# LangGraph State  (Phase 2: extended with advocate arguments)
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

    # Phase 2: advocate debate outputs (populated by advocate nodes)
    student_argument: str
    parent_argument: str

    # Self-correction bookkeeping
    generation_attempts: int
    errors: List[str]

    # LLM I/O
    raw_llm_text: Optional[str]
    final_parsed_response: Optional[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

_MASTER_COUNSELOR_SYSTEM = """\
You are the SkillSaathi Master Counsellor AI — the impartial, evidence-grounded arbiter of a \
multi-agent vocational career guidance debate (SIH 2026, Problem ID SIH26241).

You have received structured advocacy arguments from two specialist agents:
  • Student Career Advocate — champions the student's interests, passions, and preferred vocational paths.
  • Parent Welfare Advocate — champions family financial stability, accreditation, and job security.

YOUR TASK:
1. Weigh both arguments objectively against the RETRIEVED COURSE evidence.
2. Synthesize a balanced, grounded family consensus report that acknowledges both perspectives.
3. Recommend up to 3 SPECIFIC courses from the retrieved set that best resolve the debate.
4. Identify residual disagreements and construct a structured discussion guide.

STRICT RULES:
- Base ALL course recommendations ONLY on the retrieved course records. Do not invent courses.
- Never fabricate placement percentages, salary figures, or accreditations absent from the data.
- Use missing_evidence_flags to mark unverified data points.
- Return STRICTLY valid JSON. No markdown fences. No extra keys.

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

_RETRY_SYSTEM = """\
You are a precise JSON-only generation assistant for the SkillSaathi consensus pipeline.
You MUST fix ALL schema errors from the previous attempt listed in the prompt.
Every field requiring a plain string must be a string — never a dict or list.
Return ONLY the corrected JSON object. No markdown fences. No extra keys.
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


def _build_master_counselor_prompt(state: ConsensusState) -> str:
    """
    Constructs the Master Counselor prompt that incorporates both advocate
    arguments alongside the full family + course context.
    """
    context = {
        "student_advocate_argument": state["student_argument"],
        "parent_advocate_argument": state["parent_argument"],
        "student_profile": {
            "education_level": state["student_profile"].get("education_level"),
            "career_interests": state["student_profile"].get("career_interests"),
            "hands_on_activities": state["student_profile"].get("hands_on_activities"),
            "preferred_duration_months": state["student_profile"].get("preferred_duration_months"),
            "preferred_location": state["student_profile"].get("preferred_location"),
            "pre_confidence_score": state["student_profile"].get("pre_confidence_score"),
        },
        "parent_profile": {
            "primary_concerns": state["parent_profile"].get("primary_concerns"),
            "max_total_fees_inr": state["parent_profile"].get("max_total_fees_inr"),
            "preferred_streams": state["parent_profile"].get("preferred_streams"),
            "location_preference": state["parent_profile"].get("location_preference"),
            "degree_continuation_important": state["parent_profile"].get("degree_continuation_important"),
            "pre_confidence_score": state["parent_profile"].get("pre_confidence_score"),
        },
        "retrieved_courses": _build_courses_for_prompt(state["retrieved_courses"]),
        "deterministic_disagreements": state["base_analysis"].get("identified_disagreements", [])[:2],
        "deterministic_shared_strengths": state["base_analysis"].get("shared_strengths", [])[:2],
    }
    return (
        f"DEBATE ARGUMENTS & FAMILY CONTEXT:\n"
        f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        f"Arbitrate the debate and respond ONLY with valid JSON matching the schema above."
    )


def _build_retry_prompt(state: ConsensusState) -> str:
    """
    Constructs the retry prompt for generator_node, injecting prior Pydantic
    error strings so the model knows exactly which fields to fix.
    """
    error_block = "\n".join(f"  - {e}" for e in (state.get("errors") or []))
    base_context = {
        "student_profile": {
            "education_level": state["student_profile"].get("education_level"),
            "career_interests": state["student_profile"].get("career_interests"),
            "hands_on_activities": state["student_profile"].get("hands_on_activities"),
            "preferred_duration_months": state["student_profile"].get("preferred_duration_months"),
            "preferred_location": state["student_profile"].get("preferred_location"),
        },
        "parent_profile": {
            "primary_concerns": state["parent_profile"].get("primary_concerns"),
            "max_total_fees_inr": state["parent_profile"].get("max_total_fees_inr"),
            "preferred_streams": state["parent_profile"].get("preferred_streams"),
            "location_preference": state["parent_profile"].get("location_preference"),
            "degree_continuation_important": state["parent_profile"].get("degree_continuation_important"),
        },
        "retrieved_courses": _build_courses_for_prompt(state["retrieved_courses"]),
        "student_advocate_argument": state.get("student_argument", ""),
        "parent_advocate_argument": state.get("parent_argument", ""),
    }
    return (
        f"{_CORRECTION_PREAMBLE}{error_block}\n\n"
        f"FAMILY & RETRIEVED COURSE CONTEXT:\n"
        f"{json.dumps(base_context, indent=2, ensure_ascii=False)}\n\n"
        f"Respond ONLY with valid JSON matching the schema above."
    )


# ---------------------------------------------------------------------------
# JSON text cleaning
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
# LangGraph Node: Student Advocate
# ---------------------------------------------------------------------------

def student_advocate_node(state: ConsensusState) -> ConsensusState:
    """
    Wraps student_advocate_agent() as a LangGraph node.
    Writes state["student_argument"]; never raises — logs and falls back
    to an empty string so the graph can continue.
    """
    logger.info("[LangGraph][StudentAdvocate] Generating argument for family %s", state["family_id"])
    try:
        argument = student_advocate_agent(
            student_profile=state["student_profile"],
            retrieved_courses=state["retrieved_courses"],
            model_name=state["model_name"],
        )
    except Exception as exc:
        logger.warning("[LangGraph][StudentAdvocate] Agent call failed: %s", exc)
        argument = (
            f"Student advocate unavailable: {exc}. "
            f"Proceeding with student interests: "
            f"{', '.join(state['student_profile'].get('career_interests', []))}."
        )
    return {**state, "student_argument": argument}


# ---------------------------------------------------------------------------
# LangGraph Node: Parent Advocate
# ---------------------------------------------------------------------------

def parent_advocate_node(state: ConsensusState) -> ConsensusState:
    """
    Wraps parent_advocate_agent() as a LangGraph node.
    Writes state["parent_argument"]; never raises — logs and falls back.
    """
    logger.info("[LangGraph][ParentAdvocate] Generating argument for family %s", state["family_id"])
    try:
        argument = parent_advocate_agent(
            parent_profile=state["parent_profile"],
            retrieved_courses=state["retrieved_courses"],
            model_name=state["model_name"],
        )
    except Exception as exc:
        logger.warning("[LangGraph][ParentAdvocate] Agent call failed: %s", exc)
        argument = (
            f"Parent advocate unavailable: {exc}. "
            f"Proceeding with parent concerns: "
            f"{', '.join(state['parent_profile'].get('primary_concerns', []))}."
        )
    return {**state, "parent_argument": argument}


# ---------------------------------------------------------------------------
# LangGraph Node: Master Counselor
# ---------------------------------------------------------------------------

def master_counselor_node(state: ConsensusState) -> ConsensusState:
    """
    Arbitrates the student vs. parent debate and synthesises the first-pass
    raw JSON payload. Feeds raw_llm_text into the evaluator for Pydantic
    validation. This node only fires on the FIRST attempt (generation_attempts == 0).
    Subsequent retries are handled by generator_node.
    """
    model_name = state["model_name"]
    logger.info(
        "[LangGraph][MasterCounselor] Arbitrating debate for family %s using %s",
        state["family_id"],
        model_name,
    )

    prompt_text = _build_master_counselor_prompt(state)

    try:
        # llm = ChatGoogleGenerativeAI(
        #     model=model_name,
        #     google_api_key=settings.GEMINI_API_KEY,
        #     temperature=0.2,
        #     max_output_tokens=4096,
        # )
        llm = ChatOllama(model="llama3.2", temperature=0)
        
        response = llm.invoke([
            SystemMessage(content=_MASTER_COUNSELOR_SYSTEM),
            HumanMessage(content=prompt_text),
        ])
        raw_text: Optional[str] = response.content if response and response.content else None
    except Exception as exc:
        logger.warning("[LangGraph][MasterCounselor] LLM call failed: %s", exc)
        raw_text = None
        new_errors = list(state.get("errors") or [])
        new_errors.append(f"Master Counselor LLM call failed: {str(exc)}")
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
# LangGraph Node: Generator  (retry-only node)
# ---------------------------------------------------------------------------

def generator_node(state: ConsensusState) -> ConsensusState:
    """
    Retry node — only invoked when the Evaluator has detected a schema failure.
    Injects accumulated Pydantic error strings into the correction prompt so the
    model can fix precisely identified field type mistakes.
    """
    model_name = state["model_name"]

    logger.info(
        "[LangGraph][Generator] Retry attempt %d for family %s using %s",
        state["generation_attempts"] + 1,
        state["family_id"],
        model_name,
    )

    prompt_text = _build_retry_prompt(state)

    try:
        # llm = ChatGoogleGenerativeAI(
        #     model=model_name,
        #     google_api_key=settings.GEMINI_API_KEY,
        #     temperature=0.25,
        #     max_output_tokens=4096,
        # )
        llm = ChatOllama(model="llama3.2", temperature=0)

        response = llm.invoke([
            SystemMessage(content=_RETRY_SYSTEM),
            HumanMessage(content=prompt_text),
        ])
        raw_text: Optional[str] = response.content if response and response.content else None
    except Exception as exc:
        logger.warning("[LangGraph][Generator] LLM call failed: %s", exc)
        raw_text = None
        new_errors = list(state.get("errors") or [])
        new_errors.append(f"Generator retry failed on attempt {state['generation_attempts'] + 1}: {str(exc)}")
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
      2. Checking required keys are present.
      3. Coercing recommendation numeric fields.
      4. Merging with base_analysis to build a full ConsensusSummaryResponse dict.
      5. Running pydantic model_validate() — catches hallucinated field types.

    On success  → writes `final_parsed_response`.
    On failure  → appends error string to `errors` (triggers retry or fallback).
    """
    raw_text = state.get("raw_llm_text")
    base_analysis = state["base_analysis"]
    model_name = state["model_name"]

    if not raw_text:
        new_errors = list(state.get("errors") or [])
        new_errors.append("Generator/MasterCounselor returned empty response.")
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
            or f"Synthesized by {model_name} via multi-agent debate arbitration using RAG-retrieved NCVET/DGT course evidence."
        ),
        "is_demo_data": False,
    })

    # ── Step 5: Pydantic validation ─────────────────────────────────────────
    try:
        ConsensusSummaryResponse.model_validate(candidate)
    except ValidationError as exc:
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
    Never raises.
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
            "Multi-agent debate arbitration exhausted after self-correction retries. "
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
      • Otherwise                    → "generator"  (schema self-correction retry)
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

    # ── Register nodes ─────────────────────────────────────────────────────
    graph.add_node("student_advocate", student_advocate_node)
    graph.add_node("parent_advocate", parent_advocate_node)
    graph.add_node("master_counselor", master_counselor_node)
    graph.add_node("generator", generator_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("fallback", fallback_node)

    # ── Entry: fan-out to both advocate nodes sequentially ─────────────────
    # LangGraph does not natively fan-out from set_entry_point to multiple
    # nodes in a single edge; we chain them sequentially (student → parent →
    # master_counselor) which is functionally equivalent given shared state.
    graph.set_entry_point("student_advocate")
    graph.add_edge("student_advocate", "parent_advocate")

    # ── Both advocates feed into Master Counselor ──────────────────────────
    graph.add_edge("parent_advocate", "master_counselor")

    # ── Master Counselor → Evaluator (first-pass validation) ───────────────
    graph.add_edge("master_counselor", "evaluator")

    # ── Evaluator: conditional routing (self-correction loop) ──────────────
    graph.add_conditional_edges("evaluator", _route_after_evaluator, {
        END: END,
        "generator": "generator",   # schema error retry
        "fallback": "fallback",     # exhausted retries
    })

    # ── Generator retry loops back to Evaluator ────────────────────────────
    graph.add_edge("generator", "evaluator")

    # ── Fallback always terminates ─────────────────────────────────────────
    graph.add_edge("fallback", END)

    return graph.compile()


_consensus_graph = _build_graph()


# ---------------------------------------------------------------------------
# Public entry point  (signature unchanged — routes.py requires no edits)
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
    Invoke the multi-agent debate + LangGraph self-correction pipeline.

    Returns:
        (result_dict, None)        on success (ai_grounded or deterministic fallback)
        (None, error_string)       only for pre-flight failures (missing API key or
                                   empty courses); graph is never invoked in that case.
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
        # Phase 2 fields — populated by advocate nodes
        "student_argument": "",
        "parent_argument": "",
        # Self-correction bookkeeping
        "generation_attempts": 0,
        "errors": [],
        # LLM I/O
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

    # Should never reach here — fallback_node always sets final_parsed_response
    accumulated_errors = "; ".join(final_state.get("errors") or [])
    return None, f"RAG generation failed after {MAX_RETRIES} attempts: {accumulated_errors}"
