import React, { useState } from 'react';
import { Award, CheckCircle } from 'lucide-react';

export interface NCrFCreditLadderProps {
  currentLevel?: number;
  highlightStream?: string;
}

export const NCrFCreditLadder: React.FC<NCrFCreditLadderProps> = ({
  currentLevel = 4,
  highlightStream = 'Technical Vocational Trade'
}) => {
  const [activeStage, setActiveStage] = useState<number>(1);

  const stages = [
    {
      step: 1,
      nsqfLevel: 4,
      title: 'NSQF Level 4: ITI / CTS Technician',
      subtitle: 'Hands-on Craftsman Training (1–2 Years)',
      credits: '40 NCrF Credits / Year',
      formalEquiv: '12th Standard Vocational Equivalent',
      salary: '₹18,000 – ₹24,000 / month',
      outcome: 'Direct employment as Certified Technician, Wireman, or NAPS Apprentice.',
      parentAssurance: 'The student begins earning immediately while gaining official CTS national certification.',
      highlights: [
        'Over 300+ hours of practical workshop & laboratory training',
        'Eligible for government apprentice stipends under NAPS (₹8,000–₹12,000/mo)',
        'Zero academic years wasted on passive rote memorization'
      ]
    },
    {
      step: 2,
      nsqfLevel: 5,
      title: 'NSQF Level 5: Polytechnic Diploma (Lateral Entry)',
      subtitle: 'Direct Admission into 2nd Year Diploma (2 Years)',
      credits: '80 NCrF Credits Total',
      formalEquiv: 'State Board Technical Education Diploma Engineer',
      salary: '₹28,000 – ₹42,000 / month',
      outcome: 'Junior Engineer (JE), Technical Supervisor, or Industrial Site Inspector.',
      parentAssurance: 'No entrance barrier: ITI holders skip 1st year diploma completely via official AICTE lateral quota!',
      highlights: [
        'Direct 2nd-year admission (saves 1 full academic year)',
        'Qualifies for State Electricity Boards, Railways, and OEM Supervisor posts',
        'Can be pursued part-time or through evening classes while working'
      ]
    },
    {
      step: 3,
      nsqfLevel: 6,
      title: 'NSQF Level 6 & 7: Bachelor of Vocational Studies (B.Voc) / B.Tech',
      subtitle: 'Direct Lateral Entry into Engineering / B.Voc Degree (3 Years)',
      credits: '120+ NCrF Credits (Degree Status)',
      formalEquiv: 'UGC & AICTE Recognized University Bachelor’s Degree',
      salary: '₹45,000 – ₹75,000 / month',
      outcome: 'Senior Engineer, Operations Manager, or Technical Officer.',
      parentAssurance: 'Carries 100% equivalence to traditional BA/B.Sc/B.Com for UPSC, SSC, Banking, and all Central/State Govt exams.',
      highlights: [
        'Full university degree with 4+ years of real industrial workshop experience',
        'Eligible for all Central/State civil service & officer examinations',
        'Highest private employer hiring preference over pure theoretical graduates'
      ]
    }
  ];

  return (
    <div
      className="ncrf-credit-ladder"
      style={{
        backgroundColor: 'var(--color-surface, #ffffff)',
        border: '1px solid var(--color-border, #e2e8f0)',
        borderRadius: '12px',
        padding: '1.5rem',
        marginTop: '1.5rem',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <Award size={20} color="var(--color-primary, #2563eb)" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0, color: 'var(--color-text-main, #0f172a)' }}>
              National Credit Framework (NCrF) Degree Progression Ladder
            </h3>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted, #64748b)', margin: 0 }}>
            Proving that vocational certificates in <strong>{highlightStream}</strong> are not dead-ends and lead to formal degrees.
          </p>
        </div>
        <span
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: '#166534',
            backgroundColor: '#dcfce7',
            padding: '4px 10px',
            borderRadius: '999px',
            border: '1px solid #bbf7d0',
          }}
        >
          NSQF Level {currentLevel} • NEP 2020 Aligned
        </span>
      </div>

      {/* 3 Step Interactive Progress Pills */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '0.75rem',
          marginBottom: '1.5rem',
        }}
      >
        {stages.map((stage) => {
          const isActive = activeStage === stage.step;
          return (
            <button
              key={stage.step}
              onClick={() => setActiveStage(stage.step)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '0.875rem 1rem',
                borderRadius: '8px',
                border: isActive ? '2px solid var(--color-primary, #2563eb)' : '1px solid #e2e8f0',
                backgroundColor: isActive ? '#eff6ff' : '#f8fafc',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: isActive ? '#2563eb' : '#64748b' }}>
                  STEP 0{stage.step}
                </span>
                <span
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    backgroundColor: isActive ? '#dbeafe' : '#e2e8f0',
                    color: isActive ? '#1e40af' : '#475569',
                    padding: '2px 6px',
                    borderRadius: '4px',
                  }}
                >
                  NSQF {stage.nsqfLevel}
                </span>
              </div>
              <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#0f172a', lineHeight: 1.3 }}>
                {stage.step === 1 ? 'Craftsman (ITI)' : stage.step === 2 ? 'Diploma Engineer' : 'Bachelor Degree'}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                {stage.credits}
              </span>
            </button>
          );
        })}
      </div>

      {/* Selected Stage Detail Card */}
      {(() => {
        const s = stages[activeStage - 1];
        return (
          <div
            style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>
                  {s.title}
                </h4>
                <div style={{ fontSize: '0.8125rem', color: '#64748b' }}>{s.subtitle}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Expected Compensation</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#16a34a' }}>{s.salary}</div>
              </div>
            </div>

            {/* Parent Reassurance Callout */}
            <div
              style={{
                backgroundColor: '#fef3c7',
                borderLeft: '4px solid #f59e0b',
                padding: '0.75rem 1rem',
                borderRadius: '4px',
                marginBottom: '1rem',
                fontSize: '0.8125rem',
                color: '#92400e',
              }}
            >
              <strong>Reassurance for Parents:</strong> {s.parentAssurance}
            </div>

            {/* Highlights */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.5rem' }}>
              {s.highlights.map((h, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8125rem', color: '#334155' }}>
                  <CheckCircle size={15} color="#16a34a" style={{ flexShrink: 0 }} />
                  <span>{h}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
};
