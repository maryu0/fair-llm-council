import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse }) {
  if (!finalResponse) return null;

  const modelShort = (finalResponse.model || '').split('/').pop() || finalResponse.model;

  return (
    <div className="stage3-synthesis" id="stage3-synthesis">
      <div className="stage3-synthesis-header">
        <div className="stage3-chairman-label">
          <span className="chairman-crown">👑</span>
          <span className="chairman-title">Chairman Synthesis</span>
        </div>
        <div className="chairman-model-chip">
          <div className="chairman-model-dot" />
          {modelShort}
        </div>
      </div>
      <div className="stage3-synthesis-body">
        <div className="markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
