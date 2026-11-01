/**
 * Family Consensus Service
 * Connects frontend intake to the FastAPI Family Consensus Intelligence Engine
 * with resilient fallback to local demonstration evaluation if the backend is offline.
 */

import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { AssessmentAnswers } from '../../features/counselling/assessmentTypes';

export interface ConsensusDisagreement {
  topic: string;
  student_stance: string;
  parent_stance: string;
  severity: 'high' | 'medium' | 'low';
  resolution_pathway: string;
}

export interface ConsensusSharedPriority {
  topic: string;
  detail: string;
  alignment_score: number;
}

export interface ConsensusRecommendation {
  course_id: string;
  course_title: string;
  stream: string;
  fit_score: number;
  student_match_score: number;
  parent_match_score: number;
  student_rationale: string;
  parent_rationale: string;
  trade_offs: string[];
  supporting_factors?: string[];
  limiting_factors?: string[];
  missing_evidence_flags?: string[];
  duration_months: number;
  fees_inr: number;
  nsqf_level?: number;
  average_starting_salary_inr: number;
  certification_body: string;
  is_demo: boolean;
}

export interface PathwayComparison {
  pathway_a_id: string;
  pathway_a_title: string;
  pathway_b_id: string;
  pathway_b_title: string;
  duration_comparison: string;
  fee_comparison: string;
  wage_benchmark_comparison: string;
  progression_comparison: string;
  key_trade_off_summary: string;
  affordability_explanation?: string;
  eligibility_explanation?: string;
  student_interest_fit?: string;
  parent_concern_fit?: string;
  unknown_values_disclaimer?: string;
  evidence_status: string;
}

export interface ConfidenceResponse {
  family_id: string;
  role: string;
  pre_score?: number;
  post_score: number;
  delta?: number;
  delta_message: string;
  status: string;
  recorded_at: string;
}

export interface ConsensusSummaryData {
  family_id: string;
  analyzed_at: string;
  status: string;
  overall_consensus_readiness: 'high' | 'moderate' | 'requires_dialogue';
  student_priorities?: string[];
  parent_priorities?: string[];
  shared_strengths: ConsensusSharedPriority[];
  identified_disagreements: ConsensusDisagreement[];
  unresolved_concerns?: string[];
  top_pathway_recommendations: ConsensusRecommendation[];
  pathway_comparison?: PathwayComparison;
  discussion_guide: string[];
  pre_confidence_student?: number;
  pre_confidence_parent?: number;
  post_confidence_student?: number;
  post_confidence_parent?: number;
  confidence_delta?: number;
  confidence_status?: 'opt_in_pending' | 'actual_delta_recorded';
  counselling_mode?: 'deterministic' | 'ai_grounded';
  counselling_mode_note?: string;
  disclaimer: string;
  is_demo_data: boolean;
}

export interface FamilyConsensusResult {
  mode: 'live' | 'demo';
  summary: ConsensusSummaryData;
}

class FamilyConsensusService {
  /**
   * Check if backend service is available
   */
  async checkHealth(): Promise<boolean> {
    try {
      const res = await apiClient.get<{ status: string }>(ENDPOINTS.HEALTH);
      return res && res.status === 'ok';
    } catch {
      return false;
    }
  }

  /**
   * Fetch existing family consensus summary by family ID
   */
  async getFamilySummary(familyId: string): Promise<FamilyConsensusResult | null> {
    try {
      const isLive = await this.checkHealth();
      if (isLive) {
        const summary = await apiClient.get<ConsensusSummaryData>(ENDPOINTS.FAMILIES.SUMMARY(familyId));
        if (summary && summary.family_id) {
          return {
            mode: 'live',
            summary,
          };
        }
      }
    } catch (err) {
      console.warn('[SkillSaathi] Failed to fetch summary from backend:', err);
    }
    return null;
  }

