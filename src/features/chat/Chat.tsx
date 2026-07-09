import React, { useState, useRef, useEffect } from 'react';
import { useChatStream, StreamPhase } from '../../hooks/useChatStream';
import { Bot, User, Loader2, Brain, Wrench, ScanSearch, ArrowUp } from 'lucide-react';
import { cn } from '../../lib/utils';

/* ── Suggestion prompts ───────────────────────────────────────────────── */
const SUGGESTIONS = [
  'Met Dr. Sharma at City Hospital, discussed CardioX for 30 mins, positive sentiment.',
  'Search for Dr. Patel in cardiology.',
  'Generate a follow-up recommendation for the last interaction.',
];

/* ── Phase config ─────────────────────────────────────────────────────── */
const PHASE_CONFIG: Record<
  Exclude<StreamPhase, 'idle' | 'streaming'>,
  { icon: React.ElementType; label: string; color: string; bg: string; border: string }
> = {
  thinking:   { icon: Brain,      label: 'Thinking',          color: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  tool:       { icon: Wrench,     label: 'Running tool',      color: '#b45309', bg: '#fffbeb', border: '#fde68a' },
  extracting: { icon: ScanSearch, label: 'Extracting fields', color: '#1d4ed8', bg: '#eff6ff', border: '#bfdbfe' },
};

const TOOL_LABELS: Record<string, string> = {
  log_interaction:          'Extracting fields',
  edit_interaction:         'Applying edits',
  search_hcp:               'Searching records',
  meeting_summary:          'Generating summary',
  follow_up_recommendation: 'Building follow-up',
};

/* ── Extraction progress ──────────────────────────────────────────────── */
const STEPS = ['HCP & Hospital', 'Meeting Details', 'Products', 'Outcomes'];

const ExtractionProgress: React.FC = () => {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % STEPS.length), 850);
    return () => clearInterval(id);
  }, []);
  return (
    <div style={{
      margin: '0 12px 8px',
      padding: '10px 12px',
      borderRadius: 8,
      border: '1px solid #bfdbfe',
      background: '#eff6ff',
    }}>
      <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#1d4ed8', marginBottom: 8 }}>
        Extracting interaction data
      </p>
      <div style={{ display: 'flex', gap: 4 }}>
        {STEPS.map((label, i) => (
          <div key={label} style={{ flex: 1 }}>
            <div style={{
              height: 2, borderRadius: 99,
              background: i <= step ? '#3b82f6' : '#bfdbfe',
              transition: 'background .4s',
            }} />
            <p style={{
              fontSize: 9, marginTop: 3, fontWeight: 500,
              color: i === step ? '#1d4ed8' : '#93c5fd',
              transition: 'color .4s',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {label}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ── Typing indicator ─────────────────────────────────────────────────── */
const TypingIndicator: React.FC = () => (
  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
    <div style={{
      width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
      background: 'var(--surface-3)', border: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <Bot style={{ width: 13, height: 13, color: 'var(--brand)' }} />
    </div>
    <div style={{
      display: 'flex', alignItems: 'center', gap: 3,
      padding: '10px 14px',
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: '12px 12px 12px 3px',
      boxShadow: 'var(--shadow-xs)',
    }}>
      <span className="dot-1" style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--t4)', display: 'inline-block' }} />
      <span className="dot-2" style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--t4)', display: 'inline-block' }} />
      <span className="dot-3" style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--t4)', display: 'inline-block' }} />
    </div>
  </div>
);

/* ── Message timestamp ────────────────────────────────────────────────── */
const MsgTime: React.FC<{ ts?: number }> = ({ ts }) => {
  if (!ts) return null;
  return (
    <span style={{ fontSize: 10, color: 'var(--t4)', marginTop: 3, display: 'block' }}>
      {new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
    </span>
  );
};

/* ── Main component ───────────────────────────────────────────────────── */
const Chat: React.FC = () => {
  const { messages, isLoading, phase, activeTool, error, sendMessage } = useChatStream();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, phase]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  };

  const showSuggestions = messages.length === 1 && !isLoading;
  const phaseInfo = phase !== 'idle' && phase !== 'streaming' ? PHASE_CONFIG[phase] : null;
  const statusLabel = phaseInfo
    ? (activeTool && TOOL_LABELS[activeTool] ? TOOL_LABELS[activeTool] : phaseInfo.label)
    : null;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0,
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      boxShadow: 'var(--shadow-sm)',
      overflow: 'hidden',
    }}>

      {/* ── Header ── */}
      <div style={{
        flexShrink: 0,
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
      }}>
        {/* Avatar */}
        <div style={{
          width: 28, height: 28, borderRadius: 8, flexShrink: 0,
          background: 'var(--brand)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Bot style={{ width: 14, height: 14, color: 'white' }} />
        </div>

        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)', margin: 0, letterSpacing: '-0.01em' }}>
            AI Assistant
          </p>
          <p style={{ fontSize: 11, color: 'var(--t4)', margin: '1px 0 0', fontWeight: 400 }}>
            LangGraph · Groq · llama-3.1-8b
          </p>
        </div>

        <div style={{ marginLeft: 'auto' }}>
          {phaseInfo && statusLabel ? (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              padding: '3px 8px', borderRadius: 99,
              border: `1px solid ${phaseInfo.border}`,
              background: phaseInfo.bg,
              fontSize: 11, fontWeight: 500, color: phaseInfo.color,
            }}>
              <phaseInfo.icon style={{ width: 10, height: 10 }} />
              {statusLabel}
            </span>
          ) : (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              padding: '3px 8px', borderRadius: 99,
              border: '1px solid var(--border)',
              background: 'var(--surface-3)',
              fontSize: 11, fontWeight: 400, color: 'var(--t4)',
            }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              Ready
            </span>
          )}
        </div>
      </div>

      {/* ── Messages ── */}
      <div style={{
        flex: 1, overflowY: 'auto',
        padding: '16px 16px 8px',
        display: 'flex', flexDirection: 'column', gap: 12,
        background: 'var(--surface-2)',
      }}>

        {messages.map((msg) => (
          <div
            key={msg.id}
            className="slide-up"
            style={{
              display: 'flex',
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              alignItems: 'flex-end',
              gap: 8,
            }}
          >
            {/* Avatar */}
            <div style={{
              width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
              background: msg.role === 'user' ? 'var(--surface-4)' : 'var(--surface-3)',
              border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 2,
            }}>
              {msg.role === 'user'
                ? <User style={{ width: 12, height: 12, color: 'var(--t3)' }} />
                : <Bot style={{ width: 12, height: 12, color: 'var(--brand)' }} />}
            </div>

            <div style={{
              display: 'flex', flexDirection: 'column',
              alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '82%',
            }}>
              <div style={{
                padding: '9px 13px',
                borderRadius: msg.role === 'user' ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
                fontSize: 13, lineHeight: 1.55,
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                ...(msg.role === 'user' ? {
                  background: 'var(--brand)',
                  color: 'white',
                  boxShadow: '0 1px 3px rgba(91,91,214,.25)',
                } : {
                  background: 'var(--surface)',
                  color: 'var(--t2)',
                  border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow-xs)',
                }),
              }}>
                {msg.content}
                {msg.isStreaming && phase === 'streaming' && (
                  <span className="cursor-blink" style={{
                    display: 'inline-block', width: 2, height: 13,
                    background: 'currentColor', marginLeft: 2,
                    verticalAlign: 'middle', borderRadius: 1, opacity: .7,
                  }} />
                )}
              </div>
              <MsgTime ts={(msg as any).timestamp} />
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {phase === 'thinking' && <TypingIndicator />}

        {/* Suggestions */}
        {showSuggestions && (
          <div className="fade-in" style={{ paddingTop: 4 }}>
            <p style={{
              fontSize: 10, fontWeight: 600, letterSpacing: '0.06em',
              textTransform: 'uppercase', color: 'var(--t4)',
              marginBottom: 8,
            }}>
              Try an example
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => { setInput(s); textareaRef.current?.focus(); }}
                  style={{
                    textAlign: 'left', padding: '8px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    fontSize: 12, color: 'var(--t3)',
                    cursor: 'pointer', lineHeight: 1.5,
                    transition: 'all .1s',
                    boxShadow: 'var(--shadow-xs)',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--brand)';
                    (e.currentTarget as HTMLButtonElement).style.color = 'var(--brand)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                    (e.currentTarget as HTMLButtonElement).style.color = 'var(--t3)';
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Extraction progress ── */}
      {phase === 'extracting' && <ExtractionProgress />}

      {/* ── Error ── */}
      {error && (
        <div style={{
          margin: '0 12px 8px',
          padding: '8px 12px',
          borderRadius: 6,
          border: '1px solid var(--red-border)',
          background: 'var(--red-bg)',
          fontSize: 12, color: 'var(--red)',
        }}>
          {error}
        </div>
      )}

      {/* ── Input ── */}
      <div style={{
        flexShrink: 0,
        padding: '10px 12px 12px',
        borderTop: '1px solid var(--border)',
        background: 'var(--surface)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: 8,
          padding: '8px 10px 8px 12px',
          borderRadius: 10,
          border: '1px solid var(--border-2)',
          background: 'var(--surface-2)',
          transition: 'border-color .1s, box-shadow .1s',
        }}
          onFocus={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--brand)';
            (e.currentTarget as HTMLDivElement).style.boxShadow = '0 0 0 3px var(--brand-ring)';
          }}
          onBlur={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget)) {
              (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-2)';
              (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
            }
          }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? 'AI is working…' : 'Describe your HCP interaction…'}
            disabled={isLoading}
            rows={1}
            style={{
              flex: 1, resize: 'none', background: 'transparent',
              border: 'none', outline: 'none',
              fontSize: 13, color: 'var(--t1)',
              lineHeight: 1.55, minHeight: 22, maxHeight: 120,
              fontFamily: 'inherit',
            }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            style={{
              flexShrink: 0, width: 30, height: 30,
              borderRadius: 7, border: 'none',
              background: input.trim() && !isLoading ? 'var(--brand)' : 'var(--surface-4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
              transition: 'all .1s',
              boxShadow: input.trim() && !isLoading ? '0 1px 3px rgba(91,91,214,.3)' : 'none',
            }}
            onMouseEnter={(e) => { if (input.trim() && !isLoading) (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand-hover)'; }}
            onMouseLeave={(e) => { if (input.trim() && !isLoading) (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand)'; }}
          >
            {isLoading
              ? <Loader2 style={{ width: 13, height: 13, color: 'var(--t4)', animation: 'spin 1s linear infinite' }} />
              : <ArrowUp style={{ width: 13, height: 13, color: input.trim() ? 'white' : 'var(--t4)' }} />}
          </button>
        </div>
        <p style={{ fontSize: 10, color: 'var(--t4)', textAlign: 'center', marginTop: 6, userSelect: 'none' }}>
          Enter to send · Shift+Enter for new line
        </p>
      </div>

    </div>
  );
};

export default Chat;
