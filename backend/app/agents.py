"""
SkillSaathi Multi-Agent Debate Architecture — Standalone Advocate Agents
=========================================================================
Defines specialized autonomous advocate agents for the multi-agent debate
pipeline:

  1. student_advocate_agent — Advocates strongly for the student's personal
     passions, vocational interests, learning styles, and long-term career
     growth based on retrieved course evidence.

  2. parent_advocate_agent — Advocates pragmatically for family financial
     stability, upfront fee limits, job security/placement assurance,
     accreditation credibility, and degree continuation pathways.

Both agents leverage ChatGoogleGenerativeAI (Gemini 3.8 Flash) with strict
persona system prompts grounded in Indian vocational education realities.
"""

from __future__ import annotations

from langchain_ollama import ChatOllama
import json
import logging
from typing import Any, Dict, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from .config import settings

logger = logging.getLogger("skillsaathi.agents")

# ---------------------------------------------------------------------------
# System Prompts Defining Distinct Personas
# ---------------------------------------------------------------------------

STUDENT_ADVOCATE_SYSTEM_PROMPT = """\
You are the Student Career Advocate in the SkillSaathi Multi-Agent Guidance System (SIH 2026).
Your sole mission is to be the passionate, empowering, and articulate voice of the student.

YOUR CORE MANDATE:
1. Champion the student's genuine vocational interests, creative drive, and hands-on passions.
2. Defend why intrinsic interest and active engagement lead to technical mastery, career resilience, and high long-term earnings.
3. Review the RETRIEVED VOCATIONAL COURSES and highlight specific programs that align best with what the student actually wants to build or do.
4. Address duration and training preferences (e.g. practical workshops, modern tech, creative media, hands-on tasks).
5. Respectfully counter the notion that traditional rote degrees or parental expectations must automatically supersede vocational talent.

OUTPUT REQUIREMENTS:
- Provide a structured, compelling argument (2-3 punchy paragraphs or bulleted points).
- Cite specific course titles, streams, and skills from the retrieved course evidence.
- Maintain a respectful, inspiring, and culturally grounded Indian vocational counseling tone.
- Do not output markdown code blocks or JSON; return persuasive natural language text.
"""

PARENT_ADVOCATE_SYSTEM_PROMPT = """\
You are the Parent Welfare & Security Advocate in the SkillSaathi Multi-Agent Guidance System (SIH 2026).
Your sole mission is to represent the protective, practical, and financial interests of the student's family.

YOUR CORE MANDATE:
1. Champion household financial safety: scrutinize upfront fees, tool/training costs, and family budget limits.
2. Demand verifiable job security: prioritize high placement demand, immediate starting wages, and reliable employer hiring links.
3. Insist on formal credibility: favor government-recognized frameworks (NCVET, DGT, NSDC, ITI, Polytechnic) over unverified private credentials.
4. Scrutinize location and duration risks: protect against unreasonable relocation or prolonged, risky training tracks.
5. Emphasize future academic progression: advocate for NCrF credit bridges to B.Voc / university degrees under NEP 2020.

OUTPUT REQUIREMENTS:
- Provide a structured, pragmatic argument (2-3 persuasive paragraphs or bulleted points).
- Scrutinize the retrieved courses explicitly against fee ceilings, verified starting salaries, and accreditation bodies.
- Acknowledge the student's enthusiasm while firmly guarding against economic vulnerability or unverified claims.
- Do not output markdown code blocks or JSON; return persuasive natural language text.
"""


# ---------------------------------------------------------------------------
# Context Formatting Helper
# ---------------------------------------------------------------------------

