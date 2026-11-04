import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Compass,
  Clock,
  Briefcase,
  Users,
  ArrowRight,
  UserCheck,
  RotateCcw,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ShieldCheck,
  Edit3,
  RefreshCw,
  Scale,
  MessageSquare,
  AlertTriangle,
  Info,
  Award,
  Send,
  Check,
} from 'lucide-react';
import { AssessmentLanguage, AssessmentResultsData, LocalizedString, AssessmentAnswers } from './assessmentTypes';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { CounsellorRequestForm } from './CounsellorRequestForm';
import { familyConsensusService, FamilyConsensusResult, AVAILABLE_GEMINI_MODELS } from '../../services/api/familyConsensusService';
import { NCrFCreditLadder } from '../career-pathways/NCrFCreditLadder';
import { ChatMessage } from './ChatMessage';

export interface AssessmentResultsProps {
  results: AssessmentResultsData;
  language: AssessmentLanguage;
  answers?: AssessmentAnswers;
  familyId?: string;
  initialModel?: string;
  initialStrict?: boolean;
  onExploreCourses: () => void;
  onViewCourseDetails: (courseId: string) => void;
  onChangeAnswers: () => void;
  onRestart: () => void;
}

function resolveLocalized(loc: LocalizedString | undefined, lang: AssessmentLanguage): string {
  if (!loc) return '';
  if (lang === 'hi' && loc.hi) return loc.hi;
  if (lang === 'mr' && loc.mr) return loc.mr;
  return loc.en || loc.mr || '';
}

