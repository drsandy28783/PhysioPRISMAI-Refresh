# Playwright End-to-End Tests

Automated browser tests for PhysiologicPRISM using Playwright.

## Setup

1. **Install Dependencies** (already done):
   ```bash
   pip install playwright pytest-playwright
   python -m playwright install chromium
   ```

2. **Set Environment Variables**:
   ```bash
   # Windows PowerShell
   $env:TEST_PASSWORD="your_password_here"

   # Windows CMD
   set TEST_PASSWORD=your_password_here

   # Linux/Mac
   export TEST_PASSWORD="your_password_here"
   ```

3. **Configure Test URL** (optional):
   ```bash
   # Default is https://physiologicprism.com
   $env:TEST_BASE_URL="http://localhost:5000"  # For local testing
   ```

## Running Tests

### Run All Tests (Headed Mode - You Can See Browser)
```bash
cd tests/playwright
pytest --headed --slowmo 500
```

### Run All Tests (Headless Mode - Fast, No Browser Window)
```bash
pytest
```

### Run Only Basic Tests
```bash
pytest -m basic
```

### Run Only Workflow Tests
```bash
pytest -m workflow
```

### Run Specific Test File
```bash
pytest test_basic.py
pytest test_workflow.py
```

### Run Specific Test
```bash
pytest test_basic.py::TestAuthentication::test_login_success
pytest test_workflow.py::TestFullClinicalWorkflow::test_full_workflow_shoulder_acute
```

### Run with More Verbose Output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Smoke Tests Only (Quick Health Check)
```bash
pytest -m smoke
```

## Test Organization

### `test_basic.py` - Basic Functionality Tests
- **Authentication**: Login, logout, invalid credentials
- **Navigation**: Page access, redirects, menu navigation
- **Patient Management**: Create, view, list patients
- **AI Endpoints**: Basic connectivity checks
- **Health Checks**: App availability, API health

### `test_workflow.py` - Full Clinical Workflow Tests
- **Complete Workflow**: Full patient assessment from creation to treatment plan
- **AI Integration**: Test AI suggestions throughout workflow
- **Red Flag Detection**: Critical safety test for emergency scenarios
- **Navigation**: Back button, page transitions

### `conftest.py` - Test Configuration
- **Fixtures**: Shared test setup (authentication, patient creation)
- **Helpers**: Common functions for page interactions
- **Configuration**: Test environment setup

## Test Results

### Screenshots
Failed tests automatically capture screenshots:
- Location: `test-results/`
- Only captured on failure

### Videos
Failed tests automatically record videos:
- Location: `test-results/`
- Only recorded on failure

### Traces
Failed tests save Playwright traces:
- Location: `test-results/`
- View with: `playwright show-trace trace.zip`

## Configuration Options

Edit `pytest.ini` to customize:

```ini
[pytest]
addopts =
    --headed           # Show browser (remove for headless)
    --slowmo 500       # Slow down by 500ms (remove for full speed)
    --browser chromium # Browser to use (chromium, firefox, webkit)
    --screenshot only-on-failure
    --video retain-on-failure
```

## Common Issues

### Issue: Tests fail with "Authentication required"
**Solution**: Set `TEST_PASSWORD` environment variable

### Issue: Tests fail with "Quota exceeded"
**Solution**:
- AI quota may be exhausted
- Tests will skip AI-related checks automatically
- Reset quota or use test account with higher limits

### Issue: Tests are too fast to see what's happening
**Solution**: Add `--slowmo 1000` to slow down by 1 second per action

### Issue: Browser doesn't open
**Solution**:
- Use `--headed` flag
- Or remove `--headless` from pytest.ini

### Issue: Timeout errors
**Solution**: Increase timeouts in conftest.py or use slower network

## CI/CD Integration

For automated testing in CI/CD:

```bash
# Run in headless mode, no videos/screenshots unless failed
pytest --browser chromium \
       --screenshot only-on-failure \
       --video retain-on-failure \
       --tracing retain-on-failure
```

## Example Output

```
============================= test session starts ==============================
collected 25 items

test_basic.py::TestAuthentication::test_login_success PASSED           [  4%]
test_basic.py::TestAuthentication::test_login_invalid_credentials PASSED [  8%]
test_basic.py::TestNavigation::test_dashboard_access PASSED            [ 12%]
test_basic.py::TestPatientManagement::test_create_patient_success PASSED [ 16%]
test_workflow.py::TestFullClinicalWorkflow::test_full_workflow_shoulder_acute PASSED [ 20%]

✓ Full workflow completed for patient: bot-test-SC001-1234567890
✓ AI suggestion loaded successfully

======================== 25 passed in 120.45s ==============================
```

## Writing New Tests

### Basic Test Template
```python
@pytest.mark.basic
def test_my_feature(authenticated_page: Page, base_url: str):
    page = authenticated_page
    page.goto(f"{base_url}/my-page")

    # Your test code
    expect(page.locator('h1')).to_contain_text("Expected Text")
```

### Workflow Test Template
```python
@pytest.mark.workflow
@pytest.mark.slow
def test_my_workflow(authenticated_page: Page, base_url: str):
    page = authenticated_page

    # Step 1
    page.goto(f"{base_url}/step1")
    page.fill('input[name="field"]', "value")
    page.click('button[type="submit"]')

    # Step 2
    page.wait_for_url(f"{base_url}/step2/*")
    # Continue...
```

## Support

For issues or questions:
1. Check test output and error messages
2. Review screenshots/videos in `test-results/`
3. Run with `-vv` for detailed logging
4. Check browser console in headed mode
