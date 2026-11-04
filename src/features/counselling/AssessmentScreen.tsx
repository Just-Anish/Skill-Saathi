import React, { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, AlertCircle, Cpu } from 'lucide-react';
import {
  AssessmentAnswers,
  AnswerValue,
} from './assessmentTypes';
import { assessmentService } from './assessmentService';
import { AssessmentProgress } from './AssessmentProgress';
import { QuestionRenderer } from './QuestionRenderer';
import { AssessmentResults } from './AssessmentResults';
import { CareerGuidanceIntro } from './CareerGuidanceIntro';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { AVAILABLE_GEMINI_MODELS } from '../../services/api/familyConsensusService';
import { ROUTES } from '../../app/routes';
import { useTranslation, SupportedLanguageCode } from '../../i18n';

export interface AssessmentScreenProps {
  courseId?: string | null;
  onNavigate?: (route: string) => void;
  onClearCourseContext?: () => void;
  onViewCourseDetails?: (courseId: string) => void;
}

export type GuidanceViewMode = 'intro' | 'assessment' | 'model_select' | 'results';

export const AssessmentScreen: React.FC<AssessmentScreenProps> = ({
  courseId,
  onNavigate,
  onClearCourseContext,
  onViewCourseDetails,
}) => {
  const { language, changeLanguage, t } = useTranslation();
  const [viewMode, setViewMode] = useState<GuidanceViewMode>('intro');
  const [answers, setAnswers] = useState<AssessmentAnswers>({});
  const [activeQuestionIndex, setActiveQuestionIndex] = useState<number>(0);
  const [historyStack, setHistoryStack] = useState<number[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showExitModal, setShowExitModal] = useState<boolean>(false);
  const [hasSavedSession, setHasSavedSession] = useState<boolean>(false);

  const [selectedRAGModel, setSelectedRAGModel] = useState<string>(() => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      return window.sessionStorage.getItem('skillsaathi_rag_model') || 'gemini-flash-lite-latest';
    }
    return 'gemini-flash-lite-latest';
  });

  const [strictRAG, setStrictRAG] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      return window.sessionStorage.getItem('skillsaathi_strict_rag') !== 'false';
    }
    return true;
  });

  // Restore saved session or pre-seed course context on initial mount
  useEffect(() => {
    const saved = assessmentService.loadSession();
    if (saved && Object.keys(saved.answers).length > 0) {
      setAnswers(saved.answers);
      setActiveQuestionIndex(saved.activeQuestionIndex || 0);
      setHasSavedSession(true);
      if (saved.isCompleted) {
        setViewMode('results');
      }
    } else if (courseId) {
      // If user directly clicked "Ask counsellor about this course"
      setAnswers({ q_target_course: courseId });
    }
  }, [courseId]);

  // Compute active question list dynamically based on current answers
  const activeQuestions = assessmentService.getActiveQuestions(answers);
  const totalQuestions = activeQuestions.length;

  // Ensure activeQuestionIndex is within bounds if branching changes length
  const safeIndex = Math.min(activeQuestionIndex, Math.max(0, totalQuestions - 1));
  const currentQuestion = activeQuestions[safeIndex];

  // Handle answer change
  const handleAnswerChange = useCallback(
    (newVal: AnswerValue) => {
      setValidationError(null);
      setAnswers((prev) => {
        const next = { ...prev, [currentQuestion?.id]: newVal };
        // Clean out answers that may no longer be applicable if an earlier answer changed
        const cleaned = assessmentService.cleanIrrelevantAnswers(next);
        // Persist progress to session
        assessmentService.saveSession(cleaned, safeIndex);
        setHasSavedSession(true);
        return cleaned;
      });
    },
    [currentQuestion?.id, safeIndex]
  );

  // Start fresh assessment
  const handleStartFresh = () => {
    assessmentService.clearSession();
    setAnswers({});
    setActiveQuestionIndex(0);
    setHistoryStack([]);
    setHasSavedSession(false);
    setValidationError(null);
    setViewMode('assessment');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Resume saved assessment
  const handleResume = () => {
    setViewMode('assessment');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Handle Continue to next question or complete
  const handleContinue = () => {
    if (!currentQuestion) return;

    const isValid = assessmentService.isAnswerValid(currentQuestion, answers);
    if (!isValid) {
      if (currentQuestion.responseType === 'multiple_choice') {
        setValidationError(t('assessment.selectMultiError'));
      } else if (currentQuestion.responseType === 'rating_scale') {
        setValidationError(t('assessment.selectRatingError'));
      } else {
        setValidationError(t('assessment.selectOptionError'));
      }
      return;
    }

    setValidationError(null);

    // Save session snapshot
    assessmentService.saveSession(answers, safeIndex + 1);
    setHasSavedSession(true);

    if (safeIndex < totalQuestions - 1) {
      setHistoryStack((prev) => [...prev, safeIndex]);
      setActiveQuestionIndex(safeIndex + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      // Completed all applicable questions -> move to RAG Model Selection step
      assessmentService.saveSession(answers, totalQuestions, true);
      setViewMode('model_select');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Handle Back button
  const handleBack = () => {
    setValidationError(null);

    // If at Question 1, back navigation returns to the welcome screen
    if (safeIndex === 0 && historyStack.length === 0) {
      setViewMode('intro');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (historyStack.length > 0) {
      const prevIndex = historyStack[historyStack.length - 1];
      setHistoryStack((prev) => prev.slice(0, -1));
      setActiveQuestionIndex(prevIndex);
    } else {
      setActiveQuestionIndex(Math.max(0, safeIndex - 1));
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Handle Save and Exit
  const handleConfirmExit = () => {
    assessmentService.saveSession(answers, safeIndex);
    setShowExitModal(false);
    if (onNavigate) {
      onNavigate(ROUTES.HOME);
    }
  };

  // Handle Restart Assessment from results or dialog
  const handleRestart = () => {
    assessmentService.clearSession();
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.removeItem('skillsaathi_active_family_id');
    }
    setAnswers({});
    setActiveQuestionIndex(0);
    setHistoryStack([]);
    setHasSavedSession(false);
    setValidationError(null);
    if (onClearCourseContext) {
      onClearCourseContext();
    }
    setViewMode('intro');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Handle Change Answers from results
  const handleChangeAnswers = () => {
    setViewMode('assessment');
    setActiveQuestionIndex(0);
    setHistoryStack([]);
    setValidationError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isMr = language === 'mr';
  const isHi = language === 'hi';

  // 1. INTRO / GET STARTED VIEW
  if (viewMode === 'intro') {
    return (
      <div className="assessment-intro-wrapper" style={{ width: '100%', padding: '0.5rem 0' }}>
        <CareerGuidanceIntro
          hasSavedSession={hasSavedSession}
          savedQuestionNumber={safeIndex + 1}
          totalQuestions={totalQuestions}
          onStart={handleStartFresh}
          onResume={handleResume}
          onRestartNew={handleStartFresh}
          onNavigateToCounsellor={() => onNavigate && onNavigate(ROUTES.COUNSELLOR_SUPPORT)}
        />
      </div>
    );
  }

  // 2. RAG MODEL SELECTION VIEW (Between last question and results)
  if (viewMode === 'model_select') {
    return (
      <div
        className="model-selection-screen"
        style={{
          width: '100%',
          maxWidth: '760px',
          margin: '0 auto',
          padding: '1.5rem 1rem 4rem 1rem',
        }}
      >
        <div
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1.5px solid var(--color-primary-subtle, #bfdbfe)',
            borderRadius: '16px',
            padding: '2rem',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                backgroundColor: 'rgba(13, 148, 136, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-primary)',
              }}
            >
              <Cpu size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h1 style={{ fontSize: '1.375rem', fontWeight: 800, margin: 0, color: 'var(--color-text-primary)' }}>
                  Select Gemini Model for RAG Synthesis
                </h1>
                <Badge variant="primary" size="sm">
                  RAG Pipeline
                </Badge>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                Your assessment answers are saved. Choose the Google Gemini model you want to query for Retrieval-Augmented Generation (RAG).
              </p>
            </div>
          </div>

          {/* Model Options Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.875rem', margin: '1.5rem 0' }}>
            {AVAILABLE_GEMINI_MODELS.map((m) => {
              const isSelected = selectedRAGModel === m.id;
              return (
                <div
                  key={m.id}
                  onClick={() => {
                    setSelectedRAGModel(m.id);
                    if (typeof window !== 'undefined' && window.sessionStorage) {
                      window.sessionStorage.setItem('skillsaathi_rag_model', m.id);
                    }
                  }}
                  style={{
                    padding: '1rem 1.25rem',
                    borderRadius: '12px',
                    border: isSelected
                      ? '2px solid var(--color-primary)'
                      : '1.5px solid var(--color-border)',
                    backgroundColor: isSelected ? 'rgba(13, 148, 136, 0.04)' : 'var(--color-surface)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease-in-out',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
                    <input
                      type="radio"
                      name="gemini_rag_model"
                      value={m.id}
                      checked={isSelected}
                      onChange={() => {
                        setSelectedRAGModel(m.id);
                        if (typeof window !== 'undefined' && window.sessionStorage) {
                          window.sessionStorage.setItem('skillsaathi_rag_model', m.id);
                        }
                      }}
                      style={{ cursor: 'pointer', accentColor: 'var(--color-primary)' }}
                    />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <strong style={{ fontSize: '0.9375rem', color: 'var(--color-text-primary)' }}>
                          {m.name}
                        </strong>
                        <span
                          style={{
                            fontSize: '0.6875rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            backgroundColor: isSelected ? 'var(--color-primary)' : 'var(--color-neutral-subtle, #f1f5f9)',
                            color: isSelected ? '#ffffff' : 'var(--color-text-secondary)',
                          }}
                        >
                          {m.tag}
                        </span>
                      </div>
                      <p style={{ margin: '3px 0 0 0', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
                        {m.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Strict RAG Checkbox */}
          <div
            style={{
              padding: '0.875rem 1rem',
              borderRadius: '8px',
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.625rem',
              marginBottom: '1.5rem',
            }}
          >
            <input
              type="checkbox"
              id="strict_rag_toggle"
              checked={strictRAG}
              onChange={(e) => {
                const val = e.target.checked;
                setStrictRAG(val);
                if (typeof window !== 'undefined' && window.sessionStorage) {
                  window.sessionStorage.setItem('skillsaathi_strict_rag', val ? 'true' : 'false');
                }
              }}
              style={{ marginTop: '3px', cursor: 'pointer', accentColor: '#d97706' }}
            />
            <label htmlFor="strict_rag_toggle" style={{ cursor: 'pointer', fontSize: '0.8125rem', color: '#92400e', lineHeight: 1.45 }}>
              <strong>Strict RAG Mode (Recommended for RAG evaluation):</strong> If Gemini returns an error (e.g. invalid key, quota, or model issue), pause and display the exact error instead of silently proceeding on the deterministic engine.
            </label>
          </div>

          {/* Action Navigation */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <Button
              variant="outline"
              size="md"
              icon={<ArrowLeft size={16} />}
              onClick={() => {
                setActiveQuestionIndex(totalQuestions - 1);
                setViewMode('assessment');
              }}
            >
              Back to Questions
            </Button>

            <Button
              variant="primary"
              size="lg"
              icon={<ArrowRight size={18} />}
              iconPosition="right"
              onClick={() => {
                setViewMode('results');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              style={{ fontWeight: 700 }}
            >
              Launch RAG Family Consensus →
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // 3. RESULTS VIEW
  if (viewMode === 'results') {
    const resultsData = assessmentService.generateResults(answers);
    return (
      <div className="assessment-results-wrapper" style={{ width: '100%', paddingBottom: '3.5rem' }}>
        <AssessmentResults
          results={resultsData}
          language={language}
          answers={answers}
          familyId={assessmentService.loadSession()?.familyId}
          initialModel={selectedRAGModel}
          initialStrict={strictRAG}
          onExploreCourses={() => onNavigate && onNavigate(ROUTES.COURSES)}
          onViewCourseDetails={(cId) => {
            if (onViewCourseDetails) onViewCourseDetails(cId);
            else if (onNavigate) onNavigate(ROUTES.COURSE_DETAIL);
          }}
          onChangeAnswers={handleChangeAnswers}
          onRestart={handleRestart}
        />
      </div>
    );
  }

  // 3. ONE-QUESTION-AT-A-TIME DISCOVERY ASSESSMENT VIEW
  if (!currentQuestion) {
    return null;
  }

  return (
    <div
      className="assessment-screen"
      style={{
        width: '100%',
        maxWidth: '820px',
        margin: '0 auto',
        paddingBottom: '4rem',
      }}
    >
      {/* Assessment Header & Progress Bar */}
      <AssessmentProgress
        currentIndex={safeIndex}
        totalQuestions={totalQuestions}
        categoryLabel={currentQuestion.categoryLabel}
        language={language}
        onLanguageToggle={(lang) => changeLanguage(lang as SupportedLanguageCode)}
        onExit={() => setShowExitModal(true)}
      />

      {/* Main Question Card */}
      <main>
        <QuestionRenderer
          question={currentQuestion}
          currentAnswer={answers[currentQuestion.id]}
          language={language}
          onAnswerChange={handleAnswerChange}
          validationError={validationError}
        />
      </main>

      {/* Navigation Controls Bar */}
      <nav
        aria-label={isHi ? 'मूल्यांकन नेविगेशन' : isMr ? 'मूल्यांकन नेव्हिगेशन' : 'Assessment Navigation'}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: '1.75rem',
          gap: '1rem',
        }}
      >
        <Button
          variant="outline"
          size="md"
          icon={<ArrowLeft size={16} />}
          onClick={handleBack}
          style={{
            minHeight: '46px',
            padding: '0 1.25rem',
          }}
        >
          {safeIndex === 0 && historyStack.length === 0
            ? isHi ? 'शुरुआती पृष्ठ' : isMr ? 'प्रारंभिक पान' : 'Welcome Page'
            : t('assessment.btnBack')}
        </Button>

        <Button
          variant="primary"
          size="lg"
          icon={safeIndex === totalQuestions - 1 ? <CheckCircle2 size={18} /> : <ArrowRight size={18} />}
          iconPosition="right"
          onClick={handleContinue}
          style={{ minWidth: '170px', minHeight: '46px', fontWeight: 700 }}
        >
          {safeIndex === totalQuestions - 1
            ? t('assessment.btnFinish')
            : t('assessment.btnContinue')}
        </Button>
      </nav>

      {/* Exit Confirmation Dialog */}
      {showExitModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="exit-modal-title"
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
                  backgroundColor: 'var(--color-primary-subtle)',
                  color: 'var(--color-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <AlertCircle size={20} aria-hidden="true" />
              </div>
              <h2
                id="exit-modal-title"
                style={{
                  fontSize: '1.125rem',
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}
              >
                {t('assessment.exitModalTitle')}
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
              {t('assessment.exitModalDesc')}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Button
                variant="outline"
                size="md"
                onClick={() => setShowExitModal(false)}
                style={{ minHeight: '44px' }}
              >
                {isHi ? 'सत्र जारी रखें' : isMr ? 'सत्र सुरू ठेवा' : 'Continue Assessment'}
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={handleConfirmExit}
                style={{ minHeight: '44px' }}
              >
                {t('assessment.btnSaveExit')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AssessmentScreen;
