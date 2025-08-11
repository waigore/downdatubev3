# dtube - YouTube Video Downloader Module

A Python module for downloading YouTube videos with pause/resume functionality using the `yt-dlp` library.

> **Note**: This downloader was created mostly by AI assistance, demonstrating the capabilities of AI-powered code generation.

## Features

- **Download videos** from YouTube URLs
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

## API Reference

### Core Functions

#### `download_video(url, output_path="downloads", quality="best")`

Downloads a video from YouTube and returns the video ID.

**Parameters:**
- `url` (str): YouTube video URL
- `output_path` (str): Directory to save the downloaded video (default: "downloads")
- `quality` (str): Video quality preference (default: "best")

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
    quality="480p"
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

- **Preset values**: `"best"`, `"worst"`
- **Resolution**: `"720p"`, `"480p"`, `"360p"`, etc.
- **Format codes**: `"137"`, `"136"`, etc.

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
└── utils.py            # Utility functions

example.py               # Usage examples
README.md               # This documentation
Pipfile                 # Dependencies
```

## Requirements

- Python 3.10+
- yt-dlp library
- threading support (built-in)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
