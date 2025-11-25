import React, { useState } from 'react';

export default function InputCard({ onAnalyze, loading }) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('auto');
  const [prNumber, setPrNumber] = useState('');
  const [useCache, setUseCache] = useState(true);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!input.trim()) {
      alert('Please enter a GitHub PR URL, repo name, or diff text');
      return;
    }
    
    let payload = { use_cache: useCache };
    
    // Parse input based on mode
    if (mode === 'auto' || mode === 'pr') {
      // Try to extract PR info from URL
      const prMatch = input.match(/github\.com\/([^\/]+)\/([^\/]+)\/pull\/(\d+)/);
      if (prMatch) {
        payload.repo = `${prMatch[1]}/${prMatch[2]}`;
        payload.pr_number = parseInt(prMatch[3], 10);
      } else if (mode === 'pr' && prNumber) {
        // Manual PR number entry
        payload.repo = input;
        payload.pr_number = parseInt(prNumber, 10);
      } else if (mode === 'auto') {
        // Try repo mode
        const repoMatch = input.match(/github\.com\/([^\/]+)\/([^\/]+)/);
        if (repoMatch) {
          alert('Repo-only mode requires a PR number. Please provide a full PR URL or enter PR number manually.');
          return;
        }
        // Assume it's a diff
        payload.diff_text = input;
      }
    } else if (mode === 'repo') {
      // Extract repo from URL or use as-is
      const repoMatch = input.match(/github\.com\/([^\/]+)\/([^\/]+)/);
      if (repoMatch) {
        payload.repo = `${repoMatch[1]}/${repoMatch[2]}`;
      } else {
        payload.repo = input;
      }
      
      if (!prNumber) {
        alert('Please enter a PR number');
        return;
      }
      payload.pr_number = parseInt(prNumber, 10);
    } else if (mode === 'diff') {
      payload.diff_text = input;
    }
    
    onAnalyze(payload);
  };
  
  const handleClear = () => {
    setInput('');
    setPrNumber('');
    setMode('auto');
    setUseCache(true);
  };
  
  const handleLoadDemo = async () => {
    try {
      const response = await fetch('/samples/sample_analysis.json');
      const demoData = await response.json();
      onAnalyze(null, demoData); // Pass demo data directly
    } catch (error) {
      alert('Failed to load demo data');
    }
  };
  
  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="mb-2">
          <label htmlFor="mode">Input Mode</label>
          <select
            id="mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            disabled={loading}
          >
            <option value="auto">Auto-detect</option>
            <option value="pr">Pull Request</option>
            <option value="repo">Repository + PR#</option>
            <option value="diff">Raw Diff</option>
          </select>
        </div>
        
        <div className="mb-2">
          <label htmlFor="input">
            {mode === 'diff' ? 'Paste Diff Text' : 'GitHub URL or Repo Name'}
          </label>
          <textarea
            id="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              mode === 'diff'
                ? 'Paste your git diff here...'
                : mode === 'repo'
                ? 'owner/repo or https://github.com/owner/repo'
                : 'https://github.com/facebook/react/pull/31000'
            }
            rows={mode === 'diff' ? 8 : 3}
            disabled={loading}
            style={{ fontFamily: mode === 'diff' ? 'monospace' : 'inherit' }}
          />
        </div>
        
        {(mode === 'repo' || (mode === 'pr' && !input.includes('pull'))) && (
          <div className="mb-2">
            <label htmlFor="prNumber">PR Number</label>
            <input
              id="prNumber"
              type="number"
              value={prNumber}
              onChange={(e) => setPrNumber(e.target.value)}
              placeholder="e.g., 31000"
              disabled={loading}
              min="1"
            />
          </div>
        )}
        
        <div className="mb-3">
          <label>
            <input
              type="checkbox"
              checked={useCache}
              onChange={(e) => setUseCache(e.target.checked)}
              disabled={loading}
              style={{ width: 'auto', marginRight: '8px' }}
            />
            Use cache (faster for repeated analysis)
          </label>
        </div>
        
        <div className="flex gap-2">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ flex: 1 }}
          >
            {loading ? 'Analyzing...' : '🚀 Run Review'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleClear}
            disabled={loading}
          >
            Clear
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={handleLoadDemo}
            disabled={loading}
            title="Load demo data"
          >
            Demo
          </button>
        </div>
      </form>
      
      <div className="mt-3 text-muted" style={{ fontSize: '0.875rem' }}>
        <p><strong>Examples:</strong></p>
        <ul style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
          <li>PR URL: <code>https://github.com/facebook/react/pull/31000</code></li>
          <li>Repo + PR#: <code>django/django</code> + PR# <code>20316</code></li>
          <li>Raw Diff: Paste your git diff output</li>
        </ul>
      </div>
    </div>
  );
}
