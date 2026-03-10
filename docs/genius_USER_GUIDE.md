# Genius Tagger User Guide

The `genius.py` script automatically fetches and tags lyrics for your MP3 files using the Genius API. It features both a fully automated mode for high-confidence matches and a manual review mode for ambiguous cases.

## Prerequisites

- **Python 3.13+** (recommended)
- **Genius API Token**: Obtain a client access token from the [Genius API Documentation](https://genius.com/api-clients).
- **Configuration**: Create a `secrets.ini` file in the project root with the following structure:
  ```ini
  [API]
  genius_key = YOUR_GENIUS_ACCESS_TOKEN
  ```

## Usage

You can run the script via CLI or search interactively.

### 1. Simple Folder Scan
```bash
python genius.py --path "C:/Music/MyAlbum"
```
The script will recursively search the folder for MP3 files that lack lyrics.

### 2. Manual Review List
If you have a text file containing paths to specific MP3s (e.g., generated from a previous run), you can process them directly:
```bash
python genius.py --path "manual_review.txt"
```

## Interactive Controls

While the script is running, you can use the following keyboard shortcuts:
- **`p`**: Pause/Resume the scanning process.
- **`q`**: Safely quit (saves current progress).

## Scoring and Logic

- **Auto-Tagging**: Matches with a similarity score ≥ 75% are tagged automatically.
- **Manual Review**: Matches between 50% and 74% are saved to `manual_review.txt` for later processing.
- **Skipped**: Files with no results over 50% are logged to `skipped_review.txt`.
- **Instrumentals**: You can manually tag a file as "Instrumental" during the review phase by selecting option `0`.

## Files Generated

- `manual_review.txt`: List of files needing human intervention.
- `skipped_review.txt`: List of files where no suitable match was found.
