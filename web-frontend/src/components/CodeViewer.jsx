import React from 'react';

export default function CodeViewer({ diff }) {
  if (!diff) return null;
  
  return (
    <div className="card">
      <h3 style={{ marginBottom: 'var(--space-md)', fontSize: '1.25rem' }}>
        Code Preview
      </h3>
      <div className="code-block">
        <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {diff}
        </pre>
      </div>
    </div>
  );
}
