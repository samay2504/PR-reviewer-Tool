"""FastAPI application for PR analysis."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..cache import CacheClient
from ..core import Orchestrator, AnalysisRequest
from ..templates import TemplateManager
from ..utils.config import get_settings, Settings
from ..utils.logging import setup_logging, get_logger

# Setup logging
settings = get_settings()
setup_logging(log_level=settings.log_level)
logger = get_logger(__name__)

# Global instances
cache_client: Optional[CacheClient] = None
template_manager: Optional[TemplateManager] = None
orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global cache_client, template_manager, orchestrator
    
    logger.info("Initializing PR Review Agent")
    
    # Initialize cache
    if settings.redis_enabled:
        cache_client = CacheClient(
            redis_url=settings.redis_url,
            fallback_enabled=settings.cache_fallback_enabled
        )
        logger.info("Cache client initialized")
    
    # Initialize template manager
    templates_path = settings.get_templates_path()
    template_manager = TemplateManager(
        templates_dir=templates_path,
        redis_client=cache_client.redis_client if cache_client else None,
        hot_reload=settings.templates_hot_reload
    )
    logger.info("Template manager initialized")
    
    # Initialize orchestrator
    orchestrator = Orchestrator(
        settings=settings,
        cache_client=cache_client,
        template_manager=template_manager
    )
    logger.info("Orchestrator initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down PR Review Agent")
    if template_manager:
        template_manager.stop_file_watcher()


# Create FastAPI app
app = FastAPI(
    title="PR Review Agent",
    description="Automated Pull Request Review System with Multi-Agent Analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request model for PR analysis."""
    repo: Optional[str] = Field(None, description="Repository name (owner/repo)")
    pr_number: Optional[int] = Field(None, description="Pull request number")
    diff_text: Optional[str] = Field(None, description="Raw diff text")
    use_cache: bool = Field(True, description="Whether to use cache")


class AnalyzeResponse(BaseModel):
    """Response model for PR analysis."""
    request_id: str
    repo: Optional[str]
    pr_number: Optional[int]
    diff_hash: str
    comments: list
    summary: dict
    provider: str
    cached: bool


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    cache_available: bool
    redis_available: bool
    templates_loaded: int
    llm_provider: str


class TemplateListResponse(BaseModel):
    """Template list response."""
    templates: list


class TemplateResponse(BaseModel):
    """Single template response."""
    id: str
    version: str
    description: str
    variables: list
    template: str
    hash: str


# Dependency injection
def get_orchestrator() -> Orchestrator:
    """Get orchestrator instance."""
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized"
        )
    return orchestrator


def get_cache_client() -> Optional[CacheClient]:
    """Get cache client instance."""
    return cache_client


def get_template_manager() -> TemplateManager:
    """Get template manager instance."""
    if template_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Template manager not initialized"
        )
    return template_manager


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """Root endpoint."""
    return {
        "name": "PR Review Agent",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health(
    orch: Orchestrator = Depends(get_orchestrator),
    cache: Optional[CacheClient] = Depends(get_cache_client),
    tmpl: TemplateManager = Depends(get_template_manager)
):
    """Health check endpoint."""
    provider_info = orch.llm_adapter.get_provider_info()
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        cache_available=cache is not None,
        redis_available=cache.is_redis_available if cache else False,
        templates_loaded=len(tmpl.list_templates()),
        llm_provider=provider_info.get("provider", "unknown")
    )


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_pr(
    request: AnalyzeRequest,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """
    Analyze a pull request or diff.
    
    Provide either:
    - repo + pr_number (for GitHub PR)
    - diff_text (for raw diff analysis)
    """
    if not request.diff_text and not (request.repo and request.pr_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either diff_text or (repo + pr_number)"
        )
    
    try:
        # Create analysis request
        analysis_request = AnalysisRequest(
            repo=request.repo,
            pr_number=request.pr_number,
            diff_text=request.diff_text,
            use_cache=request.use_cache
        )
        
        # Run analysis
        result = await orch.analyze(analysis_request)
        
        # Convert to response - handle both AnalysisResult objects and cached dicts
        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = result.to_dict()
        
        return AnalyzeResponse(**result_dict)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/analyze/markdown", tags=["Analysis"])
async def analyze_pr_markdown(
    request: AnalyzeRequest,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """
    Analyze a pull request and return a markdown-formatted summary.
    
    This endpoint is useful for posting results as PR comments.
    """
    if not request.diff_text and not (request.repo and request.pr_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either diff_text or (repo + pr_number)"
        )
    
    try:
        # Create analysis request
        analysis_request = AnalysisRequest(
            repo=request.repo,
            pr_number=request.pr_number,
            diff_text=request.diff_text,
            use_cache=request.use_cache
        )
        
        # Run analysis
        result = await orch.analyze(analysis_request)
        
        # Generate markdown summary
        markdown_summary = ""
        if "summarizer" in orch.agents:
            try:
                # Handle both dict and AnalysisResult objects
                if isinstance(result, dict):
                    summary_data = result.get("summary")
                else:
                    summary_data = result.summary
                
                if summary_data:
                    summarizer = orch.agents["summarizer"]
                    markdown_summary = summarizer.generate_markdown_summary(
                        summary_data,
                        repo=request.repo,
                        pr_number=request.pr_number
                    )
            except Exception as e:
                logger.error(f"Failed to generate markdown summary: {e}")
                markdown_summary = "# Analysis Complete\n\nSummary generation failed."
        
        return {
            "markdown": markdown_summary,
            "request_id": result.request_id,
            "cached": result.cached
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/templates", response_model=TemplateListResponse, tags=["Templates"])
async def list_templates(tmpl: TemplateManager = Depends(get_template_manager)):
    """List all available templates."""
    templates = tmpl.list_templates()
    return TemplateListResponse(templates=templates)


@app.get("/templates/{template_id}", response_model=TemplateResponse, tags=["Templates"])
async def get_template(
    template_id: str,
    tmpl: TemplateManager = Depends(get_template_manager)
):
    """Get a specific template."""
    template = tmpl.get_template_metadata(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}"
        )
    
    return TemplateResponse(**template.to_dict())


@app.delete("/cache/{repo}/{pr_number}", tags=["Cache"])
async def invalidate_cache(
    repo: str,
    pr_number: int,
    orch: Orchestrator = Depends(get_orchestrator)
):
    """Invalidate cache for a specific PR."""
    try:
        orch.invalidate_cache(repo, pr_number)
        return {"status": "success", "message": f"Cache invalidated for {repo}#{pr_number}"}
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/stats", tags=["General"])
async def get_stats(cache: Optional[CacheClient] = Depends(get_cache_client)):
    """Get system statistics."""
    stats = {
        "cache": cache.get_stats() if cache else {"enabled": False}
    }
    return stats


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "pr_agent.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
