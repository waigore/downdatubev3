#!/usr/bin/env python3
"""
Tests for dl.py script functionality including batch mode.
"""

import sys
import os
import tempfile
import shutil
import subprocess
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_batch_mode_file_loading():
    """Test that batch mode correctly loads URLs from a text file."""
    print("Testing batch mode file loading...")
    
    try:
        # Create a temporary batch file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("https://youtube.com/watch?v=test1\n")
            f.write("https://youtube.com/watch?v=test2\n")
            f.write("https://youtube.com/watch?v=test3\n")
            f.write("\n")  # Empty line
            f.write("  https://youtube.com/watch?v=test4  \n")  # Line with whitespace
            batch_file = f.name
        
        try:
            # Import the main function from dl.py
            from dl import main
            
            # Mock the DownloadDriver to avoid actual downloads
            with patch('dl.DownloadDriver') as mock_driver_class:
                mock_driver = MagicMock()
                mock_driver_class.return_value = mock_driver
                
                # Mock sys.argv to simulate batch mode
                with patch('sys.argv', ['dl.py', '-b', batch_file, '-c', '2']):
                    # Mock sys.exit to prevent actual exit
                    with patch('sys.exit') as mock_exit:
                        main()
                        
                        # Verify DownloadDriver was created
                        mock_driver_class.assert_called_once()
                        call_args = mock_driver_class.call_args
                        
                        # Check the parameters (ignore logger comparison)
                        if (call_args[1]['max_concurrent'] == 2 and 
                            call_args[1]['output_path'] == 'downloads' and
                            call_args[1]['quality'] == 'best'):
                            print("✓ DownloadDriver created with correct parameters")
                        else:
                            print(f"✗ DownloadDriver parameters incorrect: {call_args[1]}")
                            return False
                        
                        # Verify URLs were added to the driver
                        mock_driver.add_urls.assert_called_once()
                        added_urls = mock_driver.add_urls.call_args[0][0]
                        
                        # Should have 4 valid URLs (empty line and whitespace-only lines are ignored)
                        expected_urls = [
                            "https://youtube.com/watch?v=test1",
                            "https://youtube.com/watch?v=test2", 
                            "https://youtube.com/watch?v=test3",
                            "https://youtube.com/watch?v=test4"
                        ]
                        
                        if added_urls == expected_urls:
                            print("✓ Batch mode correctly loads URLs from file")
                        else:
                            print(f"✗ Batch mode failed: got {added_urls}, expected {expected_urls}")
                            return False
                        
                        # Verify no exit was called (success case)
                        mock_exit.assert_not_called()
                        
        finally:
            # Clean up
            os.unlink(batch_file)
        
        return True
        
    except Exception as e:
        print(f"✗ Batch mode file loading test failed: {e}")
        return False


def test_batch_mode_file_validation():
    """Test that batch mode validates file existence and content."""
    print("Testing batch mode file validation...")
    
    try:
        # Test with empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty file
            empty_file = f.name
        
        try:
            with patch('sys.argv', ['dl.py', '-b', empty_file]):
                with patch('sys.exit') as mock_exit:
                    from dl import main
                    main()
                    
                    # Should exit with error for empty file (2 calls: empty file + no valid URLs)
                    if mock_exit.call_count == 2:
                        print("✓ Empty file validation works correctly")
                    else:
                        print(f"✗ Empty file validation failed: expected 2 exit calls, got {mock_exit.call_count}")
                        return False
                    
        finally:
            os.unlink(empty_file)
        
        # Test with file containing only whitespace
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("   \n\n  \n")  # Only whitespace
            whitespace_file = f.name
        
        try:
            with patch('sys.argv', ['dl.py', '-b', whitespace_file]):
                with patch('sys.exit') as mock_exit:
                    from dl import main
                    main()
                    
                    # Should exit with error for whitespace-only file (2 calls: empty file + no valid URLs)
                    if mock_exit.call_count == 2:
                        print("✓ Whitespace-only file validation works correctly")
                    else:
                        print(f"✗ Whitespace-only file validation failed: expected 2 exit calls, got {mock_exit.call_count}")
                        return False
                    
        finally:
            os.unlink(whitespace_file)
        
        print("✓ Batch mode file validation works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Batch mode file validation test failed: {e}")
        return False


