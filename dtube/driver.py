"""
Download driver functionality for managing multiple concurrent YouTube downloads.
"""

import os
import time
import threading
import logging
from typing import List, Dict, Optional
from queue import Queue, Empty

from .downloader import download_video
from .utils import get_download_status, get_download_progress, list_active_downloads


class DownloadDriver:
    """Manages multiple YouTube downloads with concurrency control."""
    
    def __init__(self, max_concurrent: int = 3, output_path: str = "downloads", quality: str = "best"):
        self.max_concurrent = max_concurrent
        self.output_path = output_path
        self.quality = quality
        self.wait_timeout = 60  # Default timeout in minutes
        self.download_queue = Queue()
        self.active_downloads: Dict[str, Dict] = {}
        self.completed_downloads: List[str] = []
        self.failed_downloads: List[str] = []
        self.lock = threading.Lock()
        self._shutdown_requested = False
        
        # Ensure output directory exists
        self.ensure_output_directory()
        
    def ensure_output_directory(self):
        """Ensure the output directory exists."""
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            logging.info(f"📁 Created output directory: {self.output_path}")
        
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
            logging.info(f"Starting download: {url}")
            video_id = download_video(url, self.output_path, self.quality)
            logging.info(f"✓ Download started for video ID: {video_id}")
            
            # Get the expected filename pattern from the download info
            from .downloader import _download_manager
            download_info = _download_manager.get_download(video_id)
            logging.debug(f"🔍 {video_id}: Download info: {download_info}")
            
            if download_info and download_info.get('title'):
                expected_pattern = f"{download_info['title']}_{video_id}.*"
            else:
                expected_pattern = f"{video_id}.*"
            logging.debug(f"🔍 Expected filename pattern: {expected_pattern}")
            
            return video_id
        except Exception as e:
            logging.error(f"✗ Failed to start download for {url}: {e}")
            import traceback
            logging.error(f"✗ Full traceback: {traceback.format_exc()}")
            return None
            
    def get_concurrency_status(self) -> Dict[str, int]:
        """Get current concurrency status."""
        with self.lock:
            return {
                'active_downloads': len(self.active_downloads),
                'max_concurrent': self.max_concurrent,
                'queue_size': self.download_queue.qsize(),
                'completed': len(self.completed_downloads),
                'failed': len(self.failed_downloads)
            }
    
    def log_concurrency_status(self):
        """Log current concurrency status."""
        status = self.get_concurrency_status()
        logging.debug(f"📊 Concurrency Status: {status['active_downloads']}/{status['max_concurrent']} active, "
                         f"{status['queue_size']} queued, {status['completed']} completed, {status['failed']} failed")

    def monitor_download(self, video_id: str, url: str):
        """Monitor a download until completion."""
        logging.debug(f"🔍 {video_id}: Starting download monitoring for URL: {url}")
        start_time = time.time()
        
        while True:
            status = get_download_status(video_id)
            logging.debug(f"🔍 {video_id}: Current status: {status}")
            
            if not status:
                # Download completed or failed - check if file exists to determine success
                logging.debug(f"🔍 {video_id}: Download status is None, checking file existence...")
                logging.debug(f"🔍 {video_id}: Current active downloads: {list(self.active_downloads.keys())}")
                logging.debug(f"🔍 {video_id}: Current completed downloads: {self.completed_downloads}")
                logging.debug(f"🔍 {video_id}: Current failed downloads: {self.failed_downloads}")
                
                if self.verify_download_exists(video_id):
                    logging.info(f"✅ {video_id}: Download completed successfully (file found)")
                    # Clean up any .part files for this video
                    part_files_removed = self.cleanup_part_files_for_video(video_id)
                    if part_files_removed > 0:
                        logging.info(f"🧹 {video_id}: Auto-cleaned up {part_files_removed} .part file(s)")
                    with self.lock:
                        self.completed_downloads.append(video_id)
                else:
                    logging.error(f"❌ {video_id}: Download failed (no file found)")
                    with self.lock:
                        self.failed_downloads.append(video_id)
                break
                
            progress = get_download_progress(video_id)
            elapsed = time.time() - start_time
            
            if status['status'] == 'downloading':
                logging.info(f"📥 {video_id}: {progress:.1f}% complete ({elapsed:.0f}s elapsed)")
            elif status['status'] == 'paused':
                logging.info(f"⏸️ {video_id}: Paused")
            elif status['status'] == 'error':
                error_msg = status.get('error', 'Unknown error')
                logging.error(f"❌ {video_id}: Error occurred: {error_msg}")
                with self.lock:
                    self.failed_downloads.append(video_id)
                break
            elif status['status'] == 'completed':
                logging.info(f"✅ {video_id}: Download completed successfully")
                # Clean up any .part files for this video
                part_files_removed = self.cleanup_part_files_for_video(video_id)
                if part_files_removed > 0:
                    logging.info(f"🧹 {video_id}: Auto-cleaned up {part_files_removed} .part file(s)")
                with self.lock:
                    self.completed_downloads.append(video_id)
                break
            else:
                logging.warning(f"🔍 {video_id}: Unknown status: {status['status']}")
                
            logging.debug(f"🔍 {video_id}: Current status: {status}")
            
            # Log concurrency status periodically
            if int(elapsed) % 10 == 0:  # Every 10 seconds
                self.log_concurrency_status()
            
            time.sleep(2)  # Update every 2 seconds
            
        # Remove from active downloads
        with self.lock:
            if video_id in self.active_downloads:
                del self.active_downloads[video_id]
                logging.debug(f"🔍 {video_id}: Removed from active downloads. "
                                f"Current active: {len(self.active_downloads)}/{self.max_concurrent}")
                
    def download_worker(self):
        """Worker thread that processes downloads from the queue."""
        logging.debug(f"🔧 Download worker thread {threading.current_thread().name} started")
        
        while True:
            try:
                # Get URL from queue with timeout
                url = self.download_queue.get(timeout=1)
                logging.debug(f"🔧 Worker {threading.current_thread().name}: Processing URL: {url}")
                
                # Wait until we can start a new download (respect max_concurrent limit)
                # Use a single lock acquisition to make the check and start atomic
                while True:
                    with self.lock:
                        if len(self.active_downloads) < self.max_concurrent:
                            # We can start a download, so start it immediately while holding the lock
                            video_id = self.start_download(url)
                            if video_id:
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
                            break
                    # If we couldn't start a download, wait a bit before checking again
                    time.sleep(0.1)
                
                self.download_queue.task_done()
                
            except Empty:
                # No more URLs in queue - check if we should keep waiting
                # For batch mode, we want workers to stay alive until explicitly told to stop
                if hasattr(self, '_shutdown_requested') and self._shutdown_requested:
                    logging.debug(f"🔧 Worker {threading.current_thread().name}: Shutdown requested, exiting")
                    break
                else:
                    # Keep waiting for more URLs (useful for batch mode)
                    logging.debug(f"🔧 Worker {threading.current_thread().name}: Queue empty, waiting for more URLs...")
                    time.sleep(0.5)  # Wait a bit before checking again
                    continue
            except Exception as e:
                logging.error(f"Error in download worker: {e}")
                self.download_queue.task_done()
        
        logging.debug(f"🔧 Download worker thread {threading.current_thread().name} finished")

    def verify_download_exists(self, video_id: str, retry_count: int = 3) -> bool:
        """Verify that a downloaded file actually exists in the output directory."""
        # Check if any file with the video_id exists in the output directory
        if not os.path.exists(self.output_path):
            logging.debug(f"🔍 {video_id}: Output directory {self.output_path} does not exist")
            return False
        
        for attempt in range(retry_count):
            logging.debug(f"🔍 {video_id}: Checking output directory '{self.output_path}' (attempt {attempt + 1})")
            logging.debug(f"🔍 {video_id}: Looking for files containing '{video_id}'")
            all_files = os.listdir(self.output_path)
            logging.debug(f"🔍 {video_id}: All files in directory: {all_files}")
            
            # Look for files that contain the video_id (either as title_video_id.ext or just video_id.ext)
            # Exclude .part files as they indicate incomplete downloads
            for filename in all_files:
                if video_id in filename:
                    if filename.endswith('.part'):
                        logging.debug(f"🔍 {video_id}: Found .part file {filename} - excluding from completion check")
                        continue
                    
                    file_path = os.path.join(self.output_path, filename)
                    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                        file_ext = os.path.splitext(filename)[1]
                        logging.debug(f"🔍 {video_id}: Found file {filename} with size {os.path.getsize(file_path)} bytes (extension: {file_ext})")
                        return True
                    else:
                        logging.debug(f"🔍 {video_id}: Found file {filename} but it's not a valid file or is empty")
            
            if attempt < retry_count - 1:
                logging.debug(f"🔍 {video_id}: No file found on attempt {attempt + 1}, retrying in 1 second...")
                time.sleep(1)
        
        logging.debug(f"🔍 {video_id}: No file containing '{video_id}' found in {self.output_path} after {retry_count} attempts")
        return False

    def cleanup_part_files(self) -> int:
        """
        Clean up any .part files in the output directory that indicate incomplete downloads.
        
        Returns:
            int: Number of .part files removed
        """
        if not os.path.exists(self.output_path):
            return 0
        
        removed_count = 0
        all_files = os.listdir(self.output_path)
        
        for filename in all_files:
            if filename.endswith('.part'):
                file_path = os.path.join(self.output_path, filename)
                try:
                    os.remove(file_path)
                    logging.info(f"🧹 Cleaned up incomplete download: {filename}")
                    removed_count += 1
                except OSError as e:
                    logging.warning(f"⚠️  Failed to remove .part file {filename}: {e}")
        
        if removed_count > 0:
            logging.info(f"🧹 Cleaned up {removed_count} incomplete download(s)")
        
        return removed_count

    def cleanup_part_files_for_video(self, video_id: str) -> int:
        """
        Clean up .part files for a specific video ID.
        
        Args:
            video_id: YouTube video ID to clean up .part files for
            
        Returns:
            int: Number of .part files removed for this video
        """
        if not os.path.exists(self.output_path):
            return 0
        
        removed_count = 0
        all_files = os.listdir(self.output_path)
        
        for filename in all_files:
            if filename.endswith('.part') and video_id in filename:
                file_path = os.path.join(self.output_path, filename)
                try:
                    os.remove(file_path)
                    logging.debug(f"🧹 {video_id}: Cleaned up .part file: {filename}")
                    removed_count += 1
                except OSError as e:
                    logging.warning(f"⚠️  {video_id}: Failed to remove .part file {filename}: {e}")
        
        if removed_count > 0:
            logging.info(f"🧹 {video_id}: Cleaned up {removed_count} .part file(s)")
        
        return removed_count

    def wait_for_all_downloads(self, timeout_minutes: int = 60):
        """Wait for all active downloads to complete."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while self.active_downloads:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logging.warning(f"⏰ Timeout reached after {timeout_minutes} minutes")
                logging.warning(f"⚠️  {len(self.active_downloads)} downloads still in progress:")
                for video_id in self.active_downloads:
                    logging.warning(f"   • {video_id}")
                break
                
            # Log concurrency status every 30 seconds
            if int(elapsed) % 30 == 0:
                self.log_concurrency_status()
            
            logging.debug(f"⏳ Waiting for {len(self.active_downloads)} active downloads to complete... (elapsed: {elapsed/60:.1f}m)")
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
                        logging.warning(f"⚠️  {video_id}: Status shows completed but file not found, continuing to wait...")
            
            # Remove completed downloads
            for video_id in completed_ids:
                if video_id in self.active_downloads:
                    del self.active_downloads[video_id]
                    # Only add to completed_downloads if not already there
                    if video_id not in self.completed_downloads:
                        self.completed_downloads.append(video_id)
                    logging.debug(f"✅ {video_id}: Download completed and removed from active. "
                                    f"Current active: {len(self.active_downloads)}/{self.max_concurrent}")
        
        if not self.active_downloads:
            logging.info("✅ All downloads completed!")
        else:
            logging.warning("⚠️  Some downloads may still be in progress")

    def run(self):
        """Run the download driver."""
        logging.info(f"🚀 Starting download driver with max {self.max_concurrent} concurrent downloads")
        logging.info(f"📁 Output directory: {self.output_path}")
        logging.info(f"🎥 Quality: {self.quality}")
        logging.info(f"📋 Queue size: {self.download_queue.qsize()} URLs")
        logging.info("-" * 60)
        
        # Start worker threads
        logging.info(f"🔧 Starting {self.max_concurrent} download worker threads...")
        workers = []
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self.download_worker, daemon=True, name=f"Worker-{i+1}")
            worker.start()
            workers.append(worker)
            logging.debug(f"🔧 Started worker thread {worker.name}")
            
        # Wait for all downloads to complete
        logging.debug("⏳ Waiting for download queue to empty...")
        self.download_queue.join()
        logging.debug("✅ Download queue is empty")
        
        # Wait for all active downloads to actually complete
        logging.debug("⏳ Waiting for all active downloads to complete...")
        self.wait_for_all_downloads(timeout_minutes=self.wait_timeout)
        
        # Signal workers to shutdown
        logging.debug("🔧 Signaling workers to shutdown...")
        self._shutdown_requested = True
        
        # Give workers a moment to see the shutdown signal
        time.sleep(1)
        
        # Wait for workers to finish
        logging.debug("⏳ Waiting for worker threads to finish...")
        for worker in workers:
            worker.join(timeout=5)
            logging.debug(f"🔧 Worker thread {worker.name} finished")
            
        # Final cleanup of any remaining .part files from current execution
        final_part_files_removed = self.cleanup_part_files()
        if final_part_files_removed > 0:
            logging.info(f"🧹 Final cleanup: Removed {final_part_files_removed} remaining .part file(s)")
        
        # Print final summary
        logging.info("📊 Generating download summary...")
        self.print_summary()
        logging.info("🏁 Download driver finished")
        
    def print_summary(self):
        """Print a summary of all downloads."""
        logging.info("\n" + "=" * 60)
        logging.info("📊 DOWNLOAD SUMMARY")
        logging.info("=" * 60)
        logging.info(f"✅ Completed: {len(self.completed_downloads)}")
        logging.info(f"❌ Failed: {len(self.failed_downloads)}")
        logging.info(f"📁 Output directory: {self.output_path}")
        
        if self.completed_downloads:
            logging.info("\n✅ Successfully downloaded:")
            for video_id in self.completed_downloads:
                if self.verify_download_exists(video_id):
                    logging.info(f"   • {video_id} ✓ (file exists)")
                else:
                    logging.warning(f"   • {video_id} ⚠️ (file missing)")
                    
        if self.failed_downloads:
            logging.info("\n❌ Failed downloads:")
            for video_id in self.failed_downloads:
                logging.info(f"   • {video_id}")
                
        # List actual files in output directory
        if os.path.exists(self.output_path):
            actual_files = [f for f in os.listdir(self.output_path) if os.path.isfile(os.path.join(self.output_path, f))]
            if actual_files:
                logging.debug(f"\n📁 Files in output directory ({len(actual_files)}):")
                for filename in actual_files:
                    file_path = os.path.join(self.output_path, filename)
                    size = os.path.getsize(file_path)
                    logging.debug(f"   • {filename} ({size} bytes)")
            else:
                logging.debug("\n📁 Output directory is empty")
        else:
            logging.debug("\n📁 Output directory does not exist")
                
        logging.info("=" * 60)
