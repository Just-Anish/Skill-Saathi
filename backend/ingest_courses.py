#!/usr/bin/env python3
"""
SkillSaathi RAG Course Ingestion Script
Standalone script to build and smoke-test the CourseVectorStore.

Usage:
    cd "SIH 2026/sih-2026-career-guide/backend"
    python ingest_courses.py

Requires:
    - GEMINI_API_KEY env var for dense vector embeddings (optional; falls back to TF-IDF)
    - Backend packages installed: see requirements.txt

What it does:
    1. Loads all DEMO_COURSES from demo_courses_data.py
    2. Queries the live SQLite DB for any additional persisted courses
    3. Builds the CourseVectorStore (Gemini embeddings or TF-IDF fallback)
    4. Runs 3 sample retrieval queries and prints results to verify correctness
    5. Prints a summary report
"""

import os
import sys

# Make backend package importable from project root
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.app.demo_courses_data import DEMO_COURSES
from backend.app.rag_retriever import (
    CourseVectorStore,
    build_rag_query,
    _course_to_document,
)

# ---------------------------------------------------------------------------
# Optionally pull courses from live SQLite DB (requires app to have run once)
# ---------------------------------------------------------------------------

def _load_courses_from_db() -> list:
    try:
        from backend.app.database import SessionLocal
        from backend.app.models import CourseModel

        db = SessionLocal()
        records = db.query(CourseModel).all()
        db.close()

        if records:
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "stream": c.stream,
                    "description": c.description,
                    "highlights": c.highlights,
                    "skills_acquired": c.skills_acquired,
                    "career_outcome": c.career_outcome,
                    "certification_body": c.certification_body,
                    "nsqf_level": c.nsqf_level,
                    "practical_hours": c.practical_hours,
                    "location": c.location,
                    "fees_inr": c.fees_inr,
                    "financial_aid_available": c.financial_aid_available,
                    "duration_months": c.duration_months,
                    "training_mode": c.training_mode,
                    "eligibility": c.eligibility,
                    "career_progression": c.career_progression,
                    "missing_evidence_flags": c.missing_evidence_flags or [],
                    "verification_status": c.verification_status,
                }
                for c in records
            ]
    except Exception as exc:
        print(f"[ingest] DB load skipped ({exc}); using DEMO_COURSES static data.")
    return []


# ---------------------------------------------------------------------------
# Sample retrieval smoke-tests
# ---------------------------------------------------------------------------

SAMPLE_QUERIES = [
    {
        "label": "EV/Automotive student with job_security concern",
        "student": {
            "career_interests": ["automotive"],
            "hands_on_activities": ["building_fixing"],
            "education_level": "10th_pass",
            "preferred_duration_months": 6,
        },
        "parent": {
            "primary_concerns": ["job_security"],
            "max_total_fees_inr": 20000,
            "preferred_streams": ["automotive", "manufacturing_engineering"],
        },
    },
    {
        "label": "Solar/Renewable student, affordable training priority",
        "student": {
            "career_interests": ["renewable_energy"],
            "hands_on_activities": ["electricity_energy"],
            "education_level": "10th_pass",
            "preferred_duration_months": 6,
        },
        "parent": {
            "primary_concerns": ["fees_cost", "degree_progression"],
            "max_total_fees_inr": 15000,
            "preferred_streams": ["renewable_energy"],
        },
    },
    {
        "label": "IT/Tech student with computers interest",
        "student": {
            "career_interests": ["it_tech"],
            "hands_on_activities": ["computers_tech", "design_creativity"],
            "education_level": "12th_pass",
            "preferred_duration_months": 12,
        },
        "parent": {
            "primary_concerns": ["social_respect", "degree_progression"],
            "max_total_fees_inr": 50000,
            "preferred_streams": ["it_tech"],
        },
    },
]


def run_smoke_tests(store: CourseVectorStore):
    print("\n" + "=" * 60)
    print("RAG RETRIEVAL SMOKE TESTS")
    print("=" * 60)

    for i, test in enumerate(SAMPLE_QUERIES, 1):
        query = build_rag_query(
            student=test.get("student"),
            parent=test.get("parent"),
        )
        results = store.retrieve(query=query, top_k=3, student=test.get("student"))

        print(f"\nTest {i}: {test['label']}")
        print(f"  Query (truncated): {query[:120]}...")
        print(f"  Retrieved {len(results)} courses:")
        for j, c in enumerate(results, 1):
            outcome = c.get("career_outcome") or {}
            print(
                f"    {j}. [{c.get('stream', '?')}] {c.get('title', '?')} "
                f"| ₹{c.get('fees_inr', 0):,} | {c.get('duration_months', '?')}mo "
                f"| {outcome.get('industry_demand', '?')} demand"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("SkillSaathi RAG Course Ingestion")
    print("=" * 60)

    # 1. Load courses
    db_courses = _load_courses_from_db()
    if db_courses:
        courses = db_courses
        print(f"\n[ingest] Loaded {len(courses)} courses from SQLite DB.")
    else:
        # Normalize DEMO_COURSES to match DB dict format
        courses = []
        for item in DEMO_COURSES:
            courses.append({
                "id": item["id"],
                "title": item["title"],
                "stream": item["stream"],
                "description": item["description"],
                "highlights": item.get("highlights", []),
                "skills_acquired": item.get("skills_acquired", []),
                "career_outcome": item.get("career_outcome", {}),
                "certification_body": item.get("certification_body", "NCVET"),
                "nsqf_level": item.get("nsqf_level"),
                "practical_hours": item.get("practical_hours"),
                "location": item.get("location", ""),
                "fees_inr": item.get("fees_inr", 0),
                "financial_aid_available": item.get("financial_aid_available", True),
                "duration_months": item.get("duration_months", 6),
                "training_mode": item.get("training_mode", "offline"),
                "eligibility": item.get("eligibility", {}),
                "career_progression": item.get("career_progression"),
                "missing_evidence_flags": item.get("missing_evidence_flags", []),
                "verification_status": item.get("verification_status", "verified_curriculum_framework"),
            })
        print(f"\n[ingest] Loaded {len(courses)} courses from DEMO_COURSES static data.")

    # 2. Show document preview
    print("\n[ingest] Sample document (course 0):")
    print(f"  {_course_to_document(courses[0])[:300]}...")

    # 3. Build vector store
    print("\n[ingest] Building CourseVectorStore...")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        print("  GEMINI_API_KEY detected — will use dense vector embeddings.")
    else:
        print("  GEMINI_API_KEY not set — will use TF-IDF keyword fallback.")

    store = CourseVectorStore()
    store.build(courses)

    embedding_mode = "Gemini dense vectors" if store._use_vectors else "TF-IDF keyword"
    print(f"\n[ingest] ✓ Store built: {store.course_count()} courses, mode={embedding_mode}")

    # 4. Smoke tests
    run_smoke_tests(store)

    print("\n" + "=" * 60)
    print("Ingestion complete. The application vector store will be")
    print("rebuilt automatically at each backend startup via lifespan().")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

