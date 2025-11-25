"""Style and readability analysis agent."""

import re
from typing import Any, Dict

from .base import BaseAgent, AgentResult, ReviewComment, Severity, Category


class StyleAgent(BaseAgent):
    """Agent focused on code style and readability."""
    
    STYLE_PATTERNS = {
        "long_line": {
            "check": lambda line: len(line) > 120,
            "message": "Line too long (>120 chars) - consider refactoring",
            "severity": Severity.LOW
        },
        "missing_docstring": {
            "pattern": r'^(def|class)\s+\w+.*:\s*$',
            "message": "Missing docstring - add documentation",
            "severity": Severity.LOW
        },
        "poor_naming": {
            "pattern": r'\b(x|y|z|tmp|temp|data)\b\s*=',
            "message": "Non-descriptive variable name - use meaningful names",
            "severity": Severity.LOW
        }
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(name="style", *args, **kwargs)
    
    def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """Analyze code for style issues."""
        code_snippet = context.get("code_snippet", "")
        file_path = context.get("file_path", "unknown")
        
        # Try LLM first
        if self.llm_adapter and not self.llm_adapter.is_fallback_mode:
            try:
                template_str = self.template_manager.get_template("style_readability_v1")
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
        """Rule-based style analysis."""
        comments = []
        lines = code_snippet.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Check line length
            if self.STYLE_PATTERNS["long_line"]["check"](line):
                comments.append(ReviewComment(
                    file=file_path,
                    line_start=line_num,
                    line_end=line_num,
                    severity=Severity.LOW,
                    category=Category.STYLE,
                    message=self.STYLE_PATTERNS["long_line"]["message"]
                ))
            
            # Check patterns
            for pattern_name, pattern_info in self.STYLE_PATTERNS.items():
                if "pattern" in pattern_info:
                    if re.search(pattern_info["pattern"], line):
                        comments.append(ReviewComment(
                            file=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            severity=pattern_info["severity"],
                            category=Category.STYLE,
                            message=pattern_info["message"]
                        ))
        
        return AgentResult(
            agent_name=self.name,
            comments=comments,
            metadata={"method": "rule_based"},
            fallback_used=True
        )
