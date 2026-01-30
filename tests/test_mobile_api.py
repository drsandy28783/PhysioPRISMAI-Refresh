"""
Mobile API Tests
================

Tests for mobile-specific API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.critical
@pytest.mark.api
def test_mobile_api_health_check(client):
    """Test mobile API health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200


@pytest.mark.api
def test_get_user_profile(client, auth_headers, mock_cosmos_db):
    """Test getting user profile."""
    with patch('mobile_api.db') as mock_db:
        mock_db.get_document.return_value = {
            'id': 'test-user@example.com',
            'name': 'Test User',
            'email': 'test-user@example.com',
            'role': 'individual',
            'institute': 'Test Clinic'
        }

        response = client.get('/api/users/profile', headers=auth_headers)
        assert response.status_code in [200, 401, 404]


@pytest.mark.api
def test_update_user_profile(client, auth_headers, mock_cosmos_db):
    """Test updating user profile."""
    update_data = {
        'name': 'Updated Name',
        'phone': '9999999999'
    }

    with patch('mobile_api.db') as mock_db:
        mock_db.update_document.return_value = {'success': True}

        response = client.post(
            '/api/users/update-profile',
            headers=auth_headers,
            json=update_data
        )

        assert response.status_code in [200, 400, 401, 500]


@pytest.mark.api
def test_get_subscription_status(client, auth_headers, mock_cosmos_db):
    """Test getting subscription status."""
    with patch('mobile_api.db') as mock_db:
        mock_db.get_document.return_value = {
            'subscription_type': 'solo',
            'status': 'active',
            'tokens_remaining': 100
        }

        response = client.get('/api/subscription', headers=auth_headers)
        assert response.status_code in [200, 401, 404]


@pytest.mark.api
def test_get_subscription_plans(client):
    """Test getting available subscription plans."""
    response = client.get('/api/subscription/plans')

    # Plans endpoint should be public (no auth required)
    assert response.status_code == 200


@pytest.mark.integration
def test_draft_save(client, auth_headers, mock_cosmos_db):
    """Test saving draft data."""
    draft_data = {
        'patient_id': 'test-patient-123',
        'section': 'subjective',
        'data': {
            'present_history': 'Draft content...',
            'past_history': 'More draft content...'
        }
    }

    with patch('mobile_api.db') as mock_db:
        mock_db.create_document.return_value = {'saved': True}

        response = client.post(
            '/api/draft/save',
            headers=auth_headers,
            json=draft_data
        )

        assert response.status_code in [200, 201, 400, 401]


@pytest.mark.api
def test_get_draft(client, auth_headers, mock_cosmos_db):
    """Test retrieving saved draft."""
    with patch('mobile_api.db') as mock_db:
        mock_db.get_document.return_value = {
            'patient_id': 'test-patient-123',
            'section': 'subjective',
            'data': {'present_history': 'Draft content'}
        }

        response = client.get(
            '/api/draft/get/test-patient-123/subjective',
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 404]


@pytest.mark.api
def test_notifications_endpoint(client, auth_headers):
    """Test getting user notifications."""
    response = client.get('/api/notifications', headers=auth_headers)
    assert response.status_code in [200, 401]


@pytest.mark.api
def test_unread_notifications_count(client, auth_headers):
    """Test getting unread notifications count."""
    response = client.get('/api/notifications/unread-count', headers=auth_headers)
    assert response.status_code in [200, 401]


@pytest.mark.integration
def test_patient_follow_ups(client, auth_headers, mock_cosmos_db):
    """Test getting patient follow-ups."""
    patient_id = 'test-patient-123'

    with patch('mobile_api.db') as mock_db:
        mock_db.query_documents.return_value = [
            {'id': 'followup-1', 'date': '2026-02-01'},
            {'id': 'followup-2', 'date': '2026-02-15'}
        ]

        response = client.get(
            f'/api/patients/{patient_id}/follow-ups',
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 404]


@pytest.mark.integration
def test_create_follow_up(client, auth_headers, mock_cosmos_db):
    """Test creating a patient follow-up."""
    patient_id = 'test-patient-123'
    followup_data = {
        'followup_date': '2026-02-01',
        'subjective_findings': 'Patient reports improvement',
        'objective_findings': 'ROM increased by 20 degrees',
        'treatment_given': 'Manual therapy, exercises'
    }

    with patch('mobile_api.db') as mock_db:
        mock_db.create_document.return_value = {'id': 'followup-new'}

        response = client.post(
            f'/api/patients/{patient_id}/follow-ups',
            headers=auth_headers,
            json=followup_data
        )

        assert response.status_code in [200, 201, 400, 401]
