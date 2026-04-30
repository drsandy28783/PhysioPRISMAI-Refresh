#!/usr/bin/env python3
"""
Fix all mobile AI endpoint responses to include both old and new field names.
"""

import re

# Read mobile_api_ai.py
with open('mobile_api_ai.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: return jsonify({'suggestion': suggestion}), 200
# Replace with split_response version
def replace_suggestion_return(match):
    indent = match.group(1)
    return f"""{indent}split_response = split_ai_response(suggestion)
{indent}return jsonify({{
{indent}    'suggestion': split_response['visible_text'],
{indent}    'text': split_response['visible_text'],
{indent}    'visible_text': split_response['visible_text'],
{indent}    'reasoning': split_response['reasoning_text'],
{indent}    'reasoning_text': split_response['reasoning_text']
{indent}}}), 200"""

pattern1 = r"(\s+)return jsonify\(\{'suggestion': suggestion\}\), 200"
content = re.sub(pattern1, replace_suggestion_return, content)

# Pattern 2: return jsonify({'summary': suggestion}), 200
def replace_summary_return(match):
    indent = match.group(1)
    return f"""{indent}split_response = split_ai_response(suggestion)
{indent}return jsonify({{
{indent}    'summary': split_response['visible_text'],
{indent}    'suggestion': split_response['visible_text'],
{indent}    'text': split_response['visible_text'],
{indent}    'visible_text': split_response['visible_text'],
{indent}    'reasoning': split_response['reasoning_text'],
{indent}    'reasoning_text': split_response['reasoning_text']
{indent}}}), 200"""

pattern2 = r"(\s+)return jsonify\(\{'summary': suggestion\}\), 200"
content = re.sub(pattern2, replace_summary_return, content)

# Pattern 3: return jsonify({'suggestion': suggestion, 'diagnosis': suggestion}), 200
def replace_diagnosis_return(match):
    indent = match.group(1)
    return f"""{indent}split_response = split_ai_response(suggestion)
{indent}return jsonify({{
{indent}    'suggestion': split_response['visible_text'],
{indent}    'diagnosis': split_response['visible_text'],
{indent}    'text': split_response['visible_text'],
{indent}    'visible_text': split_response['visible_text'],
{indent}    'reasoning': split_response['reasoning_text'],
{indent}    'reasoning_text': split_response['reasoning_text']
{indent}}}), 200"""

pattern3 = r"(\s+)return jsonify\(\{'suggestion': suggestion, 'diagnosis': suggestion\}\), 200"
content = re.sub(pattern3, replace_diagnosis_return, content)

# Write back
with open('mobile_api_ai.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all mobile AI endpoint responses in mobile_api_ai.py")