export const AssessmentResults: React.FC<AssessmentResultsProps> = ({
  results,
  language,
  answers,
  familyId,
  initialModel,
  initialStrict,
  onExploreCourses,
  onViewCourseDetails,
  onChangeAnswers,
  onRestart,
}) => {
  const isMr = language === 'mr';
  const isHi = language === 'hi';
  const [showCounsellorModal, setShowCounsellorModal] = useState<boolean>(false);
  const [showRestartConfirm, setShowRestartConfirm] = useState<boolean>(false);
  const [consensusResult, setConsensusResult] = useState<FamilyConsensusResult | null>(null);
  const [isLoadingConsensus, setIsLoadingConsensus] = useState<boolean>(false);
  const [showFallbackAnyway, setShowFallbackAnyway] = useState<boolean>(false);

  const [selectedModel, setSelectedModel] = useState<string>(
    initialModel ||
    (typeof window !== 'undefined' && window.sessionStorage
      ? window.sessionStorage.getItem('skillsaathi_rag_model') || 'gemini-flash-lite-latest'
      : 'gemini-flash-lite-latest')
  );

  const [strictRAG, setStrictRAG] = useState<boolean>(
    initialStrict !== undefined
      ? initialStrict
      : typeof window !== 'undefined' && window.sessionStorage
      ? window.sessionStorage.getItem('skillsaathi_strict_rag') !== 'false'
      : true
  );

  // Actual Post-Guidance Self-Reported Confidence Tracking (Opt-In)
  const [postConfidenceScore, setPostConfidenceScore] = useState<number>(8);
  const [postConfidenceRole, setPostConfidenceRole] = useState<'student' | 'parent' | 'joint'>('student');
  const [postConfidenceFeedback, setPostConfidenceFeedback] = useState<string>('');
  const [isSubmittingConfidence, setIsSubmittingConfidence] = useState<boolean>(false);
  const [confidenceSuccessMsg, setConfidenceSuccessMsg] = useState<string | null>(null);

  const handleSubmitPostConfidence = async () => {
    const activeFamilyId =
      consensusResult?.summary?.family_id ||
      familyId ||
      (typeof window !== 'undefined' && window.sessionStorage
        ? window.sessionStorage.getItem('skillsaathi_active_family_id')
        : null);

    if (!activeFamilyId) return;

    setIsSubmittingConfidence(true);
    try {
      const res = await familyConsensusService.submitPostConfidence(
        activeFamilyId,
        postConfidenceRole,
        postConfidenceScore,
        postConfidenceFeedback
      );

      if (res) {
        setConfidenceSuccessMsg(res.delta_message);
        if (consensusResult && consensusResult.summary) {
          setConsensusResult({
            ...consensusResult,
            summary: {
              ...consensusResult.summary,
              post_confidence_student:
                postConfidenceRole === 'parent'
                  ? consensusResult.summary.post_confidence_student
                  : res.post_score,
              post_confidence_parent:
                postConfidenceRole === 'student'
                  ? consensusResult.summary.post_confidence_parent
                  : res.post_score,
              confidence_delta: res.delta,
              confidence_status: 'actual_delta_recorded',
            },
          });
        }
      } else {
        const pre = consensusResult?.summary?.pre_confidence_student || 6.0;
        const actualDelta = Number((postConfidenceScore - pre).toFixed(1));
        const deltaMsg =
          actualDelta > 0
            ? `Self-reported confidence improved by +${actualDelta} points (from ${pre} to ${postConfidenceScore}/10).`
            : `Self-reported confidence recorded at ${postConfidenceScore}/10.`;
        setConfidenceSuccessMsg(deltaMsg);
        if (consensusResult && consensusResult.summary) {
          setConsensusResult({
            ...consensusResult,
            summary: {
              ...consensusResult.summary,
              post_confidence_student: postConfidenceScore,
              confidence_delta: actualDelta,
              confidence_status: 'actual_delta_recorded',
            },
          });
        }
      }
    } catch (err) {
      console.warn('Failed to submit post-confidence', err);
    } finally {
      setIsSubmittingConfidence(false);
    }
  };

  const executeConsensus = async (modelToUse = selectedModel, strictToUse = strictRAG) => {
    setIsLoadingConsensus(true);
    setShowFallbackAnyway(false);
    try {
      const res = await familyConsensusService.runFamilyConsensus(
        answers || {},
        language,
        modelToUse,
        strictToUse
      );
      setConsensusResult(res);
      if (res.summary?.family_id && typeof window !== 'undefined' && window.sessionStorage) {
        window.sessionStorage.setItem('skillsaathi_active_family_id', res.summary.family_id);
      }
    } catch (err: any) {
      setConsensusResult({
        mode: 'live',
        error: err?.message || 'Failed to communicate with RAG consensus service.',
        selectedModel: modelToUse,
      });
    } finally {
      setIsLoadingConsensus(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    setIsLoadingConsensus(true);

    const activeFamilyId =
      familyId ||
      (typeof window !== 'undefined' && window.sessionStorage
        ? window.sessionStorage.getItem('skillsaathi_active_family_id')
        : null);

    const loadOrRun = async () => {
      // 1. Attempt to fetch stored summary from backend first if familyId is known
      if (activeFamilyId) {
        try {
          const stored = await familyConsensusService.getFamilySummary(activeFamilyId);
          if (stored && stored.summary && isMounted) {
            // If already AI-grounded or not strict, use stored summary
            if (stored.summary.counselling_mode === 'ai_grounded' || !strictRAG) {
              setConsensusResult(stored);
              setIsLoadingConsensus(false);
              return;
            }
          }
        } catch {
          // Proceed to run fresh consensus
        }
      }

      // 2. Run fresh consensus with selectedModel and strict mode
      try {
        const res = await familyConsensusService.runFamilyConsensus(
          answers || {},
          language,
          selectedModel,
          strictRAG
        );
        if (isMounted) {
          setConsensusResult(res);
          setIsLoadingConsensus(false);
          if (res.summary?.family_id && typeof window !== 'undefined' && window.sessionStorage) {
            window.sessionStorage.setItem('skillsaathi_active_family_id', res.summary.family_id);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setConsensusResult({
            mode: 'live',
            error: err?.message || 'Failed to communicate with RAG consensus service.',
            selectedModel,
          });
          setIsLoadingConsensus(false);
        }
      }
    };

    loadOrRun();

    return () => {
      isMounted = false;
    };
  }, [answers, language, familyId, selectedModel, strictRAG]);

  const handleRefreshConsensus = () => {
    executeConsensus(selectedModel, strictRAG);
  };

  const recommendations = results.recommendations || [];
  const summary = results.summary;

  return (
    <div
      className="career-discovery-results-view"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '2.25rem',
        width: '100%',
        maxWidth: '920px',
        margin: '0 auto',
      }}
    >
      {/* ========================================================
          SECTION A — Heading and Reassurance
         ======================================================== */}
      <section
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-xl, 16px)',
          padding: '2.25rem 2rem',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.875rem', flexWrap: 'wrap' }}>
          <Badge variant="primary" size="md">
            <Sparkles size={14} aria-hidden="true" style={{ marginRight: '5px' }} />
            <span>{isHi ? 'करियर खोज परिणाम' : isMr ? 'करिअर शोध निकाल' : 'Career Discovery Results'}</span>
          </Badge>
          <Badge variant="neutral" size="sm">
            <span>{isHi ? 'प्रासंगिक सुझाव' : isMr ? 'उपयुक्त शिफारशी' : 'Personalized Suggestions'}</span>
          </Badge>
        </div>

        <h1
          style={{
            fontSize: 'clamp(1.75rem, 3.5vw, 2.25rem)',
            fontWeight: 800,
            color: 'var(--color-text-primary)',
            letterSpacing: '-0.025em',
            margin: '0 0 0.625rem 0',
            lineHeight: 1.25,
          }}
        >
          {isHi
            ? 'आपके करियर खोज परिणाम'
            : isMr
            ? 'तुमचे करिअर शोध निकाल'
            : 'Your Career Discovery Results'}
        </h1>

        <p
          style={{
            fontSize: '1rem',
            color: 'var(--color-text-secondary)',
            margin: 0,
            maxWidth: '740px',
            lineHeight: 1.6,
          }}
        >
          {isHi
            ? 'आपके उत्तर करियर की खोज के लिए एक शुरुआती बिंदु प्रदान करते हैं। ये सुझाव तलाशने के लिए संभावित विकल्प हैं, आपके भविष्य के बारे में कोई अंतिम निर्णय नहीं।'
            : isMr
            ? 'तुमची उत्तरे करिअर शोधण्यासाठी एक प्रारंभिक दिशा देतात. या शिफारशी पडताळणी करण्यासाठीचे पर्याय आहेत, तुमच्या भविष्याबद्दलचा अंतिम निर्णय नाही.'
            : 'Your answers give us a starting point for exploring careers. These suggestions are possibilities to investigate, not a final decision about your future.'}
        </p>

        {/* Quick reassuring badges */}
        <div
          style={{
            display: 'flex',
            gap: '0.875rem',
            flexWrap: 'wrap',
            marginTop: '1.25rem',
            paddingTop: '1.25rem',
            borderTop: '1px solid var(--color-border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
            <CheckCircle2 size={15} style={{ color: 'var(--color-success)' }} />
            <span>{isHi ? 'कोई बाध्यता नहीं' : isMr ? 'कोणतेही बंधन नाही' : 'No forced decisions'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
            <ShieldCheck size={15} style={{ color: 'var(--color-primary)' }} />
            <span>{isHi ? 'प्रमाणित NSQF वोकेशनल कोर्स' : isMr ? 'NCVET प्रमाणित व्यावसायिक अभ्यासक्रम' : 'Aligned to NSQF standards'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
            <Compass size={15} style={{ color: 'var(--color-secondary)' }} />
            <span>{isHi ? 'अपनी गति से खोजें' : isMr ? 'आपल्या गतीने शोधा' : 'Explore at your own pace'}</span>
          </div>
        </div>
      </section>

      {/* ========================================================
          SECTION B — Brief Interests Summary FIRST
         ======================================================== */}
      <section
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1.5px solid var(--color-primary-subtle, #bfdbfe)',
          borderRadius: 'var(--radius-xl, 16px)',
          padding: '2rem',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '1rem' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: 'var(--radius-md, 8px)',
              backgroundColor: 'var(--color-primary-subtle, #eff6ff)',
              color: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Compass size={18} aria-hidden="true" />
          </div>
          <div>
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                letterSpacing: '-0.015em',
                margin: 0,
              }}
            >
              {isHi
                ? 'आपकी रुचियों और प्राथमिकताओं का सारांश'
                : isMr
                ? 'तुमच्या आवडी आणि प्राधान्यांचा सारांश'
                : 'Your Interests & Profile Summary'}
            </h2>
            <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              {isHi
                ? 'आपके द्वारा चुने गए उत्तरों के आधार पर तैयार संक्षिप्त निष्कर्ष'
                : isMr
                ? 'तुम्ही नोंदवलेल्या उत्तरांनुसार तयार केलेला संक्षिप्त आढावा'
                : 'Synthesised from what you shared during the assessment'}
            </span>
          </div>
        </div>

        {/* Narrative Sentences */}
        <div
          style={{
            backgroundColor: 'var(--color-bg)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-lg, 12px)',
            padding: '1.25rem 1.5rem',
            marginBottom: '1.25rem',
          }}
        >
          {summary && summary.sentences.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {summary.sentences.map((sent, idx) => (
                <p
                  key={idx}
                  style={{
                    margin: 0,
                    fontSize: '0.9375rem',
                    color: 'var(--color-text-primary)',
                    lineHeight: 1.6,
                  }}
                >
                  {resolveLocalized(sent, language)}
                </p>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, fontSize: '0.9375rem', color: 'var(--color-text-primary)', lineHeight: 1.6 }}>
              {isHi
                ? 'आप व्यावहारिक कार्यों में रुचि रखते हैं और हाथों से काम करके सीखना पसंद करते हैं। आप नौकरी की स्थिरता और स्पष्ट करियर पथ को प्राथमिकता देते हैं।'
                : isMr
                ? 'तुम्हाला प्रत्यक्ष कृती करणे आणि साधने वापरून शिकणे आवडते. तुम्ही नोकरीची स्थिरता आणि स्पष्ट करिअर प्रगतीला प्राधान्य देता.'
                : 'You enjoy practical, hands-on activities and prefer learning by doing rather than theory alone. You value job stability and clear career progression.'}
            </p>
          )}
        </div>

        {/* Selected Highlight Chips / Tags */}
        {summary && summary.tags.length > 0 && (
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem', letterSpacing: '0.04em' }}>
              {isHi ? 'पहचाने गए मुख्य बिंदु:' : isMr ? 'महत्त्वाचे पैलू:' : 'Identified Profile Attributes:'}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {summary.tags.map((tag, tIdx) => (
                <Badge key={tIdx} variant="secondary" size="md">
                  {resolveLocalized(tag, language)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ========================================================
          SECTION C — Suggested Career Paths IMMEDIATELY AFTER Summary
         ======================================================== */}
      <section>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            marginBottom: '1.25rem',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.25rem' }}>
              {isHi ? 'मिलान किए गए विकल्प' : isMr ? 'जुळणारे पर्याय' : 'Matched Pathways'}
            </div>
            <h2
              style={{
                fontSize: '1.5rem',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                letterSpacing: '-0.02em',
                margin: 0,
              }}
            >
              {isHi
                ? 'तलाशने के लिए करियर मार्ग'
                : isMr
                ? 'पडताळणीसाठी करिअर मार्ग'
                : 'Career Paths to Explore'}
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', margin: '0.25rem 0 0 0' }}>
              {isHi
                ? 'स्किलसाथी कैटलॉग से आपके उत्तरों के आधार पर सुझाई गई व्यावसायिक शाखाएं'
                : isMr
                ? 'स्किलसाथी कॅटलॉगमधून तुमच्या उत्तरांनुसार सुचवलेले व्यावसायिक कोर्सेस'
                : 'Accredited vocational options aligned to your selected interests and preferences'}
            </p>
          </div>

          <Button variant="outline" size="sm" onClick={onExploreCourses} icon={<ArrowRight size={14} />}>
            {isHi ? 'पूरा कैटलॉग देखें' : isMr ? 'सर्व कोर्सेस पहा' : 'Browse All Courses'}
          </Button>
        </div>

        {/* Recommendation Cards */}
        {recommendations.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {recommendations.map((rec, idx) => {
              const { course, matchReason, skillsTaught, jobRoles, durationAndMode, eligibility, whatToVerify } = rec;

              return (
                <div
                  key={course.id || idx}
                  style={{
                    backgroundColor: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-xl, 16px)',
                    padding: '1.75rem',
                    boxShadow: 'var(--shadow-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1.125rem',
                  }}
                >
                  {/* Top Bar: Sector, NSQF, Certification */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                      <Badge variant="primary" size="sm">
                        {course.stream.replace(/_/g, ' ').toUpperCase()}
                      </Badge>
                      <Badge variant="neutral" size="sm">
                        NSQF Level {course.nsqfLevel}
                      </Badge>
                      <Badge variant="secondary" size="sm">
                        {course.certificationBody}
                      </Badge>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                      <Clock size={14} aria-hidden="true" />
                      <span>{durationAndMode}</span>
                    </div>
                  </div>

                  {/* Course Title */}
                  <h3
                    style={{
                      fontSize: '1.25rem',
                      fontWeight: 800,
                      color: 'var(--color-text-primary)',
                      letterSpacing: '-0.015em',
                      margin: 0,
                      lineHeight: 1.35,
                    }}
                  >
                    {course.title}
                  </h3>

                  {/* 1. Why this was suggested */}
                  <div
                    style={{
                      backgroundColor: 'var(--color-primary-subtle, #eff6ff)',
                      borderLeft: '4px solid var(--color-primary)',
                      borderRadius: '0 var(--radius-md, 8px) var(--radius-md, 8px) 0',
                      padding: '0.75rem 1rem',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                      {isHi ? 'यह विकल्प क्यों सुझाया गया:' : isMr ? 'हा पर्याय का सुचवला:' : 'Why this option was suggested:'}
                    </div>
                    <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-primary)', lineHeight: 1.5 }}>
                      {resolveLocalized(matchReason, language)}
                    </p>
                  </div>

                  {/* 2. Skills Taught */}
                  {skillsTaught && skillsTaught.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.375rem' }}>
                        {isHi ? 'सिखाए जाने वाले व्यावहारिक कौशल:' : isMr ? 'शिकवली जाणारी प्रत्यक्ष कौशल्ये:' : 'Key Hands-on Skills Taught:'}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                        {skillsTaught.map((skill, sIdx) => (
                          <span
                            key={sIdx}
                            style={{
                              fontSize: '0.8125rem',
                              padding: '3px 10px',
                              borderRadius: 'var(--radius-sm, 6px)',
                              backgroundColor: 'var(--color-bg)',
                              border: '1px solid var(--color-border-subtle)',
                              color: 'var(--color-text-secondary)',
                            }}
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 3. Job Roles & Eligibility Details Grid */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                      gap: '0.875rem',
                      padding: '0.875rem 1rem',
                      borderRadius: 'var(--radius-md, 8px)',
                      backgroundColor: 'var(--color-bg)',
                      border: '1px solid var(--color-border-subtle)',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                        {isHi ? 'संभावित रोजगार पद:' : isMr ? 'संभाव्य नोकरी पदे:' : 'Possible Job Roles:'}
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                        <Briefcase size={14} style={{ color: 'var(--color-primary)' }} />
                        <span>{jobRoles}</span>
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                        {isHi ? 'पात्रता:' : isMr ? 'पात्रता निकष:' : 'Eligibility:'}
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                        {eligibility}
                      </div>
                    </div>
                  </div>

                  {/* 4. What the user should verify */}
                  <div
                    style={{
                      backgroundColor: 'var(--color-surface-muted, #f8fafc)',
                      border: '1px solid var(--color-border-subtle)',
                      borderRadius: 'var(--radius-md, 8px)',
                      padding: '0.75rem 1rem',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.625rem',
                    }}
                  >
                    <AlertCircle size={16} style={{ color: 'var(--color-secondary)', flexShrink: 0, marginTop: '2px' }} />
                    <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                      <strong style={{ color: 'var(--color-text-primary)' }}>
                        {isHi ? 'दाखिले से पहले क्या जांचें:' : isMr ? 'प्रवेशापूर्वी काय तपासावे:' : 'What you should verify:'}
                      </strong>{' '}
                      {resolveLocalized(whatToVerify, language)}
                    </div>
                  </div>

                  {/* Card Action Buttons */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.75rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid var(--color-border-subtle)',
                    }}
                  >
                    <Button
                      variant="primary"
                      size="md"
                      onClick={() => onViewCourseDetails(course.id)}
                      icon={<BookOpen size={16} />}
                      style={{ minHeight: '44px' }}
                    >
                      {isHi ? 'कोर्स का विवरण देखें' : isMr ? 'कोर्स तपशील पहा' : 'View Course Details'}
                    </Button>

                    <Button
                      variant="outline"
                      size="md"
                      onClick={() => setShowCounsellorModal(true)}
                      icon={<Users size={15} />}
                      style={{ minHeight: '44px' }}
                    >
                      {isHi ? 'काउंसलर से इस पर चर्चा करें' : isMr ? 'समुपदेशकांशी चर्चा करा' : 'Discuss with a Counsellor'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div
            style={{
              padding: '2rem',
              backgroundColor: 'var(--color-surface)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--color-border)',
              textAlign: 'center',
            }}
          >
            <HelpCircle size={32} style={{ color: 'var(--color-text-muted)', marginBottom: '0.75rem' }} />
            <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-secondary)', margin: '0 0 1rem 0' }}>
              {isHi
                ? 'आपकी रुचियों के आधार पर कोई विशिष्ट सीधा मिलान नहीं मिला, लेकिन पूरा कैटलॉग देखकर या काउंसलर से बात करके उपयुक्त विकल्प खोजे जा सकते हैं।'
                : isMr
                ? 'तुमच्या आवडींशी थेट जुळणारा एकही कोर्स सापडला नाही, परंतु संपूर्ण कॅटलॉग पाहून किंवा समुपदेशकांशी बोलून अधिक पर्याय शोधता येतील.'
                : 'No single course matched all selected criteria exactly. Exploring our full catalogue or speaking with a counsellor can help identify promising avenues.'}
            </p>
            <Button variant="primary" size="md" onClick={onExploreCourses}>
              {isHi ? 'सभी कोर्स देखें' : isMr ? 'सर्व कोर्सेस एक्सप्लोर करा' : 'Explore All Courses'}
            </Button>
          </div>
        )}
      </section>

      {/* ========================================================
          SECTION C.2 — Family Consensus Intelligence & Joint Decision Support
         ======================================================== */}
      <section
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-xl, 16px)',
          padding: '2.25rem 2rem',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5rem',
        }}
      >
        {/* Section Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.5rem' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(13, 148, 136, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-primary)',
                }}
              >
                <Users size={20} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.375rem', fontWeight: 800, color: 'var(--color-text-primary)', margin: 0 }}>
                  {isHi
                    ? 'पारिवारिक सहमति इंटेलिजेंस'
                    : isMr
                    ? 'कौटुंबिक सहमती इंटेलिजन्स'
                    : 'Family Consensus Intelligence'}
                </h2>
                <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                  {isHi
                    ? 'छात्र आकांक्षाओं और माता-पिता की प्राथमिकताओं का वस्तुनिष्ठ विश्लेषण'
                    : isMr
                    ? 'विद्यार्थ्यांची आवड आणि पालकांच्या सुरक्षिततेची वस्तुनिष्ठ तुलना'
                    : 'Evidence-grounded comparison bridging student aspirations and parental priorities'}
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexWrap: 'wrap' }}>
            {/* Gemini Model Selector */}
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>RAG Model:</span>
              <select
                value={selectedModel}
                onChange={(e) => {
                  const newModel = e.target.value;
                  setSelectedModel(newModel);
                  if (typeof window !== 'undefined' && window.sessionStorage) {
                    window.sessionStorage.setItem('skillsaathi_rag_model', newModel);
                  }
                  executeConsensus(newModel, strictRAG);
                }}
                disabled={isLoadingConsensus}
                style={{
                  fontSize: '0.8125rem',
                  padding: '0.35rem 0.6rem',
                  borderRadius: '6px',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-surface)',
                  color: 'var(--color-text-primary)',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {AVAILABLE_GEMINI_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Strict RAG Checkbox */}
            <label
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '0.75rem',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer',
                userSelect: 'none',
              }}
              title="When enabled, displays actual errors if Gemini RAG fails instead of silently using deterministic scoring"
            >
              <input
                type="checkbox"
                checked={strictRAG}
                onChange={(e) => {
                  const val = e.target.checked;
                  setStrictRAG(val);
                  if (typeof window !== 'undefined' && window.sessionStorage) {
                    window.sessionStorage.setItem('skillsaathi_strict_rag', val ? 'true' : 'false');
                  }
                }}
              />
              <span>Strict RAG Mode</span>
            </label>

            {consensusResult?.mode === 'live' && !consensusResult.error && (
              <Badge variant="success" size="sm">
                <CheckCircle2 size={13} style={{ marginRight: '4px' }} />
                <span>Live FastAPI Backend</span>
              </Badge>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshConsensus}
              disabled={isLoadingConsensus}
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem' }}
            >
              <RefreshCw size={13} style={{ marginRight: '5px' }} className={isLoadingConsensus ? 'animate-spin' : ''} />
              {isLoadingConsensus ? 'Synthesizing...' : 'Re-run RAG'}
            </Button>
          </div>
        </div>

        {/* Loading State for Consensus Analysis */}
        {isLoadingConsensus && (
          <div
            style={{
              padding: '2.5rem 1.5rem',
              textAlign: 'center',
              backgroundColor: '#f8fafc',
              borderRadius: '12px',
              border: '1px dashed var(--color-border, #cbd5e1)',
            }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--color-primary)', fontWeight: 600 }}>
              <RefreshCw size={18} className="animate-spin" />
              <span>
                Synthesizing RAG Consensus with {AVAILABLE_GEMINI_MODELS.find(m => m.id === selectedModel)?.name || selectedModel}...
              </span>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted, #64748b)', margin: '8px 0 0 0' }}>
              Retrieving dense course embeddings, reconciling family priorities, and querying Google Gemini API.
            </p>
          </div>
        )}

        {/* RAG Execution Error Banner (Strict Mode) */}
        {!isLoadingConsensus && consensusResult?.error && !showFallbackAnyway && (
          <div
            style={{
              padding: '1.5rem',
              backgroundColor: '#fef2f2',
              borderRadius: '12px',
              border: '1.5px solid #f87171',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '50%',
                  backgroundColor: '#fee2e2',
                  color: '#dc2626',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <AlertTriangle size={22} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <strong style={{ color: '#991b1b', fontSize: '1.0625rem' }}>
                    Gemini RAG Generation Failed
                  </strong>
                  <Badge variant="warning" size="sm">
                    Model: {consensusResult.selectedModel || selectedModel}
                  </Badge>
                  <Badge variant="neutral" size="sm">
                    Strict RAG Active
                  </Badge>
                </div>
                <p style={{ color: '#b91c1c', fontSize: '0.875rem', margin: '6px 0 0 0', lineHeight: 1.5 }}>
                  Because <strong>Strict RAG Mode</strong> is enabled, execution paused so you can inspect the exact error rather than silently defaulting to deterministic scoring.
                </p>
                <div
                  style={{
                    marginTop: '0.75rem',
                    padding: '0.875rem 1rem',
                    backgroundColor: '#ffffff',
                    border: '1px solid #fca5a5',
                    borderRadius: '8px',
                    fontFamily: 'monospace',
                    fontSize: '0.8125rem',
                    color: '#991b1b',
                    wordBreak: 'break-word',
                  }}
                >
                  {consensusResult.error}
                </div>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.75rem',
                borderTop: '1px solid #fecaca',
                paddingTop: '0.875rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <select
                  value={selectedModel}
                  onChange={(e) => {
                    const newModel = e.target.value;
                    setSelectedModel(newModel);
                    if (typeof window !== 'undefined' && window.sessionStorage) {
                      window.sessionStorage.setItem('skillsaathi_rag_model', newModel);
                    }
                  }}
                  style={{
                    fontSize: '0.8125rem',
                    padding: '0.45rem 0.75rem',
                    borderRadius: '6px',
                    border: '1px solid #f87171',
                    backgroundColor: '#ffffff',
                    fontWeight: 600,
                  }}
                >
                  {AVAILABLE_GEMINI_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      Try {m.name}
                    </option>
                  ))}
                </select>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => executeConsensus(selectedModel, true)}
                  disabled={isLoadingConsensus}
                >
                  <RefreshCw size={14} style={{ marginRight: '6px' }} className={isLoadingConsensus ? 'animate-spin' : ''} />
                  Retry with {AVAILABLE_GEMINI_MODELS.find(m => m.id === selectedModel)?.name}
                </Button>
              </div>

              <button
                type="button"
                onClick={() => setShowFallbackAnyway(true)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#6b7280',
                  fontSize: '0.8125rem',
                  textDecoration: 'underline',
                  cursor: 'pointer',
                  padding: '4px 8px',
                }}
              >
                View Deterministic Consensus Fallback Anyway →
              </button>
            </div>
          </div>
        )}

        {/* Readiness Status Banner */}
        {consensusResult?.summary && (!consensusResult.error || showFallbackAnyway) && (
          <div
            style={{
              padding: '1rem 1.25rem',
              borderRadius: '12px',
              backgroundColor:
                consensusResult.summary.overall_consensus_readiness === 'high'
                  ? 'rgba(16, 185, 129, 0.08)'
                  : consensusResult.summary.overall_consensus_readiness === 'moderate'
                  ? 'rgba(245, 158, 11, 0.08)'
                  : 'rgba(239, 68, 68, 0.08)',
              border:
                consensusResult.summary.overall_consensus_readiness === 'high'
                  ? '1px solid rgba(16, 185, 129, 0.25)'
                  : consensusResult.summary.overall_consensus_readiness === 'moderate'
                  ? '1px solid rgba(245, 158, 11, 0.25)'
                  : '1px solid rgba(239, 68, 68, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Scale size={20} style={{ color: 'var(--color-primary)' }} />
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <strong style={{ fontSize: '0.9375rem', color: 'var(--color-text-primary)' }}>
                    Consensus Readiness:{' '}
                    {consensusResult.summary.overall_consensus_readiness === 'high'
                      ? 'High Alignment'
                      : consensusResult.summary.overall_consensus_readiness === 'moderate'
                      ? 'Moderate Alignment'
                      : 'Dialogue Recommended'}
                  </strong>
                  {consensusResult.summary.family_id && (
                    <Badge variant="neutral" size="sm">
                      ID: {consensusResult.summary.family_id.slice(0, 8)}
                    </Badge>
                  )}
                  <Badge variant={consensusResult.summary.counselling_mode === 'ai_grounded' ? 'primary' : 'neutral'} size="sm">
                    {consensusResult.summary.counselling_mode === 'ai_grounded'
                      ? `Grounded AI (${consensusResult.summary.counselling_model || selectedModel})`
                      : 'Deterministic Consensus Engine'}
                  </Badge>
                </div>
                <p style={{ margin: '0.125rem 0 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  {consensusResult.summary.overall_consensus_readiness === 'high'
                    ? 'Both student passions and parent stability concerns converge strongly on accredited pathways.'
                    : consensusResult.summary.overall_consensus_readiness === 'moderate'
                    ? 'Core technical interest aligns; structured discussion recommended on fee ceilings and degree credit progression.'
                    : 'Explicit differences in sector or time-to-earn identified. Review the resolution pathways below.'}
                </p>
                {consensusResult.summary.counselling_mode_note && (
                  <div style={{ marginTop: '0.375rem', fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Info size={12} style={{ flexShrink: 0 }} />
                    <span>{consensusResult.summary.counselling_mode_note}</span>
                  </div>
                )}
              </div>
            </div>

            {consensusResult.summary.pre_confidence_student !== undefined && (
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                Baseline Confidence — Student: {consensusResult.summary.pre_confidence_student}/10 | Parent:{' '}
                {consensusResult.summary.pre_confidence_parent || 5.5}/10
              </span>
            )}
          </div>
        )}

        {/* Multi-Agent Dialogue Log (LangGraph Turn-Taking) */}
        {consensusResult?.summary?.agent_dialogue && consensusResult.summary.agent_dialogue.length > 0 && (
          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Users size={18} style={{ color: '#2563eb' }} />
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  {isHi ? 'मल्टी-एजेंट परिवार मध्यस्थता संवाद (LangGraph)' : isMr ? 'मल्टी-एजंट कुटुंब संवाद चर्चा (LangGraph)' : 'Multi-Agent Family Mediation Dialogue (LangGraph)'}
                </h3>
              </div>
              <Badge variant="primary" size="sm">
                4 Specialized Agents
              </Badge>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {consensusResult.summary.agent_dialogue.map((turn, tIdx) => (
                <ChatMessage
                  key={tIdx}
                  message={{
                    id: `agent-turn-${tIdx}`,
                    sessionId: consensusResult.summary?.family_id || 'active',
                    senderRole: turn.name.toLowerCase().includes('parent') ? 'parent' : 'counsellor',
                    senderName: turn.name,
                    content: turn.content,
                    timestamp: 'Verified Agent Turn',
                    language: language,
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* NCrF Credit Progression Ladder Component */}
        {consensusResult?.summary && (
          <NCrFCreditLadder
            currentLevel={consensusResult.summary.top_pathway_recommendations?.[0]?.nsqf_level || 4}
            highlightStream={consensusResult.summary.top_pathway_recommendations?.[0]?.stream || 'Technical Vocational'}
          />
        )}

        {/* Stated Priorities Comparison (Student vs Parent) */}
        {consensusResult?.summary && (consensusResult.summary.student_priorities || consensusResult.summary.parent_priorities) && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1.25rem',
            }}
          >
            {/* Student Priorities */}
            <div
              style={{
                backgroundColor: 'rgba(59, 130, 246, 0.04)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Users size={16} style={{ color: '#2563eb' }} />
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                  {isHi ? 'छात्र की प्राथमिकताएं और आकांक्षाएं' : isMr ? 'विद्यार्थ्याची आवड आणि उद्दिष्टे' : 'Student Aspirations & Priorities'}
                </h3>
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                {(consensusResult.summary.student_priorities || []).map((item, idx) => (
                  <li key={idx} style={{ fontSize: '0.78125rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Parent Priorities */}
            <div
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.04)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={16} style={{ color: '#059669' }} />
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                  {isHi ? 'अभिभावक की चिंताएं और प्राथमिकताएं' : isMr ? 'पालकांची सुरक्षितता आणि प्राधान्यक्रम' : 'Parent Considerations & Priorities'}
                </h3>
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                {(consensusResult.summary.parent_priorities || []).map((item, idx) => (
                  <li key={idx} style={{ fontSize: '0.78125rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 2-Column Grid: Shared Strengths vs Disagreements */}
        {consensusResult?.summary && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '1.25rem',
            }}
          >
            {/* Card 1: Agreed Common Ground */}
            <div
              style={{
                backgroundColor: 'var(--color-bg-subtle, #f8fafc)',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.875rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={16} style={{ color: 'var(--color-success, #16a34a)' }} />
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                  Agreed Common Ground ({consensusResult.summary.shared_strengths.length})
                </h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {consensusResult.summary.shared_strengths.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '8px',
                      padding: '0.75rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <strong style={{ fontSize: '0.8125rem', color: 'var(--color-text-primary)' }}>{item.topic}</strong>
                      <span style={{ fontSize: '0.6875rem', color: 'var(--color-success)', fontWeight: 700 }}>
                        {Math.round(item.alignment_score * 100)}% Match
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                      {item.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Card 2: Identified Disagreements & Resolution */}
            <div
              style={{
                backgroundColor: 'var(--color-bg-subtle, #f8fafc)',
                border: '1px solid var(--color-border)',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.875rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={16} style={{ color: 'var(--color-warning, #d97706)' }} />
                <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                  Stated Differences & Resolution Pathways ({consensusResult.summary.identified_disagreements.length})
                </h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {consensusResult.summary.identified_disagreements.map((d, idx) => (
                  <div
                    key={idx}
                    style={{
                      backgroundColor: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '8px',
                      padding: '0.75rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.375rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ fontSize: '0.8125rem', color: 'var(--color-text-primary)' }}>{d.topic}</strong>
                      <Badge variant={d.severity === 'high' ? 'secondary' : 'warning'} size="sm">
                        {d.severity.toUpperCase()}
                      </Badge>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                      <div>
                        <strong>Student:</strong> {d.student_stance}
                      </div>
                      <div style={{ marginTop: '2px' }}>
                        <strong>Parent:</strong> {d.parent_stance}
                      </div>
                    </div>

                    <div
                      style={{
                        marginTop: '0.25rem',
                        padding: '0.375rem 0.5rem',
                        borderRadius: '6px',
                        backgroundColor: 'rgba(13, 148, 136, 0.06)',
                        borderLeft: '2px solid var(--color-primary)',
                        fontSize: '0.6875rem',
                        color: 'var(--color-primary)',
                        lineHeight: 1.4,
                      }}
                    >
                      <strong>Resolution:</strong> {d.resolution_pathway}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Side-by-Side Pathway Comparison Card */}
        {consensusResult?.summary?.pathway_comparison && (
          <div
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1.5px solid var(--color-primary-subtle, #99f6e4)',
              borderRadius: '12px',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Scale size={18} style={{ color: 'var(--color-primary)' }} />
                <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0, color: 'var(--color-text-primary)' }}>
                  {isHi ? 'विकल्प तुलना: पाथवे ए बनाम पाथवे बी' : isMr ? 'पर्याय तुलना: पाथवे ए विरुद्ध पाथवे बी' : 'Side-by-Side Pathway Comparison'}
                </h3>
              </div>
              <Badge variant="neutral" size="sm">
                <span>Multi-Criteria Trade-offs</span>
              </Badge>
            </div>

            {/* 2 Pathways Header */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', backgroundColor: 'rgba(13, 148, 136, 0.06)', border: '1px solid rgba(13, 148, 136, 0.2)' }}>
                <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase' }}>
                  Pathway A (Top Recommendation)
                </div>
                <strong style={{ fontSize: '0.9375rem', color: 'var(--color-text-primary)' }}>
                  {consensusResult.summary.pathway_comparison.pathway_a_title}
                </strong>
              </div>
              <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', backgroundColor: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
                <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#4f46e5', textTransform: 'uppercase' }}>
                  Pathway B (Alternative Option)
                </div>
                <strong style={{ fontSize: '0.9375rem', color: 'var(--color-text-primary)' }}>
                  {consensusResult.summary.pathway_comparison.pathway_b_title}
                </strong>
              </div>
            </div>

            {/* Comparison Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
              <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle, #f8fafc)', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>Duration Comparison</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-primary)', fontWeight: 500, marginTop: '2px' }}>
                  {consensusResult.summary.pathway_comparison.duration_comparison}
                </div>
              </div>
              <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle, #f8fafc)', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>Fee Ceiling Comparison</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-primary)', fontWeight: 500, marginTop: '2px' }}>
                  {consensusResult.summary.pathway_comparison.fee_comparison}
                </div>
              </div>
              <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle, #f8fafc)', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>Wage Benchmark Indicator</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-primary)', fontWeight: 500, marginTop: '2px' }}>
                  {consensusResult.summary.pathway_comparison.wage_benchmark_comparison}
                </div>
              </div>
              <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle, #f8fafc)', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>Academic / NSQF Progression</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-primary)', fontWeight: 500, marginTop: '2px' }}>
                  {consensusResult.summary.pathway_comparison.progression_comparison}
                </div>
              </div>
            </div>

            {/* Key Trade-off Summary */}
            <div
              style={{
                padding: '0.875rem 1rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                fontSize: '0.8125rem',
                color: 'var(--color-text-primary)',
                lineHeight: 1.5,
              }}
            >
              <strong>{isHi ? 'मुख्य विकल्प तुलना (Trade-off): ' : isMr ? 'मुख्य पर्याय तुलना (Trade-off): ' : 'Key Trade-off Summary: '}</strong>
              <span>{consensusResult.summary.pathway_comparison.key_trade_off_summary}</span>
            </div>

            {/* Plain-Language Parent Explanations */}
            {consensusResult.summary.pathway_comparison.affordability_explanation && (
              <div
                style={{
                  padding: '0.875rem 1rem',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  fontSize: '0.8125rem',
                  color: 'var(--color-text-primary)',
                  lineHeight: 1.5,
                }}
              >
                <strong>{isHi ? 'लागत व परिवार बजट समझ (Affordability): ' : isMr ? 'खर्च व कौटुंबिक बजेट (Affordability): ' : 'Household Affordability Explanation: '}</strong>
                <span>{consensusResult.summary.pathway_comparison.affordability_explanation}</span>
              </div>
            )}

            {consensusResult.summary.pathway_comparison.eligibility_explanation && (
              <div
                style={{
                  padding: '0.875rem 1rem',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.25)',
                  fontSize: '0.8125rem',
                  color: 'var(--color-text-primary)',
                  lineHeight: 1.5,
                }}
              >
                <strong>{isHi ? 'प्रवेश पात्रता (Eligibility): ' : isMr ? 'प्रवेश पात्रता (Eligibility): ' : 'Eligibility & Prerequisites: '}</strong>
                <span>{consensusResult.summary.pathway_comparison.eligibility_explanation}</span>
              </div>
            )}

            {/* Transparent Unknown Values Indicator */}
            {consensusResult.summary.pathway_comparison.unknown_values_disclaimer && (
              <div
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(100, 116, 139, 0.08)',
                  border: '1px dashed rgba(100, 116, 139, 0.3)',
                  fontSize: '0.75rem',
                  color: '#475569',
                  lineHeight: 1.4,
                }}
              >
                <strong>{isHi ? 'साक्ष्य पारदर्शिता (Unknown Values): ' : isMr ? 'माहिती पारदर्शकता (Unknown Values): ' : 'Transparency Notice on Unknown Values: '}</strong>
                <span>{consensusResult.summary.pathway_comparison.unknown_values_disclaimer}</span>
              </div>
            )}

            {/* Evidence Status */}
            <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Info size={12} style={{ flexShrink: 0 }} />
              <span>{consensusResult.summary.pathway_comparison.evidence_status}</span>
            </div>
          </div>
        )}

        {/* Explainable Factors for Top Courses */}
        {consensusResult?.summary?.top_pathway_recommendations && consensusResult.summary.top_pathway_recommendations.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0, color: 'var(--color-text-primary)' }}>
              {isHi ? 'कोर्स मूल्यांकन और साक्ष्य सीमाएं' : isMr ? 'अभ्यासक्रम मूल्यांकन आणि मर्यादा' : 'Explainable Course Evaluation & Evidence Boundaries'}
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              {consensusResult.summary.top_pathway_recommendations.slice(0, 2).map((rec, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '10px',
                    padding: '1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.625rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '0.875rem', color: 'var(--color-text-primary)' }}>{rec.course_title}</strong>
                    <Badge variant="primary" size="sm">Fit {rec.fit_score}%</Badge>
                  </div>

                  {/* Supporting Factors */}
                  {rec.supporting_factors && rec.supporting_factors.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#059669', marginBottom: '2px' }}>
                        ✓ Supporting Factors
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '1rem', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                        {rec.supporting_factors.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Limiting Factors */}
                  {rec.limiting_factors && rec.limiting_factors.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#d97706', marginBottom: '2px' }}>
                        ⚠ Limiting Factors / Constraints
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '1rem', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                        {rec.limiting_factors.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Missing Evidence Flags */}
                  {rec.missing_evidence_flags && rec.missing_evidence_flags.length > 0 && (
                    <div style={{ padding: '0.5rem', borderRadius: '6px', backgroundColor: 'var(--color-bg-subtle, #f8fafc)', border: '1px dashed var(--color-border)' }}>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--color-text-muted)', marginBottom: '2px' }}>
                        Missing Evidence Flags (Verified facts only):
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '1rem', fontSize: '0.6875rem', color: 'var(--color-text-muted)' }}>
                        {rec.missing_evidence_flags.map((flag, i) => (
                          <li key={i}>{flag}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unresolved Concerns Card */}
        {consensusResult?.summary?.unresolved_concerns && consensusResult.summary.unresolved_concerns.length > 0 && (
          <div
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '12px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.625rem' }}>
              <AlertCircle size={16} style={{ color: '#d97706' }} />
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                {isHi ? 'अनसुलझे मुद्दे और आगामी चर्चा बिंदु' : isMr ? 'न सुटलेले प्रश्न आणि चर्चेचे मुद्दे' : 'Unresolved Family Concerns & Action Items'}
              </h3>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              {consensusResult.summary.unresolved_concerns.map((c, idx) => (
                <li key={idx} style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Card 3: Actionable Family Discussion Guide */}
        {consensusResult?.summary?.discussion_guide && (
          <div
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '12px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <MessageSquare size={16} style={{ color: 'var(--color-primary)' }} />
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                Recommended Family Dialogue Guide
              </h3>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {consensusResult.summary.discussion_guide.map((step, idx) => (
                <li key={idx} style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                  {step}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Card 4: Actual Self-Reported Post-Guidance Confidence Tracker (Opt-In) */}
        {consensusResult?.summary && (
          <div
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1.5px solid var(--color-border)',
              borderRadius: '12px',
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Award size={18} style={{ color: 'var(--color-primary)' }} />
                  <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0, color: 'var(--color-text-primary)' }}>
                    {isHi
                      ? 'काउंसलिंग के बाद विश्वास ट्रैकर (स्वैच्छिक)'
                      : isMr
                      ? 'सल्लामसलतीनंतरचा आत्मविश्वास ट्रॅकर (ऐच्छिक)'
                      : 'Post-Guidance Confidence Tracker (Opt-In)'}
                  </h3>
                </div>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                  {isHi
                    ? 'विकल्पों और ट्रेड-ऑफ की समीक्षा के बाद अपना वास्तविक विश्वास दर्ज करें। कोई निश्चित या कृत्रिम स्कोर नहीं बनाया जाता।'
                    : isMr
                    ? 'पर्याय समजून घेतल्यानंतर तुमचा प्रत्यक्ष आत्मविश्वास नोंदवा. कोणताही खोटा किंवा स्थिर स्कोअर दिला जात नाही.'
                    : 'Report your actual confidence after reviewing trade-offs. Measured directly from user inputs (never fabricated).'}
                </p>
              </div>

              {consensusResult.summary.confidence_status === 'actual_delta_recorded' && (
                <Badge variant="success" size="sm">
                  <Check size={13} style={{ marginRight: '4px' }} />
                  <span>Actual Delta Recorded</span>
                </Badge>
              )}
            </div>

            {/* Display recorded delta if available */}
            {(consensusResult.summary.confidence_delta !== undefined && consensusResult.summary.confidence_delta !== null) || confidenceSuccessMsg ? (
              <div
                style={{
                  padding: '1rem',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <CheckCircle2 size={20} style={{ color: '#059669', flexShrink: 0 }} />
                <div>
                  <strong style={{ fontSize: '0.875rem', color: '#065f46' }}>
                    {confidenceSuccessMsg ||
                      (consensusResult.summary.confidence_delta !== undefined &&
                      consensusResult.summary.confidence_delta !== null &&
                      consensusResult.summary.confidence_delta > 0
                        ? `Self-reported confidence improved by +${consensusResult.summary.confidence_delta} points.`
                        : consensusResult.summary.confidence_delta === 0
                        ? 'Reported confidence remained steady.'
                        : `Reported confidence changed by ${consensusResult.summary.confidence_delta} points.`)}
                  </strong>
                  <div style={{ fontSize: '0.75rem', color: '#047857', marginTop: '2px' }}>
                    Baseline Pre-Score: {consensusResult.summary.pre_confidence_student || 6.0}/10 → Recorded Post-Score:{' '}
                    {consensusResult.summary.post_confidence_student || postConfidenceScore}/10
                  </div>
                </div>
              </div>
            ) : (
              /* Interactive Opt-In Submission Form */
              <div
                style={{
                  padding: '1.25rem',
                  borderRadius: '10px',
                  backgroundColor: 'var(--color-bg-subtle, #f8fafc)',
                  border: '1px solid var(--color-border)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                }}
              >
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {isHi ? 'मूल्यांकनकर्ता:' : isMr ? 'नोंदवणारा:' : 'Rating as:'}
                  </span>
                  {(['student', 'parent', 'joint'] as const).map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setPostConfidenceRole(r)}
                      style={{
                        padding: '0.35rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid',
                        borderColor: postConfidenceRole === r ? 'var(--color-primary)' : 'var(--color-border)',
                        backgroundColor: postConfidenceRole === r ? 'rgba(13, 148, 136, 0.1)' : 'var(--color-surface)',
                        color: postConfidenceRole === r ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                      }}
                    >
                      {r}
                    </button>
                  ))}
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem' }}>
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {isHi ? 'काउंसलिंग के बाद आत्मविश्वास स्तर (1-10):' : isMr ? 'सल्लामसलतीनंतरचा आत्मविश्वास (1-10):' : 'Self-Reported Confidence (1-10):'}
                    </span>
                    <strong style={{ fontSize: '0.9375rem', color: 'var(--color-primary)' }}>
                      {postConfidenceScore} / 10
                    </strong>
                  </div>

                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((score) => (
                      <button
                        key={score}
                        type="button"
                        onClick={() => setPostConfidenceScore(score)}
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '6px',
                          border: '1px solid',
                          borderColor: postConfidenceScore === score ? 'var(--color-primary)' : 'var(--color-border)',
                          backgroundColor: postConfidenceScore === score ? 'var(--color-primary)' : 'var(--color-surface)',
                          color: postConfidenceScore === score ? '#ffffff' : 'var(--color-text-primary)',
                          fontWeight: 700,
                          fontSize: '0.8125rem',
                          cursor: 'pointer',
                        }}
                      >
                        {score}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <input
                    type="text"
                    value={postConfidenceFeedback}
                    onChange={(e) => setPostConfidenceFeedback(e.target.value)}
                    placeholder={
                      isHi
                        ? 'वैकल्पिक टिप्पणी: किस बिंदु ने निर्णय को स्पष्ट करने में मदद की?'
                        : isMr
                        ? 'ऐच्छिक अभिप्राय: कोणत्या मुद्द्याने संभ्रम दूर केला?'
                        : 'Optional reflection: What helped clarify your family decision?'
                    }
                    maxLength={300}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      border: '1px solid var(--color-border)',
                      fontSize: '0.8125rem',
                      backgroundColor: 'var(--color-surface)',
                      color: 'var(--color-text-primary)',
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <Button
                    variant="primary"
                    size="sm"
                    icon={<Send size={14} />}
                    onClick={handleSubmitPostConfidence}
                    disabled={isSubmittingConfidence}
                  >
                    {isSubmittingConfidence
                      ? 'Saving...'
                      : isHi
                      ? 'विश्वास रेटिंग सहेजें'
                      : isMr
                      ? 'आत्मविश्वास रेटिंग जतन करा'
                      : 'Submit Post-Counselling Rating'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Disclaimer Note */}
        <p style={{ margin: 0, fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontStyle: 'italic', textAlign: 'center' }}>
          {consensusResult?.summary?.disclaimer ||
            'Demonstration data based on deterministic consensus engine. Official government API integration and live district wage feeds planned for Milestone 2.'}
        </p>
      </section>

      {/* ========================================================
          SECTION D — Next Steps
         ======================================================== */}
      <section
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-xl, 16px)',
          padding: '2rem',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--color-text-primary)', margin: '0 0 0.375rem 0' }}>
            {isHi ? 'सुझाए गए अगले कदम' : isMr ? 'पुढील उपयुक्त पावले' : 'Suggested Next Steps'}
          </h2>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', margin: 0 }}>
            {isHi
              ? 'इन विकल्पों की समीक्षा करने या अपने उत्तरों को संशोधित करने के लिए नीचे दिए गए कदमों का उपयोग करें'
              : isMr
              ? 'हे पर्याय अधिक जाणून घेण्यासाठी किंवा उत्तरे बदलण्यासाठी खालील पर्यायांचा वापर करा'
              : 'Choose how you would like to proceed with your career discovery'}
          </p>
        </div>

        {/* 4 Action Buttons */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '0.875rem',
          }}
        >
          <Button
            variant="primary"
            size="md"
            icon={<BookOpen size={16} />}
            onClick={onExploreCourses}
            style={{ minHeight: '48px', justifyContent: 'center' }}
          >
            {isHi ? 'सभी कोर्स देखें' : isMr ? 'सर्व कोर्सेस पहा' : 'Explore All Courses'}
          </Button>

          <Button
            variant="outline"
            size="md"
            icon={<Edit3 size={16} />}
            onClick={onChangeAnswers}
            style={{ minHeight: '48px', justifyContent: 'center' }}
          >
            {isHi ? 'मेरे उत्तर बदलें' : isMr ? 'माझी उत्तरे बदला' : 'Change My Answers'}
          </Button>

          <Button
            variant="outline"
            size="md"
            icon={<UserCheck size={16} />}
            onClick={() => setShowCounsellorModal(true)}
            style={{ minHeight: '48px', justifyContent: 'center' }}
          >
            {isHi ? 'काउंसलर से बात करें' : isMr ? 'समुपदेशकांशी बोला' : 'Talk to a Counsellor'}
          </Button>

          <Button
            variant="ghost"
            size="md"
            icon={<RotateCcw size={16} />}
            onClick={() => setShowRestartConfirm(true)}
            style={{ minHeight: '48px', justifyContent: 'center', color: 'var(--color-text-secondary)' }}
          >
            {isHi ? 'फिर से शुरू करें' : isMr ? 'पुन्हा नव्याने सुरू करा' : 'Start Again'}
          </Button>
        </div>

        {/* Honest Transparency Note */}
        <div
          style={{
            padding: '1rem',
            borderRadius: 'var(--radius-md, 8px)',
            backgroundColor: 'var(--color-surface-muted, #f8fafc)',
            border: '1px solid var(--color-border-subtle)',
            fontSize: '0.8125rem',
            color: 'var(--color-text-muted)',
            lineHeight: 1.5,
          }}
        >
          <strong style={{ color: 'var(--color-text-primary)' }}>
            {isHi ? 'प्रोटोटाइप पारदर्शिता सूचना:' : isMr ? 'पारदर्शकता सूचना:' : 'Prototype Transparency Notice:'}
          </strong>{' '}
          {isHi
            ? 'यह मूल्यांकन एक स्थानीय प्रोटोटाइप प्रदर्शन है, कोई मनोवैज्ञानिक परीक्षण या नौकरी की कानूनी गारंटी नहीं। कोर्स की फीस, सीटें और मान्यता प्रशिक्षण केंद्र से अवश्य सत्यापित करें।'
            : isMr
            ? 'हे मूल्यांकन प्रात्यक्षिक नमुना सूचना आहे, कोणतीही नोकरी हमी किंवा वैद्यकीय चाचणी नाही. कोणत्याही संस्थेत प्रवेश घेण्यापूर्वी प्रत्यक्ष NCVET मान्यता व फी तपासून घ्या.'
            : 'These recommendations are prototype discovery suggestions based on your responses, not guaranteed employment contracts or definitive clinical tests. Always verify batch timings, subsidies, and official affiliation directly with the training center.'}
        </div>
      </section>

      {/* Restart Confirmation Dialog */}
      {showRestartConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="restart-results-title"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.55)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            backdropFilter: 'blur(3px)',
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--color-surface)',
              borderRadius: 'var(--radius-lg, 12px)',
              padding: '1.75rem',
              maxWidth: '440px',
              width: '100%',
              boxShadow: 'var(--shadow-lg)',
              border: '1px solid var(--color-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-warning-subtle, #fef3c7)',
                  color: 'var(--color-warning, #d97706)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <AlertCircle size={20} aria-hidden="true" />
              </div>
              <h2
                id="restart-results-title"
                style={{
                  fontSize: '1.125rem',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}
              >
                {isHi ? 'क्या नया मूल्यांकन शुरू करना चाहते हैं?' : isMr ? 'नवीन मूल्यांकन सुरू करायचे का?' : 'Start a new assessment?'}
              </h2>
            </div>

            <p
              style={{
                fontSize: '0.875rem',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.5,
                marginBottom: '1.5rem',
              }}
            >
              {isHi
                ? 'इससे आपके पिछले मूल्यांकन के उत्तर साफ हो जाएंगे ताकि आप नए सिरे से शुरुआत कर सकें। सहेजे गए कोर्स या अन्य प्राथमिकताएं सुरक्षित रहेंगी।'
                : isMr
                ? 'यामुळे तुमची मागील मूल्यांकनाची उत्तरे काढून नव्याने सुरुवात होईल. सेव्ह केलेले कोर्सेस सुरक्षित राहतील.'
                : 'This will reset your current assessment answers so you can start fresh. Saved courses and other application preferences will not be affected.'}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Button
                variant="outline"
                size="md"
                onClick={() => setShowRestartConfirm(false)}
                style={{ minHeight: '44px' }}
              >
                {isHi ? 'रद्द करें' : isMr ? 'रद्द करा' : 'Cancel'}
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={() => {
                  setShowRestartConfirm(false);
                  onRestart();
                }}
                style={{ minHeight: '44px' }}
              >
                {isHi ? 'हाँ, नए सिरे से शुरू करें' : isMr ? 'होय, नव्याने सुरू करा' : 'Yes, Start Fresh'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Human Counsellor Escalation Modal */}
      <CounsellorRequestForm
        isOpen={showCounsellorModal}
        onClose={() => setShowCounsellorModal(false)}
        language={language}
        courseTitle={recommendations[0]?.course.title}
      />
    </div>
  );
};

export default AssessmentResults;