  /**
   * Submit actual post-counselling self-reported confidence rating (opt-in)
   */
  async submitPostConfidence(
    familyId: string,
    role: string,
    score: number,
    feedback?: string
  ): Promise<ConfidenceResponse | null> {
    try {
      const isLive = await this.checkHealth();
      if (isLive) {
        return await apiClient.post<ConfidenceResponse>(ENDPOINTS.FAMILIES.CONFIDENCE(familyId), {
          role,
          score,
          feedback,
        });
      }
    } catch (err) {
      console.warn('[SkillSaathi] Failed to submit post-confidence to backend:', err);
    }
    return null;
  }

  /**
   * Delete family session and its associated records (dev/admin)
   */
  async deleteFamily(familyId: string): Promise<boolean> {
    try {
      const isLive = await this.checkHealth();
      if (isLive) {
        await apiClient.delete(ENDPOINTS.FAMILIES.DELETE(familyId));
      }
      if (typeof window !== 'undefined' && window.sessionStorage) {
        const active = window.sessionStorage.getItem('skillsaathi_active_family_id');
        if (active === familyId) {
          window.sessionStorage.removeItem('skillsaathi_active_family_id');
        }
      }
      return true;
    } catch (err) {
      console.warn('[SkillSaathi] Failed to delete family session:', err);
      return false;
    }
  }

  /**
   * Transform assessment answers into student and parent intake payloads,
   * run the family consensus engine via FastAPI, and return the structured report.
   */
  async runFamilyConsensus(
    answers: AssessmentAnswers,
    language = 'en'
  ): Promise<FamilyConsensusResult> {
    const isLive = await this.checkHealth();

    if (isLive) {
      try {
        let familyId = typeof window !== 'undefined' && window.sessionStorage
          ? window.sessionStorage.getItem('skillsaathi_active_family_id')
          : null;

        // Context from onboarding & participant
        const onboarding = this.getStoredOnboarding();
        const participant = (answers.q_participant as string) || onboarding?.role || 'together';
        const district = onboarding?.district || 'Pune';
        const state = onboarding?.state || 'Maharashtra';

        let familyName = 'Joint Family Intake';
        let studentName = 'Student';
        let parentName = 'Parent / Guardian';

        if (participant === 'myself') {
          studentName = 'Self Learner';
          familyName = 'Student Direct Intake';
        } else if (participant === 'child_student') {
          studentName = 'Student';
          familyName = 'Parent Guided Intake';
        } else if (participant === 'together') {
          familyName = 'Joint Family Intake';
        }

        // 1. Create family session if not already existing
        if (!familyId) {
          const family = await apiClient.post<{ id: string }>(ENDPOINTS.FAMILIES.CREATE, {
            family_name: familyName,
            language,
            district,
            state,
          });
          familyId = family.id;
          if (typeof window !== 'undefined' && window.sessionStorage) {
            window.sessionStorage.setItem('skillsaathi_active_family_id', familyId);
          }
        }

        // 2. Map student profile
        const rawActivities = Array.isArray(answers.q_activities) ? (answers.q_activities as string[]) : [];
        const activities = rawActivities.filter((a) => a !== 'not_sure_yet');
        let interestStreams = this.mapActivitiesToStreams(activities);
        if (interestStreams.length === 0 && onboarding?.careerInterests?.length) {
          interestStreams = onboarding.careerInterests;
        }
        if (interestStreams.length === 0) {
          interestStreams = ['renewable_energy', 'automotive'];
        }

        const educationStr = answers.q_education as string | undefined;
        const normalizedEdu = this.normalizeEducation(educationStr);
        const derivedAge = this.deriveAgeFromEducation(educationStr);
        const preferredDuration = this.derivePreferredDuration(answers);
        const preConfidenceStudent = this.derivePreConfidenceScore(answers, false);

        // Build rich student constraints map
        const studentConstraints: Record<string, any> = {};
        if (answers.q_strengths) studentConstraints.strengths = answers.q_strengths;
        if (answers.q_environment) studentConstraints.preferred_environments = answers.q_environment;
        if (answers.q_learning_style) studentConstraints.learning_style = answers.q_learning_style;
        if (answers.q_priorities) studentConstraints.career_priorities = answers.q_priorities;
        if (answers.q_followup_employment) studentConstraints.employment_evidence_preference = answers.q_followup_employment;
        if (answers.q_followup_further_study) studentConstraints.further_study_goal = answers.q_followup_further_study;
        if (answers.q_followup_other) studentConstraints.other_priority_notes = answers.q_followup_other;
        if (answers.q_additional_notes) studentConstraints.additional_notes = answers.q_additional_notes;
        if (participant) studentConstraints.participant_perspective = participant;

        await apiClient.post(ENDPOINTS.FAMILIES.STUDENT(familyId), {
          student_name: studentName,
          age: derivedAge,
          education_level: normalizedEdu,
          career_interests: interestStreams,
          hands_on_activities: activities,
          preferred_duration_months: preferredDuration,
          preferred_location: district,
          constraints: studentConstraints,
          pre_confidence_score: preConfidenceStudent,
        });

        // 3. Map parent profile
        const parentConcerns = this.deriveParentConcerns(answers);
        const parentBudget = this.deriveParentBudget(answers);
        const degreeImportant = this.deriveDegreeImportance(answers);
        const preConfidenceParent = this.derivePreConfidenceScore(answers, true);

        // Parent preferred streams: align with student interests or high-demand technical trades
        let parentStreams: string[] = [];
        if (participant === 'together') {
          parentStreams = interestStreams.slice(0, 2);
        } else {
          const highDemandPool = ['manufacturing_engineering', 'renewable_energy', 'it_tech', 'automotive'];
          parentStreams = interestStreams.filter((s) => highDemandPool.includes(s));
          if (parentStreams.length === 0) {
            parentStreams = ['manufacturing_engineering', 'renewable_energy'];
          }
        }

        await apiClient.post(ENDPOINTS.FAMILIES.PARENT(familyId), {
          parent_name: parentName,
          primary_concerns: parentConcerns,
          max_total_fees_inr: parentBudget.maxTotalFeesInr,
          max_monthly_budget_inr: parentBudget.maxMonthlyBudgetInr,
          preferred_streams: parentStreams,
          location_preference: district,
          degree_continuation_important: degreeImportant,
          pre_confidence_score: preConfidenceParent,
        });

        // 4. Run consensus analysis
        const analysis = await apiClient.post<ConsensusSummaryData>(ENDPOINTS.FAMILIES.ANALYZE(familyId));

        return {
          mode: 'live',
          summary: analysis,
        };
      } catch (err) {
        console.warn('[SkillSaathi] Live backend consensus failed, falling back to local demo:', err);
      }
    }

    // Fallback demonstration evaluation
    return {
      mode: 'demo',
      summary: this.generateLocalFallback(answers),
    };
  }

