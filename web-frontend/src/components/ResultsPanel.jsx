import React, { useState } from 'react';
import IssueItem from './IssueItem';
import { formatToParagraphs } from '../utils/formatText';

export default function ResultsPanel({ result, onCopy }) {
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  if (!result) return null;
  
  const { comments = [], summary = {} } = result;
  const stats = summary.statistics || {};
  const severityCounts = stats.severity_counts || {};
  
  const filteredComments = comments.filter(comment => {
    if (filter !== 'all' && comment.severity.toLowerCase() !== filter) {
      return false;
    }
    
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        comment.message.toLowerCase().includes(search) ||
        comment.file.toLowerCase().includes(search) ||
        comment.category.toLowerCase().includes(search)
      );
    }
    
    return true;
  });
  
  const handleDownloadJSON = () => {
    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pr-analysis-${result.diff_hash?.substring(0, 8) || 'result'}.json`;
    link.click();
    URL.revokeObjectURL(url);
    onCopy?.('JSON downloaded!');
  };
  
  const handleCopySummary = () => {
    const markdown = `# PR Analysis Summary

**Repository:** ${result.repo || 'N/A'}
**PR Number:** ${result.pr_number || 'N/A'}
**Total Issues:** ${comments.length}

## Severity Breakdown
- Critical: ${severityCounts.critical || 0}
- High: ${severityCounts.high || 0}
- Medium: ${severityCounts.medium || 0}
- Low: ${severityCounts.low || 0}

## Executive Summary
${summary.executive_summary || 'No summary available'}

**Recommendation:** ${summary.recommendation || 'N/A'}
`;
    navigator.clipboard.writeText(markdown);
    onCopy?.('Summary copied!');
  };
  
  return (
    <div>
      <div className="card mb-3">
        <div className="flex justify-between items-center mb-3">
          <div>
            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>
              Analysis Results
            </h2>
            {result.repo && (
              <p className="text-muted" style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem' }}>
                {result.repo}{result.pr_number && ` #${result.pr_number}`}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button className="btn btn-small btn-secondary" onClick={handleDownloadJSON}>
              💾 JSON
            </button>
            <button className="btn btn-small btn-secondary" onClick={handleCopySummary}>
              📋 Summary
            </button>
          </div>
        </div>
        
        <div className="flex gap-2 mb-3" style={{ flexWrap: 'wrap' }}>
          {Object.entries(severityCounts).map(([severity, count]) => (
            count > 0 && (
              <div key={severity} className="flex items-center gap-1">
                <span className={`severity-pill severity-${severity}`}>
                  {severity.toUpperCase()}
                </span>
                <span className="text-muted">×{count}</span>
              </div>
            )
          ))}
        </div>
        
        {summary.executive_summary && (
          <div style={{ 
            padding: 'var(--space-md)', 
            backgroundColor: 'var(--card-border)', 
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--space-md)'
          }}>
            <strong style={{ display: 'block', marginBottom: '0.5rem' }}>Executive Summary:</strong>
            <div style={{ margin: 0, fontSize: '0.875rem', lineHeight: '1.8' }}>
              {formatToParagraphs(summary.executive_summary).map((paragraph, idx) => (
                <p key={idx} style={{ margin: idx > 0 ? '1rem 0 0 0' : 0 }}>
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
        )}
        
        {summary.recommendation && (
          <div className="flex items-center gap-2">
            <span style={{ fontWeight: 600 }}>Recommendation:</span>
            <span className={`severity-pill ${
              summary.recommendation === 'APPROVE' ? 'severity-low' :
              summary.recommendation === 'REQUEST_CHANGES' ? 'severity-high' :
              'severity-medium'
            }`}>
              {summary.recommendation.replace('_', ' ')}
            </span>
          </div>
        )}
      </div>
      
      <div className="card mb-3">
        <div className="mb-2">
          <input
            type="text"
            placeholder="🔍 Search issues by file, category, or message..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
          <button
            className={`btn btn-small ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter('all')}
          >
            All ({comments.length})
          </button>
          {['critical', 'high', 'medium', 'low'].map(severity => (
            severityCounts[severity] > 0 && (
              <button
                key={severity}
                className={`btn btn-small ${filter === severity ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilter(severity)}
              >
                {severity.charAt(0).toUpperCase() + severity.slice(1)} ({severityCounts[severity]})
              </button>
            )
          ))}
        </div>
      </div>
      
      <div>
        {filteredComments.length === 0 ? (
          <div className="card text-center">
            <p className="text-muted">
              {searchTerm ? 'No issues match your search' : 'No issues found'}
            </p>
          </div>
        ) : (
          filteredComments.map((comment, index) => (
            <IssueItem
              key={`${comment.file}-${comment.line_start}-${index}`}
              issue={comment}
              repo={result.repo}
              onCopy={onCopy}
            />
          ))
        )}
      </div>
    </div>
  );
}
