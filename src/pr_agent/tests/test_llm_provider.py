"""Tests for LLM Provider system with multiple fallbacks."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pr_agent.llm.llm_provider import LLMProvider, create_llm_provider


class TestLLMProvider:
    """Test LLM provider initialization and fallback logic."""
    
    def test_create_llm_provider_basic(self):
        """Test basic LLM provider creation."""
        config = {"provider_preference": ["fallback"]}
        provider = create_llm_provider(config)
        assert provider is not None
        assert provider.llm is not None
    
    def test_llm_provider_fallback_on_missing_keys(self):
        """Test fallback when API keys are missing."""
        config = {
            "provider_preference": ["google_genai", "groq", "fallback"]
        }
        
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            provider = LLMProvider(config)
            assert provider.llm is not None
            # Should fall back to fallback mode
            info = provider.get_provider_info()
            assert info["fallback_mode"] is True
    
    def test_llm_provider_google_genai_success(self):
        """Test Google Gemini provider initialization."""
        config = {
            "provider_preference": ["google_genai"],
            "temperature": 0.1
        }
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = "test response"
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"}):
            with patch("pr_agent.llm.llm_provider.GOOGLE_GENAI_AVAILABLE", True):
                with patch("pr_agent.llm.llm_provider.ChatGoogleGenerativeAI") as mock_class:
                    mock_class.return_value = mock_llm
                    provider = LLMProvider(config)
                    assert provider.llm is not None
    
    def test_llm_provider_groq_success(self):
        """Test Groq provider initialization."""
        config = {
            "provider_preference": ["groq"],
            "temperature": 0.1
        }
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = "test response"
        
        with patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}):
            with patch("pr_agent.llm.llm_provider.GROQ_AVAILABLE", True):
                with patch("pr_agent.llm.llm_provider.ChatGroq") as mock_class:
                    mock_class.return_value = mock_llm
                    provider = LLMProvider(config)
                    assert provider.llm is not None
    
    def test_llm_provider_openai_success(self):
        """Test OpenAI provider initialization."""
        config = {
            "provider_preference": ["openai"],
            "temperature": 0.1
        }
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = "test response"
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            with patch("pr_agent.llm.llm_provider.OPENAI_AVAILABLE", True):
                with patch("pr_agent.llm.llm_provider.ChatOpenAI") as mock_class:
                    mock_class.return_value = mock_llm
                    provider = LLMProvider(config)
                    assert provider.llm is not None
    
    def test_llm_provider_huggingface_token_validation_failure(self):
        """Test HuggingFace provider with invalid token."""
        config = {
            "provider_preference": ["huggingface", "fallback"]
        }
        
        with patch.dict(os.environ, {"HUGGINGFACEHUB_API_TOKEN": "invalid_token"}):
            with patch("pr_agent.llm.llm_provider.HUGGINGFACE_AVAILABLE", True):
                with patch("pr_agent.llm.llm_provider.HF_API_AVAILABLE", True):
                    with patch("pr_agent.llm.llm_provider.HfApi") as mock_api:
                        mock_api.return_value.list_models.side_effect = Exception("Invalid token")
                        provider = LLMProvider(config)
                        # Should fall back
                        info = provider.get_provider_info()
                        assert info["fallback_mode"] is True
    
    def test_llm_provider_invoke_success(self):
        """Test successful LLM invocation."""
        config = {"provider_preference": ["fallback"]}
        provider = LLMProvider(config)
        
        result = provider.invoke("Test prompt")
        assert result is not None
        assert isinstance(result, str)
    
    def test_llm_provider_invoke_with_dict_response(self):
        """Test LLM invocation with dict response."""
        config = {"provider_preference": ["fallback"]}
        provider = LLMProvider(config)
        
        # Mock to return dict with content
        with patch.object(provider.llm, 'invoke', return_value={"content": "test content"}):
            result = provider.invoke("Test prompt")
            assert result == "test content"
    
    def test_llm_provider_get_provider_info(self):
        """Test getting provider information."""
        config = {"provider_preference": ["fallback"]}
        provider = LLMProvider(config)
        
        info = provider.get_provider_info()
        assert isinstance(info, dict)
        assert "fallback_mode" in info
        assert "provider" in info
    
    def test_llm_provider_quota_error_handling(self):
        """Test handling of quota/rate limit errors."""
        config = {
            "provider_preference": ["google_genai", "fallback"]
        }
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"}):
            with patch("pr_agent.llm.llm_provider.GOOGLE_GENAI_AVAILABLE", True):
                with patch("pr_agent.llm.llm_provider.ChatGoogleGenerativeAI") as mock_class:
                    mock_class.side_effect = Exception("quota exceeded")
                    provider = LLMProvider(config)
                    # Should fall back
                    info = provider.get_provider_info()
                    assert info["fallback_mode"] is True
    
    def test_llm_provider_multiple_fallback_chain(self):
        """Test complete fallback chain with multiple providers."""
        config = {
            "provider_preference": ["google_genai", "groq", "openai", "fallback"]
        }
        
        # Clear all API keys to force fallback
        with patch.dict(os.environ, {}, clear=True):
            provider = LLMProvider(config)
            assert provider.llm is not None
            info = provider.get_provider_info()
            assert info["fallback_mode"] is True
    
    def test_llm_provider_custom_temperature(self):
        """Test custom temperature configuration."""
        config = {
            "provider_preference": ["fallback"],
            "temperature": 0.8
        }
        provider = LLMProvider(config)
        # Fallback LLM should be created with custom temperature
        assert provider.llm is not None
    
    def test_llm_provider_huggingface_model_fallback(self):
        """Test HuggingFace trying multiple models on failure."""
        config = {
            "provider_preference": ["huggingface", "fallback"]
        }
        
        with patch.dict(os.environ, {"HUGGINGFACEHUB_API_TOKEN": "test_key"}):
            with patch("pr_agent.llm.llm_provider.HUGGINGFACE_AVAILABLE", True):
                with patch("pr_agent.llm.llm_provider.HF_API_AVAILABLE", True):
                    with patch("pr_agent.llm.llm_provider.HfApi") as mock_api:
                        # Token validation succeeds
                        mock_api.return_value.list_models.return_value = [Mock()]
                        
                        with patch("pr_agent.llm.llm_provider.HuggingFaceEndpoint") as mock_hf:
                            # First model fails, second should be tried
                            mock_hf.side_effect = [
                                Exception("model not found"),
                                Exception("All HuggingFace models failed")
                            ]
                            provider = LLMProvider(config)
                            # Should fall back to fallback mode
                            info = provider.get_provider_info()
                            assert info["fallback_mode"] is True
    
    def test_llm_provider_invoke_with_aimessage(self):
        """Test handling AIMessage objects from LangChain."""
        config = {"provider_preference": ["fallback"]}
        provider = LLMProvider(config)
        
        # Mock AIMessage object
        mock_response = Mock()
        mock_response.content = "AI generated response"
        
        with patch.object(provider.llm, 'invoke', return_value=mock_response):
            result = provider.invoke("Test prompt")
            assert result == "AI generated response"
