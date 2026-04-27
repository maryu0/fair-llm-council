import ReactMarkdown from "react-markdown";
import "./Stage3.css";

export default function Stage3({ finalResponse }) {
  if (!finalResponse) return null;

  const modelShort =
    (finalResponse.model || "").split("/").pop() || finalResponse.model;
  const selection = finalResponse.selection;

  return (
    <div className="stage3-synthesis" id="stage3-synthesis">
      <div className="stage3-synthesis-header">
        <div className="stage3-chairman-label">
          <span className="chairman-crown">👑</span>
          <span className="chairman-title">Adaptive Chairperson Synthesis</span>
        </div>
        <div className="chairman-model-chip">
          <div className="chairman-model-dot" />
          {modelShort}
        </div>
      </div>
      {selection && (
        <div className="stage3-selection-summary">
          <span>
            Performance {Number(selection.performance_score ?? 0).toFixed(2)}
          </span>
          <span>Bias {Number(selection.bias_score ?? 0).toFixed(2)}</span>
          <span>Final {Number(selection.final_score ?? 0).toFixed(2)}</span>
        </div>
      )}
      <div className="stage3-synthesis-body">
        <div className="markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
