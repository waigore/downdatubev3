#!/usr/bin/env python3
"""
YouTube Download Driver Script

Usage: python dl.py [options] <url1> <url2> <url3> ...

Downloads multiple YouTube videos with configurable concurrency limits.
"""

import argparse
import sys
import time
import threading
import os
import logging
from typing import List, Dict, Optional
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed

from dtube import download_video, pause_download, resume_download
from dtube.utils import get_download_status, get_download_progress, list_active_downloads


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging configuration."""
    # Create logger
    logger = logging.getLogger("dtube_downloader")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Create formatter and add it to the handler
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(console_handler)
    
    return logger


class DownloadDriver:
    """Manages multiple YouTube downloads with concurrency control."""
    
    def __init__(self, max_concurrent: int = 3, output_path: str = "downloads", quality: str = "best", logger: logging.Logger = None):
        self.max_concurrent = max_concurrent
        self.output_path = output_path
        self.quality = quality
        self.wait_timeout = 60  # Default timeout in minutes
        self.download_queue = Queue()
        self.active_downloads: Dict[str, Dict] = {}
        self.completed_downloads: List[str] = []
        self.failed_downloads: List[str] = []
        self.lock = threading.Lock()
        self.logger = logger or logging.getLogger("dtube_downloader")
        
        # Ensure output directory exists
        self.ensure_output_directory()
        
    def ensure_output_directory(self):
        """Ensure the output directory exists."""
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            self.logger.info(f"📁 Created output directory: {self.output_path}")
        
    def add_url(self, url: str):
        """Add a URL to the download queue."""
        self.download_queue.put(url)
        
    def add_urls(self, urls: List[str]):
        """Add multiple URLs to the download queue."""
        for url in urls:
            self.download_queue.put(url)
            
    def start_download(self, url: str) -> Optional[str]:
        """Start a single download and return the video ID."""
        try:
            self.logger.info(f"Starting download: {url}")
            video_id = download_video(url, self.output_path, self.quality)
            self.logger.info(f"✓ Download started for video ID: {video_id}")
            self.logger.debug(f"🔍 Expected filename pattern: {video_id}.*")
            return video_id
        except Exception as e:
            self.logger.error(f"✗ Failed to start download for {url}: {e}")
            return None
            
    def monitor_download(self, video_id: str, url: str):
        """Monitor a download until completion."""
        self.logger.debug(f"🔍 {video_id}: Starting download monitoring for URL: {url}")
        start_time = time.time()
        
        while True:
            status = get_download_status(video_id)
            if not status:
                # Download completed or failed - check if file exists to determine success
                self.logger.debug(f"🔍 {video_id}: Download status is None, checking file existence...")
                self.logger.debug(f"🔍 {video_id}: Current active downloads: {list(self.active_downloads.keys())}")
                self.logger.debug(f"🔍 {video_id}: Current completed downloads: {self.completed_downloads}")
                self.logger.debug(f"🔍 {video_id}: Current failed downloads: {self.failed_downloads}")
                
                if self.verify_download_exists(video_id):
                    self.logger.info(f"✅ {video_id}: Download completed successfully (file found)")
                    with self.lock:
                        self.completed_downloads.append(video_id)
                else:
                    self.logger.error(f"❌ {video_id}: Download failed (no file found)")
                    with self.lock:
                        self.failed_downloads.append(video_id)
                break
                
            progress = get_download_progress(video_id)
            elapsed = time.time() - start_time
            
            if status['status'] == 'downloading':
                self.logger.info(f"📥 {video_id}: {progress:.1f}% complete ({elapsed:.0f}s elapsed)")
            elif status['status'] == 'paused':
                self.logger.info(f"⏸️  {video_id}: Paused")
            elif status['status'] == 'error':
                self.logger.error(f"❌ {video_id}: Error occurred")
                with self.lock:
                    self.failed_downloads.append(video_id)
                break
            elif status['status'] == 'completed':
                self.logger.info(f"✅ {video_id}: Download completed successfully")
                with self.lock:
                    self.completed_downloads.append(video_id)
                break
            else:
                self.logger.warning(f"🔍 {video_id}: Unknown status: {status['status']}")
                
            self.logger.debug(f"🔍 {video_id}: Current status: {status}")
            
            time.sleep(2)  # Update every 2 seconds
            
        # Remove from active downloads
        with self.lock:
            if video_id in self.active_downloads:
                del self.active_downloads[video_id]
                
    def download_worker(self):
        """Worker thread that processes downloads from the queue."""
        self.logger.debug(f"🔧 Download worker thread {threading.current_thread().name} started")
        while True:
            try:
                # Get URL from queue with timeout
                url = self.download_queue.get(timeout=1)
                self.logger.debug(f"🔧 Worker {threading.current_thread().name}: Processing URL: {url}")
                
                # Check if we can start a new download
                while len(self.active_downloads) >= self.max_concurrent:
                    time.sleep(1)
                    
                # Start the download
                video_id = self.start_download(url)
                if video_id:
                    with self.lock:
                        self.active_downloads[video_id] = {
                            'url': url,
                            'start_time': time.time()
                        }
                    
                    # Start monitoring in a separate thread
                    monitor_thread = threading.Thread(
                        target=self.monitor_download,
                        args=(video_id, url),
                        daemon=True
                    )
                    monitor_thread.start()
                    
                self.download_queue.task_done()
                
            except Empty:
                # No more URLs in queue
                self.logger.debug(f"🔧 Worker {threading.current_thread().name}: No more URLs, exiting")
                break
            except Exception as e:
                self.logger.error(f"Error in download worker: {e}")
                self.download_queue.task_done()
        
        self.logger.debug(f"🔧 Download worker thread {threading.current_thread().name} finished")

    def verify_download_exists(self, video_id: str, retry_count: int = 3) -> bool:
        """Verify that a downloaded file actually exists in the output directory."""
        # Check if any file with the video_id exists in the output directory
        if not os.path.exists(self.output_path):
            self.logger.debug(f"🔍 {video_id}: Output directory {self.output_path} does not exist")
            return False
        
        for attempt in range(retry_count):
            self.logger.debug(f"🔍 {video_id}: Checking output directory '{self.output_path}' (attempt {attempt + 1})")
            self.logger.debug(f"🔍 {video_id}: Looking for files containing '{video_id}'")
            all_files = os.listdir(self.output_path)
            self.logger.debug(f"🔍 {video_id}: All files in directory: {all_files}")
            
            for filename in all_files:
                if video_id in filename:
                    file_path = os.path.join(self.output_path, filename)
                    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                        file_ext = os.path.splitext(filename)[1]
                        self.logger.debug(f"🔍 {video_id}: Found file {filename} with size {os.path.getsize(file_path)} bytes (extension: {file_ext})")
                        return True
                    else:
                        self.logger.debug(f"🔍 {video_id}: Found file {filename} but it's not a valid file or is empty")
            
            if attempt < retry_count - 1:
                self.logger.debug(f"🔍 {video_id}: No file found on attempt {attempt + 1}, retrying in 1 second...")
                time.sleep(1)
        
        self.logger.debug(f"🔍 {video_id}: No file containing '{video_id}' found in {self.output_path} after {retry_count} attempts")
        return False

    def wait_for_all_downloads(self, timeout_minutes: int = 60):
        """Wait for all active downloads to complete."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while self.active_downloads:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                self.logger.warning(f"⏰ Timeout reached after {timeout_minutes} minutes")
                self.logger.warning(f"⚠️  {len(self.active_downloads)} downloads still in progress:")
                for video_id in self.active_downloads:
                    self.logger.warning(f"   • {video_id}")
                break
                
            self.logger.debug(f"⏳ Waiting for {len(self.active_downloads)} active downloads to complete... (elapsed: {elapsed/60:.1f}m)")
            time.sleep(5)  # Check every 5 seconds
            
            # Check if any downloads have completed
            completed_ids = []
            for video_id in list(self.active_downloads.keys()):
                status = get_download_status(video_id)
                if not status or status.get('status') == 'completed':
                    # Double-check that the file actually exists
                    if self.verify_download_exists(video_id):
                        completed_ids.append(video_id)
                    else:
                        self.logger.warning(f"⚠️  {video_id}: Status shows completed but file not found, continuing to wait...")
            
            # Remove completed downloads
            for video_id in completed_ids:
                if video_id in self.active_downloads:
                    del self.active_downloads[video_id]
                    # Only add to completed_downloads if not already there
                    if video_id not in self.completed_downloads:
                        self.completed_downloads.append(video_id)
        
        if not self.active_downloads:
            self.logger.info("✅ All downloads completed!")
        else:
            self.logger.warning("⚠️  Some downloads may still be in progress")

    def run(self):
        """Run the download driver."""
        self.logger.info(f"🚀 Starting download driver with max {self.max_concurrent} concurrent downloads")
        self.logger.info(f"📁 Output directory: {self.output_path}")
        self.logger.info(f"🎥 Quality: {self.quality}")
        self.logger.info(f"📋 Queue size: {self.download_queue.qsize()} URLs")
        self.logger.info("-" * 60)
        
        # Start worker threads
        self.logger.info("🔧 Starting download worker threads...")
        workers = []
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self.download_worker, daemon=True)
            worker.start()
            workers.append(worker)
            self.logger.debug(f"🔧 Started worker thread {worker.name}")
            
        # Wait for all downloads to complete
        self.logger.debug("⏳ Waiting for download queue to empty...")
        self.download_queue.join()
        self.logger.debug("✅ Download queue is empty")
        
        # Wait for all active downloads to actually complete
        self.logger.debug("⏳ Waiting for all active downloads to complete...")
        self.wait_for_all_downloads(timeout_minutes=self.wait_timeout)
        
        # Wait for workers to finish
        self.logger.debug("🔧 Waiting for worker threads to finish...")
        for worker in workers:
            worker.join(timeout=5)
            self.logger.debug(f"🔧 Worker thread {worker.name} finished")
            
        # Print final summary
        self.logger.info("📊 Generating download summary...")
        self.print_summary()
        self.logger.info("🏁 Download driver finished")
        
    def print_summary(self):
        """Print a summary of all downloads."""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 DOWNLOAD SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Completed: {len(self.completed_downloads)}")
        self.logger.info(f"❌ Failed: {len(self.failed_downloads)}")
        self.logger.info(f"📁 Output directory: {self.output_path}")
        
        if self.completed_downloads:
            self.logger.info("\n✅ Successfully downloaded:")
            for video_id in self.completed_downloads:
                if self.verify_download_exists(video_id):
                    self.logger.info(f"   • {video_id} ✓ (file exists)")
                else:
                    self.logger.warning(f"   • {video_id} ⚠️ (file missing)")
                    
        if self.failed_downloads:
            self.logger.info("\n❌ Failed downloads:")
            for video_id in self.failed_downloads:
                self.logger.info(f"   • {video_id}")
                
        # List actual files in output directory
        if os.path.exists(self.output_path):
            actual_files = [f for f in os.listdir(self.output_path) if os.path.isfile(os.path.join(self.output_path, f))]
            if actual_files:
                self.logger.debug(f"\n📁 Files in output directory ({len(actual_files)}):")
                for filename in actual_files:
                    file_path = os.path.join(self.output_path, filename)
                    size = os.path.getsize(file_path)
                    self.logger.debug(f"   • {filename} ({size} bytes)")
            else:
                self.logger.debug("\n📁 Output directory is empty")
        else:
            self.logger.warning("\n📁 Output directory does not exist")
                
        self.logger.info("=" * 60)


