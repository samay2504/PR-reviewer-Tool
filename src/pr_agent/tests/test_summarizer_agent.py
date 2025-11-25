"""Tests for Summarizer Agent."""

import pytest
from pr_agent.agents.summarizer_agent import SummarizerAgent
from pr_agent.agents.base import AgentResult, ReviewComment


@pytest.fixture
def summarizer_agent():
    """Create summarizer agent without LLM (testing fallback logic)."""
    return SummarizerAgent(name="summarizer", llm_adapter=None, template_manager=None)


@pytest.fixture
def sample_agent_results():
    """Create sample agent results for testing."""
    return {
        "security": AgentResult(
            agent_name="security",
            comments=[
                ReviewComment(
                    file="app.py",
                    line_start=10,
                    line_end=12,
                    severity="CRITICAL",
                    category="SECURITY",
                    message="SQL injection vulnerability detected"
                ),
                ReviewComment(
                    file="utils.py",
                    line_start=45,
                    line_end=45,
                    severity="HIGH",
                    category="SECURITY",
                    message="Hardcoded API key found"
                )
            ],
            execution_time_ms=1200
        ),
        "performance": AgentResult(
            agent_name="performance",
            comments=[
                ReviewComment(
                    file="api.py",
                    line_start=100,
                    line_end=105,
                    severity="MEDIUM",
                    category="PERFORMANCE",
                    message="N+1 query detected"
                )
            ],
            execution_time_ms=800
        ),
        "style": AgentResult(
            agent_name="style",
            comments=[
                ReviewComment(
                    file="helpers.py",
                    line_start=20,
                    line_end=25,
                    severity="LOW",
                    category="STYLE",
                    message="Function lacks docstring"
                )
            ],
            execution_time_ms=500
        )
    }


@pytest.fixture
def empty_agent_results():
    """Create empty agent results."""
    return {
        "security": AgentResult(
            agent_name="security",
            comments=[],
            execution_time_ms=100
        )
    }


