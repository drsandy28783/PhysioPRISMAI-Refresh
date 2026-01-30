"""
Test Configuration and Fixtures for PhysioPRISM
================================================

This file contains pytest fixtures used across all tests.
Fixtures provide reusable test setup and teardown.
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope='session')
def test_env():
    """
    Set up test environment variables.
    These override production settings during tests.
    """
    test_vars = {
        'FLASK_ENV': 'testing',
        'TESTING': 'true',

        # Azure Cosmos DB (will be mocked in tests)
        'AZURE_COSMOS_ENDPOINT': 'https://test-cosmosdb.documents.azure.com:443/',
        'AZURE_COSMOS_KEY': 'test-cosmos-key-for-testing-only',
        'AZURE_COSMOS_DATABASE': 'test-physiologicprism',

        # Azure OpenAI (will be mocked in tests)
        'AZURE_OPENAI_ENDPOINT': 'https://test-openai.openai.azure.com/',
        'AZURE_OPENAI_KEY': 'test-openai-key-for-testing-only',
        'AZURE_OPENAI_DEPLOYMENT': 'test-gpt-4o',

        # Firebase (will be mocked)
        'FIREBASE_CREDENTIALS_PATH': 'test-firebase-credentials.json',

        # Disable external services during tests
        'SENTRY_DSN': '',  # No Sentry in tests
        'REDIS_HOST': 'localhost',  # Will use in-memory fallback

        # App settings
        'SECRET_KEY': 'test-secret-key-not-for-production',
        'FLASK_DEBUG': 'false',
    }

    # Set test environment variables
    for key, value in test_vars.items():
        os.environ[key] = value

    yield test_vars

    # Cleanup (optional - pytest does this automatically)


@pytest.fixture(scope='function')
def app(test_env):
    """
    Create Flask app instance for testing.

    Returns:
        Flask app in testing mode
    """
    # Import here to avoid issues with environment variables
    from main import app as flask_app

    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests

    return flask_app


@pytest.fixture(scope='function')
def client(app):
    """
    Create Flask test client.

    Usage in tests:
        def test_something(client):
            response = client.get('/api/health')
            assert response.status_code == 200
    """
    return app.test_client()


@pytest.fixture(scope='function')
def mock_cosmos_db():
    """
    Mock Azure Cosmos DB for tests.
    Returns a mock that simulates database operations.
    """
    with patch('azure_cosmos_db.get_cosmos_db') as mock:
        # Mock database instance
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Mock common database methods
        mock_instance.get_document.return_value = {
            'id': 'test-user@example.com',
            'name': 'Test User',
            'email': 'test-user@example.com',
            'role': 'individual',
            'approved': 1,
            'active': 1
        }

        mock_instance.create_document.return_value = {
            'id': 'test-patient-123',
            'name': 'Test Patient',
            'created': True
        }

        mock_instance.query_documents.return_value = []

        yield mock_instance


@pytest.fixture(scope='function')
def mock_azure_openai():
    """
    Mock Azure OpenAI for tests.
    Prevents actual API calls during testing.
    """
    with patch('azure_openai_client.get_azure_openai_client') as mock:
        # Mock the client instance
        mock_client = MagicMock()
        mock.return_value = mock_client

        # Mock the main methods used for clinical suggestions
        mock_client.generate_clinical_suggestion.return_value = "This is a mocked AI clinical suggestion for testing purposes."
        mock_client.generate_json_response.return_value = {
            "suggestion": "Mocked AI suggestion",
            "confidence": "high"
        }
        mock_client.create_chat_completion.return_value = {
            "text": "Mocked chat completion",
            "content": [{"text": "Mocked chat completion"}],
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        }

        yield mock_client


@pytest.fixture(scope='function')
def mock_firebase_auth():
    """
    Mock Firebase Authentication for tests.
    """
    with patch('firebase_admin.auth') as mock_auth:
        # Mock successful token verification
        mock_auth.verify_id_token.return_value = {
            'uid': 'test-firebase-uid-123',
            'email': 'test-user@example.com'
        }

        # Mock user creation
        mock_auth.create_user.return_value = MagicMock(uid='test-firebase-uid-123')

        # Mock custom token creation
        mock_auth.create_custom_token.return_value = b'test-custom-token'

        yield mock_auth


@pytest.fixture(scope='function')
def auth_headers(client, mock_firebase_auth, mock_cosmos_db):
    """
    Fixture that provides authentication headers for tests.

    Usage:
        def test_protected_endpoint(client, auth_headers):
            response = client.get('/api/patients', headers=auth_headers)
            assert response.status_code == 200
    """
    # Simulate login to get token
    with patch('app_auth.require_firebase_auth'):
        # Return mock headers
        return {
            'Authorization': 'Bearer test-token-123',
            'Content-Type': 'application/json'
        }


@pytest.fixture(scope='function')
def sample_patient_data():
    """
    Sample patient data for testing.
    """
    return {
        'name': 'John Doe',
        'age_sex': '45/M',
        'contact': '9876543210',
        'email': 'john.doe@example.com',
        'chief_complaint': 'Right shoulder pain for 2 weeks',
        'medical_history': 'No significant medical history',
        'occupation': 'Software Engineer'
    }


@pytest.fixture(scope='function')
def sample_user_data():
    """
    Sample user registration data for testing.
    """
    return {
        'name': 'Test Physio',
        'email': 'test.physio@example.com',
        'password': 'SecurePassword123!',
        'phone': '9876543210',
        'institute': 'Test Physiotherapy Clinic'
    }


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Automatically run after each test.
    Cleans up any test artifacts.
    """
    yield
    # Cleanup code here if needed
    pass
