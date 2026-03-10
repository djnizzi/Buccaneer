# YT Video Downloader User Guide

The `yt_video_dl.py` script is a specialized tool for downloading high-quality music videos (clips) from YouTube for your personal collection.

## Prerequisites

- **Python 3.13+**
- **FFmpeg**: Required for merging video and audio streams.
- **W: Drive**: By default, the script downloads to `W:\MusicClips\NowWatching`. Ensure this drive is mapped or modify the script path.

## Usage

You can provide the URL as an argument or enter it when prompted:

```bash
python yt_video_dl.py "https://www.youtube.com/playlist?list=..."
```

## Features

- **High Quality**: Always attempts to download the best available video and audio streams and merges them into an MP4 container.
- **Smart Naming**: Automatically removes video-specific metadata from filenames (e.g., "[Official Video]", "4K", "(Lyric Video)").
- **Download Archive**: Remembers previously downloaded videos using `downloaded_ids.txt`. It will skip any video that has already been successfuly downloaded in a previous session.
- **Automatic Thumbnails**: Downloads the video thumbnail and embeds/saves it along with the video.

## Output & Logs

- **Videos**: Saved to `W:\MusicClips\NowWatching`.
- **Logs**: Detailed execution logs are stored in the `logs/` folder with timestamps for easy troubleshooting.
- **Archive**: `downloaded_ids.txt` tracks everything you've ever downloaded with this script.
