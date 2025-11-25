"""Tests for security agent."""

import pytest

from pr_agent.agents import SecurityAgent, Severity, Category


def test_security_agent_rule_based(sample_code):
    """Test rule-based security analysis."""
    agent = SecurityAgent(llm_adapter=None, template_manager=None)
    
    context = {
        "code_snippet": sample_code,
        "file_path": "test.py",
        "language": "python"
    }
    
    result = agent.analyze(context)
    
    assert result.agent_name == "security"
    assert result.fallback_used  # No LLM, so fallback
    assert len(result.comments) > 0
    
    # Check for hardcoded secret detection
    secret_comments = [c for c in result.comments if "secret" in c.message.lower() or "hardcoded" in c.message.lower()]
    assert len(secret_comments) > 0, f"Expected secret detection, got comments: {[c.message for c in result.comments]}"
    
    # Check for SQL injection detection
    sql_comments = [c for c in result.comments if "sql" in c.message.lower() or "injection" in c.message.lower()]
    assert len(sql_comments) > 0, f"Expected SQL injection detection, got comments: {[c.message for c in result.comments]}"


def test_security_patterns():
    """Test security pattern matching."""
    patterns = SecurityAgent.SECURITY_PATTERNS
    
    assert "hardcoded_secret" in patterns
    assert "sql_injection" in patterns
    assert "command_injection" in patterns
    assert "eval_usage" in patterns
    
    # All patterns should have required fields
    for pattern in patterns.values():
        assert "pattern" in pattern
        assert "message" in pattern
        assert "severity" in pattern
