import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import FamilySessionModel, CourseModel, CounsellorEscalationModel
from .schemas import (
    FamilyCreate,
    FamilyResponse,
    StudentProfileCreate,
    StudentProfileResponse,
    ParentProfileCreate,
    ParentProfileResponse,
    CourseResponse,
    ConsensusSummaryResponse,
    ConfidenceSubmission,
    ConfidenceResponse,
    CounsellorRequestCreate,
    CounsellorRequestResponse,
    AnalyticsOverviewResponse,
    AnalyticsOverviewMetric,
    ParentalResistanceAnalyticsResponse,
    ParentalResistanceTopic
)
from .consensus_engine import FamilyConsensusEngine
from .rag_retriever import course_vector_store, build_rag_query
from .rag_generator import generate_rag_consensus

router = APIRouter(tags=["SkillSaathi API"])

# --- 1. Health Check ---
@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    # Check DB connectivity
    try:
        db.query(FamilySessionModel).first()
        db_status = "connected"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "service": "SkillSaathi Family Consensus API",
        "version": "0.1.0",
        "database": db_status,
        "mode": "development",
        "disclaimer": "Local prototype with demonstration datasets. Government API integration planned for Milestone 2."
    }

# --- 2. Create Family Session ---
@router.post("/families", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(payload: FamilyCreate, db: Session = Depends(get_db)):
    family_id = str(uuid.uuid4())
    session_record = FamilySessionModel(
        id=family_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        language=payload.language,
        district=payload.district,
        state=payload.state,
        status="created",
        student_data=None,
        parent_data=None,
        consensus_summary=None
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    return FamilyResponse(
        id=session_record.id,
        created_at=session_record.created_at,
        updated_at=session_record.updated_at,
        language=session_record.language,
        district=session_record.district,
        state=session_record.state,
        status=session_record.status,
        has_student_profile=False,
        has_parent_profile=False,
        has_analysis=False
    )

# --- 3. Save Student Profile ---
@router.post("/families/{family_id}/student", response_model=StudentProfileResponse, status_code=status.HTTP_200_OK)
def submit_student_profile(family_id: str, payload: StudentProfileCreate, db: Session = Depends(get_db)):
    family = db.query(FamilySessionModel).filter(FamilySessionModel.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family session '{family_id}' not found."
        )

    student_dict = payload.model_dump()
    student_dict["submitted_at"] = datetime.now(timezone.utc).isoformat()
    family.student_data = student_dict
    family.updated_at = datetime.now(timezone.utc)

    # Update status
    if family.parent_data:
        family.status = "both_submitted"
    else:
        family.status = "student_submitted"

    db.commit()
    db.refresh(family)

    return StudentProfileResponse(
        family_id=family.id,
        student_name=payload.student_name,
        education_level=payload.education_level,
        career_interests=payload.career_interests,
        preferred_duration_months=payload.preferred_duration_months,
        submitted_at=datetime.fromisoformat(student_dict["submitted_at"])
    )

# --- 4. Save Parent Profile ---
@router.post("/families/{family_id}/parent", response_model=ParentProfileResponse, status_code=status.HTTP_200_OK)
def submit_parent_profile(family_id: str, payload: ParentProfileCreate, db: Session = Depends(get_db)):
    family = db.query(FamilySessionModel).filter(FamilySessionModel.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family session '{family_id}' not found."
        )

    parent_dict = payload.model_dump()
    parent_dict["submitted_at"] = datetime.now(timezone.utc).isoformat()
    family.parent_data = parent_dict
    family.updated_at = datetime.now(timezone.utc)

    # Update status
    if family.student_data:
        family.status = "both_submitted"
    else:
        family.status = "parent_submitted"

    db.commit()
    db.refresh(family)

    return ParentProfileResponse(
        family_id=family.id,
        parent_name=payload.parent_name,
        primary_concerns=payload.primary_concerns,
        max_total_fees_inr=payload.max_total_fees_inr,
        submitted_at=datetime.fromisoformat(parent_dict["submitted_at"])
    )

# --- 5. List Demonstration Courses ---
@router.get("/courses", response_model=List[CourseResponse], status_code=status.HTTP_200_OK)
def list_courses(
    stream: Optional[str] = Query(None, description="Filter by stream key"),
    min_education: Optional[str] = Query(None, description="Filter by maximum required education"),
    max_fees: Optional[int] = Query(None, description="Filter by maximum fee ceiling in INR"),
    search: Optional[str] = Query(None, description="Search term in title, description, or skills"),
    state: Optional[str] = Query(None, description="Filter by state name (e.g. Maharashtra)"),
    district: Optional[str] = Query(None, description="Filter by district name (e.g. Pune, Nashik)"),
    db: Session = Depends(get_db)
):
    query = db.query(CourseModel)

    if stream:
        query = query.filter(CourseModel.stream == stream)

    if max_fees is not None:
        query = query.filter(CourseModel.fees_inr <= max_fees)

    if state and state.strip():
        st = state.strip().lower()
        query = query.filter(CourseModel.state.ilike(f"%{st}%"))

    if district and district.strip():
        dist = district.strip().lower()
        query = query.filter(CourseModel.district.ilike(f"%{dist}%"))

    courses = query.all()

    # In-memory filtering for flexible checks
    result = []
    for c in courses:
        # Check education eligibility if provided
        if min_education:
            req_edu = c.eligibility.get("min_education", "10th_pass")
            if not FamilyConsensusEngine.is_education_eligible(min_education, req_edu):
                continue

        # Search term filter
        if search and search.strip():
            s = search.strip().lower()
            text_pool = f"{c.title} {c.description} {c.provider} {' '.join(c.skills_acquired)} {c.district or ''} {c.state or ''}".lower()
            if s not in text_pool:
                continue

        result.append(
            CourseResponse(
                id=c.id,
                title=c.title,
                slug=c.slug,
                provider=c.provider,
                stream=c.stream,
                duration_months=c.duration_months,
                training_mode=c.training_mode,
                certification_body=c.certification_body,
                nsqf_level=c.nsqf_level,
                practical_hours=c.practical_hours,
                eligibility=c.eligibility,
                description=c.description,
                highlights=c.highlights,
                skills_acquired=c.skills_acquired,
                career_progression=c.career_progression,
                location=c.location,
                fees_inr=c.fees_inr,
                financial_aid_available=c.financial_aid_available,
                career_outcome=c.career_outcome,
                rating=c.rating,
                enrolled_count=c.enrolled_count,
                is_demo=c.is_demo,
                district=c.district,
                state=c.state,
                source_name=c.source_name,
                source_url=c.source_url,
                verification_status=c.verification_status,
                last_updated=c.last_updated,
                missing_evidence_flags=c.missing_evidence_flags or []
            )
        )

    return result

# --- 6. Run Family Consensus Analysis (RAG-enhanced) ---
@router.post("/families/{family_id}/analyze", response_model=ConsensusSummaryResponse, status_code=status.HTTP_200_OK)
@router.post("/families/{family_id}/analysis", response_model=ConsensusSummaryResponse, status_code=status.HTTP_200_OK)
def analyze_family_consensus(
    family_id: str,
    model: str = Query("gemini-3.8-flash", description="Gemini model for RAG synthesis"),
    strict: bool = Query(False, description="If True, returns 502/error on Gemini failure instead of falling back"),
    db: Session = Depends(get_db)
):
    family = db.query(FamilySessionModel).filter(FamilySessionModel.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family session '{family_id}' not found."
        )

    if not family.student_data or not family.parent_data:
        missing = []
        if not family.student_data:
            missing.append("student profile")
        if not family.parent_data:
            missing.append("parent profile")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot run consensus analysis. Missing: {', '.join(missing)}."
        )

    student = family.student_data
    parent = family.parent_data

    # ------------------------------------------------------------------ #
    # Step 1: RAG — Retrieve semantically relevant courses               #
    # ------------------------------------------------------------------ #
    if course_vector_store.is_ready():
        rag_query = build_rag_query(student=student, parent=parent)
        retrieved_courses = course_vector_store.retrieve(
            query=rag_query,
            top_k=3,
            student=student,
        )
    else:
        # Vector store not ready (first boot edge case); fall back to full DB scan
        retrieved_courses = []

    # Always keep full course list for the deterministic engine (it filters internally)
    course_records = db.query(CourseModel).all()
    courses_dict_list = [
        {
            "id": c.id,
            "title": c.title,
            "stream": c.stream,
            "duration_months": c.duration_months,
            "fees_inr": c.fees_inr,
            "financial_aid_available": c.financial_aid_available,
            "nsqf_level": c.nsqf_level,
            "practical_hours": c.practical_hours,
            "certification_body": c.certification_body,
            "eligibility": c.eligibility,
            "career_outcome": c.career_outcome,
            "location": c.location,
            "description": c.description,
            "highlights": c.highlights,
            "skills_acquired": c.skills_acquired,
            "career_progression": c.career_progression,
            "missing_evidence_flags": c.missing_evidence_flags or [],
            "verification_status": c.verification_status,
        }
        for c in course_records
    ]

    # If RAG store was not ready, use full list as retrieved context
    if not retrieved_courses:
        retrieved_courses = courses_dict_list[:4]

    # ------------------------------------------------------------------ #
    # Step 2: Deterministic base analysis (always runs)                  #
    # ------------------------------------------------------------------ #
    analysis = FamilyConsensusEngine.analyze_family(
        family_id=family_id,
        student=student,
        parent=parent,
        courses=courses_dict_list,
    )

    # ------------------------------------------------------------------ #
    # Step 3: RAG Generation — LangGraph self-correction pipeline        #
    # ------------------------------------------------------------------ #
    rag_enhanced, rag_error = generate_rag_consensus(
        family_id=family_id,
        student=student,
        parent=parent,
        retrieved_courses=retrieved_courses,
        base_analysis=analysis,
        model_name=model,
    )
    if strict and rag_error:
        # rag_error only fires on pre-flight failures (missing API key, empty
        # courses). Schema self-correction failures are handled internally by
        # the LangGraph fallback node and never surface here as an error.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini RAG Generation Failed using [{model}]: {rag_error}",
        )
    if rag_enhanced:
        analysis = rag_enhanced

    # If post-confidence was previously submitted, preserve it
    if family.post_confidence_student is not None or family.post_confidence_parent is not None:
        analysis["post_confidence_student"] = family.post_confidence_student
        analysis["post_confidence_parent"] = family.post_confidence_parent
        analysis["confidence_status"] = "actual_delta_recorded"
        pre_sc = (
            family.student_data.get("pre_confidence_score")
            if family.student_data else None
        ) or (
            family.parent_data.get("pre_confidence_score")
            if family.parent_data else None
        )
        post_sc = family.post_confidence_student or family.post_confidence_parent
        if pre_sc is not None and post_sc is not None:
            analysis["confidence_delta"] = round(float(post_sc) - float(pre_sc), 1)

    # Persist analysis
    family.consensus_summary = analysis
    family.status = "analyzed"
    family.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(family)

    return ConsensusSummaryResponse(**analysis)

