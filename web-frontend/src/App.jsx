import React, { useState, useEffect } from 'react';
import InputCard from './components/InputCard';
import ResultsPanel from './components/ResultsPanel';
import Spinner from './components/Spinner';
import Toast from './components/Toast';
import { analyze, loadConfig, getApiBase } from './api/client';
import './styles/main.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [apiBase, setApiBase] = useState('');
  const [abortController, setAbortController] = useState(null);
  
  useEffect(() => {
    // Load config on mount
    loadConfig().then(config => {
      setApiBase(config.API_BASE);
    });
  }, []);
  
  const handleAnalyze = async (payload, demoData = null) => {
    // If demo data provided, show it directly
    if (demoData) {
      setResult(demoData);
      setError(null);
      setToast('Demo data loaded!');
      return;
    }
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      const data = await analyze(payload, controller.signal);
      setResult(data);
      setToast('Analysis complete!');
    } catch (err) {
      setError(err.message);
      console.error('Analysis error:', err);
    } finally {
      setLoading(false);
      setAbortController(null);
    }
  };
  
  const handleCancel = () => {
    if (abortController) {
      abortController.abort();
      setLoading(false);
      setAbortController(null);
      setToast('Analysis cancelled');
    }
  };
  
  const handleCopy = (message) => {
    setToast(message);
  };
  
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Progress bar */}
      {loading && <div className="progress-bar"></div>}
      
      {/* Header */}
      <header style={{
        padding: 'var(--space-lg) var(--space-xl)',
        borderBottom: '1px solid var(--card-border)',
        backgroundColor: 'var(--card-bg)'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <div className="flex justify-between items-center" style={{ flexWrap: 'wrap', gap: 'var(--space-md)' }}>
            <div>
              <h1 style={{ 
                margin: 0, 
                fontSize: '2rem', 
                fontWeight: 700,
                background: 'linear-gradient(135deg, #ffffff 0%, #E10600 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>
                PR Review Agent
              </h1>
              <p className="text-muted" style={{ margin: '0.5rem 0 0 0', fontSize: '0.875rem' }}>
                AI-powered automated pull request analysis with security, performance, and style checks
              </p>
            </div>
            <div className="flex items-center gap-2">
              {apiBase && (
                <div style={{
                  padding: 'var(--space-xs) var(--space-sm)',
                  backgroundColor: 'var(--card-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  fontFamily: 'monospace'
                }}>
                  API: {apiBase}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Main content */}
      <main style={{
        flex: 1,
        padding: 'var(--space-xl)',
        maxWidth: '1400px',
        width: '100%',
        margin: '0 auto'
      }}>
        {/* Loading Modal */}
        {loading && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div className="card" style={{ textAlign: 'center', minWidth: '300px' }}>
              <Spinner text="Analyzing — this may take a few seconds..." />
              <button
                className="btn btn-secondary btn-small mt-3"
                onClick={handleCancel}
              >
                ✕ Cancel
              </button>
            </div>
          </div>
        )}
        
        {/* Input Section */}
        <div style={{ marginBottom: 'var(--space-xl)' }}>
          <InputCard onAnalyze={handleAnalyze} loading={loading} />
        </div>
        
        {/* Error Display */}
        {error && (
          <div className="card mb-3" style={{
            borderColor: 'var(--accent)',
            backgroundColor: 'rgba(225, 6, 0, 0.1)'
          }}>
            <div className="flex items-center gap-2">
              <span style={{ fontSize: '1.5rem' }}>⚠️</span>
              <div style={{ flex: 1 }}>
                <strong style={{ display: 'block', marginBottom: '0.5rem' }}>Error</strong>
                <p style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                  {error}
                </p>
              </div>
            </div>
          </div>
        )}
        
        {/* Results Section */}
        {result && (
          <ResultsPanel result={result} onCopy={handleCopy} />
        )}
        
        {/* Empty State */}
        {!loading && !result && !error && (
          <div className="card text-center" style={{ padding: 'var(--space-2xl)' }}>
            <div style={{ fontSize: '4rem', marginBottom: 'var(--space-lg)' }}>
              🔍
            </div>
            <h2 style={{ marginBottom: 'var(--space-md)', color: 'var(--fg)' }}>
              Ready to analyze your PR
            </h2>
            <p className="text-muted" style={{ maxWidth: '600px', margin: '0 auto', lineHeight: '1.6' }}>
              Paste a GitHub PR URL, repository name with PR number, or raw diff text above to get started.
              Our AI agents will analyze your code for security vulnerabilities, performance issues, and style problems.
            </p>
          </div>
        )}
      </main>
      
      {/* Footer */}
      <footer style={{
        padding: 'var(--space-lg) var(--space-xl)',
        borderTop: '1px solid var(--card-border)',
        backgroundColor: 'var(--card-bg)',
        textAlign: 'center'
      }}>
        <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
          PR Review Agent © 2025 | 
          <a 
            href="https://github.com/samay2504/PR-reviewer-Tool" 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ color: 'var(--accent)', textDecoration: 'none', marginLeft: '0.5rem' }}
          >
            GitHub
          </a>
        </p>
      </footer>
      
      {/* Toast */}
      {toast && (
        <Toast
          message={toast}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;
