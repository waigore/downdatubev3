#!/usr/bin/env python3
"""
Tests for dtube.downloader download functionality with new filename format.
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
def test_download_filename_format():
    """Test that download filenames are formatted correctly."""
    from dtube.downloader import _create_filename_template

    # Test with title and video ID
    template = _create_filename_template("Test Video", "video123")
    assert template == "Test Video_video123.%(ext)s"

    # Test with empty title
    template = _create_filename_template("", "video123")
    assert template == "video123.%(ext)s"

    # Test with None title
    template = _create_filename_template(None, "video123")
    assert template == "video123.%(ext)s"

@pytest.mark.timeout(5)
def test_download_manager_title_storage():
    """Test that the download manager properly stores title information."""
    from dtube.downloader import _download_manager

    # Clear any existing downloads
    _download_manager._downloads.clear()

    # Add a test download
    test_video_id = "test123"
    test_info = {
        'url': 'https://youtube.com/watch?v=test123',
        'title': 'Test Video Title',
        'output_path': 'downloads',
        'quality': 'best'
    }
    
    _download_manager.add_download(test_video_id, test_info)
    
    # Verify title is stored
    stored_info = _download_manager.get_download(test_video_id)
    assert stored_info is not None
    assert stored_info['title'] == 'Test Video Title'
    
    # Clean up
    _download_manager.remove_download(test_video_id)

@pytest.mark.timeout(5)
def test_filename_template_generation():
    """Test that filename templates are generated correctly."""
    from dtube.downloader import _create_filename_template

    test_cases = [
        ("Test Video", "video123", "Test Video_video123.%(ext)s"),
        ("", "video123", "video123.%(ext)s"),
        ("Very Long Title That Should Be Truncated", "video456", "Very Long Title That Should Be Truncated_video456.%(ext)s"),
        ("Title with Special Chars < > \" '", "video789", "Title with Special Chars < > \" '_video789.%(ext)s"),
    ]

    for title, video_id, expected in test_cases:
        template = _create_filename_template(title, video_id)
        assert template == expected, f"Expected '{expected}' for title '{title}' and video ID '{video_id}', got '{template}'"

@pytest.mark.timeout(5)
def test_download_with_custom_filename():
    """Test downloading with custom filename format."""
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
                
                # Test download with custom filename
                video_id = download_video("https://youtube.com/watch?v=test123", temp_dir, "best")
                
                # Verify video ID was returned
                assert video_id == "test123"
                
                # Verify download was added to manager
                from dtube.downloader import _download_manager
                download_info = _download_manager.get_download(video_id)
                assert download_info is not None
                assert download_info['title'] == "Test Video Title"
                
                # Clean up
                _download_manager.remove_download(video_id)
                
    finally:
        shutil.rmtree(temp_dir)

@pytest.mark.timeout(5)
def test_filename_cleaning():
    """Test that filenames are properly cleaned for filesystem compatibility."""
    from dtube.downloader import _clean_title_for_filename

    test_cases = [
        ("Normal Title", "Normal Title"),
        ("Title with <brackets>", "Title with _brackets_"),
        ("Title with /slashes\\", "Title with _slashes_"),
        ("Title with |pipes|", "Title with _pipes_"),
        ("Title with ?question?", "Title with _question_"),
        ("Title with *asterisk*", "Title with _asterisk_"),
        ("Title with \"quotes\"", "Title with _quotes_"),
        ("Title with 'apostrophes'", "Title with 'apostrophes'"),  # Single quotes are not replaced in actual implementation
    ]

    for original, expected in test_cases:
        cleaned = _clean_title_for_filename(original)
        assert cleaned == expected, f"Expected '{expected}' for '{original}', got '{cleaned}'"

@pytest.mark.timeout(5)
def test_download_manager_integration():
    """Test download manager integration with filename handling."""
    from dtube.downloader import _download_manager, _create_filename_template

    # Clear existing downloads
    _download_manager._downloads.clear()

    # Test adding a download with title
    test_video_id = "test456"
    test_info = {
        'url': 'https://youtube.com/watch?v=test456',
        'title': 'Integration Test Video',
        'output_path': 'downloads',
        'quality': '720p'
    }
    
    _download_manager.add_download(test_video_id, test_info)
    
    # Verify filename template generation works with stored title
    stored_info = _download_manager.get_download(test_video_id)
    template = _create_filename_template(stored_info['title'], test_video_id)
    assert template == "Integration Test Video_test456.%(ext)s"
    
    # Clean up
    _download_manager.remove_download(test_video_id)

@pytest.mark.timeout(5)
def test_download_status_tracking():
    """Test that download status is properly tracked with filename information."""
    from dtube.downloader import _download_manager

    # Clear existing downloads
    _download_manager._downloads.clear()

    # Add a test download
    test_video_id = "test789"
    test_info = {
        'url': 'https://youtube.com/watch?v=test789',
        'title': 'Status Test Video',
        'output_path': 'downloads',
        'quality': 'best'
    }
    
    _download_manager.add_download(test_video_id, test_info)
    
    # Update status
    _download_manager.update_download_status(test_video_id, 'downloading', progress=50.0)
    
    # Verify status was updated
    stored_info = _download_manager.get_download(test_video_id)
    assert stored_info['status'] == 'downloading'
    assert stored_info['progress'] == 50.0
    assert stored_info['title'] == 'Status Test Video'
    
    # Clean up
    _download_manager.remove_download(test_video_id)

@pytest.mark.timeout(5)
def test_download_cleanup():
    """Test that downloads can be properly cleaned up."""
    from dtube.downloader import _download_manager

    # Clear existing downloads
    _download_manager._downloads.clear()

    # Add multiple test downloads
    test_video_ids = ["cleanup1", "cleanup2", "cleanup3"]
    for video_id in test_video_ids:
        test_info = {
            'url': f'https://youtube.com/watch?v={video_id}',
            'title': f'Cleanup Test {video_id}',
            'output_path': 'downloads',
            'quality': 'best'
        }
        _download_manager.add_download(video_id, test_info)
    
    # Verify downloads were added
    assert len(_download_manager._downloads) == 3
    
    # Clean up all downloads
    for video_id in test_video_ids:
        _download_manager.remove_download(video_id)
    
    # Verify all downloads were removed
    assert len(_download_manager._downloads) == 0

@pytest.mark.timeout(5)
def test_download_error_handling():
    """Test that download errors are properly handled."""
    from dtube.downloader import _download_manager

    # Clear existing downloads
    _download_manager._downloads.clear()

    # Add a test download
    test_video_id = "error123"
    test_info = {
        'url': 'https://youtube.com/watch?v=error123',
        'title': 'Error Test Video',
        'output_path': 'downloads',
        'quality': 'best'
    }
    
    _download_manager.add_download(test_video_id, test_info)
    
    # Simulate an error
    _download_manager.update_download_status(test_video_id, 'error', error='Test error message')
    
    # Verify error status was recorded
    stored_info = _download_manager.get_download(test_video_id)
    assert stored_info['status'] == 'error'
    assert stored_info['error'] == 'Test error message'
    assert stored_info['title'] == 'Error Test Video'  # Title should still be preserved
    
    # Clean up
    _download_manager.remove_download(test_video_id)
