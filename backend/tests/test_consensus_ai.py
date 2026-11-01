import pytest
from backend.tests.conftest import client
from backend.app.consensus_engine import FamilyConsensusEngine
from backend.app.ai_counsellor import AICounsellorAdapter
from backend.app.config import settings

# 1. Aligned Priorities Test
def test_aligned_priorities_consensus():
    # Create family session
    resp = client.post("/api/families", json={"preferred_language": "en"})
    assert resp.status_code == 201
    family_id = resp.json()["id"]

    # Student wants renewable energy, 6 months
    st_res = client.post(f"/api/families/{family_id}/student", json={
        "student_name": "Rohan Deshmukh",
        "education_level": "10th_pass",
        "career_interests": ["renewable_energy"],
        "hands_on_activities": ["workshop_tools"],
        "preferred_duration_months": 6,
        "pre_confidence_score": 5.0
    })
    assert st_res.status_code == 200

    # Parent also prefers renewable energy, budget 25,000
    pr_res = client.post(f"/api/families/{family_id}/parent", json={
        "parent_name": "Suresh Deshmukh",
        "relationship": "father",
        "preferred_streams": ["renewable_energy"],
        "primary_concerns": ["job_security"],
        "max_total_fees_inr": 25000,
        "degree_continuation_important": False,
        "pre_confidence_score": 6.0
    })
    assert pr_res.status_code == 200

    # Run analysis
    analysis_resp = client.post(f"/api/families/{family_id}/analyze")
    assert analysis_resp.status_code == 200
    data = analysis_resp.json()

    # Consensus readiness should be high or moderate
    assert data["overall_consensus_readiness"] in ["high", "moderate"]
    # Shared priorities must contain career sector
    topics = [s["topic"] for s in data["shared_strengths"]]
    assert "Agreed Career Sector" in topics
    # Disagreements should be low severity
    for d in data["identified_disagreements"]:
        assert d["severity"] != "high"
    # Priorities extracted
    assert len(data["student_priorities"]) > 0
    assert len(data["parent_priorities"]) > 0
    # Recommendations should include solar technician
    assert len(data["top_pathway_recommendations"]) > 0
    top = data["top_pathway_recommendations"][0]
    assert top["stream"] == "renewable_energy"
    assert len(top["supporting_factors"]) > 0
    assert len(top["limiting_factors"]) > 0
    assert len(top["missing_evidence_flags"]) > 0

# 2. Conflicting Priorities Test
def test_conflicting_priorities_consensus():
    resp = client.post("/api/families", json={"preferred_language": "en"})
    family_id = resp.json()["id"]

    # Student wants IT / Software, 12 months, low pre-confidence
    st_res = client.post(f"/api/families/{family_id}/student", json={
        "student_name": "Pooja Patil",
        "education_level": "10th_pass",
        "career_interests": ["it_tech"],
        "hands_on_activities": ["coding_lab"],
        "preferred_duration_months": 12,
        "pre_confidence_score": 4.0
    })
    assert st_res.status_code == 200

    # Parent strongly wants healthcare only, budget capped at 5,000, wants 6 months
    pr_res = client.post(f"/api/families/{family_id}/parent", json={
        "parent_name": "Sunita Patil",
        "relationship": "mother",
        "preferred_streams": ["healthcare"],
        "primary_concerns": ["fees_cost", "time_to_earn", "social_respect"],
        "max_total_fees_inr": 5000,
        "degree_continuation_important": True,
        "pre_confidence_score": 3.0
    })
    assert pr_res.status_code == 200

    analysis_resp = client.post(f"/api/families/{family_id}/analyze")
    assert analysis_resp.status_code == 200
    data = analysis_resp.json()

    # Should detect high severity stream disagreement
    assert data["overall_consensus_readiness"] == "requires_dialogue"
    disagreements = data["identified_disagreements"]
    topics = [d["topic"] for d in disagreements]
    assert "Vocational Stream Preference" in topics
    assert "Training Cost & Household Budget" in topics

    # Unresolved concerns should be explicitly populated
    assert len(data["unresolved_concerns"]) > 0

    # Pathway comparison should compare two pathways side-by-side
    assert data["pathway_comparison"] is not None
    comp = data["pathway_comparison"]
    assert comp["pathway_a_id"] != comp["pathway_b_id"]
    assert "vs" in comp["duration_comparison"]
    assert "vs" in comp["fee_comparison"]
    assert "vs" in comp["wage_benchmark_comparison"]
    assert comp["evidence_status"] is not None

