#!/usr/bin/env python3
"""
Tests for dtube.driver module.
"""

import sys
import os
import time
import tempfile
import shutil
import threading
import logging
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_download_driver_initialization():
    """Test DownloadDriver initialization and basic properties."""
    print("Testing DownloadDriver initialization...")
    
    try:
        from dtube import DownloadDriver
        
        # Test with default parameters
        driver = DownloadDriver()
        if (driver.max_concurrent == 3 and 
            driver.output_path == "downloads" and 
            driver.quality == "best" and
            driver.wait_timeout == 60):
            print("✓ Default initialization works")
        else:
            print("✗ Default initialization failed")
            return False
        
        # Test with custom parameters
        custom_driver = DownloadDriver(
            max_concurrent=5,
            output_path="custom_downloads",
            quality="720p"
        )
        if (custom_driver.max_concurrent == 5 and 
            custom_driver.output_path == "custom_downloads" and 
            custom_driver.quality == "720p"):
            print("✓ Custom initialization works")
        else:
            print("✗ Custom initialization failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver initialization test failed: {e}")
        return False


def test_download_driver_url_management():
    """Test DownloadDriver URL queue management."""
    print("Testing DownloadDriver URL management...")
    
    try:
        from dtube import DownloadDriver
        
        driver = DownloadDriver()
        
        # Test adding single URL
        test_url = "https://www.youtube.com/watch?v=test123"
        driver.add_url(test_url)
        if driver.download_queue.qsize() == 1:
            print("✓ Single URL addition works")
        else:
            print("✗ Single URL addition failed")
            return False
        
        # Test adding multiple URLs
        test_urls = [
            "https://www.youtube.com/watch?v=test456",
            "https://www.youtube.com/watch?v=test789"
        ]
        driver.add_urls(test_urls)
        if driver.download_queue.qsize() == 3:  # 1 + 2
            print("✓ Multiple URL addition works")
        else:
            print("✗ Multiple URL addition failed")
            return False
        
        # Test queue retrieval
        retrieved_urls = []
        while not driver.download_queue.empty():
            retrieved_urls.append(driver.download_queue.get())
        
        expected_urls = [test_url] + test_urls
        if retrieved_urls == expected_urls:
            print("✓ URL queue retrieval works")
        else:
            print(f"✗ URL queue retrieval failed: got {retrieved_urls}, expected {expected_urls}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver URL management test failed: {e}")
        return False


def test_download_driver_directory_creation():
    """Test DownloadDriver output directory creation."""
    print("Testing DownloadDriver directory creation...")
    
    try:
        from dtube import DownloadDriver
        
        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="dtube_test_")
        test_output = os.path.join(test_dir, "downloads")
        
        try:
            # Test that directory is created when it doesn't exist
            driver = DownloadDriver(output_path=test_output)
            if os.path.exists(test_output) and os.path.isdir(test_output):
                print("✓ Directory creation works")
            else:
                print("✗ Directory creation failed")
                return False
            
            # Test that existing directory is handled correctly
            driver2 = DownloadDriver(output_path=test_output)
            if os.path.exists(test_output) and os.path.isdir(test_output):
                print("✓ Existing directory handling works")
            else:
                print("✗ Existing directory handling failed")
                return False
                
        finally:
            # Clean up
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver directory creation test failed: {e}")
        return False


def test_download_driver_file_verification():
    """Test DownloadDriver file verification functionality."""
    print("Testing DownloadDriver file verification...")
    
    try:
        from dtube import DownloadDriver
        
        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="dtube_test_")
        
        try:
            driver = DownloadDriver(output_path=test_dir)
            
            # Test with non-existent video ID
            if not driver.verify_download_exists("nonexistent_id"):
                print("✓ Non-existent file verification works")
            else:
                print("✗ Non-existent file verification failed")
                return False
            
            # Test with existing file
            test_video_id = "test123"
            test_filename = f"{test_video_id}.mp4"
            test_filepath = os.path.join(test_dir, test_filename)
            
            # Create a test file
            with open(test_filepath, 'wb') as f:
                f.write(b"test content" * 100)  # Write some content
            
            if driver.verify_download_exists(test_video_id):
                print("✓ Existing file verification works")
            else:
                print("✗ Existing file verification failed")
                return False
            
            # Test with empty file (should fail) - create a file with different video ID
            empty_video_id = "test456"
            empty_filename = f"{empty_video_id}.mp4"
            empty_filepath = os.path.join(test_dir, empty_filename)
            with open(empty_filepath, 'wb') as f:
                pass  # Create empty file
            
            if not driver.verify_download_exists(empty_video_id, retry_count=1):
                print("✓ Empty file verification works")
            else:
                print("✗ Empty file verification failed")
                return False
                
        finally:
            # Clean up
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver file verification test failed: {e}")
        return False


