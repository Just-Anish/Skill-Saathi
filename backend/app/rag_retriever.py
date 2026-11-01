"""
SkillSaathi RAG Retriever
In-memory ChromaDB vector store for course catalog.
Embeds courses at startup using Google's gemini-embedding-2 model (via Gemini API).
Falls back to TF-IDF keyword retrieval when GEMINI_API_KEY is absent.
"""

import json
import logging
import math
import re
import urllib.request
import urllib.error
from collections import Counter
from typing import List, Dict, Any, Optional

from .config import settings

logger = logging.getLogger("skillsaathi.rag")

# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _embed_via_gemini(texts: List[str]) -> Optional[List[List[float]]]:
    """Batch-embed texts using Gemini gemini-embedding-2. Returns None on failure."""
    if not settings.GEMINI_API_KEY:
        return None

    api_key = settings.GEMINI_API_KEY.strip()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-embedding-2:batchEmbedContents?key={api_key}"
    )

    requests_payload = [
        {
            "model": "models/gemini-embedding-2",
            "content": {"parts": [{"text": t}]},
            "taskType": "RETRIEVAL_DOCUMENT",
        }
        for t in texts
    ]
    payload = {"requests": requests_payload}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                embeddings = [e["values"] for e in data.get("embeddings", [])]
                if len(embeddings) == len(texts):
                    return embeddings
    except Exception as exc:
        logger.warning("[RAG] Gemini embedding call failed: %s", exc)
    return None


