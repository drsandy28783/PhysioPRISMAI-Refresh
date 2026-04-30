#!/usr/bin/env python3
"""
Fix all AI endpoint responses to include both old and new field names.
"""

import re

# Read main.py
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: return jsonify({'suggestion': split_response['visible_text'], 'reasoning': split_response['reasoning_text']})
pattern1 = r"return jsonify\(\{\s*'suggestion':\s*split_response\['visible_text'\],\s*'reasoning':\s*split_response\['reasoning_text'\]\s*\}\)"
replacement1 = """return jsonify({
            'suggestion': split_response['visible_text'],
            'text': split_response['visible_text'],
            'visible_text': split_response['visible_text'],
            'reasoning': split_response['reasoning_text'],
            'reasoning_text': split_response['reasoning_text']
        })"""

content = re.sub(pattern1, replacement1, content)

# Pattern 2: return jsonify({'field': field, 'suggestion': split_response['visible_text'], 'reasoning': split_response['reasoning_text']})
pattern2 = r"return jsonify\(\{\s*'field':\s*field,\s*'suggestion':\s*split_response\['visible_text'\],\s*'reasoning':\s*split_response\['reasoning_text'\]\s*\}\)"
replacement2 = """return jsonify({
            'field': field,
            'suggestion': split_response['visible_text'],
            'text': split_response['visible_text'],
            'visible_text': split_response['visible_text'],
            'reasoning': split_response['reasoning_text'],
            'reasoning_text': split_response['reasoning_text']
        })"""

content = re.sub(pattern2, replacement2, content)

# Pattern 3: Summary endpoints (already have suggestion field)
pattern3 = r"return jsonify\(\{\s*'summary':\s*split_response\['visible_text'\],\s*#\s*Keep 'summary' for backward compatibility\s*'suggestion':\s*split_response\['visible_text'\],\s*#\s*Also provide 'suggestion' for consistency\s*'reasoning':\s*split_response\['reasoning_text'\]\s*\}\)"
replacement3 = """return jsonify({
            'summary': split_response['visible_text'],  # Keep 'summary' for backward compatibility
            'suggestion': split_response['visible_text'],  # Also provide 'suggestion' for consistency
            'text': split_response['visible_text'],
            'visible_text': split_response['visible_text'],
            'reasoning': split_response['reasoning_text'],
            'reasoning_text': split_response['reasoning_text']
        })"""

content = re.sub(pattern3, replacement3, content)

# Write back
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all AI endpoint responses in main.py")
