#!/bin/bash
# Check if Identity Toolkit PROJECT_SOFT_DELETED issue is resolved
# Run this periodically: bash check_identity_toolkit_status.sh

echo "Checking Identity Toolkit status for project physiologicprism-474610..."
echo ""

response=$(curl -s -X PATCH \
  "https://identitytoolkit.googleapis.com/v2/projects/physiologicprism-474610/config?updateMask=signIn.email.enabled" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: physiologicprism-474610" \
  -d '{
    "signIn": {
      "email": {
        "enabled": true,
        "passwordRequired": true
      }
    }
  }')

echo "$response" | grep -q "PROJECT_SOFT_DELETED"

if [ $? -eq 0 ]; then
  echo "❌ STILL BROKEN: Identity Toolkit returns PROJECT_SOFT_DELETED"
  echo ""
  echo "Response:"
  echo "$response" | jq . 2>/dev/null || echo "$response"
else
  echo "$response" | grep -q "signIn"
  if [ $? -eq 0 ]; then
    echo "✅ FIXED! Identity Toolkit is responding normally"
    echo ""
    echo "Response:"
    echo "$response" | jq . 2>/dev/null || echo "$response"
    echo ""
    echo "Next steps:"
    echo "1. Go to Firebase Console: https://console.firebase.google.com/project/physiologicprism-474610/authentication/providers"
    echo "2. Enable Email/Password authentication"
    echo "3. Test login at: https://physiologicprism.com/login/firebase"
  else
    echo "⚠️  UNKNOWN STATUS: Unexpected response"
    echo ""
    echo "Response:"
    echo "$response" | jq . 2>/dev/null || echo "$response"
  fi
fi
