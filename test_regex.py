#!/usr/bin/env python3
"""
Test regex parsing
"""
import re

def test_regex():
    test_string = "<datetime> <note>"
    param_matches = re.findall(r'<([^>]+)>', test_string)
    print(f"Input: {test_string}")
    print(f"Matches: {param_matches}")
    
    for param in param_matches:
        print(f"Parameter: '{param}'")

if __name__ == "__main__":
    test_regex()