  private getStoredOnboarding(): {
    role?: string;
    educationLevel?: string;
    state?: string;
    district?: string;
    careerInterests?: string[];
  } | null {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      try {
        const raw = window.sessionStorage.getItem('skillsaathi_demo_onboarding_prefs_v1');
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    }
    return null;
  }

  private normalizeEducation(eduStr?: string): string {
    if (!eduStr) return '10th_pass';
    const val = eduStr.toLowerCase();
    if (val === 'class_8_10' || val.includes('8')) return '8th_pass';
    if (val === 'completed_12' || val.includes('12')) return '12th_pass';
    if (val === 'iti_vocational' || val.includes('iti') || val.includes('diploma') || val === 'diploma') return 'diploma';
    if (val === 'graduate' || val.includes('grad')) return 'graduate';
    return '10th_pass';
  }

  private deriveAgeFromEducation(eduStr?: string): number {
    switch (eduStr) {
      case 'class_8_10':
        return 15;
      case 'completed_10':
        return 16;
      case 'studying_11_12':
        return 17;
      case 'completed_12':
        return 18;
      case 'iti_vocational':
        return 19;
      case 'diploma':
        return 20;
      case 'graduate':
        return 22;
      default:
        return 17;
    }
  }

  private mapActivitiesToStreams(activities: string[]): string[] {
    const streams = new Set<string>();
    if (activities.includes('electricity_energy')) {
      streams.add('renewable_energy');
    }
    if (activities.includes('building_fixing')) {
      streams.add('automotive');
      streams.add('manufacturing_engineering');
    }
    if (activities.includes('precision_making')) {
      streams.add('manufacturing_engineering');
    }
    if (activities.includes('computers_tech')) {
      streams.add('it_tech');
    }
    if (activities.includes('design_creativity')) {
      streams.add('it_tech');
      streams.add('creative_media');
    }
    if (activities.includes('helping_people')) {
      streams.add('healthcare');
      streams.add('hospitality_tourism');
    }
    if (activities.includes('nature_outdoors')) {
      streams.add('agriculture_allied');
    }
    if (activities.includes('communication_org')) {
      streams.add('hospitality_tourism');
    }
    return Array.from(streams);
  }

