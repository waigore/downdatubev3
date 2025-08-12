#!/usr/bin/env python3
"""
YouTube Download Driver Script

Usage: python dl.py [options] <url1> <url2> <url3> ...

Downloads multiple YouTube videos with configurable concurrency limits.
"""

import argparse
import sys
import logging

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
