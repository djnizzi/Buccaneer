# Buccaneer - YouTube Music Downloader & Tagger

A collection of Python scripts for downloading music from YouTube and tagging MP3 files with metadata from Discogs and lyrics from Genius.

---

## Installation

### Prerequisites

- Python 3.10+
- FFmpeg (for audio extraction)
- API keys for Discogs and Genius

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `secrets.ini` file based on `secrets_example.ini`:
```ini
[API]
key = your_discogs_api_key
genius_key = your_genius_api_key

[USER]
name = your_name
provider = your_provider

[APP]
appname = Buccaneer
version = 1.0
```

3. Configure FFmpeg path in individual scripts (some scripts have hardcoded paths)

---

## Core Scripts

### ytm2mp3.py

Downloads YouTube playlists as MP3 files and tags them with YouTube metadata and optional Discogs metadata.

**Parameters:**
- Interactive prompts for:
  - Playlist URL
  - Whether to enable Discogs tagging (y/N)
  - Whether this is an album (y/N)
  - Album artist and title (for albums)
  - Track selection (numbers or ranges like 1-9, 10,12-15)

**Output:** MP3 files in `downloads/` folder with metadata from YouTube and optionally Discogs

**Dependencies:** yt_dlp, discogs_client, mutagen, requests, rapidfuzz, tqdm, yaspin

---

### genius.py

Fetches and embeds song lyrics from Genius into MP3 files with fuzzy matching and manual review support.

**Parameters:**
- `--path` - Folder path containing MP3 files (or path to `manual_review.txt`)

**Features:**
- Keyboard shortcuts: `p` to pause, `q` to quit
- Automatic fuzzy matching (threshold: 75%)
- Manual review for ambiguous matches
- Skips files that already have lyrics
- Retries with stripped "feat." on low scores

**Output Files:**
- `manual_review.txt` - Files needing manual review
- `skipped_review.txt` - Files not found on Genius
- Tag lyrics to MP3 files

**Dependencies:** lyricsgenius, mutagen, rapidfuzz, tqdm

---

### discogs_tagger.py

Tags MP3 files with metadata from Discogs database including album art, labels, and catalog numbers.

**Parameters:**
- `--path` - Folder path to process
- `--overwrite` - Overwrite existing tags? (y/n)
- `--mode` - Tagging mode: (s)ongs or (a)lbums

**Features:**
- Caches successful searches to `saved_searches.txt`
- Handles Single/EP detection
- Embeds album artwork from Discogs

**Output:** Tagged MP3 files with Discogs metadata

**Dependencies:** discogs_client, mutagen, rapidfuzz

---

### tag.py

Core tagging utilities for MP3 files (used by other scripts).

**Functions:**
- `tagged_with_discogs(filepath)` - Check if file already tagged with Discogs
- `get_metadata_tags(filepath)` - Read title, artist, album, year from MP3
- `tag_from_yt(filepath, url, album, album_artist, track_num)` - Tag from YouTube metadata
- `tag_mp3_with_discogs(filepath, release, overwrite)` - Tag with Discogs metadata

**Dependencies:** mutagen, requests, PIL

---

### discogs.py

Discogs search utilities with fuzzy matching and user selection.

**Functions:**
- `search_discogs(query, max_results, top_n)` - Search and display top matches
- `search_discogs_with_prompt(query)` - Interactive search with feat. stripping

**Dependencies:** discogs_client, rapidfuzz

---

## YouTube Video Downloader

### yt_video_dl.py

Downloads YouTube playlists as video files (MP4) with thumbnail embedding.

**Parameters:**
- Command line argument: playlist URL (or prompted interactively)

**Features:**
- Strips video tags from filenames (Official Video, Music Video, etc.)
- Downloads archive to avoid re-downloading
- Logs to `logs/` directory

