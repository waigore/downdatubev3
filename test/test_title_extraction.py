#!/usr/bin/env python3
"""
Tests for dtube.downloader title extraction functionality.
"""

import sys
import os
from unittest.mock import patch

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_title_cleaning():
    """Test the title cleaning functionality with various problematic titles."""
    print("Testing title cleaning functionality...")
    
    try:
        from dtube.downloader import _clean_title_for_filename
        
        test_titles = [
            ("Normal Title", "Normal Title"),
            ("Title with <brackets> and \"quotes\"", "Title with _brackets_ and _quotes_"),
            ("Title with /slashes\\ and |pipes|", "Title with _slashes_ and _pipes_"),
            ("Title with ?question? and *asterisk* marks", "Title with _question_ and _asterisk_ marks"),
            ("Very long title that exceeds the maximum length limit and should be truncated appropriately to fit within the filename constraints", "Very long title that exceeds the maximum length limit and should be truncated appropriately to fit w"),
            ("Title with leading and trailing spaces and dots . . .", "Title with leading and trailing spaces and dots"),
            ("", ""),  # Empty title
            ("Title with multiple     spaces", "Title with multiple     spaces")
        ]
        
        for original, expected in test_titles:
            cleaned = _clean_title_for_filename(original)
            if cleaned == expected:
                print(f"✓ '{original}' → '{cleaned}'")
            else:
                print(f"✗ '{original}' → '{cleaned}' (expected: '{expected}')")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Title cleaning test failed: {e}")
        return False


def test_filename_template_creation():
    """Test filename template creation with and without titles."""
    print("Testing filename template creation...")
    
    try:
        from dtube.downloader import _create_filename_template
        
        test_cases = [
            ("Test Title", "video123", "Test Title_video123.%(ext)s"),
            ("", "video123", "video123.%(ext)s"),
            ("Very Long Title That Should Be Truncated", "video456", "Very Long Title That Should Be Truncated_video456.%(ext)s"),
        ]
        
        for title, video_id, expected in test_cases:
            template = _create_filename_template(title, video_id)
            if template == expected:
                print(f"✓ Title: '{title}', Video ID: '{video_id}' → '{template}'")
            else:
                print(f"✗ Title: '{title}', Video ID: '{video_id}' → '{template}' (expected: '{expected}')")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Filename template creation test failed: {e}")
        return False


def test_title_extraction_integration():
    """Test the complete title extraction workflow."""
    print("Testing title extraction integration...")
    
    try:
        from dtube.downloader import _clean_title_for_filename, _create_filename_template
        from unittest.mock import patch
        
        # Mock video ID and title (no network call needed)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = "dQw4w9WgXcQ"
        
        # Mock the title extraction to avoid network calls
        with patch('dtube.downloader._extract_video_title') as mock_extract:
            mock_extract.return_value = "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)"
            
            # Extract title (mocked)
            title = mock_extract(test_url)
            if not title:
                print("✗ Title extraction failed - no title returned")
                return False
            
            print(f"✓ Extracted title: '{title}'")
            
            # Clean title
            cleaned_title = _clean_title_for_filename(title)
            if not cleaned_title:
                print("✗ Title cleaning failed - no cleaned title returned")
                return False
            
            print(f"✓ Cleaned title: '{cleaned_title}'")
            
            # Create filename template
            filename_template = _create_filename_template(cleaned_title, video_id)
            if not filename_template:
                print("✗ Filename template creation failed")
                return False
            
            print(f"✓ Filename template: '{filename_template}'")
            
            # Verify the template contains both title and video ID
            if cleaned_title in filename_template and video_id in filename_template:
                print("✓ Template contains both title and video ID")
            else:
                print("✗ Template missing title or video ID")
                return False
            
            return True
        
    except Exception as e:
        print(f"✗ Title extraction integration test failed: {e}")
        return False


def run_title_extraction_tests():
    """Run all title extraction tests."""
    print("=== Title Extraction Tests ===\n")
    
    tests = [
        test_title_cleaning,
        test_filename_template_creation,
        test_title_extraction_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            print()
    
    print(f"Title extraction tests: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    success = run_title_extraction_tests()
    sys.exit(0 if success else 1)