  private deriveParentConcerns(answers: AssessmentAnswers): string[] {
    const concerns = new Set<string>();
    const priorities = Array.isArray(answers.q_priorities) ? (answers.q_priorities as string[]) : [];

    if (priorities.includes('stable_employment') || priorities.includes('earning_potential')) {
      concerns.add('job_security');
    }
    if (priorities.includes('affordable_training') || answers.q_followup_affordable) {
      concerns.add('fees_cost');
    }
    if (priorities.includes('work_soon')) {
      concerns.add('time_to_earn');
    }
    if (priorities.includes('near_home')) {
      concerns.add('relocation');
    }
    if (priorities.includes('study_further') || answers.q_followup_further_study) {
      concerns.add('degree_progression');
    }

    const empFollowup = answers.q_followup_employment as string | undefined;
    if (empFollowup === 'placement_records' || empFollowup === 'company_mous') {
      concerns.add('job_security');
      concerns.add('social_respect');
    } else if (empFollowup === 'naps_stipend') {
      concerns.add('job_security');
      concerns.add('time_to_earn');
    }

    if (concerns.size === 0) {
      concerns.add('job_security');
    }
    return Array.from(concerns);
  }

  private deriveParentBudget(answers: AssessmentAnswers): { maxTotalFeesInr?: number; maxMonthlyBudgetInr?: number } {
    const affordableFollowup = answers.q_followup_affordable as string | undefined;
    const priorities = Array.isArray(answers.q_priorities) ? (answers.q_priorities as string[]) : [];

    if (affordableFollowup === 'budget_under_15k') {
      return { maxTotalFeesInr: 15000, maxMonthlyBudgetInr: 2500 };
    }
    if (affordableFollowup === 'subsidy_scholarship') {
      return { maxTotalFeesInr: 10000, maxMonthlyBudgetInr: 2000 };
    }
    if (affordableFollowup === 'installment_options') {
      return { maxTotalFeesInr: 20000, maxMonthlyBudgetInr: 3000 };
    }
    if (affordableFollowup === 'flexible_if_placed') {
      return { maxTotalFeesInr: 35000, maxMonthlyBudgetInr: 5000 };
    }
    if (priorities.includes('affordable_training')) {
      return { maxTotalFeesInr: 15000, maxMonthlyBudgetInr: 2500 };
    }
    return { maxTotalFeesInr: 25000, maxMonthlyBudgetInr: 4000 };
  }

  private derivePreferredDuration(answers: AssessmentAnswers): number {
    const priorities = Array.isArray(answers.q_priorities) ? (answers.q_priorities as string[]) : [];
    if (priorities.includes('work_soon')) {
      return 6;
    }
    const studyFollowup = answers.q_followup_further_study as string | undefined;
    if (studyFollowup === 'polytechnic_diploma' || studyFollowup === 'bvoc_degree') {
      return 12;
    }
    if (answers.q_learning_style === 'practical_hands_on') {
      return 6;
    }
    return 6;
  }

  private deriveDegreeImportance(answers: AssessmentAnswers): boolean {
    const priorities = Array.isArray(answers.q_priorities) ? (answers.q_priorities as string[]) : [];
    const studyFollowup = answers.q_followup_further_study as string | undefined;

    if (studyFollowup === 'flexible_later') {
      return false;
    }
    if (priorities.includes('study_further') || studyFollowup === 'polytechnic_diploma' || studyFollowup === 'bvoc_degree') {
      return true;
    }
    if (priorities.includes('work_soon') && !priorities.includes('study_further')) {
      return false;
    }
    return true;
  }

