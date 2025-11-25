/**
 * Session storage utilities for sensitive data
 */

const POSTING_TOKEN_KEY = 'pr_agent_posting_token';

/**
 * Store posting token in session storage
 * @param {string} token - GitHub token
 */
export function storePostingToken(token) {
  if (!token) return;
  sessionStorage.setItem(POSTING_TOKEN_KEY, token);
}

/**
 * Get posting token from session storage
 * @returns {string|null} Token or null
 */
export function getPostingToken() {
  return sessionStorage.getItem(POSTING_TOKEN_KEY);
}

/**
 * Clear posting token from session storage
 */
export function clearPostingToken() {
  sessionStorage.removeItem(POSTING_TOKEN_KEY);
}

/**
 * Check if posting token exists
 * @returns {boolean} Has token
 */
export function hasPostingToken() {
  return !!sessionStorage.getItem(POSTING_TOKEN_KEY);
}
