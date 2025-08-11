"""
Utility functions for dtube module.
"""

from typing import Dict, List, Optional, Any
from .downloader import _download_manager


def get_download_status(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current status of a download.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Dict containing download status information or None if not found
    """
    return _download_manager.get_download(video_id)


def list_active_downloads() -> List[Dict[str, Any]]:
    """
    Get a list of all active downloads.
    
    Returns:
        List of dictionaries containing download information
    """
    downloads = []
    for video_id, info in _download_manager._downloads.items():
        downloads.append({
            'video_id': video_id,
            **info
        })
    return downloads


def cancel_download(video_id: str) -> bool:
    """
    Cancel a download and remove it from the manager.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        bool: True if download was cancelled, False if not found
    """
    download_info = _download_manager.get_download(video_id)
    if download_info:
        _download_manager.remove_download(video_id)
        return True
    return False


def get_download_progress(video_id: str) -> Optional[float]:
    """
    Get the current progress of a download as a percentage.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        float: Download progress as percentage (0-100) or None if not found
    """
    download_info = _download_manager.get_download(video_id)
    if download_info:
        return download_info.get('progress', 0.0)
    return None
