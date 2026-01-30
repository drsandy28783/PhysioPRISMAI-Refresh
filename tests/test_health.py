"""
Health Check Tests
==================

Simple tests to verify the app is running and basic endpoints work.
These should ALWAYS pass - if they don't, something is very wrong!
"""

import pytest


@pytest.mark.critical
def test_app_exists(app):
    """Test that the Flask app was created successfully."""
    assert app is not None
    assert app.config['TESTING'] is True


@pytest.mark.critical
def test_health_endpoint(client):
    """
    Test /api/health endpoint returns 200 OK.

    This is the most basic test - if this fails, the app isn't starting.
    """
    response = client.get('/api/health')

    assert response.status_code == 200
    assert response.json['status'] == 'healthy'


@pytest.mark.api
def test_app_runs_in_test_mode(app):
    """Verify app is configured for testing."""
    assert app.config['TESTING'] is True
    assert app.config['WTF_CSRF_ENABLED'] is False


def test_404_error_handling(client):
    """Test that non-existent endpoints return 404."""
    response = client.get('/api/this-endpoint-does-not-exist')
    assert response.status_code == 404
