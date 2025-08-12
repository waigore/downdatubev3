#!/usr/bin/env python3
"""
Main test runner for all dtube module tests.
"""

import sys
import os

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests():
    """Run all test modules."""
    print("=== dtube Module Test Suite ===\n")
    
    # Import and run test modules
    try:
        from test.test_downloader import run_downloader_tests
        from test.test_driver import run_driver_tests
        
        # Run downloader tests
        print("Running downloader tests...")
        downloader_success = run_downloader_tests()
        print()
        
        # Run driver tests
        print("Running driver tests...")
        driver_success = run_driver_tests()
        print()
        
        # Overall results
        print("=== Overall Test Results ===")
        if downloader_success and driver_success:
            print("🎉 All tests passed! The dtube module is working correctly.")
            return True
        else:
            print("❌ Some tests failed. Please check the errors above.")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import test modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
