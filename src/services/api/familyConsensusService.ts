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
  counselling_model?: string;
  counselling_mode_note?: string;
  disclaimer: string;
  is_demo_data: boolean;
  agent_dialogue?: Array<{
    name: string;
    role: string;
    content: string;
  }>;
  verified_facts?: Array<{
    category: string;
    data: any;
  }>;
}

export const AVAILABLE_GEMINI_MODELS = [
  {
    id: 'gemini-flash-lite-latest',
    name: 'Gemini Flash Lite (Active Quota)',
    tag: 'Recommended (Fast & Active)',
    description: 'Ultra-fast, responsive Google Gemini model with active free-tier quota.',
  },
  {
    id: 'gemini-3.1-flash-lite',
    name: 'Gemini 3.1 Flash Lite',
    tag: 'Low-Latency',
    description: 'High-speed model optimized for rapid multi-agent turn taking.',
  },
  {
    id: 'gemini-3.8-flash',
    name: 'Gemini 3.8 Flash',
    tag: 'Deep Reasoning',
    description: 'Extended reasoning model for grounded evidence synthesis.',
  },
] as const;

export type GeminiModelId = typeof AVAILABLE_GEMINI_MODELS[number]['id'];

export interface FamilyConsensusResult {
  mode: 'live' | 'demo';
  summary?: ConsensusSummaryData;
  error?: string;
  selectedModel?: string;
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
   * Send an interactive chat turn to the LangGraph multi-agent backend
   */
  async sendChatMessage(
    familyId: string,
    sender: 'student' | 'parent' | 'counsellor',
    message: string
  ): Promise<{
    family_id: string;
    messages: Array<{ name: string; role: string; content: string }>;
    latest_response?: string;
    consensus_readiness?: string;
  } | null> {
    try {
      const isLive = await this.checkHealth();
      if (isLive) {
        return await apiClient.post(ENDPOINTS.FAMILIES.CHAT(familyId), {
          sender,
          message,
        });
      }
    } catch (err) {
      console.warn('[SkillSaathi] Failed to send chat message:', err);
    }
    return null;
  }

  /**
   * Resume an interrupted session with expert counselor guidance
   */
  async resumeSession(
    familyId: string,
    counsellorNotes: string
  ): Promise<{ status: string; message: string; resumed_readiness?: string } | null> {
    try {
      const isLive = await this.checkHealth();
      if (isLive) {
        return await apiClient.post(ENDPOINTS.FAMILIES.RESUME(familyId), {
          counsellor_notes: counsellorNotes,
        });
      }
    } catch (err) {
      console.warn('[SkillSaathi] Failed to resume session:', err);
    }
    return null;
  }

