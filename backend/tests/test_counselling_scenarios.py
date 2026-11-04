"""
Phase 7 Scenario Tests for SkillSaathi Family Consensus Engine
Covers 4 core real-world family counseling scenarios (SIH26241).
"""

import pytest
from backend.app.agents.graph import (
    run_family_counselling,
    build_counselling_graph,
    get_counselling_state,
    resume_counselling_session
)
from backend.app.demo_courses_data import DEMO_COURSES


# ---------------------------------------------------------------------------
# Scenario A: Immediate High Alignment
# Both student and parent agree on technical stream and budget
# ---------------------------------------------------------------------------
def test_scenario_a_high_alignment():
    fam_id = "scenario-a-alignment-01"
    student = {
        "education_level": "10th_pass",
        "career_interests": ["manufacturing_engineering"],
        "hands_on_activities": ["precision_making"],
        "preferred_duration_months": 12,
        "district": "Pune",
        "state": "Maharashtra"
    }
    parent = {
        "primary_concerns": ["job_security"],
        "max_total_fees_inr": 25000,
        "preferred_streams": ["manufacturing_engineering"],
        "district": "Pune",
        "state": "Maharashtra"
    }

    result = run_family_counselling(
        family_id=fam_id,
        student_profile=student,
        parent_profile=parent,
        courses=DEMO_COURSES[:4],
        strict=False
    )

    summary = result.get("final_consensus_summary")
    assert summary is not None
    assert summary["overall_consensus_readiness"] in ["high", "moderate"]
    assert len(summary["top_pathway_recommendations"]) > 0

    # Ensure all agents participated
    agent_names = [msg.name for msg in result.get("messages", [])]
    assert "StudentAdvocate" in agent_names
    assert "ParentLiaison" in agent_names
    assert "FactChecker" in agent_names
    assert "ConsensusMediator" in agent_names


# ---------------------------------------------------------------------------
# Scenario B: Disagreement Resolved via Tools (NCrF & ROI)
# Student wants hands-on EV/Auto; Parent fears lack of degree & high fees
# ---------------------------------------------------------------------------
def test_scenario_b_disagreement_resolved_via_tools():
    fam_id = "scenario-b-mediation-02"
    student = {
        "education_level": "10th_pass",
        "career_interests": ["automotive"],
        "hands_on_activities": ["building_fixing"],
        "preferred_duration_months": 12,
        "district": "Pune",
        "state": "Maharashtra"
    }
    parent = {
        "primary_concerns": ["degree_progression", "fees_cost"],
        "max_total_fees_inr": 8000,
        "preferred_streams": ["it_tech"],  # parent wants traditional IT
        "district": "Pune",
        "state": "Maharashtra"
    }

    result = run_family_counselling(
        family_id=fam_id,
        student_profile=student,
        parent_profile=parent,
        courses=DEMO_COURSES[:4],
        strict=False
    )

    # Fact-Checker must have retrieved NCrF ladder and wage benchmark
    facts = result.get("verified_facts", [])
    categories = [f.get("category") for f in facts]
    assert "ncrf_ladder" in categories
    assert "wage_benchmark" in categories
    assert "roi_analysis" in categories

    summary = result.get("final_consensus_summary")
    assert summary is not None
    assert len(summary["discussion_guide"]) >= 2


# ---------------------------------------------------------------------------
# Scenario C: Critical Deadlock & Human-In-The-Loop Escalation
# Severe irreconcilable dispute halts the graph and pauses for counselor
# ---------------------------------------------------------------------------
def test_scenario_c_deadlock_and_hitl_escalation():
    fam_id = "scenario-c-deadlock-03"
    graph = build_counselling_graph(enable_hitl=True)

    state = {
        "family_id": fam_id,
        "messages": [],
        "student_profile": {"career_interests": ["creative_media"]},
        "parent_profile": {"primary_concerns": ["job_security"]},
        "student_advocate_notes": "Advocate analyzed aspirations.",
        "parent_liaison_notes": "Parent liaison analyzed objections.",
        "verified_facts": [{"category": "wages", "data": {}}],
        "disagreements": [
            {
                "topic": "Career Field Rejection",
                "severity": "critical",
                "student_stance": "Refuses any trade except Arts",
                "parent_stance": "Refuses to pay for Arts"
            }
        ],
        "iteration_count": 1
    }

    config = {"configurable": {"thread_id": fam_id}}
    graph.invoke(state, config=config)

    # Graph must pause execution at escalation node
    snapshot = graph.get_state(config)
    assert "escalation" in snapshot.next

    # Resume with expert counselor notes
    resumed = resume_counselling_session(
        thread_id=fam_id,
        counsellor_notes="Human counselor recommends Digital Animation Diploma bridging Creative & Technical fields."
    )
    assert resumed is not None
    assert resumed.get("human_escalation_needed") is False


# ---------------------------------------------------------------------------
# Scenario D: Offline Fallback Resiliency
# Verifies zero-crash operation when offline or no API key is provided
# ---------------------------------------------------------------------------
def test_scenario_d_offline_resilience(monkeypatch):
    from backend.app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    fam_id = "scenario-d-offline-04"
    result = run_family_counselling(
        family_id=fam_id,
        student_profile={"education_level": "10th_pass", "career_interests": ["renewable_energy"]},
        parent_profile={"primary_concerns": ["job_security"], "max_total_fees_inr": 10000},
        courses=DEMO_COURSES[:3],
        strict=False
    )

    assert result is not None
    summary = result.get("final_consensus_summary")
    assert summary is not None
    assert summary["overall_consensus_readiness"] in ["high", "moderate", "requires_dialogue"]

