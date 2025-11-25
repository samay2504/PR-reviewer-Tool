"""GitHub API client for fetching PR diffs."""

import requests
from typing import Optional, Dict, Any
from ..utils.logging import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def fetch_pr_diff(self, repo: str, pr_number: int) -> Optional[str]:
        """
        Fetch PR diff from GitHub.
        
        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            Diff text or None if failed
        """
        try:
            # Get PR metadata
            pr_url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
            logger.info(f"Fetching PR metadata from {pr_url}")
            
            response = requests.get(pr_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            pr_data = response.json()
            diff_url = pr_data.get("diff_url")
            
            if not diff_url:
                logger.error("No diff_url found in PR data")
                return None
            
            # Fetch diff
            logger.info(f"Fetching diff from {diff_url}")
            diff_response = requests.get(diff_url, headers=self.headers, timeout=30)
            diff_response.raise_for_status()
            
            diff_text = diff_response.text
            logger.info(f"Successfully fetched diff ({len(diff_text)} bytes)")
            
            return diff_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch PR diff: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching PR diff: {e}")
            return None
    
    def fetch_pr_metadata(self, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """
        Fetch PR metadata from GitHub.
        
        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            
        Returns:
            PR metadata dictionary or None if failed
        """
        try:
            pr_url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
            response = requests.get(pr_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch PR metadata: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching PR metadata: {e}")
            return None
    
    def list_pull_requests(self, repo: str, state: str = "open", limit: int = 20) -> Optional[list]:
        """
        List pull requests for a repository.
        
        Args:
            repo: Repository in format "owner/repo"
            state: PR state ("open", "closed", "all")
            limit: Maximum number of PRs to fetch (default 20)
            
        Returns:
            List of PR dictionaries or None if failed
        """
        try:
            pr_list_url = f"{self.base_url}/repos/{repo}/pulls"
            params = {
                "state": state,
                "per_page": limit,
                "sort": "updated",
                "direction": "desc"
            }
            
            logger.info(f"Fetching {state} PRs from {repo}")
            response = requests.get(pr_list_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            prs = response.json()
            logger.info(f"Found {len(prs)} {state} PRs")
            
            return prs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch PR list: {e}")
            return None