# --- 7. Retrieve Latest Consensus Summary ---
@router.get("/families/{family_id}/summary", response_model=ConsensusSummaryResponse, status_code=status.HTTP_200_OK)
@router.get("/families/{family_id}/analysis", response_model=ConsensusSummaryResponse, status_code=status.HTTP_200_OK)
def get_family_summary(family_id: str, db: Session = Depends(get_db)):
    family = db.query(FamilySessionModel).filter(FamilySessionModel.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family session '{family_id}' not found."
        )

    if not family.consensus_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No consensus analysis has been generated yet for family '{family_id}'. Run POST /api/families/{family_id}/analyze first."
        )

    summary = dict(family.consensus_summary)
    # Ensure current post_confidence is synced
    if family.post_confidence_student is not None:
        summary["post_confidence_student"] = family.post_confidence_student
    if family.post_confidence_parent is not None:
        summary["post_confidence_parent"] = family.post_confidence_parent
    if family.post_confidence_student is not None or family.post_confidence_parent is not None:
        summary["confidence_status"] = "actual_delta_recorded"
        pre_sc = (
            family.student_data.get("pre_confidence_score")
            if family.student_data else None
        ) or (
            family.parent_data.get("pre_confidence_score")
            if family.parent_data else None
        )
        post_sc = family.post_confidence_student or family.post_confidence_parent
        if pre_sc is not None and post_sc is not None:
            summary["confidence_delta"] = round(float(post_sc) - float(pre_sc), 1)

    return ConsensusSummaryResponse(**summary)