  private derivePreConfidenceScore(answers: AssessmentAnswers, isParent = false): number {
    if (typeof answers.q_confidence === 'number') {
      return answers.q_confidence;
    }
    const strengths = Array.isArray(answers.q_strengths) ? (answers.q_strengths as string[]) : [];
    const activities = Array.isArray(answers.q_activities) ? (answers.q_activities as string[]) : [];

    if (activities.includes('not_sure_yet') || strengths.includes('discovering_strengths')) {
      return isParent ? 5.0 : 5.0;
    }
    if (strengths.length >= 3 && !strengths.includes('discovering_strengths')) {
      return isParent ? 6.5 : 7.0;
    }
    return isParent ? 5.5 : 6.0;
  }

  private generateLocalFallback(answers: AssessmentAnswers): ConsensusSummaryData {
    const activities = Array.isArray(answers.q_activities) ? (answers.q_activities as string[]) : [];
    const streams = this.mapActivitiesToStreams(activities);
    const parentBudget = this.deriveParentBudget(answers);
    const preStudent = this.derivePreConfidenceScore(answers, false);
    const preParent = this.derivePreConfidenceScore(answers, true);

    return {
      family_id: 'local-demo-session',
      analyzed_at: new Date().toISOString(),
      status: 'analyzed',
      overall_consensus_readiness: 'moderate',
      student_priorities: [
        `Target Career Domain: ${streams[0] ? streams[0].replace('_', ' ').toUpperCase() : 'Renewable Energy & Automotive Tech'}`,
        'Hands-on workshop training with modern practical tools',
        'Direct employment trajectory within 6-12 months',
      ],
      parent_priorities: [
        'Recognized government certification (NCVET/DGT/NSDC)',
        `Budget cap: manageable tuition under ₹${parentBudget.maxTotalFeesInr?.toLocaleString() || '20,000'} with financial aid`,
        'Preserved lateral entry option to degree (B.Voc / Diploma)',
      ],
      shared_strengths: [
        {
          topic: 'Government-Recognized Qualification',
          detail: 'Both student and parent agree on pursuing certified NCVET/DGT programs over unaccredited courses.',
          alignment_score: 0.95,
        },
        {
          topic: 'Financial Self-Reliance',
          detail: 'Mutual agreement to avoid heavy educational debt and launch practical earnings early.',
          alignment_score: 0.90,
        },
      ],
      identified_disagreements: [
        {
          topic: 'Degree Equivalency vs Fast Employment',
          student_stance: 'Student wishes to learn hands-on technology immediately.',
          parent_stance: 'Parent is concerned that vocational study closes off formal university degrees.',
          severity: 'medium',
          resolution_pathway: 'Clarify that National Credit Framework (NCrF) Level 4-5 certificates articulate directly into 3-year Bachelor of Vocation (B.Voc) degrees.',
        },
        {
          topic: 'Household Budget & Fee Allocation',
          student_stance: 'Student prefers high-demand tech courses with modern lab training.',
          parent_stance: 'Parent needs reassurance that training fees remain within affordable limits.',
          severity: 'medium',
          resolution_pathway: 'Utilize government scheme subsidies (PMKVY/SMAM) and paid on-the-job apprenticeship stipends.',
        },
      ],
      unresolved_concerns: [
        'Confirm specific state university credit transfer guidelines for chosen trade.',
        'Verify local industrial cluster apprenticeship stipend rates during campus visit.',
      ],
      top_pathway_recommendations: [
        {
          course_id: 'course-solar-pv-01',
          course_title: 'Solar PV Installation & Maintenance Technician',
          stream: streams[0] || 'renewable_energy',
          fit_score: 92,
          student_match_score: 94,
          parent_match_score: 90,
          student_rationale: 'Directly aligns with hands-on technical interests and green energy technology.',
          parent_rationale: 'Government-backed NCVET Level 4 certification with strong starting wages and clear B.Voc credit pathway.',
          trade_offs: [
            'Affordable fee of ₹12,000 with financial aid available',
            'Compact 6-month duration enabling rapid employment',
            'Regional placement available in Pune and Nashik industrial clusters',
          ],
          supporting_factors: [
            'Government-backed NCVET Level 4 credential',
            '140+ hours practical hands-on rooftop solar installation',
            'Affordable ₹12,000 fee within household target',
          ],
          limiting_factors: [
            'Requires 10th pass qualification',
            'Requires 6 months full-time attendance',
          ],
          missing_evidence_flags: [
            'Verified recruiter placement percentages awaiting official state portal integration.',
            'Stipend rates vary by participating solar EPC contractor.',
          ],
          duration_months: 6,
          fees_inr: 12000,
          nsqf_level: 4,
          average_starting_salary_inr: 22000,
          certification_body: 'NCVET',
          is_demo: true,
        },
        {
          course_id: 'course-ev-tech-02',
          course_title: 'Electric Vehicle (EV) Powertrain & Diagnostics Specialist',
          stream: 'automotive',
          fit_score: 87,
          student_match_score: 92,
          parent_match_score: 82,
          student_rationale: 'Hands-on troubleshooting of battery management systems and EV motor controllers.',
          parent_rationale: 'High industry hiring demand from leading automotive OEMs; bridge to Polytechnic Diploma.',
          trade_offs: [
            'Course fee of ₹24,000 is higher, but starting salary benchmarks reach ₹26,000/month',
            '8-month duration with in-depth workshop diagnostics',
          ],
          supporting_factors: [
            'Rapidly growing EV manufacturing sector',
            'Advanced lab equipment for battery diagnostics',
          ],
          limiting_factors: [
            'Course fee (₹24,000) exceeds standard ₹20,000 ceiling without installment plan',
            '8-month training duration before full-time placement',
          ],
          missing_evidence_flags: [
            'Starting salary is national benchmark; actual offers depend on employer technical evaluation.',
          ],
          duration_months: 8,
          fees_inr: 24000,
          nsqf_level: 5,
          average_starting_salary_inr: 26000,
          certification_body: 'Industry_Partner',
          is_demo: true,
        },
      ],
      pathway_comparison: {
        pathway_a_id: 'course-solar-pv-01',
        pathway_a_title: 'Solar PV Installation & Maintenance Technician',
        pathway_b_id: 'course-ev-tech-02',
        pathway_b_title: 'Electric Vehicle (EV) Powertrain & Diagnostics Specialist',
        duration_comparison: 'Solar PV: 6 months vs EV Diagnostics: 8 months',
        fee_comparison: 'Solar PV: ₹12,000 vs EV Diagnostics: ₹24,000',
        wage_benchmark_comparison: 'Solar PV: ~₹22,000/mo vs EV Diagnostics: ~₹26,000/mo benchmark',
        progression_comparison: 'Pathway A offers faster entry; Pathway B offers deeper NSQF Level 5 tech specialization.',
        key_trade_off_summary: 'Pathway A provides immediate affordability and quick earning; Pathway B demands longer duration and higher fee for advanced automotive diagnostics.',
        evidence_status: 'Grounded in CTS/NCVET national curricula; district live employer feeds scheduled for state deployment.',
      },
      discussion_guide: [
        '1. Discuss how vocational credits count toward a 3-year B.Voc degree under NEP 2020.',
        '2. Confirm fee subsidies and apprenticeship stipends to ensure zero household financial strain.',
        '3. Plan a joint weekend visit to the local Government ITI to inspect workshop equipment.',
      ],
      pre_confidence_student: preStudent,
      pre_confidence_parent: preParent,
      post_confidence_student: undefined,
      post_confidence_parent: undefined,
      confidence_delta: undefined,
      confidence_status: 'opt_in_pending',
      counselling_mode: 'deterministic',
      counselling_mode_note: 'Evaluated using SkillSaathi Evidence-Grounded Consensus Engine (Deterministic Mode). Real LLM mode activates when GEMINI_API_KEY is configured in backend environment.',
      disclaimer: 'Demonstration data based on rule-grounded consensus engine. Official government API integration planned for Milestone 2.',
      is_demo_data: true,
    };
  }
}

export const familyConsensusService = new FamilyConsensusService();

