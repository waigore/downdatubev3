## dtube

### Download Management with Mongita

#### Overview
The download management system will be refactored to use Mongita (a lightweight, file-based MongoDB alternative) instead of in-memory dictionaries. This provides persistent storage, better querying capabilities, and improved scalability while maintaining all existing functionality. The architecture will include a separate data access layer that manages all database operations.

#### Architecture Overview

```
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│  DownloadManager│    │   Data Access Layer │    │   Mongita DB    │
│                 │    │                     │    │                 │
│ - add_download  │───▶│ - CRUD operations  │───▶│ - downloads     │
│ - get_download  │    │ - Index management │    │ - history       │
│ - pause/resume  │    │ - Query helpers    │    │ - events        │
│ - status mgmt   │    │ - Init scripts     │    │ - queue         │
└─────────────────┘    └─────────────────────┘    └─────────────────┘
```

#### Mongita Database Schema

##### Database Configuration
- **Database Name**: `dtube_downloads`
- **Storage**: File-based database stored in `./data/dtube_downloads/`
- **Collections**: Multiple collections for different aspects of download management

##### Collections

###### 1. downloads Collection
Primary collection for tracking active and completed downloads.

```json
{
  "_id": "ObjectId",
  "video_id": "string (unique)",
  "url": "string",
  "title": "string",
  "status": "string (downloading|paused|completed|error|cancelled)",
  "paused": "boolean",
  "progress": "number (0.0-100.0)",
  "start_time": "datetime",
  "end_time": "datetime (optional)",
  "output_path": "string",
  "quality": "string",
  "filename": "string (optional)",
  "file_size": "number (optional)",
  "error_message": "string (optional)",
  "retry_count": "number (default: 0)",
  "max_retries": "number (default: 3)",
  "completed_at": "datetime",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

###### 2. download_history Collection
Persistent history of all downloads for analytics and debugging.

```json
{
  "_id": "ObjectId",
  "video_id": "string",
  "url": "string",
  "title": "string",
  "final_status": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "duration_seconds": "number",
  "file_size": "number (optional)",
  "output_path": "string",
  "quality": "string",
  "error_message": "string (optional)",
  "retry_count": "number",
  
}
```

###### 3. download_events Collection
Audit trail of all download state changes and events.

```json
{
  "_id": "ObjectId",
  "video_id": "string",
  "event_type": "string (status_change|progress_update|pause|resume|error|retry)",
  "event_data": "object",
  "timestamp": "datetime",
  "user_agent": "string (optional)"
}
```

###### 4. download_queue Collection
Queue management for pending downloads with priority and scheduling.

```json
{
  "_id": "ObjectId",
  "video_id": "string",
  "url": "string",
  "title": "string",
  "priority": "number (1-10, default: 5)",
  "scheduled_time": "datetime (optional)",
  "max_concurrent": "number (optional)",
  "output_path": "string",
  "quality": "string",
  "status": "string (queued|processing|completed|failed)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### Data Access Layer Design

##### DownloadDataAccess Class
The data access layer will provide a clean interface for all database operations, with the DownloadManager never directly accessing Mongita collections.

```python
class DownloadDataAccess:
    """Data access layer for managing Mongita database operations."""
    
    def __init__(self, db_path: str = "./data/dtube_downloads"):
        self.db_path = db_path
        self.db = None
        self.collections = {}
        self._initialized = False
        self._lock = threading.Lock()
        
    def initialize(self):
        """Initialize database connection and collections."""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:  # Double-check pattern
                return
                
            try:
                self._connect_database()
                self._initialize_collections()
                self._create_indexes()
                self._initialized = True
                logging.info("✅ Download data access layer initialized successfully")
            except Exception as e:
                logging.error(f"❌ Failed to initialize data access layer: {e}")
                raise
    
    def _connect_database(self):
        """Establish connection to Mongita database."""
        self.db = Mongita(self.db_path)
        
    def _initialize_collections(self):
        """Initialize all required collections."""
        self.collections = {
            'downloads': self.db.get_collection("downloads"),
            'history': self.db.get_collection("download_history"),
            'events': self.db.get_collection("download_events"),
            'queue': self.db.get_collection("download_queue")
        }
    
    def _create_indexes(self):
        """Create database indexes for optimal query performance."""
        # downloads collection indexes
        self.collections['downloads'].create_index("video_id", unique=True)
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
        
        logging.info("✅ Database indexes created successfully")
    
    def is_initialized(self) -> bool:
        """Check if the data access layer is properly initialized."""
        return self._initialized
```

##### CRUD Operations Interface
The data access layer provides comprehensive CRUD operations for each collection. The caller is responsible for ensuring database initialization:

```python
    # Download CRUD operations
    def create_download(self, download_data: Dict[str, Any]) -> str:
        """Create a new download record."""
        # ... implementation
        
    def get_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve download by video ID."""
        # ... implementation
        
    def update_download(self, video_id: str, update_data: Dict[str, Any]) -> bool:
        """Update download record."""
        # ... implementation
        
    def delete_download(self, video_id: str) -> bool:
        """Delete download record."""
        # ... implementation
        
    def list_downloads(self, filters: Dict[str, Any] = None, 
                      sort_by: str = "created_at", limit: int = None) -> List[Dict[str, Any]]:
        """List downloads with optional filtering and sorting."""
        # ... implementation
    
    # History operations
    def add_to_history(self, download_data: Dict[str, Any]) -> str:
        """Move completed download to history."""
        # ... implementation
        
    def get_download_history(self, video_id: str = None, 
                           filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve download history."""
        # ... implementation
    
    # Event logging operations
    def log_event(self, video_id: str, event_type: str, event_data: Dict[str, Any]) -> str:
        """Log a download event."""
        # ... implementation
        
    def get_events(self, video_id: str = None, 
                  event_type: str = None, 
                  date_range: Tuple[datetime, datetime] = None) -> List[Dict[str, Any]]:
        """Retrieve events with optional filtering."""
        # ... implementation
    
    # Queue operations
    def add_to_queue(self, queue_data: Dict[str, Any]) -> str:
        """Add download to queue."""
        # ... implementation
        
    def get_next_queued_download(self) -> Optional[Dict[str, Any]]:
        """Get next download from queue."""
        # ... implementation
        
    def update_queue_status(self, video_id: str, status: str) -> bool:
        """Update queue item status."""
        # ... implementation
```

##### Helper Functions and Initialization Scripts
The data access layer includes helper functions for common operations and initialization tasks:

```python
    def get_download_stats(self) -> Dict[str, Any]:
        """Get aggregate download statistics."""
        
    def get_failed_downloads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of failed downloads for analysis."""
        
    def cleanup_old_records(self, days_to_keep: int = 365) -> int:
        """Clean up old history and event records."""
        
    def validate_database_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and report issues."""
        

```

#### DownloadManager Class Refactor
The existing `DownloadManager` class will be refactored to use the data access layer instead of directly managing Mongita collections:

```python
class DownloadManager:
    """Manages active downloads and their states via data access layer."""
    
    def __init__(self, data_access: DownloadDataAccess = None):
        self.data_access = data_access or DownloadDataAccess()
        self._lock = threading.Lock()
        
        # Initialize data access layer if not already done
        if not self.data_access.is_initialized():
            self.data_access.initialize()
    
    def add_download(self, video_id: str, download_info: Dict[str, Any]):
        """Add a new download to the manager."""
        with self._lock:
            download_data = {
                **download_info,
                'status': 'downloading',
                'paused': False,
                'progress': 0.0,
                'start_time': datetime.now(),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Create download record via data access layer
            self.data_access.create_download(download_data)
            
            # Log the event
            self.data_access.log_event(video_id, 'download_started', {
                'status': 'downloading',
                'output_path': download_info.get('output_path'),
                'quality': download_info.get('quality')
            })
    
    def get_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get download information for a video ID."""
        return self.data_access.get_download(video_id)
    
    def update_download_status(self, video_id: str, status: str, **kwargs):
        """Update download status and other properties."""
        with self._lock:
            update_data = {
                'status': status,
                'updated_at': datetime.now(),
                **kwargs
            }
            
            # Update download record via data access layer
            if self.data_access.update_download(video_id, update_data):
                # Log the status change event
                self.data_access.log_event(video_id, 'status_change', {
                    'old_status': self.get_download(video_id).get('status') if self.get_download(video_id) else 'unknown',
                    'new_status': status,
                    **kwargs
                })
    
    def pause_download(self, video_id: str) -> bool:
        """Pause a download."""
        with self._lock:
            if self.update_download_status(video_id, 'paused', paused=True):
                self.data_access.log_event(video_id, 'download_paused', {})
                return True
            return False
    
    def resume_download(self, video_id: str) -> bool:
        """Resume a paused download."""
        with self._lock:
            if self.update_download_status(video_id, 'downloading', paused=False):
                self.data_access.log_event(video_id, 'download_resumed', {})
                return True
            return False
    
    def remove_download(self, video_id: str):
        """Remove a completed or failed download."""
        with self._lock:
            # Get download info before removal
            download_info = self.get_download(video_id)
            if download_info:
                # Move to history
                history_data = {
                    **download_info,
                    'final_status': download_info.get('status'),
                    'end_time': datetime.now(),
                    'duration_seconds': (datetime.now() - download_info.get('start_time')).total_seconds(),
                    'completed_at': datetime.now()
                }
                self.data_access.add_to_history(history_data)
                
                # Log completion event
                self.data_access.log_event(video_id, 'download_completed', {
                    'final_status': download_info.get('status'),
                    'duration_seconds': history_data['duration_seconds']
                })
                
                # Delete from active downloads
                self.data_access.delete_download(video_id)
```

#### Database Persistence and Initialization

##### Persistent Database Requirements
The Mongita database must be persistent across application sessions with the following characteristics:

- **Session Persistence**: If a previous session of dtube created the database, the same database will be used for subsequent app runs
- **Initialization Logic**: Database checks (e.g. existence and proper initialization of collections and indexes) should be executed at `dl.py` startup
- **Assumption of Initialization**: The data access and downloader layers should assume that the database is fully initialized on any data access operation. It is the caller's responsibility to ensure the database exists and is properly initialized

##### Database Initialization and Recovery
The system provides a helper function to ensure database integrity and proper initialization:

```python
class DownloadDataAccess:
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
                    # Database is valid, just connect and set up collections reference
                    self._connect_database()
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
            temp_db = Mongita(self.db_path)
            required_collections = ['downloads', 'download_history', 'download_events', 'download_queue']
            
            for collection_name in required_collections:
                try:
                    collection = temp_db.get_collection(collection_name)
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
                logging.info("🗑️ Removed corrupted database directory")
            
            # Create fresh database
            self._connect_database()
            self._initialize_collections()
            self._create_indexes()
            logging.info("🆕 Fresh database created with all collections and indexes")
        except Exception as e:
            logging.error(f"❌ Failed to recreate database: {e}")
            raise
```

##### Startup Sequence
The data access layer handles all initialization at startup, ensuring indexes and collections are created only when necessary:

```python
class DownloadManager:
    def __init__(self, data_access: DownloadDataAccess = None):
        self.data_access = data_access or DownloadDataAccess()
        self._lock = threading.Lock()
        
        # Initialize data access layer at startup
        self._initialize_at_startup()
    
    def _initialize_at_startup(self):
        """Initialize data access layer during startup."""
        try:
            logging.info("🔧 Initializing download data access layer...")
            self.data_access.ensure_database_ready()
            logging.info("✅ Download data access layer ready")
        except Exception as e:
            logging.error(f"❌ Failed to initialize download data access layer: {e}")
            # Fallback to in-memory storage or raise error based on configuration
            raise
```

```

##### Caller Responsibility for Database Initialization
The data access and downloader layers assume the database is fully initialized. The caller (typically `dl.py` at startup) is responsible for ensuring database readiness:

```python
# In dl.py startup
def initialize_download_system():
    """Initialize the download system at application startup."""
    try:
        # Create data access instance
        data_access = DownloadDataAccess()
        
        # Ensure database is ready (this will recreate if corrupted)
        data_access.ensure_database_ready()
        
        # Create download manager with initialized data access
        download_manager = DownloadManager(data_access)
        
        logging.info("✅ Download system initialized successfully")
        return download_manager
        
    except Exception as e:
        logging.error(f"❌ Failed to initialize download system: {e}")
        raise

# Usage in main application
if __name__ == "__main__":
    try:
        download_manager = initialize_download_system()
        # Application continues with fully initialized database
    except Exception as e:
        logging.error(f"❌ Application startup failed: {e}")
        sys.exit(1)
```

##### Data Access Layer Initialization Contract
The data access layer provides a clear contract for initialization:

```python
class DownloadDataAccess:
    def __init__(self, db_path: str = "./data/dtube_downloads"):
        """Initialize data access layer. Database is NOT initialized until ensure_database_ready() is called."""
        self.db_path = db_path
        self.db = None
        self.collections = {}
        self._initialized = False
        self._lock = threading.Lock()
    
    def ensure_database_ready(self):
        """Ensure database is ready for operations. This method:
        - Checks if existing database is valid
        - Recreates database if corrupted or missing
        - Creates all required collections and indexes
        - Sets _initialized flag to True
        
        This method is idempotent and thread-safe.
        """
        # ... implementation as shown above
    
    def is_initialized(self) -> bool:
        """Check if database is ready for operations."""
        return self._initialized
    

```

##### Database Integrity Validation
The system includes comprehensive database integrity checking:

```python
class DownloadDataAccess:
    def validate_database_integrity(self) -> Dict[str, Any]:
        """Validate database integrity and report issues."""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'collections_status': {},
            'indexes_status': {}
        }
        
        try:
            if not self._initialized:
                validation_result['is_valid'] = False
                validation_result['issues'].append("Database not initialized")
                return validation_result
            
            # Check collections
            required_collections = ['downloads', 'download_history', 'download_events', 'download_queue']
            for collection_name in required_collections:
                try:
                    collection = self.collections[collection_name]
                    # Test basic operations
                    collection.find_one()
                    validation_result['collections_status'][collection_name] = 'OK'
                except Exception as e:
                    validation_result['collections_status'][collection_name] = f'ERROR: {e}'
                    validation_result['issues'].append(f"Collection {collection_name}: {e}")
                    validation_result['is_valid'] = False
            
            # Check indexes
            try:
                # Verify key indexes exist and are functional
                downloads_coll = self.collections['downloads']
                downloads_coll.find_one({"video_id": "test_index_check"})
                validation_result['indexes_status']['downloads'] = 'OK'
            except Exception as e:
                validation_result['indexes_status']['downloads'] = f'ERROR: {e}'
                validation_result['issues'].append(f"Downloads indexes: {e}")
                validation_result['is_valid'] = False
                
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"Validation error: {e}")
        
        return validation_result
