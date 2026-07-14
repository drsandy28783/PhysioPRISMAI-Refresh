"""
Tests for:
- POST /api/institute/invite-member (institute admin adds a team member directly)
- register_with_institute() web route's hard block when no matching institute admin exists
"""

import pytest
from unittest.mock import patch, MagicMock


def _mock_admin_request(caller_email='admin@example.com', caller_institute='Clinic A', is_admin=1):
    """Patch require_auth's bearer-token path so the request authenticates
    as an institute admin, matching the pattern used in tests/test_patients.py."""
    fake_user_doc = MagicMock()
    fake_user_doc.exists = True
    fake_user_doc.to_dict.return_value = {
        'email': caller_email,
        'institute': caller_institute,
        'is_admin': is_admin,
        'is_super_admin': 0,
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
def test_institute_admin_can_invite_team_member(client):
    """Institute admin invites -> user doc created auto-approved, institute
    taken from the caller (not client input), Firebase user created, email sent."""
    verify_patch, get_db_patch = _mock_admin_request()

    new_user_doc = MagicMock()
    new_user_doc.exists = False  # not a duplicate

    with verify_patch, get_db_patch, \
         patch('main.db') as mock_db, \
         patch('main.auth') as mock_firebase_auth, \
         patch('subscription_manager.check_user_limit', return_value=(True, '', 2, 10)), \
         patch('main.send_team_invite_notification', return_value=True) as mock_send_email:

        mock_db.collection.return_value.document.return_value.get.return_value = new_user_doc
        mock_firebase_auth.create_user.return_value = MagicMock(uid='new-firebase-uid')

        response = client.post(
            '/api/institute/invite-member',
            headers={'Authorization': 'Bearer fake-token'},
            json={'name': 'New Physio', 'email': 'newphysio@example.com', 'phone': '1234567890'}
        )

        assert response.status_code == 201
        assert response.get_json()['ok'] is True

        # The created doc must carry the ADMIN's own institute, not anything
        # the client could have supplied (client sent no institute field at all).
        set_calls = [c for c in mock_db.collection.return_value.document.return_value.set.call_args_list]
        assert len(set_calls) == 1
        created_doc = set_calls[0].args[0]
        assert created_doc['institute'] == 'Clinic A'
        assert created_doc['institute_id'] == 'admin@example.com'
        assert created_doc['approved'] == 1
        assert created_doc['active'] == 1
        assert created_doc['is_admin'] == 0

        mock_send_email.assert_called_once()


@pytest.mark.integration
def test_invite_blocked_for_duplicate_email(client):
    verify_patch, get_db_patch = _mock_admin_request()

    existing_user_doc = MagicMock()
    existing_user_doc.exists = True

    with verify_patch, get_db_patch, patch('main.db') as mock_db:
        mock_db.collection.return_value.document.return_value.get.return_value = existing_user_doc

        response = client.post(
            '/api/institute/invite-member',
            headers={'Authorization': 'Bearer fake-token'},
            json={'name': 'Dup', 'email': 'existing@example.com'}
        )

        assert response.status_code == 409
        assert response.get_json()['error'] == 'EMAIL_EXISTS'


@pytest.mark.integration
def test_invite_blocked_for_non_admin_caller(client):
    verify_patch, get_db_patch = _mock_admin_request(is_admin=0)

    with verify_patch, get_db_patch:
        response = client.post(
            '/api/institute/invite-member',
            headers={'Authorization': 'Bearer fake-token'},
            json={'name': 'Someone', 'email': 'someone@example.com'}
        )

        assert response.status_code == 403
        assert response.get_json()['error'] == 'ADMIN_REQUIRED'


@pytest.mark.integration
def test_invite_blocked_when_user_limit_reached(client):
    verify_patch, get_db_patch = _mock_admin_request()

    new_user_doc = MagicMock()
    new_user_doc.exists = False

    with verify_patch, get_db_patch, \
         patch('main.db') as mock_db, \
         patch('subscription_manager.check_user_limit',
               return_value=(False, 'Plan limit reached', 10, 10)):
        mock_db.collection.return_value.document.return_value.get.return_value = new_user_doc

        response = client.post(
            '/api/institute/invite-member',
            headers={'Authorization': 'Bearer fake-token'},
            json={'name': 'New Physio', 'email': 'newphysio2@example.com'}
        )

        assert response.status_code == 403
        assert response.get_json()['error'] == 'USER_LIMIT_REACHED'


@pytest.mark.integration
def test_register_with_institute_blocks_on_no_matching_admin(client):
    """Regression test for the web hard-block fix: a typo'd/nonexistent
    institute name must NOT silently create an orphaned account."""
    with patch('main.db') as mock_db:
        # No existing user/phone matches, and no admin matches the institute name
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []

        response = client.post('/register_with_institute', data={
            'name': 'Ghost Staff',
            'email': 'ghost@example.com',
            'phone': '9999999999',
            'password': 'SecurePassword123',
            'institute': 'Nonexistent Clinic',
        })

        # Must redirect back to the form (blocked), not proceed to create the account
        assert response.status_code == 302
        assert '/register_with_institute' in response.headers.get('Location', '')

        # The account must never have been written
        mock_db.collection.return_value.document.return_value.set.assert_not_called()