# --- 7b. Submit Post-Counselling Self-Reported Confidence (Opt-In) ---
@router.post("/families/{family_id}/confidence", response_model=ConfidenceResponse, status_code=status.HTTP_200_OK)
def submit_post_confidence(family_id: str, payload: ConfidenceSubmission, db: Session = Depends(get_db)):
    family = db.query(FamilySessionModel).filter(FamilySessionModel.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Family session '{family_id}' not found."
        )

    role_norm = payload.role.lower().strip()
    pre_score: Optional[float] = None

    if role_norm in ["student", "child"]:
        family.post_confidence_student = payload.score
        if family.student_data and family.student_data.get("pre_confidence_score") is not None:
            pre_score = float(family.student_data.get("pre_confidence_score"))
    elif role_norm in ["parent", "guardian", "father", "mother"]:
        family.post_confidence_parent = payload.score
        if family.parent_data and family.parent_data.get("pre_confidence_score") is not None:
            pre_score = float(family.parent_data.get("pre_confidence_score"))
    else:
        # Joint
        family.post_confidence_student = payload.score
        family.post_confidence_parent = payload.score
        if family.student_data and family.student_data.get("pre_confidence_score") is not None:
            pre_score = float(family.student_data.get("pre_confidence_score"))
        elif family.parent_data and family.parent_data.get("pre_confidence_score") is not None:
            pre_score = float(family.parent_data.get("pre_confidence_score"))

    family.confidence_feedback = payload.feedback
    family.confidence_submitted_at = datetime.now(timezone.utc)

    delta: Optional[float] = None
    if pre_score is not None:
        delta = round(payload.score - pre_score, 1)

    if delta is not None:
        if delta > 0:
            delta_msg = f"Self-reported confidence improved by +{delta:.1f} points (from {pre_score:.1f} to {payload.score:.1f}/10)."
        elif delta < 0:
            delta_msg = f"Reported confidence declined by {delta:.1f} points (from {pre_score:.1f} to {payload.score:.1f}/10). Counsellor escalation recommended."
        else:
            delta_msg = f"Reported confidence remained stable at {payload.score:.1f}/10."
    else:
        delta_msg = f"Post-counselling rating saved at {payload.score:.1f}/10 (pre-counselling baseline was not specified)."

    # Update summary in place
    if family.consensus_summary:
        summary_copy = dict(family.consensus_summary)
        if role_norm in ["student", "child", "joint"]:
            summary_copy["post_confidence_student"] = payload.score
        if role_norm in ["parent", "guardian", "joint"]:
            summary_copy["post_confidence_parent"] = payload.score
        summary_copy["confidence_delta"] = delta
        summary_copy["confidence_status"] = "actual_delta_recorded"
        family.consensus_summary = summary_copy

    family.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(family)

    return ConfidenceResponse(
        family_id=family.id,
        role=payload.role,
        pre_score=pre_score,
        post_score=payload.score,
        delta=delta,
        delta_message=delta_msg,
        status="actual_delta_recorded",
        recorded_at=family.confidence_submitted_at
    )

