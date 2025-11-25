"""Tests for Template Manager with Redis mirroring and hot reload."""

import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from pr_agent.templates import (
    TemplateManager,
    TemplateMetadata,
    TemplateFileHandler
)


@pytest.fixture
def temp_templates_dir():
    """Create temporary directory for templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_template_data():
    """Sample template data."""
    return {
        "id": "test_template",
        "version": "1.0",
        "description": "Test template for unit tests",
        "variables": [
            {"name": "input_text", "description": "Text to analyze"}
        ],
        "template": "Analyze this: {input_text}"
    }


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = Mock()
    redis.set = Mock(return_value=True)
    redis.get = Mock(return_value=None)
    redis.publish = Mock(return_value=1)
    return redis


class TestTemplateMetadata:
    """Test template metadata functionality."""
    
    def test_template_metadata_creation(self, sample_template_data):
        """Test creating template metadata."""
        template = TemplateMetadata.from_dict(sample_template_data)
        assert template.id == "test_template"
        assert template.version == "1.0"
        assert template.description == "Test template for unit tests"
        assert len(template.variables) == 1
        assert template.template == "Analyze this: {input_text}"
    
    def test_compute_hash(self, sample_template_data):
        """Test hash computation."""
        template = TemplateMetadata.from_dict(sample_template_data)
        hash1 = template.compute_hash()
        hash2 = template.compute_hash()
        
        # Same template should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hash length
    
    def test_compute_hash_changes_with_content(self, sample_template_data):
        """Test that hash changes when content changes."""
        template1 = TemplateMetadata.from_dict(sample_template_data)
        hash1 = template1.compute_hash()
        
        # Modify template
        sample_template_data["template"] = "Different template: {input_text}"
        template2 = TemplateMetadata.from_dict(sample_template_data)
        hash2 = template2.compute_hash()
        
        assert hash1 != hash2
    
    def test_to_dict(self, sample_template_data):
        """Test converting template to dict."""
        template = TemplateMetadata.from_dict(sample_template_data)
        result = template.to_dict()
        
        assert result["id"] == "test_template"
        assert result["version"] == "1.0"
        assert "hash" in result
        assert result["template"] == "Analyze this: {input_text}"
    
    def test_to_dict_includes_last_modified(self, sample_template_data):
        """Test that to_dict includes last_modified when set."""
        sample_template_data["last_modified"] = 1234567890.0
        template = TemplateMetadata.from_dict(sample_template_data)
        result = template.to_dict()
        
        assert result["last_modified"] == 1234567890.0


class TestTemplateManager:
    """Test template manager functionality."""
    
    def test_manager_initialization(self, temp_templates_dir):
        """Test basic manager initialization."""
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert manager.templates_dir == temp_templates_dir
        assert manager.redis_client is None
        assert manager._templates == {}
    
    def test_manager_with_redis(self, temp_templates_dir, mock_redis):
        """Test manager with Redis client."""
        manager = TemplateManager(
            temp_templates_dir,
            redis_client=mock_redis,
            hot_reload=False
        )
        assert manager.redis_client == mock_redis
    
    def test_load_yaml_template(self, temp_templates_dir, sample_template_data):
        """Test loading YAML template file."""
        # Create YAML file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert "test_template" in manager._templates
        assert manager._templates["test_template"].version == "1.0"
    
    def test_load_json_template(self, temp_templates_dir, sample_template_data):
        """Test loading JSON template file."""
        # Create JSON file
        template_file = temp_templates_dir / "test_template.json"
        with open(template_file, 'w') as f:
            json.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert "test_template" in manager._templates
    
    def test_load_multiple_templates(self, temp_templates_dir):
        """Test loading multiple template files."""
        # Create multiple templates
        for i in range(3):
            template_data = {
                "id": f"template_{i}",
                "version": "1.0",
                "description": f"Template {i}",
                "variables": [],
                "template": f"Template {i} content"
            }
            template_file = temp_templates_dir / f"template_{i}.yaml"
            with open(template_file, 'w') as f:
                import yaml
                yaml.dump(template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert len(manager._templates) == 3
        assert "template_0" in manager._templates
        assert "template_1" in manager._templates
        assert "template_2" in manager._templates
    
    def test_get_template_from_memory(self, temp_templates_dir, sample_template_data):
        """Test getting template from memory."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        template = manager.get_template("test_template")
        
        assert template == "Analyze this: {input_text}"
    
    def test_get_template_from_redis(self, temp_templates_dir, sample_template_data, mock_redis):
        """Test getting template from Redis cache."""
        # Mock Redis to return cached template
        cached_data = {**sample_template_data, "hash": "test_hash"}
        mock_redis.get.return_value = json.dumps(cached_data)
        
        manager = TemplateManager(
            temp_templates_dir,
            redis_client=mock_redis,
            hot_reload=False
        )
        
        template = manager.get_template("test_template")
        assert template == "Analyze this: {input_text}"
        mock_redis.get.assert_called_once()
    
    def test_get_template_not_found(self, temp_templates_dir):
        """Test getting non-existent template."""
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        template = manager.get_template("nonexistent")
        assert template is None
    
    def test_mirror_to_redis(self, temp_templates_dir, sample_template_data, mock_redis):
        """Test mirroring template to Redis."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(
            temp_templates_dir,
            redis_client=mock_redis,
            hot_reload=False
        )
        
        # Redis set should have been called (twice - once for template, once for version)
        assert mock_redis.set.called
        assert mock_redis.set.call_count >= 1
    
    def test_mirror_to_redis_failure(self, temp_templates_dir, sample_template_data, mock_redis):
        """Test handling Redis mirroring failure."""
        mock_redis.set.side_effect = Exception("Redis connection error")
        
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        # Should not raise exception
        manager = TemplateManager(
            temp_templates_dir,
            redis_client=mock_redis,
            hot_reload=False
        )
        assert "test_template" in manager._templates
    
    def test_reload_template(self, temp_templates_dir, sample_template_data):
        """Test reloading a specific template."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        original_template = manager.get_template("test_template")
        
        # Modify template file
        sample_template_data["template"] = "Modified: {input_text}"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        # Reload
        manager.reload_template("test_template")
        new_template = manager.get_template("test_template")
        
        assert new_template == "Modified: {input_text}"
        assert new_template != original_template
    
    def test_publish_template_update(self, temp_templates_dir, sample_template_data, mock_redis):
        """Test publishing template update via Redis pub/sub."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(
            temp_templates_dir,
            redis_client=mock_redis,
            hot_reload=False
        )
        
        # Modify and reload
        sample_template_data["template"] = "Modified template"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager.reload_template("test_template")
        
        # Should publish update
        assert mock_redis.publish.called
    
    def test_list_templates(self, temp_templates_dir):
        """Test listing all templates."""
        # Create multiple templates
        for i in range(3):
            template_data = {
                "id": f"template_{i}",
                "version": "1.0",
                "description": f"Template {i}",
                "variables": [],
                "template": f"Content {i}"
            }
            template_file = temp_templates_dir / f"template_{i}.yaml"
            with open(template_file, 'w') as f:
                import yaml
                yaml.dump(template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        templates = manager.list_templates()
        
        assert len(templates) == 3
        template_ids = [t["id"] for t in templates]
        assert "template_0" in template_ids
        assert "template_1" in template_ids
        assert "template_2" in template_ids
    
    def test_get_template_metadata(self, temp_templates_dir, sample_template_data):
        """Test getting template metadata."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        metadata = manager.get_template_metadata("test_template")
        
        assert metadata is not None
        assert metadata.id == "test_template"
        assert metadata.version == "1.0"
        assert metadata.compute_hash() is not None
    
    def test_hot_reload_disabled(self, temp_templates_dir):
        """Test manager with hot reload disabled."""
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert manager._observer is None
    
    def test_stop_file_watcher(self, temp_templates_dir):
        """Test stopping file watcher."""
        with patch("watchdog.observers.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer
            
            manager = TemplateManager(temp_templates_dir, hot_reload=True)
            manager.stop_file_watcher()
            
            mock_observer.stop.assert_called_once()
            mock_observer.join.assert_called_once()
    
    def test_unsupported_file_format(self, temp_templates_dir):
        """Test handling of unsupported file format."""
        # Create text file (unsupported)
        template_file = temp_templates_dir / "test_template.txt"
        with open(template_file, 'w') as f:
            f.write("This is not a template")
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert "test_template" not in manager._templates
    
    def test_load_corrupted_yaml(self, temp_templates_dir):
        """Test handling of corrupted YAML file."""
        # Create corrupted YAML
        template_file = temp_templates_dir / "corrupted.yaml"
        with open(template_file, 'w') as f:
            f.write("invalid: yaml: content:\n  - broken")
        
        # Should not raise exception
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        assert "corrupted" not in manager._templates
    
    def test_render_template(self, temp_templates_dir, sample_template_data):
        """Test getting template for manual rendering."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        template_str = manager.get_template("test_template")
        
        # User would render manually using their templating engine
        assert template_str == "Analyze this: {input_text}"
        rendered = template_str.format(input_text="sample input")
        assert rendered == "Analyze this: sample input"
    
    def test_get_template_for_rendering(self, temp_templates_dir, sample_template_data):
        """Test getting template string for external rendering."""
        # Create template file
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        
        template_str = manager.get_template("test_template")
        assert template_str is not None
        assert "{input_text}" in template_str


class TestTemplateFileHandler:
    """Test template file handler for hot reload."""
    
    def test_file_handler_creation(self, temp_templates_dir):
        """Test creating file handler."""
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        handler = TemplateFileHandler(manager)
        assert handler.template_manager == manager
    
    def test_file_handler_ignores_directories(self, temp_templates_dir):
        """Test that handler ignores directory events."""
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        handler = TemplateFileHandler(manager)
        
        # Create mock event for directory
        mock_event = Mock()
        mock_event.is_directory = True
        mock_event.src_path = str(temp_templates_dir / "subdir")
        
        # Should not raise exception
        handler.on_modified(mock_event)
    
    def test_file_handler_processes_yaml(self, temp_templates_dir, sample_template_data):
        """Test that handler processes YAML file changes."""
        # Create initial template
        template_file = temp_templates_dir / "test_template.yaml"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        manager = TemplateManager(temp_templates_dir, hot_reload=False)
        handler = TemplateFileHandler(manager)
        
        # Simulate file modification
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = str(template_file)
        
        # Modify template
        sample_template_data["template"] = "Updated template"
        with open(template_file, 'w') as f:
            import yaml
            yaml.dump(sample_template_data, f)
        
        handler.on_modified(mock_event)
        
        # Template should be reloaded
        assert manager.get_template("test_template") == "Updated template"
