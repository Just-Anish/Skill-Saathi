"""
Family Consensus Intelligence Engine
Deterministic, evidence-grounded comparison of student aspirations and parent concerns.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

EDUCATION_HIERARCHY = {
    "below_8th": 1,
    "8th_pass": 2,
    "10th_pass": 3,
    "12th_pass": 4,
    "diploma": 5,
    "graduate": 6
}

STREAM_DISPLAY_NAMES = {
    "renewable_energy": "Solar & Renewable Energy",
    "automotive": "Electric Vehicle & Auto Diagnostics",
    "healthcare": "Healthcare & Patient Care",
    "it_tech": "IT & Web Applications",
    "manufacturing_engineering": "Precision CNC & Industrial Machining",
    "agriculture_allied": "Agriculture & Drone Sensing",
    "hospitality_tourism": "Hospitality & Facility Operations",
    "construction_infrastructure": "Construction & Drafting"
}

CONCERN_EXPLANATIONS = {
    "job_security": "Parent seeks verified post-training employment stability and formal hiring partners.",
    "social_respect": "Parent worries about social perception of vocational certificates compared with traditional degrees.",
    "degree_progression": "Parent wants assurance that vocational study doesn't block later higher education (e.g. B.Voc/B.Tech).",
    "fees_cost": "Family budget requires manageable fees, subsidized training, or installment options.",
    "time_to_earn": "Family prioritizes quick financial return to support household livelihood within 6-12 months.",
    "relocation": "Parent is cautious about student relocating to distant urban centers."
}

class FamilyConsensusEngine:
    @staticmethod
    def is_education_eligible(student_level: str, required_level: str) -> bool:
        s_rank = EDUCATION_HIERARCHY.get(student_level, 0)
        r_rank = EDUCATION_HIERARCHY.get(required_level, 3)
        return s_rank >= r_rank

    @classmethod
    def identify_shared_priorities(
        cls,
        student: Dict[str, Any],
        parent: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        shared: List[Dict[str, Any]] = []

        student_interests = set(student.get("career_interests", []))
        parent_streams = set(parent.get("preferred_streams", []))
        common_streams = student_interests.intersection(parent_streams)

        if common_streams:
            stream_names = [STREAM_DISPLAY_NAMES.get(s, s) for s in common_streams]
            shared.append({
                "topic": "Agreed Career Sector",
                "detail": f"Both student and parent show strong mutual interest in {', '.join(stream_names)}.",
                "alignment_score": 1.0
            })

        # Shared value on formal certification
        shared.append({
            "topic": "Government-Recognized Qualification",
            "detail": "Both parties prioritize accredited frameworks (NCVET/DGT/NSDC) with formal trade credentials rather than uncertified short courses.",
            "alignment_score": 0.95
        })

        # Shared economic objective
        shared.append({
            "topic": "Practical Career Launch",
            "detail": "Both desire hands-on skilling that creates viable employment without incurring unmanageable debt.",
            "alignment_score": 0.90
        })

        # Location alignment
        st_loc = student.get("preferred_location")
        pr_loc = parent.get("location_preference")
        if st_loc and pr_loc and (st_loc.lower() == pr_loc.lower() or "maharashtra" in st_loc.lower()):
            shared.append({
                "topic": "Geographic Region",
                "detail": f"Mutual preference to train within regional industrial hubs ({st_loc}).",
                "alignment_score": 0.85
            })

        return shared

    @classmethod
    def identify_disagreements(
        cls,
        student: Dict[str, Any],
        parent: Dict[str, Any],
        courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        disagreements: List[Dict[str, Any]] = []

        student_interests = set(student.get("career_interests", []))
        parent_streams = set(parent.get("preferred_streams", []))
        parent_concerns = set(parent.get("primary_concerns", []))

        # 1. Sector Difference
        if parent_streams and not student_interests.intersection(parent_streams):
            st_str = [STREAM_DISPLAY_NAMES.get(s, s) for s in student_interests]
            pr_str = [STREAM_DISPLAY_NAMES.get(s, s) for s in parent_streams]
            disagreements.append({
                "topic": "Vocational Stream Preference",
                "student_stance": f"Student aspires to enter {', '.join(st_str)}.",
                "parent_stance": f"Parent prefers tracks in {', '.join(pr_str)} for perceived predictability.",
                "severity": "high",
                "resolution_pathway": "Compare local placement demand, starting wages, and growth trajectories for both sectors using verified course facts."
            })

        # 2. Degree vs Vocational Stigma
        if "degree_progression" in parent_concerns or "social_respect" in parent_concerns or parent.get("degree_continuation_important"):
            disagreements.append({
                "topic": "Degree Equivalency & Social Standing",
                "student_stance": "Student wants practical job-oriented training right away.",
                "parent_stance": "Parent worries a vocational certificate closes off university degree prospects or lacks social prestige.",
                "severity": "medium",
                "resolution_pathway": "Review NEP 2020 and National Credit Framework (NCrF) pathways where ITI/NSQF Level 4-5 credits seamlessly articulate into 3-year Bachelor of Vocation (B.Voc) programs."
            })

        # 3. Budget & Fee Thresholds
        max_fees = parent.get("max_total_fees_inr")
        if max_fees is not None and max_fees > 0:
            expensive_courses = [c for c in courses if c.get("stream") in student_interests and c.get("fees_inr", 0) > max_fees]
            if expensive_courses:
                course_titles = [c.get("title", "") for c in expensive_courses[:2]]
                disagreements.append({
                    "topic": "Training Cost & Household Budget",
                    "student_stance": f"Student's preferred course options ({', '.join(course_titles)}) cost above ₹{max_fees:,}.",
                    "parent_stance": f"Parent has set a fee ceiling of ₹{max_fees:,} to protect family cash flow.",
                    "severity": "medium",
                    "resolution_pathway": "Explore government financial aid, PMKVY / SMAM fee concessions, and monthly stipend apprenticeship arrangements."
                })

        # 4. Training Duration / Time-to-Earn
        st_duration = student.get("preferred_duration_months")
        if "time_to_earn" in parent_concerns and st_duration and st_duration > 6:
            disagreements.append({
                "topic": "Training Duration vs Immediate Earning",
                "student_stance": f"Student is prepared for a {st_duration}-month comprehensive curriculum.",
                "parent_stance": "Parent requires income contribution or apprenticeship earnings within 6 months.",
                "severity": "medium",
                "resolution_pathway": "Select dual-system training (DST) or hybrid programs that integrate paid on-the-job training (OJT) within the first 6 months."
            })

        # If no severe disagreement found, supply low-friction guidance
        if not disagreements:
            disagreements.append({
                "topic": "Specific Trade Specialization",
                "student_stance": "Student is open to exploring specific sub-specialties within preferred stream.",
                "parent_stance": "Parent seeks confirmation of formal hiring partners before enrolment.",
                "severity": "low",
                "resolution_pathway": "Visit the local training center lab together and review audited placement records of recent graduating batches."
            })

        return disagreements

    @classmethod
    def extract_student_priorities(cls, student: Dict[str, Any]) -> List[str]:
        priorities: List[str] = []
        interests = student.get("career_interests", [])
        if interests:
            interest_names = [STREAM_DISPLAY_NAMES.get(i, i) for i in interests]
            priorities.append(f"Target Career Domains: {', '.join(interest_names)}")
        if student.get("hands_on_activities"):
            priorities.append("Prefers practical workshop learning and hands-on lab training over pure theory.")
        duration = student.get("preferred_duration_months")
        if duration:
            priorities.append(f"Preferred Training Duration: ~{duration} months for structured skill development.")
        edu = student.get("education_level")
        if edu:
            priorities.append(f"Academic Entry Qualification: {edu.replace('_', ' ').title()}.")
        loc = student.get("preferred_location")
        if loc:
            priorities.append(f"Preferred Training Location: {loc}.")
        constraints = student.get("constraints") or {}
        if constraints.get("learning_style"):
            ls = constraints["learning_style"]
            if ls == "practical_hands_on":
                priorities.append("Learning Style: Prefers practical workshop learning and hands-on lab training.")
            elif ls == "mix_practical_classroom":
                priorities.append("Learning Style: Balanced mix of classroom theory and practical workshop practice.")
            elif ls == "classroom_theory":
                priorities.append("Learning Style: Structured conceptual learning and theoretical fundamentals.")
        if constraints.get("strengths"):
            st_list = [str(s).replace("_", " ").title() for s in constraints["strengths"] if s != "discovering_strengths"]
            if st_list:
                priorities.append(f"Practical Strengths: {', '.join(st_list[:3])}.")
        if not priorities:
            priorities.append("Seeking industry-aligned vocational skills with fast track to employment.")
        return priorities

    @classmethod
    def extract_parent_priorities(cls, parent: Dict[str, Any]) -> List[str]:
        priorities: List[str] = []
        streams = parent.get("preferred_streams", [])
        if streams:
            stream_names = [STREAM_DISPLAY_NAMES.get(s, s) for s in streams]
            priorities.append(f"Preferred Employment Sectors: {', '.join(stream_names)}")
        concerns = parent.get("primary_concerns", [])
        for c in concerns:
            if c in CONCERN_EXPLANATIONS:
                priorities.append(CONCERN_EXPLANATIONS[c])
        max_fees = parent.get("max_total_fees_inr")
        if max_fees is not None and max_fees > 0:
            priorities.append(f"Budget Limit: Total training expenditure capped at ₹{max_fees:,}.")
        monthly_budget = parent.get("max_monthly_budget_inr")
        if monthly_budget is not None and monthly_budget > 0:
            priorities.append(f"Monthly Budget: Target installment capacity around ₹{monthly_budget:,}/month.")
        loc_pref = parent.get("location_preference")
        if loc_pref:
            priorities.append(f"Location Preference: Regional centers around {loc_pref}.")
        if parent.get("degree_continuation_important"):
            priorities.append("Requires clear pathway for lateral entry to degree (B.Voc / Polytechnic diploma).")
        if not priorities:
            priorities.append("Prioritizes job security, government accreditation, and manageable tuition.")
        return priorities

    @classmethod
    def identify_unresolved_concerns(
        cls,
        student: Dict[str, Any],
        parent: Dict[str, Any],
        top_courses: List[Dict[str, Any]]
    ) -> List[str]:
        concerns: List[str] = []
        max_fees = parent.get("max_total_fees_inr")
        if top_courses and max_fees:
            top_fee = top_courses[0].get("fees_inr", 0)
            if top_fee > max_fees:
                concerns.append(
                    f"Tuition gap: Top-ranked option fees (₹{top_fee:,}) exceed parent target (₹{max_fees:,}). "
                    "Action needed: Check government fee reimbursement and apprenticeship stipend offsets."
                )

        parent_concerns = set(parent.get("primary_concerns", []))
        if "degree_progression" in parent_concerns:
            concerns.append(
                "Degree articulation verification: Need to confirm specific state university B.Voc credit transfer "
                "for the selected ITI/NSQF certification before final admission."
            )

        if "relocation" in parent_concerns:
            concerns.append(
                "Commute / Hostel evaluation: Confirm safe hostel availability or daily transport connectivity "
                "to the regional vocational center."
            )

        st_duration = student.get("preferred_duration_months")
        if "time_to_earn" in parent_concerns and st_duration and st_duration > 6:
            concerns.append(
                f"Income timeline: Student prefers {st_duration}-month course, while parent seeks quick earnings. "
                "Action needed: Select a Dual System of Training (DST) batch with 6th-month paid on-the-job training."
            )

        if not concerns:
            concerns.append("Confirm batch intake dates and document requirements at the nearest ITI / training center.")
            concerns.append("Inspect training workshop infrastructure and speak with current batch trainees during campus visit.")

        return concerns

    @classmethod
    def build_pathway_comparison(
        cls,
        top_courses: List[Dict[str, Any]],
        student: Dict[str, Any],
        parent: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if len(top_courses) < 2:
            return None

        ca = top_courses[0]
        cb = None
        for cand in top_courses[1:]:
            if cand.get("course_id") != ca.get("course_id") and cand.get("course_title") != ca.get("course_title"):
                cb = cand
                break
        if cb is None:
            cb = top_courses[1]

        dur_a = ca.get("duration_months", 6)
        dur_b = cb.get("duration_months", 6)
        fee_a = ca.get("fees_inr", 0)
        fee_b = cb.get("fees_inr", 0)
        sal_a = ca.get("average_starting_salary_inr", 20000)
        sal_b = cb.get("average_starting_salary_inr", 20000)
        nsqf_a = ca.get("nsqf_level", 4)
        nsqf_b = cb.get("nsqf_level", 4)
        cert_a = ca.get("certification_body", "NCVET")
        cert_b = cb.get("certification_body", "NCVET")

        dur_comp = f"{ca['course_title']}: {dur_a} months vs {cb['course_title']}: {dur_b} months"
        fee_comp = f"{ca['course_title']}: ₹{fee_a:,} vs {cb['course_title']}: ₹{fee_b:,}"
        wage_comp = (
            f"{ca['course_title']}: ~₹{sal_a:,}/mo vs {cb['course_title']}: ~₹{sal_b:,}/mo "
            f"(Benchmark based on national CTS wage indicators; local recruiter terms vary)."
        )
        prog_comp = (
            f"Pathway A (NSQF L{nsqf_a}, {cert_a}) provides direct lateral entry into advanced diploma, "
            f"while Pathway B (NSQF L{nsqf_b}, {cert_b}) offers specialized industry certifications."
        )

        # Plain-language explanation for parents with non-technical background
        diff_fees = abs(fee_a - fee_b)
        if fee_a < fee_b:
            affordability_exp = (
                f"Pathway A costs ₹{fee_a:,} (₹{diff_fees:,} more economical than Pathway B). "
                f"Both pathways offer government scholarship eligibility and paid apprenticeship stipends to offset family expenses."
            )
        elif fee_b < fee_a:
            affordability_exp = (
                f"Pathway B costs ₹{fee_b:,} (₹{diff_fees:,} lower than Pathway A). "
                f"Both pathways include on-the-job training stipends so the student earns while learning."
            )
        else:
            affordability_exp = f"Both pathways have identical total fees of ₹{fee_a:,}, fitting equally within the family budget."

        elig_a = ca.get("eligibility", {}).get("min_education", "10th_pass")
        elig_b = cb.get("eligibility", {}).get("min_education", "10th_pass")
        eligibility_exp = (
            f"Pathway A requires {elig_a.replace('_', ' ').title()}; Pathway B requires {elig_b.replace('_', ' ').title()}. "
            f"No prior technical background is assumed; basic tools and safety are taught from scratch."
        )

        stream_a_name = STREAM_DISPLAY_NAMES.get(ca.get("stream", ""), ca.get("stream", ""))
        stream_b_name = STREAM_DISPLAY_NAMES.get(cb.get("stream", ""), cb.get("stream", ""))
        student_interest_fit = (
            f"Student showed strong preference for {stream_a_name} (Pathway A). "
            f"Pathway B ({stream_b_name}) offers a related hands-on track with high industrial applicability."
        )

        parent_concerns = parent.get("primary_concerns", [])
        concern_str = ", ".join(parent_concerns[:2]) if parent_concerns else "job security and affordability"
        parent_concern_fit = (
            f"Pathway A addresses parent priority on {concern_str} via accredited {cert_a} credentials. "
            f"Pathway B provides alternative progression with {cert_b} certification."
        )

        trade_off = (
            f"Pathway A ({ca['course_title']}) has a higher overall consensus fit ({ca['fit_score']}/100) "
            f"and aligns with student trade choice, while Pathway B ({cb['course_title']}) offers alternative "
            f"specialization with difference of ₹{diff_fees:,} in fees and {abs(dur_a - dur_b)} months in duration."
        )

        return {
            "pathway_a_id": ca["course_id"],
            "pathway_a_title": ca["course_title"],
            "pathway_b_id": cb["course_id"],
            "pathway_b_title": cb["course_title"],
            "duration_comparison": dur_comp,
            "fee_comparison": fee_comp,
            "wage_benchmark_comparison": wage_comp,
            "progression_comparison": prog_comp,
            "key_trade_off_summary": trade_off,
            "affordability_explanation": affordability_exp,
            "eligibility_explanation": eligibility_exp,
            "student_interest_fit": student_interest_fit,
            "parent_concern_fit": parent_concern_fit,
            "unknown_values_disclaimer": "Third-party audited institutional placement percentages and exact private contract wages are unverified in public government data. Benchmarks shown reflect official CTS/NCVET curricula.",
            "evidence_status": "Grounded in standardized CTS/NCVET curricula; live district employer placement telemetry scheduled for future rollout."
        }

    @classmethod
    def evaluate_courses(
        cls,
        student: Dict[str, Any],
        parent: Dict[str, Any],
        courses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        student_interests = set(student.get("career_interests", []))
        parent_streams = set(parent.get("preferred_streams", []))
        parent_concerns = set(parent.get("primary_concerns", []))
        max_fees = parent.get("max_total_fees_inr")
        education_level = student.get("education_level", "10th_pass")

        scored_courses: List[Tuple[float, Dict[str, Any]]] = []

        for c in courses:
            stream = c.get("stream", "")
            fees = c.get("fees_inr", 0)
            duration = c.get("duration_months", 6)
            eligibility = c.get("eligibility", {})
            req_edu = eligibility.get("min_education", "10th_pass")
            outcome = c.get("career_outcome", {})
            demand = outcome.get("industry_demand", "medium")
            cert_body = c.get("certification_body", "")

            # 1. Eligibility Check
            is_eligible = cls.is_education_eligible(education_level, req_edu)
            if not is_eligible:
                continue

            # 2. Student Score (0 - 100)
            student_score = 40.0
            if stream in student_interests:
                student_score += 45.0
            if student.get("hands_on_activities") and c.get("practical_hours", 0) >= 120:
                student_score += 15.0
            student_score = min(100.0, student_score)

            # 3. Parent Score (0 - 100)
            parent_score = 40.0
            if parent_streams and stream in parent_streams:
                parent_score += 25.0
            elif not parent_streams and stream in student_interests:
                parent_score += 15.0

            # Fee check
            if max_fees is not None and max_fees > 0:
                if fees <= max_fees:
                    parent_score += 20.0
                elif c.get("financial_aid_available"):
                    parent_score += 10.0
            else:
                if fees <= 15000 or c.get("financial_aid_available"):
                    parent_score += 15.0

            # Recognition / Demand
            if demand in ["high", "very_high"]:
                parent_score += 15.0
            if cert_body in ["NCVET", "DGT_ITI", "NSDC"]:
                parent_score += 10.0

            parent_score = min(100.0, parent_score)

            # Combined Fit Score
            fit_score = int(round(student_score * 0.55 + parent_score * 0.45))

            # Student Rationale
            st_rationale = (
                f"Directly matches your interest in {STREAM_DISPLAY_NAMES.get(stream, stream)}. "
                f"Features {c.get('practical_hours', 100)} hours of hands-on workshop experience "
                f"building in-demand technical competencies."
            )

            # Parent Rationale
            pr_rationale = (
                f"Provides government-recognized {cert_body} qualification with {demand.replace('_', ' ')} industry demand. "
                f"Starting salary benchmarks near ₹{outcome.get('average_starting_salary_inr', 20000):,}/month, "
                f"and includes formal credit progression toward higher diplomas."
            )

            # Trade-offs
            trade_offs = []
            if max_fees and fees > max_fees:
                trade_offs.append(f"Course fee (₹{fees:,}) exceeds stated target of ₹{max_fees:,}, but financial aid is available.")
            else:
                trade_offs.append(f"Affordable fee structure of ₹{fees:,} with financial aid eligibility.")

            if duration <= 6:
                trade_offs.append(f"Fast time-to-earn: compact {duration}-month duration leads quickly to apprenticeships.")
            else:
                trade_offs.append(f"Slightly longer {duration}-month curriculum, balanced by deeper NSQF Level {c.get('nsqf_level', 4)} specialization.")

            trade_offs.append(f"Training location: {c.get('location', 'Maharashtra')}.")

            # Supporting factors (reasons to choose)
            supporting_factors = [
                f"Recognized {cert_body} qualification (NSQF Level {c.get('nsqf_level', 4)})",
                f"Extensive practical focus: {c.get('practical_hours', 100)}+ hours hands-on lab training",
                f"Strong industrial hiring demand in regional sector"
            ]
            if fees <= (max_fees or 20000):
                supporting_factors.append(f"Fits within household fee range (₹{fees:,})")
            if c.get("financial_aid_available"):
                supporting_factors.append("Eligible for government financial aid & fee concessions")

            # Limiting factors (constraints and caveats)
            limiting_factors = [
                f"Requires prerequisite qualification: {req_edu.replace('_', ' ').title()}",
                f"Requires {duration} months commitment before full certification"
            ]
            if max_fees and fees > max_fees:
                limiting_factors.append(f"Exceeds parent budget limit of ₹{max_fees:,} by ₹{fees - max_fees:,}")
            if duration > 6 and "time_to_earn" in parent_concerns:
                limiting_factors.append("Duration exceeds parent's desired 6-month earning timeline")

            # Missing evidence flags (honest, factual boundaries)
            missing_evidence_flags = [
                "Recruiter placement rate pending state-wide tracking portal integration.",
                "Stipend variations depend on local industrial cluster partnerships.",
                "Salary indicator represents national benchmark; actual starting wage depends on employer interview."
            ]

            scored_courses.append((
                fit_score,
                {
                    "course_id": c.get("id"),
                    "course_title": c.get("title"),
                    "stream": stream,
                    "fit_score": fit_score,
                    "student_match_score": int(round(student_score)),
                    "parent_match_score": int(round(parent_score)),
                    "student_rationale": st_rationale,
                    "parent_rationale": pr_rationale,
                    "trade_offs": trade_offs,
                    "supporting_factors": supporting_factors,
                    "limiting_factors": limiting_factors,
                    "missing_evidence_flags": missing_evidence_flags,
                    "duration_months": duration,
                    "fees_inr": fees,
                    "nsqf_level": c.get("nsqf_level"),
                    "average_starting_salary_inr": outcome.get("average_starting_salary_inr", 20000),
                    "certification_body": cert_body,
                    "is_demo": True
                }
            ))

        # Sort descending by fit score
        scored_courses.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_courses[:3]]

    @classmethod
    def generate_discussion_guide(
        cls,
        disagreements: List[Dict[str, Any]],
        shared: List[Dict[str, Any]]
    ) -> List[str]:
        guide: List[str] = [
            "1. Celebrate Common Ground: Acknowledge shared agreement on seeking a government-recognized credential and sustainable employment.",
            "2. Clarify Budget Realities: Discuss whether family cash flow prefers lower upfront fees or if an apprenticeship stipend can offset course expenses.",
            "3. Examine Career Growth: Review how this vocational certification qualifies the student for lateral entry into B.Voc/Polytechnic diploma programs.",
            "4. Action Step: Schedule a joint visit to the nearest certified ITI/Training Hub to speak with recent alumni and inspect workshop equipment."
        ]
        return guide

    @classmethod
    def analyze_family(
        cls,
        family_id: str,
        student: Dict[str, Any],
        parent: Dict[str, Any],
        courses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        from .ai_counsellor import AICounsellorAdapter

        shared = cls.identify_shared_priorities(student, parent)
        disagreements = cls.identify_disagreements(student, parent, courses)
        recommendations = cls.evaluate_courses(student, parent, courses)
        student_priorities = cls.extract_student_priorities(student)
        parent_priorities = cls.extract_parent_priorities(parent)
        unresolved = cls.identify_unresolved_concerns(student, parent, recommendations)
        comparison = cls.build_pathway_comparison(recommendations, student, parent)
        guide = cls.generate_discussion_guide(disagreements, shared)

        # Assess overall readiness
        high_severity_count = sum(1 for d in disagreements if d.get("severity") == "high")
        if high_severity_count > 0:
            readiness = "requires_dialogue"
        elif any(d.get("severity") == "medium" for d in disagreements):
            readiness = "moderate"
        else:
            readiness = "high"

        base_analysis = {
            "family_id": family_id,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "status": "analyzed",
            "overall_consensus_readiness": readiness,
            "student_priorities": student_priorities,
            "parent_priorities": parent_priorities,
            "shared_strengths": shared,
            "identified_disagreements": disagreements,
            "unresolved_concerns": unresolved,
            "top_pathway_recommendations": recommendations,
            "pathway_comparison": comparison,
            "discussion_guide": guide,
            "pre_confidence_student": student.get("pre_confidence_score"),
            "pre_confidence_parent": parent.get("pre_confidence_score"),
            "post_confidence_student": None,
            "post_confidence_parent": None,
            "confidence_delta": None,
            "confidence_status": "opt_in_pending",
            "counselling_mode": "deterministic",
            "counselling_mode_note": (
                "Evaluated using SkillSaathi Evidence-Grounded Consensus Engine (Deterministic Mode). "
                "Real LLM mode activates when GEMINI_API_KEY is configured in backend environment."
            ),
            "disclaimer": (
                "Demonstration data based on rule-grounded consensus engine. "
                "Official government API integration and live district wage feeds planned for Milestone 2."
            ),
            "is_demo_data": True
        }

        # Attempt grounded AI enhancement if provider credentials exist
        enhanced = AICounsellorAdapter.enhance_analysis(base_analysis, student, parent, courses)
        if enhanced:
            return enhanced

        return base_analysis

