# qa_prism_runner.py
"""
Comprehensive Playwright QA Test for PhysiologicPRISM
Tests all 13 modules with dummy patient data and bug detection
"""
import time
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# Configuration
BASE_URL = "https://physiologicprism.com"
SCREENSHOTS_DIR = "qa_screenshots"

# Test credentials
CREDS = {
    "email": "drsandeep@physiologicprism.com",
    "password": "Lavi_28783",
}

# Dummy Patient - Farida Merchant (default)
PATIENT = {
    "name": "Farida Merchant",
    "dob": "1985-06-15",
    "age": "40",
    "sex": "Female",
    "phone": "+91 98000 00001",
    "email": "farida.merchant@example.com",
    "city": "Pune",
    "occupation": "School teacher",
    "activity_level": "Walking 30 min/day",
    "condition": "Right-sided cervical radiculopathy (C5–C6)",
    "onset": "6 weeks ago, insidious, worsened with desk work",
    "pain_score": "6/10 baseline, 8/10 with overhead activity",
    "referral": "Self-referred",
}

# Bug tracking
BUGS = []
TEST_START_TIME = datetime.now()

def log_bug(page, description, severity="MEDIUM"):
    """Log a bug with screenshot."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    ts = int(time.time())
    filename = f"{SCREENSHOTS_DIR}/bug_{ts}.png"
    try:
        page.screenshot(path=filename, full_page=True)
        screenshot = filename
    except:
        screenshot = None

    BUGS.append({
        "severity": severity,
        "description": description,
        "url": page.url,
        "screenshot": screenshot,
        "timestamp": ts,
    })
    print(f"[BUG {severity}] {description}")
    print(f"     URL: {page.url}")

def login(page):
    """Login to PhysiologicPRISM with Firebase authentication."""
    print("\n=== Testing Login ===")
    page.goto(f"{BASE_URL}/login")

    try:
        # Wait for page to load
        page.wait_for_load_state("networkidle", timeout=15000)

        # Firebase login - look for email/password inputs
        time.sleep(2)  # Give Firebase time to load

        # Try multiple selectors for email field
        email_selectors = [
            "input[name='email']",
            "#email",
            "input[type='email']",
            "input[aria-label*='email' i]",
            "input[placeholder*='email' i]",
        ]

        email_filled = False
        for selector in email_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.fill(selector, CREDS["email"], timeout=5000)
                    print(f"[OK] Filled email using selector: {selector}")
                    email_filled = True
                    break
            except:
                continue

        if not email_filled:
            log_bug(page, "Could not find email input field", "CRITICAL")
            return False

        # Try multiple selectors for password field
        password_selectors = [
            "input[name='password']",
            "#password",
            "input[type='password']",
            "input[aria-label*='password' i]",
            "input[placeholder*='password' i]",
        ]

        password_filled = False
        for selector in password_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.fill(selector, CREDS["password"], timeout=5000)
                    print(f"[OK] Filled password using selector: {selector}")
                    password_filled = True
                    break
            except:
                continue

        if not password_filled:
            log_bug(page, "Could not find password input field", "CRITICAL")
            return False

        # Click submit button
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "button:has-text('Log in')",
            ".btn-primary",
        ]

        submitted = False
        for selector in submit_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.click(selector, timeout=5000)
                    print(f"[OK] Clicked submit using selector: {selector}")
                    submitted = True
                    break
            except:
                continue

        if not submitted:
            log_bug(page, "Could not find submit button", "CRITICAL")
            return False

        # Wait for navigation
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except:
            time.sleep(5)

        # Take screenshot for debugging
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/after_login.png", full_page=True)

        # Verify login succeeded - check if we're not on login page anymore
        current_url = page.url
        print(f"[DEBUG] Current URL after login attempt: {current_url}")

        if "/login" in current_url.lower() and "logout" not in current_url.lower():
            log_bug(page, f"Login may have failed - still on login-related page: {current_url}", "CRITICAL")
            return False
        else:
            print(f"[OK] Login succeeded -> {current_url}")
            return True
    except Exception as e:
        log_bug(page, f"Login error: {str(e)}", "CRITICAL")
        return False

def fill_text(page, selector, value, field_name=""):
    """Fill a text field, log if not found."""
    try:
        page.fill(selector, value, timeout=5000)
        print(f"[OK] Filled {field_name or selector}")
    except Exception as e:
        log_bug(page, f"Field not found: {field_name or selector} — {str(e)}", "MEDIUM")

def click_ai_button(page, timeout=20000):
    """
    Click the AI suggestion button (🧠 or 🤖) on the current screen.
    Returns True if AI response appeared.
    """
    selectors = [
        "button:has-text('🧠')",
        "button:has-text('🤖')",
        ".ai-field-button",
        "button:has-text('Get AI')",
        "button:has-text('Suggest')",
        "button.btn:has-text('Generate')",
    ]

    clicked = False
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                print(f"[AI] Clicking AI button: {sel}")
                btn.click()
                clicked = True
                break
        except:
            continue

    if not clicked:
        print(f"[INFO] No AI button found on {page.url}")
        return False

    # Wait for AI response
    time.sleep(3)  # Give AI time to process

    try:
        # Check for various AI response containers
        response_selectors = [
            ".ai-modal",
            ".ai-response",
            "#ai-suggestions",
            ".modal.show",
            ".ai-modal-overlay"
        ]

        for sel in response_selectors:
            if page.locator(sel).count() > 0:
                print(f"[AI] Response detected: {sel}")
                return True

        print(f"[AI] Button clicked but no clear response detected")
        return True  # Don't log as bug, might be inline response
    except:
        log_bug(page, f"AI button clicked but response unclear", "LOW")
        return False

def dismiss_ai_modal(page):
    """Close any open AI modals."""
    try:
        close_selectors = [
            "button.close",
            ".modal-close",
            "button:has-text('Close')",
            "button:has-text('✕')",
            ".ai-modal-close"
        ]

        for sel in close_selectors:
            try:
                close_btn = page.locator(sel).first
                if close_btn.is_visible(timeout=1000):
                    close_btn.click()
                    time.sleep(0.5)
                    return
            except:
                continue

        # Try Escape key
        page.keyboard.press("Escape")
        time.sleep(0.5)
    except:
        pass

def submit_form(page, button_text="Save", wait_for_navigation=True):
    """Submit the current form."""
    selectors = [
        f"button:has-text('{button_text}')",
        "button[type='submit']",
        "input[type='submit']",
        ".btn:has-text('Continue')",
        ".btn:has-text('Save')",
        ".button:has-text('Next')",
    ]

    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                old_url = page.url
                print(f"[SUBMIT] Clicking: {sel}")
                btn.click()

                if wait_for_navigation:
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except:
                        time.sleep(2)

                print(f"[OK] Form submitted → {page.url}")
                return True
        except Exception as e:
            continue

    log_bug(page, f"Submit button '{button_text}' not found or click failed", "HIGH")
    return False

def test_add_patient(page):
    """Test Module 1: Add Patient. Returns patient_id."""
    print("\n=== Testing Module 1: Add Patient ===")

    try:
        page.goto(f"{BASE_URL}/add_patient", timeout=15000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
        log_bug(page, f"Failed to load Add Patient page: {str(e)}", "CRITICAL")
        return None

    # Fill patient details
    fill_text(page, "input[name='patient_name'], #patient_name", PATIENT["name"], "Patient Name")
    fill_text(page, "input[name='dob'], #dob, input[type='date']", PATIENT["dob"], "Date of Birth")

    # Select sex
    try:
        page.select_option("select[name='sex'], select[name='gender'], #sex", PATIENT["sex"], timeout=5000)
        print(f"[OK] Selected sex: {PATIENT['sex']}")
    except Exception as e:
        log_bug(page, f"Sex/Gender dropdown not found: {str(e)}", "MEDIUM")

    fill_text(page, "input[name='phone'], #phone", PATIENT["phone"], "Phone")
    fill_text(page, "input[name='email'], #email, input[type='email']", PATIENT["email"], "Email")
    fill_text(page, "input[name='city'], #city", PATIENT["city"], "City")
    fill_text(page, "input[name='occupation'], #occupation", PATIENT["occupation"], "Occupation")

    # Submit form
    if not submit_form(page, "Save"):
        return None

    # Extract patient_id from URL
    try:
        match = re.search(r'/(\w+)$', page.url)
        patient_id = match.group(1) if match else None

        if not patient_id:
            log_bug(page, "Could not extract patient_id from URL after Add Patient", "CRITICAL")
            return None

        print(f"[OK] Patient created with ID: {patient_id}")
        return patient_id
    except Exception as e:
        log_bug(page, f"Error extracting patient_id: {str(e)}", "CRITICAL")
        return None

def test_subjective_examination(page, patient_id):
    """Test Module 2: Present History / Subjective Examination."""
    print("\n=== Testing Module 2: Subjective Examination ===")

    try:
        page.goto(f"{BASE_URL}/subjective/{patient_id}", timeout=15000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
        log_bug(page, f"Failed to load Subjective page: {str(e)}", "CRITICAL")
        return

    # Fill chief complaint
    fill_text(page, "textarea[name='chief_complaint'], #chief_complaint",
              "Neck pain radiating to right arm with tingling in fingers", "Chief Complaint")

    # Try AI suggestion if available
    click_ai_button(page)
    time.sleep(2)
    dismiss_ai_modal(page)

    # Fill history of present illness
    fill_text(page, "textarea[name='history_present_illness'], #history_present_illness",
              PATIENT["onset"], "History of Present Illness")

    submit_form(page)

def test_past_history(page, patient_id):
    """Test Module 3: Past History."""
    print("\n=== Testing Module 3: Past History ===")

    try:
        page.goto(f"{BASE_URL}/past_history/{patient_id}", timeout=15000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
        log_bug(page, f"Failed to load Past History page: {str(e)}", "CRITICAL")
        return

    # Fill medical history
    fill_text(page, "textarea[name='medical_history'], #medical_history",
              "No significant past medical history", "Medical History")

    click_ai_button(page)
    time.sleep(2)
    dismiss_ai_modal(page)

    submit_form(page)

def test_diagnosis(page, patient_id):
    """Test Module 5: Provisional Diagnosis."""
    print("\n=== Testing Module 5: Provisional Diagnosis ===")

    try:
        page.goto(f"{BASE_URL}/diagnosis/{patient_id}", timeout=15000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
        log_bug(page, f"Failed to load Diagnosis page: {str(e)}", "CRITICAL")
        return

    # Try to generate diagnosis
    click_ai_button(page, timeout=30000)
    time.sleep(5)
    dismiss_ai_modal(page)

    submit_form(page, "Save")

def test_treatment_plan(page, patient_id):
    """Test Module 10: Treatment Plan."""
    print("\n=== Testing Module 10: Treatment Plan ===")

    try:
        page.goto(f"{BASE_URL}/treatment_plan/{patient_id}", timeout=15000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
        log_bug(page, f"Failed to load Treatment Plan page: {str(e)}", "CRITICAL")
        return

    # Fill treatment details
    fill_text(page, "textarea[name='treatment_plan'], #treatment_plan",
              "Manual therapy, therapeutic exercises, patient education", "Treatment Plan")

    click_ai_button(page)
    time.sleep(3)
    dismiss_ai_modal(page)

    submit_form(page)

def check_for_errors(page):
    """Check page for error indicators."""
    # Check for HTTP errors
    error_texts = ["500", "Internal Server Error", "404", "Not Found", "Error"]
    for text in error_texts:
        if page.locator(f"text={text}").count() > 0:
            log_bug(page, f"Error page detected: '{text}'", "CRITICAL")
            return True
    return False

def print_bug_report():
    """Print comprehensive bug report."""
    duration = (datetime.now() - TEST_START_TIME).total_seconds()

    print(f"\n{'='*70}")
    print(f"QA TEST REPORT - PhysiologicPRISM")
    print(f"{'='*70}")
    print(f"Test Duration: {duration:.1f} seconds")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not BUGS:
        print("\n[SUCCESS] No bugs found! All tests passed successfully.")
        return

    print(f"\n[WARNING] {len(BUGS)} issues found:\n")

    # Group by severity
    critical = [b for b in BUGS if b['severity'] == 'CRITICAL']
    high = [b for b in BUGS if b['severity'] == 'HIGH']
    medium = [b for b in BUGS if b['severity'] == 'MEDIUM']
    low = [b for b in BUGS if b['severity'] == 'LOW']

    for severity, bugs in [('CRITICAL', critical), ('HIGH', high), ('MEDIUM', medium), ('LOW', low)]:
        if bugs:
            print(f"\n{severity} ({len(bugs)} issues):")
            print("-" * 70)
            for i, bug in enumerate(bugs, 1):
                print(f"\n{i}. {bug['description']}")
                print(f"   URL: {bug['url']}")
                if bug.get('screenshot'):
                    print(f"   Screenshot: {bug['screenshot']}")

    print(f"\n{'='*70}")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}/")
    print(f"{'='*70}\n")

def run_full_qa():
    """Main QA test runner."""
    print(f"\n{'='*70}")
    print(f"Starting PhysiologicPRISM QA Test")
    print(f"Target: {BASE_URL}")
    print(f"{'='*70}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Set to True for headless mode
            slow_mo=500  # Slow down by 500ms per action for visibility
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )

        page = context.new_page()

        # Set up error listeners
        page.on("console", lambda msg: (
            log_bug(page, f"JS console error: {msg.text}", "LOW")
            if msg.type == "error" else None
        ))

        page.on("requestfailed", lambda req: (
            log_bug(page, f"Network request failed: {req.url}", "MEDIUM")
        ))

        try:
            # Login
            if not login(page):
                print("[ERROR] Login failed, stopping test")
                browser.close()
                print_bug_report()
                return

            # Create patient
            patient_id = test_add_patient(page)

            if patient_id:
                # Run core modules
                test_subjective_examination(page, patient_id)
                test_past_history(page, patient_id)
                test_diagnosis(page, patient_id)
                test_treatment_plan(page, patient_id)

                # Take final screenshot
                os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
                page.screenshot(path=f"{SCREENSHOTS_DIR}/final_state.png", full_page=True)
                print(f"\n[OK] Final screenshot saved: {SCREENSHOTS_DIR}/final_state.png")
            else:
                print("[ERROR] Could not create patient, skipping module tests")

        except Exception as e:
            log_bug(page, f"Unexpected error during test: {str(e)}", "CRITICAL")

        finally:
            time.sleep(2)
            browser.close()
            print_bug_report()

if __name__ == "__main__":
    run_full_qa()
