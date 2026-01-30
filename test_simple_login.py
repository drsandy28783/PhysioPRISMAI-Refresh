#!/usr/bin/env python3
"""
Simple test endpoint to verify Cosmos DB password verification works.
Add this route to mobile_api.py temporarily for testing.
"""

# Add this to mobile_api.py after the health endpoint:

"""
@mobile_api.route('/login-test', methods=['POST'])
def api_login_test():
    '''
    Simplified login endpoint for testing - only uses Cosmos DB verification
    '''
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.error("===== LOGIN TEST ENDPOINT HIT =====")  # ERROR level to ensure it shows

        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        logger.error(f"Test login for email: {email}, password length: {len(password)}")

        if not email or not password:
            logger.error("Missing email or password")
            return jsonify({'ok': False, 'error': 'Email and password required'}), 400

        # Get user from Cosmos DB  - exactly like web app does
        logger.error(f"Fetching user document for: {email}")
        user_doc = db.collection('users').document(email).get()

        if not user_doc.exists:
            logger.error(f"User not found: {email}")
            return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

        logger.error("User document exists, checking password")
        user_data = user_doc.to_dict()

        # Check password hash
        from werkzeug.security import check_password_hash
        password_hash = user_data.get('password_hash', '')

        logger.error(f"Has password_hash: {bool(password_hash)}")

        if not password_hash:
            logger.error("No password_hash in user document")
            return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

        if not check_password_hash(password_hash, password):
            logger.error("Password verification failed")
            return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

        logger.error("Password verified successfully!")

        # Return success
        return jsonify({
            'ok': True,
            'message': 'Login test successful',
            'email': email,
            'has_firebase_uid': bool(user_data.get('firebase_uid'))
        }), 200

    except Exception as e:
        logger.error(f"Login test exception: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500
"""

print("Add the above code to mobile_api.py after the health endpoint")
print("Then redeploy and test with: https://physiologicprism.com/api/login-test")
