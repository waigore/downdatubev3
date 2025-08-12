#!/usr/bin/env python3
"""
Tests for dtube.downloader module.
"""

import sys
import os
import time
import tempfile
import shutil

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_video_id_extraction():
    """Test video ID extraction functionality."""
    print("Testing video ID extraction...")
    
    try:
        from dtube.downloader import extract_video_id
        
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            extracted_id = extract_video_id(url)
            if extracted_id == expected_id:
                print(f"✓ {url} → {extracted_id}")
            else:
                print(f"✗ {url} → {extracted_id} (expected: {expected_id})")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Video ID extraction test failed: {e}")
        return False


def test_download_manager():
    """Test the download manager functionality."""
    print("Testing download manager...")
    
    try:
        from dtube.downloader import DownloadManager
        
        manager = DownloadManager()
        
        # Test adding a download
        test_info = {'url': 'test_url', 'output_path': 'test_path'}
        manager.add_download('test_id', test_info)
        
        # Test getting download info
        download_info = manager.get_download('test_id')
        if download_info and download_info['url'] == 'test_url':
            print("✓ Download manager add/get works")
        else:
            print("✗ Download manager add/get failed")
            return False
        
        # Test pausing
        if manager.pause_download('test_id'):
            download_info = manager.get_download('test_id')
            if download_info['paused']:
                print("✓ Download pause works")
            else:
                print("✗ Download pause failed")
                return False
        else:
            print("✗ Download pause failed")
            return False
        
        # Test resuming
        if manager.resume_download('test_id'):
            download_info = manager.get_download('test_id')
            if not download_info['paused']:
                print("✓ Download resume works")
            else:
                print("✗ Download resume failed")
                return False
        else:
            print("✗ Download resume failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Download manager test failed: {e}")
        return False


def test_file_existence():
    """Test that downloaded videos actually exist in the output path."""
    print("Testing file existence after download...")
    
    try:
        from dtube import download_video
        from dtube.utils import get_download_status, get_download_progress
        
        # Create a temporary directory for testing
        test_output_dir = tempfile.mkdtemp(prefix="dtube_test_")
        print(f"📁 Using test output directory: {test_output_dir}")
        
        # Use a short, reliable video for testing (Rick Roll - very short)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        try:
            # Start the download
            print(f"🚀 Starting download: {test_url}")
            video_id = download_video(test_url, output_path=test_output_dir, quality="worst")
            print(f"✓ Download started for video ID: {video_id}")
            
            # Monitor download progress
            max_wait_time = 60  # Maximum 60 seconds to wait
            start_time = time.time()
            
            while True:
                if time.time() - start_time > max_wait_time:
                    print("⚠️  Test timed out - download may still be in progress")
                    break
                
                status = get_download_status(video_id)
                if not status:
                    print("✓ Download completed")
                    break
                
                progress = get_download_progress(video_id)
                elapsed = time.time() - start_time
                
                if status['status'] == 'downloading':
                    print(f"📥 Progress: {progress:.1f}% ({elapsed:.0f}s elapsed)")
                elif status['status'] == 'completed':
                    print("✅ Download completed successfully")
                    break
                elif status['status'] == 'error':
                    print(f"❌ Download failed: {status.get('error', 'Unknown error')}")
                    return False
                
                time.sleep(2)
            
            # Check if the file actually exists
            print(f"🔍 Checking for downloaded file in: {test_output_dir}")
            files_in_dir = os.listdir(test_output_dir)
            print(f"📋 Files found: {files_in_dir}")
            
            # Look for a file that starts with the video ID
            downloaded_file = None
            for filename in files_in_dir:
                if filename.startswith(video_id):
                    downloaded_file = filename
                    break
            
            if downloaded_file:
                file_path = os.path.join(test_output_dir, downloaded_file)
                file_size = os.path.getsize(file_path)
                print(f"✅ File found: {downloaded_file} ({file_size} bytes)")
                
                # Verify file is not empty (should be at least a few KB)
                if file_size > 1024:
                    print("✅ File size is reasonable")
                    return True
                else:
                    print("❌ File is too small - download may have failed")
                    return False
            else:
                print("❌ No file found with expected video ID prefix")
                return False
                
        finally:
            # Clean up test directory
            print(f"🧹 Cleaning up test directory: {test_output_dir}")
            try:
                shutil.rmtree(test_output_dir)
                print("✓ Test directory cleaned up")
            except Exception as e:
                print(f"⚠️  Warning: Could not clean up test directory: {e}")
        
    except Exception as e:
        print(f"✗ File existence test failed: {e}")
        return False


def run_downloader_tests():
    """Run all downloader tests."""
    print("=== dtube.downloader Module Tests ===\n")
    
    tests = [
        test_video_id_extraction,
        test_download_manager,
        test_file_existence,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Downloader Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All downloader tests passed!")
        return True
    else:
        print("❌ Some downloader tests failed.")
        return False


if __name__ == "__main__":
    success = run_downloader_tests()
    sys.exit(0 if success else 1)
