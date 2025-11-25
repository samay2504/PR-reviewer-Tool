"""Performance analysis agent."""

import re
from typing import Any, Dict

from .base import BaseAgent, AgentResult, ReviewComment, Severity, Category
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PerformanceAgent(BaseAgent):
    """Agent focused on performance optimization."""
    
    PERFORMANCE_PATTERNS = {
        "nested_loop": {
            "pattern": r'for\s+.*:\s*\n\s+for\s+',
            "message": "Nested loops detected - consider algorithmic optimization",
            "severity": Severity.MEDIUM
        },
        "repeated_db_call": {
            "pattern": r'(execute|query|find|get)\s*\(.*\n.*for\s+',
            "message": "Possible repeated database calls in loop",
            "severity": Severity.HIGH
        },
        "large_copy": {
            "pattern": r'\.copy\(\)|list\(|dict\(',
            "message": "Large data structure copy - consider references or generators",
            "severity": Severity.MEDIUM
        }
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(name="performance", *args, **kwargs)
    
    def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """Analyze code for performance issues."""
        code_snippet = context.get("code_snippet", "")
        file_path = context.get("file_path", "unknown")
        
        # Try LLM first
        if self.llm_adapter and not self.llm_adapter.is_fallback_mode:
            try:
                template_str = self.template_manager.get_template("performance_analysis_v1")
                if template_str:
                    chain = self.llm_adapter.create_chain(template_str)
                    response = self.llm_adapter.run_chain(chain, context)
                    if response:
                        comments = self._parse_llm_response(response)
                        return AgentResult(
                            agent_name=self.name,
                            comments=comments,
                            metadata={"method": "llm"}
                        )
            except Exception as e:
                self.logger.warning(f"LLM analysis failed: {e}")
        
        # Fallback to rules
        return self._rule_based_analysis(code_snippet, file_path)
    
    def _rule_based_analysis(self, code_snippet: str, file_path: str) -> AgentResult:
        """Rule-based performance analysis."""
        comments = []
        lines = code_snippet.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            for pattern_name, pattern_info in self.PERFORMANCE_PATTERNS.items():
                if re.search(pattern_info["pattern"], line):
                    comments.append(ReviewComment(
                        file=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        severity=pattern_info["severity"],
                        category=Category.PERFORMANCE,
                        message=pattern_info["message"]
                    ))
        
        return AgentResult(
            agent_name=self.name,
            comments=comments,
            metadata={"method": "rule_based"},
            fallback_used=True
        )
