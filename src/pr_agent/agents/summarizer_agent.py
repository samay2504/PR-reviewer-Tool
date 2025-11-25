"""Summarizer Agent - Aggregates findings from all agents into actionable summary."""

from typing import Dict, Any, List
from collections import defaultdict

from .base import BaseAgent, AgentResult, ReviewComment
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SummarizerAgent(BaseAgent):
    """
    Agent that aggregates findings from all other agents and generates
    an executive summary with actionable insights.
    """
    
    def analyze(self, context: Dict[str, Any]) -> AgentResult:
        """
        Not used for SummarizerAgent - use summarize() instead.
        This is here to satisfy the BaseAgent interface.
        """
        return AgentResult(
            agent_name="summarizer",
            comments=[],
            execution_time_ms=0
        )
    
    def summarize(
        self,
        all_results: Dict[str, AgentResult],
        file_changes: List[Any]
    ) -> Dict[str, Any]:
        """
        Create comprehensive summary of all agent findings.
        
        Args:
            all_results: Dictionary mapping agent names to their results
            file_changes: List of FileChange objects
            
        Returns:
            Dictionary with summary statistics and insights
        """
        logger.info("Generating summary from all agent results")
        
        # Aggregate all comments
        all_comments = []
        for agent_name, result in all_results.items():
            for comment in result.comments:
                comment_dict = comment.dict() if hasattr(comment, 'dict') else comment
                if isinstance(comment_dict, dict):
                    comment_dict["agent"] = agent_name
                all_comments.append(comment_dict)
        
        # Calculate statistics
        stats = self._calculate_statistics(all_comments, all_results)
        
        # Group findings
        grouped = self._group_findings(all_comments)
        
        # Generate insights using LLM
        insights = self._generate_insights(stats, grouped, file_changes)
        
        return {
            "statistics": stats,
            "grouped_findings": grouped,
            "insights": insights,
            "recommendation": self._get_recommendation(stats)
        }
    
    def _calculate_statistics(
        self,
        comments: List[Dict[str, Any]],
        agent_results: Dict[str, AgentResult]
    ) -> Dict[str, Any]:
        """Calculate summary statistics."""
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        file_counts = defaultdict(int)
        agent_comment_counts = defaultdict(int)
        
        for comment in comments:
            if isinstance(comment, dict):
                severity_counts[comment.get("severity", "UNKNOWN")] += 1
                category_counts[comment.get("category", "UNKNOWN")] += 1
                file_counts[comment.get("file", "UNKNOWN")] += 1
                agent_comment_counts[comment.get("agent", "UNKNOWN")] += 1
        
        # Calculate fallback usage
        fallback_agents = [
            name for name, result in agent_results.items()
            if hasattr(result, 'fallback_used') and result.fallback_used
        ]
        
        return {
            "total_issues": len(comments),
            "by_severity": dict(severity_counts),
            "by_category": dict(category_counts),
            "by_file": dict(file_counts),
            "by_agent": dict(agent_comment_counts),
            "critical_count": severity_counts.get("CRITICAL", 0),
            "high_count": severity_counts.get("HIGH", 0),
            "medium_count": severity_counts.get("MEDIUM", 0),
            "low_count": severity_counts.get("LOW", 0),
            "files_with_issues": len(file_counts),
            "agents_used_fallback": fallback_agents
        }
    
    def _group_findings(self, comments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by severity and category."""
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "by_category": defaultdict(list)
        }
        
        for comment in comments:
            if not isinstance(comment, dict):
                continue
                
            severity = comment.get("severity", "UNKNOWN").lower()
            category = comment.get("category", "UNKNOWN")
            
            if severity in grouped:
                grouped[severity].append(comment)
            
            grouped["by_category"][category].append(comment)
        
        # Convert defaultdict to regular dict for JSON serialization
        grouped["by_category"] = dict(grouped["by_category"])
        
        return grouped
    
    def _generate_insights(
        self,
        stats: Dict[str, Any],
        grouped: Dict[str, Any],
        file_changes: List[Any]
    ) -> str:
        """Generate AI-powered insights using LLM."""
        try:
            # Build context for LLM
            context = {
                "total_files": len(file_changes),
                "total_issues": stats["total_issues"],
                "critical_count": stats["critical_count"],
                "high_count": stats["high_count"],
                "severity_breakdown": stats["by_severity"],
                "category_breakdown": stats["by_category"],
                "top_files": self._get_top_problematic_files(stats["by_file"], 5)
            }
            
            # Try to use template if available
            if self.template_manager:
                template = self.template_manager.get_template("summarizer_insights_v1")
                if template:
                    prompt = template.format(**context)
                else:
                    prompt = self._build_default_prompt(context)
            else:
                prompt = self._build_default_prompt(context)
            
            # Get LLM insights
            if self.llm_adapter:
                insights = self.llm_adapter.invoke(prompt)
                if insights:
                    return insights
            
            # Fallback to template-based insights
            return self._build_template_insights(context)
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return self._build_template_insights(context)
    
    def _build_default_prompt(self, context: Dict[str, Any]) -> str:
        """Build default prompt when template is not available."""
        return f"""You are a senior code reviewer analyzing a pull request. Generate actionable insights based on these findings:

Total Files Changed: {context['total_files']}
Total Issues Found: {context['total_issues']}

Severity Breakdown:
- Critical: {context['critical_count']}
- High: {context['high_count']}

Categories: {', '.join(context['category_breakdown'].keys())}

Top Problematic Files:
{chr(10).join([f"- {file} ({count} issues)" for file, count in context['top_files']])}

Provide:
1. Overall assessment (1-2 sentences)
2. Top 3 priorities to address
3. Recommendation for merge readiness

Be concise and actionable."""
    
    def _build_template_insights(self, context: Dict[str, Any]) -> str:
        """Build template-based insights as fallback."""
        critical = context['critical_count']
        high = context['high_count']
        total = context['total_issues']
        
        if critical > 0:
            assessment = f"⚠️ **Blocking Issues Found**: {critical} critical issue(s) must be resolved before merge."
        elif high > 5:
            assessment = f"⚠️ **Multiple High-Priority Issues**: {high} high-severity issues require attention."
        elif total > 20:
            assessment = f"📊 **Large Change Set**: {total} issues across {context['total_files']} files. Consider breaking into smaller PRs."
        elif total == 0:
            assessment = "✅ **Clean Code**: No issues detected. Code follows best practices."
        else:
            assessment = f"✓ **Minor Issues Only**: {total} low-priority suggestions for improvement."
        
        # Build priorities
        priorities = []
        categories = sorted(
            context['category_breakdown'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        for i, (category, count) in enumerate(categories, 1):
            priorities.append(f"{i}. Address {count} {category.lower()} issue(s)")
        
        if not priorities:
            priorities = ["No critical issues to address"]
        
        return f"""{assessment}

**Top Priorities:**
{chr(10).join(priorities)}

**Most Affected Files:**
{chr(10).join([f"- `{file}` ({count} issues)" for file, count in context['top_files'][:3]])}"""
    
    def _get_top_problematic_files(
        self,
        file_counts: Dict[str, int],
        limit: int = 5
    ) -> List[tuple]:
        """Get top N files with most issues."""
        return sorted(
            file_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
    
    def _get_recommendation(self, stats: Dict[str, Any]) -> str:
        """Get merge recommendation based on statistics."""
        critical = stats["critical_count"]
        high = stats["high_count"]
        total = stats["total_issues"]
        
        if critical > 0:
            return "BLOCK_MERGE"
        elif high > 3:
            return "REQUEST_CHANGES"
        elif total > 15:
            return "COMMENT"
        elif total > 0:
            return "APPROVE_WITH_SUGGESTIONS"
        else:
            return "APPROVE"
    
    def generate_markdown_summary(
        self,
        summary: Dict[str, Any],
        repo: str = None,
        pr_number: int = None
    ) -> str:
        """
        Generate a markdown-formatted summary for posting as PR comment.
        
        Args:
            summary: Summary dictionary from summarize()
            repo: Repository name
            pr_number: PR number
            
        Returns:
            Markdown-formatted summary
        """
        stats = summary["statistics"]
        insights = summary["insights"]
        recommendation = summary["recommendation"]
        
        # Build header
        if repo and pr_number:
            header = f"# 🤖 AI Code Review Summary\n**Repository:** `{repo}` | **PR:** #{pr_number}\n\n"
        else:
            header = "# 🤖 AI Code Review Summary\n\n"
        
        # Build status badge
        badges = {
            "APPROVE": "✅ **APPROVED**",
            "APPROVE_WITH_SUGGESTIONS": "✓ **APPROVED** (with minor suggestions)",
            "COMMENT": "💬 **COMMENTED**",
            "REQUEST_CHANGES": "⚠️ **CHANGES REQUESTED**",
            "BLOCK_MERGE": "🚫 **BLOCKING** - Critical issues found"
        }
        status = badges.get(recommendation, "📊 **REVIEWED**")
        
        # Build statistics section
        stats_section = f"""## 📊 Statistics

| Metric | Count |
|--------|-------|
| Total Issues | {stats['total_issues']} |
| 🔴 Critical | {stats['critical_count']} |
| 🟠 High | {stats['high_count']} |
| 🟡 Medium | {stats['medium_count']} |
| 🟢 Low | {stats['low_count']} |
| Files Affected | {stats['files_with_issues']} |

"""
        
        # Build category breakdown
        if stats['by_category']:
            category_section = "### Issues by Category\n"
            for category, count in sorted(
                stats['by_category'].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                category_section += f"- **{category}**: {count}\n"
            category_section += "\n"
        else:
            category_section = ""
        
        # Build insights section
        insights_section = f"""## 💡 Key Insights

{insights}

"""
        
        # Build footer
        footer = f"""---
**Recommendation:** {status}

<sub>Generated by PR Review Agent | Powered by AI</sub>"""
        
        return header + stats_section + category_section + insights_section + footer
