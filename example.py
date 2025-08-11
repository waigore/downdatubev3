#!/usr/bin/env python3
"""
Example usage of the dtube module.

This script demonstrates how to use the three main functions:
- download_video
- pause_download  
- resume_download
"""

import time
from dtube import download_video, pause_download, resume_download
from dtube.utils import get_download_status, list_active_downloads, get_download_progress


def main():
    """Main example function."""
    print("=== dtube Module Example ===\n")
    
    # Example YouTube URL
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"Starting download for: {youtube_url}")
    
    try:
        # Start the download
        video_id = download_video(youtube_url, output_path="downloads", quality="720p")
        print(f"Download started! Video ID: {video_id}")
        
        # Monitor download progress for a few seconds
        print("\nMonitoring download progress...")
        for i in range(10):
            time.sleep(1)
            progress = get_download_progress(video_id)
            status = get_download_status(video_id)
            if status:
                print(f"Progress: {progress:.1f}% | Status: {status['status']}")
            else:
                print("Download completed or failed")
                break
        
        # Show active downloads
        print(f"\nActive downloads: {len(list_active_downloads())}")
        
        # Example of pausing and resuming (if download is still active)
        status = get_download_status(video_id)
        if status and status['status'] == 'downloading':
            print(f"\nPausing download for video ID: {video_id}")
            if pause_download(video_id):
                print("Download paused successfully")
                
                # Wait a moment
                time.sleep(2)
                
                print(f"Resuming download for video ID: {video_id}")
                if resume_download(video_id):
                    print("Download resumed successfully")
                else:
                    print("Failed to resume download")
            else:
                print("Failed to pause download")
        
        print("\n=== Example completed ===")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
