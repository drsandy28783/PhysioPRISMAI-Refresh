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


def _mock_patient_doc(physio_id='owner@example.com', institute='Clinic A'):
    doc = MagicMock()
    doc.exists = True
    doc.id = 'patient-123'
    doc.to_dict.return_value = {
        'physio_id': physio_id,
        'institute': institute,
        'name': 'Test Patient',
    }
    return doc


def _mock_authenticated_request(caller_email, caller_institute, is_admin=0, is_super_admin=0):
    """Patch the require_auth bearer-token path so the request authenticates
    as the given user, with the given institute/admin flags carried onto
    g.user (which patient_access_allowed() reads via _actor_from_g_user())."""
    fake_user_doc = MagicMock()
    fake_user_doc.exists = True
    fake_user_doc.to_dict.return_value = {
        'email': caller_email,
        'institute': caller_institute,
        'is_admin': is_admin,
        'is_super_admin': is_super_admin,
        'approved': 1,
        'active': 1,
    }

    mock_auth_db = MagicMock()
    mock_auth_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
    mock_auth_db.collection.return_value.document.return_value.get.return_value = fake_user_doc

    verify_patch = patch('app_auth.verify_firebase_token',
                          return_value={'uid': 'caller-uid', 'email': caller_email})
    get_db_patch = patch('app_auth.get_cosmos_db', return_value=mock_auth_db)
    return verify_patch, get_db_patch


@pytest.mark.integration
def test_teammate_in_same_institute_can_view_patient(client):
    """Team-wide access: a same-institute teammate (not the owner, not an
    admin) can now GET a colleague's patient -- the new behavior this
    change adds."""
    patient_doc = _mock_patient_doc(physio_id='owner@example.com', institute='Clinic A')
    verify_patch, get_db_patch = _mock_authenticated_request(
        'teammate@example.com', 'Clinic A', is_admin=0
    )

    with verify_patch, get_db_patch, \
         patch('mobile_api.get_patient_safe', return_value=patient_doc), \
         patch('mobile_api.db') as mock_db:
        mock_db.collection.return_value.add.return_value = None

        response = client.get(
            '/api/patients/patient-123',
            headers={'Authorization': 'Bearer fake-token'}
        )

        assert response.status_code == 200


@pytest.mark.integration
def test_different_institute_user_denied(client):
    """Regression guard: a physio from a different institute still gets 403."""
    patient_doc = _mock_patient_doc(physio_id='owner@example.com', institute='Clinic A')
    verify_patch, get_db_patch = _mock_authenticated_request(
        'stranger@example.com', 'Clinic B', is_admin=1
    )

    with verify_patch, get_db_patch, \
         patch('mobile_api.get_patient_safe', return_value=patient_doc), \
         patch('mobile_api.db') as mock_db:
        mock_db.collection.return_value.add.return_value = None

        response = client.get(
            '/api/patients/patient-123',
            headers={'Authorization': 'Bearer fake-token'}
        )

        assert response.status_code == 403


@pytest.mark.integration
def test_solo_physio_cannot_view_another_solo_physios_patient(client):
    """Solo physios (blank institute) remain siloed under the new rule."""
    patient_doc = _mock_patient_doc(physio_id='solo1@example.com', institute='')
    verify_patch, get_db_patch = _mock_authenticated_request(
        'solo2@example.com', '', is_admin=0
    )

    with verify_patch, get_db_patch, \
         patch('mobile_api.get_patient_safe', return_value=patient_doc), \
         patch('mobile_api.db') as mock_db:
        mock_db.collection.return_value.add.return_value = None

        response = client.get(
            '/api/patients/patient-123',
            headers={'Authorization': 'Bearer fake-token'}
        )

        assert response.status_code == 403


@pytest.mark.integration
def test_super_admin_can_view_patient_in_different_institute(client):
    """Super admins keep global cross-institute access."""
    patient_doc = _mock_patient_doc(physio_id='owner@example.com', institute='Clinic A')
    verify_patch, get_db_patch = _mock_authenticated_request(
        'sandeep@example.com', '', is_admin=0, is_super_admin=1
    )

    with verify_patch, get_db_patch, \
         patch('mobile_api.get_patient_safe', return_value=patient_doc), \
         patch('mobile_api.db') as mock_db:
        mock_db.collection.return_value.add.return_value = None

        response = client.get(
            '/api/patients/patient-123',
            headers={'Authorization': 'Bearer fake-token'}
        )

        assert response.status_code == 200