def test_download_driver_monitoring():
    """Test DownloadDriver download monitoring functionality."""
    print("Testing DownloadDriver monitoring...")
    
    try:
        from dtube import DownloadDriver
        
        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="dtube_test_")
        
        try:
            driver = DownloadDriver(output_path=test_dir)
            
            # Mock the monitoring functions to avoid actual downloads
            with patch('dtube.driver.get_download_status') as mock_status, \
                 patch('dtube.driver.get_download_progress') as mock_progress:
                
                # Test monitoring with completed status
                mock_status.side_effect = [
                    {'status': 'downloading'},  # First call
                    {'status': 'downloading'},  # Second call
                    None  # Third call (completed)
                ]
                mock_progress.return_value = 50.0
                
                # Mock file verification to return True
                with patch.object(driver, 'verify_download_exists', return_value=True):
                    # Start monitoring in a separate thread
                    monitor_thread = threading.Thread(
                        target=driver.monitor_download,
                        args=("test123", "https://youtube.com/watch?v=test123"),
                        daemon=True
                    )
                    monitor_thread.start()
                    
                    # Wait for monitoring to complete
                    monitor_thread.join(timeout=5)
                    
                    if "test123" in driver.completed_downloads:
                        print("✓ Download monitoring with completion works")
                    else:
                        print("✗ Download monitoring with completion failed")
                        return False
                
                # Test monitoring with error status
                mock_status.side_effect = [
                    {'status': 'downloading'},
                    {'status': 'error'}
                ]
                mock_progress.return_value = 25.0
                
                # Reset completed downloads
                driver.completed_downloads.clear()
                driver.failed_downloads.clear()
                
                with patch.object(driver, 'verify_download_exists', return_value=False):
                    monitor_thread = threading.Thread(
                        target=driver.monitor_download,
                        args=("test456", "https://youtube.com/watch?v=test456"),
                        daemon=True
                    )
                    monitor_thread.start()
                    monitor_thread.join(timeout=5)
                    
                    if "test456" in driver.failed_downloads:
                        print("✓ Download monitoring with error works")
                    else:
                        print("✗ Download monitoring with error failed")
                        return False
                        
        finally:
            # Clean up
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver monitoring test failed: {e}")
        return False


def test_download_driver_worker():
    """Test DownloadDriver worker thread functionality."""
    print("Testing DownloadDriver worker...")
    
    try:
        from dtube import DownloadDriver
        
        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="dtube_test_")
        
        try:
            driver = DownloadDriver(output_path=test_dir, max_concurrent=1)
            
            # Mock the download functions
            with patch.object(driver, 'start_download', return_value="test123"), \
                 patch.object(driver, 'monitor_download') as mock_monitor:
                
                # Add a test URL to the queue
                test_url = "https://youtube.com/watch?v=test123"
                driver.add_url(test_url)
                
                # Start the worker thread
                worker_thread = threading.Thread(
                    target=driver.download_worker,
                    daemon=True
                )
                worker_thread.start()
                
                # Wait for worker to process the URL
                time.sleep(0.1)
                
                # Check if the download was started
                if "test123" in driver.active_downloads:
                    print("✓ Worker thread processing works")
                else:
                    print("✗ Worker thread processing failed")
                    return False
                
                # Stop the worker
                worker_thread.join(timeout=1)
                
        finally:
            # Clean up
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver worker test failed: {e}")
        return False