class TestSummarizerAgent:
    """Test summarizer agent functionality."""
    
    def test_summarizer_initialization(self):
        """Test basic initialization."""
        agent = SummarizerAgent(name="summarizer", llm_adapter=None, template_manager=None)
        assert agent is not None
    
    def test_calculate_statistics(self, summarizer_agent, sample_agent_results):
        """Test statistics calculation."""
        all_comments = []
        for agent_name, result in sample_agent_results.items():
            for comment in result.comments:
                comment_dict = comment.dict()
                comment_dict["agent"] = agent_name
                all_comments.append(comment_dict)
        
        stats = summarizer_agent._calculate_statistics(all_comments, sample_agent_results)
        
        assert stats["total_issues"] == 4
        assert stats["critical_count"] == 1
        assert stats["high_count"] == 1
        assert stats["medium_count"] == 1
        assert stats["low_count"] == 1
        assert stats["files_with_issues"] == 4
    
    def test_group_findings(self, summarizer_agent, sample_agent_results):
        """Test grouping findings by severity."""
        all_comments = []
        for agent_name, result in sample_agent_results.items():
            for comment in result.comments:
                comment_dict = comment.dict()
                comment_dict["agent"] = agent_name
                all_comments.append(comment_dict)
        
        grouped = summarizer_agent._group_findings(all_comments)
        
        assert len(grouped["critical"]) == 1
        assert len(grouped["high"]) == 1
        assert len(grouped["medium"]) == 1
        assert len(grouped["low"]) == 1
        assert "SECURITY" in grouped["by_category"]
        assert "PERFORMANCE" in grouped["by_category"]
    
    def test_get_recommendation_block_merge(self, summarizer_agent):
        """Test recommendation for blocking merge."""
        stats = {
            "critical_count": 2,
            "high_count": 1,
            "total_issues": 5
        }
        recommendation = summarizer_agent._get_recommendation(stats)
        assert recommendation == "BLOCK_MERGE"
    
    def test_get_recommendation_request_changes(self, summarizer_agent):
        """Test recommendation for requesting changes."""
        stats = {
            "critical_count": 0,
            "high_count": 5,
            "total_issues": 10
        }
        recommendation = summarizer_agent._get_recommendation(stats)
        assert recommendation == "REQUEST_CHANGES"
    
    def test_get_recommendation_approve(self, summarizer_agent):
        """Test recommendation for approval."""
        stats = {
            "critical_count": 0,
            "high_count": 0,
            "total_issues": 0
        }
        recommendation = summarizer_agent._get_recommendation(stats)
        assert recommendation == "APPROVE"
    
    def test_get_recommendation_approve_with_suggestions(self, summarizer_agent):
        """Test recommendation for approval with suggestions."""
        stats = {
            "critical_count": 0,
            "high_count": 0,
            "total_issues": 3
        }
        recommendation = summarizer_agent._get_recommendation(stats)
        assert recommendation == "APPROVE_WITH_SUGGESTIONS"
    
    def test_summarize_with_findings(self, summarizer_agent, sample_agent_results):
        """Test full summarization with findings."""
        file_changes = []  # Mock file changes
        
        summary = summarizer_agent.summarize(sample_agent_results, file_changes)
        
        assert "statistics" in summary
        assert "grouped_findings" in summary
        assert "insights" in summary
        assert "recommendation" in summary
        
        assert summary["statistics"]["total_issues"] == 4
        assert summary["recommendation"] == "BLOCK_MERGE"  # Has critical issue
    
    def test_summarize_with_no_findings(self, summarizer_agent, empty_agent_results):
        """Test summarization with no findings."""
        file_changes = []
        
        summary = summarizer_agent.summarize(empty_agent_results, file_changes)
        
        assert summary["statistics"]["total_issues"] == 0
        assert summary["recommendation"] == "APPROVE"
    
    def test_get_top_problematic_files(self, summarizer_agent):
        """Test getting top problematic files."""
        file_counts = {
            "file1.py": 5,
            "file2.py": 3,
            "file3.py": 8,
            "file4.py": 1
        }
        
        top_files = summarizer_agent._get_top_problematic_files(file_counts, 2)
        
        assert len(top_files) == 2
        assert top_files[0] == ("file3.py", 8)
        assert top_files[1] == ("file1.py", 5)
    
    def test_build_template_insights(self, summarizer_agent):
        """Test template-based insights generation."""
        context = {
            "total_files": 5,
            "total_issues": 10,
            "critical_count": 2,
            "high_count": 3,
            "category_breakdown": {"SECURITY": 5, "PERFORMANCE": 3, "STYLE": 2},
            "top_files": [("app.py", 5), ("api.py", 3)]
        }
        
        insights = summarizer_agent._build_template_insights(context)
        
        assert "Blocking Issues Found" in insights or "critical" in insights.lower()
        assert "app.py" in insights
    
    def test_generate_markdown_summary(self, summarizer_agent, sample_agent_results):
        """Test markdown summary generation."""
        file_changes = []
        summary = summarizer_agent.summarize(sample_agent_results, file_changes)
        
        markdown = summarizer_agent.generate_markdown_summary(
            summary,
            repo="test/repo",
            pr_number=123
        )
        
        assert "# 🤖 AI Code Review Summary" in markdown
        assert "test/repo" in markdown
        assert "#123" in markdown
        assert "## 📊 Statistics" in markdown
        assert "BLOCKING" in markdown  # Has critical issues
        assert "4" in markdown  # Total issues
    
    def test_generate_markdown_summary_no_repo(self, summarizer_agent, empty_agent_results):
        """Test markdown summary without repo info."""
        file_changes = []
        summary = summarizer_agent.summarize(empty_agent_results, file_changes)
        
        markdown = summarizer_agent.generate_markdown_summary(summary)
        
        assert "# 🤖 AI Code Review Summary" in markdown
        assert "APPROVED" in markdown
        assert "0" in markdown  # Total issues
    
    def test_severity_counts_in_statistics(self, summarizer_agent, sample_agent_results):
        """Test that severity counts are correct in statistics."""
        all_comments = []
        for agent_name, result in sample_agent_results.items():
            for comment in result.comments:
                comment_dict = comment.dict()
                comment_dict["agent"] = agent_name
                all_comments.append(comment_dict)
        
        stats = summarizer_agent._calculate_statistics(all_comments, sample_agent_results)
        
        # Verify each severity level
        assert stats["by_severity"]["CRITICAL"] == 1
        assert stats["by_severity"]["HIGH"] == 1
        assert stats["by_severity"]["MEDIUM"] == 1
        assert stats["by_severity"]["LOW"] == 1
    
    def test_category_counts_in_statistics(self, summarizer_agent, sample_agent_results):
        """Test that category counts are correct."""
        all_comments = []
        for agent_name, result in sample_agent_results.items():
            for comment in result.comments:
                comment_dict = comment.dict()
                comment_dict["agent"] = agent_name
                all_comments.append(comment_dict)
        
        stats = summarizer_agent._calculate_statistics(all_comments, sample_agent_results)
        
        assert stats["by_category"]["SECURITY"] == 2
        assert stats["by_category"]["PERFORMANCE"] == 1
        assert stats["by_category"]["STYLE"] == 1
