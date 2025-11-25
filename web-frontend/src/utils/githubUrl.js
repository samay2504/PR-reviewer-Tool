/**
 * GitHub URL utilities
 */

/**
 * Construct GitHub file URL with line range
 * @param {string} repo - Repository owner/name
 * @param {string} file - File path
 * @param {number} lineStart - Start line
 * @param {number} lineEnd - End line (optional)
 * @param {string} branch - Branch name (default: main)
 * @returns {string} GitHub URL
 */
export function getGitHubFileUrl(repo, file, lineStart, lineEnd = null, branch = 'main') {
  const baseUrl = `https://github.com/${repo}/blob/${branch}/${file}`;
  
  if (lineEnd && lineEnd !== lineStart) {
    return `${baseUrl}#L${lineStart}-L${lineEnd}`;
  }
  
  return `${baseUrl}#L${lineStart}`;
}

/**
 * Construct GitHub PR URL
 * @param {string} repo - Repository owner/name
 * @param {number} prNumber - PR number
 * @returns {string} GitHub PR URL
 */
export function getGitHubPRUrl(repo, prNumber) {
  return `https://github.com/${repo}/pull/${prNumber}`;
}

/**
 * Extract owner and repo name from repo string
 * @param {string} repo - Repository string (owner/repo)
 * @returns {Object} {owner, name}
 */
export function parseRepo(repo) {
  const [owner, name] = repo.split('/');
  return { owner, name };
}
