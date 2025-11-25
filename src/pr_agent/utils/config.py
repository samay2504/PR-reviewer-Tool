"""Configuration management for PR Agent."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GitHub Configuration
    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_enabled: bool = Field(True, env="REDIS_ENABLED")
    
    # LLM Provider Configuration
    llm_provider_preference: str = Field(
        "google_genai,groq,openai,huggingface,fallback",
        env="LLM_PROVIDER_PREFERENCE"
    )
    default_temperature: float = Field(0.39, env="DEFAULT_TEMPERATURE")
    default_model: Optional[str] = Field(None, env="DEFAULT_MODEL")
    
    # API Keys
    huggingfacehub_api_token: Optional[str] = Field(None, env="HUGGINGFACEHUB_API_TOKEN")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    groq_api_key: Optional[str] = Field(None, env="GROQ_API_KEY")
    
    # Cache Configuration
    cache_default_ttl_seconds: int = Field(86400, env="CACHE_DEFAULT_TTL_SECONDS")
    cache_analysis_ttl: int = Field(86400, env="CACHE_ANALYSIS_TTL")
    cache_template_ttl: int = Field(604800, env="CACHE_TEMPLATE_TTL")
    cache_agent_state_ttl: int = Field(600, env="CACHE_AGENT_STATE_TTL")
    cache_fallback_enabled: bool = Field(True, env="CACHE_FALLBACK_ENABLED")
    
    # Application Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8000, env="APP_PORT")
    app_workers: int = Field(4, env="APP_WORKERS")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # Agent Configuration
    max_llm_retries: int = Field(3, env="MAX_LLM_RETRIES")
    max_agent_concurrency: int = Field(5, env="MAX_AGENT_CONCURRENCY")
    agent_timeout_seconds: int = Field(300, env="AGENT_TIMEOUT_SECONDS")
    
    # Template Configuration
    templates_dir: str = Field("templates", env="TEMPLATES_DIR")
    templates_hot_reload: bool = Field(True, env="TEMPLATES_HOT_RELOAD")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
    
    @property
    def provider_preference_list(self) -> List[str]:
        """Parse provider preference string into list."""
        return [p.strip() for p in self.llm_provider_preference.split(",")]
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration dictionary for LLMProvider."""
        return {
            "provider_preference": self.provider_preference_list,
            "temperature": self.default_temperature,
            "model": self.default_model,
            "max_retries": self.max_llm_retries,
        }
    
    def get_templates_path(self) -> Path:
        """Get absolute path to templates directory."""
        # Go up from config.py: utils -> pr_agent -> src -> project root
        base_path = Path(__file__).parent.parent.parent.parent
        return base_path / self.templates_dir


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (for dependency injection)."""
    return settings
