"""
Comprehensive test suite for the data access layer.
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime, timedelta
from dtube.data_access import DownloadDataAccess


class TestDownloadDataAccess:
    """Test suite for DownloadDataAccess class."""
    
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
        """Create a fresh DownloadDataAccess instance for each test."""
        return DownloadDataAccess(db_path=temp_db_path)
    
    @pytest.fixture
    def sample_download_data(self):
        """Sample download data for testing."""
        return {
            "video_id": "test_video_123",
            "url": "https://youtube.com/watch?v=test_video_123",
            "title": "Test Video Title",
            "status": "downloading",
            "paused": False,
            "progress": 0.0,
            "start_time": datetime.now(),
            "output_path": "/tmp/downloads",
            "quality": "best",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    def test_initialization(self, data_access):
        """Test database initialization."""
        assert not data_access.is_initialized()
        
        data_access.ensure_database_ready()
        assert data_access.is_initialized()
        
        # Test double initialization (should not fail)
        data_access.ensure_database_ready()
        assert data_access.is_initialized()
    
    def test_create_download(self, data_access, sample_download_data):
        """Test creating a download record."""
        data_access.ensure_database_ready()
        
        # Create download
        result_id = data_access.create_download(sample_download_data)
        assert result_id is not None
        
        # Verify it was created
        created_download = data_access.get_download(sample_download_data["video_id"])
        assert created_download is not None
        assert created_download["video_id"] == sample_download_data["video_id"]
        assert created_download["title"] == sample_download_data["title"]
    
    def test_get_download(self, data_access, sample_download_data):
        """Test retrieving a download record."""
        data_access.ensure_database_ready()
        
        # Create and retrieve
        data_access.create_download(sample_download_data)
        download = data_access.get_download(sample_download_data["video_id"])
        
        assert download is not None
        assert download["video_id"] == sample_download_data["video_id"]
        
        # Test non-existent download
        non_existent = data_access.get_download("non_existent_id")
        assert non_existent is None
    
    def test_update_download(self, data_access, sample_download_data):
        """Test updating a download record."""
        data_access.ensure_database_ready()
        
        # Create download
        data_access.create_download(sample_download_data)
        
        # Update status
        update_data = {"status": "completed", "progress": 100.0}
        success = data_access.update_download(sample_download_data["video_id"], update_data)
        assert success is True
        
        # Verify update
        updated_download = data_access.get_download(sample_download_data["video_id"])
        assert updated_download["status"] == "completed"
        assert updated_download["progress"] == 100.0
        
        # Test update of non-existent download
        success = data_access.update_download("non_existent_id", update_data)
        assert success is False
    
    def test_delete_download(self, data_access, sample_download_data):
        """Test deleting a download record."""
        data_access.ensure_database_ready()
        
        # Create download
        data_access.create_download(sample_download_data)
        
        # Verify it exists
        assert data_access.get_download(sample_download_data["video_id"]) is not None
        
        # Delete it
        success = data_access.delete_download(sample_download_data["video_id"])
        assert success is True
        
        # Verify it's gone
        assert data_access.get_download(sample_download_data["video_id"]) is None
        
        # Test delete of non-existent download
        success = data_access.delete_download("non_existent_id")
        assert success is False
    
    def test_list_downloads(self, data_access, sample_download_data):
        """Test listing downloads with filters."""
        data_access.ensure_database_ready()
        
        # Create multiple downloads
        download1 = {**sample_download_data, "video_id": "video1", "status": "downloading"}
        download2 = {**sample_download_data, "video_id": "video2", "status": "completed"}
        download3 = {**sample_download_data, "video_id": "video3", "status": "error"}
        
        data_access.create_download(download1)
        data_access.create_download(download2)
        data_access.create_download(download3)
        
        # List all downloads
        all_downloads = data_access.list_downloads()
        assert len(all_downloads) == 3
        
        # List with status filter
        downloading = data_access.list_downloads({"status": "downloading"})
        assert len(downloading) == 1
        assert downloading[0]["video_id"] == "video1"
        
        # List with limit
        limited = data_access.list_downloads(limit=2)
        assert len(limited) == 2
    
    def test_add_to_history(self, data_access, sample_download_data):
        """Test adding downloads to history."""
        data_access.ensure_database_ready()
        
        # Add to history
        history_data = {**sample_download_data, "final_status": "completed", "end_time": datetime.now()}
        result_id = data_access.add_to_history(history_data)
        assert result_id is not None
        
        # Verify in history
        history = data_access.get_download_history(sample_download_data["video_id"])
        assert len(history) == 1
        assert history[0]["video_id"] == sample_download_data["video_id"]
        assert history[0]["final_status"] == "completed"
    
    def test_get_download_history(self, data_access, sample_download_data):
        """Test retrieving download history."""
        data_access.ensure_database_ready()
        
        # Add multiple history entries
        history1 = {**sample_download_data, "video_id": "video1", "final_status": "completed"}
        history2 = {**sample_download_data, "video_id": "video2", "final_status": "error"}
        
        data_access.add_to_history(history1)
        data_access.add_to_history(history2)
        
        # Get all history
        all_history = data_access.get_download_history()
        assert len(all_history) == 2
        
        # Get history for specific video
        video1_history = data_access.get_download_history("video1")
        assert len(video1_history) == 1
        assert video1_history[0]["video_id"] == "video1"
    
    def test_log_event(self, data_access, sample_download_data):
        """Test event logging."""
        data_access.ensure_database_ready()
        
        # Log an event
        event_data = {"status": "started", "progress": 0}
        result_id = data_access.log_event(sample_download_data["video_id"], "download_started", event_data)
        assert result_id is not None
        
        # Retrieve events
        events = data_access.get_events(sample_download_data["video_id"])
        assert len(events) == 1
        assert events[0]["event_type"] == "download_started"
        assert events[0]["event_data"]["status"] == "started"
    
    def test_get_events(self, data_access, sample_download_data):
        """Test retrieving events with filters."""
        data_access.ensure_database_ready()
        
        # Log multiple events
        data_access.log_event("video1", "status_change", {"old": "downloading", "new": "completed"})
        data_access.log_event("video1", "progress_update", {"progress": 50})
        data_access.log_event("video2", "status_change", {"old": "downloading", "new": "error"})
        
        # Get all events
        all_events = data_access.get_events()
        assert len(all_events) == 3
        
        # Get events for specific video
        video1_events = data_access.get_events("video1")
        assert len(video1_events) == 2
        
        # Get events by type
        status_events = data_access.get_events(event_type="status_change")
        assert len(status_events) == 2
        
        # Get events by date range
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        recent_events = data_access.get_events(date_range=(yesterday, tomorrow))
        assert len(recent_events) == 3
    
    def test_queue_operations(self, data_access):
        """Test comprehensive queue operations."""
        data_access.ensure_database_ready()
        
        # Test adding to queue
        queue_data = {
            'video_id': 'test_queue_123',
            'url': 'https://youtube.com/watch?v=test_queue_123',
            'title': 'Test Queue Video',
            'priority': 8,
            'output_path': '/tmp/test',
            'quality': '720p'
        }
        
        result_id = data_access.add_to_queue(queue_data)
        assert result_id is not None
        
        # Test getting queued downloads
        queued = data_access.get_queued_downloads(status='queued')
        assert len(queued) == 1
        assert queued[0]['video_id'] == 'test_queue_123'
        assert queued[0]['priority'] == 8
        
        # Test priority promotion
        assert data_access.promote_queue_item('test_queue_123', 10)
        updated = data_access.get_queued_downloads(status='queued')[0]
        assert updated['priority'] == 10
        
        # Test priority demotion
        assert data_access.demote_queue_item('test_queue_123', 6)
        updated = data_access.get_queued_downloads(status='queued')[0]
        assert updated['priority'] == 6
        
        # Test moving to front
        assert data_access.move_to_front_of_queue('test_queue_123')
        updated = data_access.get_queued_downloads(status='queued')[0]
        assert updated['priority'] > 6  # Should be higher than previous priority
        
        # Test updating queue item
        assert data_access.update_queue_item('test_queue_123', {'user_notes': 'Test note'})
        updated = data_access.get_queued_downloads(status='queued')[0]
        assert updated['user_notes'] == 'Test note'
        
        # Test removing from queue
        assert data_access.remove_from_queue('test_queue_123')
        queued = data_access.get_queued_downloads(status='queued')
        assert len(queued) == 0
    
    def test_queue_priority_management(self, data_access):
        """Test queue priority management functionality."""
        data_access.ensure_database_ready()
        
        # Add multiple items with different priorities
        items = [
            {'video_id': 'low_priority', 'priority': 3, 'url': 'https://test1.com'},
            {'video_id': 'high_priority', 'priority': 8, 'url': 'https://test2.com'},
            {'video_id': 'medium_priority', 'priority': 5, 'url': 'https://test3.com'}
        ]
        
        for item in items:
            data_access.add_to_queue(item)
        
        # Test priority-based ordering
        queued = data_access.get_queued_downloads(status='queued')
        assert len(queued) == 3
        
        # Should be ordered by priority (highest first)
        assert queued[0]['priority'] == 8
        assert queued[1]['priority'] == 5
        assert queued[2]['priority'] == 3
        
        # Test promotion validation
        assert not data_access.promote_queue_item('high_priority', 8)  # Same priority
        assert not data_access.promote_queue_item('high_priority', 7)  # Lower priority
        
        # Test demotion validation
        assert not data_access.demote_queue_item('low_priority', 3)  # Same priority
        assert not data_access.demote_queue_item('low_priority', 4)  # Higher priority
    
    def test_queue_status_management(self, data_access):
        """Test queue status management functionality."""
        data_access.ensure_database_ready()
        
        # Add item to queue
        queue_data = {
            'video_id': 'status_test_123',
            'url': 'https://youtube.com/watch?v=status_test_123',
            'title': 'Status Test Video'
        }
        
        data_access.add_to_queue(queue_data)
        
        # Test status updates
        assert data_access.update_queue_status('status_test_123', 'processing')
        assert data_access.update_queue_status('status_test_123', 'completed')
        
        # Test filtering by status
        queued = data_access.get_queued_downloads(status='queued')
        assert len(queued) == 0
        
        completed = data_access.get_queued_downloads(status='completed')
        assert len(completed) == 1
        assert completed[0]['video_id'] == 'status_test_123'
    
    def test_queue_retry_functionality(self, data_access):
        """Test queue retry functionality."""
        data_access.ensure_database_ready()
        
        # Add item to queue
        queue_data = {
            'video_id': 'retry_test_123',
            'url': 'https://youtube.com/watch?v=retry_test_123',
            'title': 'Retry Test Video',
            'max_retries': 2
        }
        
        data_access.add_to_queue(queue_data)
        
        # Test retry functionality
        assert data_access.retry_failed_queue_item('retry_test_123')
        
        # Verify retry count increased
        item = data_access.get_queued_downloads(status='queued')[0]
        assert item['retry_count'] == 1
        
        # Test max retries limit
        assert data_access.retry_failed_queue_item('retry_test_123')
        assert not data_access.retry_failed_queue_item('retry_test_123')  # Should fail
    
    def test_queue_statistics(self, data_access):
        """Test queue statistics functionality."""
        data_access.ensure_database_ready()
        
        # Add items with different statuses and priorities
        items = [
            {'video_id': 'stat1', 'priority': 8, 'url': 'https://test1.com'},
            {'video_id': 'stat2', 'priority': 5, 'url': 'https://test2.com'},
            {'video_id': 'stat3', 'priority': 3, 'url': 'https://test3.com'}
        ]
        
        for item in items:
            data_access.add_to_queue(item)
        
        # Update some statuses
        data_access.update_queue_status('stat1', 'processing')
        data_access.update_queue_status('stat2', 'completed')
        
        # Get statistics
        stats = data_access.get_queue_stats()
        
        assert stats['total_items'] == 3
        assert stats['queued_items'] == 1
        assert stats['processing_items'] == 1
        assert stats['completed_items'] == 1
        assert stats['highest_priority'] == 8
        assert stats['lowest_priority'] == 3
        assert 5.0 <= stats['average_priority'] <= 6.0
    
    def test_scheduled_downloads(self, data_access):
        """Test scheduled downloads functionality."""
        data_access.ensure_database_ready()
        
        from datetime import datetime, timedelta
        
        now = datetime.now()
        future = now + timedelta(hours=1)
        past = now - timedelta(hours=1)
        
        # Add items with different scheduled times
        items = [
            {'video_id': 'past_scheduled', 'scheduled_time': past, 'url': 'https://test1.com'},
            {'video_id': 'now_scheduled', 'scheduled_time': now, 'url': 'https://test2.com'},
            {'video_id': 'future_scheduled', 'scheduled_time': future, 'url': 'https://test3.com'}
        ]
        
        for item in items:
            data_access.add_to_queue(item)
        
        # Test time range filtering
        past_items = data_access.get_scheduled_downloads(end_time=now)
        assert len(past_items) == 2  # past and now
        
        future_items = data_access.get_scheduled_downloads(start_time=now)
        assert len(future_items) == 2  # now and future
    
    def test_queue_clear_operations(self, data_access):
        """Test queue clear operations."""
        data_access.ensure_database_ready()
        
        # Add items to queue first (they will all have 'queued' status initially)
        items = [
            {'video_id': 'clear1', 'url': 'https://test1.com'},
            {'video_id': 'clear2', 'url': 'https://test2.com'},
            {'video_id': 'clear3', 'url': 'https://test3.com'}
        ]
        
        for item in items:
            data_access.add_to_queue(item)
        
        # Now update some statuses to test clearing by status
        data_access.update_queue_status('clear2', 'processing')
        data_access.update_queue_status('clear3', 'completed')
        
        # Test clearing by status
        cleared = data_access.clear_queue(status='completed')
        assert cleared == 1
        
        # Test clearing all
        cleared = data_access.clear_queue()
        assert cleared == 2  # remaining items
        
        # Verify queue is empty
        all_items = data_access.get_queued_downloads()
        assert len(all_items) == 0
    
    def test_queue_bulk_operations(self, data_access):
        """Test bulk queue operations."""
        data_access.ensure_database_ready()
        
        # Add multiple items
        items = []
        for i in range(5):
            items.append({
                'video_id': f'bulk_test_{i}',
                'url': f'https://test{i}.com',
                'priority': 5 + i
            })
        
        for item in items:
            data_access.add_to_queue(item)
        
        # Test getting with limit
        limited = data_access.get_queued_downloads(limit=3)
        assert len(limited) == 3
        
        # Test priority filtering - should get items with priority >= 7
        high_priority = data_access.get_queued_downloads(priority=7)
        # Items with priority 7, 8, 9 should be returned
        assert len(high_priority) == 3  # priority 7, 8, and 9
        
        # Test status filtering
        queued = data_access.get_queued_downloads(status='queued')
        assert len(queued) == 5
    
    def test_queue_error_handling(self, data_access):
        """Test queue error handling."""
        data_access.ensure_database_ready()
        
        # Test adding item without required fields
        with pytest.raises(ValueError):
            data_access.add_to_queue({})
        
        # Test operations on non-existent items
        assert not data_access.update_queue_status('non_existent', 'processing')
        assert not data_access.remove_from_queue('non_existent')
        assert not data_access.promote_queue_item('non_existent', 10)
        assert not data_access.demote_queue_item('non_existent', 1)
        assert not data_access.move_to_front_of_queue('non_existent')
        assert not data_access.retry_failed_queue_item('non_existent')
        
        # Test invalid priority changes
        # Add a test item first
        data_access.add_to_queue({
            'video_id': 'error_test',
            'url': 'https://test.com'
        })
        
        # Try to promote to same or lower priority
        assert not data_access.promote_queue_item('error_test', 5)
        assert not data_access.demote_queue_item('error_test', 5)
    
    def test_get_download_stats(self, data_access, sample_download_data):
        """Test download statistics."""
        data_access.ensure_database_ready()
        
        # Create downloads with different statuses
        download1 = {**sample_download_data, "video_id": "video1", "status": "downloading"}
        download2 = {**sample_download_data, "video_id": "video2", "status": "completed"}
        download3 = {**sample_download_data, "video_id": "video3", "status": "error"}
        
        data_access.create_download(download1)
        data_access.create_download(download2)
        data_access.create_download(download3)
        
        # Get stats
        stats = data_access.get_download_stats()
        assert stats["total_downloads"] == 3
        assert "status_counts" in stats
        assert stats["status_counts"]["downloading"] == 1
        assert stats["status_counts"]["completed"] == 1
        assert stats["status_counts"]["error"] == 1
    
    def test_get_failed_downloads(self, data_access, sample_download_data):
        """Test retrieving failed downloads."""
        data_access.ensure_database_ready()
        
        # Create failed downloads
        failed1 = {**sample_download_data, "video_id": "video1", "status": "error"}
        failed2 = {**sample_download_data, "video_id": "video2", "status": "error"}
        success = {**sample_download_data, "video_id": "video3", "status": "completed"}
        
        data_access.create_download(failed1)
        data_access.create_download(failed2)
        data_access.create_download(success)
        
        # Get failed downloads
        failed = data_access.get_failed_downloads()
        assert len(failed) == 2
        
        # Test with limit
        limited_failed = data_access.get_failed_downloads(limit=1)
        assert len(limited_failed) == 1
    
    def test_cleanup_old_records(self, data_access, sample_download_data):
        """Test cleanup of old records."""
        data_access.ensure_database_ready()
        
        # Add old history and events
        old_date = datetime.now() - timedelta(days=400)
        old_history = {**sample_download_data, "completed_at": old_date}
        
        data_access.add_to_history(old_history)
        
        # Add old event directly to avoid timestamp issues
        old_event_data = {
            "video_id": sample_download_data["video_id"],
            "event_type": "old_event",
            "event_data": {},
            "timestamp": old_date,
            "user_agent": "dtube_downloader"
        }
        data_access.collections['events'].insert_one(old_event_data)
        
        # Add recent records
        recent_history = {**sample_download_data, "video_id": "recent", "completed_at": datetime.now()}
        data_access.add_to_history(recent_history)
        
        # Cleanup old records
        deleted_count = data_access.cleanup_old_records(days_to_keep=365)
        assert deleted_count == 2  # old history + old event
        
        # Verify old records are gone, recent ones remain
        all_history = data_access.get_download_history()
        assert len(all_history) == 1
        assert all_history[0]["video_id"] == "recent"
    
    def test_validate_database_integrity(self, data_access, sample_download_data):
        """Test database integrity validation."""
        data_access.ensure_database_ready()
        
        # Create valid download
        data_access.create_download(sample_download_data)
        
        # Add orphaned event (no corresponding download)
        data_access.log_event("orphaned_video", "orphaned_event", {})
        
        # Validate integrity
        try:
            integrity = data_access.validate_database_integrity()
            print(f"Integrity result: {integrity}")
            assert not integrity["valid"]
            assert len(integrity["issues"]) > 0
            assert "orphaned events" in integrity["issues"][0]
            assert integrity["total_downloads"] == 1
            assert integrity["total_history"] == 0
            assert integrity["total_events"] == 1
        except Exception as e:
            print(f"Exception during validation: {e}")
            raise
    

    
    def test_lazy_initialization(self, data_access, sample_download_data):
        """Test lazy initialization behavior."""
        # Should not be initialized initially
        assert not data_access.is_initialized()
        
        # Operations should trigger initialization
        data_access.create_download(sample_download_data)
        assert data_access.is_initialized()
        
        # Verify data was created
        download = data_access.get_download(sample_download_data["video_id"])
        assert download is not None
    
    def test_concurrent_access(self, data_access, sample_download_data):
        """Test concurrent access to the data access layer."""
        import threading
        import time
        
        data_access.ensure_database_ready()
        
        # Create multiple threads that access the database
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                # Create download
                download_data = {**sample_download_data, "video_id": f"video_{thread_id}"}
                result_id = data_access.create_download(download_data)
                results.append((thread_id, result_id))
                
                # Small delay to increase concurrency
                time.sleep(0.01)
                
                # Update download
                success = data_access.update_download(f"video_{thread_id}", {"status": "completed"})
                if success:
                    results.append((thread_id, "updated"))
                    
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
        
        # Verify all operations completed
        assert len(results) == 10  # 5 creates + 5 updates
        
        # Verify data integrity
        for i in range(5):
            download = data_access.get_download(f"video_{i}")
            assert download is not None
            assert download["status"] == "completed"
    
    def test_lock_usage_for_database_operations(self, data_access, sample_download_data):
        """Test that locks are properly used for database modification operations."""
        import threading
        import time
        
        data_access.ensure_database_ready()
        
        # Test that read operations don't block each other
        read_results = []
        read_errors = []
        
        def read_worker(thread_id):
            try:
                # Perform multiple read operations
                for i in range(10):
                    downloads = data_access.list_downloads()
                    events = data_access.get_events()
                    history = data_access.get_download_history()
                    read_results.append((thread_id, i, len(downloads), len(events), len(history)))
                    time.sleep(0.001)  # Very small delay
            except Exception as e:
                read_errors.append((thread_id, str(e)))
        
        # Start multiple read threads
        read_threads = []
        for i in range(3):
            thread = threading.Thread(target=read_worker, args=(i,))
            read_threads.append(thread)
            thread.start()
        
        # Wait for read threads to complete
        for thread in read_threads:
            thread.join()
        
        # Verify no read errors occurred
        assert len(read_errors) == 0, f"Read operation errors: {read_errors}"
        
        # Verify all read operations completed
        assert len(read_results) == 30  # 3 threads × 10 iterations
        
        # Test that write operations are properly serialized
        write_results = []
        write_errors = []
        
        def write_worker(thread_id):
            try:
                # Create download
                download_data = {**sample_download_data, "video_id": f"write_test_{thread_id}"}
                result_id = data_access.create_download(download_data)
                write_results.append((thread_id, "created", result_id))
                
                # Update download
                success = data_access.update_download(f"write_test_{thread_id}", {"status": "processing"})
                if success:
                    write_results.append((thread_id, "updated"))
                
                # Log event
                event_id = data_access.log_event(f"write_test_{thread_id}", "test_event", {"thread": thread_id})
                write_results.append((thread_id, "event_logged", event_id))
                
            except Exception as e:
                write_errors.append((thread_id, str(e)))
        
        # Start multiple write threads
        write_threads = []
        for i in range(5):
            thread = threading.Thread(target=write_worker, args=(i,))
            write_threads.append(thread)
            thread.start()
        
        # Wait for write threads to complete
        for thread in write_threads:
            thread.join()
        
        # Verify no write errors occurred
        assert len(write_errors) == 0, f"Write operation errors: {write_errors}"
        
        # Verify all write operations completed (5 threads × 3 operations each)
        assert len(write_results) == 15
        
        # Verify data integrity - all downloads should exist with correct status
        for i in range(5):
            download = data_access.get_download(f"write_test_{i}")
            assert download is not None
            assert download["status"] == "processing"
            
            # Check that events were logged
            events = data_access.get_events(f"write_test_{i}")
            assert len(events) == 1
            assert events[0]["event_type"] == "test_event"
            assert events[0]["event_data"]["thread"] == i
