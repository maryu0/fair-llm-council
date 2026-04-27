import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

function getProviderClass(model, provider) {
  const m = (model || '').toLowerCase();
  const p = (provider || '').toLowerCase();
  if (p === 'gemini' || m.includes('gemini')) return 'gemini';
  if (p === 'groq' || m.includes('groq')) return 'groq';
  if (m.includes('llama')) return 'llama';
  return 'default';
}

function getShortName(model, provider) {
  if (provider === 'gemini') return 'Gemini';
  if (provider === 'groq') return 'Groq';
  // Try to get the part after last '/'
  const parts = model.split('/');
  const base = parts[parts.length - 1];
  // shorten model names
  if (base.includes('gemini')) return base.replace('gemini-', 'Gemini ').replace('-', ' ');
  if (base.includes('llama')) return 'Llama';
  return base.slice(0, 16);
}

export default function Stage1({ responses }) {
  const [activeIndex, setActiveIndex] = useState(null);

  if (!responses || responses.length === 0) return null;

  const toggleCard = (i) => setActiveIndex(activeIndex === i ? null : i);

  return (
    <div className="stage1">
      <div className="stage1-grid">
        {responses.map((resp, i) => {
          const provClass = getProviderClass(resp.model, resp.provider);
          const shortName = getShortName(resp.model, resp.provider);
          const isActive = activeIndex === i;

          return (
            <div
              key={i}
              className={`model-card ${isActive ? 'active' : ''}`}
              onClick={() => toggleCard(i)}
              id={`model-card-${i}`}
            >
              <div className="model-card-header">
                <span className={`model-badge ${provClass}`}>
                  <span className="model-badge-dot" />
                  {shortName}
                </span>
                {resp.latency_ms != null && (
                  <span className="latency-chip">{resp.latency_ms}ms</span>
                )}
              </div>

              <div className="model-name-full">{resp.model}</div>

              <div className="model-preview">
                {resp.response?.slice(0, 180)}
                {resp.response?.length > 180 && '…'}
              </div>
            </div>
          );
        })}
      </div>

      {activeIndex !== null && (
        <div className="stage1-detail">
          <div className="stage1-detail-header">
            <span className="stage1-detail-title">
              {responses[activeIndex].model}
            </span>
            <span className={`model-badge ${getProviderClass(responses[activeIndex].model, responses[activeIndex].provider)}`}>
              <span className="model-badge-dot" />
              {getShortName(responses[activeIndex].model, responses[activeIndex].provider)}
            </span>
          </div>
          <div className="stage1-detail-body">
            <div className="markdown-content">
              <ReactMarkdown>{responses[activeIndex].response}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
