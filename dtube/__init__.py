"""
dtube - A YouTube video downloader module using yt-dlp

This module provides functionality to download, pause, and resume YouTube video downloads.
"""

from .downloader import download_video, pause_download, resume_download

__version__ = "1.0.0"
__all__ = ["download_video", "pause_download", "resume_download"]
