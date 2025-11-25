"""LLM Adapter for LangChain integration with robust fallback."""

import asyncio
from typing import Any, Dict, List, Optional, Union

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models import BaseLanguageModel

from .llm_provider import LLMProvider, create_llm_provider
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LLMAdapter:
    """
    Adapter that wraps LLMProvider and provides a uniform interface for LangChain.
    Handles async/sync calls, retries, and fallback logic.
    """
    
    def __init__(self, provider: LLMProvider, max_retries: int = 3, max_concurrency: int = 5):
        """
        Initialize LLM adapter.
        
        Args:
            provider: LLMProvider instance
            max_retries: Maximum number of retries on failure
            max_concurrency: Maximum concurrent LLM calls
        """
        self.provider = provider
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrency)
    
    @property
    def llm(self) -> BaseLanguageModel:
        """Get the underlying LLM instance for LangChain."""
        return self.provider.llm
    
    def create_chain(self, template_str: str):
        """
        Create a LangChain chain with the given template using LCEL.
        
        Args:
            template_str: Prompt template string
            
        Returns:
            Configured chain (prompt | llm | parser)
        """
        prompt = PromptTemplate.from_template(template_str)
        parser = StrOutputParser()
        return prompt | self.llm | parser
    
    def invoke(self, prompt: str, retries: Optional[int] = None) -> Optional[str]:
        """
        Invoke the LLM with a prompt (synchronous).
        
        Args:
            prompt: Prompt text
            retries: Number of retries (uses max_retries if not specified)
            
        Returns:
            LLM response or None on failure
        """
        retries = retries or self.max_retries
        
        for attempt in range(retries):
            try:
                logger.debug(f"LLM invocation attempt {attempt + 1}/{retries}")
                response = self.provider.invoke(prompt)
                
                if response is None:
                    logger.warning(f"LLM returned None on attempt {attempt + 1}")
                    if attempt < retries - 1:
                        continue
                    return None
                
                # Validate response
                if isinstance(response, str) and response.strip():
                    return response
                elif isinstance(response, dict) and response.get('content'):
                    return response['content']
                else:
                    logger.warning(f"Invalid LLM response format: {type(response)}")
                    if attempt < retries - 1:
                        continue
                    return None
                    
            except Exception as e:
                logger.error(f"LLM invocation error on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    logger.info(f"Retrying... ({attempt + 2}/{retries})")
                    continue
                else:
                    logger.error("All retry attempts exhausted")
                    return None
        
        return None
    
    async def ainvoke(self, prompt: str, retries: Optional[int] = None) -> Optional[str]:
        """
        Invoke the LLM with a prompt (asynchronous).
        
        Args:
            prompt: Prompt text
            retries: Number of retries (uses max_retries if not specified)
            
        Returns:
            LLM response or None on failure
        """
        async with self._semaphore:
            # Run synchronous invoke in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.invoke, prompt, retries)
    
    def batch_invoke(self, prompts: List[str]) -> List[Optional[str]]:
        """
        Invoke LLM with multiple prompts (synchronous batch).
        
        Args:
            prompts: List of prompt texts
            
        Returns:
            List of responses (may contain None for failures)
        """
        return [self.invoke(prompt) for prompt in prompts]
    
    async def abatch_invoke(self, prompts: List[str]) -> List[Optional[str]]:
        """
        Invoke LLM with multiple prompts (asynchronous batch).
        
        Args:
            prompts: List of prompt texts
            
        Returns:
            List of responses (may contain None for failures)
        """
        tasks = [self.ainvoke(prompt) for prompt in prompts]
        return await asyncio.gather(*tasks)
    
    def run_chain(self, chain, inputs: Dict[str, Any]) -> Optional[str]:
        """
        Run a LangChain LCEL chain with inputs and error handling.
        
        Args:
            chain: LCEL chain instance (prompt | llm | parser)
            inputs: Dictionary of template variables
            
        Returns:
            Chain output or None on failure
        """
        try:
            result = chain.invoke(inputs)
            
            # Handle different result types
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and 'text' in result:
                return result['text']
            elif isinstance(result, dict) and 'content' in result:
                return result['content']
            else:
                logger.warning(f"Unexpected chain result type: {type(result)}")
                return str(result) if result else None
                
        except Exception as e:
            logger.error(f"Chain execution failed: {e}", exc_info=True)
            return None
    
    async def arun_chain(self, chain, inputs: Dict[str, Any]) -> Optional[str]:
        """
        Run a LangChain LCEL chain with inputs (asynchronous).
        
        Args:
            chain: LCEL chain instance (prompt | llm | parser)
            inputs: Dictionary of template variables
            
        Returns:
            Chain output or None on failure
        """
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.run_chain, chain, inputs)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current LLM provider."""
        return self.provider.get_provider_info()
    
    @property
    def is_fallback_mode(self) -> bool:
        """Check if currently in fallback mode."""
        info = self.get_provider_info()
        return info.get("fallback_mode", False)


def create_llm_adapter(config: Dict[str, Any]) -> LLMAdapter:
    """
    Factory function to create LLM adapter.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured LLMAdapter instance
    """
    provider = create_llm_provider(config)
    max_retries = config.get("max_retries", 3)
    max_concurrency = config.get("max_agent_concurrency", 5)
    return LLMAdapter(provider, max_retries=max_retries, max_concurrency=max_concurrency)
