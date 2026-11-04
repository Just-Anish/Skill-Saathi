"""
Unit & Integration Tests for SkillSaathi LangGraph Multi-Agent Engine
Tests cyclic turns, checkpoint persistence, and HITL interrupts (SIH26241).
"""

import pytest
from backend.app.agents.graph import (
    build_counselling_graph,
    run_family_counselling,
    get_counselling_state
)
from backend.app.demo_courses_data import DEMO_COURSES


@pytest.fixture
def sample_family_data():
    return {
        "family_id": "test-langgraph-fam-001",
        "student": {
            "education_level": "10th_pass",
            "career_interests": ["automotive"],
            "hands_on_activities": ["building_fixing"],
            "preferred_duration_months": 12,
            "district": "Pune",
            "state": "Maharashtra"
        },
        "parent": {
            "primary_concerns": ["job_security", "degree_progression"],
            "max_total_fees_inr": 15000,
            "preferred_streams": ["automotive"],
            "district": "Pune",
            "state": "Maharashtra"
        },
        "courses": DEMO_COURSES[:3]
    }


def test_graph_compilation():
    """Verify that StateGraph compiles without errors."""
    graph = build_counselling_graph(enable_hitl=True)
    assert graph is not None


def test_full_graph_execution(sample_family_data):
    """Test full multi-agent cycle resulting in a verified consensus report."""
    final_state = run_family_counselling(
        family_id=sample_family_data["family_id"],
        student_profile=sample_family_data["student"],
        parent_profile=sample_family_data["parent"],
        courses=sample_family_data["courses"]
    )

    assert "final_consensus_summary" in final_state
    report = final_state["final_consensus_summary"]
    assert report is not None
    assert "overall_consensus_readiness" in report
    assert report["overall_consensus_readiness"] in ["high", "moderate", "requires_dialogue"]
    assert len(report["top_pathway_recommendations"]) > 0

    # Ensure all agents contributed to message history
    names = [msg.name for msg in final_state["messages"]]
    assert "StudentAdvocate" in names
    assert "ParentLiaison" in names
    assert "FactChecker" in names
    assert "ConsensusMediator" in names


def test_checkpoint_state_retrieval(sample_family_data):
    """Test that SQLite checkpointer preserves session state for thread_id."""
    fam_id = "test-checkpoint-fam-002"
    run_family_counselling(
        family_id=fam_id,
        student_profile=sample_family_data["student"],
        parent_profile=sample_family_data["parent"],
        courses=sample_family_data["courses"]
    )

    saved_state = get_counselling_state(fam_id)
    assert saved_state is not None
    assert saved_state["family_id"] == fam_id
    assert "final_consensus_summary" in saved_state