def _embed_query_gemini(text: str) -> Optional[List[float]]:
    """Embed a single query string for retrieval."""
    if not settings.GEMINI_API_KEY:
        return None

    api_key = settings.GEMINI_API_KEY.strip()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-embedding-2:embedContent?key={api_key}"
    )
    payload = {
        "model": "models/gemini-embedding-2",
        "content": {"parts": [{"text": text}]},
        "taskType": "RETRIEVAL_QUERY",
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("embedding", {}).get("values")
    except Exception as exc:
        logger.warning("[RAG] Gemini query embed failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b + 1e-9)


# ---------------------------------------------------------------------------
# TF-IDF fallback
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class _TFIDFIndex:
    """Minimal in-memory TF-IDF index for keyword fallback retrieval."""

    def __init__(self):
        self._docs: List[str] = []
        self._doc_term_freqs: List[Counter] = []
        self._idf: Dict[str, float] = {}
        self._doc_vectors: List[Dict[str, float]] = []

    def build(self, texts: List[str]) -> None:
        self._docs = texts
        self._doc_term_freqs = [Counter(_tokenize(t)) for t in texts]
        N = len(texts)
        df: Dict[str, int] = {}
        for tf in self._doc_term_freqs:
            for term in tf:
                df[term] = df.get(term, 0) + 1
        self._idf = {term: math.log((N + 1) / (freq + 1)) + 1 for term, freq in df.items()}
        self._doc_vectors = self._tfidf_vectors(self._doc_term_freqs)

    def _tfidf_vectors(self, term_freqs: List[Counter]) -> List[Dict[str, float]]:
        vecs = []
        for tf in term_freqs:
            vec: Dict[str, float] = {}
            total = sum(tf.values()) or 1
            for term, cnt in tf.items():
                vec[term] = (cnt / total) * self._idf.get(term, 1.0)
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            vecs.append({k: v / norm for k, v in vec.items()})
        return vecs

    def query(self, text: str, top_k: int = 3) -> List[int]:
        q_tf = Counter(_tokenize(text))
        q_vec = self._tfidf_vectors([q_tf])[0]
        scores = []
        for idx, doc_vec in enumerate(self._doc_vectors):
            score = sum(q_vec.get(t, 0.0) * doc_vec.get(t, 0.0) for t in q_vec)
            scores.append((score, idx))
        scores.sort(reverse=True)
        return [idx for _, idx in scores[:top_k]]


# ---------------------------------------------------------------------------
# Course document builder
# ---------------------------------------------------------------------------

def _course_to_document(course: Dict[str, Any]) -> str:
    """
    Serialize a course dict into a rich text document for embedding.
    Fields: title, description, stream, skills_acquired, career_outcome, highlights,
    certification_body, nsqf_level, location, fees_inr.
    """
    outcome = course.get("career_outcome") or {}
    skills = course.get("skills_acquired") or []
    highlights = course.get("highlights") or []
    role_title = outcome.get("role_title", "")
    avg_salary = outcome.get("average_starting_salary_inr", "")
    demand = outcome.get("industry_demand", "")
    employers = ", ".join(outcome.get("potential_employers") or [])

    parts = [
        f"Course: {course.get('title', '')}",
        f"Stream: {course.get('stream', '').replace('_', ' ')}",
        f"Description: {course.get('description', '')}",
        f"Skills: {'; '.join(skills)}",
        f"Highlights: {'; '.join(highlights)}",
        f"Career role: {role_title}",
        f"Industry demand: {demand}",
        f"Starting salary: {avg_salary} INR/month",
        f"Employers: {employers}",
        f"Certification: {course.get('certification_body', '')} NSQF Level {course.get('nsqf_level', '')}",
        f"Location: {course.get('location', '')}",
        f"Duration: {course.get('duration_months', '')} months",
        f"Fees: {course.get('fees_inr', '')} INR",
        f"Training mode: {course.get('training_mode', '')}",
        f"Career progression: {course.get('career_progression', '')}",
    ]
    return " | ".join(p for p in parts if p.split(": ", 1)[-1].strip())


# ---------------------------------------------------------------------------
# Query builder from assessment answers / family profiles
# ---------------------------------------------------------------------------

STREAM_KEYWORDS: Dict[str, str] = {
    "renewable_energy": "solar energy photovoltaic installation green power electrical wiring",
    "automotive": "electric vehicle EV diagnostics motor powertrain automobile repair",
    "healthcare": "patient care nursing health assistance hospital pharmacy paramedic",
    "it_tech": "computers software web development programming digital IT tech",
    "manufacturing_engineering": "CNC machining precision tooling welding industrial production",
    "agriculture_allied": "agriculture farming drone sensing crop technology outdoor field",
    "hospitality_tourism": "hotel hospitality tourism food service facility management",
    "construction_infrastructure": "construction civil drafting infrastructure site surveying",
    "creative_media": "design media graphics animation multimedia art photography",
}

ACTIVITY_KEYWORDS: Dict[str, str] = {
    "building_fixing": "mechanical repair tools machines building fixing assembly",
    "electricity_energy": "electrical wiring energy solar circuit electronics",
    "computers_tech": "computers software programming coding digital apps",
    "design_creativity": "design creative drawing art media digital",
    "helping_people": "helping people care patient healthcare support community",
    "nature_outdoors": "agriculture nature outdoors farming field environment",
    "precision_making": "precision measurement manufacturing CNC tooling quality",
}

CONCERN_KEYWORDS: Dict[str, str] = {
    "job_security": "stable employment verified placement hiring job security",
    "degree_progression": "degree B.Voc diploma lateral entry credit higher education",
    "fees_cost": "affordable low fees financial aid scholarship subsidy",
    "time_to_earn": "fast quick short duration earning income 6 months",
    "social_respect": "government recognized accredited respected established",
    "relocation": "local nearby district regional no relocation",
}


def build_rag_query(
    student: Optional[Dict[str, Any]] = None,
    parent: Optional[Dict[str, Any]] = None,
    assessment_answers: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Construct a rich natural-language retrieval query from student/parent profiles
    or raw assessment answers. Used to retrieve the most relevant courses via
    semantic or keyword similarity.
    """
    tokens: List[str] = []

    if student:
        for stream in student.get("career_interests") or []:
            tokens.append(STREAM_KEYWORDS.get(stream, stream.replace("_", " ")))
        for activity in student.get("hands_on_activities") or []:
            tokens.append(ACTIVITY_KEYWORDS.get(activity, activity.replace("_", " ")))
        edu = student.get("education_level", "")
        if edu:
            tokens.append(f"requires {edu.replace('_', ' ')} education")
        dur = student.get("preferred_duration_months")
        if dur:
            tokens.append(f"training duration {dur} months practical workshop hands-on")

    if parent:
        for concern in parent.get("primary_concerns") or []:
            tokens.append(CONCERN_KEYWORDS.get(concern, concern.replace("_", " ")))
        max_fees = parent.get("max_total_fees_inr")
        if max_fees:
            tokens.append(f"fees under {max_fees} INR affordable")
        for stream in parent.get("preferred_streams") or []:
            tokens.append(STREAM_KEYWORDS.get(stream, stream.replace("_", " ")))

    if assessment_answers:
        activities = assessment_answers.get("q_activities") or []
        if isinstance(activities, list):
            for act in activities:
                tokens.append(ACTIVITY_KEYWORDS.get(act, act.replace("_", " ")))
        concerns = assessment_answers.get("q_primary_concern")
        if concerns:
            tokens.append(CONCERN_KEYWORDS.get(str(concerns), str(concerns).replace("_", " ")))

    if not tokens:
        tokens = ["vocational training government certified practical employment"]

    return " ".join(tokens)


# ---------------------------------------------------------------------------
# CourseVectorStore — the main RAG store
# ---------------------------------------------------------------------------

class CourseVectorStore:
    """
    In-process vector store for vocational course catalog.

    - On `build()`: generates embeddings for all course documents via Gemini.
      Falls back to TF-IDF if Gemini is unavailable.
    - On `retrieve()`: embeds the query and returns top-k courses by cosine
      similarity. Falls back to TF-IDF keyword ranking.

    Instantiate once and call `build()` at application startup.
    """

    def __init__(self) -> None:
        self._courses: List[Dict[str, Any]] = []
        self._embeddings: Optional[List[List[float]]] = None
        self._tfidf: _TFIDFIndex = _TFIDFIndex()
        self._documents: List[str] = []
        self._ready: bool = False
        self._use_vectors: bool = False

    # ------------------------------------------------------------------
    def build(self, courses: List[Dict[str, Any]]) -> None:
        """
        Ingest courses and build the retrieval index.
        Called at application startup once courses are seeded into the DB.
        """
        if not courses:
            logger.warning("[RAG] No courses provided to CourseVectorStore.build()")
            return

        self._courses = courses
        self._documents = [_course_to_document(c) for c in courses]

        # Always build TF-IDF as reliable fallback
        self._tfidf.build(self._documents)

        # Attempt Gemini-based dense embeddings
        embeddings = _embed_via_gemini(self._documents)
        if embeddings:
            self._embeddings = embeddings
            self._use_vectors = True
            logger.info(
                "[RAG] Vector store built with Gemini embeddings for %d courses.",
                len(courses),
            )
        else:
            self._use_vectors = False
            logger.info(
                "[RAG] Vector store built with TF-IDF fallback for %d courses "
                "(set GEMINI_API_KEY for dense vector retrieval).",
                len(courses),
            )

        self._ready = True

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        student: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top_k most relevant courses for the given query.
        Optionally filters by student education eligibility.

        Returns a list of course dicts augmented with a `_rag_score` field.
        """
        if not self._ready:
            logger.warning("[RAG] Store not built; returning empty list.")
            return []

        if self._use_vectors:
            q_emb = _embed_query_gemini(query)
            if q_emb:
                scored = [
                    (_cosine(q_emb, emb), idx)
                    for idx, emb in enumerate(self._embeddings)  # type: ignore[arg-type]
                ]
                scored.sort(reverse=True)
                indices = [idx for _, idx in scored[:top_k * 2]]  # over-fetch for eligibility filter
            else:
                # Gemini query embed failed at runtime; fall through to TF-IDF
                indices = self._tfidf.query(query, top_k * 2)
        else:
            indices = self._tfidf.query(query, top_k * 2)

        results: List[Dict[str, Any]] = []
        for idx in indices:
            course = dict(self._courses[idx])
            # Eligibility filter
            if student:
                from .consensus_engine import FamilyConsensusEngine, EDUCATION_HIERARCHY
                req_edu = (course.get("eligibility") or {}).get("min_education", "10th_pass")
                student_edu = student.get("education_level", "10th_pass")
                if not FamilyConsensusEngine.is_education_eligible(student_edu, req_edu):
                    continue
            results.append(course)
            if len(results) >= top_k:
                break

        return results

    # ------------------------------------------------------------------
    def is_ready(self) -> bool:
        return self._ready

    def course_count(self) -> int:
        return len(self._courses)

    def rebuild(self, courses: List[Dict[str, Any]]) -> None:
        """Re-ingest when course catalog changes."""
        self.build(courses)


# Singleton instance — imported and used across the application
course_vector_store = CourseVectorStore()

