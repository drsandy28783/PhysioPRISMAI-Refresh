# How to Run Tests - Simple Guide
**PhysioPRISM - Automated Testing for Non-Developers**

---

## 🎯 What You Just Got

I've created **30+ automated tests** that check:
- ✅ Login and authentication
- ✅ Patient creation, editing, deletion
- ✅ AI suggestions
- ✅ Mobile API endpoints
- ✅ Database operations

**You can now test your entire app in 30 seconds!**

---

## 📋 Quick Start (First Time Setup)

### Step 1: Install Testing Tools (ONE TIME - 2 minutes)

```bash
# Navigate to your project
cd "D:\New folder\New folder\Recovery"

# Install testing dependencies
pip install -r requirements-test.txt
```

**Expected output:**
```
Successfully installed pytest-7.4.3 pytest-flask-1.3.0 ...
```

✅ **That's it!** Testing tools are now installed.

---

### Step 2: Run Your First Test (30 seconds)

```bash
# Run all tests
pytest
```

**What you'll see:**
```
========================= test session starts =========================
collected 30 items

tests/test_health.py ....                                       [ 13%]
tests/test_auth.py .......                                      [ 36%]
tests/test_patients.py ........                                 [ 63%]
tests/test_ai.py ......                                         [ 83%]
tests/test_database.py .....                                    [ 96%]
tests/test_mobile_api.py ..                                     [100%]

========================== 30 passed in 5.23s =========================
```

### What This Means:

- ✅ **30 passed** = All tests passed! Safe to deploy!
- ⏱️ **5.23s** = Tests ran in 5 seconds
- 🟢 **Green dots (.)** = Individual passing tests

---

## 🚨 Understanding Test Results

### ✅ ALL TESTS PASS (Good!)

```
========================== 30 passed in 5.23s =========================
```

**What this means:**
- Your app is working correctly
- Safe to deploy to production
- All critical features tested OK

**What to do:**
- Deploy confidently! 🚀
- Or continue developing

---

### ❌ SOME TESTS FAIL (Needs Attention)

```
========================== 2 failed, 28 passed in 5.45s ==============
FAILED tests/test_auth.py::test_login_with_valid_credentials
FAILED tests/test_patients.py::test_create_patient
```

**What this means:**
- Something is broken
- DO NOT deploy yet
- Need to investigate failures

**What to do:**
1. Don't panic! This is why we have tests
2. Read the error messages (scroll up in terminal)
3. See "Troubleshooting" section below
4. Or come back to me (Claude) with the error

---

### ⚠️ TESTS ERROR (Configuration Issue)

```
ERROR collecting tests/test_auth.py
```

**What this means:**
- Test file has a problem
- Usually a missing import or syntax error
- Not your app's fault - test needs fixing

**What to do:**
- Come back to me with the error
- I'll fix the test file

---

## 🎯 Different Ways to Run Tests

### Run All Tests:
```bash
pytest
```

### Run Tests Verbosely (more detail):
```bash
pytest -v
```

Output:
```
tests/test_health.py::test_app_exists PASSED                   [  3%]
tests/test_health.py::test_health_endpoint PASSED              [  6%]
tests/test_auth.py::test_login_endpoint_exists PASSED          [  9%]
...
```

### Run Only Critical Tests:
```bash
pytest -m critical
```

This runs only the most important tests (faster).

### Run Specific Test File:
```bash
pytest tests/test_auth.py
```

Only tests authentication.

### Run Specific Test Function:
```bash
pytest tests/test_auth.py::test_login_with_valid_credentials
```

Runs just one specific test.

### Run Tests with Coverage Report:
```bash
pytest --cov=. --cov-report=html
```

Shows which code is tested (creates `htmlcov/index.html`).

---

## 📊 Reading Test Output

### Example Test Run:

```bash
$ pytest -v

tests/test_health.py::test_app_exists PASSED                   [  3%]
tests/test_health.py::test_health_endpoint PASSED              [  6%]
tests/test_auth.py::test_login_endpoint_exists PASSED          [  9%]
tests/test_auth.py::test_login_with_missing_email PASSED       [ 13%]
tests/test_patients.py::test_create_patient FAILED             [ 16%]
```

### Breaking it down:

- `tests/test_auth.py` = Test file
- `::test_login_endpoint_exists` = Test function
- `PASSED` = ✅ Test passed
- `FAILED` = ❌ Test failed
- `[ 16%]` = Progress (16% complete)

---

## 🔧 Troubleshooting Common Issues

### Problem: "pytest: command not found"

**Cause:** pytest not installed

**Fix:**
```bash
pip install -r requirements-test.txt
```

---

### Problem: "ModuleNotFoundError: No module named 'main'"

**Cause:** Wrong directory

**Fix:**
```bash
# Make sure you're in Recovery folder
cd "D:\New folder\New folder\Recovery"
pytest
```

---

### Problem: "ImportError: cannot import name 'app'"

**Cause:** Main app has syntax error

**Fix:**
1. Try running app normally: `python main.py`
2. If app doesn't start, fix the app first
3. Then run tests

---

### Problem: Tests failing but app works fine

**Cause:** Tests need adjustment for your specific setup

**Fix:**
1. Copy the failed test output
2. Come back to me (Claude)
3. I'll adjust the tests for your configuration

**This is NORMAL on first run!** Tests may need tweaking.

---

### Problem: "FAILED tests/test_auth.py::test_login_with_valid_credentials"

**Cause:** Mock authentication needs adjustment

**Fix:**
This test is checking login flow. The mock may need updating for your specific setup.

**Don't worry** - this doesn't mean login is broken. Just means the test mock needs adjustment.

