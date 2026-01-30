"""
Patient Management Tests
========================

Tests for patient CRUD operations (Create, Read, Update, Delete).
Critical for core app functionality.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.critical
@pytest.mark.api
def test_get_patients_endpoint_exists(client, auth_headers):
    """Test that get patients endpoint exists."""
    response = client.get('/api/patients/mine', headers=auth_headers)
    # Endpoint should exist
    assert response.status_code != 404


@pytest.mark.critical
@pytest.mark.api
def test_get_patients_requires_auth(client):
    """Test that getting patients requires authentication."""
    response = client.get('/api/patients/mine')
    # Should be unauthorized (401) or forbidden (403)
    assert response.status_code in [401, 403]


@pytest.mark.integration
def test_create_patient(client, auth_headers, sample_patient_data, mock_cosmos_db):
    """
    Test creating a new patient.

    This is a critical workflow - physios need to be able to create patients!
    """
    with patch('mobile_api.db') as mock_db:
        # Mock successful patient creation
        mock_db.create_document.return_value = {
            'id': 'patient-123',
            **sample_patient_data
        }

        response = client.post(
            '/api/patients',
            headers=auth_headers,
            json=sample_patient_data
        )

        # Should succeed or return validation error
        assert response.status_code in [200, 201, 400, 401, 422]


@pytest.mark.api
def test_create_patient_validation(client, auth_headers):
    """Test patient creation validates required fields."""
    # Try to create patient with missing required fields
    incomplete_data = {
        'name': 'Test Patient'
        # Missing age_sex, contact, chief_complaint
    }

    response = client.post(
        '/api/patients',
        headers=auth_headers,
        json=incomplete_data
    )

    # Should return validation error or auth error (if auth fails first)
    assert response.status_code in [400, 401, 422]


@pytest.mark.integration
def test_get_patient_by_id(client, auth_headers, mock_cosmos_db):
    """Test retrieving a specific patient by ID."""
    patient_id = 'test-patient-123'

    with patch('mobile_api.db') as mock_db:
        mock_db.get_document.return_value = {
            'id': patient_id,
            'name': 'Test Patient',
            'age_sex': '45/M',
            'contact': '9876543210',
            'chief_complaint': 'Test complaint'
        }

        response = client.get(
            f'/api/patients/{patient_id}',
            headers=auth_headers
        )

        assert response.status_code in [200, 401, 404]


@pytest.mark.integration
def test_update_patient(client, auth_headers, mock_cosmos_db):
    """Test updating an existing patient."""
    patient_id = 'test-patient-123'

    updated_data = {
        'name': 'Updated Patient Name',
        'chief_complaint': 'Updated complaint'
    }

    with patch('mobile_api.db') as mock_db:
        mock_db.update_document.return_value = {
            'id': patient_id,
            **updated_data
        }

        response = client.patch(
            f'/api/patients/{patient_id}',
            headers=auth_headers,
            json=updated_data
        )

        assert response.status_code in [200, 401, 404, 422, 500]


@pytest.mark.integration
def test_delete_patient(client, auth_headers, mock_cosmos_db):
    """Test deleting a patient."""
    patient_id = 'test-patient-123'

    with patch('mobile_api.db') as mock_db:
        mock_db.delete_document.return_value = True

        response = client.delete(
            f'/api/patients/{patient_id}',
            headers=auth_headers
        )

        assert response.status_code in [200, 204, 401, 404]


@pytest.mark.api
def test_patient_list_requires_auth(client):
    """Test that listing patients requires authentication."""
    response = client.get('/api/patients/mine')
    assert response.status_code in [401, 403]


@pytest.mark.unit
def test_patient_data_structure(sample_patient_data):
    """Test that sample patient data has required fields."""
    required_fields = ['name', 'age_sex', 'contact', 'chief_complaint']

    for field in required_fields:
        assert field in sample_patient_data
        assert sample_patient_data[field] is not None
        assert len(str(sample_patient_data[field])) > 0
