import React, { useState } from 'react';
import { getGitHubFileUrl } from '../utils/githubUrl';

const getCategoryIcon = (category) => {
  const icons = {
    SECURITY: '🔒',
    PERFORMANCE: '⚡',
    STYLE: '🎨',
    BUG: '🐛',
    DOCUMENTATION: '📝'
  };
  return icons[category] || '📌';
};

export default function IssueItem({ issue, repo, onCopy }) {
  const [expanded, setExpanded] = useState(false);
  
  const handleCopyPatch = () => {
    if (issue.suggestion_patch) {
      navigator.clipboard.writeText(issue.suggestion_patch);
      onCopy?.('Patch copied!');
    }
  };
  
  const githubUrl = repo && issue.file !== 'unknown' 
    ? getGitHubFileUrl(repo, issue.file, issue.line_start, issue.line_end)
    : null;
  
  return (
    <div 
      className="card mb-2" 
      style={{ cursor: 'pointer', transition: 'border-color 0.2s' }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2" style={{ flex: 1 }}>
          <span className="category-icon">{getCategoryIcon(issue.category)}</span>
          <div style={{ flex: 1 }}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`severity-pill severity-${issue.severity.toLowerCase()}`}>
                {issue.severity}
              </span>
              <span className="text-muted" style={{ fontSize: '0.875rem' }}>
                {issue.category}
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>
              {expanded ? issue.message : issue.message.substring(0, 80) + (issue.message.length > 80 ? '...' : '')}
            </p>
            <p className="text-muted" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
              {issue.file}:{issue.line_start}
              {issue.line_end && issue.line_end !== issue.line_start && `-${issue.line_end}`}
            </p>
          </div>
        </div>
        <div style={{ fontSize: '1.5rem' }}>
          {expanded ? '▼' : '▶'}
        </div>
      </div>
      
      {expanded && (
        <div className="mt-3" style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1rem' }} onClick={(e) => e.stopPropagation()}>
          <p style={{ marginBottom: '1rem' }}>{issue.message}</p>
          
          {issue.suggestion_patch && (
            <div className="mb-2">
              <div className="flex justify-between items-center mb-1">
                <strong style={{ fontSize: '0.875rem' }}>Suggested Fix:</strong>
                <button className="btn btn-small btn-secondary" onClick={handleCopyPatch}>
                  📋 Copy Patch
                </button>
              </div>
              <div className="code-block">
                <pre>{issue.suggestion_patch}</pre>
              </div>
            </div>
          )}
          
          <div className="flex gap-2">
            {githubUrl && (
              <a 
                href={githubUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="btn btn-small btn-secondary"
              >
                Open on GitHub →
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