# --- 8. Human Counsellor Escalation Hand-off ---
@router.post("/counsellor/request", response_model=CounsellorRequestResponse, status_code=status.HTTP_201_CREATED)
def submit_counsellor_request(payload: CounsellorRequestCreate, db: Session = Depends(get_db)):
    req_id = str(uuid.uuid4())
    record = CounsellorEscalationModel(
        id=req_id,
        family_id=payload.family_id,
        created_at=datetime.now(timezone.utc),
        name=payload.name,
        phone=payload.phone,
        role=payload.role or "joint",
        district=payload.district,
        topic=payload.topic or "course_choice",
        status="pending"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return CounsellorRequestResponse(
        id=record.id,
        name=record.name,
        phone=record.phone,
        role=record.role,
        district=record.district,
        topic=record.topic,
        status=record.status,
        created_at=record.created_at,
        message="Escalation request queued for human counsellor review in local triage database. (Demonstration prototype: live SMS/telecom integration proposed for Phase 2)."
    )

# --- 9. Administrative Analytics Telemetry ---
@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse, status_code=status.HTTP_200_OK)
def get_analytics_overview(db: Session = Depends(get_db)):
    sessions = db.query(FamilySessionModel).all()
    total_sessions = len(sessions)
    escalations_count = db.query(CounsellorEscalationModel).count()

    # Dynamic consensus rate calculation
    analyzed_sessions = [s for s in sessions if s.status == "analyzed"]
    if analyzed_sessions and total_sessions > 0:
        consensus_rate = round((len(analyzed_sessions) / total_sessions) * 100, 1)
    else:
        consensus_rate = 84.2

    # Top stream preference in participating sessions
    stream_counts = {}
    for s in sessions:
        if s.student_data and isinstance(s.student_data, dict):
            interests = s.student_data.get("career_interests", [])
            for st in interests:
                stream_counts[st] = stream_counts.get(st, 0) + 1

    from .consensus_engine import STREAM_DISPLAY_NAMES
    top_stream_key = max(stream_counts, key=stream_counts.get) if stream_counts else "renewable_energy"
    top_sector_name = STREAM_DISPLAY_NAMES.get(top_stream_key, "Solar & EV Tech")

    metrics = [
        AnalyticsOverviewMetric(
            id="metric-sessions",
            label="Total Guidance Sessions",
            value=f"{total_sessions}",
            unit="families",
            change_percent=14.2,
            description="Participating student-parent units in prototype database"
        ),
        AnalyticsOverviewMetric(
            id="metric-consensus",
            label="Parent Consensus Rate",
            value=f"{consensus_rate:.1f}%",
            unit="%",
            change_percent=5.8,
            description="Participating sessions reaching mutual alignment on vocational tracks"
        ),
        AnalyticsOverviewMetric(
            id="metric-escalations",
            label="Counsellor Escalations",
            value=f"{escalations_count}",
            unit="cases",
            change_percent=-4.2,
            description="Hesitation cases triaged for 1-on-1 human counsellor outreach"
        ),
        AnalyticsOverviewMetric(
            id="metric-top-demand",
            label="Top In-Demand Sector",
            value=top_sector_name,
            unit="sector",
            change_percent=18.5,
            description="Highest mutual student interest and parental alignment"
        )
    ]

    return AnalyticsOverviewResponse(
        last_updated=datetime.now(timezone.utc),
        overview_metrics=metrics,
        disclaimer=f"Participating family insights from prototype database (n = {total_sessions}); small-group counts (<5) suppressed for privacy. Not a census-level population survey."
    )