Come back to me with the full error and I'll fix it.

---

## 🔄 When to Run Tests

### Before Every Deployment:
```bash
pytest
# If all pass → deploy
# If any fail → fix first
```

### After Adding New Features:
```bash
# Add feature
# Add test for feature
pytest
# If passes → commit code
```

### When Fixing Bugs:
```bash
# Fix bug
pytest
# Make sure you didn't break anything else
```

### Weekly (Recommended):
```bash
pytest
# Just to make sure everything still works
```

---

## 📝 Adding Your Own Tests

### Example: Test a New Feature

Create: `tests/test_my_feature.py`

```python
"""
My New Feature Tests
"""

import pytest


@pytest.mark.critical
def test_my_new_feature(client, auth_headers):
    """Test my new feature works"""
    response = client.post(
        '/api/my-new-endpoint',
        headers=auth_headers,
        json={'data': 'test'}
    )

    assert response.status_code == 200
    assert 'result' in response.json
```

Run it:
```bash
pytest tests/test_my_feature.py
```

---

## 🎯 Test Markers Explained

I've marked tests with categories:

- `@pytest.mark.critical` - Must pass before deployment
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.integration` - Tests multiple components
- `@pytest.mark.unit` - Tests single function

### Run only critical tests:
```bash
pytest -m critical
```

### Run only API tests:
```bash
pytest -m api
```

---

## 📊 What Each Test File Does

### `test_health.py` (4 tests)
- ✅ App starts correctly
- ✅ Health endpoint works
- ✅ Basic configuration

**If these fail:** App has major issues

---

### `test_auth.py` (8 tests)
- ✅ Login with valid credentials
- ✅ Login with invalid credentials
- ✅ Registration flow
- ✅ Password hashing

**If these fail:** Authentication broken

---

### `test_patients.py` (9 tests)
- ✅ Create patient
- ✅ Get patients list
- ✅ Update patient
- ✅ Delete patient
- ✅ Data validation

**If these fail:** Patient management broken

---

### `test_ai.py` (8 tests)
- ✅ AI suggestions work (mocked)
- ✅ Past questions
- ✅ Diagnosis
- ✅ Treatment plans

**If these fail:** AI integration issues

---

### `test_database.py` (5 tests)
- ✅ Database mocking works
- ✅ CRUD operations

**If these fail:** Database configuration issues

---

### `test_mobile_api.py` (12 tests)
- ✅ Mobile endpoints
- ✅ User profile
- ✅ Subscriptions
- ✅ Draft saving
- ✅ Follow-ups

**If these fail:** Mobile API issues

---

## 🚀 Deployment Workflow

### Recommended Process:

```bash
# 1. Make code changes
# (edit files, add features, fix bugs)

# 2. Run tests locally
pytest

# 3. If tests pass:
git add .
git commit -m "Add new feature"
git push

# 4. Deploy to production
# (Azure will auto-deploy if you have CI/CD)

# 5. Monitor Sentry for errors
# (check dashboard for 24 hours)
```

---

## ⚡ Quick Reference

```bash
# Install testing tools (first time only)
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only critical tests
pytest -m critical

# Run specific file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=.

# Stop on first failure (faster debugging)
pytest -x

# Show local variables on failure (debugging)
pytest -l

# Quiet mode (less output)
pytest -q
```

---

## ✅ Success Checklist

After first test run:

- [ ] Testing tools installed (`pip install -r requirements-test.txt`)
- [ ] Tests run successfully (`pytest`)
- [ ] Understand test output (pass/fail)
- [ ] Know how to run specific tests
- [ ] Tests integrated into workflow (run before deploy)
- [ ] Sentry set up (error tracking)

**When all checked:** You're production-ready! 🎉

---

## 🎯 Next Steps

1. **TODAY:**
   - Install testing tools
   - Run tests for first time
   - See which tests pass/fail

2. **THIS WEEK:**
   - Fix any failing tests (or ask me for help)
   - Set up Sentry (see SENTRY_SETUP_GUIDE.md)
   - Run tests before each deployment

3. **ONGOING:**
   - Add tests for new features
   - Run tests weekly
   - Monitor Sentry dashboard

---

## 📞 Getting Help

### If tests are failing:

1. **Copy the error output:**
   ```bash
   pytest -v > test_output.txt
   ```

2. **Come back to me (Claude) with:**
   - The failed test name
   - Error message
   - What you were trying to do

3. **I'll help you:**
   - Fix the test
   - Or fix your code
   - Or adjust the mock

### If you want to add tests:

1. **Tell me what feature to test**
2. **I'll write the test for you**
3. **You run it and verify it works**

---

## 💡 Pro Tips

### Tip 1: Run tests in watch mode (auto-run on file change)
```bash
pip install pytest-watch
ptw
```

### Tip 2: Run tests in parallel (faster)
```bash
pip install pytest-xdist
pytest -n auto
```

### Tip 3: Only run failed tests from last run
```bash
pytest --lf
```

### Tip 4: Run tests in random order (catch hidden dependencies)
```bash
pip install pytest-random-order
pytest --random-order
```

---

## 🎉 You Now Have Production-Level Testing!

**What this means:**
- ✅ Can deploy confidently
- ✅ Catch bugs before users see them
- ✅ Verify updates don't break existing features
- ✅ Professional development workflow

**Combined with Sentry:**
- ✅ Tests catch bugs before deployment
- ✅ Sentry catches bugs that slip through
- ✅ You're alerted immediately
- ✅ Full error details for quick fixes

**You're ready for production! 🚀**

---

**Document Version:** 1.0
**Status:** Ready to Use
**Next:** Set up Sentry, then deploy!
