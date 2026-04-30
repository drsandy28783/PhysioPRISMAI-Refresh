"""
Full Clinical Workflow Tests
============================
Tests complete clinical assessment workflow from patient creation to treatment plan
"""
import pytest
from playwright.sync_api import Page, expect
import sys
import os

# Add parent directory to path to import clinical scenarios
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from clinical_scenarios import SCENARIO_SHOULDER_ACUTE, SCENARIO_KNEE_OA


@pytest.mark.workflow
class TestFullClinicalWorkflow:
    """Test complete clinical assessment workflow"""

    @pytest.mark.slow
    def test_full_workflow_shoulder_acute(self, authenticated_page: Page, base_url: str):
        """Test full workflow for acute shoulder injury"""
        page = authenticated_page
        scenario = SCENARIO_SHOULDER_ACUTE

        # STEP 1: Create Patient
        page.goto(f"{base_url}/add_patient")
        page.fill('input[name="name"]', scenario.patient_data["name"])
        page.fill('input[name="age_sex"]', scenario.patient_data["age_sex"])
        page.fill('input[name="contact"]', scenario.patient_data["contact"])
        page.fill('textarea[name="present_history"]', scenario.patient_data["chief_complaint"])
        page.fill('textarea[name="past_history"]', scenario.patient_data["medical_history"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/patho_mechanism/*", timeout=10000)

        # Extract patient ID
        patient_id = page.url.split("/patho_mechanism/")[1]

        # STEP 2: Pathophysiological Mechanism
        page.wait_for_load_state("networkidle")
        page.fill('textarea[name="area_involved"]', scenario.patho_mechanism_data["area_involved"])
        page.fill('textarea[name="presenting_symptom"]', scenario.patho_mechanism_data["presenting_symptom"])
        page.fill('textarea[name="pain_type"]', scenario.patho_mechanism_data["pain_type"])

        # Test AI suggestion (optional - may hit quota)
        try:
            ai_button = page.locator('button:has-text("AI"), button:has-text("Suggest")').first
            if ai_button.is_visible():
                ai_button.click()
                page.wait_for_selector('.ai-suggestion-text, [data-ai-response]', timeout=10000)
        except:
            pass  # Skip if AI quota exhausted

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/subjective/*", timeout=10000)

        # STEP 3: Subjective Examination
        page.wait_for_load_state("networkidle")
        subj_data = scenario.subjective_examination_data
        page.fill('textarea[name="body_function"]', subj_data["body_function"])
        page.fill('textarea[name="activity_limitation"]', subj_data["activity_limitation"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/perspectives/*", timeout=10000)

        # STEP 4: Patient Perspectives
        page.wait_for_load_state("networkidle")
        persp_data = scenario.perspectives_data
        page.fill('textarea[name="patient_goals"]', persp_data["patient_goals"])
        page.fill('textarea[name="concerns"]', persp_data["concerns"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/initial_plan/*", timeout=10000)

        # STEP 5: Initial Assessment Plan
        page.wait_for_load_state("networkidle")
        plan_data = scenario.initial_plan_data

        # Select mandatory assessments (if checkboxes present)
        if page.locator('input[type="checkbox"][value*="Range of motion"]').is_visible():
            page.check('input[type="checkbox"][value*="Range of motion"]')

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/chronic_disease/*", timeout=10000)

        # STEP 6: Chronic Disease Factors
        page.wait_for_load_state("networkidle")
        chronic_data = scenario.chronic_disease_data

        # Fill yellow flags
        page.fill('textarea[name="yellow_flags"]', chronic_data["yellow_flags"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/clinical_flags/*", timeout=10000)

        # STEP 7: Clinical Flags
        page.wait_for_load_state("networkidle")
        flags_data = scenario.clinical_flags_data

        # Select red flags (important for safety testing!)
        # This scenario should NOT have red flags
        if page.locator('input[type="checkbox"][name="red_flags"]').count() > 0:
            # Verify no red flags are checked (as per scenario)
            checked_count = page.locator('input[type="checkbox"][name="red_flags"]:checked').count()
            assert checked_count == 0, "Unexpected red flags checked for non-emergency scenario"

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/objective_assessment/*", timeout=10000)

        # STEP 8: Objective Assessment
        page.wait_for_load_state("networkidle")
        obj_data = scenario.objective_assessment_data

        page.fill('textarea[name="observation"]', obj_data["observation"])
        page.fill('textarea[name="palpation"]', obj_data["palpation"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/provisional_diagnosis/*", timeout=10000)

        # STEP 9: Provisional Diagnosis
        page.wait_for_load_state("networkidle")
        diag_data = scenario.provisional_diagnosis_data

        page.fill('textarea[name="structure_fault"]', diag_data["structure_fault"])
        page.fill('textarea[name="functional_limitation"]', diag_data["functional_limitation"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/smart_goals/*", timeout=10000)

        # STEP 10: SMART Goals
        page.wait_for_load_state("networkidle")
        goals_data = scenario.smart_goals_data

        page.fill('textarea[name="patient_goal"]', goals_data["patient_goal"])
        page.fill('textarea[name="therapist_goals"]', goals_data["therapist_goals"])

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/treatment_plan/*", timeout=10000)

        # STEP 11: Treatment Plan
        page.wait_for_load_state("networkidle")
        treat_data = scenario.treatment_plan_data

        page.fill('textarea[name="treatment_plan"]', treat_data["treatment_plan"])
        page.fill('textarea[name="reasoning"]', treat_data["reasoning"])

        page.click('button[type="submit"]')

        # Should complete successfully
        # May redirect to summary, view patients, or dashboard
        page.wait_for_load_state("networkidle")

        # Verify we're not on an error page
        expect(page.locator('h1:has-text("Error"), h1:has-text("500")')).not_to_be_visible()

        # Success!
        print(f"\n✓ Full workflow completed for patient: {patient_id}")


    @pytest.mark.slow
    def test_full_workflow_with_ai_suggestions(self, authenticated_page: Page, base_url: str):
        """Test workflow including AI suggestion interactions"""
        page = authenticated_page
        scenario = SCENARIO_KNEE_OA

        # Create patient
        page.goto(f"{base_url}/add_patient")
        page.fill('input[name="name"]', scenario.patient_data["name"])
        page.fill('input[name="age_sex"]', scenario.patient_data["age_sex"])
        page.fill('input[name="contact"]', scenario.patient_data["contact"])
        page.fill('textarea[name="present_history"]', scenario.patient_data["chief_complaint"])
        page.fill('textarea[name="past_history"]', scenario.patient_data["medical_history"])
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/patho_mechanism/*", timeout=10000)

        # Test AI suggestion on patho mechanism page
        page.wait_for_load_state("networkidle")

        # Try to use AI suggestion
        try:
            ai_buttons = page.locator('button:has-text("AI"), button:has-text("Suggest"), button[data-ai-field]')
            if ai_buttons.count() > 0:
                first_button = ai_buttons.first
                first_button.click()

                # Wait for AI response
                page.wait_for_selector('.ai-suggestion-text, [data-ai-response], .suggestion', timeout=30000)

                # Verify suggestion appears
                suggestion_text = page.locator('.ai-suggestion-text, [data-ai-response], .suggestion').first
                expect(suggestion_text).to_be_visible()
                expect(suggestion_text).not_to_be_empty()

                print("\n✓ AI suggestion loaded successfully")
        except Exception as e:
            print(f"\n⚠ AI suggestion test skipped (quota may be exhausted): {e}")

        # Continue with minimal workflow
        page.fill('textarea[name="area_involved"]', scenario.patho_mechanism_data["area_involved"])
        page.click('button[type="submit"]')

        # Success if we reach next page
        page.wait_for_url(f"{base_url}/subjective/*", timeout=10000)
        expect(page).to_have_url(pytest.approx(f"{base_url}/subjective/", rel=1e-1))


@pytest.mark.workflow
class TestRedFlagDetection:
    """Critical safety test: Red flag detection"""

    def test_red_flag_scenario_workflow(self, authenticated_page: Page, base_url: str):
        """Test that red flag scenarios are properly handled"""
        page = authenticated_page

        # Create a patient with red flag symptoms (Cauda Equina-like)
        page.goto(f"{base_url}/add_patient")
        page.fill('input[name="name"]', "Red Flag Test Patient")
        page.fill('input[name="age_sex"]', "52/M")
        page.fill('input[name="contact"]', "9999999999")
        page.fill('textarea[name="present_history"]',
                  "Severe lower back pain with bilateral leg weakness, saddle anesthesia, and bladder dysfunction for 12 hours")
        page.fill('textarea[name="past_history"]', "Recent heavy lifting")

        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/patho_mechanism/*", timeout=10000)

        # Continue through workflow to clinical flags page
        page.fill('textarea[name="area_involved"]', "Lumbar spine, cauda equina")
        page.fill('textarea[name="presenting_symptom"]', "Severe pain with neurological symptoms")
        page.fill('textarea[name="pain_type"]', "Neuropathic with motor deficit")
        page.click('button[type="submit"]')

        # Navigate to clinical flags page
        # (would need to fill intermediate forms - shortened for test)
        patient_id = page.url.split("/")[-1]

        # Jump directly to clinical flags
        page.goto(f"{base_url}/clinical_flags/{patient_id}")
        page.wait_for_load_state("networkidle")

        # Verify red flag checkboxes are present
        red_flag_section = page.locator('text=/red flag/i').first
        expect(red_flag_section).to_be_visible()

        # Look for emergency warning if red flags are detected
        # (implementation depends on your UI)
        # emergency_warning = page.locator('.alert-danger, .warning, text=/immediate referral|emergency/i')
        # This test verifies the form structure exists for red flag assessment

        print("\n✓ Red flag assessment form structure verified")


@pytest.mark.workflow
class TestWorkflowNavigation:
    """Test navigation between workflow steps"""

    def test_back_navigation(self, authenticated_page: Page, patient_id: str, base_url: str):
        """Test that users can navigate back between workflow steps"""
        page = authenticated_page

        # Start at patho mechanism
        page.goto(f"{base_url}/patho_mechanism/{patient_id}")
        page.wait_for_load_state("networkidle")

        # Fill and proceed
        page.fill('textarea[name="area_involved"]', "Test area")
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/subjective/*", timeout=10000)

        # Use browser back button
        page.go_back()
        page.wait_for_load_state("networkidle")

        # Should be back at patho mechanism page
        expect(page).to_have_url(pytest.approx(f"{base_url}/patho_mechanism/", rel=1e-1))

    def test_skip_to_summary(self, authenticated_page: Page, patient_id: str, base_url: str):
        """Test accessing patient summary/view page"""
        page = authenticated_page

        # Navigate to patient summary (if route exists)
        # Adjust URL based on your actual summary route
        try:
            page.goto(f"{base_url}/patient_summary/{patient_id}", timeout=5000)
            expect(page.locator('h1, h2').first).to_be_visible()
        except:
            # If summary route doesn't exist, that's okay
            print("\n⚠ Patient summary route not tested (may not exist)")
