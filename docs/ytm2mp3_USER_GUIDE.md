# YTM2MP3 User Guide

The `ytm2mp3.py` script allows you to download YouTube Music playlists (or individual videos) and convert them to high-quality MP3 files with proper metadata tagging.

## Prerequisites

- **Python 3.13+**
- **FFmpeg**: Required for audio extraction. Ensure it is installed and the path is correctly configured in the script (default: `C:\Users\djniz\anaconda3\envs\python3_13\Library\bin`).
- **yt-dlp**: Automated downloader (installed via `requirements.txt`).
- **Discogs Account (Optional)**: If you want to use advanced Discogs tagging, you'll need API credentials in `secrets.ini`.

## Usage

Run the script and follow the interactive prompts:

```bash
python ytm2mp3.py
```

### Steps:
1. **Enter URL**: Paste the YouTube/YouTube Music playlist or video URL.
2. **Discogs Tagging**: Choose whether to search Discogs for professional-grade metadata (Artist, Album, Year, Genre, etc.). Type `y` for yes or press Enter to skip.
3. **Wait for Download**: The script will show a progress bar for each track.
4. **Final Result**: MP3s are saved in the `downloads/` folder with cleaned "Artist - Title" filenames.

## Features

- **Smart Filenames**: Automatically cleans "Official Video", "Lyrics", and other tags from filenames.
- **Metadata Tagging**: 
  - Standard: Uses YouTube uploader and title information.
  - Discogs: Prompts for search refinement and release selection for pixel-perfect tagging.
- **Avoids Duplicates**: If a file with the same name already exists, it appends the YouTube ID to prevent overwriting.

## Output

All downloads are placed in the `downloads` directory relative to the script's location.
