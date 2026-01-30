"""
Test script to verify Sentry error tracking is working.
Run this AFTER setting up Sentry DSN.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Sentry (same as in main.py)
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SENTRY_DSN = os.environ.get('SENTRY_DSN')

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FlaskIntegration(),
            LoggingIntegration(
                level=None,
                event_level=None
            )
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get('ENVIRONMENT', 'development')
    )
    print("✅ Sentry initialized successfully")
else:
    print("❌ SENTRY_DSN not found in environment")
    exit(1)

# Trigger test error
print("\n🧪 Triggering test error...")
print("This will send an error to Sentry dashboard.\n")

try:
    # This will cause a division by zero error
    result = 1 / 0
except Exception as e:
    # Capture the exception in Sentry
    sentry_sdk.capture_exception(e)
    print(f"✅ Test error captured: {type(e).__name__}")
    print("\n📧 Check your Sentry dashboard and email!")
    print("   You should receive an error notification.\n")

# Send a test message
sentry_sdk.capture_message("🧪 Test message from PhysioPRISM - Sentry is working!", level="info")
print("✅ Test message sent to Sentry")

print("\n" + "="*50)
print("✅ SENTRY TEST COMPLETE")
print("="*50)
print("\n📋 Next steps:")
print("1. Go to https://sentry.io")
print("2. Check your project dashboard")
print("3. You should see the test error")
print("4. Check your email for notification")
print("\nIf you see the error in Sentry → Setup successful! 🎉")
