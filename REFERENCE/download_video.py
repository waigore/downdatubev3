#!/usr/bin/env python3
"""
Python script equivalent to the yt-dlp command:
yt-dlp -f "bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]/bestvideo[height>=720]+bestaudio" https://www.youtube.com/watch?v=hvq3gK6ta9U

This script demonstrates how to use the yt-dlp Python API to download videos with custom format selection.
"""

import yt_dlp
import sys


def main():
    # The URL to download
    url = "https://www.youtube.com/watch?v=hvq3gK6ta9U"
    
    # Format selection equivalent to the command line format string
    # This replicates: "bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]/bestvideo[height>=720]+bestaudio"
    def format_selector(ctx):
        """
        Custom format selector that replicates the command line format string.
        
        The format string breaks down as:
        1. bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]  (first choice)
        2. / (alternative choice)
        3. bestvideo[height>=720]+bestaudio  (fallback choice)
        """
        formats = ctx.get('formats', [])
        
        # First choice: bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]
        try:
            # Find best video with height=720 and ext=mp4
            video_720_mp4 = None
            for f in formats:
                if (f.get('vcodec') != 'none' and 
                    f.get('acodec') == 'none' and  # video-only
                    f.get('height') == 720 and 
                    f.get('ext') == 'mp4'):
                    if video_720_mp4 is None or f.get('filesize', 0) > video_720_mp4.get('filesize', 0):
                        video_720_mp4 = f
            
            # Find best audio with acodec starting with mp4a
            audio_mp4a = None
            for f in formats:
                if (f.get('acodec') != 'none' and 
                    f.get('vcodec') == 'none' and  # audio-only
                    f.get('acodec', '').startswith('mp4a')):
                    if audio_mp4a is None or f.get('filesize', 0) > audio_mp4a.get('filesize', 0):
                        audio_mp4a = f
            
            # If we found both, yield the merged format
            if video_720_mp4 and audio_mp4a:
                yield {
                    'format_id': f'{video_720_mp4["format_id"]}+{audio_mp4a["format_id"]}',
                    'ext': 'mp4',
                    'requested_formats': [video_720_mp4, audio_mp4a],
                    'protocol': f'{video_720_mp4.get("protocol", "http")}+{audio_mp4a.get("protocol", "http")}'
                }
                return
        except Exception as e:
            print(f"Error in first format choice: {e}")
        
        # Fallback choice: bestvideo[height>=720]+bestaudio
        try:
            # Find best video with height >= 720
            video_720_plus = None
            for f in formats:
                if (f.get('vcodec') != 'none' and 
                    f.get('acodec') == 'none' and  # video-only
                    f.get('height', 0) >= 720):
                    if video_720_plus is None or f.get('filesize', 0) > video_720_plus.get('filesize', 0):
                        video_720_plus = f
            
            # Find best audio
            best_audio = None
            for f in formats:
                if (f.get('acodec') != 'none' and 
                    f.get('vcodec') == 'none'):  # audio-only
                    if best_audio is None or f.get('filesize', 0) > best_audio.get('filesize', 0):
                        best_audio = f
            
            # If we found both, yield the merged format
            if video_720_plus and best_audio:
                yield {
                    'format_id': f'{video_720_plus["format_id"]}+{best_audio["format_id"]}',
                    'ext': video_720_plus.get('ext', 'mp4'),
                    'requested_formats': [video_720_plus, best_audio],
                    'protocol': f'{video_720_plus.get("protocol", "http")}+{best_audio.get("protocol", "http")}'
                }
                return
        except Exception as e:
            print(f"Error in fallback format choice: {e}")
        
        # If all else fails, yield the best available format
        best_format = None
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                if best_format is None or f.get('filesize', 0) > best_format.get('filesize', 0):
                    best_format = f
        
        if best_format:
            yield best_format
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': "bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio",
        'outtmpl': '%(title)s.%(ext)s',  # Output filename template
        'merge_output_format': 'mp4',     # Force MP4 output
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'verbose': True,  # Show detailed output
    }
    
    try:
        # Create YoutubeDL instance and download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Starting download of: {url}")
            print("Format selection: bestvideo[height=720][ext=mp4]+bestaudio[acodec^=mp4a]/bestvideo[height>=720]+bestaudio")
            print("-" * 80)
            
            # Download the video
            error_code = ydl.download([url])
            
            if error_code == 0:
                print("\nDownload completed successfully!")
            else:
                print(f"\nDownload completed with errors (code: {error_code})")
                sys.exit(error_code)
                
    except Exception as e:
        print(f"Error during download: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
