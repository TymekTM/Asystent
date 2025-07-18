#!/usr/bin/env python3
"""Fix linting errors in routes.py."""

import re

def fix_routes_file():
    """Fix common linting issues in routes.py."""
    with open('server/api/routes.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix unused loop variable
    content = re.sub(r'for user_email_key, user_data', 'for _, user_data', content)
    
    # Fix exception handling - add 'from e' to remaining except clauses
    patterns = [
        (r'(except Exception as e:\s+logger\.error\([^)]+\)\s+raise HTTPException\([^)]+\))(?! from)', r'\1 from e'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Fix bare except
    content = re.sub(r'except:', 'except Exception:', content)
    
    with open('server/api/routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed routes.py linting issues")

if __name__ == '__main__':
    fix_routes_file()