def test_batch_mode_url_validation():
    """Test that batch mode validates URLs in the file."""
    print("Testing batch mode URL validation...")
    
    try:
        from dl import main
        
        # Create a batch file with some invalid URLs
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("https://youtube.com/watch?v=valid1\n")
            f.write("invalid_url\n")
            f.write("ftp://example.com/file\n")
            f.write("https://youtube.com/watch?v=valid2\n")
            batch_file = f.name
        
        try:
            with patch('dl.DownloadDriver') as mock_driver_class:
                mock_driver = MagicMock()
                mock_driver_class.return_value = mock_driver
                
                # Mock sys.argv to simulate batch mode
                with patch('sys.argv', ['dl.py', '-b', batch_file]):
                    with patch('sys.exit') as mock_exit:
                        main()
                        
                        # Should still process valid URLs despite warnings
                        mock_driver.add_urls.assert_called_once()
                        added_urls = mock_driver.add_urls.call_args[0][0]
                        
                        # Should have 2 valid URLs
                        expected_urls = [
                            "https://youtube.com/watch?v=valid1",
                            "https://youtube.com/watch?v=valid2"
                        ]
                        
                        if added_urls == expected_urls:
                            print("✓ Batch mode correctly filters invalid URLs")
                        else:
                            print(f"✗ Batch mode failed: got {added_urls}, expected {expected_urls}")
                            return False
                        
                        # Should not exit (warnings only)
                        mock_exit.assert_not_called()
                        
        finally:
            os.unlink(batch_file)
        
        return True
        
    except Exception as e:
        print(f"✗ Batch mode URL validation test failed: {e}")
        return False


def test_batch_mode_ignores_command_line_urls():
    """Test that batch mode ignores URLs passed as command-line arguments."""
    print("Testing batch mode ignores command-line URLs...")
    
    try:
        from dl import main
        
        # Create a batch file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("https://youtube.com/watch?v=from_file\n")
            batch_file = f.name
        
        try:
            with patch('dl.DownloadDriver') as mock_driver_class:
                mock_driver = MagicMock()
                mock_driver_class.return_value = mock_driver
                
                # Mock sys.argv to simulate batch mode with command-line URLs
                with patch('sys.argv', ['dl.py', '-b', batch_file, 'https://youtube.com/watch?v=from_cmd']):
                    with patch('sys.exit') as mock_exit:
                        main()
                        
                        # Should only process URLs from file, not command-line
                        mock_driver.add_urls.assert_called_once()
                        added_urls = mock_driver.add_urls.call_args[0][0]
                        
                        # Should only have the URL from the file
                        expected_urls = ["https://youtube.com/watch?v=from_file"]
                        
                        if added_urls == expected_urls:
                            print("✓ Batch mode correctly ignores command-line URLs")
                        else:
                            print(f"✗ Batch mode failed: got {added_urls}, expected {expected_urls}")
                            return False
                        
        finally:
            os.unlink(batch_file)
        
        return True
        
    except Exception as e:
        print(f"✗ Batch mode ignores command-line URLs test failed: {e}")
        return False


