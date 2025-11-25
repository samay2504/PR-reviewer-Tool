"""Redis caching with disk-based fallback."""

import json
import pickle
from pathlib import Path
from typing import Any, Optional, Union

import diskcache
from redis import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CacheClient:
    """
    Unified cache client with Redis primary and disk fallback.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        fallback_enabled: bool = True,
        fallback_dir: Union[str, Path] = ".cache/diskcache"
    ):
        """
        Initialize cache client.
        
        Args:
            redis_url: Redis connection URL
            fallback_enabled: Enable disk-based fallback
            fallback_dir: Directory for disk cache
        """
        self.redis_client: Optional[Redis] = None
        self.fallback_cache: Optional[diskcache.Cache] = None
        self.fallback_enabled = fallback_enabled
        self._redis_available = False
        
        # Initialize Redis
        if redis_url:
            try:
                self.redis_client = Redis.from_url(
                    redis_url,
                    decode_responses=False,  # Handle bytes for pickle
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                self._redis_available = True
                logger.info(f"Redis connected: {redis_url}")
            except (RedisError, RedisConnectionError) as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None
        
        # Initialize fallback cache
        if fallback_enabled:
            try:
                fallback_path = Path(fallback_dir)
                fallback_path.mkdir(parents=True, exist_ok=True)
                self.fallback_cache = diskcache.Cache(str(fallback_path), eviction_policy='none')
                logger.info(f"Disk cache initialized: {fallback_path}")
            except Exception as e:
                logger.error(f"Failed to initialize disk cache: {e}")
                self.fallback_cache = None
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Try JSON first (more portable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None
    ) -> bool:
        """
        Set a cache value.
        
        Args:
            key: Cache key
            value: Value to cache
            ex: Expiration time in seconds
            
        Returns:
            True if successful
        """
        # Try Redis first
        if self._redis_available and self.redis_client:
            try:
                serialized = self._serialize(value)
                self.redis_client.set(key, serialized, ex=ex)
                logger.debug(f"Set Redis key: {key}")
                return True
            except RedisError as e:
                logger.warning(f"Redis set failed: {e}")
                self._redis_available = False
        
        # Fall back to disk cache (use value directly, diskcache handles serialization)
        if self.fallback_enabled and self.fallback_cache is not None:
            try:
                result = self.fallback_cache.set(key, value, expire=ex)
                logger.debug(f"Set disk cache key: {key}, result: {result}")
                return True
            except Exception as e:
                logger.error(f"Disk cache set failed: {e}", exc_info=True)
                return False
        
        logger.warning(f"No cache available for key: {key}")
        return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a cache value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        # Try Redis first
        if self._redis_available and self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    logger.debug(f"Redis cache hit: {key}")
                    return self._deserialize(data)
            except RedisError as e:
                logger.warning(f"Redis get failed: {e}")
                self._redis_available = False
        
        # Fall back to disk cache
        if self.fallback_enabled and self.fallback_cache:
            try:
                data = self.fallback_cache.get(key)
                if data is not None:
                    logger.debug(f"Disk cache hit: {key}")
                    return data  # diskcache handles serialization internally
            except Exception as e:
                logger.error(f"Disk cache get failed: {e}")
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        success = False
        
        # Delete from Redis
        if self._redis_available and self.redis_client:
            try:
                self.redis_client.delete(key)
                success = True
            except RedisError as e:
                logger.warning(f"Redis delete failed: {e}")
        
        # Delete from disk cache
        if self.fallback_enabled and self.fallback_cache:
            try:
                self.fallback_cache.delete(key)
                success = True
            except Exception as e:
                logger.error(f"Disk cache delete failed: {e}")
        
        return success
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        # Check Redis
        if self._redis_available and self.redis_client:
            try:
                if self.redis_client.exists(key):
                    return True
            except RedisError as e:
                logger.debug(f"Redis exists check failed for {key}: {e}")
        
        # Check disk cache
        if self.fallback_enabled and self.fallback_cache:
            try:
                return key in self.fallback_cache
            except Exception as e:
                logger.debug(f"Disk cache exists check failed for {key}: {e}")
        
        return False
    
    def publish(self, channel: str, message: str) -> bool:
        """
        Publish message to Redis pub/sub channel.
        
        Args:
            channel: Channel name
            message: Message to publish
            
        Returns:
            True if successful
        """
        if self._redis_available and self.redis_client:
            try:
                self.redis_client.publish(channel, message)
                return True
            except RedisError as e:
                logger.warning(f"Redis publish failed: {e}")
        return False
    
    def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "pr:analysis:*")
            
        Returns:
            Number of keys deleted
        """
        count = 0
        
        # Flush from Redis
        if self._redis_available and self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count += self.redis_client.delete(*keys)
            except RedisError as e:
                logger.warning(f"Redis flush pattern failed: {e}")
        
        # Flush from disk cache (simple implementation)
        if self.fallback_enabled and self.fallback_cache:
            try:
                # Disk cache doesn't have pattern matching, so iterate
                import fnmatch
                for key in list(self.fallback_cache.iterkeys()):
                    if fnmatch.fnmatch(key, pattern):
                        self.fallback_cache.delete(key)
                        count += 1
            except Exception as e:
                logger.error(f"Disk cache flush pattern failed: {e}")
        
        logger.info(f"Flushed {count} keys matching pattern: {pattern}")
        return count
    
    def clear(self) -> bool:
        """Clear all cache."""
        success = False
        
        # Clear Redis
        if self._redis_available and self.redis_client:
            try:
                self.redis_client.flushdb()
                success = True
            except RedisError as e:
                logger.warning(f"Redis clear failed: {e}")
        
        # Clear disk cache
        if self.fallback_enabled and self.fallback_cache:
            try:
                self.fallback_cache.clear()
                success = True
            except Exception as e:
                logger.error(f"Disk cache clear failed: {e}")
        
        return success
    
    @property
    def is_redis_available(self) -> bool:
        """Check if Redis is available."""
        return self._redis_available
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = {
            "redis_available": self._redis_available,
            "fallback_enabled": self.fallback_enabled
        }
        
        # Redis stats
        if self._redis_available and self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_keys"] = self.redis_client.dbsize()
                stats["redis_memory"] = info.get("used_memory_human", "unknown")
            except RedisError as e:
                logger.debug(f"Redis stats retrieval failed: {e}")
        
        # Disk cache stats
        if self.fallback_enabled and self.fallback_cache:
            try:
                stats["disk_cache_size"] = len(self.fallback_cache)
                stats["disk_cache_volume"] = self.fallback_cache.volume()
            except Exception as e:
                logger.debug(f"Disk cache stats retrieval failed: {e}")
        
        return stats


# Cache key patterns and builders
class CacheKeys:
    """Cache key builders for consistent key naming."""
    
    @staticmethod
    def pr_analysis(repo: str, pr_number: int, diff_hash: str) -> str:
        """Key for PR analysis result."""
        return f"pr:analysis:{repo}:{pr_number}:{diff_hash}"
    
    @staticmethod
    def template(template_id: str) -> str:
        """Key for template."""
        return f"template:{template_id}"
    
    @staticmethod
    def template_version(template_id: str) -> str:
        """Key for template version hash."""
        return f"template_version:{template_id}"
    
    @staticmethod
    def agent_state(request_id: str) -> str:
        """Key for agent state."""
        return f"agent_state:{request_id}"
    
    @staticmethod
    def rate_limit(client_id: str) -> str:
        """Key for rate limiting."""
        return f"rate_limit:{client_id}"
