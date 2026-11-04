"""
Integration Tests for Multi-Party Chat & HITL Resume API Endpoints (Phase 5).
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_family_chat_and_resume_flow():
    # 1. Create a family session
    create_res = client.post("/api/families", json={"language": "en", "district": "Pune", "state": "Maharashtra"})
    assert create_res.status_code == 201
    fam_id = create_res.json()["id"]

    # 2. Submit student profile
    student_res = client.post(
        f"/api/families/{fam_id}/student",
        json={
            "education_level": "10th_pass",
            "career_interests": ["automotive"],
            "hands_on_activities": ["building_fixing"],
            "preferred_duration_months": 12,
            "work_environment_preference": "workshop",
            "pre_confidence_score": 5.0
        }
    )
    assert student_res.status_code == 200

    # 3. Submit parent profile
    parent_res = client.post(
        f"/api/families/{fam_id}/parent",
        json={
            "primary_concerns": ["job_security", "degree_progression"],
            "max_total_fees_inr": 15000,
            "preferred_streams": ["automotive"],
            "degree_vs_vocational_preference": "balanced",
            "pre_confidence_score": 4.0
        }
    )
    assert parent_res.status_code == 200

    # 4. Run consensus analysis
    analysis_res = client.post(f"/api/families/{fam_id}/analyze")
    assert analysis_res.status_code == 200
    data = analysis_res.json()
    assert "overall_consensus_readiness" in data
    assert "top_pathway_recommendations" in data

    # 5. Send an interactive chat message as student
    chat_res = client.post(
        f"/api/families/{fam_id}/chat",
        json={
            "sender": "student",
            "message": "I want to work with Electric Vehicles. Can I earn while I learn?"
        }
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["family_id"] == fam_id
    assert len(chat_data["messages"]) > 0

    # 6. Resume endpoint
    resume_res = client.post(
        f"/api/families/{fam_id}/resume",
        json={
            "counsellor_notes": "Expert counselor recommends the DGT CTS Dual VET model with guaranteed NAPS stipend."
        }
    )
    assert resume_res.status_code == 200
    resume_data = resume_res.json()
    assert resume_data["status"] == "resumed"

