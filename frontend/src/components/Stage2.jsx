import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

const MEDALS = ['🥇', '🥈', '🥉'];

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;
  let result = text;
  Object.entries(labelToModel).forEach(([label, model]) => {
    const shortName = model.split('/').pop() || model;
    result = result.replace(new RegExp(label, 'g'), `**${shortName}**`);
  });
  return result;
}

function getShortName(model) {
  const parts = (model || '').split('/');
  return parts[parts.length - 1] || model;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!rankings || rankings.length === 0) return null;

  // Calculate max avg_rank for bar scaling
  const maxRank = aggregateRankings?.length
    ? Math.max(...aggregateRankings.map(a => a.average_rank))
    : 1;

  return (
    <div className="stage2">
      {/* Aggregate Leaderboard */}
      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="leaderboard">
          {aggregateRankings.map((agg, idx) => {
            const barClass = idx === 0 ? 'rank-1' : idx === 1 ? 'rank-2' : idx === 2 ? 'rank-3' : '';
            // Lower avg_rank = better performance → invert bar width
            const barWidth = Math.max(10, 100 - ((agg.average_rank / maxRank) * 80));

            return (
              <div key={idx} className="leaderboard-row" id={`leaderboard-row-${idx}`}>
                <div className="leaderboard-rank">
                  {idx < 3 ? MEDALS[idx] : `#${idx + 1}`}
                </div>
                <div className="leaderboard-model">
                  <div className="leaderboard-model-name">{getShortName(agg.model)}</div>
                  <div className="leaderboard-model-full">{agg.model}</div>
                </div>
                <div className="leaderboard-score-area">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', justifyContent: 'flex-end' }}>
                    <span className="score-label">Avg Rank</span>
                    <span className="score-value">{agg.average_rank.toFixed(2)}</span>
                    <span className="score-count">({agg.rankings_count}v)</span>
                  </div>
                  <div className="score-bar-track" style={{ width: 120 }}>
                    <div
                      className={`score-bar-fill ${barClass}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Raw Evaluations */}
      <div className="eval-section">
        <div className="eval-section-title">Raw Evaluations</div>
        <div className="eval-tabs">
          {rankings.map((rank, i) => (
            <button
              key={i}
              className={`eval-tab ${activeTab === i ? 'active' : ''}`}
              onClick={() => setActiveTab(i)}
              id={`eval-tab-${i}`}
            >
              {getShortName(rank.model)}
            </button>
          ))}
        </div>

        {rankings[activeTab] && (
          <div className="eval-content">
            <div className="eval-content-header">
              {rankings[activeTab].model}
            </div>
            <div className="eval-content-body">
              <div className="markdown-content">
                <ReactMarkdown>
                  {deAnonymizeText(rankings[activeTab].ranking, labelToModel)}
                </ReactMarkdown>
              </div>

              {rankings[activeTab].parsed_ranking?.length > 0 && (
                <div className="parsed-ranking">
                  <div className="parsed-ranking-title">Extracted Ranking</div>
                  <ol>
                    {rankings[activeTab].parsed_ranking.map((label, i) => (
                      <li key={i}>
                        {labelToModel?.[label]
                          ? getShortName(labelToModel[label])
                          : label}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
