# Discogs Searcher User Guide

The `discogs.py` script provides a robust interface for searching the Discogs database to find official release information for your music tracks. It is used as a module by other scripts (like `ytm2mp3.py`) but can also be tested independently.

## Prerequisites

- **Discogs API Token**: Create a token in your [Discogs Settings](https://www.discogs.com/settings/developers).
- **Configuration**: Ensure `secrets.ini` contains your credentials:
  ```ini
  [API]
  key = YOUR_DISCOGS_USER_TOKEN

  [APP]
  appname = YOUR_APP_NAME
  version = 1.0
  ```

## Usage

When integrated into a workflow, the script will:

1. **Clean Queries**: Automatically strips "feat." and other decorations to improve search hits.
2. **Proposed Query**: Shows you the cleaned search term and asks for confirmation or a custom override.
3. **Display Results**: Lists the top 5 matches with detailed information:
   - Artists & Title
   - Release Date/Year
   - Labels
   - Country
   - Format (Vinyl, CD, File, etc.)
4. **Interactive Selection**:
   - Type the number (1-5) to select a release.
   - Type `0` to skip Discogs tagging for the current track.

## Understanding Scores

The percentage next to each result (e.g., `92.50%`) represents the **Fuzzy Match Score**. It compares your search query against the Discogs release title. Higher scores generally indicate a more accurate match.

## Troubleshooting

- **No Results**: If a query returns no results, try a custom query that is more specific (e.g., add the label name or catalog number).
- **API Errors**: Ensure your `secrets.ini` is correctly formatted and your token is active.
