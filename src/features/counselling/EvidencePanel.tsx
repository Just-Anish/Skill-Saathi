import React from 'react';
import {
  ShieldCheck,
  Award,
  Clock,
  Briefcase,
  TrendingUp,
  MapPin,
  Sparkles,
  Info,
  BookOpen,
  AlertTriangle,
} from 'lucide-react';
import { Course } from '../../types/course';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { CounsellingLanguage } from './counsellingContent';
import { courseService, EDUCATION_LEVEL_LABELS } from '../../services/courses/courseService';
import { ConsensusRecommendation } from '../../services/api/familyConsensusService';

export interface EvidencePanelProps {
  course?: Course | null;
  language: CounsellingLanguage;
  onExploreCourses: () => void;
  onViewCourseDetails?: (courseId: string) => void;
  /** RAG-sourced pathway recommendations from POST /families/{id}/analyze.
   *  When provided, each recommendation's missing_evidence_flags are surfaced
   *  as amber warning badges beneath the student / parent rationale text. */
  consensusRecommendations?: ConsensusRecommendation[];
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  course,
  language,
  onExploreCourses,
  onViewCourseDetails,
  consensusRecommendations,
}) => {
  const isMr = language === 'mr';
  const isHi = language === 'hi';

  /** Renders amber RAG data-gap badges for a single recommendation's missing_evidence_flags. */
  const MissingEvidenceBadges: React.FC<{ flags: string[] | undefined }> = ({ flags }) => {
    if (!flags || flags.length === 0) return null;
    return (
      <div
        style={{
          marginTop: '0.625rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.3rem',
        }}
        aria-label="RAG data gaps — information not yet verified from official sources"
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            fontSize: '0.6875rem',
            fontWeight: 700,
            color: '#92400e',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          <AlertTriangle size={11} aria-hidden="true" style={{ color: '#d97706', flexShrink: 0 }} />
          <span>
            {isHi
              ? 'अनुपलब्ध / असत्यापित डेटा:'
              : isMr
              ? 'पडताळणी न झालेली माहिती:'
              : 'Unverified Data Gaps:'}
          </span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3125rem' }}>
          {flags.map((flag, fIdx) => (
            <span
              key={fIdx}
              style={{
                display: 'inline-block',
                fontSize: '0.6875rem',
                lineHeight: 1.4,
                backgroundColor: '#fffbeb',
                color: '#92400e',
                border: '1px solid #fde68a',
                borderRadius: '4px',
                padding: '2px 7px',
                fontWeight: 500,
              }}
              title={flag}
            >
              {flag}
            </span>
          ))}
        </div>
      </div>
    );
  };

  if (!course) {
    return (
      <aside
        className="evidence-panel empty-panel"
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: '1.5rem',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Info size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {isHi ? 'कोर्स साक्ष्य एवं सत्यापन' : isMr ? 'कोर्स पुरावे आणि पडताळणी' : 'Course Evidence & Verification'}
          </h2>
        </div>

        <p style={{ fontSize: '0.84375rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
          {isHi
            ? 'वर्तमान में इस सत्र से कोई विशिष्ट कोर्स नहीं जुड़ा है। आप सामान्य करियर प्रश्न पूछ सकते हैं, या आधिकारिक NSQF प्रमाण पत्र, वेतन दिशानिर्देश और पाठ्यक्रम सत्यापित करने के लिए कोर्स एक्सप्लोरर से एक वोकेशनल कोर्स चुन सकते हैं।'
            : isMr
            ? 'सध्या कोणताही विशिष्ट कोर्स निवडलेला नाही. विशिष्ट कोर्सचे प्रत्यक्ष कौशल्य, पगार आणि NCVET मान्यता पडताळण्यासाठी एक्सप्लोररमधून कोर्स निवडा.'
            : 'No course is currently pinned to this session. You can ask general career questions, or select a specific vocational course to verify official NSQF credentials, wage guidelines, and curricula.'}
        </p>

        <div
          style={{
            backgroundColor: 'var(--color-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
            border: '1px solid var(--color-border-subtle)',
            fontSize: '0.8125rem',
            color: 'var(--color-text-secondary)',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.25rem' }}>
            {isHi ? 'महाराष्ट्र वोकेशनल मुख्य बिंदु:' : isMr ? 'महाराष्ट्र कौशल्यांची ठळक वैशिष्ट्ये' : 'Maharashtra Vocational Highlights:'}
          </div>
          <ul style={{ listStyle: 'disc', paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <li>{isHi ? 'पुणे व छत्रपति संभाजीनगर में ईवी और सीएनसी हब' : isMr ? 'पुणे व संभाजीनगर (औरंगाबाद) मध्ये ईव्ही व सीएनसी हब' : 'EV & CNC hubs in Pune & Chhatrapati Sambhajinagar'}</li>
            <li>{isHi ? 'नासिक व पश्चिमी महाराष्ट्र में सौर ऊर्जा और एग्री-ड्रोन हब' : isMr ? 'नाशिक व पश्चिम महाराष्ट्रात सौरऊर्जा व ॲग्री-ड्रोन' : 'Solar & Agri-Drone hubs in Nashik & Western Maharashtra'}</li>
            <li>{isHi ? 'मुंबई उपनगर व नागपुर में स्वास्थ्य सेवा जीडीए ट्रैक्स' : isMr ? 'मुंबई उपनगर व नागपूरमध्ये आरोग्य सेवा तंत्रज्ञ' : 'Healthcare GDA tracks in Mumbai & Nagpur'}</li>
          </ul>
        </div>

        <Button variant="outline" size="sm" icon={<BookOpen size={15} />} onClick={onExploreCourses}>
          {isHi ? 'कोर्स चुनें (Browse Courses)' : isMr ? 'कोर्स निवडा (Browse Courses)' : 'Select a Course from Explorer'}
        </Button>

        {/* ── RAG Consensus Recommendations (no course pinned) ── */}
        {consensusRecommendations && consensusRecommendations.length > 0 && (
          <div
            style={{
              borderTop: '1px solid var(--color-border-subtle)',
              paddingTop: '0.875rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div
              style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              {isHi ? 'RAG मार्ग सुझाव' : isMr ? 'RAG मार्ग शिफारशी' : 'RAG Pathway Recommendations'}
            </div>
            {consensusRecommendations.map((rec, idx) => (
              <div
                key={rec.course_id || idx}
                style={{
                  backgroundColor: 'var(--color-bg)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.625rem 0.75rem',
                }}
              >
                <div
                  style={{
                    fontSize: '0.8125rem',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    marginBottom: '0.25rem',
                  }}
                >
                  {rec.course_title}
                </div>
                {rec.student_rationale && (
                  <p
                    style={{
                      margin: '0 0 0.2rem 0',
                      fontSize: '0.78125rem',
                      color: 'var(--color-text-secondary)',
                      lineHeight: 1.4,
                    }}
                  >
                    {rec.student_rationale}
                  </p>
                )}
                <MissingEvidenceBadges flags={rec.missing_evidence_flags} />
              </div>
            ))}
          </div>
        )}
      </aside>
    );
  }

  const streamMeta = courseService.getStreamMeta(course.stream);

  return (
    <aside
      className="evidence-panel active-course-panel"
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.5rem',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}
      aria-label="Course evidence and factual verification"
    >
      {/* Panel Title & Status Tag */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
          <ShieldCheck size={18} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
          <h2 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {isHi ? 'सत्यापित साक्ष्य पैनल' : isMr ? 'कोर्स पुरावे आणि पडताळणी' : 'Verified Evidence Panel'}
          </h2>
        </div>

        <Badge variant="primary" size="sm">
          {streamMeta.shortLabel}
        </Badge>
      </div>

      {/* Course Title & Core Specs */}
      <div>
        <h3 style={{ fontSize: '1.0625rem', fontWeight: 700, color: 'var(--color-text-primary)', lineHeight: 1.35, marginBottom: '0.25rem' }}>
          {course.title}
        </h3>
        <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginBottom: '0.75rem' }}>
          {course.provider}
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginBottom: '0.75rem' }}>
          {course.nsqfLevel && (
            <Badge variant="neutral" size="sm" icon={<Award size={12} />}>
              NSQF Level {course.nsqfLevel}
            </Badge>
          )}

          {course.certificationBody && (
            <Badge variant="secondary" size="sm">
              {course.certificationBody}
            </Badge>
          )}

          <Badge variant="neutral" size="sm" icon={<Clock size={12} />}>
            {course.durationMonths} Mo ({course.trainingMode})
          </Badge>
        </div>

        <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <MapPin size={13} aria-hidden="true" />
          <span>{course.location}</span>
        </div>
      </div>

      {/* Target Job Role & Salary Note */}
      <div
        style={{
          backgroundColor: 'var(--color-bg)',
          borderRadius: 'var(--radius-md)',
          padding: '0.875rem',
          border: '1px solid var(--color-border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
          <Briefcase size={13} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          <span>{isHi ? 'संभावित नौकरी पद:' : isMr ? 'संभाव्य नोकरीचे पद:' : 'Target Entry Designation:'}</span>
        </div>
        <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--color-text-primary)', marginBottom: '0.5rem' }}>
          {course.careerOutcome.roleTitle}
        </div>

        {/* Starting Salary with Explicit Illustrative Label */}
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
          {isHi ? 'शुरुआती वेतन (अनुमानित):' : isMr ? 'सुरुवातीचा पगार (अंदाजे):' : 'Illustrative Initial Guideline:'}
        </div>
        <div style={{ fontSize: '1.0625rem', fontWeight: 800, color: 'var(--color-primary)' }}>
          ₹{course.careerOutcome.averageStartingSalaryInr.toLocaleString()} / mo
        </div>
        <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontStyle: 'italic' }}>
          {isHi
            ? '*प्रोटोटाइप सर्वेक्षण बेंचमार्क। कोई कानूनी रोजगार गारंटी नहीं।'
            : isMr
            ? '*प्रात्यक्षिक पाहणीवर आधारित अंदाज, कोणतीही कायदेशीर हमी नाही.'
            : '*Prototype survey benchmark. Not a contractual employment guarantee.'}
        </div>
      </div>

      {/* Practical Competencies Acquired */}
      {course.skillsAcquired && course.skillsAcquired.length > 0 && (
        <div>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '0.375rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Sparkles size={13} style={{ color: 'var(--color-secondary)' }} aria-hidden="true" />
            <span>{isHi ? 'सत्यापित व्यावहारिक कौशल:' : isMr ? 'शिकवली जाणारी प्रत्यक्ष कौशल्ये:' : 'Certified Skills Covered:'}</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
            {course.skillsAcquired.slice(0, 4).map((skill) => (
              <span
                key={skill}
                style={{
                  fontSize: '0.75rem',
                  backgroundColor: 'var(--color-surface-muted)',
                  color: 'var(--color-text-secondary)',
                  padding: '2px 7px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border-subtle)',
                }}
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* NEP 2020 Academic Progression */}
      {course.careerProgression && (
        <div
          style={{
            backgroundColor: 'var(--color-secondary-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem',
            border: '1px solid #99f6e4',
            fontSize: '0.78125rem',
            color: 'var(--color-secondary)',
            lineHeight: 1.45,
          }}
        >
          <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.25rem', marginBottom: '0.25rem' }}>
            <TrendingUp size={14} aria-hidden="true" />
            <span>{isHi ? 'NEP 2020 क्रेडिट सीढ़ी:' : isMr ? 'NEP 2020 पदवी प्रगती' : 'NEP 2020 Credit Ladder:'}</span>
          </div>
          <span>{course.careerProgression}</span>
        </div>
      )}

      {/* Eligibility */}
      <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-secondary)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '0.75rem' }}>
        <strong>{isHi ? 'न्यूनतम योग्यता:' : isMr ? 'किमान पात्रता:' : 'Min Eligibility:'}</strong>{' '}
        {EDUCATION_LEVEL_LABELS[course.eligibility.minEducation] || course.eligibility.minEducation} (Age {course.eligibility.minAge}+)
      </div>

      {/* Button to View Full Course Details */}
      {onViewCourseDetails && (
        <Button variant="outline" size="sm" onClick={() => onViewCourseDetails(course.id)}>
          {isHi ? 'पूरा कोर्स विवरण खोलें' : isMr ? 'संपूर्ण कोर्स तपशील उघडा' : 'Open Full Course Page'}
        </Button>
      )}

      {/* ── RAG Consensus Pathway Recommendations ─────────────────────────
          Rendered when consensusRecommendations are provided from the
          POST /families/{id}/analyze RAG pipeline. Shows missing_evidence_flags
          as amber badges beneath each recommendation's rationale to surface
          data gaps identified during retrieval-augmented generation.
      ─────────────────────────────────────────────────────────────────── */}
      {consensusRecommendations && consensusRecommendations.length > 0 && (
        <div
          style={{
            borderTop: '1px solid var(--color-border-subtle)',
            paddingTop: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.875rem',
          }}
        >
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
            }}
          >
            <Sparkles size={12} aria-hidden="true" style={{ color: 'var(--color-primary)' }} />
            <span>
              {isHi
                ? 'RAG-आधारित पाठ्यक्रम सुझाव'
                : isMr
                ? 'RAG-आधारित मार्ग शिफारशी'
                : 'RAG-Grounded Pathway Recommendations'}
            </span>
          </div>

          {consensusRecommendations.map((rec, idx) => (
            <div
              key={rec.course_id || idx}
              style={{
                backgroundColor: 'var(--color-bg)',
                border: '1px solid var(--color-border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem 0.875rem',
              }}
            >
              {/* Recommendation title + fit score */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                  marginBottom: '0.375rem',
                }}
              >
                <span
                  style={{
                    fontSize: '0.8125rem',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    lineHeight: 1.35,
                    flex: 1,
                  }}
                >
                  {rec.course_title}
                </span>
                {rec.fit_score !== undefined && (
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      color: 'var(--color-primary)',
                      backgroundColor: 'var(--color-primary-subtle, #eff6ff)',
                      border: '1px solid var(--color-primary-subtle, #bfdbfe)',
                      borderRadius: '4px',
                      padding: '1px 6px',
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
                    }}
                  >
                    {rec.fit_score}/100
                  </span>
                )}
              </div>

              {/* Student rationale */}
              {rec.student_rationale && (
                <p
                  style={{
                    margin: '0 0 0.25rem 0',
                    fontSize: '0.78125rem',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.45,
                  }}
                >
                  {rec.student_rationale}
                </p>
              )}

              {/* Parent rationale */}
              {rec.parent_rationale && (
                <p
                  style={{
                    margin: '0 0 0.25rem 0',
                    fontSize: '0.78125rem',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.45,
                    fontStyle: 'italic',
                  }}
                >
                  {rec.parent_rationale}
                </p>
              )}

              {/* ── RAG Data-Gap Flags ──────────────────────────────────
                  Amber badge list mapping over missing_evidence_flags[].
                  Renders nothing when the array is empty or undefined.
              ──────────────────────────────────────────────────────── */}
              <MissingEvidenceBadges flags={rec.missing_evidence_flags} />
            </div>
          ))}
        </div>
      )}
    </aside>
  );
};

export default EvidencePanel;
