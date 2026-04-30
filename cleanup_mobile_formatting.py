#!/usr/bin/env python3
"""
Clean up extra blank lines in mobile_api_ai.py
"""

import re

# Read mobile_api_ai.py
with open('mobile_api_ai.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove excessive blank lines within return statements
# Replace multiple consecutive newlines with double newlines
content = re.sub(r'\n\n\n+', '\n\n', content)

# Fix the specific pattern of extra lines in jsonify returns
content = re.sub(r'\{\n\n\n\s+\'', r'{\n            \'', content)
content = re.sub(r'\',\n\n\n\s+\'', r'\',\n            \'', content)
content = re.sub(r'\'\n\n\n\s+\}', r'\'\n        }', content)

# Write back
with open('mobile_api_ai.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Cleaned up formatting in mobile_api_ai.py")