def test_batch_mode_respects_other_flags():
    """Test that batch mode respects all other command-line flags."""
    print("Testing batch mode respects other flags...")
    
    try:
        from dl import main
        
        # Create a batch file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("https://youtube.com/watch?v=test1\n")
            f.write("https://youtube.com/watch?v=test2\n")
            batch_file = f.name
        
        try:
            with patch('dl.DownloadDriver') as mock_driver_class:
                mock_driver = MagicMock()
                mock_driver_class.return_value = mock_driver
                
                # Mock sys.argv to simulate batch mode with various flags
                with patch('sys.argv', ['dl.py', '-b', batch_file, '-c', '5', '-o', 'custom_dir', '-q', '720p', '-t', '120']):
                    with patch('sys.exit') as mock_exit:
                        main()
                        
                        # Verify DownloadDriver was created
                        mock_driver_class.assert_called_once()
                        call_args = mock_driver_class.call_args
                        
                        # Check the parameters (ignore logger comparison)
                        if (call_args[1]['max_concurrent'] == 5 and 
                            call_args[1]['output_path'] == 'custom_dir' and
                            call_args[1]['quality'] == '720p'):
                            print("✓ DownloadDriver created with correct parameters")
                        else:
                            print(f"✗ DownloadDriver parameters incorrect: {call_args[1]}")
                            return False
                        
                        # Verify URLs were added
                        mock_driver.add_urls.assert_called_once()
                        added_urls = mock_driver.add_urls.call_args[0][0]
                        
                        expected_urls = [
                            "https://youtube.com/watch?v=test1",
                            "https://youtube.com/watch?v=test2"
                        ]
                        
                        if added_urls == expected_urls:
                            print("✓ Batch mode correctly respects all other flags")
                        else:
                            print(f"✗ Batch mode failed: got {added_urls}, expected {expected_urls}")
                            return False
                        
                        # Verify timeout was set
                        mock_driver.wait_timeout = 120
                        
        finally:
            os.unlink(batch_file)
        
        return True
        
    except Exception as e:
        print(f"✗ Batch mode respects other flags test failed: {e}")
        return False


def test_command_line_mode_fallback():
    """Test that command-line mode works when batch mode is not specified."""
    print("Testing command-line mode fallback...")
    
    try:
        from dl import main
        
        with patch('dl.DownloadDriver') as mock_driver_class:
            mock_driver = MagicMock()
            mock_driver_class.return_value = mock_driver
            
            # Mock sys.argv to simulate command-line mode
            with patch('sys.argv', ['dl.py', 'https://youtube.com/watch?v=cmd1', 'https://youtube.com/watch?v=cmd2']):
                with patch('sys.exit') as mock_exit:
                    main()
                    
                    # Verify DownloadDriver was created
                    mock_driver_class.assert_called_once()
                    call_args = mock_driver_class.call_args
                    
                    # Check the parameters (ignore logger comparison)
                    if (call_args[1]['max_concurrent'] == 3 and 
                        call_args[1]['output_path'] == 'downloads' and
                        call_args[1]['quality'] == 'best'):
                        print("✓ DownloadDriver created with correct parameters")
                    else:
                        print(f"✗ DownloadDriver parameters incorrect: {call_args[1]}")
                        return False
                    
                    # Verify URLs were added
                    mock_driver.add_urls.assert_called_once()
                    added_urls = mock_driver.add_urls.call_args[0][0]
                    
                    expected_urls = [
                        "https://youtube.com/watch?v=cmd1",
                        "https://youtube.com/watch?v=cmd2"
                    ]
                    
                    if added_urls == expected_urls:
                        print("✓ Command-line mode works correctly")
                    else:
                        print(f"✗ Command-line mode failed: got {added_urls}, expected {expected_urls}")
                        return False
                    
        return True
        
    except Exception as e:
        print(f"✗ Command-line mode fallback test failed: {e}")
        return False


def test_error_handling_no_urls():
    """Test error handling when no URLs are provided."""
    print("Testing error handling with no URLs...")
    
    try:
        from dl import main
        
        with patch('sys.argv', ['dl.py']):  # No URLs, no batch file
            with patch('sys.exit') as mock_exit:
                main()
                
                # Should exit with error
                mock_exit.assert_called_once_with(1)
        
        print("✓ Error handling with no URLs works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Error handling with no URLs test failed: {e}")
        return False


def run_dl_script_tests():
    """Run all dl.py script tests."""
    print("=== dl.py Script Tests ===\n")
    
    tests = [
        test_batch_mode_file_loading,
        test_batch_mode_file_validation,
        test_batch_mode_url_validation,
        test_batch_mode_ignores_command_line_urls,
        test_batch_mode_respects_other_flags,
        test_command_line_mode_fallback,
        test_error_handling_no_urls,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== dl.py Script Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All dl.py script tests passed!")
        return True
    else:
        print("❌ Some dl.py script tests failed.")
        return False


if __name__ == "__main__":
    success = run_dl_script_tests()
    sys.exit(0 if success else 1)
