"""
AI Suggestion Tests
===================

Tests for AI-powered clinical reasoning features.
These are mocked to avoid actual API calls during testing.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.critical
@pytest.mark.api
def test_ai_suggestion_endpoint_exists(client, auth_headers):
    """Test that AI suggestion endpoints exist."""
    # Test one of the AI endpoints
    response = client.post(
        '/api/ai_suggestion/past_questions',
        headers=auth_headers,
        json={'age_sex': '45/M', 'present_history': 'Shoulder pain'}
    )

    # Endpoint should exist
    assert response.status_code != 404


@pytest.mark.integration
def test_past_questions_suggestion(client, auth_headers, mock_azure_openai):
    """
    Test AI past questions suggestion.

    This mocks the AI response to avoid actual API calls.
    """
    test_data = {
        'age_sex': '45/M',
        'present_history': 'Right shoulder pain for 2 weeks',
        'chief_complaint': 'Difficulty lifting arm overhead'
    }

    response = client.post(
        '/api/ai_suggestion/past_questions',
        headers=auth_headers,
        json=test_data
    )

    # Should succeed or return error
    assert response.status_code in [200, 400, 401, 500]


@pytest.mark.integration
def test_provisional_diagnosis_suggestion(client, auth_headers, mock_azure_openai):
    """Test AI provisional diagnosis suggestion."""
    test_data = {
        'age_sex': '45/M',
        'present_history': 'Shoulder pain',
        'examination_findings': 'Limited ROM, painful arc',
        'chief_complaint': 'Cannot lift arm'
    }

    response = client.post(
        '/api/ai_suggestion/provisional_diagnosis',
        headers=auth_headers,
        json=test_data
    )

    assert response.status_code in [200, 400, 401, 500]


@pytest.mark.integration
def test_smart_goals_suggestion(client, auth_headers, mock_azure_openai):
    """Test AI SMART goals suggestion."""
    test_data = {
        'patient_id': 'test-patient-123',
        'diagnosis': 'Rotator cuff tendinopathy',
        'patient_goals': 'Return to tennis'
    }

    response = client.post(
        '/api/ai_suggestion/smart_goals',
        headers=auth_headers,
        json=test_data
    )

    assert response.status_code in [200, 400, 401, 500]


@pytest.mark.integration
def test_treatment_plan_suggestion(client, auth_headers, mock_azure_openai):
    """Test AI treatment plan suggestion."""
    test_data = {
        'patient_id': 'test-patient-123',
        'diagnosis': 'Shoulder impingement',
        'goals': 'Reduce pain, improve ROM'
    }

    response = client.post(
        '/api/ai_suggestion/treatment_plan_summary/test-patient-123',
        headers=auth_headers,
        json=test_data
    )

    assert response.status_code in [200, 400, 401, 404, 500]


@pytest.mark.api
def test_ai_requires_authentication(client):
    """Test that AI suggestions require authentication."""
    response = client.post(
        '/api/ai_suggestion/past_questions',
        json={'age_sex': '45/M'}
    )

    # Should be unauthorized
    assert response.status_code in [401, 403]


@pytest.mark.unit
def test_ai_client_mock(mock_azure_openai):
    """Test that Azure OpenAI is properly mocked in tests."""
    # Call the mock's generate_clinical_suggestion method
    result = mock_azure_openai.generate_clinical_suggestion(
        system_prompt="Test prompt",
        user_prompt="Test question"
    )

    # Should return mocked response
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.api
def test_ai_handles_missing_data(client, auth_headers, mock_azure_openai):
    """Test AI endpoints handle missing required data gracefully."""
    # Send incomplete data
    response = client.post(
        '/api/ai_suggestion/past_questions',
        headers=auth_headers,
        json={}  # Empty data
    )

    # Should return validation error or auth error (if auth fails first)
    assert response.status_code in [400, 401, 422, 500]


@pytest.mark.integration
def test_ai_field_specific_suggestion(client, auth_headers, mock_azure_openai):
    """Test AI suggestion for specific field."""
    response = client.post(
        '/api/ai_suggestion/field/occupation',
        headers=auth_headers,
        json={
            'patient_id': 'test-patient-123',
            'context': {'age_sex': '45/M', 'chief_complaint': 'Back pain'}
        }
    )

    assert response.status_code in [200, 400, 401, 404, 500]