def test_download_driver_concurrency_control():
    """Test DownloadDriver concurrency control functionality."""
    print("Testing DownloadDriver concurrency control...")
    
    try:
        from dtube import DownloadDriver
        
        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="dtube_test_")
        
        try:
            # Test with max_concurrent=2
            driver = DownloadDriver(output_path=test_dir, max_concurrent=2)
            
            # Mock the download functions to simulate slow downloads
            def mock_start_download(url):
                # Simulate a download that takes time
                time.sleep(0.1)
                return f"video_{url.split('=')[-1]}"
            
            def mock_monitor_download(video_id, url):
                # Simulate monitoring that takes time
                time.sleep(0.2)
                # Mark as completed
                with driver.lock:
                    if video_id in driver.active_downloads:
                        del driver.active_downloads[video_id]
                    driver.completed_downloads.append(video_id)
            
            with patch.object(driver, 'start_download', side_effect=mock_start_download), \
                 patch.object(driver, 'monitor_download', side_effect=mock_monitor_download):
                
                # Add multiple test URLs to the queue
                test_urls = [
                    "https://youtube.com/watch?v=test1",
                    "https://youtube.com/watch?v=test2",
                    "https://youtube.com/watch?v=test3",
                    "https://youtube.com/watch?v=test4"
                ]
                driver.add_urls(test_urls)
                
                # Start worker threads
                workers = []
                for i in range(driver.max_concurrent):
                    worker = threading.Thread(
                        target=driver.download_worker,
                        daemon=True,
                        name=f"TestWorker-{i+1}"
                    )
                    worker.start()
                    workers.append(worker)
                
                # Wait for workers to process URLs
                time.sleep(0.1)
                
                # Check that we never exceed max_concurrent active downloads
                max_active = 0
                for _ in range(10):  # Check multiple times
                    current_active = len(driver.active_downloads)
                    max_active = max(max_active, current_active)
                    time.sleep(0.01)
                
                # Wait for all workers to finish
                for worker in workers:
                    worker.join(timeout=2)
                
                # Verify concurrency control
                if max_active <= driver.max_concurrent:
                    print(f"✓ Concurrency control works: max active downloads was {max_active}, limit was {driver.max_concurrent}")
                else:
                    print(f"✗ Concurrency control failed: max active downloads was {max_active}, limit was {driver.max_concurrent}")
                    return False
                
                # Verify all downloads were processed
                if len(driver.completed_downloads) == len(test_urls):
                    print("✓ All downloads were processed")
                else:
                    print(f"✗ Not all downloads were processed: {len(driver.completed_downloads)}/{len(test_urls)}")
                    return False
                
        finally:
            # Clean up
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver concurrency control test failed: {e}")
        return False


def test_download_driver_timeout():
    """Test DownloadDriver timeout functionality."""
    print("Testing DownloadDriver timeout...")
    
    try:
        from dtube import DownloadDriver
        
        # Create a temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="dtube_test_")
        
        try:
            driver = DownloadDriver(output_path=test_dir, max_concurrent=1)
            
            # Add a fake active download
            driver.active_downloads["test123"] = {
                'url': 'https://youtube.com/watch?v=test123',
                'start_time': time.time()
            }
            
            # Mock the status function to simulate ongoing download
            with patch('dtube.driver.get_download_status', return_value={'status': 'downloading'}):
                # Test timeout with a very short timeout
                start_time = time.time()
                driver.wait_for_all_downloads(timeout_minutes=0.01)  # 0.6 seconds
                elapsed = time.time() - start_time
                
                # The timeout should trigger and break the loop
                # Note: The method now sleeps for 0.5 seconds between checks, so it will take much less time
                if elapsed >= 0.5 and len(driver.active_downloads) == 1:  # Should timeout and keep the download active
                    print("✓ Download timeout works")
                else:
                    print(f"✗ Download timeout failed: elapsed={elapsed:.2f}s, active_downloads={len(driver.active_downloads)}")
                    return False
                    
        finally:
            # Clean up
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadDriver timeout test failed: {e}")
        return False


def run_driver_tests():
    """Run all driver tests."""
    print("=== dtube.driver Module Tests ===\n")
    
    tests = [
        test_download_driver_initialization,
        test_download_driver_url_management,
        test_download_driver_directory_creation,
        test_download_driver_file_verification,
        test_download_driver_monitoring,
        test_download_driver_worker,
        test_download_driver_concurrency_control,
        test_download_driver_timeout,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Driver Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All driver tests passed!")
        return True
    else:
        print("❌ Some driver tests failed.")
        return False


if __name__ == "__main__":
    success = run_driver_tests()
    sys.exit(0 if success else 1)
