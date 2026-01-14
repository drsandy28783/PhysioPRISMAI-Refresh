"""
Azure AD B2C Authentication Module
Simple email/password authentication that preserves your existing approval workflow
Replaces Firebase Authentication while keeping the same user experience
"""

import os
import msal
from typing import Dict, Any, Optional
from functools import wraps
from flask import session, redirect, url_for, request, flash


class AzureADB2CAuth:
    """
    Simple Azure AD B2C authentication wrapper
    Preserves your existing registration → approval → login workflow
    """

    def __init__(
        self,
        tenant_name: str = None,
        client_id: str = None,
        client_secret: str = None,
        authority: str = None,
        signup_signin_policy: str = None,
        password_reset_policy: str = None,
        redirect_uri: str = None
    ):
        """
        Initialize Azure AD B2C authentication

        Args:
            tenant_name: B2C tenant name (e.g., 'physiologicprismb2c')
            client_id: Application client ID
            client_secret: Application client secret
            authority: B2C authority URL
            signup_signin_policy: Sign-up/sign-in policy name
            password_reset_policy: Password reset policy name
            redirect_uri: OAuth redirect URI
        """
        # Load configuration from environment
        self.tenant_name = tenant_name or os.getenv('AZURE_AD_B2C_TENANT_NAME')
        self.client_id = client_id or os.getenv('AZURE_AD_B2C_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('AZURE_AD_B2C_CLIENT_SECRET')
        self.authority_base = authority or os.getenv('AZURE_AD_B2C_AUTHORITY')
        self.signup_signin_policy = signup_signin_policy or os.getenv('AZURE_AD_B2C_SIGNUP_SIGNIN_POLICY', 'B2C_1_signupsignin')
        self.password_reset_policy = password_reset_policy or os.getenv('AZURE_AD_B2C_PASSWORD_RESET_POLICY', 'B2C_1_passwordreset')
        self.redirect_uri = redirect_uri or os.getenv('AZURE_AD_B2C_REDIRECT_URI', 'http://localhost:5000/auth/callback')

        # Build authority URLs
        self.authority_signin = f"{self.authority_base}/{self.tenant_name}.onmicrosoft.com/{self.signup_signin_policy}"
        self.authority_password_reset = f"{self.authority_base}/{self.tenant_name}.onmicrosoft.com/{self.password_reset_policy}"

        # Scopes
        self.scopes = [f"https://{self.tenant_name}.onmicrosoft.com/{self.client_id}/user_impersonation"]

        # Check if B2C is configured
        self.is_configured = bool(self.client_id and self.client_secret and self.tenant_name)

        if not self.is_configured:
            print("⚠️ Azure AD B2C not configured. Set AZURE_AD_B2C_* environment variables.")

    def create_msal_app(self, authority: str = None) -> msal.ConfidentialClientApplication:
        """Create MSAL application instance"""
        return msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority or self.authority_signin,
            client_credential=self.client_secret
        )

    def get_auth_url(self, state: str = None) -> str:
        """
        Get authorization URL for login/signup

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if not self.is_configured:
            raise ValueError("Azure AD B2C not configured")

        msal_app = self.create_msal_app()

        auth_url = msal_app.get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri
        )

        return auth_url

    def get_password_reset_url(self, state: str = None) -> str:
        """
        Get password reset URL

        Args:
            state: Optional state parameter

        Returns:
            Password reset URL
        """
        if not self.is_configured:
            raise ValueError("Azure AD B2C not configured")

        msal_app = self.create_msal_app(authority=self.authority_password_reset)

        reset_url = msal_app.get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri
        )

        return reset_url

    def acquire_token_by_auth_code(self, auth_code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for tokens

        Args:
            auth_code: Authorization code from callback

        Returns:
            Token response dict with access_token, id_token, etc.
        """
        if not self.is_configured:
            raise ValueError("Azure AD B2C not configured")

        msal_app = self.create_msal_app()

        result = msal_app.acquire_token_by_authorization_code(
            code=auth_code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )

        if "error" in result:
            print(f"Token acquisition error: {result.get('error_description')}")
            return None

        return result

    def validate_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate ID token and extract user info

        Args:
            id_token: JWT ID token from Azure AD B2C

        Returns:
            Decoded token claims (user info)
        """
        try:
            # For production, you should validate the token signature
            # For now, we'll decode without validation (development only)
            import jwt
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            return decoded
        except Exception as e:
            print(f"Token validation error: {e}")
            return None

    def get_user_from_token(self, token_response: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Extract user information from token response

        Args:
            token_response: Token response from acquire_token_*

        Returns:
            Dict with user email and name
        """
        if not token_response or "id_token_claims" not in token_response:
            return None

        claims = token_response["id_token_claims"]

        return {
            "email": claims.get("emails", [None])[0] or claims.get("email"),
            "name": claims.get("name"),
            "given_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "oid": claims.get("oid"),  # Object ID (unique user ID)
            "sub": claims.get("sub")   # Subject (also unique)
        }


def require_b2c_auth(f):
    """
    Decorator to require Azure AD B2C authentication
    Similar to @login_required but for B2C

    Usage:
        @app.route('/protected')
        @require_b2c_auth
        def protected_route():
            return "Protected content"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))

        return f(*args, **kwargs)

    return decorated_function


# Singleton instance
_azure_b2c_instance = None


def get_azure_b2c() -> AzureADB2CAuth:
    """Get or create Azure AD B2C instance (singleton)"""
    global _azure_b2c_instance
    if _azure_b2c_instance is None:
        _azure_b2c_instance = AzureADB2CAuth()
    return _azure_b2c_instance


def is_b2c_configured() -> bool:
    """Check if Azure AD B2C is configured"""
    b2c = get_azure_b2c()
    return b2c.is_configured
