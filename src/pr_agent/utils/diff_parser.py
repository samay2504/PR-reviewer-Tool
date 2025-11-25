"""Diff parsing utilities for analyzing code changes."""

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FileChange:
    """Represents a change to a single file."""
    
    path: str
    old_path: Optional[str] = None
    change_type: str = "modified"  # added, deleted, modified, renamed
    additions: int = 0
    deletions: int = 0
    hunks: List['DiffHunk'] = None
    language: Optional[str] = None
    
    def __post_init__(self):
        if self.hunks is None:
            self.hunks = []


@dataclass
class DiffHunk:
    """Represents a single hunk (contiguous block of changes) in a diff."""
    
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str
    lines: List[str]
    
    def get_changed_line_numbers(self) -> List[int]:
        """Get list of line numbers that were changed (added or modified)."""
        changed_lines = []
        current_line = self.new_start
        
        for line in self.lines:
            if line.startswith('+') and not line.startswith('+++'):
                changed_lines.append(current_line)
                current_line += 1
            elif not line.startswith('-'):
                current_line += 1
        
        return changed_lines


class DiffParser:
    """Parser for Git-style unified diffs."""
    
    # File extension to language mapping
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'shell',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.sql': 'sql',
    }
    
    @staticmethod
    def compute_diff_hash(diff_text: str) -> str:
        """
        Compute SHA256 hash of diff text for caching.
        
        Args:
            diff_text: The diff text to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(diff_text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def detect_language(filepath: str) -> Optional[str]:
        """
        Detect programming language from file extension.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Language name or None
        """
        ext = '.' + filepath.rsplit('.', 1)[-1] if '.' in filepath else ''
        return DiffParser.LANGUAGE_MAP.get(ext.lower())
    
    @staticmethod
    def parse_unified_diff(diff_text: str) -> List[FileChange]:
        """
        Parse a unified diff into structured FileChange objects.
        
        Args:
            diff_text: Unified diff text
            
        Returns:
            List of FileChange objects
        """
        if not diff_text or not diff_text.strip():
            logger.warning("Empty diff provided")
            return []
        
        file_changes = []
        current_file = None
        current_hunk = None
        
        lines = diff_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # New file starts with 'diff --git'
            if line.startswith('diff --git'):
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)
                    current_hunk = None
                if current_file:
                    file_changes.append(current_file)
                
                # Parse file paths
                match = re.match(r'diff --git a/(.*?) b/(.*?)$', line)
                if match:
                    old_path, new_path = match.groups()
                    current_file = FileChange(
                        path=new_path,
                        old_path=old_path if old_path != new_path else None,
                        language=DiffParser.detect_language(new_path)
                    )
                else:
                    logger.warning(f"Could not parse diff header: {line}")
                    current_file = FileChange(path="unknown")
            
            # File mode changes
            elif line.startswith('new file mode'):
                if current_file:
                    current_file.change_type = 'added'
            elif line.startswith('deleted file mode'):
                if current_file:
                    current_file.change_type = 'deleted'
            elif line.startswith('rename from'):
                if current_file:
                    current_file.change_type = 'renamed'
            
            # Hunk header
            elif line.startswith('@@'):
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)
                
                # Parse hunk header: @@ -old_start,old_lines +new_start,new_lines @@
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)', line)
                if match:
                    old_start = int(match.group(1))
                    old_lines = int(match.group(2) or 1)
                    new_start = int(match.group(3))
                    new_lines = int(match.group(4) or 1)
                    header = match.group(5).strip()
                    
                    current_hunk = DiffHunk(
                        old_start=old_start,
                        old_lines=old_lines,
                        new_start=new_start,
                        new_lines=new_lines,
                        header=header,
                        lines=[]
                    )
            
            # Hunk content
            elif current_hunk is not None and (
                line.startswith('+') or line.startswith('-') or line.startswith(' ')
            ):
                current_hunk.lines.append(line)
                if current_file:
                    if line.startswith('+') and not line.startswith('+++'):
                        current_file.additions += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        current_file.deletions += 1
            
            i += 1
        
        # Add final file and hunk
        if current_file:
            if current_hunk:
                current_file.hunks.append(current_hunk)
            file_changes.append(current_file)
        
        logger.info(f"Parsed diff: {len(file_changes)} files changed")
        return file_changes
    
    @staticmethod
    def get_changed_files_summary(file_changes: List[FileChange]) -> Dict[str, any]:
        """
        Get summary statistics about changed files.
        
        Args:
            file_changes: List of FileChange objects
            
        Returns:
            Dictionary with summary statistics
        """
        total_additions = sum(f.additions for f in file_changes)
        total_deletions = sum(f.deletions for f in file_changes)
        
        languages = {}
        for fc in file_changes:
            if fc.language:
                languages[fc.language] = languages.get(fc.language, 0) + 1
        
        return {
            "total_files": len(file_changes),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "languages": languages,
            "files_by_type": {
                "added": sum(1 for f in file_changes if f.change_type == 'added'),
                "deleted": sum(1 for f in file_changes if f.change_type == 'deleted'),
                "modified": sum(1 for f in file_changes if f.change_type == 'modified'),
                "renamed": sum(1 for f in file_changes if f.change_type == 'renamed'),
            }
        }
    
    @staticmethod
    def extract_code_snippets(
        file_changes: List[FileChange],
        context_lines: int = 3
    ) -> Dict[str, List[Tuple[int, str]]]:
        """
        Extract code snippets from changes with context.
        
        Args:
            file_changes: List of FileChange objects
            context_lines: Number of context lines to include
            
        Returns:
            Dictionary mapping file paths to list of (line_number, snippet) tuples
        """
        snippets = {}
        
        for fc in file_changes:
            file_snippets = []
            
            for hunk in fc.hunks:
                # Get the actual changed lines
                snippet_lines = []
                current_line = hunk.new_start
                
                for line in hunk.lines:
                    if line.startswith('+'):
                        snippet_lines.append((current_line, line[1:]))
                        current_line += 1
                    elif not line.startswith('-'):
                        current_line += 1
                
                file_snippets.extend(snippet_lines)
            
            if file_snippets:
                snippets[fc.path] = file_snippets
        
        return snippets
