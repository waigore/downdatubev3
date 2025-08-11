"""
Core downloader functionality for dtube module.
"""

import os
import threading
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import yt_dlp
from yt_dlp.utils import DownloadError


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
        quality: Video quality preference (best, worst, 720p, 480p, etc.)
    
    Returns:
        str: YouTube video ID
        
    Raises:
        ValueError: If URL is invalid or video ID cannot be extracted
        DownloadError: If download fails
    """
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Could not extract video ID from URL")
    
    # Create output directory
    os.makedirs(output_path, exist_ok=True)
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': f'best[height<={quality}]' if quality.isdigit() else quality,
        'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
        'progress_hooks': [lambda d: _progress_hook(d, video_id)],
        'noplaylist': True,
        'ignoreerrors': False,
    }
    
    try:
        # Add download to manager
        _download_manager.add_download(video_id, {
            'url': url,
            'output_path': output_path,
            'quality': quality,
            'ydl_opts': ydl_opts
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
        if _download_manager.get_download(video_id):
            # Check if download is paused
            download_info = _download_manager.get_download(video_id)
            if download_info and download_info.get('paused'):
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
    
    elif d['status'] == 'finished':
        _download_manager.update_download_status(video_id, 'completed')
        _download_manager.remove_download(video_id)


def _download_worker(video_id: str, ydl_opts: Dict[str, Any]):
    """Worker thread for handling downloads."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Check if download should be paused before starting
            download_info = _download_manager.get_download(video_id)
            if download_info and download_info.get('paused'):
                _download_manager.update_download_status(video_id, 'paused')
                return
            
            ydl.download([download_info['url']])
            
    except Exception as e:
        _download_manager.update_download_status(video_id, 'error', error=str(e))
        # Keep the download in manager for error inspection
        time.sleep(5)  # Wait before cleanup
        _download_manager.remove_download(video_id)