  /**
   * Transform assessment answers into student and parent intake payloads,
   * run the family consensus engine via FastAPI, and return the structured report.
   */
  async runFamilyConsensus(
    answers: AssessmentAnswers,
    language = 'en',
    model = 'gemini-3.8-flash',
    strict = true
  ): Promise<FamilyConsensusResult> {
    const isLive = await this.checkHealth();

    if (isLive) {
      try {
        let familyId = typeof window !== 'undefined' && window.sessionStorage
          ? window.sessionStorage.getItem('skillsaathi_active_family_id')
          : null;

        // 1. Create family session if not already existing
        if (!familyId) {
          const family = await apiClient.post<{ id: string }>(ENDPOINTS.FAMILIES.CREATE, {
            family_name: 'Joint Family Intake',
            language,
            district: 'Pune',
            state: 'Maharashtra',
          });
          familyId = family.id;
          if (typeof window !== 'undefined' && window.sessionStorage) {
            window.sessionStorage.setItem('skillsaathi_active_family_id', familyId);
          }
        }

        // 2. Map student profile
        const activities = Array.isArray(answers.q_activities) ? (answers.q_activities as string[]) : [];
        const interestStreams = this.mapActivitiesToStreams(activities);

        await apiClient.post(ENDPOINTS.FAMILIES.STUDENT(familyId), {
          student_name: 'Learner',
          age: 17,
          education_level: this.normalizeEducation(answers.q_education as string),
          career_interests: interestStreams.length > 0 ? interestStreams : ['renewable_energy', 'automotive'],
          hands_on_activities: activities,
          preferred_duration_months: 6,
          preferred_location: 'Pune',
          pre_confidence_score: typeof answers.q_confidence === 'number' ? answers.q_confidence : 6.0,
        });

        // 3. Map parent profile
        const concern = (answers.q_primary_concern as string) || 'job_security';
        const concernsList = [concern];
        if (answers.q_progression === 'degree_pathway') {
          concernsList.push('degree_progression');
        }

        await apiClient.post(ENDPOINTS.FAMILIES.PARENT(familyId), {
          parent_name: 'Guardian / Parent',
          primary_concerns: concernsList,
          max_total_fees_inr: 20000,
          preferred_streams: ['manufacturing_engineering', 'renewable_energy'],
          location_preference: 'Pune',
          degree_continuation_important: answers.q_progression !== 'fast_job',
          pre_confidence_score: 5.5,
        });

        // 4. Run consensus analysis with chosen Gemini model & strict mode
        const endpoint = `${ENDPOINTS.FAMILIES.ANALYZE(familyId)}?model=${encodeURIComponent(model)}&strict=${strict ? 'true' : 'false'}`;
        const analysis = await apiClient.post<ConsensusSummaryData>(endpoint);

        return {
          mode: 'live',
          summary: analysis,
          selectedModel: model,
        };
      } catch (err: any) {
        console.warn('[SkillSaathi] Live backend consensus failed:', err);
        const errorDetail =
          err?.details?.detail ||
          err?.message ||
          `Gemini RAG Generation Failed (${model}). Please verify GEMINI_API_KEY and model availability.`;

        if (strict) {
          return {
            mode: 'live',
            error: errorDetail,
            selectedModel: model,
          };
        }
      }
    } else if (strict) {
      return {
        mode: 'live',
        error: 'FastAPI Backend is offline or unreachable at /api/health. Please ensure the backend server is running (.venv/bin/python backend/run.py) to execute RAG.',
        selectedModel: model,
      };
    }

    // Fallback demonstration evaluation (only when strict is disabled)
    return {
      mode: 'demo',
      summary: this.generateLocalFallback(answers),
      selectedModel: model,
    };
  }

  private normalizeEducation(eduStr?: string): string {
    if (!eduStr) return '10th_pass';
    if (eduStr.includes('8')) return '8th_pass';
    if (eduStr.includes('12')) return '12th_pass';
    if (eduStr.includes('iti') || eduStr.includes('diploma')) return 'diploma';
    if (eduStr.includes('grad')) return 'graduate';
    return '10th_pass';
  }

  private mapActivitiesToStreams(activities: string[]): string[] {
    const streams: string[] = [];
    if (activities.includes('electricity_energy') || activities.includes('building_fixing')) {
      streams.push('renewable_energy', 'automotive');
    }
    if (activities.includes('computers_tech') || activities.includes('design_creativity')) {
      streams.push('it_tech');
    }
    if (activities.includes('helping_people')) {
      streams.push('healthcare');
    }
    if (activities.includes('precision_making')) {
      streams.push('manufacturing_engineering');
    }
    if (activities.includes('nature_outdoors')) {
      streams.push('agriculture_allied');
    }
    return streams;
  }

  private generateLocalFallback(answers: AssessmentAnswers): ConsensusSummaryData {
    const activities = Array.isArray(answers.q_activities) ? (answers.q_activities as string[]) : [];
    const streams = this.mapActivitiesToStreams(activities);

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
        'Budget cap: manageable tuition under ₹20,000 with financial aid',
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
      pre_confidence_student: typeof answers.q_confidence === 'number' ? answers.q_confidence : 6.0,
      pre_confidence_parent: 5.5,
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