```

#### Migration Strategy

##### Phase 1: Data Access Layer Implementation
1. Create `DownloadDataAccess` class with Mongita backend
2. Implement all CRUD operations and helper functions
3. Add initialization scripts and index management
4. Create comprehensive test suite for data access layer

##### Phase 2: DownloadManager Refactoring
1. Refactor `DownloadManager` to use data access layer
2. Maintain backward compatibility with existing API
3. Implement event logging for all operations
4. Add error handling and fallback mechanisms

##### Phase 3: Enhanced Features
1. Implement queue management system via data access layer

##### Phase 4: Testing and Validation
1. Comprehensive testing of data access layer
2. Integration testing with DownloadManager
3. Performance testing and optimization

#### Benefits of Layered Architecture

##### Separation of Concerns
- **DownloadManager**: Business logic and download orchestration
- **Data Access Layer**: Database operations and data persistence
- **Mongita**: Storage engine and query processing

##### Maintainability
- Clear interface boundaries between layers
- Easier testing and mocking of database operations
- Simplified error handling and recovery

##### Flexibility
- Easy to switch database backends if needed
- Support for different storage strategies
- Configurable initialization and setup

##### Performance
- Connection pooling and resource management
- Optimized query patterns and indexing
- Efficient data access patterns

#### Benefits of Persistent Database Approach

##### Data Persistence
- **Session Continuity**: Downloads and history persist across application restarts
- **User Experience**: Users don't lose download progress or history between sessions
- **Reliability**: Robust data storage with automatic recovery from corruption

##### Automatic Recovery
- **Self-Healing**: Database automatically recreates itself if corrupted
- **Zero Manual Intervention**: No need for users to manually fix database issues
- **Graceful Degradation**: Application continues to work even after database corruption

##### Clear Initialization Contract
- **Explicit Responsibility**: Clear separation between initialization and usage
- **Fail-Fast Behavior**: Operations fail immediately if database isn't ready
- **Predictable Behavior**: Consistent initialization state across all operations

#### Configuration Options

##### Data Access Layer Settings
```python
DATA_ACCESS_CONFIG = {
    "db_path": "./data/dtube_downloads",
    "auto_initialize": False,  # Changed: Caller must explicitly initialize
    "lazy_initialization": True,  # Changed: Supports lazy initialization
    "connection_timeout": 30,
    "max_retries": 3,
    "auto_recovery": True,  # New: Enable automatic database recovery
    "validate_on_startup": True  # New: Validate database integrity at startup
}
```

##### Database Settings
```python
DOWNLOAD_DB_CONFIG = {
    "max_connections": 10,
    "write_concern": "majority",
    "read_preference": "primary",
    "index_creation": "startup",  # startup|lazy|manual
    "auto_cleanup": True,
    "cleanup_interval_days": 30,
    "persistence_mode": "file_based",  # New: File-based persistence
    "backup_on_startup": False,  # New: Optional backup before operations
    "integrity_check_interval": "startup"  # New: When to run integrity checks
}
```

##### Initialization Configuration
```python
INITIALIZATION_CONFIG = {
    "startup_initialization": True,  # Initialize at dl.py startup
    "fail_fast": True,  # Fail immediately if database can't be initialized
    "recovery_attempts": 3,  # Number of recovery attempts
    "fallback_to_memory": False,  # Don't fall back to in-memory storage
    "log_initialization": True  # Log all initialization steps
}
```