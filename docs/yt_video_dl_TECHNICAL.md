# YT Video Downloader Technical Documentation

`yt_video_dl.py` is a streamlined implementation of `yt-dlp` designed for high-fidelity video acquisition.

## Architecture

The script extends the standard `yt-dlp` functionality through class inheritance and custom hooks.

### `MyYDL` Class
This subclass overrides `prepare_filename` to apply `utils.strip_video_tags` before the file is even created on disk. This ensures that the filesystem path is clean and matches the project's naming conventions immediately.

### Logging System
- **File Logging**: Uses Python's `logging` module to write to `logs/download_log_{timestamp}.log`.
- **Level**: `INFO` for general progress, `DEBUG` for granular download stats (percent, speed, ETA).
- **Stream**: Simultaneously outputs to `stdout` for real-time monitoring.

## Configuration Highlights

- **`outtmpl`**: Set to `%(title)s.%(ext)s` in the `DOWNLOAD_DIR`.
- **`format`**: `bestvideo+bestaudio/best` ensures maximum quality. 
- **`merge_output_format`**: Standardized to `mp4` for maximum compatibility with media players (like MediaMonkey).
- **`download_archive`**: Pointed to `ARCHIVE_FILE` to provide persistent state across sessions.
- **`ignoreerrors`**: Set to `True` so that a single failed video doesn't stop an entire playlist download.

## Dependencies

- **`yt-dlp`**: The core library.
- **`ffmpeg`**: Essential for the `merge_output_format` operation. Without FFmpeg, `yt-dlp` cannot combine high-quality DASH streams.
- **`utils.strip_video_tags`**: A local utility that uses regex/string manipulation to prune common YouTube title decorations.

## Maintenance

To "reset" the downloader and re-download previously fetched videos, simply delete or rename the `downloaded_ids.txt` file.
