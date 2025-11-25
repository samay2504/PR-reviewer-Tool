"""Tests for diff parser."""

import pytest

from pr_agent.utils.diff_parser import DiffParser, FileChange


def test_compute_diff_hash():
    """Test diff hash computation."""
    diff1 = "some diff content"
    diff2 = "some diff content"
    diff3 = "different content"
    
    hash1 = DiffParser.compute_diff_hash(diff1)
    hash2 = DiffParser.compute_diff_hash(diff2)
    hash3 = DiffParser.compute_diff_hash(diff3)
    
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64  # SHA256 hex length


def test_detect_language():
    """Test language detection from file paths."""
    assert DiffParser.detect_language("test.py") == "python"
    assert DiffParser.detect_language("test.js") == "javascript"
    assert DiffParser.detect_language("test.go") == "go"
    assert DiffParser.detect_language("test.unknown") is None


def test_parse_unified_diff(sample_diff):
    """Test parsing of unified diff."""
    file_changes = DiffParser.parse_unified_diff(sample_diff)
    
    assert len(file_changes) == 1
    assert file_changes[0].path == "src/example.py"
    assert file_changes[0].language == "python"
    assert file_changes[0].additions > 0
    assert file_changes[0].deletions > 0
    assert len(file_changes[0].hunks) > 0


def test_parse_empty_diff():
    """Test parsing empty diff."""
    file_changes = DiffParser.parse_unified_diff("")
    assert len(file_changes) == 0
    
    file_changes = DiffParser.parse_unified_diff("   ")
    assert len(file_changes) == 0


def test_get_changed_files_summary(sample_diff):
    """Test changed files summary."""
    file_changes = DiffParser.parse_unified_diff(sample_diff)
    summary = DiffParser.get_changed_files_summary(file_changes)
    
    assert summary["total_files"] == 1
    assert summary["total_additions"] > 0
    assert summary["total_deletions"] > 0
    assert "python" in summary["languages"]


def test_extract_code_snippets(sample_diff):
    """Test code snippet extraction."""
    file_changes = DiffParser.parse_unified_diff(sample_diff)
    snippets = DiffParser.extract_code_snippets(file_changes)
    
    assert "src/example.py" in snippets
    assert len(snippets["src/example.py"]) > 0


def test_hunk_changed_line_numbers(sample_diff):
    """Test getting changed line numbers from hunks."""
    file_changes = DiffParser.parse_unified_diff(sample_diff)
    
    for fc in file_changes:
        for hunk in fc.hunks:
            changed_lines = hunk.get_changed_line_numbers()
            assert isinstance(changed_lines, list)
            assert all(isinstance(line, int) for line in changed_lines)
