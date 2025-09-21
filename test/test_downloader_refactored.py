"""
Test the refactored DownloadManager with data access layer.
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime
from dtube.downloader import DownloadManager
from dtube.data_access import DownloadDataAccess


class TestDownloadManagerRefactored:
    """Test the refactored DownloadManager class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_dtube_downloads")
        yield db_path
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def data_access(self, temp_db_path):
        """Create a fresh DownloadDataAccess instance for testing."""
        data_access = DownloadDataAccess(db_path=temp_db_path)
        data_access.ensure_database_ready()  # Ensure it's initialized
        return data_access
    
    @pytest.fixture
    def download_manager(self, data_access):
        """Create a fresh DownloadManager instance for testing."""
        return DownloadManager(data_access=data_access)
    
    def test_initialization(self, download_manager):
        """Test that DownloadManager initializes correctly."""
        assert download_manager.data_access.is_initialized()
        assert download_manager.data_access is not None
    
    def test_add_download(self, download_manager):
        """Test adding a download."""
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        
        download_manager.add_download('test123', download_info)
        
        # Verify download was created
        download = download_manager.get_download('test123')
        assert download is not None
        assert download['video_id'] == 'test123'
        assert download['status'] == 'downloading'
        assert download['paused'] is False
        assert download['progress'] == 0.0
        
        # Verify event was logged
        events = download_manager.data_access.get_events('test123', 'download_started')
        assert len(events) == 1
    
    def test_update_download_status(self, download_manager):
        """Test updating download status."""
        # Add a download first
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test123', download_info)
        
        # Update status
        download_manager.update_download_status('test123', 'processing', progress=50.0)
        
        # Verify update
        download = download_manager.get_download('test123')
        assert download['status'] == 'processing'
        assert download['progress'] == 50.0
        
        # Verify event was logged
        events = download_manager.data_access.get_events('test123', 'status_change')
        assert len(events) == 1
        assert events[0]['event_data']['new_status'] == 'processing'
    
    def test_pause_and_resume_download(self, download_manager):
        """Test pausing and resuming downloads."""
        # Add a download first
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test123', download_info)
        
        # Pause download
        success = download_manager.pause_download('test123')
        assert success is True
        
        download = download_manager.get_download('test123')
        assert download['status'] == 'paused'
        assert download['paused'] is True
        
        # Resume download
        success = download_manager.resume_download('test123')
        assert success is True
        
        download = download_manager.get_download('test123')
        assert download['status'] == 'downloading'
        assert download['paused'] is False
        
        # Verify events were logged
        pause_events = download_manager.data_access.get_events('test123', 'download_paused')
        resume_events = download_manager.data_access.get_events('test123', 'download_resumed')
        assert len(pause_events) == 1
        assert len(resume_events) == 1
    
    def test_remove_download(self, download_manager):
        """Test removing a download (moving to history)."""
        # Add a download first
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test123', download_info)
        
        # Verify download exists
        assert download_manager.get_download('test123') is not None
        
        # Remove download
        download_manager.remove_download('test123')
        
        # Verify download is gone from active downloads
        assert download_manager.get_download('test123') is None
        
        # Verify download is in history
        history = download_manager.get_download_history('test123')
        assert len(history) == 1
        assert history[0]['video_id'] == 'test123'
        assert history[0]['final_status'] == 'downloading'
        
        # Verify completion event was logged
        events = download_manager.data_access.get_events('test123', 'download_completed')
        assert len(events) == 1
    
    def test_list_downloads(self, download_manager):
        """Test listing downloads."""
        # Add multiple downloads
        download_info = {
            'url': 'https://youtube.com/watch?v=test1',
            'title': 'Test Video 1',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test1', download_info)
        
        download_info2 = {
            'url': 'https://youtube.com/watch?v=test2',
            'title': 'Test Video 2',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test2', download_info2)
        
        # List all downloads
        all_downloads = download_manager.list_downloads()
        assert len(all_downloads) == 2
        
        # List by status
        downloading = download_manager.list_downloads('downloading')
        assert len(downloading) == 2
    
    def test_get_download_stats(self, download_manager):
        """Test getting download statistics."""
        # Add a download
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test123', download_info)
        
        # Get stats
        stats = download_manager.get_download_stats()
        assert stats['total_downloads'] == 1
        assert 'status_counts' in stats
        assert stats['status_counts']['downloading'] == 1
    
    def test_get_download_history(self, download_manager):
        """Test getting download history."""
        # Add and remove a download to create history
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test123', download_info)
        download_manager.remove_download('test123')
        
        # Get history
        history = download_manager.get_download_history()
        assert len(history) == 1
        assert history[0]['video_id'] == 'test123'
    
    def test_get_failed_downloads(self, download_manager):
        """Test getting failed downloads."""
        # Add a download and mark it as failed
        download_info = {
            'url': 'https://youtube.com/watch?v=test123',
            'title': 'Test Video',
            'output_path': '/tmp/downloads',
            'quality': 'best'
        }
        download_manager.add_download('test123', download_info)
        download_manager.update_download_status('test123', 'error', error='Test error')
        
        # Get failed downloads
        failed = download_manager.get_failed_downloads()
        assert len(failed) == 1
        assert failed[0]['video_id'] == 'test123'
        assert failed[0]['status'] == 'error'


class TestUtilityFunctions:
    """Test utility functions used by the downloader."""
    
    def test_video_id_extraction(self):
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

    def test_file_existence_checking(self):
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

    def test_download_manager_concurrent_access(self):
        """Test that the download manager can handle concurrent access."""
        import threading
        import time
        from dtube.downloader import DownloadManager
        from dtube.data_access import DownloadDataAccess

        # Create temporary database for testing
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_concurrent")
        
        try:
            data_access = DownloadDataAccess(db_path=db_path)
            data_access.ensure_database_ready()
            download_manager = DownloadManager(data_access=data_access)
            
            # Test concurrent access to download manager
            results = []
            errors = []
            
            def worker(thread_id):
                try:
                    # Create download
                    video_id = f"concurrent_test_{thread_id}"
                    download_info = {
                        'url': f'https://youtube.com/watch?v={video_id}',
                        'title': f'Test Video {thread_id}',
                        'output_path': 'downloads',
                        'quality': 'best'
                    }
                    
                    download_manager.add_download(video_id, download_info)
                    results.append((thread_id, "created"))
                    
                    # Small delay to increase concurrency
                    time.sleep(0.01)
                    
                    # Update download
                    download_manager.update_download_status(video_id, 'completed')
                    results.append((thread_id, "updated"))
                    
                    # Clean up
                    download_manager.remove_download(video_id)
                    results.append((thread_id, "removed"))
                    
                except Exception as e:
                    errors.append((thread_id, str(e)))
            
            # Start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify no errors occurred
            assert len(errors) == 0, f"Concurrent access errors: {errors}"
            
            # Verify all operations completed (5 threads × 3 operations each)
            assert len(results) == 15
            
            # Verify no downloads remain
            for i in range(5):
                video_id = f"concurrent_test_{i}"
                assert download_manager.get_download(video_id) is None
                
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)