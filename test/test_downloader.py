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

'''
def test_format_selection():
    """Test the format selection logic."""
    print("Testing format selection logic...")
    
    try:
        from dtube.downloader import _select_best_format
        
        # Test case 1: Empty formats list
        result = _select_best_format([])
        if result is None:
            print("✓ Empty formats list returns None")
        else:
            print("✗ Empty formats list should return None")
            return False
        
        # Test case 2: Video-only formats should be acceptable for separate downloads
        video_only_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'none', 'height': 1080, 'width': 1920, 'ext': 'mp4'},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'none', 'height': 720, 'width': 1280, 'ext': 'mp4'},
        ]
        result = _select_best_format(video_only_formats, 720)
        if result and result['format_id'] == '1' and result['height'] == 1080:
            print("✓ Video-only formats correctly selected highest quality (1080p) for separate downloads")
        else:
            print(f"✗ Should select 1080p video-only format (highest quality), got: {result}")
            return False
        
        # Test case 3: No suitable formats (all audio-only)
        audio_only_formats = [
            {'format_id': '1', 'vcodec': 'none', 'acodec': 'aac', 'height': 0, 'width': 0, 'ext': 'm4a'},
            {'format_id': '2', 'vcodec': 'none', 'acodec': 'mp3', 'height': 0, 'width': 0, 'ext': 'mp3'},
        ]
        result = _select_best_format(audio_only_formats, 720)
        if result is None:
            print("✓ Audio-only formats correctly filtered out")
        else:
            print("✗ Audio-only formats should be filtered out")
            return False
        
        # Test case 4: No suitable formats (HLS protocols)
        hls_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 1080, 'width': 1920, 'ext': 'mp4', 'protocol': 'm3u8'},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'mp4', 'protocol': 'm3u8_native'},
        ]
        result = _select_best_format(hls_formats, 720)
        if result is None:
            print("✓ HLS protocol formats correctly filtered out")
        else:
            print(f"✗ HLS protocol formats should be filtered out, got: {result}")
            return False
        
        # Test case 5: Formats below target height (should fall back to 480p)
        low_height_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 480, 'width': 854, 'ext': 'mp4'},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 360, 'width': 640, 'ext': 'mp4'},
        ]
        result = _select_best_format(low_height_formats, 720)
        if result and result['format_id'] == '1' and result['height'] == 480:
            print("✓ Correctly fell back to 480p when 720p not available")
        else:
            print(f"✗ Should fall back to 480p, got: {result}")
            return False
        
        # Test case 6: Suitable formats at target height
        suitable_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'mp4', 'filesize': 1000000},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 1080, 'width': 1920, 'ext': 'mp4', 'filesize': 2000000},
            {'format_id': '3', 'vcodec': 'h264', 'acodec': 'aac', 'height': 480, 'width': 854, 'ext': 'mp4', 'filesize': 500000},
        ]
        result = _select_best_format(suitable_formats, 720)
        if result and result['format_id'] == '2':  # Should select 1080p as highest quality
            print("✓ Correctly selected highest quality format")
        else:
            print(f"✗ Should select 1080p format, got: {result}")
            return False
        
        # Test case 7: MP4 preference
        mixed_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'webm', 'filesize': 1000000},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'mp4', 'filesize': 1000000},
            {'format_id': '3', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'avi', 'filesize': 1000000},
        ]
        result = _select_best_format(mixed_formats, 720)
        if result and result['format_id'] == '2' and result['ext'] == 'mp4':
            print("✓ Correctly preferred MP4 format")
        else:
            print(f"✗ Should prefer MP4 format, got: {result}")
            return False
        
        # Test case 8: Fallback to lower height when target not met
        fallback_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 480, 'width': 854, 'ext': 'mp4'},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 360, 'width': 640, 'ext': 'mp4'},
        ]
        result = _select_best_format(fallback_formats, 720)
        if result and result['format_id'] == '1' and result['height'] == 480:
            print("✓ Correctly fell back to 480p when 720p not available")
        else:
            print(f"✗ Should fall back to 480p, got: {result}")
            return False
        
        # Test case 9: Final fallback to any video+audio format
        final_fallback_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 240, 'width': 426, 'ext': 'mp4'},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 144, 'width': 256, 'ext': 'mp4'},
        ]
        result = _select_best_format(final_fallback_formats, 720)
        if result and result['format_id'] == '1' and result['height'] == 240:
            print("✓ Correctly fell back to any video+audio format")
        else:
            print(f"✗ Should fall back to any video+audio format, got: {result}")
            return False
        
        # Test case 10: Quality sorting (height first, then filesize)
        quality_formats = [
            {'format_id': '1', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'mp4', 'filesize': 2000000},
            {'format_id': '2', 'vcodec': 'h264', 'acodec': 'aac', 'height': 720, 'width': 1280, 'ext': 'mp4', 'filesize': 1000000},
            {'format_id': '3', 'vcodec': 'h264', 'acodec': 'aac', 'height': 1080, 'width': 1920, 'ext': 'mp4', 'filesize': 1500000},
        ]
        result = _select_best_format(quality_formats, 720)
        if result and result['format_id'] == '3' and result['height'] == 1080:
            print("✓ Correctly sorted by quality (height first)")
        else:
            print(f"✗ Should select 1080p format, got: {result}")
            return False
        
        print("✓ All format selection tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Format selection test failed: {e}")
        return False
    '''

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
            
            # Look for a file that contains the video ID (new format: title_videoID.ext)
            downloaded_file = None
            for filename in files_in_dir:
                if video_id in filename:
                    downloaded_file = filename
                    break
            
            if downloaded_file:
                file_path = os.path.join(test_output_dir, downloaded_file)
                file_size = os.path.getsize(file_path)
                print(f"✅ File found: {downloaded_file} ({file_size} bytes)")
                
                # Verify file is not empty (should be at least a few KB)
                if file_size > 1024:
                    print("✅ File size is reasonable")
                    
                    # Check if the file follows the new naming convention
                    if '_' in downloaded_file and video_id in downloaded_file:
                        print("✅ File follows the new title_videoID naming convention")
                    else:
                        print("⚠️  File doesn't follow the expected naming convention")
                    
                    return True
                else:
                    print("❌ File is too small - download may have failed")
                    return False
            else:
                print("❌ No file found containing the video ID")
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
