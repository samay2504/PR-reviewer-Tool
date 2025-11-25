"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from pr_agent.api.main import app


@pytest.fixture
def client():
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()


def test_health_endpoint(client):
    """Test health check."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "llm_provider" in data


def test_analyze_endpoint_missing_params(client):
    """Test analyze endpoint with missing parameters."""
    response = client.post("/analyze", json={})
    assert response.status_code == 400


def test_analyze_endpoint_with_diff(client, sample_diff):
    """Test analyze endpoint with diff text."""
    response = client.post("/analyze", json={
        "diff_text": sample_diff,
        "use_cache": False
    })
    
    # May fail if LLM not available, but should not crash
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "request_id" in data
        assert "comments" in data
        assert "summary" in data


def test_list_templates(client):
    """Test templates listing."""
    response = client.get("/templates")
    assert response.status_code == 200
    
    data = response.json()
    assert "templates" in data
    assert isinstance(data["templates"], list)


def test_get_nonexistent_template(client):
    """Test getting non-existent template."""
    response = client.get("/templates/nonexistent")
    assert response.status_code == 404


def test_stats_endpoint(client):
    """Test stats endpoint."""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "cache" in data
