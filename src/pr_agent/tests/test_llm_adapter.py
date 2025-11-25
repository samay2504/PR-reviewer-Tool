"""Tests for LLM Adapter with retry and concurrency logic."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pr_agent.llm.llm_adapter import LLMAdapter, create_llm_adapter
from pr_agent.llm.llm_provider import LLMProvider


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = Mock(spec=LLMProvider)
    provider.llm = Mock()
    provider.invoke = Mock(return_value="Test response")
    provider.get_provider_info = Mock(return_value={
        "provider": "test",
        "fallback_mode": False
    })
    return provider


@pytest.fixture
def adapter(mock_provider):
    """Create LLM adapter with mock provider."""
    return LLMAdapter(mock_provider, max_retries=3, max_concurrency=5)


class TestLLMAdapter:
    """Test LLM adapter functionality."""
    
    def test_adapter_creation(self, mock_provider):
        """Test basic adapter creation."""
        adapter = LLMAdapter(mock_provider)
        assert adapter.provider == mock_provider
        assert adapter.max_retries == 3
        assert adapter._semaphore._value == 5
    
    def test_adapter_custom_config(self, mock_provider):
        """Test adapter with custom configuration."""
        adapter = LLMAdapter(mock_provider, max_retries=5, max_concurrency=10)
        assert adapter.max_retries == 5
        assert adapter._semaphore._value == 10
    
    def test_llm_property(self, adapter, mock_provider):
        """Test LLM property access."""
        assert adapter.llm == mock_provider.llm
    
    def test_create_chain(self, adapter):
        """Test chain creation."""
        template = "Analyze this: {text}"
        chain = adapter.create_chain(template)
        assert chain is not None
    
    def test_invoke_success(self, adapter, mock_provider):
        """Test successful synchronous invocation."""
        result = adapter.invoke("Test prompt")
        assert result == "Test response"
        mock_provider.invoke.assert_called_once()
    
    def test_invoke_with_retries(self, adapter, mock_provider):
        """Test invocation with retry on initial failure."""
        # Fail twice, then succeed
        mock_provider.invoke.side_effect = [
            None,
            None,
            "Success on third try"
        ]
        
        result = adapter.invoke("Test prompt", retries=3)
        assert result == "Success on third try"
        assert mock_provider.invoke.call_count == 3
    
    def test_invoke_all_retries_exhausted(self, adapter, mock_provider):
        """Test invocation when all retries fail."""
        mock_provider.invoke.side_effect = [None, None, None]
        
        result = adapter.invoke("Test prompt", retries=3)
        assert result is None
        assert mock_provider.invoke.call_count == 3
    
    def test_invoke_with_exception(self, adapter, mock_provider):
        """Test invocation with exception handling."""
        # First call raises exception, second succeeds
        mock_provider.invoke.side_effect = [
            Exception("Temporary error"),
            "Success after error"
        ]
        
        result = adapter.invoke("Test prompt", retries=3)
        assert result == "Success after error"
        assert mock_provider.invoke.call_count == 2
    
    def test_invoke_with_dict_response(self, adapter, mock_provider):
        """Test invocation with dict response containing content."""
        mock_provider.invoke.return_value = {"content": "Dict response"}
        
        result = adapter.invoke("Test prompt")
        assert result == "Dict response"
    
    def test_invoke_with_invalid_response_format(self, adapter, mock_provider):
        """Test handling of invalid response formats."""
        # First return invalid, then valid
        mock_provider.invoke.side_effect = [
            {"invalid": "format"},
            "Valid response"
        ]
        
        result = adapter.invoke("Test prompt", retries=2)
        assert result == "Valid response"
    
    def test_invoke_with_empty_string(self, adapter, mock_provider):
        """Test handling of empty string responses."""
        mock_provider.invoke.side_effect = ["", "Non-empty response"]
        
        result = adapter.invoke("Test prompt", retries=2)
        assert result == "Non-empty response"
    
    @pytest.mark.asyncio
    async def test_ainvoke_success(self, adapter, mock_provider):
        """Test successful asynchronous invocation."""
        result = await adapter.ainvoke("Test prompt")
        assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_ainvoke_with_semaphore(self, adapter, mock_provider):
        """Test async invocation respects concurrency semaphore."""
        # Create multiple concurrent calls
        tasks = [adapter.ainvoke(f"Prompt {i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(r == "Test response" for r in results)
    
    def test_batch_invoke(self, adapter, mock_provider):
        """Test synchronous batch invocation."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        results = adapter.batch_invoke(prompts)
        
        assert len(results) == 3
        assert all(r == "Test response" for r in results)
        assert mock_provider.invoke.call_count == 3
    
    def test_batch_invoke_with_failures(self, adapter, mock_provider):
        """Test batch invocation with some failures."""
        # Mock provider will retry on None, so we need to fail all attempts
        mock_provider.invoke.side_effect = [
            "Success 1",
            Exception("Error"),  # Will retry and exhaust attempts
            Exception("Error"),
            Exception("Error"),
            "Success 3"
        ]
        
        results = adapter.batch_invoke(["P1", "P2", "P3"])
        assert results[0] == "Success 1"
        assert results[1] is None  # Failed after retries
        assert results[2] == "Success 3"
    
    @pytest.mark.asyncio
    async def test_abatch_invoke(self, adapter, mock_provider):
        """Test asynchronous batch invocation."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        results = await adapter.abatch_invoke(prompts)
        
        assert len(results) == 3
        assert all(r == "Test response" for r in results)
    
    def test_run_chain_success(self, adapter):
        """Test successful chain execution."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = "Chain output"
        
        result = adapter.run_chain(mock_chain, {"input": "test"})
        assert result == "Chain output"
        mock_chain.invoke.assert_called_once_with({"input": "test"})
    
    def test_run_chain_with_dict_output(self, adapter):
        """Test chain execution with dict output."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = {"text": "Text output"}
        
        result = adapter.run_chain(mock_chain, {"input": "test"})
        assert result == "Text output"
    
    def test_run_chain_with_content_dict(self, adapter):
        """Test chain execution with content in dict."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = {"content": "Content output"}
        
        result = adapter.run_chain(mock_chain, {"input": "test"})
        assert result == "Content output"
    
    def test_run_chain_with_exception(self, adapter):
        """Test chain execution with exception."""
        mock_chain = Mock()
        mock_chain.invoke.side_effect = Exception("Chain error")
        
        result = adapter.run_chain(mock_chain, {"input": "test"})
        assert result is None
    
    def test_run_chain_with_unexpected_type(self, adapter):
        """Test chain execution with unexpected result type."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = 12345  # Unexpected type
        
        result = adapter.run_chain(mock_chain, {"input": "test"})
        assert result == "12345"  # Should convert to string
    
    @pytest.mark.asyncio
    async def test_arun_chain_success(self, adapter):
        """Test asynchronous chain execution."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = "Async chain output"
        
        result = await adapter.arun_chain(mock_chain, {"input": "test"})
        assert result == "Async chain output"
    
    def test_get_provider_info(self, adapter, mock_provider):
        """Test getting provider information."""
        info = adapter.get_provider_info()
        assert info == {"provider": "test", "fallback_mode": False}
        mock_provider.get_provider_info.assert_called_once()
    
    def test_is_fallback_mode_false(self, adapter, mock_provider):
        """Test fallback mode detection when not in fallback."""
        assert adapter.is_fallback_mode is False
    
    def test_is_fallback_mode_true(self, adapter, mock_provider):
        """Test fallback mode detection when in fallback."""
        mock_provider.get_provider_info.return_value = {
            "provider": "fallback",
            "fallback_mode": True
        }
        assert adapter.is_fallback_mode is True
    
    def test_create_llm_adapter_factory(self):
        """Test factory function for creating adapter."""
        config = {
            "provider_preference": ["fallback"],
            "max_retries": 5,
            "max_agent_concurrency": 10
        }
        
        adapter = create_llm_adapter(config)
        assert adapter is not None
        assert adapter.max_retries == 5
        assert adapter._semaphore._value == 10
    
    def test_create_llm_adapter_default_config(self):
        """Test factory with default configuration."""
        config = {"provider_preference": ["fallback"]}
        
        adapter = create_llm_adapter(config)
        assert adapter.max_retries == 3  # Default
        assert adapter._semaphore._value == 5  # Default
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, adapter, mock_provider):
        """Test that semaphore limits concurrent requests."""
        # Track concurrent calls
        concurrent_calls = []
        max_concurrent = 0
        
        async def slow_invoke(prompt):
            concurrent_calls.append(1)
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, len(concurrent_calls))
            await asyncio.sleep(0.01)  # Simulate work
            concurrent_calls.pop()
            return "Response"
        
        # Replace invoke with slow version
        adapter.invoke = lambda p, r=None: asyncio.run(slow_invoke(p))
        
        # Create many concurrent requests
        tasks = [adapter.ainvoke(f"Prompt {i}") for i in range(20)]
        await asyncio.gather(*tasks)
        
        # Should not exceed semaphore limit
        assert max_concurrent <= adapter._semaphore._value
