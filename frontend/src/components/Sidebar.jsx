import './Sidebar.css';

function formatRelativeTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// Council nodes SVG icon
function CouncilIcon() {
  return (
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Center node */}
      <circle cx="20" cy="20" r="5" fill="#6c63ff" />
      {/* Top node */}
      <circle cx="20" cy="6" r="3.5" fill="#8781ff" />
      {/* Bottom-left node */}
      <circle cx="8" cy="31" r="3.5" fill="#8781ff" />
      {/* Bottom-right node */}
      <circle cx="32" cy="31" r="3.5" fill="#8781ff" />
      {/* Connections */}
      <line x1="20" y1="9.5" x2="20" y2="15" stroke="#6c63ff" strokeWidth="1.5" strokeOpacity="0.7" />
      <line x1="10.5" y1="29" x2="16" y2="23" stroke="#6c63ff" strokeWidth="1.5" strokeOpacity="0.7" />
      <line x1="29.5" y1="29" x2="24" y2="23" stroke="#6c63ff" strokeWidth="1.5" strokeOpacity="0.7" />
      {/* Glow rings */}
      <circle cx="20" cy="20" r="8" stroke="#6c63ff" strokeWidth="0.8" strokeOpacity="0.25" />
      <circle cx="20" cy="20" r="12" stroke="#6c63ff" strokeWidth="0.5" strokeOpacity="0.1" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 2.5A1.5 1.5 0 013.5 1h9A1.5 1.5 0 0114 2.5v7A1.5 1.5 0 0112.5 11H9l-3 3v-3H3.5A1.5 1.5 0 012 9.5v-7z"
        stroke="currentColor" strokeWidth="1.2" fill="none" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" width="13" height="13">
      <path d="M2 4h12M5 4V2.5A.5.5 0 015.5 2h5a.5.5 0 01.5.5V4M6 7v5M10 7v5M3 4l.8 9.5A.5.5 0 004.3 14h7.4a.5.5 0 00.5-.5L13 4"
        stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}) {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <CouncilIcon />
        </div>
        <div className="brand-text">
          <div className="brand-name">FairCouncil</div>
          <div className="brand-tagline">Bias-Aware AI Council</div>
        </div>
      </div>

      {/* New Conversation */}
      <div className="sidebar-actions">
        <button
          className="new-conversation-btn"
          onClick={onNewConversation}
          id="new-conversation-btn"
        >
          <PlusIcon />
          New Conversation
        </button>
      </div>

      {/* Section Label */}
      {conversations.length > 0 && (
        <div className="sidebar-section-label">Conversations</div>
      )}

      {/* Conversation List */}
      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="conv-list-empty">
            <p>No conversations yet.<br />Start one above.</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
              id={`conversation-${conv.id}`}
            >
              <div className="conv-icon">
                <ChatIcon />
              </div>
              <div className="conv-meta">
                <div className="conv-title">
                  {conv.title || 'New Conversation'}
                </div>
                <div className="conv-subtitle">
                  {formatRelativeTime(conv.created_at)}
                </div>
              </div>
              {conv.message_count > 0 && (
                <div className="conv-badge">{conv.message_count}</div>
              )}
              <button
                className="conv-delete-btn"
                onClick={(e) => { e.stopPropagation(); onDeleteConversation(conv.id); }}
                id={`delete-conversation-${conv.id}`}
                aria-label="Delete conversation"
                title="Delete conversation"
              >
                <TrashIcon />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="footer-status-dot" />
        <span className="footer-label">Online</span>
        <div className="footer-providers">
          <span className="provider-chip gemini">Gemini</span>
          <span className="provider-chip groq">Groq</span>
        </div>
      </div>
    </aside>
  );
}
