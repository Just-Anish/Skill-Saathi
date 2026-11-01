from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Family Schemas ---

class FamilyCreate(BaseModel):
    family_name: Optional[str] = Field(None, max_length=100)
    language: str = Field("en", max_length=10)
    district: Optional[str] = Field("Pune", max_length=100)
    state: str = Field("Maharashtra", max_length=100)

class FamilyResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    language: str
    district: Optional[str]
    state: str
    status: str
    has_student_profile: bool
    has_parent_profile: bool
    has_analysis: bool

# --- Student Profile Schemas ---

class StudentProfileCreate(BaseModel):
    student_name: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=14, le=50)
    education_level: str = Field(..., description="e.g. 8th_pass, 10th_pass, 12th_pass, diploma, graduate")
    career_interests: List[str] = Field(..., min_length=1, description="List of preferred vocational streams")
    hands_on_activities: Optional[List[str]] = Field(default_factory=list)
    preferred_duration_months: Optional[int] = Field(None, ge=1, le=48)
    preferred_location: Optional[str] = Field(None, max_length=100)
    constraints: Optional[Dict[str, Any]] = Field(default_factory=dict)
    pre_confidence_score: Optional[float] = Field(None, ge=1.0, le=10.0, description="Self-reported initial confidence (1-10)")

class StudentProfileResponse(BaseModel):
    family_id: str
    student_name: Optional[str]
    education_level: str
    career_interests: List[str]
    preferred_duration_months: Optional[int]
    submitted_at: datetime

# --- Parent Profile Schemas ---

class ParentProfileCreate(BaseModel):
    parent_name: Optional[str] = Field(None, max_length=100)
    primary_concerns: List[str] = Field(..., min_length=1, description="Concerns such as job_security, fees_cost, social_respect, degree_progression")
    max_monthly_budget_inr: Optional[int] = Field(None, ge=0)
    max_total_fees_inr: Optional[int] = Field(None, ge=0)
    preferred_streams: Optional[List[str]] = Field(default_factory=list)
    location_preference: Optional[str] = Field(None, max_length=100)
    degree_continuation_important: Optional[bool] = Field(True)
    pre_confidence_score: Optional[float] = Field(None, ge=1.0, le=10.0, description="Self-reported initial confidence (1-10)")

class ParentProfileResponse(BaseModel):
    family_id: str
    parent_name: Optional[str]
    primary_concerns: List[str]
    max_total_fees_inr: Optional[int]
    submitted_at: datetime

# --- Course Schemas ---

class CourseEligibilitySchema(BaseModel):
    min_age: int
    max_age: Optional[int] = None
    min_education: str
    prior_experience_required: bool = False

class CareerOutcomeSchema(BaseModel):
    role_title: str
    average_starting_salary_inr: int
    industry_demand: str
    potential_employers: List[str]

class CourseResponse(BaseModel):
    id: str
    title: str
    slug: str
    provider: str
    stream: str
    duration_months: int
    training_mode: str
    certification_body: str
    nsqf_level: Optional[int]
    practical_hours: Optional[int]
    eligibility: CourseEligibilitySchema
    description: str
    highlights: List[str]
    skills_acquired: List[str]
    career_progression: Optional[str]
    location: str
    fees_inr: int
    financial_aid_available: bool
    career_outcome: CareerOutcomeSchema
    rating: float
    enrolled_count: int
    is_demo: bool = True
    district: Optional[str] = None
    state: Optional[str] = "Maharashtra"
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    verification_status: Optional[str] = "verified_curriculum_framework"
    last_updated: Optional[str] = "2026-10-19"
    missing_evidence_flags: List[str] = Field(default_factory=list)

# --- Consensus Engine Output Schemas ---

class ConsensusDisagreement(BaseModel):
    topic: str
    student_stance: str
    parent_stance: str
    severity: str  # high, medium, low
    resolution_pathway: str

class ConsensusSharedPriority(BaseModel):
    topic: str
    detail: str
    alignment_score: float  # 0.0 - 1.0

