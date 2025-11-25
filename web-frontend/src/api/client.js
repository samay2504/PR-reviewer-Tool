/**
 * API client for PR Review Agent backend
 * Reads configuration from /config.json at runtime
 */

let config = null;

/**
 * Load configuration from public/config.json
 */
export async function loadConfig() {
  if (config) return config;
  
  try {
    const response = await fetch('/config.json');
    config = await response.json();
    return config;
  } catch (error) {
    console.error('Failed to load config:', error);
    // Fallback config
    config = {
      API_BASE: 'http://localhost:8000',
      ALLOW_POST_FROM_UI: false,
      DEMO_MODE: false
    };
    return config;
  }
}

/**
 * Get current API base URL
 */
export function getApiBase() {
  return config?.API_BASE || 'http://localhost:8000';
}

/**
 * Analyze a PR or diff
 * @param {Object} payload - Analysis request
 * @param {AbortSignal} signal - Abort controller signal
 * @returns {Promise<Object>} Analysis result
 */
export async function analyze(payload, signal = null) {
  await loadConfig();
  
  const url = `${getApiBase()}/analyze`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Request cancelled');
    }
    
    // Check for CORS error
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      throw new Error(
        `CORS Error: Unable to connect to ${url}. ` +
        `Please ensure the backend allows requests from ${window.location.origin}. ` +
        `Contact the backend administrator to whitelist this origin.`
      );
    }
    
    throw error;
  }
}

/**
 * Post comments to GitHub PR (requires posting token)
 * @param {string} repo - Repository owner/name
 * @param {number} prNumber - PR number
 * @param {Array} comments - Comments to post
 * @param {string} token - GitHub token
 * @returns {Promise<Object>} Post result
 */
export async function postComments(repo, prNumber, comments, token) {
  await loadConfig();
  
  if (!config.ALLOW_POST_FROM_UI) {
    throw new Error('Posting comments from UI is disabled. Set ALLOW_POST_FROM_UI to true in config.json');
  }
  
  const url = `${getApiBase()}/post-comments`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        repo,
        pr_number: prNumber,
        comments
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    throw error;
  }
}

/**
 * Check backend health
 * @returns {Promise<Object>} Health status
 */
export async function healthCheck() {
  await loadConfig();
  
  const url = `${getApiBase()}/health`;
  
  try {
    const response = await fetch(url);
    return await response.json();
  } catch (error) {
    throw new Error('Backend is not responding');
  }
}

/**
 * Load demo data from samples
 * @returns {Promise<Object>} Sample analysis
 */
export async function loadDemoData() {
  try {
    const response = await fetch('/samples/sample_analysis.json');
    return await response.json();
  } catch (error) {
    console.error('Failed to load demo data:', error);
    throw error;
  }
}
