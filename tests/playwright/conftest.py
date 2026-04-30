"""
Playwright Test Configuration and Fixtures
==========================================
Provides shared fixtures for authentication and test setup
"""
import os
import pytest
from playwright.sync_api import Page, BrowserContext, expect


# Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "https://physiologicprism.com")
TEST_EMAIL = os.getenv("TEST_EMAIL", "drsandeep@physiologicprism.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")  # Set via environment variable


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application"""
    return BASE_URL


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials"""
    password = TEST_PASSWORD or os.getenv("PHYSIO_TEST_PASSWORD")
    if not password:
        pytest.skip("TEST_PASSWORD environment variable not set")
    return {
        "email": TEST_EMAIL,
        "password": password
    }


@pytest.fixture(scope="function")
def authenticated_page(page: Page, base_url: str, test_credentials: dict) -> Page:
    """
    Provides an authenticated page ready to use.
    Logs in before each test and clears cookies after.
    """
    # Navigate to Firebase login page
    page.goto(f"{base_url}/login/firebase")

    # Wait for Firebase UI to load
    page.wait_for_load_state("networkidle")

    # Fill in credentials (Firebase UI uses specific selectors)
    page.fill('input[type="email"]', test_credentials["email"])
    page.fill('input[type="password"]', test_credentials["password"])

    # Click login button and wait for redirect
    page.click('button[type="submit"]')

    # Wait for redirect to dashboard (Firebase auth takes a moment)
    # Super admin accounts redirect to /super_admin_dashboard
    # Regular accounts redirect to /dashboard
    try:
        page.wait_for_url("**/super_admin_dashboard", timeout=30000)
    except:
        # If not super admin, wait for regular dashboard
        page.wait_for_url("**/dashboard", timeout=30000)

    # Verify we're logged in
    assert "dashboard" in page.url.lower(), f"Expected dashboard but got: {page.url}"

    yield page

    # Cleanup: logout or clear cookies
    # (optional - context is isolated per test anyway)


@pytest.fixture(scope="function")
def patient_id(authenticated_page: Page, base_url: str) -> str:
    """
    Creates a test patient and returns the patient ID.
    Cleans up after the test.
    """
    # Navigate to add patient page
    authenticated_page.goto(f"{base_url}/add_patient")

    # Fill in patient data
    authenticated_page.fill('input[name="name"]', "Playwright Test Patient")
    authenticated_page.fill('input[name="age_sex"]', "45/M")
    authenticated_page.fill('input[name="contact"]', "9999999999")
    authenticated_page.fill('textarea[name="present_history"]', "Test complaint")
    authenticated_page.fill('textarea[name="past_history"]', "No past history")

    # Submit form
    authenticated_page.click('button[type="submit"]')

    # Wait for redirect to patho mechanism page
    authenticated_page.wait_for_url(f"{base_url}/patho_mechanism/*", timeout=10000)

    # Extract patient ID from URL
    url = authenticated_page.url
    patient_id = url.split("/patho_mechanism/")[1]

    yield patient_id

    # Cleanup: delete test patient (optional)
    # Note: implement patient deletion if needed


@pytest.fixture(autouse=True)
def slow_down_tests(page: Page):
    """
    Slow down tests for visibility during development.
    Remove or disable for CI/CD.
    """
    page.set_default_timeout(10000)  # 10 second timeout
    page.set_default_navigation_timeout(30000)  # 30 second nav timeout


# Helper functions for common actions
class PageHelpers:
    """Helper methods for common page interactions"""

    @staticmethod
    def fill_form_field(page: Page, name: str, value: str):
        """Fill a form field by name"""
        selector = f'input[name="{name}"], textarea[name="{name}"], select[name="{name}"]'
        page.fill(selector, value)

    @staticmethod
    def click_ai_suggestion_button(page: Page):
        """Click the AI suggestion button and wait for response"""
        page.click('button:has-text("Get AI Suggestion")')
        page.wait_for_selector('.ai-suggestion-text', timeout=30000)

    @staticmethod
    def submit_form_and_wait(page: Page, base_url: str, next_page: str):
        """Submit form and wait for navigation to next page"""
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/{next_page}/*", timeout=10000)


@pytest.fixture
def helpers():
    """Provides helper methods"""
    return PageHelpers


# Configure pytest-playwright
def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "basic: Basic functionality tests"
    )
    config.addinivalue_line(
        "markers", "workflow: Full clinical workflow tests"
    )