class ConsensusRecommendation(BaseModel):
    course_id: str
    course_title: str
    stream: str
    fit_score: int
    student_match_score: int
    parent_match_score: int
    student_rationale: str
    parent_rationale: str
    trade_offs: List[str]
    duration_months: int
    fees_inr: int
    nsqf_level: Optional[int]
    average_starting_salary_inr: int
    certification_body: str
    supporting_factors: List[str] = Field(default_factory=list)
    limiting_factors: List[str] = Field(default_factory=list)
    missing_evidence_flags: List[str] = Field(default_factory=list)
    is_demo: bool = True

class PathwayComparison(BaseModel):
    pathway_a_id: str
    pathway_a_title: str
    pathway_b_id: str
    pathway_b_title: str
    duration_comparison: str
    fee_comparison: str
    wage_benchmark_comparison: str
    progression_comparison: str
    key_trade_off_summary: str
    affordability_explanation: Optional[str] = None
    eligibility_explanation: Optional[str] = None
    student_interest_fit: Optional[str] = None
    parent_concern_fit: Optional[str] = None
    unknown_values_disclaimer: Optional[str] = (
        "Third-party audited placement rates and exact private-contract wages are unverified in public data and omitted to avoid misleading families."
    )
    evidence_status: str = "Standardized CTS/NCVET curricula; verified state admissions telemetry scheduled for Phase 2."

class ConsensusSummaryResponse(BaseModel):
    family_id: str
    analyzed_at: datetime
    status: str
    overall_consensus_readiness: str  # high, moderate, requires_dialogue
    student_priorities: List[str] = Field(default_factory=list)
    parent_priorities: List[str] = Field(default_factory=list)
    shared_strengths: List[ConsensusSharedPriority]
    identified_disagreements: List[ConsensusDisagreement]
    unresolved_concerns: List[str] = Field(default_factory=list)
    top_pathway_recommendations: List[ConsensusRecommendation]
    pathway_comparison: Optional[PathwayComparison] = None
    discussion_guide: List[str]
    pre_confidence_student: Optional[float] = None
    pre_confidence_parent: Optional[float] = None
    post_confidence_student: Optional[float] = None
    post_confidence_parent: Optional[float] = None
    confidence_delta: Optional[float] = None
    confidence_status: str = "opt_in_pending"  # opt_in_pending, actual_delta_recorded
    counselling_mode: str = "deterministic"  # deterministic, ai_grounded
    counselling_model: Optional[str] = None
    counselling_mode_note: str = "Evaluated using SkillSaathi Evidence-Grounded Consensus Engine."
    disclaimer: str
    is_demo_data: bool = True

class ConfidenceSubmission(BaseModel):
    role: str = Field("student", description="student, parent, or joint")
    score: float = Field(..., ge=1.0, le=10.0, description="Self-reported post-counselling confidence rating (1-10)")
    feedback: Optional[str] = Field(None, max_length=500)

class ConfidenceResponse(BaseModel):
    family_id: str
    role: str
    pre_score: Optional[float]
    post_score: float
    delta: Optional[float]
    delta_message: str
    status: str = "actual_delta_recorded"
    recorded_at: datetime

# --- Counsellor Escalation Schemas ---

class CounsellorRequestCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=8, max_length=20)
    role: Optional[str] = Field("joint", max_length=50)
    district: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field("course_choice", max_length=100)
    family_id: Optional[str] = Field(None, max_length=36)

class CounsellorRequestResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    district: Optional[str]
    topic: str
    status: str
    created_at: datetime
    message: str = "Escalation request queued for human counsellor contact."

# --- Admin Analytics Schemas ---

class AnalyticsOverviewMetric(BaseModel):
    id: str
    label: str
    value: str
    unit: str
    change_percent: float
    description: str

class AnalyticsOverviewResponse(BaseModel):
    last_updated: datetime
    overview_metrics: List[AnalyticsOverviewMetric]
    disclaimer: str = "Participating family insights from prototype deployments; not district-wide census data."

class ParentalResistanceTopic(BaseModel):
    topic: str
    description: str
    frequency_percent: float
    primary_resolution_framework: str

class ParentalResistanceAnalyticsResponse(BaseModel):
    total_sessions_analyzed: int
    parent_consensus_rate: float
    top_resistance_topics: List[ParentalResistanceTopic]
    district_insights: Dict[str, Any]
    disclaimer: str = "Aggregated insights from participating families for scheme administrators."
