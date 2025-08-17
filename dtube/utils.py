"""
Utility functions for dtube module.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from .downloader import _download_manager


def get_download_status(video_id: str) -> Optional[Dict]:
    """Get the current status of a download."""
    return _download_manager.get_download(video_id)


def get_download_progress(video_id: str) -> float:
    """Get the progress of a download as a percentage."""
    download_info = _download_manager.get_download(video_id)
    if download_info:
        return download_info.get('progress', 0.0)
    return 0.0


def list_active_downloads() -> List[str]:
    """Get a list of active download video IDs."""
    return list(_download_manager._downloads.keys())


def check_for_part_files(output_path: str = "downloads") -> List[str]:
    """
    Check for .part files that indicate incomplete downloads.
    
    Args:
        output_path: Directory to check for .part files
        
    Returns:
        List of .part filenames found
    """
    if not os.path.exists(output_path):
        return []
    
    part_files = []
    for filename in os.listdir(output_path):
        if filename.endswith('.part'):
            part_files.append(filename)
    
    return part_files


def check_videos_without_audio(output_path: str = "downloads") -> List[Dict[str, str]]:
    """
    Check which downloaded videos are missing audio tracks.
    
    Args:
        output_path: Directory to check for videos
        
    Returns:
        List of dictionaries with video info for videos without audio
    """
    if not os.path.exists(output_path):
        return []
    
    videos_without_audio = []
    
    for filename in os.listdir(output_path):
        if not os.path.isfile(os.path.join(output_path, filename)):
            continue
            
        # Skip .part files and other non-video files
        if filename.endswith('.part') or not any(ext in filename.lower() for ext in ['.mp4', '.webm', '.mkv', '.avi']):
            continue
        
        file_path = os.path.join(output_path, filename)
        
        # Check if this is a video-only file (no audio)
        if _is_video_only_file(filename):
            # Try to extract video ID from filename
            video_id = _extract_video_id_from_filename(filename)
            
            videos_without_audio.append({
                'filename': filename,
                'file_path': file_path,
                'video_id': video_id,
                'size': os.path.getsize(file_path)
            })
    
    return videos_without_audio


def _is_video_only_file(filename: str) -> bool:
    """
    Check if a filename indicates a video-only file (no audio).
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if the file appears to be video-only
    """
    # Check for patterns that indicate video-only streams
    # YouTube often uses .fXXX.mp4 format for video-only streams
    if '.f' in filename and filename.endswith('.mp4'):
        # Extract the format ID (e.g., f398 from .f398.mp4)
        parts = filename.split('.f')
        if len(parts) > 1:
            format_part = parts[1].split('.')[0]
            # If it's a 3-digit number, it's likely a video-only format ID
            if format_part.isdigit() and len(format_part) == 3:
                return True
    
    # Check for other video-only indicators
    video_only_indicators = ['video_only', 'no_audio', 'muted']
    if any(indicator in filename.lower() for indicator in video_only_indicators):
        return True
    
    return False


def _extract_video_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract YouTube video ID from a filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        YouTube video ID if found, None otherwise
    """
    # Look for 11-character YouTube video IDs in the filename
    import re
    
    # YouTube video IDs are 11 characters long and contain alphanumeric characters and hyphens/underscores
    pattern = r'[a-zA-Z0-9_-]{11}'
    matches = re.findall(pattern, filename)
    
    if matches:
        return matches[0]
    
    return None


def get_download_summary(output_path: str = "downloads") -> Dict[str, any]:
    """
    Get a summary of all downloaded videos and their audio status.
    
    Args:
        output_path: Directory to check
        
    Returns:
        Dictionary with download summary information
    """
    if not os.path.exists(output_path):
        return {
            'total_videos': 0,
            'videos_with_audio': 0,
            'videos_without_audio': 0,
            'total_size': 0,
            'videos_without_audio_list': []
        }
    
    all_videos = []
    videos_without_audio = []
    total_size = 0
    
    for filename in os.listdir(output_path):
        if not os.path.isfile(os.path.join(output_path, filename)):
            continue
            
        # Skip .part files and other non-video files
        if filename.endswith('.part') or not any(ext in filename.lower() for ext in ['.mp4', '.webm', '.mkv', '.avi']):
            continue
        
        file_path = os.path.join(output_path, filename)
        file_size = os.path.getsize(file_path)
        total_size += file_size
        
        video_info = {
            'filename': filename,
            'file_path': file_path,
            'size': file_size,
            'video_id': _extract_video_id_from_filename(filename)
        }
        
        all_videos.append(video_info)
        
        if _is_video_only_file(filename):
            videos_without_audio.append(video_info)
    
    return {
        'total_videos': len(all_videos),
        'videos_with_audio': len(all_videos) - len(videos_without_audio),
        'videos_without_audio': len(videos_without_audio),
        'total_size': total_size,
        'videos_without_audio_list': videos_without_audio
    }


def get_video_resolution(file_path: str) -> Optional[tuple]:
    """
    Get the resolution of a video file.
    
    Args:
        file_path: Path to the video file
        
    Returns:
        tuple: (width, height) or None if unable to determine
    """
    try:
        import subprocess
        # Use ffprobe to get video stream dimensions
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-select_streams', 'v:0', 
            '-show_entries', 'stream=width,height', '-of', 'csv=p=0', file_path
        ], capture_output=True, text=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            # Parse width,height from output
            dimensions = result.stdout.strip().split(',')
            if len(dimensions) == 2:
                width = int(dimensions[0])
                height = int(dimensions[1])
                return (width, height)
        
        return None
    except (ImportError, FileNotFoundError, subprocess.SubprocessError, ValueError):
        return None


def check_download_quality(file_path: str, expected_min_height: int = 720) -> Dict[str, Any]:
    """
    Check if a downloaded video meets quality expectations.
    
    Args:
        file_path: Path to the downloaded video file
        expected_min_height: Minimum expected height in pixels
        
    Returns:
        Dict containing quality information and whether it meets expectations
    """
    resolution = get_video_resolution(file_path)
    has_audio_track = _has_audio(file_path)
    
    if resolution:
        width, height = resolution
        meets_quality = height >= expected_min_height
        quality_label = f"{height}p"
    else:
        width, height = None, None
        meets_quality = False
        quality_label = "unknown"
    
    return {
        'file_path': file_path,
        'resolution': resolution,
        'width': width,
        'height': height,
        'quality_label': quality_label,
        'has_audio': has_audio_track,
        'meets_quality_expectation': meets_quality,
        'expected_min_height': expected_min_height
    }


def _has_audio(file_path: str) -> bool:
    """Check if a video file has audio track."""
    try:
        import subprocess
        # Use ffprobe to check if file has audio stream
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-select_streams', 'a', 
            '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', file_path
        ], capture_output=True, text=True, check=False)
        
        return 'audio' in result.stdout
    except (ImportError, FileNotFoundError, subprocess.SubprocessError):
        # Fallback: assume file has audio if it's not a .fXXX.mp4 file
        # (which indicates video-only stream)
        filename = os.path.basename(file_path)
        return not ('.f' in filename and filename.endswith('.mp4') and 
                   any(char.isdigit() for char in filename.split('.f')[1].split('.')[0]))
