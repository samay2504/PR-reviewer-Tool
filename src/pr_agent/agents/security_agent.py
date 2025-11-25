"""Security analysis agent."""

import re
from typing import Any, Dict, List

from .base import BaseAgent, AgentResult, ReviewComment, Severity, Category
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SecurityAgent(BaseAgent):
    """Agent focused on security vulnerability detection."""
    
    # Security patterns to detect (rule-based fallback)
    SECURITY_PATTERNS = {
        "hardcoded_secret": {
            "pattern": r'(password|secret|api_key|token|auth)\s*=\s*["\'][\w\-_+=]{8,}["\']',
            "message": "Potential hardcoded secret detected",
            "severity": Severity.CRITICAL
        },
        "sql_injection": {
            "pattern": r'(execute|query|cursor\.execute).*["\'].*%s.*["\']|SELECT.*FROM.*WHERE.*["\'].*%.*["\']',
            "message": "Potential SQL injection vulnerability - use parameterized queries",
            "severity": Severity.HIGH
        },
        "command_injection": {
            "pattern": r'(os\.system|subprocess\.(call|run|Popen))\s*\(.*\+.*\)',
            "message": "Potential command injection - avoid string concatenation with shell commands",
            "severity": Severity.HIGH
        },
        "path_traversal": {
            "pattern": r'open\s*\([^)]*\+[^)]*\)',
            "message": "Potential path traversal - validate and sanitize file paths",
            "severity": Severity.MEDIUM
        },
        "eval_usage": {
            "pattern": r'\beval\s*\(',
            "message": "Usage of eval() is dangerous - consider safer alternatives",
            "severity": Severity.HIGH
        },
        "pickle_unsafe": {
            "pattern": r'pickle\.loads?\s*\(',
            "message": "Pickle deserialization can be unsafe - validate data source",
            "severity": Severity.MEDIUM
        }
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(name="security", *args, **kwargs)
    
    def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """
        Analyze code for security vulnerabilities.
        
        Args:
            context: Analysis context with code_snippet, file_path, language
            
        Returns:
            AgentResult with security findings
        """
        code_snippet = context.get("code_snippet", "")
        file_path = context.get("file_path", "unknown")
        language = context.get("language", "unknown")
        
        self.logger.info(f"Security analysis for {file_path}")
        
        # Try LLM-based analysis first
        if self.llm_adapter and not self.llm_adapter.is_fallback_mode:
            llm_result = self._llm_analysis(context)
            if llm_result and llm_result.comments:
                return llm_result
        
        # Fall back to rule-based analysis
        return self._rule_based_analysis(code_snippet, file_path)
    
    def _llm_analysis(self, context: Dict[str, Any]) -> AgentResult:
        """
        LLM-based security analysis.
        
        Args:
            context: Analysis context
            
        Returns:
            AgentResult
        """
        try:
            template_str = self.template_manager.get_template("security_analysis_v1")
            if not template_str:
                self.logger.warning("Security template not found")
                return self._create_fallback_result("Template not available")
            
            # Create and run chain
            chain = self.llm_adapter.create_chain(template_str)
            response = self.llm_adapter.run_chain(chain, context)
            
            if not response:
                return self._create_fallback_result("LLM returned no response")
            
            # Parse response
            comments = self._parse_llm_response(response)
            
            return AgentResult(
                agent_name=self.name,
                comments=comments,
                metadata={"method": "llm", "template": "security_analysis_v1"}
            )
            
        except Exception as e:
            self.logger.error(f"LLM security analysis failed: {e}")
            return self._create_fallback_result(str(e))
    
    def _rule_based_analysis(
        self,
        code_snippet: str,
        file_path: str
    ) -> AgentResult:
        """
        Rule-based security analysis using regex patterns.
        
        Args:
            code_snippet: Code to analyze
            file_path: Path to file
            
        Returns:
            AgentResult with detected issues
        """
        comments = []
        lines = code_snippet.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            for pattern_name, pattern_info in self.SECURITY_PATTERNS.items():
                if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                    comment = ReviewComment(
                        file=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        severity=pattern_info["severity"],
                        category=Category.SECURITY,
                        message=pattern_info["message"],
                        suggestion_patch=None
                    )
                    comments.append(comment)
                    self.logger.debug(f"Security issue found: {pattern_name} at line {line_num}")
        
        return AgentResult(
            agent_name=self.name,
            comments=comments,
            metadata={"method": "rule_based", "patterns_checked": len(self.SECURITY_PATTERNS)},
            fallback_used=True
        )
