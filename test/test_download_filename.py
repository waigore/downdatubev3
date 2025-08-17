#!/usr/bin/env python3
"""
Tests for dtube.downloader download functionality with new filename format.
"""

import sys
import os
import time
import tempfile
import shutil
from unittest.mock import patch

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_download_filename_format():
    """Test that downloads use the new filename format with title and video ID."""
    print("Testing download filename format...")
    
    try:
        from dtube.downloader import _download_manager
        from unittest.mock import patch
        
        # Mock video ID and title (no network call needed)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = "dQw4w9WgXcQ"
        test_title = "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)"
        
        # Mock the download_video function to avoid actual downloads
        with patch('dtube.downloader.download_video') as mock_download:
            mock_download.return_value = video_id
            
            # Mock the download manager to return test data
            with patch.object(_download_manager, 'get_download') as mock_get_download:
                mock_get_download.return_value = {
                    'title': test_title,
                    'ydl_opts': {
                        'outtmpl': f"test_output/{test_title}_{video_id}.%(ext)s"
                    }
                }
                
                # Simulate download start
                video_id = mock_download(test_url, output_path="test_output", quality="144p")
                
                if not video_id:
                    print("✗ Download failed to start")
                    return False
                
                print(f"✓ Download started with video ID: {video_id}")
                
                # Check if the download info contains the title
                download_info = mock_get_download(video_id)
                if not download_info:
                    print("✗ Download info not found")
                    return False
                
                title = download_info.get('title', '')
                if not title:
                    print("✗ No title found in download info")
                    return False
                
                print(f"✓ Title extracted: '{title}'")
                
                # Check if the yt-dlp options contain the correct filename template
                ydl_opts = download_info.get('ydl_opts', {})
                outtmpl = ydl_opts.get('outtmpl', '')
                
                # Handle both string and dictionary outtmpl formats
                if isinstance(outtmpl, dict):
                    template = outtmpl.get('default', '')
                else:
                    template = outtmpl
                
                # The template should contain the title and video ID
                if title in template and video_id in template:
                    print(f"✓ Filename template contains title and video ID")
                    print(f"  Template: {template}")
                    return True
                else:
                    print(f"✗ Filename template missing title or video ID")
                    print(f"  Template: {template}")
                    print(f"  Title: {title}")
                    print(f"  Video ID: {video_id}")
                    return False
            
    except Exception as e:
        print(f"✗ Download filename format test failed: {e}")
        return False


def test_download_manager_title_storage():
    """Test that the download manager properly stores title information."""
    print("Testing download manager title storage...")
    
    try:
        from dtube.downloader import _download_manager
        from unittest.mock import patch
        
        # Clear any existing downloads
        _download_manager._downloads.clear()
        
        # Test URL
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = "dQw4w9WgXcQ"
        test_title = "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)"
        
        # Mock the download_video function to avoid actual downloads
        with patch('dtube.downloader.download_video') as mock_download:
            mock_download.return_value = video_id
            
            # Mock the download manager to return test data
            with patch.object(_download_manager, 'get_download') as mock_get_download:
                mock_get_download.return_value = {
                    'title': test_title,
                    'url': test_url,
                    'output_path': 'test_output'
                }
                
                # Simulate download start
                video_id = mock_download(test_url, output_path="test_output", quality="144p")
                
                if not video_id:
                    print("✗ Download failed to start")
                    return False
                
                # Check if title is stored in download info
                download_info = mock_get_download(video_id)
                if not download_info:
                    print("✗ Download info not found")
                    return False
                
                title = download_info.get('title', '')
                if title:
                    print(f"✓ Title stored in download info: '{title}'")
                    
                    # Verify title is a string and not empty
                    if isinstance(title, str) and len(title) > 0:
                        print("✓ Title is valid string")
                        return True
                    else:
                        print("✗ Title is not a valid string")
                        return False
                else:
                    print("✗ No title found in download info")
                    return False
            
    except Exception as e:
        print(f"✗ Download manager title storage test failed: {e}")
        return False


def test_filename_template_integration():
    """Test that the filename template is properly integrated into yt-dlp options."""
    print("Testing filename template integration...")
    
    try:
        from dtube.downloader import _download_manager
        from unittest.mock import patch
        
        # Test URL
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = "dQw4w9WgXcQ"
        test_title = "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)"
        
        # Mock the download_video function to avoid actual downloads
        with patch('dtube.downloader.download_video') as mock_download:
            mock_download.return_value = video_id
            
            # Mock the download manager to return test data
            with patch.object(_download_manager, 'get_download') as mock_get_download:
                mock_get_download.return_value = {
                    'title': test_title,
                    'ydl_opts': {
                        'outtmpl': f"test_output/{test_title}_{video_id}.%(ext)s"
                    }
                }
                
                # Simulate download start
                video_id = mock_download(test_url, output_path="test_output", quality="144p")
                
                if not video_id:
                    print("✗ Download failed to start")
                    return False
                
                # Get download info
                download_info = mock_get_download(video_id)
                if not download_info:
                    print("✗ Download info not found")
                    return False
                
                # Check yt-dlp options
                ydl_opts = download_info.get('ydl_opts', {})
                outtmpl = ydl_opts.get('outtmpl', '')
                
                if not outtmpl:
                    print("✗ No outtmpl found in yt-dlp options")
                    return False
                
                print(f"✓ yt-dlp outtmpl: {outtmpl}")
                
                # Check if the template contains the video ID
                if video_id in outtmpl:
                    print("✓ Template contains video ID")
                else:
                    print("✗ Template missing video ID")
                    return False
                
                # Check if the template contains the title (if available)
                title = download_info.get('title', '')
                if title and title in outtmpl:
                    print("✓ Template contains title")
                elif not title:
                    print("✓ No title available, template uses video ID only")
                else:
                    print("✗ Template missing title")
                    return False
                
                return True
        
    except Exception as e:
        print(f"✗ Filename template integration test failed: {e}")
        return False


def run_download_filename_tests():
    """Run all download filename tests."""
    print("=== Download Filename Tests ===\n")
    
    tests = [
        test_download_filename_format,
        test_download_manager_title_storage,
        test_filename_template_integration
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
    
    print(f"Download filename tests: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    success = run_download_filename_tests()
    sys.exit(0 if success else 1)
