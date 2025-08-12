# dtube - YouTube Video Downloader Module

A Python module for downloading YouTube videos with pause/resume functionality using the `yt-dlp` library.

> **Note**: This downloader was created mostly by AI assistance, demonstrating the capabilities of AI-powered code generation.

## Features

- **Download videos** from YouTube URLs
- **Smart filename generation** with video title and ID (e.g., `Title_VideoID.ext`)
- **Pause downloads** at any time
- **Resume paused downloads**
- **Progress tracking** for active downloads
- **Thread-safe** download management
- **Multiple quality options** support

## Installation

The module requires Python 3.10+ and uses `pipenv` for dependency management.

```bash
# Install dependencies
pipenv install

# Or install yt-dlp directly
pip install yt-dlp

# Install ffmpeg (required for video/audio merging)
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS (using Homebrew):
brew install ffmpeg

# Windows (using Chocolatey):
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

## Quick Start

```python
from dtube import download_video, pause_download, resume_download

# Download a video
video_id = download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Pause the download
pause_download(video_id)

# Resume the download
resume_download(video_id)
```

## Filename Format

The module automatically generates descriptive filenames for downloaded videos:

**Format**: `[Video Title]_[Video ID].[extension]`

**Examples**:
- `Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)_dQw4w9WgXcQ.mp4`
- `Python Tutorial for Beginners_video123.webm`

**Features**:
- **Automatic title extraction** from YouTube metadata
- **Filesystem-safe names** with special characters replaced
- **Length limiting** to prevent extremely long filenames
- **Fallback format** uses video ID only if title extraction fails
- **Unique identification** with video ID to prevent conflicts

## API Reference

### Core Functions

#### `download_video(url, output_path="downloads", quality="best")`

Downloads a video from YouTube and returns the video ID.

**Parameters:**
- `url` (str): YouTube video URL
- `output_path` (str): Directory to save the downloaded video (default: "downloads")
- `quality` (str): Video quality preference that controls the height parameter:
  - "best" (default): 720p height
  - "worst": 144p height  
  - "720p", "480p", "360p": Specific height in pixels
  - "720", "480", "360": Direct height values
  - Any other value: Defaults to 720p height

**Returns:**
- `str`: YouTube video ID

**Raises:**
- `ValueError`: If URL is invalid or video ID cannot be extracted
- `DownloadError`: If download fails

**Example:**
```python
video_id = download_video(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_path="my_videos",
    quality="720p"
)
```

#### `pause_download(video_id)`

Pauses an active video download.

**Parameters:**
- `video_id` (str): YouTube video ID

**Returns:**
- `bool`: True if download was paused, False if not found

**Example:**
```python
if pause_download(video_id):
    print("Download paused successfully")
```

#### `resume_download(video_id)`

Resumes a paused video download.

**Parameters:**
- `video_id` (str): YouTube video ID

**Returns:**
- `bool`: True if download was resumed, False if not found

**Example:**
```python
if resume_download(video_id):
    print("Download resumed successfully")
```

### Utility Functions

#### `get_download_status(video_id)`

Get the current status of a download.

**Returns:**
- `Dict` containing download status information or `None` if not found

#### `list_active_downloads()`

Get a list of all active downloads.

**Returns:**
- `List[Dict]` of dictionaries containing download information

#### `get_download_progress(video_id)`

Get the current progress of a download as a percentage.

**Returns:**
- `float`: Download progress as percentage (0-100) or `None` if not found

#### `cancel_download(video_id)`

Cancel a download and remove it from the manager.

**Returns:**
- `bool`: True if download was cancelled, False if not found

## Usage Examples

### Basic Download

```python
from dtube import download_video

# Simple download
video_id = download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Downloading video: {video_id}")
```

### Download with Custom Settings

```python
from dtube import download_video

# Download with specific quality and output path
video_id = download_video(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_path="videos",
    quality="480p"  # Will download 480p height video
)
```

### Pause and Resume Download

```python
import time
from dtube import download_video, pause_download, resume_download
from dtube.utils import get_download_status

# Start download
video_id = download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Wait a bit for download to start
time.sleep(5)

# Pause download
if pause_download(video_id):
    print("Download paused")
    
    # Wait some time
    time.sleep(10)
    
    # Resume download
    if resume_download(video_id):
        print("Download resumed")
```

### Monitor Download Progress

```python
import time
from dtube import download_video
from dtube.utils import get_download_progress, get_download_status

# Start download
video_id = download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Monitor progress
while True:
    progress = get_download_progress(video_id)
    status = get_download_status(video_id)
    
    if not status:
        print("Download completed or failed")
        break
    
    print(f"Progress: {progress:.1f}% | Status: {status['status']}")
    time.sleep(1)
```

### Multiple Downloads

```python
from dtube import download_video
from dtube.utils import list_active_downloads

# Start multiple downloads
urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "https://www.youtube.com/watch?v=kJQP7kiw5Fk"
]

video_ids = []
for url in urls:
    video_id = download_video(url)
    video_ids.append(video_id)
    print(f"Started download: {video_id}")

# Check active downloads
active = list_active_downloads()
print(f"Active downloads: {len(active)}")
```

## Supported URL Formats

The module supports various YouTube URL formats:

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- Direct video ID strings

## Quality Options

Quality can be specified as:

- **Preset values**: 
  - `"best"` (default): 720p height
  - `"worst"`: 144p height
- **Resolution**: `"720p"`, `"480p"`, `"360p"`, etc.
- **Direct height**: `"720"`, `"480"`, `"360"`, etc.
- **Any other value**: Defaults to 720p height

The quality parameter controls the `height` value in the format string `bestvideo[height=X]+bestaudio/bestvideo+bestaudio`, ensuring consistent video quality while maintaining the best available audio.

## Error Handling

The module provides comprehensive error handling:

```python
from dtube import download_video
from yt_dlp.utils import DownloadError

try:
    video_id = download_video("https://www.youtube.com/watch?v=invalid")
except ValueError as e:
    print(f"Invalid URL: {e}")
except DownloadError as e:
    print(f"Download failed: {e}")
```

## Thread Safety

All download management operations are thread-safe, allowing you to:

- Start downloads from multiple threads
- Pause/resume downloads from different threads
- Monitor progress from any thread

## File Structure

```
dtube/
├── __init__.py          # Main module interface
├── downloader.py        # Core download functionality
├── driver.py            # Download driver for multiple concurrent downloads
└── utils.py            # Utility functions

test/                    # Comprehensive test suite
├── test_downloader.py   # Core functionality tests
├── test_driver.py       # Driver functionality tests
├── test_title_extraction.py # Title extraction tests
├── test_download_filename.py # Filename format tests
└── run_all_tests.py     # Test runner

example.py               # Usage examples
dl.py                    # Command-line interface
README.md                # This documentation
Pipfile                  # Dependencies
```

## Requirements

- Python 3.10+
- yt-dlp library
- ffmpeg (for merging video and audio streams)
- threading support (built-in)

## Testing

The module includes a comprehensive test suite:

```bash
# Run all tests
pipenv run python test/run_all_tests.py

# Run specific test modules
pipenv run python test/test_downloader.py
pipenv run python test/test_driver.py
pipenv run python test/test_title_extraction.py
pipenv run python test/test_download_filename.py
```

**Test Coverage**:
- Core download functionality
- Title extraction and filename generation
- Download driver and concurrency
- Error handling and edge cases
- All tests run under pipenv shell

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
