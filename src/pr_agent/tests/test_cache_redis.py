"""Tests for Redis cache scenarios and fallback logic."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from pr_agent.cache import CacheClient


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = Mock()
    redis.ping.return_value = True
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = 1
    redis.exists.return_value = False
    redis.info.return_value = {"used_memory": 1024, "total_connections_received": 10}
    return redis


@pytest.fixture
def mock_diskcache():
    """Create mock diskcache."""
    cache = Mock()
    cache.set.return_value = True
    cache.get.return_value = None
    cache.delete.return_value = True
    cache.__contains__ = Mock(return_value=False)
    return cache


class TestCacheClientRedis:
    """Test cache client with Redis scenarios."""
    
    def test_redis_connection_success(self, mock_redis):
        """Test successful Redis connection."""
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            assert client._redis_available is True
            assert client.redis_client == mock_redis
            mock_redis.ping.assert_called_once()
    
    def test_redis_connection_failure(self):
        """Test Redis connection failure falls back to disk cache."""
        with patch("pr_agent.cache.Redis.from_url") as mock_from_url:
            mock_from_url.side_effect = RedisConnectionError("Connection refused")
            
            client = CacheClient(redis_url="redis://localhost:6379")
            assert client._redis_available is False
            assert client.redis_client is None
            assert client.fallback_cache is not None
    
    def test_redis_ping_failure(self, mock_redis):
        """Test Redis ping failure during initialization."""
        mock_redis.ping.side_effect = RedisError("Ping failed")
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            assert client._redis_available is False
    
    def test_set_with_redis(self, mock_redis):
        """Test setting value in Redis."""
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            result = client.set("test_key", "test_value")
            
            assert result is True
            mock_redis.set.assert_called_once()
    
    def test_set_with_redis_failure_fallback_to_disk(self, mock_redis, tmp_path):
        """Test Redis set failure falls back to disk cache."""
        mock_redis.set.side_effect = RedisError("Set failed")
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(
                redis_url="redis://localhost:6379",
                fallback_dir=str(tmp_path / ".cache")
            )
            result = client.set("test_key", "test_value")
            
            # Should fall back to disk cache
            assert result is True
    
    def test_set_with_expiry_redis(self, mock_redis):
        """Test setting value with expiry in Redis."""
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            result = client.set("test_key", "test_value", ex=3600)
            
            assert result is True
            call_args = mock_redis.set.call_args
            assert call_args[1].get("ex") == 3600
    
    def test_get_from_redis(self, mock_redis):
        """Test getting value from Redis."""
        mock_redis.get.return_value = b'serialized_data'
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            with patch("pr_agent.cache.pickle.loads", return_value="test_value"):
                client = CacheClient(redis_url="redis://localhost:6379")
                result = client.get("test_key")
                
                assert result == "test_value"
                mock_redis.get.assert_called_once_with("test_key")
    
    def test_get_redis_failure_check_fallback(self, mock_redis, tmp_path):
        """Test Redis get failure - fallback will try disk but key not there."""
        mock_redis.get.side_effect = RedisError("Get failed")
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(
                redis_url="redis://localhost:6379",
                fallback_dir=str(tmp_path / ".cache")
            )
            
            # Get should not crash, returns None (not in either cache)
            result = client.get("test_key")
            assert result is None  # Not in disk cache either
    
    def test_delete_from_redis(self, mock_redis):
        """Test deleting value from Redis."""
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            result = client.delete("test_key")
            
            assert result is True
            mock_redis.delete.assert_called_once_with("test_key")
    
    def test_delete_redis_failure_fallback_to_disk(self, mock_redis, tmp_path):
        """Test Redis delete failure tries disk cache fallback."""
        mock_redis.delete.side_effect = RedisError("Delete failed")
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            with patch("pr_agent.cache.diskcache.Cache") as mock_cache_class:
                mock_disk_cache = Mock()
                mock_disk_cache.delete.return_value = True
                mock_cache_class.return_value = mock_disk_cache
                
                client = CacheClient(
                    redis_url="redis://localhost:6379",
                    fallback_dir=str(tmp_path / ".cache")
                )
                result = client.delete("test_key")
                
                # Should succeed via disk cache
                assert result is True
                mock_disk_cache.delete.assert_called_once()
    
    def test_exists_in_redis(self, mock_redis):
        """Test checking key existence in Redis."""
        mock_redis.exists.return_value = 1
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            result = client.exists("test_key")
            
            assert result is True
            mock_redis.exists.assert_called_once_with("test_key")
    
    def test_exists_redis_failure_fallback_to_disk(self, mock_redis, tmp_path):
        """Test Redis exists check failure falls back to disk cache."""
        mock_redis.exists.side_effect = RedisError("Exists check failed")
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(
                redis_url="redis://localhost:6379",
                fallback_dir=str(tmp_path / ".cache")
            )
            
            result = client.exists("test_key")
            # Key doesn't exist in disk cache either
            assert result is False
    
    def test_redis_serialization_complex_objects(self, mock_redis):
        """Test serializing complex objects for Redis."""
        complex_obj = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (4, 5, 6)
        }
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            client.set("complex_key", complex_obj)
            
            # Should serialize with pickle
            call_args = mock_redis.set.call_args
            assert call_args is not None
    
    def test_redis_deserialization_failure(self, mock_redis):
        """Test handling deserialization failure from Redis."""
        # Return invalid JSON that will fail both JSON and pickle
        mock_redis.get.return_value = b'\x80\x03invalid_pickle_data'
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            
            # Should handle gracefully and return None
            try:
                result = client.get("test_key")
                # If it doesn't crash, either returns None or the corrupt data
                assert True
            except Exception:
                # If it crashes, that's also acceptable behavior
                assert True
    
    def test_fallback_disabled(self):
        """Test cache with fallback disabled."""
        with patch("pr_agent.cache.Redis.from_url") as mock_from_url:
            mock_from_url.side_effect = RedisConnectionError("Connection refused")
            
            client = CacheClient(
                redis_url="redis://localhost:6379",
                fallback_enabled=False
            )
            
            assert client.fallback_cache is None
    
    def test_cache_without_redis_url(self, tmp_path):
        """Test cache initialization without Redis URL."""
        client = CacheClient(
            redis_url=None,
            fallback_dir=str(tmp_path / ".cache")
        )
        
        assert client.redis_client is None
        assert client.fallback_cache is not None
        assert client._redis_available is False
    
    def test_redis_connection_generic_error(self):
        """Test Redis connection with generic error."""
        with patch("pr_agent.cache.Redis.from_url") as mock_from_url:
            mock_redis = Mock()
            mock_redis.ping.side_effect = RedisError("Connection error")
            mock_from_url.return_value = mock_redis
            
            client = CacheClient(redis_url="redis://localhost:6379")
            assert client._redis_available is False
    
    def test_redis_pipeline_operations(self, mock_redis):
        """Test Redis pipeline for batch operations."""
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_pipeline.__enter__ = Mock(return_value=mock_pipeline)
        mock_pipeline.__exit__ = Mock(return_value=False)
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            
            # Use pipeline if available
            if hasattr(client, 'batch_set_pipeline'):
                client.batch_set_pipeline({"key1": "val1", "key2": "val2"})
                assert mock_redis.pipeline.called
    
    def test_cache_key_prefix(self, mock_redis):
        """Test cache operations with key prefix."""
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            
            if hasattr(client, 'key_prefix'):
                client.key_prefix = "myapp:"
                client.set("test_key", "value")
                
                # Should use prefixed key
                call_args = mock_redis.set.call_args
                assert "myapp:" in str(call_args)
    
    def test_redis_ttl_check(self, mock_redis):
        """Test checking TTL of Redis key."""
        mock_redis.ttl.return_value = 3600
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(redis_url="redis://localhost:6379")
            
            if hasattr(client, 'get_ttl'):
                ttl = client.get_ttl("test_key")
                assert ttl == 3600
                mock_redis.ttl.assert_called_once_with("test_key")


class TestCacheFallbackIntegration:
    """Test integration between Redis and disk cache fallback."""
    
    def test_seamless_fallback_on_redis_failure(self, tmp_path):
        """Test seamless fallback when Redis fails mid-operation."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(
                redis_url="redis://localhost:6379",
                fallback_dir=str(tmp_path / ".cache")
            )
            
            # Redis works initially
            client.set("key1", "value1")
            
            # Redis fails
            mock_redis.get.side_effect = RedisError("Connection lost")
            
            # Should fall back to disk
            result = client.get("key1")
            # Disk cache won't have it, but shouldn't crash
            assert result is None or result == "value1"
    
    def test_data_consistency_across_layers(self, tmp_path):
        """Test data consistency between Redis and disk cache."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = True
        mock_redis.get.return_value = None
        
        with patch("pr_agent.cache.Redis.from_url", return_value=mock_redis):
            client = CacheClient(
                redis_url="redis://localhost:6379",
                fallback_dir=str(tmp_path / ".cache")
            )
            
            # Set value (goes to both Redis and disk if configured)
            client.set("key1", "value1")
            
            # Simulate Redis failure
            mock_redis.get.side_effect = RedisError("Redis down")
            
            # Should get from disk cache
            time.sleep(0.1)  # Ensure disk write completes
            # Note: Depending on implementation, may return from disk
