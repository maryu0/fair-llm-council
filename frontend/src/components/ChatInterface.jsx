import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

// ── Icons ────────────────────────────────────────────────

function CouncilIconLarge() {
  return (
    <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="40" cy="40" r="10" fill="#6c63ff" />
      <circle cx="40" cy="12" r="7" fill="#8781ff" />
      <circle cx="16" cy="62" r="7" fill="#8781ff" />
      <circle cx="64" cy="62" r="7" fill="#8781ff" />
      <line x1="40" y1="19" x2="40" y2="30" stroke="#6c63ff" strokeWidth="2.5" strokeOpacity="0.7" />
      <line x1="21" y1="57" x2="32" y2="46" stroke="#6c63ff" strokeWidth="2.5" strokeOpacity="0.7" />
      <line x1="59" y1="57" x2="48" y2="46" stroke="#6c63ff" strokeWidth="2.5" strokeOpacity="0.7" />
      <circle cx="40" cy="40" r="18" stroke="#6c63ff" strokeWidth="1" strokeOpacity="0.2" />
      <circle cx="40" cy="40" r="28" stroke="#6c63ff" strokeWidth="0.6" strokeOpacity="0.1" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronDown() {
  return (
    <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" width="14" height="14">
      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Helpers ───────────────────────────────────────────────

const QUICK_CHIPS = [
  'Ethical trade-offs in AI decision making',
  'Bias detection in datasets',
  'Policy synthesis for fair governance',
  'Explain bias-aware model selection',
];

function StageLoadingCard({ badgeClass, badgeLabel, title, sub }) {
  return (
    <div className="stage-loading-container">
      <div className="stage-loading-spinner">
        <div className="spinner-ring outer" />
        <div className="spinner-ring inner" />
      </div>
      <div className="stage-loading-text">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span className={`stage-badge ${badgeClass}`}>
            <span className="stage-badge-dot" />
            {badgeLabel}
          </span>
        </div>
        <div className="stage-loading-title">{title}</div>
        <div className="stage-loading-sub">
          {sub}&nbsp;
          <span className="loading-dots">
            <span /><span /><span />
          </span>
        </div>
      </div>
    </div>
  );
}

function CollapsibleStage({ badgeClass, badgeLabel, title, meta, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="stage-container">
      <div className="stage-header" onClick={() => setOpen(o => !o)}>
        <div className="stage-header-left">
          <span className={`stage-badge ${badgeClass}`}>
            <span className="stage-badge-dot" />
            {badgeLabel}
          </span>
          <span className="stage-title-text">{title}</span>
          {meta && <span className="stage-meta">{meta}</span>}
        </div>
        <span className={`stage-chevron ${open ? 'expanded' : ''}`}>
          <ChevronDown />
        </span>
      </div>
      {open && (
        <div className="stage-body">
          {children}
        </div>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────

export default function ChatInterface({ conversation, onSendMessage, isLoading }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    // Auto-resize
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 140) + 'px';
  };

  const handleQuickChip = (text) => {
    setInput(text);
    textareaRef.current?.focus();
  };

  // ── Empty (no conversation selected) ──
  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <div className="empty-council-icon">
            <CouncilIconLarge />
          </div>
          <div className="empty-state-headline">Ask the Council</div>
          <div className="empty-state-sub">
            Multiple AI models will debate and synthesize the best answer for you.
            Bias-aware, peer-ranked, and unified.
          </div>
          <div style={{ color: 'var(--text-subtle)', fontSize: '0.8rem' }}>
            ← Create a new conversation to begin
          </div>
        </div>
      </div>
    );
  }

  const hasMessages = conversation.messages && conversation.messages.length > 0;

  return (
    <div className="chat-interface">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-title">
          <span className="chat-title-text">
            {conversation.title && conversation.title !== 'New Conversation'
              ? conversation.title
              : 'New Conversation'}
          </span>
        </div>
        <div className="chat-status-badge">
          <div className="status-dot" />
          Council Online
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {!hasMessages ? (
          <div className="empty-state" style={{ flex: 1 }}>
            <div className="empty-council-icon">
              <CouncilIconLarge />
            </div>
            <div className="empty-state-headline">Ask the Council</div>
            <div className="empty-state-sub">
              Multiple AI models will debate and synthesize the best answer.
              Bias-aware, peer-ranked, and unified.
            </div>
            <div className="quick-chips">
              {QUICK_CHIPS.map((chip, i) => (
                <button
                  key={i}
                  className="quick-chip"
                  onClick={() => handleQuickChip(chip)}
                  id={`quick-chip-${i}`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : (
          conversation.messages.map((msg, idx) => (
            <div key={idx} className="message-group">
              {msg.role === 'user' ? (
                /* ── USER MESSAGE ── */
                <div className="user-message">
                  <div className="message-label-user">You</div>
                  <div className="user-bubble">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                /* ── COUNCIL MESSAGE ── */
                <div className="assistant-message">
                  <div className="message-label-council">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <StageLoadingCard
                      badgeClass="stage1-badge"
                      badgeLabel="Stage 1 • Collect"
                      title="Gathering individual responses"
                      sub="Models are thinking"
                    />
                  )}
                  {msg.stage1 && (
                    <CollapsibleStage
                      badgeClass="stage1-badge"
                      badgeLabel="Stage 1 • Collect"
                      title="Individual Responses"
                      meta={`${msg.stage1.length} model${msg.stage1.length !== 1 ? 's' : ''}`}
                      defaultOpen={true}
                    >
                      <Stage1 responses={msg.stage1} />
                    </CollapsibleStage>
                  )}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <StageLoadingCard
                      badgeClass="stage2-badge"
                      badgeLabel="Stage 2 • Review"
                      title="Running peer evaluations"
                      sub="Models are ranking each other"
                    />
                  )}
                  {msg.stage2 && (
                    <CollapsibleStage
                      badgeClass="stage2-badge"
                      badgeLabel="Stage 2 • Review"
                      title="Peer Rankings"
                      meta={`${msg.stage2.length} evaluator${msg.stage2.length !== 1 ? 's' : ''}`}
                      defaultOpen={true}
                    >
                      <Stage2
                        rankings={msg.stage2}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateRankings={msg.metadata?.aggregate_rankings}
                      />
                    </CollapsibleStage>
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <StageLoadingCard
                      badgeClass="stage3-badge"
                      badgeLabel="Stage 3 • Chairman"
                      title="Synthesizing final answer"
                      sub="Chairman is deliberating"
                    />
                  )}
                  {msg.stage3 && (
                    <Stage3 finalResponse={msg.stage3} />
                  )}
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <form onSubmit={handleSubmit}>
          <div className="input-container">
            <textarea
              ref={textareaRef}
              id="message-input"
              className="message-textarea"
              placeholder="Ask the council a question…"
              value={input}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
              aria-label="Message input"
            />
            <button
              type="submit"
              id="send-button"
              className="send-button"
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          </div>
        </form>
        <div className="input-hint">
          <span className="input-hint-text">
            <kbd>Shift</kbd> + <kbd>Enter</kbd> for new line
          </span>
        </div>
      </div>
    </div>
  );
}
