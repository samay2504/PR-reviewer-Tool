"""Tests for cache client."""

import pytest
import time

from pr_agent.cache import CacheClient, CacheKeys


def test_cache_set_get(cache_client):
    """Test basic cache set and get."""
    success = cache_client.set("test_key", "test_value", ex=60)
    assert success, "Cache set should succeed"
    
    value = cache_client.get("test_key")
    assert value == "test_value"


def test_cache_delete(cache_client):
    """Test cache deletion."""
    cache_client.set("delete_me", "value")
    time.sleep(0.1)  # Give cache time to persist
    assert cache_client.exists("delete_me")
    
    cache_client.delete("delete_me")
    assert not cache_client.exists("delete_me")


def test_cache_miss(cache_client):
    """Test cache miss returns None."""
    value = cache_client.get("nonexistent_key")
    assert value is None


def test_cache_complex_objects(cache_client):
    """Test caching complex objects."""
    data = {
        "key": "value",
        "nested": {"list": [1, 2, 3]},
        "number": 42
    }
    
    cache_client.set("complex", data)
    time.sleep(0.1)  # Give cache time to persist
    retrieved = cache_client.get("complex")
    
    assert retrieved == data


def test_cache_keys():
    """Test cache key builders."""
    pr_key = CacheKeys.pr_analysis("owner/repo", 123, "abc123")
    assert pr_key == "pr:analysis:owner/repo:123:abc123"
    
    template_key = CacheKeys.template("test_template")
    assert template_key == "template:test_template"
    
    agent_state_key = CacheKeys.agent_state("request-123")
    assert agent_state_key == "agent_state:request-123"
    
    rate_limit_key = CacheKeys.rate_limit("client-1")
    assert rate_limit_key == "rate_limit:client-1"


def test_cache_stats(cache_client):
    """Test cache statistics."""
    stats = cache_client.get_stats()
    
    assert "redis_available" in stats
    assert "fallback_enabled" in stats
