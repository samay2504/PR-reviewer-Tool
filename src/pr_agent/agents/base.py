"""Base agent class and shared agent utilities."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils.logging import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Category(str, Enum):
    """Issue categories."""
    BUG = "BUG"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    STYLE = "STYLE"
    DOCUMENTATION = "DOCUMENTATION"
    BEST_PRACTICE = "BEST_PRACTICE"


class ReviewComment(BaseModel):
    """Structured review comment."""
    file: str
    line_start: int
    line_end: Optional[int] = None
    severity: Severity
    category: Category
    message: str
    suggestion_patch: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AgentResult(BaseModel):
    """Result from an agent's analysis."""
    agent_name: str
    comments: List[ReviewComment] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    fallback_used: bool = False


class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(
        self,
        name: str,
        llm_adapter: Optional[Any] = None,
        template_manager: Optional[Any] = None
    ):
        """
        Initialize agent.
        
        Args:
            name: Agent name
            llm_adapter: LLM adapter instance
            template_manager: Template manager instance
        """
        self.name = name
        self.llm_adapter = llm_adapter
        self.template_manager = template_manager
        self.logger = get_logger(f"pr_agent.agents.{name}")
    
    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """
        Analyze code and return review comments.
        
        Args:
            context: Analysis context
            
        Returns:
            AgentResult with comments
        """
        pass
    
    def _parse_llm_response(self, response: str) -> List[ReviewComment]:
        """
        Parse LLM JSON response into ReviewComment objects.
        
        Args:
            response: LLM response string
            
        Returns:
            List of ReviewComment objects
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_str = response.strip()
            
            # Handle empty responses
            if not json_str or json_str == "[]":
                return []
            
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Handle both array and single object
            if not isinstance(data, list):
                data = [data]
            
            # Empty array is valid - no issues found
            if len(data) == 0:
                return []
            
            comments = []
            for item in data:
                try:
                    # Normalize field names
                    comment_data = {
                        "file": item.get("file", "unknown"),
                        "line_start": item.get("line_start") or item.get("line", 0),
                        "line_end": item.get("line_end"),
                        "severity": item.get("severity", "MEDIUM").upper(),
                        "category": item.get("category", "BUG").upper(),
                        "message": item.get("message", ""),
                        "suggestion_patch": item.get("suggestion_patch") or item.get("suggestion")
                    }
                    
                    comment = ReviewComment(**comment_data)
                    comments.append(comment)
                except Exception as e:
                    self.logger.warning(f"Failed to parse comment item: {e}")
                    continue
            
            return comments
            
        except json.JSONDecodeError as e:
            # Only log as warning if response has content (not just empty)
            if response and response.strip():
                self.logger.warning(f"LLM returned non-JSON response, using fallback")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error parsing LLM response: {e}")
            return []
    
    def _create_fallback_result(
        self,
        message: str = "Analysis not available"
    ) -> AgentResult:
        """
        Create fallback result when LLM fails.
        
        Args:
            message: Error message
            
        Returns:
            AgentResult with fallback flag
        """
        return AgentResult(
            agent_name=self.name,
            comments=[],
            error=message,
            fallback_used=True
        )
