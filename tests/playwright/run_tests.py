#!/usr/bin/env python
"""
Playwright Test Runner
=====================
Simple script to run Playwright tests with proper configuration
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run Playwright tests"""
    print("=" * 70)
    print("PhysiologicPRISM - Playwright E2E Tests")
    print("=" * 70)

    # Check if password is set
    if not os.getenv("TEST_PASSWORD") and not os.getenv("PHYSIO_TEST_PASSWORD"):
        print("\n[ERROR] TEST_PASSWORD environment variable not set!")
        print("\nPlease set your test password:")
        print("  Windows PowerShell: $env:TEST_PASSWORD=\"your_password\"")
        print("  Windows CMD:        set TEST_PASSWORD=your_password")
        print("  Linux/Mac:          export TEST_PASSWORD=\"your_password\"")
        sys.exit(1)

    # Display configuration
    base_url = os.getenv("TEST_BASE_URL", "https://physiologicprism.com")
    test_email = os.getenv("TEST_EMAIL", "drsandeep@physiologicprism.com")

    print(f"\nConfiguration:")
    print(f"  Base URL:  {base_url}")
    print(f"  Test User: {test_email}")
    print(f"  Password:  {'*' * 8} (set)")

    # Parse command line arguments
    test_type = "all"
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()

    # Build pytest command
    cmd = ["pytest"]

    if test_type == "basic":
        print(f"\n[TARGET] Running: Basic functionality tests only")
        cmd.extend(["-m", "basic"])
    elif test_type == "workflow":
        print(f"\n[TARGET] Running: Full workflow tests only")
        cmd.extend(["-m", "workflow"])
    elif test_type == "smoke":
        print(f"\n[TARGET] Running: Quick smoke tests only")
        cmd.extend(["-m", "smoke"])
    elif test_type == "headless":
        print(f"\n[TARGET] Running: All tests in headless mode (fast)")
        cmd.extend(["--browser", "chromium"])
    else:
        print(f"\n[TARGET] Running: All tests (headed mode - you'll see browser)")
        cmd.extend(["--headed", "--slowmo", "500"])

    # Add verbose output
    cmd.append("-v")

    # Show command
    print(f"\n[EXECUTE] {' '.join(cmd)}")
    print("=" * 70)

    # Run tests
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Show usage if --help
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Playwright Test Runner

Usage:
  python run_tests.py [test_type]

Test Types:
  all       - Run all tests (default, headed mode)
  basic     - Run basic functionality tests only
  workflow  - Run full workflow tests only
  smoke     - Run quick smoke tests only
  headless  - Run all tests in headless mode (fast)

Examples:
  python run_tests.py              # Run all tests, see browser
  python run_tests.py basic        # Run only basic tests
  python run_tests.py headless     # Run all tests, no browser window

Environment Variables:
  TEST_PASSWORD    - Required: Your test account password
  TEST_BASE_URL    - Optional: App URL (default: https://physiologicprism.com)
  TEST_EMAIL       - Optional: Test email (default: drsandeep@physiologicprism.com)
""")
        sys.exit(0)

    main()
