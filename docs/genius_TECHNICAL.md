# Genius Tagger Technical Documentation

The `genius.py` script is a CLI tool designed to enrich MP3 metadata with unsynchronized lyrics (USLT frames) by leveraging the Genius API and fuzzy string matching.

## Architecture & Flow

1. **Discovery**: Scans the target directory for `.mp3` files using `utils.get_mp3_files`.
2. **Filtering**: Checks for existing `USLT` frames using `mutagen`. If lyrics exist, the file is skipped.
3. **Search**:
   - Extracts metadata (Artist, Title) using `tag.get_metadata_tags`.
   - Uses `lyricsgenius` to query the Genius API.
   - Performs a "flipped query" search (Title - Artist) which often yields better results on Genius.
4. **Ranking**: Uses `rapidfuzz` (token sort ratio) to compare the query against search results.
5. **Action**:
   - **High Confidence**: Fetches full lyrics and tags the file.
   - **Low Confidence/Ambiguous**: Logs path for manual review.
6. **Manual Phase**: If run on a `.txt` file or after a folder scan, prompts the user to select from top-scored candidates.

## Key Dependencies

- `lyricsgenius`: Primary API client for Genius.com.
- `rapidfuzz`: Used for robust similarity scoring between local metadata and API results.
- `mutagen`: Handles ID3 tagging (USLT frames).
- `tqdm`: Provides a dynamic, colored progress bar with live statistics.
- `msvcrt` (Windows): Used for non-blocking keyboard input (pause/quit).

## Internal Logic Details

### Query Refinement
If a search fails or yields a low score, the script attempts an "alternative query" using `utils.keep_main` to strip "feat." and other decorations, increasing match probability for collaborations.

### Threading
A background thread (`key_listener`) runs on Windows to listen for the `p` and `q` keys, allowing real-time interaction without interrupting the primary search/tagging loop.

### Tagging Implementation
The script explicitly removes all existing `USLT` frames before adding a new one to ensure a clean state and prevent double frames.
