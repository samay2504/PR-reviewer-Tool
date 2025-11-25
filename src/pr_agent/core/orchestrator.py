"""Core orchestrator for multi-agent PR analysis."""

import asyncio
import hashlib
import uuid
from typing import Any, Dict, List, Optional

from ..agents import SecurityAgent, PerformanceAgent, StyleAgent, SummarizerAgent, AgentResult
from ..cache import CacheClient, CacheKeys
from ..llm import create_llm_adapter
from ..templates import TemplateManager
from ..utils.config import Settings
from ..utils.diff_parser import DiffParser, FileChange
from ..utils.github_client import GitHubClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisRequest:
    """Represents an analysis request."""
    
    def __init__(
        self,
        repo: Optional[str] = None,
        pr_number: Optional[int] = None,
        diff_text: Optional[str] = None,
        use_cache: bool = True
    ):
        self.request_id = str(uuid.uuid4())
        self.repo = repo
        self.pr_number = pr_number
        self.diff_text = diff_text
        self.use_cache = use_cache
        self.diff_hash = DiffParser.compute_diff_hash(diff_text) if diff_text else None


class AnalysisResult:
    """Represents the final analysis result."""
    
    def __init__(
        self,
        request_id: str,
        repo: Optional[str],
        pr_number: Optional[int],
        diff_hash: str,
        file_changes: List[FileChange],
        agent_results: Dict[str, AgentResult],
        cached: bool = False,
        provider: str = "unknown",
        summary: Optional[Dict[str, Any]] = None
    ):
        self.request_id = request_id
        self.repo = repo
        self.pr_number = pr_number
        self.diff_hash = diff_hash
        self.file_changes = file_changes
        self.agent_results = agent_results
        self.cached = cached
        self.provider = provider
        self.summary = summary or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        # Aggregate all comments from agents
        all_comments = []
        for agent_name, result in self.agent_results.items():
            for comment in result.comments:
                comment_dict = comment.dict()
                comment_dict["agent"] = agent_name
                all_comments.append(comment_dict)
        
        # Include executive summary if available
        base_summary = {
            "total_comments": len(all_comments),
            "total_files": len(self.file_changes),
            "agents_run": list(self.agent_results.keys()),
            "fallback_agents": [
                name for name, result in self.agent_results.items()
                if result.fallback_used
            ]
        }
        
        # Merge with executive summary from SummarizerAgent
        if self.summary:
            base_summary.update({
                "executive_summary": self.summary.get("insights", ""),
                "recommendation": self.summary.get("recommendation", "COMMENT"),
                "statistics": self.summary.get("statistics", {})
            })
        
        return {
            "request_id": self.request_id,
            "repo": self.repo,
            "pr_number": self.pr_number,
            "diff_hash": self.diff_hash,
            "comments": all_comments,
            "summary": base_summary,
            "provider": self.provider,
            "cached": self.cached
        }


