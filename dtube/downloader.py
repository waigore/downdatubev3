"""
Core downloader functionality for dtube module.
"""

import os
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs
import yt_dlp
from yt_dlp.utils import DownloadError
from .data_access import DownloadDataAccess


class DownloadFilter(logging.Filter):
    """Filter to suppress [download] prefixed messages from yt-dlp."""
    
    def filter(self, record):
        # Suppress messages that start with [download]
        if record.getMessage().startswith('[download]'):
            return False
        return True


# Create a custom logger for yt-dlp
_ytdlp_logger = logging.getLogger('yt_dlp')
_ytdlp_logger.setLevel(logging.INFO)
_ytdlp_logger.addFilter(DownloadFilter())

# Ensure root logger is configured for dtube
if not logging.getLogger().handlers:
    # Configure root logger if not already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


class DownloadManager:
    """Manages active downloads and their states via data access layer."""
    
    def __init__(self, data_access: DownloadDataAccess = None):
        self.data_access = data_access or DownloadDataAccess()
        # Removed lock - multithreaded access is assumed safe
        
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
    
    def add_download(self, video_id: str, download_info: Dict[str, Any]):
        """Add a new download to the manager."""
        # Removed lock usage
        # Only store serializable data in the database
        serializable_info = {k: v for k, v in download_info.items() 
                           if k not in ['ydl_opts'] and not callable(v) and not hasattr(v, '__dict__')}
        
        download_data = {
            **serializable_info,
            'video_id': video_id,
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
    
    def add_to_queue(self, video_id: str, queue_info: Dict[str, Any]) -> str:
        """Add a download to the queue."""
        try:
            # Ensure video_id is in queue_info
            queue_info['video_id'] = video_id
            
            # Add to queue via data access layer
            result_id = self.data_access.add_to_queue(queue_info)
            
            # Log the event
            self.data_access.log_event(video_id, 'queued_for_download', {
                'priority': queue_info.get('priority', 5),
                'scheduled_time': queue_info.get('scheduled_time', 'immediate'),
                'output_path': queue_info.get('output_path'),
                'quality': queue_info.get('quality')
            })
            
            logging.info(f"✅ Added {video_id} to download queue")
            return result_id
            
        except Exception as e:
            logging.error(f"❌ Failed to add {video_id} to queue: {e}")
            raise
    
    def get_next_queued_download(self) -> Optional[Dict[str, Any]]:
        """Get the next download from the queue."""
        return self.data_access.get_next_queued_download()
    
    def get_queued_downloads(self, status: str = None, priority: int = None, 
                            limit: int = None) -> List[Dict[str, Any]]:
        """Get queued downloads with optional filtering."""
        return self.data_access.get_queued_downloads(status, priority, limit)
    
    def start_queued_download(self, video_id: str) -> bool:
        """Start a download from the queue."""
        try:
            # Get queue item
            queue_item = self.data_access.collections['queue'].find_one({"video_id": video_id})
            if not queue_item:
                logging.warning(f"⚠️ Queue item {video_id} not found")
                return False
            
            if queue_item.get('status') != 'queued':
                logging.warning(f"⚠️ Queue item {video_id} is not queued (status: {queue_item.get('status')})")
                return False
            
            # Update queue status to processing
            self.data_access.update_queue_status(video_id, 'processing')
            
            # Create download record
            download_data = {
                'video_id': video_id,
                'url': queue_item.get('url', ''),
                'title': queue_item.get('title', ''),
                'status': 'downloading',
                'paused': False,
                'progress': 0.0,
                'start_time': datetime.now(),
                'output_path': queue_item.get('output_path', './downloads'),
                'quality': queue_item.get('quality', 'best'),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            self.data_access.create_download(download_data)
            
            # Log the event
            self.data_access.log_event(video_id, 'download_started_from_queue', {
                'queue_priority': queue_item.get('priority'),
                'output_path': queue_item.get('output_path'),
                'quality': queue_item.get('quality')
            })
            
            logging.info(f"✅ Started download for queued item {video_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to start queued download {video_id}: {e}")
            # Reset queue status on failure
            self.data_access.update_queue_status(video_id, 'queued')
            return False
    
    def promote_queue_item(self, video_id: str, new_priority: int) -> bool:
        """Promote a queue item to higher priority."""
        success = self.data_access.promote_queue_item(video_id, new_priority)
        if success:
            self.data_access.log_event(video_id, 'queue_priority_promoted', {
                'new_priority': new_priority
            })
        return success
    
    def demote_queue_item(self, video_id: str, new_priority: int) -> bool:
        """Demote a queue item to lower priority."""
        success = self.data_access.demote_queue_item(video_id, new_priority)
        if success:
            self.data_access.log_event(video_id, 'queue_priority_demoted', {
                'new_priority': new_priority
            })
        return success
    
    def move_to_front_of_queue(self, video_id: str) -> bool:
        """Move a queue item to the front of the queue."""
        success = self.data_access.move_to_front_of_queue(video_id)
        if success:
            self.data_access.log_event(video_id, 'queue_item_moved_to_front', {})
        return success
    
    def remove_from_queue(self, video_id: str) -> bool:
        """Remove an item from the queue."""
        success = self.data_access.remove_from_queue(video_id)
        if success:
            self.data_access.log_event(video_id, 'queue_item_removed', {})
        return success
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        return self.data_access.get_queue_stats()
    
    def clear_queue(self, status: str = None) -> int:
        """Clear all items from queue with optional status filter."""
        cleared_count = self.data_access.clear_queue(status)
        if cleared_count > 0:
            self.data_access.log_event('system', 'queue_cleared', {
                'cleared_count': cleared_count,
                'status_filter': status
            })
        return cleared_count
    
    def retry_failed_queue_item(self, video_id: str) -> bool:
        """Retry a failed queue item."""
        success = self.data_access.retry_failed_queue_item(video_id)
        if success:
            self.data_access.log_event(video_id, 'queue_item_retried', {})
        return success
    
    def get_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get download information for a video ID."""
        return self.data_access.get_download(video_id)
    
    def update_download_status(self, video_id: str, status: str, **kwargs):
        """Update download status and other properties."""
        # Removed lock usage
        update_data = {
            'status': status,
            'updated_at': datetime.now(),
            **kwargs
        }
        
        # Update download record via data access layer
        success = self.data_access.update_download(video_id, update_data)
        if success:
            # Log the status change event
            old_status = self.get_download(video_id).get('status') if self.get_download(video_id) else 'unknown'
            self.data_access.log_event(video_id, 'status_change', {
                'old_status': old_status,
                'new_status': status,
                **kwargs
            })
            
            # If download completed, update queue status if it exists
            if status == 'completed':
                self.data_access.update_queue_status(video_id, 'completed')
            elif status == 'error':
                self.data_access.update_queue_status(video_id, 'failed')
        
        return success
    
    def pause_download(self, video_id: str) -> bool:
        """Pause a download."""
        # Removed lock usage
        # Check if download exists first
        if not self.get_download(video_id):
            return False
            
        if self.update_download_status(video_id, 'paused', paused=True):
            self.data_access.log_event(video_id, 'download_paused', {})
            return True
        return False
    
    def resume_download(self, video_id: str) -> bool:
        """Resume a paused download."""
        # Removed lock usage
        # Check if download exists first
        if not self.get_download(video_id):
            return False
            
        if self.update_download_status(video_id, 'downloading', paused=False):
            self.data_access.log_event(video_id, 'download_resumed', {})
            return True
        return False
    
    def remove_download(self, video_id: str):
        """Remove a completed or failed download."""
        # Removed lock usage
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
            
            # Delete from active downloads - ensure all records with this video_id are removed
            success = self.data_access.delete_download(video_id)
            if not success:
                logging.warning(f"Failed to delete download {video_id} from database")
            
            # Verify deletion
            remaining = self.get_download(video_id)
            if remaining:
                logging.warning(f"Download {video_id} still exists after deletion attempt")
                # Force cleanup by deleting all records with this video_id
                self.data_access.collections['downloads'].delete_many({"video_id": video_id})
    
    def list_downloads(self, status: str = None) -> List[Dict[str, Any]]:
        """List all downloads with optional status filter."""
        filters = {"status": status} if status else None
        return self.data_access.list_downloads(filters)
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics."""
        return self.data_access.get_download_stats()
    
    def get_download_history(self, video_id: str = None) -> List[Dict[str, Any]]:
        """Get download history."""
        return self.data_access.get_download_history(video_id)
    
    def get_failed_downloads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of failed downloads for analysis."""
        return self.data_access.get_failed_downloads(limit)
    
    def clear_all_downloads(self) -> int:
        """Clear all downloads for testing purposes."""
        return self.data_access.clear_all_downloads()


# Global download manager instance
_download_manager = DownloadManager()


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    # Handle different YouTube URL formats
    if 'youtube.com/watch' in url:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        return query_params.get('v', [None])[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0]
    elif 'youtube.com/embed/' in url:
        return url.split('youtube.com/embed/')[-1].split('?')[0]
    else:
        # Assume it's already a video ID
        return url


def download_video(url: str, output_path: str = "downloads", 
                  quality: str = "best") -> str:
    """
    Download a video from YouTube.
    
    Args:
        url: YouTube video URL
        output_path: Directory to save the downloaded video
        quality: Video quality preference (kept for compatibility, but format selection
                now prioritizes 720p height with MP4 extension)
    
    Returns:
        str: YouTube video ID
        
    Raises:
        ValueError: If URL is invalid or video ID cannot be extracted
        DownloadError: If download fails
        
    Note:
        Format selection now uses a smart approach to find the best available quality:
        1. First tries to find 720p+ formats with video+audio
        2. Falls back to 480p+ formats with video+audio
        3. Finally falls back to best available quality
    """
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Could not extract video ID from URL")
    
    # Create output directory
    os.makedirs(output_path, exist_ok=True)
    
    # Extract video metadata to get the title
    video_title = _extract_video_title(url)
    
    # Create filename template with title and video ID
    filename_template = _create_filename_template(video_title, video_id)
    
    # Use fixed format specification for consistent quality
    format_spec = 'bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio'
    # Format selection with specified preference priority:
    # Use the smart-selected format or fall back to strict quality requirements
    ydl_opts = {
        'format': format_spec,
        'outtmpl': os.path.join(output_path, filename_template),
        'progress_hooks': [lambda d: _progress_hook(d, video_id)],
        'noplaylist': True,
        'ignoreerrors': False,
        'logger': _ytdlp_logger,
        # Ensure separate video and audio downloads are properly merged with ffmpeg
        'merge_output_format': 'mp4',
        'verbose': True,
    }
    
    # Log the format selection strategy
    logging.info(f"🔧 Format selection strategy: {format_spec}")
    
    try:
        # Add download to manager
        _download_manager.add_download(video_id, {
            'url': url,
            'output_path': output_path,
            'quality': quality,
            'ydl_opts': ydl_opts,
            'title': video_title
        })
        
        # Start download in a separate thread
        download_thread = threading.Thread(
            target=_download_worker,
            args=(video_id, ydl_opts),
            daemon=True
        )
        download_thread.start()
        
        return video_id
        
    except Exception as e:
        _download_manager.remove_download(video_id)
        raise DownloadError(f"Failed to start download: {str(e)}")


def pause_download(video_id: str) -> bool:
    """
    Pause a video download.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        bool: True if download was paused, False if not found
    """
    return _download_manager.pause_download(video_id)


def resume_download(video_id: str) -> bool:
    """
    Resume a paused video download.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        bool: True if download was resumed, False if not found
    """
    return _download_manager.resume_download(video_id)


def _progress_hook(d: Dict[str, Any], video_id: str):
    """Progress hook for yt-dlp to track download progress."""
    if d['status'] == 'downloading':
        download_info = _download_manager.get_download(video_id)
        if not download_info:
            # Download was removed from manager, skip progress updates
            return
            
        # Check if download is paused
        if download_info.get('paused'):
            # Signal to yt-dlp to stop (this will be handled in the worker)
            return
        
        # Update progress
        if 'total_bytes' in d and d['total_bytes']:
            progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            _download_manager.update_download_status(
                video_id, 
                'downloading', 
                progress=progress
            )
            
            # Log progress event
            _download_manager.data_access.log_event(video_id, 'progress_update', {
                'progress': progress,
                'downloaded_bytes': d['downloaded_bytes'],
                'total_bytes': d['total_bytes']
            })
            
        # Log format information if available
        if 'format' in d:
            format_info = d['format']
            logging.info(f"📥 {video_id}: Downloading format {format_info.get('format_id', 'unknown')} "
                       f"({format_info.get('resolution', 'unknown resolution')})")
    
    elif d['status'] == 'finished':
        # Log completion with format details
        if 'format' in d:
            format_info = d['format']
            logging.info(f"✅ {video_id}: Download completed - Format: {format_info.get('format_id', 'unknown')} "
                        f"({format_info.get('resolution', 'unknown resolution')})")
        else:
            logging.info(f"✅ {video_id}: Download completed")


def _download_worker(video_id: str, ydl_opts: Dict[str, Any]):
    """Worker thread for handling downloads."""
    try:
        logging.info(f"🔧 {video_id}: Starting download worker thread")
        
        # Get download info and URL
        download_info = _download_manager.get_download(video_id)
        if not download_info:
            logging.error(f"❌ {video_id}: Download info not found in manager")
            return
            
        url = download_info.get('url')
        if not url:
            logging.error(f"❌ {video_id}: URL not found in download info")
            return
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Check if download should be paused before starting
            if download_info.get('paused'):
                logging.info(f"⏸️ {video_id}: Download paused before starting")
                _download_manager.update_download_status(video_id, 'paused')
                return
            
            logging.info(f"🔧 {video_id}: Starting yt-dlp download")
            ydl.download([url])
            logging.info(f"✅ {video_id}: yt-dlp download completed successfully")

            _download_manager.update_download_status(video_id, 'completed')
            _download_manager.remove_download(video_id)
            
    except Exception as e:
        logging.error(f"❌ {video_id}: Exception in download worker: {str(e)}")
        logging.error(f"❌ {video_id}: Exception type: {type(e).__name__}")
        import traceback
        logging.error(f"❌ {video_id}: Full traceback: {traceback.format_exc()}")
        
        # Log error event
        _download_manager.data_access.log_event(video_id, 'download_error', {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        })
        
        _download_manager.update_download_status(video_id, 'error', error=str(e))
        # Keep the download in manager for error inspection
        time.sleep(5)  # Wait before cleanup
        _download_manager.remove_download(video_id)


def _extract_video_title(url: str) -> str:
    """
    Extract video title from YouTube URL using yt-dlp.
    
    Args:
        url: YouTube video URL
        
    Returns:
        str: Video title, or empty string if extraction fails
    """
    try:
        # Use yt-dlp to extract video info without downloading
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            
            # Clean the title for filesystem compatibility
            cleaned_title = _clean_title_for_filename(title)
            return cleaned_title
            
    except Exception as e:
        logging.warning(f"Failed to extract video title: {e}")
        return ""


def _clean_title_for_filename(title: str) -> str:
    """
    Clean video title to make it safe for use in filenames.
    
    Args:
        title: Raw video title
        
    Returns:
        str: Cleaned title safe for filenames
    """
    if not title:
        return ""
    
    # Remove or replace characters that are problematic in filenames
    import re
    
    # Replace problematic characters with underscores or remove them
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', title)
    
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip(' .')
    
    # Limit length to avoid extremely long filenames
    max_length = 100
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(' .')
    
    # Ensure it's not empty after cleaning
    if not cleaned:
        cleaned = "untitled"
    
    return cleaned


def _create_filename_template(title: str, video_id: str) -> str:
    """
    Create filename template with title and video ID.
    
    Args:
        title: Cleaned video title
        video_id: YouTube video ID
        
    Returns:
        str: Filename template for yt-dlp
    """
    if title:
        # Use title + video ID format
        return f'{title}_{video_id}.%(ext)s'
    else:
        # Fallback to just video ID if title extraction failed
        return f'{video_id}.%(ext)s'



