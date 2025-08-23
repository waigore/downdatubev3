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
The data access layer provides comprehensive CRUD operations for each collection:

```python
    # Download CRUD operations
    def create_download(self, download_data: Dict[str, Any]) -> str:
        """Create a new download record."""
        
    def get_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve download by video ID."""
        
    def update_download(self, video_id: str, update_data: Dict[str, Any]) -> bool:
        """Update download record."""
        
    def delete_download(self, video_id: str) -> bool:
        """Delete download record."""
        
    def list_downloads(self, filters: Dict[str, Any] = None, 
                      sort_by: str = "created_at", limit: int = None) -> List[Dict[str, Any]]:
        """List downloads with optional filtering and sorting."""
    
    # History operations
    def add_to_history(self, download_data: Dict[str, Any]) -> str:
        """Move completed download to history."""
        
    def get_download_history(self, video_id: str = None, 
                           filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve download history."""
    
    # Event logging operations
    def log_event(self, video_id: str, event_type: str, event_data: Dict[str, Any]) -> str:
        """Log a download event."""
        
    def get_events(self, video_id: str = None, 
                  event_type: str = None, 
                  date_range: Tuple[datetime, datetime] = None) -> List[Dict[str, Any]]:
        """Retrieve events with optional filtering."""
    
    # Queue operations
    def add_to_queue(self, queue_data: Dict[str, Any]) -> str:
        """Add download to queue."""
        
    def get_next_queued_download(self) -> Optional[Dict[str, Any]]:
        """Get next download from queue."""
        
    def update_queue_status(self, video_id: str, status: str) -> bool:
        """Update queue item status."""
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
        
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup."""
        
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
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

#### Initialization and Startup Management

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
            if not self.data_access.is_initialized():
                logging.info("🔧 Initializing download data access layer...")
                self.data_access.initialize()
                logging.info("✅ Download data access layer ready")
            else:
                logging.info("✅ Download data access layer already initialized")
        except Exception as e:
            logging.error(f"❌ Failed to initialize download data access layer: {e}")
            # Fallback to in-memory storage or raise error based on configuration
            raise
```

##### Lazy Initialization
The system supports lazy initialization for scenarios where immediate database setup isn't required:

```python
class DownloadDataAccess:
    def ensure_initialized(self):
        """Ensure database is initialized before operations."""
        if not self._initialized:
            self.initialize()
    
    def create_download(self, download_data: Dict[str, Any]) -> str:
        """Create a new download record with lazy initialization."""
        self.ensure_initialized()
        # ... implementation
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
2. Add analytics and reporting capabilities
3. Implement retry logic and scheduling
4. Add database maintenance and cleanup functions

##### Phase 4: Testing and Validation
1. Comprehensive testing of data access layer
2. Integration testing with DownloadManager
3. Performance testing and optimization
4. Migration testing from in-memory to persistent storage

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

#### Configuration Options

##### Data Access Layer Settings
```python
DATA_ACCESS_CONFIG = {
    "db_path": "./data/dtube_downloads",
    "auto_initialize": True,
    "lazy_initialization": False,
    "connection_timeout": 30,
    "max_retries": 3,
    "backup_on_startup": False
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
    "cleanup_interval_days": 30
}
```

#### Error Handling and Recovery

##### Data Access Layer Failures
- Automatic retry with exponential backoff
- Fallback to in-memory storage during outages
- Graceful degradation of functionality
- Comprehensive error logging and reporting

##### Database Connection Issues
- Connection pooling and health checks
- Automatic reconnection with backoff
- Circuit breaker pattern for repeated failures
- Health status monitoring and alerts

##### Data Integrity
- Transaction support for critical operations
- Automatic backup before major changes
- Data validation and constraint checking
- Recovery mechanisms for corrupted records

#### Future Enhancements

##### Advanced Data Access Features
- Query optimization and caching
- Bulk operations for batch processing
- Real-time change notifications
- Advanced aggregation pipelines

##### Monitoring and Observability
- Performance metrics and query analysis
- Database health monitoring
- Automated performance tuning
- Integration with monitoring systems

##### Scalability Features
- Sharding and partitioning strategies
- Read replicas for high availability
- Horizontal scaling capabilities
- Multi-region deployment support