def _summarize_courses(courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format retrieved courses for prompt clarity without token bloat."""
    summaries = []
    for c in courses:
        outcome = c.get("career_outcome") or {}
        summaries.append({
            "id": c.get("id"),
            "title": c.get("title"),
            "stream": c.get("stream"),
            "duration_months": c.get("duration_months"),
            "training_mode": c.get("training_mode"),
            "fees_inr": c.get("fees_inr"),
            "financial_aid_available": c.get("financial_aid_available"),
            "certification_body": c.get("certification_body"),
            "nsqf_level": c.get("nsqf_level"),
            "skills_acquired": (c.get("skills_acquired") or [])[:5],
            "average_starting_salary_inr": outcome.get("average_starting_salary_inr"),
            "industry_demand": outcome.get("industry_demand"),
            "missing_evidence_flags": c.get("missing_evidence_flags") or [],
            "verification_status": c.get("verification_status"),
        })
    return summaries


# ---------------------------------------------------------------------------
# Agent 1: Student Advocate Agent
# ---------------------------------------------------------------------------

def student_advocate_agent(
    student_profile: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
    model_name: str = "gemini-3.8-flash",
) -> str:
    """
    Evaluates student profile and retrieved courses, generating a strong,
    evidence-backed argument championing the student's career aspirations.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        # Deterministic fallback when Gemini API key is unconfigured
        interests = ", ".join(student_profile.get("career_interests", [])) or "chosen vocational track"
        return (
            f"[Student Advocate - Deterministic Baseline] The student demonstrates high motivation for {interests}. "
            f"Retrieved courses provide structured, hands-on curricula that match their learning style. "
            f"Fostering intrinsic passion here will yield greater technical mastery and career longevity."
        )

    # llm = ChatGoogleGenerativeAI(
    #     model=model_name,
    #     google_api_key=settings.GEMINI_API_KEY.strip(),
    #     max_output_tokens=1024,
    # )

    llm = ChatOllama(model="llama3.2", temperature=0)

    context = {
        "student_profile": {
            "student_name": student_profile.get("student_name", "Student"),
            "education_level": student_profile.get("education_level"),
            "career_interests": student_profile.get("career_interests", []),
            "hands_on_activities": student_profile.get("hands_on_activities", []),
            "preferred_duration_months": student_profile.get("preferred_duration_months"),
            "preferred_location": student_profile.get("preferred_location"),
            "pre_confidence_score": student_profile.get("pre_confidence_score"),
        },
        "retrieved_courses": _summarize_courses(retrieved_courses),
    }

    user_prompt = (
        f"STUDENT PROFILE & RETRIEVED COURSES CONTEXT:\n"
        f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        f"Build a powerful, evidence-grounded advocacy statement for this student's preferred vocational pathways."
    )

    messages = [
        SystemMessage(content=STUDENT_ADVOCATE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content if response and response.content else ""
        # Gemini may return a list of content parts; coerce to str
        argument = raw if isinstance(raw, str) else " ".join(str(p) for p in raw)
        return argument.strip()
    except Exception as exc:
        logger.warning("[StudentAdvocateAgent] Call failed (%s): %s", model_name, exc)
        return (
            f"[Student Advocate] Advocating for student's focus on "
            f"{', '.join(student_profile.get('career_interests', []))}. "
            f"Retrieved practical courses enable direct industry skill acquisition and higher engagement."
        )


# ---------------------------------------------------------------------------
# Agent 2: Parent Advocate Agent
# ---------------------------------------------------------------------------

def parent_advocate_agent(
    parent_profile: Dict[str, Any],
    retrieved_courses: List[Dict[str, Any]],
    model_name: str = "gemini-3.8-flash",
) -> str:
    """
    Evaluates parent profile and retrieved courses, generating a strong,
    pragmatic argument centered on financial risk, ROI, and job security.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        # Deterministic fallback when Gemini API key is unconfigured
        concerns = ", ".join(parent_profile.get("primary_concerns", [])) or "cost and job security"
        max_fees = parent_profile.get("max_total_fees_inr", "specified limits")
        return (
            f"[Parent Advocate - Deterministic Baseline] Priority must remain on family stability and addressing {concerns}. "
            f"Any recommended course must fall within the INR {max_fees} fee ceiling and feature verified government "
            f"accreditation (NCVET/DGT) with clear placement pathways."
        )

    # llm = ChatGoogleGenerativeAI(
    #     model=model_name,
    #     google_api_key=settings.GEMINI_API_KEY.strip(),
    #     max_output_tokens=1024,
    # )

    llm = ChatOllama(model="llama3.2", temperature=0)

    context = {
        "parent_profile": {
            "parent_name": parent_profile.get("parent_name", "Parent"),
            "primary_concerns": parent_profile.get("primary_concerns", []),
            "max_total_fees_inr": parent_profile.get("max_total_fees_inr"),
            "preferred_streams": parent_profile.get("preferred_streams", []),
            "location_preference": parent_profile.get("location_preference"),
            "degree_continuation_important": parent_profile.get("degree_continuation_important", True),
            "pre_confidence_score": parent_profile.get("pre_confidence_score"),
        },
        "retrieved_courses": _summarize_courses(retrieved_courses),
    }

    user_prompt = (
        f"PARENT PROFILE & RETRIEVED COURSES CONTEXT:\n"
        f"{json.dumps(context, indent=2, ensure_ascii=False)}\n\n"
        f"Build a rigorous, welfare-centered advocacy statement safeguarding this family's financial and stability priorities."
    )

    messages = [
        SystemMessage(content=PARENT_ADVOCATE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content if response and response.content else ""
        # Gemini may return a list of content parts; coerce to str
        argument = raw if isinstance(raw, str) else " ".join(str(p) for p in raw)
        return argument.strip()
    except Exception as exc:
        logger.warning("[ParentAdvocateAgent] Call failed (%s): %s", model_name, exc)
        return (
            f"[Parent Advocate] Advocating for risk reduction on {', '.join(parent_profile.get('primary_concerns', []))}. "
            f"Recommended options must prioritize low fees (<= INR {parent_profile.get('max_total_fees_inr', 'Budget')}) "
            f"and verified institutional credentials."
        )

