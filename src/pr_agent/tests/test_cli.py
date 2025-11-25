"""Tests for CLI functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pr_agent.cli import PRAgentCLI


class TestCLI:
    """Test suite for CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cli = PRAgentCLI()
    
    def test_parse_github_url_with_pr(self):
        """Test parsing GitHub URL with PR number."""
        url = "https://github.com/django/django/pull/20316"
        result = self.cli.parse_github_url(url)
        
        assert result is not None
        repo, pr_number = result
        assert repo == "django/django"
        assert pr_number == 20316
    
    def test_parse_github_url_without_pr(self):
        """Test parsing GitHub URL without PR number."""
        url = "https://github.com/facebook/react"
        result = self.cli.parse_github_url(url)
        
        assert result is not None
        repo, pr_number = result
        assert repo == "facebook/react"
        assert pr_number is None
    
    def test_parse_repo_name_only(self):
        """Test parsing repo name without URL."""
        url = "django/django"
        result = self.cli.parse_github_url(url)
        
        assert result is not None
        repo, pr_number = result
        assert repo == "django/django"
        assert pr_number is None
    
    def test_parse_repo_name_with_pr(self):
        """Test parsing repo name with PR in path format."""
        url = "django/django/pull/20316"
        result = self.cli.parse_github_url(url)
        
        assert result is not None
        repo, pr_number = result
        assert repo == "django/django"
        assert pr_number == 20316
    
    def test_parse_invalid_url(self):
        """Test parsing invalid URL."""
        url = "not-a-valid-url"
        result = self.cli.parse_github_url(url)
        
        assert result is None
    
    def test_parse_url_with_trailing_slash(self):
        """Test URL parsing handles trailing slashes."""
        url = "https://github.com/django/django/pull/20316/"
        result = self.cli.parse_github_url(url)
        
        assert result is not None
        repo, pr_number = result
        assert repo == "django/django"
        assert pr_number == 20316
    
    @patch('pr_agent.cli.requests.get')
    def test_check_server_status_running(self, mock_get):
        """Test server status check when server is running."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.cli.check_server_status()
        
        assert result is True
        mock_get.assert_called_once_with("http://localhost:8000/health", timeout=2)
    
    @patch('pr_agent.cli.requests.get')
    def test_check_server_status_not_running(self, mock_get):
        """Test server status check when server is not running."""
        mock_get.side_effect = Exception("Connection error")
        
        result = self.cli.check_server_status()
        
        assert result is False
    
    @patch('pr_agent.cli.requests.post')
    def test_analyze_pr_success(self, mock_post, capsys):
        """Test successful PR analysis."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "repo": "django/django",
            "pr_number": 20316,
            "summary": {
                "total_files": 1,
                "total_comments": 5,
                "statistics": {
                    "severity_counts": {
                        "critical": 0,
                        "high": 2,
                        "medium": 2,
                        "low": 1
                    }
                },
                "executive_summary": "Test summary",
                "recommendation": "APPROVE_WITH_SUGGESTIONS"
            },
            "provider": "groq",
            "cached": False
        }
        mock_post.return_value = mock_response
        
        result = self.cli.analyze_pr("django/django", 20316)
        
        assert result is True
        captured = capsys.readouterr()
        assert "django/django" in captured.out
        assert "20316" in captured.out
        assert "Test summary" in captured.out
    
    @patch('pr_agent.cli.requests.post')
    def test_analyze_pr_connection_error(self, mock_post, capsys):
        """Test PR analysis with connection error."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = self.cli.analyze_pr("django/django", 20316)
        
        assert result is False
        captured = capsys.readouterr()
        assert "Failed to connect" in captured.out
    
    @patch('pr_agent.cli.requests.post')
    def test_analyze_pr_api_error(self, mock_post, capsys):
        """Test PR analysis with API error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response
        
        result = self.cli.analyze_pr("django/django", 20316)
        
        assert result is False
        captured = capsys.readouterr()
        assert "failed with status 500" in captured.out
    
    @patch('pr_agent.cli.requests.post')
    def test_analyze_pr_markdown_format(self, mock_post, capsys):
        """Test PR analysis with markdown output."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "markdown": "# Test Markdown Output\n\nTest content"
        }
        mock_post.return_value = mock_response
        
        result = self.cli.analyze_pr("django/django", 20316, output_format="markdown")
        
        assert result is True
        captured = capsys.readouterr()
        assert "Test Markdown Output" in captured.out
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/analyze/markdown" in call_args[0][0]
    
    @patch('pr_agent.utils.github_client.GitHubClient.list_pull_requests')
    def test_list_and_select_pr_success(self, mock_list_prs, monkeypatch, capsys):
        """Test listing PRs and selecting one."""
        mock_list_prs.return_value = [
            {
                "number": 123,
                "title": "Fix bug",
                "state": "open",
                "user": {"login": "testuser"}
            },
            {
                "number": 124,
                "title": "Add feature",
                "state": "open",
                "user": {"login": "anotheruser"}
            }
        ]
        
        # Simulate user input
        monkeypatch.setattr('builtins.input', lambda _: '123')
        
        result = self.cli.list_and_select_pr("test/repo")
        
        assert result == 123
        captured = capsys.readouterr()
        assert "Fix bug" in captured.out
        assert "Add feature" in captured.out
    
    @patch('pr_agent.utils.github_client.GitHubClient.list_pull_requests')
    def test_list_and_select_pr_quit(self, mock_list_prs, monkeypatch, capsys):
        """Test quitting from PR selection."""
        mock_list_prs.return_value = [
            {
                "number": 123,
                "title": "Fix bug",
                "state": "open",
                "user": {"login": "testuser"}
            }
        ]
        
        # Simulate user quitting
        monkeypatch.setattr('builtins.input', lambda _: 'q')
        
        result = self.cli.list_and_select_pr("test/repo")
        
        assert result is None
    
    @patch('pr_agent.utils.github_client.GitHubClient.list_pull_requests')
    def test_list_and_select_pr_invalid_then_valid(self, mock_list_prs, monkeypatch, capsys):
        """Test invalid input followed by valid selection."""
        mock_list_prs.return_value = [
            {
                "number": 123,
                "title": "Fix bug",
                "state": "open",
                "user": {"login": "testuser"}
            }
        ]
        
        # Simulate invalid input then valid
        inputs = iter(['999', '123'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        
        result = self.cli.list_and_select_pr("test/repo")
        
        assert result == 123
        captured = capsys.readouterr()
        assert "not in the list" in captured.out
    
    @patch('pr_agent.utils.github_client.GitHubClient.list_pull_requests')
    def test_list_and_select_pr_no_prs(self, mock_list_prs, capsys):
        """Test when no PRs are found."""
        mock_list_prs.return_value = None
        
        result = self.cli.list_and_select_pr("test/repo")
        
        assert result is None
        captured = capsys.readouterr()
        assert "No open PRs found" in captured.out
    
    def test_print_analysis_result_complete(self, capsys):
        """Test printing complete analysis result."""
        result = {
            "repo": "django/django",
            "pr_number": 20316,
            "summary": {
                "total_files": 3,
                "total_comments": 10,
                "statistics": {
                    "severity_counts": {
                        "critical": 1,
                        "high": 3,
                        "medium": 4,
                        "low": 2
                    }
                },
                "executive_summary": "This PR introduces security concerns.",
                "recommendation": "BLOCK_MERGE"
            },
            "provider": "groq",
            "cached": True
        }
        
        self.cli._print_analysis_result(result)
        
        captured = capsys.readouterr()
        assert "django/django" in captured.out
        assert "20316" in captured.out
        assert "Files Analyzed: 3" in captured.out
        assert "Issues Found: 10" in captured.out
        assert "Critical: 1" in captured.out
        assert "High: 3" in captured.out
        assert "security concerns" in captured.out
        assert "Block Merge" in captured.out
        assert "Yes" in captured.out  # cached
    
    def test_print_analysis_result_minimal(self, capsys):
        """Test printing minimal analysis result."""
        result = {
            "repo": "test/repo",
            "pr_number": 1,
            "summary": {
                "total_files": 0,
                "total_comments": 0
            },
            "provider": "test",
            "cached": False
        }
        
        self.cli._print_analysis_result(result)
        
        captured = capsys.readouterr()
        assert "test/repo" in captured.out
        assert "Files Analyzed: 0" in captured.out
        assert "Issues Found: 0" in captured.out
        assert "No" in captured.out  # not cached


class TestGitHubClientListPRs:
    """Test GitHub client PR listing functionality."""
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_list_pull_requests_success(self, mock_get):
        """Test successful PR listing."""
        from pr_agent.utils.github_client import GitHubClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"number": 1, "title": "PR 1"},
            {"number": 2, "title": "PR 2"}
        ]
        mock_get.return_value = mock_response
        
        client = GitHubClient(token="test_token")
        result = client.list_pull_requests("test/repo", state="open", limit=20)
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["number"] == 1
        
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "test/repo/pulls" in call_args[0][0]
        assert call_args[1]["params"]["state"] == "open"
        assert call_args[1]["params"]["per_page"] == 20
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_list_pull_requests_error(self, mock_get):
        """Test PR listing with error."""
        from pr_agent.utils.github_client import GitHubClient
        from requests.exceptions import RequestException
        
        mock_get.side_effect = RequestException("API error")
        
        client = GitHubClient(token="test_token")
        result = client.list_pull_requests("test/repo")
        
        assert result is None
    
    @patch('pr_agent.utils.github_client.requests.get')
    def test_list_pull_requests_different_states(self, mock_get):
        """Test listing PRs with different states."""
        from pr_agent.utils.github_client import GitHubClient
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        client = GitHubClient(token="test_token")
        
        # Test different states
        for state in ["open", "closed", "all"]:
            client.list_pull_requests("test/repo", state=state)
            call_args = mock_get.call_args
            assert call_args[1]["params"]["state"] == state
