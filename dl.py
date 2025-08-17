#!/usr/bin/env python3
"""
YouTube Download Driver Script

Usage: python dl.py [options] <url1> <url2> <url3> ...

Downloads multiple YouTube videos with configurable concurrency limits.
"""

import argparse
import sys
import logging
import os

from dtube import DownloadDriver


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
  python dl.py -b urls.txt -c 3 -q 720p
  python dl.py --batch playlist.txt --concurrent 2 --quality best
  python dl.py --check-parts  # Check for incomplete downloads

Note: .part files are automatically cleaned up during and after downloads, but startup cleanup is disabled to allow resumption of interrupted downloads.
        """
    )
    
    parser.add_argument(
        'urls',
        nargs='*',  # Make URLs optional (0 or more)
        help='YouTube URLs or video IDs to download (not used when --batch is specified)'
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
        '-b', '--batch',
        type=str,
        help='Text file containing YouTube URLs, one per line (batch mode)'
    )
    
    parser.add_argument(
        '--check-parts',
        action='store_true',
        help='Check for .part files and exit without downloading'
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
    
    # Handle cleanup and check-parts options first
    if args.check_parts:
        from dtube.utils import check_for_part_files
        part_files = check_for_part_files(args.output)
        if part_files:
            logger.warning(f"⚠️  Found {len(part_files)} incomplete download(s) in '{args.output}':")
            for part_file in part_files:
                logger.warning(f"   • {part_file}")
            logger.info("Use --cleanup to remove these files")
        else:
            logger.info(f"✅ No incomplete downloads found in '{args.output}'")
        sys.exit(0)
    
    # Handle batch mode vs command-line URLs
    urls_to_download = []
    
    if args.batch:
        # Batch mode: read URLs from file
        if not os.path.exists(args.batch):
            logger.error(f"Error: Batch file '{args.batch}' does not exist")
            sys.exit(1)
            
        # Read the file content
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"Error reading batch file '{args.batch}': {e}")
            sys.exit(1)
            
        # Parse URLs from file content
        urls_to_download = [line.strip() for line in file_content.split('\n') if line.strip()]
        
        if not urls_to_download:
            logger.error(f"Error: Batch file '{args.batch}' is empty or contains no valid URLs")
            sys.exit(1)
            
        logger.info(f"📁 Batch mode: Loaded {len(urls_to_download)} URLs from '{args.batch}'")
        
        # Validate URLs (basic check) and filter invalid ones
        valid_urls = []
        invalid_urls = []
        
        for url in urls_to_download:
            if url.startswith(('http://', 'https://')):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if invalid_urls:
            logger.warning(f"⚠️  Warning: {len(invalid_urls)} URLs in batch file may not be valid HTTP/HTTPS URLs")
            logger.debug(f"   Invalid URLs: {invalid_urls[:5]}{'...' if len(invalid_urls) > 5 else ''}")
        
        # Use only valid URLs
        urls_to_download = valid_urls
        
        if not urls_to_download:
            logger.error(f"Error: No valid URLs found in batch file '{args.batch}'")
            sys.exit(1)
    else:
        # Command-line mode: use URLs from arguments
        urls_to_download = args.urls
        
        if not urls_to_download:
            logger.error("Error: No URLs provided. Use --batch <file> or provide URLs as arguments.")
            sys.exit(1)
    
    # Create and run download driver
    driver = DownloadDriver(
        max_concurrent=args.concurrent,
        output_path=args.output,
        quality=args.quality
    )
    
    # Add URLs to queue
    driver.add_urls(urls_to_download)
    
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
