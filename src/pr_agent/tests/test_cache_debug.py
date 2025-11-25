from pr_agent.cache import CacheClient
import tempfile

c = CacheClient(redis_url=None, fallback_enabled=True, fallback_dir=tempfile.mkdtemp())
print(f"Has fallback: {c.fallback_cache is not None}")
result = c.set('test', 'value')
print(f"Set result: {result}")
value = c.get('test')
print(f"Get result: {value}")
