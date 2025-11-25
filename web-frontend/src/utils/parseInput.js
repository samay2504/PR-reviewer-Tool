/**
 * Parse various input formats into structured request
 */

const PR_URL_REGEX = /github\.com\/([^\/]+)\/([^\/]+)\/pull\/(\d+)/;
const REPO_URL_REGEX = /github\.com\/([^\/]+)\/([^\/]+)/;
const REPO_NAME_REGEX = /^([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_.-]+)$/;

/**
 * Detect input type and parse accordingly
 * @param {string} input - User input
 * @param {string} mode - Forced mode or 'auto'
 * @returns {Object} Parsed request data
 */
export function parseInput(input, mode = 'auto') {
  const trimmed = input.trim();
  
  if (!trimmed) {
    throw new Error('Input cannot be empty');
  }
  
  // Auto-detect mode
  if (mode === 'auto') {
    // Check for PR URL
    const prMatch = trimmed.match(PR_URL_REGEX);
    if (prMatch) {
      return {
        type: 'pr',
        repo: `${prMatch[1]}/${prMatch[2]}`,
        pr_number: parseInt(prMatch[3], 10)
      };
    }
    
    // Check for repo URL
    const repoUrlMatch = trimmed.match(REPO_URL_REGEX);
    if (repoUrlMatch) {
      return {
        type: 'repo',
        repo: `${repoUrlMatch[1]}/${repoUrlMatch[2]}`
      };
    }
    
    // Check for repo name
    const repoNameMatch = trimmed.match(REPO_NAME_REGEX);
    if (repoNameMatch) {
      return {
        type: 'repo',
        repo: trimmed
      };
    }
    
    // Assume it's a diff
    return {
      type: 'diff',
      diff_text: trimmed
    };
  }
  
  // Forced mode
  switch (mode) {
    case 'pr':
      const prMatch = trimmed.match(PR_URL_REGEX);
      if (prMatch) {
        return {
          type: 'pr',
          repo: `${prMatch[1]}/${prMatch[2]}`,
          pr_number: parseInt(prMatch[3], 10)
        };
      }
      throw new Error('Invalid PR URL format. Expected: https://github.com/owner/repo/pull/123');
    
    case 'repo':
      const repoMatch = trimmed.match(REPO_URL_REGEX) || trimmed.match(REPO_NAME_REGEX);
      if (repoMatch) {
        return {
          type: 'repo',
          repo: repoMatch[1] ? `${repoMatch[1]}/${repoMatch[2]}` : trimmed
        };
      }
      throw new Error('Invalid repo format. Expected: owner/repo or https://github.com/owner/repo');
    
    case 'diff':
      return {
        type: 'diff',
        diff_text: trimmed
      };
    
    default:
      throw new Error(`Unknown mode: ${mode}`);
  }
}

/**
 * Validate parsed input
 * @param {Object} parsed - Parsed input
 * @returns {boolean} Is valid
 */
export function validateInput(parsed) {
  if (!parsed || !parsed.type) {
    return false;
  }
  
  switch (parsed.type) {
    case 'pr':
      return !!(parsed.repo && parsed.pr_number);
    case 'repo':
      return !!parsed.repo;
    case 'diff':
      return !!parsed.diff_text;
    default:
      return false;
  }
}

/**
 * Convert parsed input to API payload
 * @param {Object} parsed - Parsed input
 * @param {Object} options - Additional options
 * @returns {Object} API request payload
 */
export function toApiPayload(parsed, options = {}) {
  const payload = {
    use_cache: options.use_cache !== false
  };
  
  switch (parsed.type) {
    case 'pr':
      payload.repo = parsed.repo;
      payload.pr_number = parsed.pr_number;
      break;
    case 'repo':
      payload.repo = parsed.repo;
      // Note: Backend doesn't support listing PRs, this should show error
      break;
    case 'diff':
      payload.diff_text = parsed.diff_text;
      break;
  }
  
  return payload;
}
