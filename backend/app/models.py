from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

def utc_now():
    return datetime.now(timezone.utc)

class FamilySessionModel(Base):
    __tablename__ = "family_sessions"

    id = Column(String(36), primary_key=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    language = Column(String(10), default="en")
    district = Column(String(100), nullable=True)
    state = Column(String(100), default="Maharashtra")
    status = Column(String(50), default="created")  # created, student_submitted, parent_submitted, analyzed

    # Stored profile snapshots as JSON
    student_data = Column(JSON, nullable=True)
    parent_data = Column(JSON, nullable=True)
    consensus_summary = Column(JSON, nullable=True)

    # Actual Post-Guidance Confidence Tracking (Opt-In)
    post_confidence_student = Column(Float, nullable=True)
    post_confidence_parent = Column(Float, nullable=True)
    confidence_feedback = Column(Text, nullable=True)
    confidence_submitted_at = Column(DateTime, nullable=True)

    # Cascading dependent records
    escalations = relationship(
        "CounsellorEscalationModel",
        back_populates="family_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class CourseModel(Base):
    __tablename__ = "courses"

    id = Column(String(100), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False)
    stream = Column(String(100), nullable=False, index=True)
    duration_months = Column(Integer, nullable=False)
    training_mode = Column(String(50), nullable=False)
    certification_body = Column(String(100), nullable=False)
    nsqf_level = Column(Integer, nullable=True)
    practical_hours = Column(Integer, nullable=True)
    eligibility = Column(JSON, nullable=False)
    description = Column(Text, nullable=False)
    highlights = Column(JSON, nullable=False)
    skills_acquired = Column(JSON, nullable=False)
    career_progression = Column(Text, nullable=True)
    location = Column(String(255), nullable=False)
    fees_inr = Column(Integer, nullable=False)
    financial_aid_available = Column(Boolean, default=True)
    career_outcome = Column(JSON, nullable=False)
    rating = Column(Float, default=4.5)
    enrolled_count = Column(Integer, default=0)
    is_demo = Column(Boolean, default=True)
    district = Column(String(100), nullable=True, index=True)
    state = Column(String(100), default="Maharashtra")
    source_name = Column(String(255), default="DGT / NCVET Qualification Framework")
    source_url = Column(String(255), default="https://dgt.gov.in/en/CTS")
    verification_status = Column(String(50), default="verified_curriculum_framework")
    last_updated = Column(String(50), default="2026-10-19")
    missing_evidence_flags = Column(JSON, default=list)

class CounsellorEscalationModel(Base):
    __tablename__ = "counsellor_escalations"

    id = Column(String(36), primary_key=True, index=True)
    family_id = Column(String(36), ForeignKey("family_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    role = Column(String(50), default="joint")
    district = Column(String(100), nullable=True)
    topic = Column(String(100), default="course_choice")
    status = Column(String(50), default="pending")

    family_session = relationship("FamilySessionModel", back_populates="escalations")
