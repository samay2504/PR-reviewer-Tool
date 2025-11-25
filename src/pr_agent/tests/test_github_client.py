"""Test GitHub API client functionality."""

import pytest
from unittest.mock import Mock, patch
from pr_agent.utils.github_client import GitHubClient


class TestGitHubClient:
    """Test GitHub client functionality."""
    
    def test_github_client_initialization(self):
        """Test basic initialization."""
        client = GitHubClient(token="test_token")
        assert client.token == "test_token"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_token"
    
    def test_github_client_without_token(self):
        """Test initialization without token."""
        client = GitHubClient()
        assert client.token is None
        assert "Authorization" not in client.headers
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_fetch_pr_diff_success(self, mock_get):
        """Test successful PR diff fetching."""
        # Mock PR metadata response
        pr_response = Mock()
        pr_response.json.return_value = {
            "number": 123,
            "title": "Test PR",
            "diff_url": "https://github.com/test/repo/pull/123.diff"
        }
        pr_response.raise_for_status = Mock()
        
        # Mock diff response
        diff_response = Mock()
        diff_response.text = "diff --git a/test.py b/test.py\n..."
        diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [pr_response, diff_response]
        
        client = GitHubClient(token="test_token")
        diff = client.fetch_pr_diff("test/repo", 123)
        
        assert diff == "diff --git a/test.py b/test.py\n..."
        assert mock_get.call_count == 2
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_fetch_pr_diff_no_diff_url(self, mock_get):
        """Test PR without diff_url."""
        pr_response = Mock()
        pr_response.json.return_value = {
            "number": 123,
            "title": "Test PR"
            # Missing diff_url
        }
        pr_response.raise_for_status = Mock()
        
        mock_get.return_value = pr_response
        
        client = GitHubClient(token="test_token")
        diff = client.fetch_pr_diff("test/repo", 123)
        
        assert diff is None
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_fetch_pr_diff_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_get.side_effect = Exception("HTTP 404 Not Found")
        
        client = GitHubClient(token="test_token")
        diff = client.fetch_pr_diff("test/repo", 999)
        
        assert diff is None
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_fetch_pr_metadata_success(self, mock_get):
        """Test successful PR metadata fetching."""
        pr_response = Mock()
        pr_response.json.return_value = {
            "number": 123,
            "title": "Test PR",
            "user": {"login": "testuser"},
            "state": "open"
        }
        pr_response.raise_for_status = Mock()
        
        mock_get.return_value = pr_response
        
        client = GitHubClient(token="test_token")
        metadata = client.fetch_pr_metadata("test/repo", 123)
        
        assert metadata["number"] == 123
        assert metadata["title"] == "Test PR"
        assert metadata["user"]["login"] == "testuser"
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_fetch_pr_metadata_error(self, mock_get):
        """Test metadata fetching error."""
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("Network error")
        
        client = GitHubClient(token="test_token")
        metadata = client.fetch_pr_metadata("test/repo", 123)
        
        assert metadata is None
    
    def test_real_github_api_connection(self):
        """Test real GitHub API with django/django PR (no token needed for public)."""
        client = GitHubClient()
        
        # Test metadata fetch
        metadata = client.fetch_pr_metadata("django/django", 20316)
        
        if metadata:
            assert "number" in metadata
            assert metadata["number"] == 20316
            assert "title" in metadata
        else:
            pytest.skip("GitHub API not accessible (rate limit or network issue)")
    
    def test_real_github_api_diff_fetch(self):
        """Test real diff fetching from GitHub."""
        client = GitHubClient()
        
        # Fetch a small closed PR
        diff = client.fetch_pr_diff("django/django", 20316)
        
        if diff:
            assert "diff --git" in diff
            assert len(diff) > 0
        else:
            pytest.skip("GitHub API not accessible (rate limit or network issue)")
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_fetch_with_timeout(self, mock_get):
        """Test that requests use proper timeout."""
        pr_response = Mock()
        pr_response.json.return_value = {"diff_url": "https://test.diff"}
        pr_response.raise_for_status = Mock()
        
        diff_response = Mock()
        diff_response.text = "diff content"
        diff_response.raise_for_status = Mock()
        
        mock_get.side_effect = [pr_response, diff_response]
        
        client = GitHubClient()
        client.fetch_pr_diff("test/repo", 1)
        
        # Verify timeout was used
        calls = mock_get.call_args_list
        assert calls[0][1]['timeout'] == 10  # PR metadata timeout
        assert calls[1][1]['timeout'] == 30  # Diff fetch timeout