# 3. Insufficient / Missing Profiles Handling
def test_incomplete_family_handling():
    resp = client.post("/api/families", json={"preferred_language": "mr"})
    family_id = resp.json()["id"]

    # Student profile only, no parent profile
    client.post(f"/api/families/{family_id}/student", json={
        "student_name": "Amit Shinde",
        "education_level": "8th_pass",
        "career_interests": ["automotive"]
    })

    # Attempt to analyze without parent
    analyze_resp = client.post(f"/api/families/{family_id}/analyze")
    assert analyze_resp.status_code == 400
    assert "Missing" in analyze_resp.json()["detail"]

# 4. AI Provider Safe Fallback & Evidence-Aware Response Policy
def test_ai_provider_fallback_mode(monkeypatch):
    # When GEMINI_API_KEY is not set or adapter returns None
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert AICounsellorAdapter.is_configured() is False
    res = AICounsellorAdapter.enhance_analysis(
        base_analysis={"dummy": 123},
        student={},
        parent={},
        courses=[]
    )
    assert res is None  # Safe fallback signaled

    # Test full end-to-end consensus returns deterministic mode tag
    resp = client.post("/api/families", json={})
    family_id = resp.json()["id"]
    st_res = client.post(f"/api/families/{family_id}/student", json={
        "student_name": "Kavita Rao",
        "education_level": "10th_pass",
        "career_interests": ["manufacturing_engineering"]
    })
    assert st_res.status_code == 200
    pr_res = client.post(f"/api/families/{family_id}/parent", json={
        "parent_name": "Venkatesh Rao",
        "preferred_streams": ["manufacturing_engineering"],
        "primary_concerns": ["job_security"]
    })
    assert pr_res.status_code == 200

    ana_resp = client.post(f"/api/families/{family_id}/analyze")
    assert ana_resp.status_code == 200
    data = ana_resp.json()
    assert data["counselling_mode"] == "deterministic"
    assert "Deterministic Mode" in data["counselling_mode_note"]
    assert data["is_demo_data"] is True

# 5. Confidence Tracking: Actual Delta vs No Fabrication
def test_actual_confidence_tracking():
    resp = client.post("/api/families", json={})
    family_id = resp.json()["id"]

    # Pre-confidence is 4.0 for student, 5.0 for parent
    st_res = client.post(f"/api/families/{family_id}/student", json={
        "student_name": "Aniket Gore",
        "education_level": "12th_pass",
        "career_interests": ["renewable_energy"],
        "pre_confidence_score": 4.0
    })
    assert st_res.status_code == 200
    pr_res = client.post(f"/api/families/{family_id}/parent", json={
        "parent_name": "Balasaheb Gore",
        "preferred_streams": ["renewable_energy"],
        "primary_concerns": ["job_security"],
        "pre_confidence_score": 5.0
    })
    assert pr_res.status_code == 200

    # Analyze
    ana_res = client.post(f"/api/families/{family_id}/analyze")
    assert ana_res.status_code == 200

    # Before submitting post-confidence: delta is None, status is opt_in_pending
    summary_before = client.get(f"/api/families/{family_id}/summary").json()
    assert summary_before["confidence_delta"] is None
    assert summary_before["confidence_status"] == "opt_in_pending"
    assert summary_before["post_confidence_student"] is None

    # Opt-in: Student submits post-guidance score of 8.5
    conf_resp = client.post(f"/api/families/{family_id}/confidence", json={
        "role": "student",
        "score": 8.5,
        "feedback": "Clear explanation of lateral B.Voc entry resolved family hesitation."
    })
    assert conf_resp.status_code == 200
    conf_data = conf_resp.json()
    assert conf_data["pre_score"] == 4.0
    assert conf_data["post_score"] == 8.5
    # Actual delta: 8.5 - 4.0 = +4.5
    assert conf_data["delta"] == 4.5
    assert "+4.5" in conf_data["delta_message"]

    # Verify summary now reflects actual delta and persists
    summary_after = client.get(f"/api/families/{family_id}/summary").json()
    assert summary_after["post_confidence_student"] == 8.5
    assert summary_after["confidence_delta"] == 4.5
    assert summary_after["confidence_status"] == "actual_delta_recorded"
