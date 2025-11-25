"""Template management system with hot reload and Redis mirroring."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import yaml
from watchdog.events import FileSystemEventHandler

if TYPE_CHECKING:
    from watchdog.observers import Observer

from ..utils.logging import get_logger

logger = get_logger(__name__)


class TemplateMetadata:
    """Template metadata and validation."""
    
    def __init__(
        self,
        id: str,
        version: str,
        description: str,
        variables: List[Dict[str, str]],
        template: str,
        last_modified: Optional[float] = None
    ):
        self.id = id
        self.version = version
        self.description = description
        self.variables = variables
        self.template = template
        self.last_modified = last_modified
    
    def compute_hash(self) -> str:
        """Compute SHA256 hash of template content."""
        content = f"{self.id}{self.version}{self.template}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "variables": self.variables,
            "template": self.template,
            "hash": self.compute_hash(),
            "last_modified": self.last_modified
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateMetadata':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            version=data["version"],
            description=data["description"],
            variables=data["variables"],
            template=data["template"],
            last_modified=data.get("last_modified")
        )


class TemplateFileHandler(FileSystemEventHandler):
    """Watch for template file changes."""
    
    def __init__(self, template_manager: 'TemplateManager'):
        self.template_manager = template_manager
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if event.src_path.endswith(('.yaml', '.yml', '.json')):
            logger.info(f"Template file modified: {event.src_path}")
            # Reload the specific template
            try:
                template_id = Path(event.src_path).stem
                self.template_manager.reload_template(template_id)
            except Exception as e:
                logger.error(f"Failed to reload template: {e}")


class TemplateManager:
    """
    Manages prompt templates with hot reload and Redis mirroring.
    """
    
    def __init__(
        self,
        templates_dir: Path,
        redis_client: Optional[Any] = None,
        hot_reload: bool = True
    ):
        """
        Initialize template manager.
        
        Args:
            templates_dir: Path to templates directory
            redis_client: Optional Redis client for caching
            hot_reload: Enable hot reload via file watching
        """
        self.templates_dir = Path(templates_dir)
        self.redis_client = redis_client
        self.hot_reload = hot_reload
        self._templates: Dict[str, TemplateMetadata] = {}
        self._observer: Optional["Observer"] = None
        
        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Load all templates
        self.load_all_templates()
        
        # Start file watcher if hot reload is enabled
        if hot_reload:
            self._start_file_watcher()
    
    def _start_file_watcher(self):
        """Start watching template directory for changes."""
        try:
            from watchdog.observers import Observer
            self._observer = Observer()
            event_handler = TemplateFileHandler(self)
            self._observer.schedule(event_handler, str(self.templates_dir), recursive=False)
            self._observer.start()
            logger.info(f"Template hot reload enabled for {self.templates_dir}")
        except Exception as e:
            logger.warning(f"Failed to start file watcher: {e}")
    
    def stop_file_watcher(self):
        """Stop the file watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("Template file watcher stopped")
    
    def _load_template_file(self, file_path: Path) -> Optional[TemplateMetadata]:
        """
        Load a single template file.
        
        Args:
            file_path: Path to template file
            
        Returns:
            TemplateMetadata or None on error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix == '.json':
                    data = json.load(f)
                else:
                    logger.warning(f"Unsupported template file format: {file_path}")
                    return None
            
            # Add last modified timestamp
            data['last_modified'] = file_path.stat().st_mtime
            
            template = TemplateMetadata.from_dict(data)
            logger.debug(f"Loaded template: {template.id} v{template.version}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to load template {file_path}: {e}")
            return None
    
    def load_all_templates(self):
        """Load all templates from the templates directory."""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return
        
        loaded_count = 0
        for file_path in self.templates_dir.glob('*'):
            if file_path.suffix in ['.yaml', '.yml', '.json']:
                template = self._load_template_file(file_path)
                if template:
                    self._templates[template.id] = template
                    self._mirror_to_redis(template)
                    loaded_count += 1
        
        logger.info(f"Loaded {loaded_count} templates from {self.templates_dir}")
    
    def reload_template(self, template_id: str):
        """
        Reload a specific template from disk.
        
        Args:
            template_id: Template ID to reload
        """
        # Find the file
        for ext in ['.yaml', '.yml', '.json']:
            file_path = self.templates_dir / f"{template_id}{ext}"
            if file_path.exists():
                template = self._load_template_file(file_path)
                if template:
                    old_template = self._templates.get(template_id)
                    self._templates[template_id] = template
                    self._mirror_to_redis(template)
                    
                    # Publish update if hash changed
                    if old_template and old_template.compute_hash() != template.compute_hash():
                        self._publish_template_update(template_id)
                        logger.info(f"Template {template_id} updated and published")
                break
    
    def _mirror_to_redis(self, template: TemplateMetadata):
        """
        Mirror template to Redis for fast access.
        
        Args:
            template: Template to mirror
        """
        if not self.redis_client:
            return
        
        try:
            key = f"template:{template.id}"
            version_key = f"template_version:{template.id}"
            
            # Store template data
            self.redis_client.set(
                key,
                json.dumps(template.to_dict()),
                ex=604800  # 1 week TTL
            )
            
            # Store template hash for version checking
            self.redis_client.set(version_key, template.compute_hash())
            
            logger.debug(f"Mirrored template {template.id} to Redis")
        except Exception as e:
            logger.error(f"Failed to mirror template to Redis: {e}")
    
    def _publish_template_update(self, template_id: str):
        """
        Publish template update event via Redis pub/sub.
        
        Args:
            template_id: ID of updated template
        """
        if not self.redis_client:
            return
        
        try:
            channel = f"templates:updated:{template_id}"
            self.redis_client.publish(channel, template_id)
            logger.debug(f"Published template update: {template_id}")
        except Exception as e:
            logger.error(f"Failed to publish template update: {e}")
    
    def get_template(self, template_id: str) -> Optional[str]:
        """
        Get template string by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template string or None if not found
        """
        # Try Redis first if available
        if self.redis_client:
            try:
                key = f"template:{template_id}"
                cached = self.redis_client.get(key)
                if cached:
                    data = json.loads(cached)
                    return data['template']
            except Exception as e:
                logger.warning(f"Redis template fetch failed: {e}")
        
        # Fall back to in-memory cache
        template = self._templates.get(template_id)
        if template:
            return template.template
        
        logger.warning(f"Template not found: {template_id}")
        return None
    
    def get_template_metadata(self, template_id: str) -> Optional[TemplateMetadata]:
        """
        Get full template metadata.
        
        Args:
            template_id: Template ID
            
        Returns:
            TemplateMetadata or None
        """
        return self._templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates.
        
        Returns:
            List of template metadata dictionaries
        """
        return [t.to_dict() for t in self._templates.values()]
    
    def save_template(self, template: TemplateMetadata, format: str = 'yaml') -> bool:
        """
        Save template to disk.
        
        Args:
            template: Template to save
            format: File format ('yaml' or 'json')
            
        Returns:
            True if successful
        """
        try:
            file_path = self.templates_dir / f"{template.id}.{format}"
            data = template.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == 'yaml':
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(data, f, indent=2)
            
            # Update in-memory cache and Redis
            self._templates[template.id] = template
            self._mirror_to_redis(template)
            self._publish_template_update(template.id)
            
            logger.info(f"Saved template: {template.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save template {template.id}: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete template.
        
        Args:
            template_id: Template ID to delete
            
        Returns:
            True if successful
        """
        try:
            # Remove from disk
            for ext in ['.yaml', '.yml', '.json']:
                file_path = self.templates_dir / f"{template_id}{ext}"
                if file_path.exists():
                    file_path.unlink()
            
            # Remove from memory
            if template_id in self._templates:
                del self._templates[template_id]
            
            # Remove from Redis
            if self.redis_client:
                self.redis_client.delete(f"template:{template_id}")
                self.redis_client.delete(f"template_version:{template_id}")
            
            logger.info(f"Deleted template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template {template_id}: {e}")
            return False
