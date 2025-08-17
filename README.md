# DownDaTube v3

A robust YouTube downloader with concurrency control, progress tracking, intelligent format selection, and advanced download management.

## Features

- **Concurrent Downloads**: Download multiple videos simultaneously with configurable limits
- **Smart Format Selection**: Automatically selects the best quality while ensuring audio is included
- **Progress Tracking**: Real-time download progress monitoring with detailed status updates
- **Batch Processing**: Download from text files containing multiple URLs
- **Audio Verification**: Detect and fix videos downloaded without audio
- **Resume Support**: Automatically resume interrupted downloads
- **Quality Control**: Configurable video quality preferences with intelligent fallbacks
- **Comprehensive Logging**: Detailed logging with configurable levels and emoji indicators
- **Download Management**: Monitor active downloads and progress
- **Download Utilities**: Check for incomplete downloads

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd downdatubev3
```

2. Install dependencies using pipenv:
```bash
pipenv install
```

3. Activate the virtual environment:
```bash
pipenv shell
```

## Usage

### Basic Download

Download a single video:
```bash
python dl.py https://youtube.com/watch?v=VIDEO_ID
```

### Multiple Downloads

Download multiple videos with concurrency control:
```bash
python dl.py -c 5 -q 720p https://youtube.com/watch?v=VIDEO1 https://youtube.com/watch?v=VIDEO2
```

### Batch Downloads

Download from a text file containing URLs:
```bash
python dl.py -b urls.txt -c 3 -q best
```

### Quality Options

- `best` (default): 720p height with MP4 format
- `worst`: 144p height
- `720p`, `480p`, `360p`: Specific height in pixels
- `720`, `480`, `360`: Direct height values

### Advanced Features

#### Download Management
Check download status and progress:
```bash
# Check for incomplete downloads (.part files)
python dl.py --check-parts
```

#### Audio Issues and Fixes

##### Problem
Some videos may be downloaded without audio tracks. This typically happens when:
- YouTube serves video and audio as separate streams
- The downloader selects a video-only format
- Audio merging fails during post-processing

##### Detection
Check for videos without audio:
```bash
python dl.py --check-audio
```

##### Solution
The updated downloader now:
1. **Prioritizes formats with both video and audio** using intelligent format selection
2. **Uses improved format selection** to avoid video-only streams
3. **Ensures proper audio merging** during download with FFmpeg
4. **Provides redownload functionality** for problematic videos
5. **Implements smart fallbacks** for quality selection

To fix a video without audio:
```bash
# Redownload with audio
python dl.py https://youtube.com/watch?v=VIDEO_ID
```

### Other Options

Check for incomplete downloads:
```bash
python dl.py --check-parts
```

Set custom output directory:
```bash
python dl.py -o /path/to/output https://youtube.com/watch?v=VIDEO_ID
```

Set download timeout:
```bash
python dl.py -t 120 https://youtube.com/watch?v=VIDEO_ID
```

Set logging level:
```bash
python dl.py -l DEBUG https://youtube.com/watch?v=VIDEO_ID
```

## Configuration

### Concurrency Limits
- **Default**: 3 concurrent downloads
- **Range**: 1-10 (higher values may cause rate limiting)
- **Recommendation**: 3-5 for most users

### Quality Settings
- **best**: 720p MP4 (good balance of quality and file size)
- **720p**: 1280x720 resolution
- **480p**: 854x480 resolution
- **360p**: 640x360 resolution

### Format Selection Strategy
The downloader uses intelligent format selection:
1. **Primary**: 720p+ formats with video+audio in MP4
2. **Fallback**: 480p+ formats with video+audio
3. **Last resort**: Best available quality with proper audio merging

## Troubleshooting

### Common Issues

1. **Videos without audio**
   - Use `python dl.py --check-audio` to identify problematic videos
   - Redownload using the updated downloader
   - The new format selection ensures audio is included

2. **Incomplete downloads (.part files)**
   - Use `python dl.py --check-parts` to identify incomplete downloads
   - .part files are automatically cleaned up during downloads
   - Interrupted downloads can be resumed

3. **Rate limiting**
   - Reduce concurrency with `-c` flag
   - Use lower quality settings
   - Add delays between batch downloads

4. **Format selection issues**
   - Check logs for format selection details
   - Verify FFmpeg installation for audio merging

### Logging

Set log level for debugging:
```bash
python dl.py -l DEBUG https://youtube.com/watch?v=VIDEO_ID
```

Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

The logger provides emoji indicators for better readability:
- 🔧 Configuration and setup
- 📥 Download progress
- ✅ Completion
- ❌ Errors
- ⚠️ Warnings

## Technical Details

### Format Selection
The downloader uses intelligent format selection:
1. **Primary**: Formats with both video and audio at requested quality
2. **Fallback**: Separate video + audio streams with proper merging
3. **Last resort**: Best available format

### Audio Handling
- **Format**: MP4 with M4A audio (best compatibility)
- **Quality**: Best available audio
- **Merging**: Automatic using FFmpeg
- **Verification**: Audio track presence detection

### Download Management
- **Threading**: Separate threads for each download
- **Progress**: Real-time progress tracking with percentage
- **Status**: Comprehensive download state management
- **Cleanup**: Automatic .part file cleanup

### URL Support
Supports multiple YouTube URL formats:
- `https://youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/embed/VIDEO_ID`
- Direct video IDs

## Examples

### Download Sports Highlights
```bash
python dl.py -q 720p -c 2 \
  "https://youtube.com/watch?v=VIDEO1" \
  "https://youtube.com/watch?v=VIDEO2"
```

### Batch Download Tutorial Series
```bash
# Create urls.txt with tutorial URLs
echo "https://youtube.com/watch?v=TUTORIAL1" > urls.txt
echo "https://youtube.com/watch?v=TUTORIAL2" >> urls.txt

# Download with 3 concurrent downloads
python dl.py -b urls.txt -c 3 -q best
```

### Check and Fix Audio Issues
```bash
# Check for videos without audio
python dl.py --check-audio

# Fix a specific video
python dl.py "https://youtube.com/watch?v=PROBLEMATIC_VIDEO"
```



### Monitor Downloads
```bash
# Check for incomplete downloads
python dl.py --check-parts
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading
- Uses [FFmpeg](https://ffmpeg.org/) for audio/video processing
- Inspired by the need for reliable YouTube downloads with audio
- Enhanced with intelligent format selection and progress tracking