class Orchestrator:
    """
    Main orchestrator that coordinates multi-agent PR analysis.
    """
    
    def __init__(
        self,
        settings: Settings,
        cache_client: Optional[CacheClient] = None,
        template_manager: Optional[TemplateManager] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            settings: Application settings
            cache_client: Cache client instance
            template_manager: Template manager instance
        """
        self.settings = settings
        self.cache_client = cache_client
        self.template_manager = template_manager
        
        # Initialize GitHub client
        self.github_client = GitHubClient(token=settings.github_token)
        
        # Initialize LLM adapter
        llm_config = settings.get_llm_config()
        self.llm_adapter = create_llm_adapter(llm_config)
        
        # Initialize agents
        self.agents = self._initialize_agents()
        
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all agents."""
        agents = {}
        
        try:
            agents["security"] = SecurityAgent(
                llm_adapter=self.llm_adapter,
                template_manager=self.template_manager
            )
        except Exception as e:
            logger.error(f"Failed to initialize SecurityAgent: {e}")
        
        try:
            agents["performance"] = PerformanceAgent(
                llm_adapter=self.llm_adapter,
                template_manager=self.template_manager
            )
        except Exception as e:
            logger.error(f"Failed to initialize PerformanceAgent: {e}")
        
        try:
            agents["style"] = StyleAgent(
                llm_adapter=self.llm_adapter,
                template_manager=self.template_manager
            )
        except Exception as e:
            logger.error(f"Failed to initialize StyleAgent: {e}")
        
        try:
            agents["summarizer"] = SummarizerAgent(
                name="summarizer",
                llm_adapter=self.llm_adapter,
                template_manager=self.template_manager
            )
        except Exception as e:
            logger.error(f"Failed to initialize SummarizerAgent: {e}")
        
        return agents
    
    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Analyze a PR or diff.
        
        Args:
            request: Analysis request
            
        Returns:
            AnalysisResult
        """
        logger.info(f"Starting analysis for request {request.request_id}")
        
        # Fetch diff from GitHub if repo and PR number provided
        if request.repo and request.pr_number and not request.diff_text:
            logger.info(f"Fetching diff from GitHub: {request.repo} PR #{request.pr_number}")
            request.diff_text = self.github_client.fetch_pr_diff(request.repo, request.pr_number)
            
            if not request.diff_text:
                logger.error("Failed to fetch diff from GitHub")
                return AnalysisResult(
                    request_id=request.request_id,
                    repo=request.repo,
                    pr_number=request.pr_number,
                    diff_hash="",
                    file_changes=[],
                    agent_results={},
                    provider=self.llm_adapter.get_provider_info().get("provider", "unknown")
                )
            
            # Compute diff hash after fetching
            request.diff_hash = DiffParser.compute_diff_hash(request.diff_text)
            logger.info(f"Fetched diff successfully, hash: {request.diff_hash[:16]}...")
        
        # Check cache first
        if request.use_cache and self.cache_client and request.diff_hash:
            cached_result = self._check_cache(request)
            if cached_result:
                logger.info("Returning cached result")
                return cached_result
        
        # Parse diff
        file_changes = DiffParser.parse_unified_diff(request.diff_text or "")
        if not file_changes:
            logger.warning("No file changes found in diff")
            return AnalysisResult(
                request_id=request.request_id,
                repo=request.repo,
                pr_number=request.pr_number,
                diff_hash=request.diff_hash or "",
                file_changes=[],
                agent_results={},
                provider=self.llm_adapter.get_provider_info().get("provider", "unknown")
            )
        
        # Run agents concurrently (excluding summarizer)
        agent_results = await self._run_agents(file_changes, request.request_id)
        
        # Generate executive summary using SummarizerAgent
        executive_summary = {}
        if "summarizer" in self.agents:
            try:
                summarizer = self.agents["summarizer"]
                executive_summary = summarizer.summarize(agent_results, file_changes)
                logger.info("Generated executive summary")
            except Exception as e:
                logger.error(f"Failed to generate summary: {e}")
        
        # Create result
        result = AnalysisResult(
            request_id=request.request_id,
            repo=request.repo,
            pr_number=request.pr_number,
            diff_hash=request.diff_hash or "",
            file_changes=file_changes,
            agent_results=agent_results,
            provider=self.llm_adapter.get_provider_info().get("provider", "unknown"),
            summary=executive_summary
        )
        
        # Cache result
        if self.cache_client:
            self._cache_result(request, result)
        
        return result
    
    async def _run_agents(
        self,
        file_changes: List[FileChange],
        request_id: str
    ) -> Dict[str, AgentResult]:
        """
        Run all agents concurrently on file changes.
        
        Args:
            file_changes: List of file changes
            request_id: Request ID
            
        Returns:
            Dictionary of agent results
        """
        tasks = []
        agent_names = []
        
        for agent_name, agent in self.agents.items():
            # Skip summarizer agent - it runs after all other agents
            if agent_name == "summarizer":
                continue
                
            for file_change in file_changes:
                # Skip binary files or files without content
                if not file_change.hunks:
                    continue
                
                # Build context for agent
                code_snippet = "\n".join([
                    line for hunk in file_change.hunks
                    for line in hunk.lines
                ])
                
                context = {
                    "code_snippet": code_snippet,
                    "file_path": file_change.path,
                    "language": file_change.language or "unknown",
                    "pr_title": "",
                    "changed_files": file_change.path,
                    "diff_snippet": code_snippet
                }
                
                # Run agent analysis
                task = asyncio.create_task(self._run_agent_async(agent, context))
                tasks.append(task)
                agent_names.append(agent_name)
        
        # Wait for all agents to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results by agent
        agent_results = {}
        for agent_name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_name} failed: {result}")
                continue
            
            if agent_name not in agent_results:
                agent_results[agent_name] = result
            else:
                # Merge comments if agent ran on multiple files
                agent_results[agent_name].comments.extend(result.comments)
        
        return agent_results
    
    async def _run_agent_async(self, agent: Any, context: Dict[str, Any]) -> AgentResult:
        """
        Run a single agent asynchronously.
        
        Args:
            agent: Agent instance
            context: Analysis context
            
        Returns:
            AgentResult
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, agent.analyze, context)
    
    def _check_cache(self, request: AnalysisRequest) -> Optional[AnalysisResult]:
        """
        Check if analysis result is cached.
        
        Args:
            request: Analysis request
            
        Returns:
            Cached AnalysisResult or None
        """
        if not request.repo or not request.pr_number or not request.diff_hash:
            return None
        
        try:
            cache_key = CacheKeys.pr_analysis(
                request.repo,
                request.pr_number,
                request.diff_hash
            )
            cached_data = self.cache_client.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for {cache_key}")
                # Reconstruct result from cached data
                # Simplified: return as-is (in production, properly deserialize)
                return cached_data
            
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
        
        return None
    
    def _cache_result(self, request: AnalysisRequest, result: AnalysisResult):
        """
        Cache analysis result.
        
        Args:
            request: Analysis request
            result: Analysis result
        """
        if not request.repo or not request.pr_number or not request.diff_hash:
            return
        
        try:
            cache_key = CacheKeys.pr_analysis(
                request.repo,
                request.pr_number,
                request.diff_hash
            )
            self.cache_client.set(
                cache_key,
                result.to_dict(),
                ex=self.settings.cache_analysis_ttl
            )
            logger.info(f"Cached result: {cache_key}")
            
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")
    
    def invalidate_cache(self, repo: str, pr_number: int):
        """
        Invalidate cache for a specific PR.
        
        Args:
            repo: Repository name
            pr_number: PR number
        """
        if not self.cache_client:
            return
        
        try:
            pattern = f"pr:analysis:{repo}:{pr_number}:*"
            count = self.cache_client.flush_pattern(pattern)
            logger.info(f"Invalidated {count} cache entries for {repo}#{pr_number}")
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
