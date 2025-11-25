"""Test configuration and fixtures."""

import pytest
from pathlib import Path

from pr_agent.utils.config import Settings
from pr_agent.cache import CacheClient
from pr_agent.templates import TemplateManager


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        redis_enabled=False,
        cache_fallback_enabled=True,
        templates_hot_reload=False,
        log_level="DEBUG"
    )


@pytest.fixture
def cache_client(tmp_path):
    """Create cache client for testing."""
    cache_dir = tmp_path / "cache"
    return CacheClient(
        redis_url=None,
        fallback_enabled=True,
        fallback_dir=str(cache_dir)
    )


@pytest.fixture
def template_manager(tmp_path):
    """Create template manager for testing."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # Create a test template
    test_template = templates_dir / "test_template.yaml"
    test_template.write_text("""
id: test_template
version: "1.0.0"
description: "Test template"
variables:
  - name: code
    type: str
template: "Analyze this code: {code}"
""")
    
    return TemplateManager(
        templates_dir=templates_dir,
        redis_client=None,
        hot_reload=False
    )


@pytest.fixture
def sample_diff():
    """Sample Git diff for testing."""
    return """diff --git a/src/example.py b/src/example.py
index 1234567..abcdefg 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,5 +1,8 @@
 def hello():
-    print("Hello")
+    password = "secret123"  # Bad: hardcoded secret
+    print("Hello World")
+    for i in range(100):
+        for j in range(100):
+            print(i * j)  # Nested loops
     
 if __name__ == "__main__":
     hello()
"""


@pytest.fixture
def sample_code():
    """Sample code for analysis."""
    return '''def process_data(user_input):
    password = "hardcoded_secret_123"
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    return query
'''
