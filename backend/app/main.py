from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base, SessionLocal
from .models import CourseModel
from .demo_courses_data import DEMO_COURSES
from .routes import router
from .rag_retriever import course_vector_store

def seed_courses():
    db = SessionLocal()
    try:
        for item in DEMO_COURSES:
            existing = db.query(CourseModel).filter(CourseModel.id == item["id"]).first()
            if existing:
                existing.title = item["title"]
                existing.slug = item["slug"]
                existing.provider = item["provider"]
                existing.stream = item["stream"]
                existing.duration_months = item["duration_months"]
                existing.training_mode = item["training_mode"]
                existing.certification_body = item["certification_body"]
                existing.nsqf_level = item.get("nsqf_level")
                existing.practical_hours = item.get("practical_hours")
                existing.eligibility = item["eligibility"]
                existing.description = item["description"]
                existing.highlights = item["highlights"]
                existing.skills_acquired = item["skills_acquired"]
                existing.career_progression = item.get("career_progression")
                existing.location = item["location"]
                existing.fees_inr = item["fees_inr"]
                existing.financial_aid_available = item.get("financial_aid_available", True)
                existing.career_outcome = item["career_outcome"]
                existing.rating = item.get("rating", 4.5)
                existing.enrolled_count = item.get("enrolled_count", 0)
                existing.is_demo = item.get("is_demo", True)
                existing.district = item.get("district")
                existing.state = item.get("state", "Maharashtra")
                existing.source_name = item.get("source_name")
                existing.source_url = item.get("source_url")
                existing.verification_status = item.get("verification_status", "verified_curriculum_framework")
                existing.last_updated = item.get("last_updated", "2026-10-19")
                existing.missing_evidence_flags = item.get("missing_evidence_flags", [])
            else:
                course = CourseModel(
                    id=item["id"],
                    title=item["title"],
                    slug=item["slug"],
                    provider=item["provider"],
                    stream=item["stream"],
                    duration_months=item["duration_months"],
                    training_mode=item["training_mode"],
                    certification_body=item["certification_body"],
                    nsqf_level=item.get("nsqf_level"),
                    practical_hours=item.get("practical_hours"),
                    eligibility=item["eligibility"],
                    description=item["description"],
                    highlights=item["highlights"],
                    skills_acquired=item["skills_acquired"],
                    career_progression=item.get("career_progression"),
                    location=item["location"],
                    fees_inr=item["fees_inr"],
                    financial_aid_available=item.get("financial_aid_available", True),
                    career_outcome=item["career_outcome"],
                    rating=item.get("rating", 4.5),
                    enrolled_count=item.get("enrolled_count", 0),
                    is_demo=item.get("is_demo", True),
                    district=item.get("district"),
                    state=item.get("state", "Maharashtra"),
                    source_name=item.get("source_name"),
                    source_url=item.get("source_url"),
                    verification_status=item.get("verification_status", "verified_curriculum_framework"),
                    last_updated=item.get("last_updated", "2026-10-19"),
                    missing_evidence_flags=item.get("missing_evidence_flags", [])
                )
                db.add(course)

        # Remove obsolete legacy demo courses
        valid_ids = [item["id"] for item in DEMO_COURSES]
        db.query(CourseModel).filter(~CourseModel.id.in_(valid_ids)).delete(synchronize_session=False)

        db.commit()
        print(f"[SkillSaathi] Synchronized {len(DEMO_COURSES)} demonstration vocational courses.")
    finally:
        db.close()

from sqlalchemy import text

def migrate_sqlite_schema():
    with engine.connect() as conn:
        try:
            # 1. Migrate family_sessions
            res = conn.execute(text("PRAGMA table_info(family_sessions)")).fetchall()
            col_names = [r[1] for r in res]
            if col_names:
                if "post_confidence_student" not in col_names:
                    conn.execute(text("ALTER TABLE family_sessions ADD COLUMN post_confidence_student FLOAT"))
                if "post_confidence_parent" not in col_names:
                    conn.execute(text("ALTER TABLE family_sessions ADD COLUMN post_confidence_parent FLOAT"))
                if "confidence_feedback" not in col_names:
                    conn.execute(text("ALTER TABLE family_sessions ADD COLUMN confidence_feedback TEXT"))
                if "confidence_submitted_at" not in col_names:
                    conn.execute(text("ALTER TABLE family_sessions ADD COLUMN confidence_submitted_at DATETIME"))
                conn.commit()

            # 2. Migrate courses
            res_c = conn.execute(text("PRAGMA table_info(courses)")).fetchall()
            col_names_c = [r[1] for r in res_c]
            if col_names_c:
                if "district" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN district VARCHAR(100)"))
                if "state" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN state VARCHAR(100) DEFAULT 'Maharashtra'"))
                if "source_name" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN source_name VARCHAR(255)"))
                if "source_url" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN source_url VARCHAR(255)"))
                if "verification_status" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN verification_status VARCHAR(50)"))
                if "last_updated" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN last_updated VARCHAR(50)"))
                if "missing_evidence_flags" not in col_names_c:
                    conn.execute(text("ALTER TABLE courses ADD COLUMN missing_evidence_flags JSON"))
                conn.commit()
        except Exception as e:
            print(f"[SkillSaathi Migration] Schema migration note: {e}")

def _build_rag_index():
    """Build the in-process course vector store after seeding."""
    db = SessionLocal()
    try:
        course_records = db.query(CourseModel).all()
        courses_dict = [
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
            for c in course_records
        ]
        course_vector_store.build(courses_dict)
        print(f"[SkillSaathi] RAG index built for {len(courses_dict)} courses.")
    except Exception as e:
        print(f"[SkillSaathi] RAG index build failed (non-fatal): {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist, seed demo courses, build RAG index
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema()
    seed_courses()
    _build_rag_index()
    yield
    # Shutdown

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Backend services for SkillSaathi vocational career counselling and family decision-support.",
    lifespan=lifespan
)

# CORS configuration for local Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_check": "/api/health"
    }
