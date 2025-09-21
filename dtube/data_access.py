"""
Data access layer for managing Mongita database operations.
"""

import os
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from mongita import MongitaClientDisk as Mongita


class DownloadDataAccess:
    """Data access layer for managing Mongita database operations."""
    
    def __init__(self, db_path: str = "./data/dtube_downloads"):
        self.db_path = db_path
        self.db = None
        self.collections = {}
        self._initialized = False
        self._lock = threading.Lock()
        
    def ensure_database_ready(self):
        """Ensure database is ready for operations, recreating if necessary."""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:  # Double-check pattern
                return
                
            try:
                # Check if database exists and is valid
                if self._is_database_valid():
                    # Database is valid, connect and set up collections reference
                    self._connect_database()
                    self._initialize_collections()
                    self._initialized = True
                    logging.info("✅ Existing database loaded successfully")
                else:
                    # Database is corrupted or missing, recreate from scratch
                    logging.warning("⚠️ Database appears corrupted or missing, recreating...")
                    self._recreate_database()
                    self._initialized = True
                    logging.info("✅ Database recreated successfully")
            except Exception as e:
                logging.error(f"❌ Failed to initialize database: {e}")
                # Attempt to recreate database as last resort
                try:
                    logging.info("🔄 Attempting database recreation as fallback...")
                    self._recreate_database()
                    self._initialized = True
                    logging.info("✅ Database recreated successfully after fallback")
                except Exception as recreate_error:
                    logging.error(f"❌ Failed to recreate database: {recreate_error}")
                    raise
    
    def _is_database_valid(self) -> bool:
        """Check if existing database is valid and contains required collections."""
        try:
            if not os.path.exists(self.db_path):
                return False
                
            # Try to connect and verify collections exist
            temp_client = Mongita(self.db_path)
            temp_db = temp_client["dtube_downloads"]
            required_collections = ['downloads', 'download_history', 'download_events', 'download_queue']
            
            for collection_name in required_collections:
                try:
                    # Use direct dictionary-style access like the working code does
                    collection = temp_db[collection_name]
                    # Try a simple operation to verify collection is functional
                    collection.find_one()
                except Exception:
                    return False
                    
            return True
        except Exception:
            return False
    
    def _recreate_database(self):
        """Recreate database from scratch with all required collections and indexes."""
        try:
            # Remove existing database directory if it exists
            if os.path.exists(self.db_path):
                import shutil
                shutil.rmtree(self.db_path)
                logging.debug("🗑️ Removed corrupted database directory")
            
            # Create fresh database
            self._connect_database()
            self._initialize_collections()
            self._create_indexes()
            logging.info("🆕 Fresh database created with all collections and indexes")
        except Exception as e:
            logging.error(f"❌ Failed to recreate database: {e}")
            raise
    
    def _connect_database(self):
        """Establish connection to Mongita database."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.client = Mongita(self.db_path)
        self.db = self.client["dtube_downloads"]  # Access the specific database
        logging.debug(f"Connected to database at {self.db_path}")
        logging.debug(f"Client type: {type(self.client)}")
        logging.debug(f"Database type: {type(self.db)}")
        logging.debug(f"Database dir: {[x for x in dir(self.db) if not x.startswith('_')]}")
        
    def _initialize_collections(self):
        """Initialize all required collections."""
        # Access collections from the database
        self.collections = {
            'downloads': self.db["downloads"],
            'history': self.db["download_history"],
            'events': self.db["download_events"],
            'queue': self.db["download_queue"]
        }
        
        # Debug: verify collection types
        for name, coll in self.collections.items():
            logging.debug(f"Collection {name}: {type(coll)}")
            if hasattr(coll, 'create_index'):
                logging.debug(f"  - Has create_index method: {callable(coll.create_index)}")
            else:
                logging.debug(f"  - No create_index method")
                
        # Verify we have the right types
        for name, coll in self.collections.items():
            if not hasattr(coll, 'create_index'):
                raise TypeError(f"Collection {name} is not a valid collection object: {type(coll)}")
    
    def _create_indexes(self):
        """Create database indexes for optimal query performance."""
        try:
            # downloads collection indexes
            logging.debug(f"Creating index on downloads.video_id, collection type: {type(self.collections['downloads'])}")
            self.collections['downloads'].create_index("video_id")
            self.collections['downloads'].create_index("status")
            self.collections['downloads'].create_index("created_at")
            
            # history collection indexes
            self.collections['history'].create_index("video_id")
            self.collections['history'].create_index("final_status")
            self.collections['history'].create_index("completed_at")
            
            # events collection indexes
            self.collections['events'].create_index("video_id")
            self.collections['events'].create_index("event_type")
            self.collections['events'].create_index("timestamp")
            
            # queue collection indexes
            self.collections['queue'].create_index("status")
            self.collections['queue'].create_index("priority")
            self.collections['queue'].create_index("scheduled_time")
            
            logging.debug("✅ Database indexes created successfully")
        except Exception as e:
            logging.error(f"❌ Error creating indexes: {e}")
            logging.error(f"❌ Collection types: {[(name, type(coll)) for name, coll in self.collections.items()]}")
            raise
    
    def is_initialized(self) -> bool:
        """Check if the data access layer is properly initialized."""
        return self._initialized
    
    def ensure_initialized(self):
        """Ensure database is initialized before operations."""
        if not self._initialized:
            self.ensure_database_ready()
    
    def initialize(self):
        """Initialize database connection and collections (legacy method)."""
        self.ensure_database_ready()
    
    # Download CRUD operations
    def create_download(self, download_data: Dict[str, Any]) -> str:
        """Create a new download record."""
        self.ensure_initialized()
        with self._lock:
            try:
                result = self.collections['downloads'].insert_one(download_data)
                logging.debug(f"✅ Created download record for video {download_data.get('video_id')}")
                return str(result.inserted_id)
            except Exception as e:
                logging.error(f"❌ Failed to create download record: {e}")
                raise
    
    def get_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve download by video ID."""
        self.ensure_initialized()
        try:
            return self.collections['downloads'].find_one({"video_id": video_id})
        except Exception as e:
            logging.error(f"❌ Failed to retrieve download {video_id}: {e}")
            return None
        
    def update_download(self, video_id: str, update_data: Dict[str, Any]) -> bool:
        """Update download record."""
        self.ensure_initialized()
        with self._lock:
            try:
                result = self.collections['downloads'].update_one(
                    {"video_id": video_id},
                    {"$set": update_data}
                )
                return result.modified_count > 0
            except Exception as e:
                logging.error(f"❌ Failed to update download {video_id}: {e}")
                return False
        
    def delete_download(self, video_id: str) -> bool:
        """Delete download record."""
        self.ensure_initialized()
        with self._lock:
            try:
                result = self.collections['downloads'].delete_one({"video_id": video_id})
                return result.deleted_count > 0
            except Exception as e:
                logging.error(f"❌ Failed to delete download {video_id}: {e}")
                return False
        
    def list_downloads(self, filters: Dict[str, Any] = None, 
                      sort_by: str = "created_at", limit: int = None) -> List[Dict[str, Any]]:
        """List downloads with optional filtering and sorting."""
        self.ensure_initialized()
        try:
            query = filters or {}
            cursor = self.collections['downloads'].find(query)
            
            # Apply sorting manually since Mongita may have different sort syntax
            results = list(cursor)
            if sort_by and results:
                try:
                    # Try to sort by the specified field
                    results.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
                except (TypeError, AttributeError):
                    # Fallback to no sorting if the field doesn't support comparison
                    logging.debug(f"Could not sort by {sort_by}, returning unsorted results")
            
            if limit:
                results = results[:limit]
            return results
        except Exception as e:
            logging.error(f"❌ Failed to list downloads: {e}")
            return []
    
    # History operations
    def add_to_history(self, download_data: Dict[str, Any]) -> str:
        """Move completed download to history."""
        self.ensure_initialized()
        with self._lock:
            try:
                result = self.collections['history'].insert_one(download_data)
                logging.debug(f"✅ Added download {download_data.get('video_id')} to history")
                return str(result.inserted_id)
            except Exception as e:
                logging.error(f"❌ Failed to add to history: {e}")
                raise
    
    def get_download_history(self, video_id: str = None, 
                           filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve download history."""
        self.ensure_initialized()
        try:
            query = filters or {}
            if video_id:
                query["video_id"] = video_id
            results = list(self.collections['history'].find(query))
            
            # Sort by completed_at manually
            if results:
                try:
                    results.sort(key=lambda x: x.get("completed_at", 0), reverse=True)
                except (TypeError, AttributeError):
                    logging.debug("Could not sort by completed_at, returning unsorted results")
            
            return results
        except Exception as e:
            logging.error(f"❌ Failed to retrieve download history: {e}")
            return []
    
    # Event logging operations
    def log_event(self, video_id: str, event_type: str, event_data: Dict[str, Any]) -> str:
        """Log a download event."""
        self.ensure_initialized()
        with self._lock:
            try:
                event_record = {
                    "video_id": video_id,
                    "event_type": event_type,
                    "event_data": event_data,
                    "timestamp": datetime.now(),
                    "user_agent": "dtube_downloader"
                }
                result = self.collections['events'].insert_one(event_record)
                return str(result.inserted_id)
            except Exception as e:
                logging.error(f"❌ Failed to log event: {e}")
                raise
        
    def get_events(self, video_id: str = None, 
                  event_type: str = None, 
                  date_range: Tuple[datetime, datetime] = None) -> List[Dict[str, Any]]:
        """Retrieve events with optional filtering."""
        self.ensure_initialized()
        try:
            query = {}
            if video_id:
                query["video_id"] = video_id
            if event_type:
                query["event_type"] = event_type
            if date_range:
                start_date, end_date = date_range
                query["timestamp"] = {"$gte": start_date, "$lte": end_date}
            
            results = list(self.collections['events'].find(query))
            
            # Sort by timestamp manually
            if results:
                try:
                    results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                except (TypeError, AttributeError):
                    logging.debug("Could not sort by timestamp, returning unsorted results")
            
            return results
        except Exception as e:
            logging.error(f"❌ Failed to retrieve events: {e}")
            return []
    
    # Queue operations
    def add_to_queue(self, queue_data: Dict[str, Any]) -> str:
        """Add download to queue."""
        self.ensure_initialized()
        with self._lock:
            try:
                # Ensure required fields are present
                if 'video_id' not in queue_data:
                    raise ValueError("video_id is required for queue items")
                
                # Set default values for queue items
                queue_item = {
                    'video_id': queue_data['video_id'],
                    'url': queue_data.get('url', ''),
                    'title': queue_data.get('title', ''),
                    'priority': queue_data.get('priority', 5),  # Default priority 5
                    'scheduled_time': queue_data.get('scheduled_time', datetime.now()),
                    'max_concurrent': queue_data.get('max_concurrent', 1),
                    'output_path': queue_data.get('output_path', './downloads'),
                    'quality': queue_data.get('quality', 'best'),
                    'status': 'queued',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'retry_count': 0,
                    'max_retries': queue_data.get('max_retries', 3),
                    'user_notes': queue_data.get('user_notes', ''),
                    'tags': queue_data.get('tags', [])
                }
                
                result = self.collections['queue'].insert_one(queue_item)
                logging.debug(f"✅ Added download {queue_data.get('video_id')} to queue with priority {queue_item['priority']}")
                return str(result.inserted_id)
            except Exception as e:
                logging.error(f"❌ Failed to add to queue: {e}")
                raise
        
    def get_next_queued_download(self) -> Optional[Dict[str, Any]]:
        """Get next download from queue."""
        self.ensure_initialized()
        try:
            # Get all queued downloads and sort manually
            queued_downloads = list(self.collections['queue'].find({"status": "queued"}))
            
            if not queued_downloads:
                return None
            
            # Sort by priority (descending) then by created_at (ascending)
            try:
                queued_downloads.sort(key=lambda x: (
                    x.get("priority", 5),  # Default priority 5
                    x.get("created_at", datetime.min)  # Default to earliest time
                ), reverse=True)
            except (TypeError, AttributeError):
                logging.debug("Could not sort queue, returning first available item")
            
            return queued_downloads[0] if queued_downloads else None
        except Exception as e:
            logging.error(f"❌ Failed to get next queued download: {e}")
            return None
    
    def get_queued_downloads(self, status: str = None, priority: int = None, 
                            limit: int = None) -> List[Dict[str, Any]]:
        """Get queued downloads with optional filtering."""
        self.ensure_initialized()
        try:
            query = {}
            if status:
                query["status"] = status
            if priority is not None:
                # Return items with priority >= specified value (more useful for queue management)
                query["priority"] = {"$gte": priority}
            
            results = list(self.collections['queue'].find(query))
            
            # Sort by priority (descending) then by created_at (ascending)
            if results:
                try:
                    results.sort(key=lambda x: (
                        x.get("priority", 5),
                        x.get("created_at", datetime.min)
                    ), reverse=True)
                except (TypeError, AttributeError):
                    logging.debug("Could not sort queue results")
            
            if limit:
                results = results[:limit]
            
            return results
        except Exception as e:
            logging.error(f"❌ Failed to get queued downloads: {e}")
            return []
    
    def update_queue_status(self, video_id: str, status: str) -> bool:
        """Update queue item status."""
        self.ensure_initialized()
        with self._lock:
            try:
                result = self.collections['queue'].update_one(
                    {"video_id": video_id},
                    {"$set": {"status": status, "updated_at": datetime.now()}}
                )
                return result.modified_count > 0
            except Exception as e:
                logging.error(f"❌ Failed to update queue status: {e}")
                return False
    
    def update_queue_item(self, video_id: str, update_data: Dict[str, Any]) -> bool:
        """Update queue item with multiple fields."""
        self.ensure_initialized()
        with self._lock:
            try:
                update_data['updated_at'] = datetime.now()
                result = self.collections['queue'].update_one(
                    {"video_id": video_id},
                    {"$set": update_data}
                )
                return result.modified_count > 0
            except Exception as e:
                logging.error(f"❌ Failed to update queue item {video_id}: {e}")
                return False
    
    def remove_from_queue(self, video_id: str) -> bool:
        """Remove item from queue."""
        self.ensure_initialized()
        with self._lock:
            try:
                result = self.collections['queue'].delete_one({"video_id": video_id})
                if result.deleted_count > 0:
                    logging.debug(f"✅ Removed {video_id} from queue")
                    return True
                return False
            except Exception as e:
                logging.error(f"❌ Failed to remove {video_id} from queue: {e}")
                return False
    
    def clear_queue(self, status: str = None) -> int:
        """Clear all items from queue with optional status filter."""
        self.ensure_initialized()
        with self._lock:
            try:
                query = {}
                if status:
                    query["status"] = status
                
                result = self.collections['queue'].delete_many(query)
                cleared_count = result.deleted_count
                logging.debug(f"✅ Cleared {cleared_count} items from queue")
                return cleared_count
            except Exception as e:
                logging.error(f"❌ Failed to clear queue: {e}")
                return 0
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        self.ensure_initialized()
        try:
            stats = {}
            
            # Count by status
            queue_items = list(self.collections['queue'].find({}))
            status_counts = {}
            priority_counts = {}
            
            for item in queue_items:
                status = item.get('status', 'unknown')
                priority = item.get('priority', 5)
                
                status_counts[status] = status_counts.get(status, 0) + 1
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            stats['status_counts'] = status_counts
            stats['priority_counts'] = priority_counts
            stats['total_items'] = len(queue_items)
            stats['queued_items'] = status_counts.get('queued', 0)
            stats['processing_items'] = status_counts.get('processing', 0)
            stats['completed_items'] = status_counts.get('completed', 0)
            stats['failed_items'] = status_counts.get('failed', 0)
            
            # Priority distribution
            if priority_counts:
                stats['highest_priority'] = max(priority_counts.keys())
                stats['lowest_priority'] = min(priority_counts.keys())
                stats['average_priority'] = sum(p * c for p, c in priority_counts.items()) / sum(priority_counts.values())
            
            return stats
        except Exception as e:
            logging.error(f"❌ Failed to get queue stats: {e}")
            return {}
    
    def promote_queue_item(self, video_id: str, new_priority: int) -> bool:
        """Promote a queue item to higher priority."""
        self.ensure_initialized()
        with self._lock:
            try:
                # Get current priority
                current_item = self.collections['queue'].find_one({"video_id": video_id})
                if not current_item:
                    logging.warning(f"⚠️ Queue item {video_id} not found for promotion")
                    return False
                
                current_priority = current_item.get('priority', 5)
                if new_priority <= current_priority:
                    logging.warning(f"⚠️ New priority {new_priority} must be higher than current {current_priority}")
                    return False
                
                result = self.collections['queue'].update_one(
                    {"video_id": video_id},
                    {"$set": {"priority": new_priority, "updated_at": datetime.now()}}
                )
                
                if result.modified_count > 0:
                    logging.debug(f"✅ Promoted {video_id} from priority {current_priority} to {new_priority}")
                    return True
                return False
            except Exception as e:
                logging.error(f"❌ Failed to promote queue item {video_id}: {e}")
                return False
    
    def demote_queue_item(self, video_id: str, new_priority: int) -> bool:
        """Demote a queue item to lower priority."""
        self.ensure_initialized()
        with self._lock:
            try:
                # Get current priority
                current_item = self.collections['queue'].find_one({"video_id": video_id})
                if not current_item:
                    logging.warning(f"⚠️ Queue item {video_id} not found for demotion")
                    return False
                
                current_priority = current_item.get('priority', 5)
                if new_priority >= current_priority:
                    logging.warning(f"⚠️ New priority {new_priority} must be lower than current {current_priority}")
                    return False
                
                result = self.collections['queue'].update_one(
                    {"video_id": video_id},
                    {"$set": {"priority": new_priority, "updated_at": datetime.now()}}
                )
                
                if result.modified_count > 0:
                    logging.debug(f"✅ Demoted {video_id} from priority {current_priority} to {new_priority}")
                    return True
                return False
            except Exception as e:
                logging.error(f"❌ Failed to demote queue item {video_id}: {e}")
                return False
    
    def move_to_front_of_queue(self, video_id: str) -> bool:
        """Move a queue item to the front by setting highest priority and earliest timestamp."""
        self.ensure_initialized()
        with self._lock:
            try:
                # Get current highest priority
                highest_priority_item = self.collections['queue'].find_one(
                    {"status": "queued"}, 
                    sort=[("priority", -1), ("created_at", 1)]
                )
                
                if not highest_priority_item:
                    logging.warning("⚠️ No queued items found")
                    return False
                
                highest_priority = highest_priority_item.get('priority', 5)
                new_priority = highest_priority + 1
                
                result = self.collections['queue'].update_one(
                    {"video_id": video_id},
                    {"$set": {
                        "priority": new_priority, 
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    }}
                )
                
                if result.modified_count > 0:
                    logging.debug(f"✅ Moved {video_id} to front of queue with priority {new_priority}")
                    return True
                return False
            except Exception as e:
                logging.error(f"❌ Failed to move {video_id} to front of queue: {e}")
                return False
    
    def get_scheduled_downloads(self, start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """Get downloads scheduled for a specific time range."""
        self.ensure_initialized()
        try:
            query = {}
            if start_time or end_time:
                query["scheduled_time"] = {}
                if start_time:
                    query["scheduled_time"]["$gte"] = start_time
                if end_time:
                    query["scheduled_time"]["$lte"] = end_time
            
            results = list(self.collections['queue'].find(query))
            
            # Sort by scheduled_time
            if results:
                try:
                    results.sort(key=lambda x: x.get("scheduled_time", datetime.min))
                except (TypeError, AttributeError):
                    logging.debug("Could not sort by scheduled_time")
            
            return results
        except Exception as e:
            logging.error(f"❌ Failed to get scheduled downloads: {e}")
            return []
    
    def retry_failed_queue_item(self, video_id: str) -> bool:
        """Retry a failed queue item by resetting its status and incrementing retry count."""
        self.ensure_initialized()
        with self._lock:
            try:
                current_item = self.collections['queue'].find_one({"video_id": video_id})
                if not current_item:
                    logging.warning(f"⚠️ Queue item {video_id} not found for retry")
                    return False
                
                current_retry_count = current_item.get('retry_count', 0)
                max_retries = current_item.get('max_retries', 3)
                
                if current_retry_count >= max_retries:
                    logging.warning(f"⚠️ {video_id} has exceeded max retries ({current_retry_count}/{max_retries})")
                    return False
                
                result = self.collections['queue'].update_one(
                    {"video_id": video_id},
                    {"$set": {
                        "status": "queued",
                        "retry_count": current_retry_count + 1,
                        "updated_at": datetime.now()
                    }}
                )
                
                if result.modified_count > 0:
                    logging.debug(f"✅ Retried {video_id} (attempt {current_retry_count + 1}/{max_retries})")
                    return True
                return False
            except Exception as e:
                logging.error(f"❌ Failed to retry queue item {video_id}: {e}")
                return False
    
    # Helper functions
    def get_download_stats(self) -> Dict[str, Any]:
        """Get aggregate download statistics."""
        self.ensure_initialized()
        try:
            stats = {}
            
            # Count by status - use manual counting since Mongita may not support aggregation
            downloads = list(self.collections['downloads'].find({}))
            status_counts = {}
            for download in downloads:
                status = download.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            stats['status_counts'] = status_counts
            
            # Total downloads
            stats['total_downloads'] = len(downloads)
            
            # Total history
            stats['total_history'] = self.collections['history'].count_documents({})
            
            # Total events
            stats['total_events'] = self.collections['events'].count_documents({})
            
            return stats
        except Exception as e:
            logging.error(f"❌ Failed to get download stats: {e}")
            return {}
        
    def get_failed_downloads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of failed downloads for analysis."""
        self.ensure_initialized()
        try:
            results = list(self.collections['downloads'].find({"status": "error"}))
            
            # Sort by updated_at manually
            if results:
                try:
                    results.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
                except (TypeError, AttributeError):
                    logging.debug("Could not sort by updated_at, returning unsorted results")
            
            # Apply limit manually
            if limit:
                results = results[:limit]
            
            return results
        except Exception as e:
            logging.error(f"❌ Failed to get failed downloads: {e}")
            return []
        
    def cleanup_old_records(self, days_to_keep: int = 365) -> int:
        """Clean up old history and event records."""
        self.ensure_initialized()
        with self._lock:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # Clean up old history records
                history_result = self.collections['history'].delete_many({
                    "completed_at": {"$lt": cutoff_date}
                })
                
                # Clean up old event records
                events_result = self.collections['events'].delete_many({
                    "timestamp": {"$lt": cutoff_date}
                })
                
                total_deleted = history_result.deleted_count + events_result.deleted_count
                logging.debug(f"✅ Cleaned up {total_deleted} old records")
                return total_deleted
            except Exception as e:
                logging.error(f"❌ Failed to cleanup old records: {e}")
                return 0
        
    def validate_database_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and report issues."""
        self.ensure_initialized()
        try:
            issues = []
            
            logging.debug("Starting database integrity validation...")
            
            # Check for orphaned events - use manual counting to avoid $nin issues
            logging.debug("Checking for orphaned events...")
            download_ids = set()
            for doc in self.collections['downloads'].find({}):
                download_ids.add(doc.get('video_id'))
            logging.debug(f"Found {len(download_ids)} download IDs")
            
            orphaned_count = 0
            for event in self.collections['events'].find({}):
                if event.get('video_id') not in download_ids:
                    orphaned_count += 1
            
            if orphaned_count > 0:
                issues.append(f"Found {orphaned_count} orphaned events")
            logging.debug(f"Found {orphaned_count} orphaned events")
            
            # Check for duplicate video IDs in downloads - use manual checking
            logging.debug("Checking for duplicate video IDs...")
            video_id_counts = {}
            for doc in self.collections['downloads'].find({}):
                video_id = doc.get('video_id')
                if video_id:
                    video_id_counts[video_id] = video_id_counts.get(video_id, 0) + 1
            
            duplicates = [vid for vid, count in video_id_counts.items() if count > 1]
            if duplicates:
                issues.append(f"Found {len(duplicates)} duplicate video IDs")
            logging.debug(f"Found {len(duplicates)} duplicate video IDs")
            
            logging.debug("Getting collection counts...")
            total_downloads = self.collections['downloads'].count_documents({})
            logging.debug(f"Total downloads: {total_downloads}")
            
            total_history = self.collections['history'].count_documents({})
            logging.debug(f"Total history: {total_history}")
            
            total_events = self.collections['events'].count_documents({})
            logging.debug(f"Total events: {total_events}")
            
            result = {
                "valid": len(issues) == 0,
                "issues": issues,
                "total_downloads": total_downloads,
                "total_history": total_history,
                "total_events": total_events
            }
            logging.debug(f"Validation complete: {result}")
            return result
        except Exception as e:
            logging.error(f"❌ Failed to validate database integrity: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {"valid": False, "issues": [f"Validation failed: {e}"]}
    
    def clear_all_downloads(self) -> int:
        """Clear all downloads for testing purposes."""
        self.ensure_initialized()
        with self._lock:
            try:
                downloads_count = self.collections['downloads'].count_documents({})
                history_count = self.collections['history'].count_documents({})
                events_count = self.collections['events'].count_documents({})
                queue_count = self.collections['queue'].count_documents({})
                
                # Clear all collections
                self.collections['downloads'].delete_many({})
                self.collections['history'].delete_many({})
                self.collections['events'].delete_many({})
                self.collections['queue'].delete_many({})
                
                total_cleared = downloads_count + history_count + events_count + queue_count
                logging.debug(f"✅ Cleared {total_cleared} records from all collections for testing")
                return total_cleared
            except Exception as e:
                logging.error(f"❌ Failed to clear downloads: {e}")
                return 0
        

