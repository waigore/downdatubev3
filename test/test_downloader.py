#!/usr/bin/env python3
"""
Tests for dtube.downloader module.
"""

import sys
import os
import time
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

# Add the parent directory to Python path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.timeout(5)
def test_video_id_extraction():
    """Test video ID extraction from various YouTube URL formats."""
    from dtube.downloader import extract_video_id

    # Test different YouTube URL formats
    test_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),  # Already a video ID
    ]

    for url, expected_id in test_cases:
        extracted_id = extract_video_id(url)
        assert extracted_id == expected_id, f"Expected {expected_id} for {url}, got {extracted_id}"

@pytest.mark.timeout(5)
def test_download_manager():
    """Test the download manager functionality."""
    from dtube.downloader import _download_manager

    # Clear any existing downloads
    _download_manager._downloads.clear()

    # Test adding a download
    test_video_id = "test123"
    test_info = {
        'url': 'https://youtube.com/watch?v=test123',
        'title': 'Test Video',
        'output_path': 'downloads',
        'quality': 'best'
    }
    
    _download_manager.add_download(test_video_id, test_info)
    
    # Verify download was added
    stored_info = _download_manager.get_download(test_video_id)
    assert stored_info is not None
    assert stored_info['url'] == test_info['url']
    assert stored_info['title'] == test_info['title']
    assert stored_info['status'] == 'downloading'
    
    # Test updating status
    _download_manager.update_download_status(test_video_id, 'completed', progress=100.0)
    updated_info = _download_manager.get_download(test_video_id)
    assert updated_info['status'] == 'completed'
    assert updated_info['progress'] == 100.0
    
    # Test pausing and resuming
    assert _download_manager.pause_download(test_video_id)
    paused_info = _download_manager.get_download(test_video_id)
    assert paused_info['status'] == 'paused'
    assert paused_info['paused'] == True
    
    assert _download_manager.resume_download(test_video_id)
    resumed_info = _download_manager.get_download(test_video_id)
    assert resumed_info['status'] == 'downloading'
    assert resumed_info['paused'] == False
    
    # Test removal
    _download_manager.remove_download(test_video_id)
    assert _download_manager.get_download(test_video_id) is None

@pytest.mark.timeout(5)
def test_format_selection():
    """Test the format selection logic."""
    # The actual implementation doesn't have a separate select_best_format function
    # Format selection is handled directly in download_video with yt-dlp options
    from dtube.downloader import download_video

    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="dtube_test_")

    try:
        # Mock the actual download to avoid network calls
        with patch('dtube.downloader._download_worker') as mock_worker:
            mock_worker.return_value = None
            
            # Mock the title extraction
            with patch('dtube.downloader._extract_video_title') as mock_extract:
                mock_extract.return_value = "Test Video Title"
                
                # Test download with format selection
                video_id = download_video("https://youtube.com/watch?v=test123", temp_dir, "best")
                
                # Verify download was added to manager
                from dtube.downloader import _download_manager
                download_info = _download_manager.get_download(video_id)
                assert download_info is not None
                
                # Check that yt-dlp options contain format specification
                ydl_opts = download_info.get('ydl_opts', {})
                assert 'format' in ydl_opts
                # The actual implementation uses a specific format string
                expected_format = 'bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio'
                assert ydl_opts['format'] == expected_format
                
                # Clean up
                _download_manager.remove_download(video_id)
                
    finally:
        shutil.rmtree(temp_dir)

@pytest.mark.timeout(5)
def test_download_validation():
    """Test download validation logic."""
    # The actual implementation doesn't have a separate validate_download_url function
    # Basic validation is done in the main script by checking URL format
    from dtube.downloader import extract_video_id

    # Test valid URLs
    valid_urls = [
        "https://www.youtube.com/watch?v=test123",
        "https://youtu.be/test123",
        "https://www.youtube.com/embed/test123"
    ]
    
    for url in valid_urls:
        video_id = extract_video_id(url)
        assert video_id is not None
        assert len(video_id) > 0
    
    # Test invalid URLs (should still extract something, even if not valid)
    invalid_urls = [
        "not_a_url",
        "https://example.com/video",
        "ftp://youtube.com/video"
    ]
    
    for url in invalid_urls:
        video_id = extract_video_id(url)
        # The current implementation returns the URL as-is for non-YouTube URLs
        assert video_id is not None

@pytest.mark.timeout(5)
def test_file_existence():
    """Test file existence checking functionality."""
    from dtube.utils import check_for_part_files

    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="dtube_test_")

    try:
        # Create some test files
        test_files = [
            "video1.mp4",
            "video2.part",
            "video3.webm",
            "video4.part"
        ]
        
        for filename in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        # Check for .part files
        part_files = check_for_part_files(temp_dir)
        
        # Should find 2 .part files
        assert len(part_files) == 2
        assert "video2.part" in part_files
        assert "video4.part" in part_files
        
    finally:
        shutil.rmtree(temp_dir)