**Output:** MP4 files in `W:\MusicClips\NowWatching\`

**Dependencies:** yt_dlp

---

### tag_videos.py

Embeds thumbnails as attached pictures in MP4 files.

**Parameters:** None (uses hardcoded paths)

**Features:**
- Converts WebP/PNG to JPG if needed
- Cleans up image files after embedding

**Dependencies:** subprocess (ffmpeg)

---

### strip_video_tags.py

Utility function to strip common video-related tags from filenames.

**Removes patterns like:**
- (Official Video), (Official Music Video)
- [Official Audio], [Lyric Video]
- (Music Video), (Visualizer)

---

## MediaMonkey Database Scripts

### ant_to_mm5.py

Migrates movie metadata from CSV to MediaMonkey 5 database.

**Parameters:**
- `--dry-run` - Preview changes without applying
- `--force` - Actually execute updates

**Features:**
- Backs up database before changes
- Drops/restores triggers to avoid conflicts
- Scrapes production companies from IMDB
- Copies folder.jpg images

**Configuration:** Hardcoded paths to CSV and database

**Dependencies:** sqlite3, requests, bs4

---

### mm5_sync_metadata.py

Syncs metadata (Year, Genre, Publisher) from Audio songs to Music Videos.

**Parameters:**
- `--dry-run` - Preview without applying

**Features:**
- Matches by title and artist
- Filters out videos from 2022+
- Auto-selects oldest year for multiple matches
- Logs processed IDs to avoid re-processing

**Dependencies:** sqlite3

---

### mm5_video_tagger.py

Tags music videos in MediaMonkey 5 by appending " [Music Video]" to Album field.

**Parameters:**
- `--dry-run` - Preview without applying

**Features:**
- Drops/restores triggers
- Skips already tagged entries
- Creates timestamped backups

**Dependencies:** sqlite3

---

### mm5_artist_separator.py

Separates multiple artists in MediaMonkey 5 by replacing separators with semicolons.

**Parameters:**
- `--dry-run` - Preview without applying

**Replacements:**
- ` feat.` -> `;`
- `,` -> `;`
- ` x ` -> `;`
- ` & ` -> `;`

**Dependencies:** sqlite3

---

### inspect_mm5_schema.py

Utility to inspect MediaMonkey 5 database schema.

**Output:** Lists all columns in the Songs table

---

## CUE Sheet Utilities

### check_cues.py

Validates and fixes CUE sheet files for album folders.

**Parameters:** Interactive - prompts for root folder

**Features:**
- Detects encoding with chardet
- Extracts performer and title from folder structure
- Updates PERFORMER and TITLE fields
- Creates `.bak` backups

**Path patterns:**
- Regular: `Artist/(YYYY) Album/track.cue`
- VVAA: `.../VVAA/(YYYY) Album/track.cue`

---

### missing_cues.py

Finds MP3 files longer than 25 minutes without corresponding CUE files.

**Parameters:**
- `path` - Root directory to scan (default: current directory)

**Output:** `missing_cues_report.txt`

**Dependencies:** mutagen

---

### restore_cue.py

Restores CUE files from `.bak` backups created by `check_cues.py`.

**Parameters:** None (uses default log file)

**Output:** `restore_log.txt`

---

### cue_bak.py

Moves all `.cue.bak` files from source to backup location.

**Configuration:** Hardcoded SOURCE_ROOT, DEST_ROOT paths

---

## Audio Analysis

### bpm_key_tagger.py

Analyzes audio files and tags them with BPM (tempo) and musical key.

**Parameters:** Interactive - prompts for folder path

**Features:**
- Uses Krumhansl-Kessler key profiles
- Converts to Camelot wheel notation (e.g., "8B", "11A")
- Tags MP3 with TKEY, TBPM, and TXXX frames

**Supported formats:** MP3, WAV, FLAC, OGG, M4A

**Dependencies:** librosa, numpy, mutagen

---

## Cover Art Utilities

### cover_scraper.py

Extracts embedded album art from MP3 files and saves as individual images.

**Parameters:** Interactive prompts for source and destination folders

**Output:** Images named `<trackname>.jpg` or `<trackname>.png`

**Dependencies:** mutagen, PIL

---

### cover_to_folder.py

Processes album folders to standardize cover art as `folder.jpg`.

**Features:**
- Deletes `Folder.jpg` and `AlbumArtSmall.jpg`
- Handles `_resize.jpg` files
- Resizes large images to 640px width
- Extracts from MP3 if no JPG found

**Configuration:** Hardcoded root path

**Dependencies:** PIL, mutagen

---

## Utility Scripts

### utils.py

Shared utility functions used by multiple scripts.

**Functions:**
- `clean_feat(artist)` - Normalize feat./ft. in artist names
- `strip_feat(title)` - Remove featured artists from titles
- `merge_feat(artist)` - Combine main and featured artists
- `normalize_yt_title(info)` - Parse YouTube title to (artist, song)
- `clean_title(title)` - Remove noise from titles
- `safe_filename(name)` - Remove forbidden characters
- `fetch_and_crop_cover(thumbnails)` - Download and crop cover art
- `flip_query(query)` - Swap "Artist - Title" to "Title - Artist"
- `get_mp3_files(folder, recursive)` - List MP3 files

---

### nolyrics.py

Scans folders for MP3 files missing lyrics tags.

**Parameters:** Interactive prompts

**Features:**
- `--show-list` - Display files without lyrics
- `--export` - Save list to text file

**Output:** `missing_lyrics.txt`

**Dependencies:** mutagen, tqdm

---

### scan_mp3_tags.py

CLI tool to display all ID3 tags from an MP3 file in table format.

**Parameters:**
- File path as argument or interactive prompt

**Output:** Formatted table of frame IDs, names, and values

**Dependencies:** mutagen

---

### empty_mp3s.py

Finds 0-byte MP3 files in a folder.

**Parameters:** Interactive prompt for folder path

**Output:** `empty_mp3s.txt`

**Dependencies:** tqdm

---

### find_pngs.py

Scans for PNG files (incomplete/broken implementation).

---

### yt.py

YouTube metadata extraction utilities.

**Functions:**
- `parse_youtube_description(description)` - Extract year, publisher, composer, lyrics
- `get_yt_metadata(url)` - Fetch full metadata from YouTube

**Dependencies:** yt_dlp

---

### debug.py

Debugging utility for inspecting Python objects.

---

### tqdm_super_bar.py

Demo/example of tqdm progress bar customization.

---

### debug_paths.py

Debug utility for checking MediaMonkey database paths.

---

### clean_ant_csv.py

Cleans actor fields in CSV files by converting newline-separated entries to comma-separated.

**Input:** `mymovies.csv`
**Output:** `cleaned_mymovies.csv`

---

## Web Application

### web_app.py

Flask web interface for tagging operations.

**Routes:**
- `/` - Main page
- `/progress_stream` - SSE stream for Genius tagging progress
- `/discogs_tagger` - Discogs tagging interface
- `/genius_tagger` - Genius tagging interface

**Features:**
- Real-time progress updates via Server-Sent Events
- Docker-ready with Dockerfile and docker-compose.yml

---

## Dependencies Summary

All dependencies are listed in `requirements.txt`:

```
discogs_client==2.3.0
lyricsgenius==3.7.2
mutagen==1.47.0
pillow==11.3.0
rapidfuzz==3.14.1
requests==2.32.5
tqdm==4.67.1
yt_dlp==2025.10.22
numpy==2.3.4
librosa==0.11.0
yaspin==3.3.0
flask==3.1.2
chardet==5.2.0
bs4==0.0.2
fake_headers==1.0.2
```

---

## Notes

- Some scripts have hardcoded paths (FFmpeg location, database paths, etc.)
- Scripts that modify MediaMonkey database create `.bak` backups
- The `docs/` folder contains additional technical documentation and user guides