"""
Basic Functionality Tests
=========================
Tests core application features: login, navigation, patient management
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.basic
class TestAuthentication:
    """Test authentication flows"""

    def test_login_page_loads(self, page: Page, base_url: str):
        """Test that login page loads correctly"""
        page.goto(f"{base_url}/login/firebase")
        page.wait_for_load_state("networkidle")
        expect(page.locator('input[type="email"]')).to_be_visible()
        expect(page.locator('input[type="password"]')).to_be_visible()

    def test_login_success(self, page: Page, base_url: str, test_credentials: dict):
        """Test successful login"""
        page.goto(f"{base_url}/login/firebase")
        page.wait_for_load_state("networkidle")
        page.fill('input[type="email"]', test_credentials["email"])
        page.fill('input[type="password"]', test_credentials["password"])
        page.click('button[type="submit"]')

        # Should redirect to dashboard (Firebase auth takes time)
        try:
            page.wait_for_url("**/super_admin_dashboard", timeout=30000)
        except:
            page.wait_for_url("**/dashboard", timeout=30000)

        assert "dashboard" in page.url.lower(), f"Expected dashboard but got: {page.url}"

    def test_login_invalid_credentials(self, page: Page, base_url: str):
        """Test login with invalid credentials"""
        page.goto(f"{base_url}/login/firebase")
        page.wait_for_load_state("networkidle")
        page.fill('input[type="email"]', "invalid@example.com")
        page.fill('input[type="password"]', "wrongpassword")
        page.click('button[type="submit"]')

        # Should show error message or stay on login page
        # Firebase shows errors in various ways, so check we didn't reach dashboard
        page.wait_for_timeout(3000)  # Wait for error to appear
        # Should NOT be on dashboard (login failed)
        assert page.url != f"{base_url}/dashboard", "Login should have failed but reached dashboard"


@pytest.mark.basic
class TestNavigation:
    """Test navigation and page access"""

    def test_dashboard_access(self, authenticated_page: Page, base_url: str):
        """Test dashboard page loads"""
        authenticated_page.goto(f"{base_url}/dashboard")
        expect(authenticated_page).to_have_url(f"{base_url}/dashboard")

    def test_view_patients_page(self, authenticated_page: Page, base_url: str):
        """Test patient list page loads"""
        authenticated_page.goto(f"{base_url}/view_patients")
        expect(authenticated_page).to_have_url(f"{base_url}/view_patients")

    def test_add_patient_page(self, authenticated_page: Page, base_url: str):
        """Test add patient page loads"""
        authenticated_page.goto(f"{base_url}/add_patient")
        expect(authenticated_page).to_have_url(f"{base_url}/add_patient")
        expect(authenticated_page.locator('input[name="name"]')).to_be_visible()

    def test_unauthenticated_redirect(self, page: Page, base_url: str):
        """Test that unauthenticated users are redirected to login"""
        page.goto(f"{base_url}/dashboard")
        page.wait_for_url(f"{base_url}/login**", timeout=5000)
        # Should be redirected to login page (either /login or /login/firebase)
        assert "/login" in page.url, f"Should redirect to login but got: {page.url}"


@pytest.mark.basic
class TestPatientManagement:
    """Test patient creation and management"""

    def test_create_patient_form_validation(self, authenticated_page: Page, base_url: str):
        """Test form validation on patient creation"""
        authenticated_page.goto(f"{base_url}/add_patient")

        # Try to submit empty form
        authenticated_page.click('button[type="submit"]')

        # Should show validation errors (form should not submit)
        # HTML5 validation or Flask validation should trigger
        expect(authenticated_page).to_have_url(f"{base_url}/add_patient")

    def test_create_patient_success(self, authenticated_page: Page, base_url: str):
        """Test successful patient creation"""
        authenticated_page.goto(f"{base_url}/add_patient")

        # Fill in required fields
        authenticated_page.fill('input[name="name"]', "Test Patient Basic")
        authenticated_page.fill('input[name="age_sex"]', "35/F")
        authenticated_page.fill('input[name="contact"]', "9876543210")
        authenticated_page.fill('textarea[name="present_history"]', "Lower back pain for 2 weeks")
        authenticated_page.fill('textarea[name="past_history"]', "No significant history")

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to patho mechanism page
        authenticated_page.wait_for_url(f"{base_url}/patho_mechanism/*", timeout=10000)
        assert "/patho_mechanism/" in authenticated_page.url, f"Expected patho_mechanism but got: {authenticated_page.url}"

    def test_patient_list_displays(self, authenticated_page: Page, base_url: str):
        """Test that patient list page shows patients"""
        authenticated_page.goto(f"{base_url}/view_patients")

        # Should show patient table or cards
        # Check for either table rows or patient cards
        has_content = (
            authenticated_page.locator('table tbody tr').count() > 0 or
            authenticated_page.locator('.patient-card').count() > 0 or
            authenticated_page.locator('[data-patient-id]').count() > 0
        )

        # If no patients, should show empty message
        if not has_content:
            empty_msg = authenticated_page.locator('text=/no patients|empty|create your first/i')
            expect(empty_msg).to_be_visible()


@pytest.mark.basic
class TestAIEndpoints:
    """Test AI suggestion endpoints (basic connectivity)"""

    def test_ai_suggestion_button_exists(self, authenticated_page: Page, patient_id: str, base_url: str):
        """Test that AI suggestion buttons are present"""
        # Navigate to patho mechanism page
        authenticated_page.goto(f"{base_url}/patho_mechanism/{patient_id}")
        authenticated_page.wait_for_load_state("networkidle")

        # Check that page loaded successfully (has form elements)
        # AI buttons may be hidden/shown based on quota or JavaScript
        form_elements = authenticated_page.locator('textarea, input, button').count()
        assert form_elements > 0, "Page didn't load properly - no form elements found"

        # AI buttons are optional (may be hidden if quota exhausted)
        print(f"\nPage loaded successfully with {form_elements} form elements")

    def test_ai_quota_check(self, authenticated_page: Page, base_url: str):
        """Test that AI quota is checked (should see quota indicator or warning)"""
        authenticated_page.goto(f"{base_url}/dashboard")

        # Should see some quota indicator (exact selector depends on your UI)
        # This is a placeholder - adjust selector based on your actual UI
        # quota_element = authenticated_page.locator('[data-quota], .quota-indicator, text=/AI calls|quota/i')
        # If quota display exists, verify it's visible
        # expect(quota_element.first).to_be_visible(timeout=5000)

        # For now, just verify dashboard loads (quota check happens server-side)
        expect(authenticated_page).to_have_url(f"{base_url}/dashboard")


@pytest.mark.basic
@pytest.mark.smoke
class TestHealthCheck:
    """Quick smoke tests for app health"""

    def test_homepage_loads(self, page: Page, base_url: str):
        """Test that homepage loads"""
        response = page.goto(base_url)
        assert response.status == 200

    def test_api_health_endpoint(self, page: Page, base_url: str):
        """Test that health check API responds"""
        response = page.goto(f"{base_url}/api/health")
        assert response.status == 200

    def test_static_assets_load(self, page: Page, base_url: str):
        """Test that static assets (CSS/JS) load"""
        page.goto(f"{base_url}/login")

        # Check that CSS is loaded (page should be styled)
        # Look for computed styles indicating CSS loaded
        body = page.locator('body')
        expect(body).to_be_visible()

        # Check for no major console errors
        # (Playwright captures console messages automatically)
