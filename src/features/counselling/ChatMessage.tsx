import React from 'react';
import { User, Users, GraduationCap, ShieldCheck, Award, Sparkles } from 'lucide-react';
import { CounsellingMessage } from '../../types/counselling';

export interface ChatMessageProps {
  message: CounsellingMessage;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isCounsellor = message.senderRole === 'counsellor' || message.senderRole === 'system';
  const isParent = message.senderRole === 'parent';

  // Agent persona detection
  const isStudentAdvocate = message.senderName === 'StudentAdvocate' || message.senderName.includes('Student Advocate');
  const isParentLiaison = message.senderName === 'ParentLiaison' || message.senderName.includes('Parent Liaison');
  const isFactChecker = message.senderName === 'FactChecker' || message.senderName.includes('Fact-Checker');
  const isMediator = message.senderName === 'ConsensusMediator' || message.senderName.includes('Mediator');

  const isMultiAgent = isStudentAdvocate || isParentLiaison || isFactChecker || isMediator;

  // Determine avatar background color
  const getAvatarBg = () => {
    if (isStudentAdvocate) return '#2563eb'; // Blue
    if (isParentLiaison) return '#d97706'; // Amber
    if (isFactChecker) return '#059669'; // Emerald
    if (isMediator) return '#7c3aed'; // Purple
    if (isCounsellor) return 'var(--color-primary, #2563eb)';
    if (isParent) return 'var(--color-secondary, #475569)';
    return 'var(--color-info, #0284c7)';
  };

  // Determine badge styling
  const getAgentBadge = () => {
    if (isStudentAdvocate) {
      return (
        <span style={{ fontSize: '10px', backgroundColor: '#dbeafe', color: '#1e40af', borderRadius: '9999px', padding: '1px 6px', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
          <Sparkles size={10} /> Student Advocate
        </span>
      );
    }
    if (isParentLiaison) {
      return (
        <span style={{ fontSize: '10px', backgroundColor: '#fef3c7', color: '#92400e', borderRadius: '9999px', padding: '1px 6px', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
          <Users size={10} /> Parent Liaison
        </span>
      );
    }
    if (isFactChecker) {
      return (
        <span style={{ fontSize: '10px', backgroundColor: '#dcfce7', color: '#166534', borderRadius: '9999px', padding: '1px 6px', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
          <ShieldCheck size={10} /> Fact-Checker & Tools
        </span>
      );
    }
    if (isMediator) {
      return (
        <span style={{ fontSize: '10px', backgroundColor: '#f3e8ff', color: '#6b21a8', borderRadius: '9999px', padding: '1px 6px', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
          <Award size={10} /> Consensus Mediator
        </span>
      );
    }
    if (isCounsellor) {
      return (
        <span style={{ fontSize: '10px', backgroundColor: 'var(--color-success-bg, #dcfce7)', color: 'var(--color-success-text, #166534)', borderRadius: '9999px', padding: '1px 6px', display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
          <ShieldCheck size={10} /> Verified Guide
        </span>
      );
    }
    return null;
  };

  // Format simple markdown-like bold (**text**) and bullet points
  const formatContent = (text: string) => {
    const lines = text.split('\n');

    return lines.map((line, idx) => {
      if (line.trim().startsWith('|')) {
        return (
          <div
            key={idx}
            style={{
              fontFamily: 'monospace',
              fontSize: '0.8125rem',
              overflowX: 'auto',
              whiteSpace: 'pre',
              backgroundColor: 'rgba(0, 0, 0, 0.03)',
              padding: '2px 4px',
              borderRadius: '3px',
              margin: '2px 0',
            }}
          >
            {line}
          </div>
        );
      }

      const isBullet = line.trim().startsWith('- ') || line.trim().startsWith('* ') || /^[0-9]+\.\s/.test(line.trim());
      const cleanLine = isBullet ? line.trim().replace(/^([0-9]+\.\s|[-*]\s)/, '') : line;

      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const renderedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (isBullet) {
        return (
          <div key={idx} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ color: getAvatarBg(), fontWeight: 700 }}>•</span>
            <span style={{ flex: 1 }}>{renderedParts}</span>
          </div>
        );
      }

      return line.trim() === '' ? (
        <div key={idx} style={{ height: '0.5rem' }} />
      ) : (
        <p key={idx} style={{ marginBottom: idx === lines.length - 1 ? 0 : '0.5rem' }}>
          {renderedParts}
        </p>
      );
    });
  };

  const isLeftAligned = isCounsellor || isMultiAgent;

  return (
    <div
      className={`chat-message-row ${isLeftAligned ? 'counsellor-row' : 'user-row'}`}
      style={{
        display: 'flex',
        flexDirection: isLeftAligned ? 'row' : 'row-reverse',
        gap: '0.75rem',
        alignItems: 'flex-start',
        marginBottom: '1rem',
      }}
    >
      {/* Sender Avatar */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          backgroundColor: getAvatarBg(),
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          marginTop: '2px',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        }}
        aria-hidden="true"
      >
        {isStudentAdvocate ? (
          <GraduationCap size={18} />
        ) : isParentLiaison ? (
          <Users size={17} />
        ) : isFactChecker ? (
          <ShieldCheck size={18} />
        ) : isMediator ? (
          <Award size={18} />
        ) : isCounsellor ? (
          <GraduationCap size={18} />
        ) : isParent ? (
          <Users size={17} />
        ) : (
          <User size={17} />
        )}
      </div>

      {/* Message Card Bubble */}
      <div
        style={{
          maxWidth: '82%',
          backgroundColor: isLeftAligned ? '#ffffff' : 'var(--color-primary-subtle, #eff6ff)',
          color: 'var(--color-text-primary, #0f172a)',
          border: `1px solid ${isLeftAligned ? '#e2e8f0' : '#bfdbfe'}`,
          borderLeft: isMultiAgent ? `4px solid ${getAvatarBg()}` : undefined,
          borderRadius: isLeftAligned ? '0 14px 14px 14px' : '14px 0 14px 14px',
          padding: '0.875rem 1.125rem',
          boxShadow: isLeftAligned ? '0 1px 3px rgba(0, 0, 0, 0.05)' : 'none',
        }}
      >
        {/* Sender Name & Timestamp Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
            marginBottom: '0.375rem',
            borderBottom: '1px solid #f1f5f9',
            paddingBottom: '0.25rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: getAvatarBg() }}>
              {message.senderName}
            </span>
            {getAgentBadge()}
          </div>

          <span style={{ fontSize: '0.6875rem', color: '#64748b' }}>
            {message.timestamp}
          </span>
        </div>

        {/* Message Content */}
        <div style={{ fontSize: '0.90625rem', lineHeight: 1.55 }}>
          {formatContent(message.content)}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