def main():
    """Main function to parse arguments and run the download driver."""
    parser = argparse.ArgumentParser(
        description="Download multiple YouTube videos with concurrency control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dl.py https://youtube.com/watch?v=VIDEO1
  python dl.py -c 5 -q 720p https://youtube.com/watch?v=VIDEO1 https://youtube.com/watch?v=VIDEO2
  python dl.py -o videos -q best -t 120 video1 video2 video3
        """
    )
    
    parser.add_argument(
        'urls',
        nargs='+',
        help='YouTube URLs or video IDs to download'
    )
    
    parser.add_argument(
        '-c', '--concurrent',
        type=int,
        default=3,
        help='Maximum number of simultaneous downloads (default: 3)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='downloads',
        help='Output directory for downloaded videos (default: downloads)'
    )
    
    parser.add_argument(
        '-q', '--quality',
        default='best',
        help='Video quality preference (default: best)'
    )
    
    parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=60,
        help='Timeout in minutes for waiting for downloads to complete (default: 60)'
    )
    
    parser.add_argument(
        '-l', '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    # Validate arguments
    if args.concurrent < 1:
        logger.error("Error: Concurrent downloads must be at least 1")
        sys.exit(1)
        
    if args.concurrent > 10:
        logger.warning("Warning: High concurrency may cause rate limiting")
        
    # Create and run download driver
    driver = DownloadDriver(
        max_concurrent=args.concurrent,
        output_path=args.output,
        quality=args.quality,
        logger=logger
    )
    
    # Add URLs to queue
    driver.add_urls(args.urls)
    
    try:
        # Set timeout for waiting for downloads
        driver.wait_timeout = args.timeout
        driver.run()
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Download interrupted by user")
        logger.info("Active downloads will continue to completion")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
