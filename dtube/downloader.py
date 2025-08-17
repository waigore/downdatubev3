"""
Core downloader functionality for dtube module.
"""

import os
import threading
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import yt_dlp
from yt_dlp.utils import DownloadError


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
    """Manages active downloads and their states."""
    
    def __init__(self):
        self._downloads: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def add_download(self, video_id: str, download_info: Dict[str, Any]):
        """Add a new download to the manager."""
        with self._lock:
            self._downloads[video_id] = {
                **download_info,
                'status': 'downloading',
                'paused': False,
                'progress': 0.0,
                'start_time': time.time()
            }
    
    def get_download(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get download information for a video ID."""
        with self._lock:
            return self._downloads.get(video_id)
    
    def update_download_status(self, video_id: str, status: str, **kwargs):
        """Update download status and other properties."""
        with self._lock:
            if video_id in self._downloads:
                self._downloads[video_id].update(kwargs)
                self._downloads[video_id]['status'] = status
    
    def pause_download(self, video_id: str) -> bool:
        """Pause a download."""
        with self._lock:
            if video_id in self._downloads:
                self._downloads[video_id]['paused'] = True
                self._downloads[video_id]['status'] = 'paused'
                return True
            return False
    
    def resume_download(self, video_id: str) -> bool:
        """Resume a paused download."""
        with self._lock:
            if video_id in self._downloads:
                self._downloads[video_id]['paused'] = False
                self._downloads[video_id]['status'] = 'downloading'
                return True
            return False
    
    def remove_download(self, video_id: str):
        """Remove a completed or failed download."""
        with self._lock:
            self._downloads.pop(video_id, None)


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



