#!/usr/bin/env python3
"""
Simple pytest runner for dtube module tests.
Run this script to execute all tests with pytest.
"""

import subprocess
import sys
import os

def main():
    """Run pytest on the test directory."""
    print("Running dtube tests with pytest...")
    
    # Run pytest
    result = subprocess.run([
        'pytest', 'test/', 
        '-v', 
        '--tb=short',
        '--timeout=5'
    ], capture_output=False)
    
    return result.returncode

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