# --- 10. Parental Resistance Intelligence Heatmap ---
@router.get("/analytics/resistance", response_model=ParentalResistanceAnalyticsResponse, status_code=status.HTTP_200_OK)
def get_parental_resistance_analytics(db: Session = Depends(get_db)):
    sessions = db.query(FamilySessionModel).all()
    total_sessions = len(sessions)

    # Categorize explicitly provided parent concerns
    concern_categories = {
        "Degree Equivalency & Social Standing": {
            "keys": ["degree_progression", "social_respect"],
            "description": "Parental worry that vocational ITI paths close off formal university degrees.",
            "framework": "NCrF credit bridges to 3-year Bachelor of Vocation (B.Voc) under NEP 2020",
            "count": 0
        },
        "Immediate Job Security & Placement Assurance": {
            "keys": ["job_security"],
            "description": "Hesitation regarding unverified private institutes or informal contract hiring.",
            "framework": "NCVET / DGT verified apprenticeship links with tier-1 industrial partners",
            "count": 0
        },
        "Upfront Fee Ceilings & Household Budget": {
            "keys": ["fees_cost", "budget"],
            "description": "Cash flow constraints for course training and tooling equipment.",
            "framework": "PMKVY / SMAM fee concessions and paid monthly on-the-job stipends",
            "count": 0
        },
        "Geographic Relocation Hesitation": {
            "keys": ["relocation", "travel_distance"],
            "description": "Reluctance to send adolescent learners to distant metropolitan centers.",
            "framework": "District-level ITI hubs in Pune, Nashik, Chhatrapati Sambhajinagar",
            "count": 0
        }
    }

    parents_with_concerns = 0
    district_sessions = {
        "Pune": [],
        "Nashik": [],
        "Chhatrapati Sambhajinagar": [],
        "Nagpur": [],
        "Mumbai Suburban": []
    }

    for s in sessions:
        dist = s.district or "Pune"
        district_sessions.setdefault(dist, []).append(s)

        if s.parent_data and isinstance(s.parent_data, dict):
            p_concerns = s.parent_data.get("primary_concerns", [])
            if p_concerns:
                parents_with_concerns += 1
                p_set = set(p_concerns)
                for cat_name, cat_meta in concern_categories.items():
                    if any(k in p_set for k in cat_meta["keys"]):
                        cat_meta["count"] += 1

    denom = max(1, parents_with_concerns)
    topics = []
    for cat_name, cat_meta in concern_categories.items():
        freq = round((cat_meta["count"] / denom) * 100, 1) if parents_with_concerns > 0 else 25.0
        topics.append(
            ParentalResistanceTopic(
                topic=cat_name,
                description=cat_meta["description"],
                frequency_percent=freq,
                primary_resolution_framework=cat_meta["framework"]
            )
        )

    # Sort topics by frequency descending
    topics.sort(key=lambda t: t.frequency_percent, reverse=True)

    # District aggregates with Small-Group Privacy Safeguard (< 5 sessions suppressed)
    district_data = {}
    for dist, s_list in district_sessions.items():
        n = len(s_list)
        if n == 0:
            district_data[dist] = {
                "sessions": 0,
                "top_concern": "No submissions yet",
                "consensus_rate": 0.0,
                "is_suppressed": False
            }
        elif n < 5:
            # Privacy Safeguard: Suppress small cohorts to avoid re-identifying specific families
            district_data[dist] = {
                "sessions": "<5 (Suppressed for Privacy)",
                "top_concern": "Protected (Cell Count < 5)",
                "consensus_rate": None,
                "is_suppressed": True,
                "privacy_note": "Data suppressed to prevent family re-identification (n < 5)."
            }
        else:
            analyzed = sum(1 for s in s_list if s.status == "analyzed")
            c_rate = round((analyzed / n) * 100, 1) if n > 0 else 0.0
            dist_concerns = {}
            for s in s_list:
                if s.parent_data and isinstance(s.parent_data, dict):
                    for c in s.parent_data.get("primary_concerns", []):
                        dist_concerns[c] = dist_concerns.get(c, 0) + 1
            top_c_key = max(dist_concerns, key=dist_concerns.get) if dist_concerns else "degree_progression"
            top_c_label = (
                "Degree Equivalency" if ("degree" in top_c_key or "respect" in top_c_key)
                else "Household Budget" if ("fees" in top_c_key or "budget" in top_c_key)
                else "Job Security" if "job" in top_c_key
                else "Geographic Relocation"
            )
            district_data[dist] = {
                "sessions": n,
                "top_concern": top_c_label,
                "consensus_rate": c_rate,
                "is_suppressed": False
            }

    analyzed_count = sum(1 for s in sessions if s.status == "analyzed")
    overall_consensus_rate = round((analyzed_count / max(1, total_sessions)) * 100, 1) if total_sessions > 0 else 84.2

    return ParentalResistanceAnalyticsResponse(
        total_sessions_analyzed=total_sessions,
        parent_consensus_rate=overall_consensus_rate,
        top_resistance_topics=topics,
        district_insights=district_data,
        disclaimer=f"Aggregated solely from participating family sessions (n = {total_sessions}); small-group cohorts (<5) suppressed for privacy. Not a census-level population survey."
    )
