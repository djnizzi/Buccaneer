# YTM2MP3 Technical Documentation

The `ytm2mp3.py` script serves as a high-level wrapper around `yt-dlp` for automated music acquisition.

## Pipeline Architecture

1. **Input**: Accepts a URL and an optional flag for Discogs integration.
2. **Extraction (`yt-dlp`)**:
   - Downloads the best available audio stream.
   - Uses `FFmpegExtractAudio` post-processor to convert to MP3 at 128kbps (configurable).
   - Temporary files are named using the video ID to prevent collisions during parallel downloads or with illegal characters.
3. **Normalization**:
   - Uses `utils.normalize_yt_title` to split the YouTube title into Artist and Song.
   - Cleans common "junk" strings (e.g., "[Official Video]") via `utils.clean_feat` and `utils.clean_title`.
4. **Tagging**:
   - **Phase 1 (YouTube)**: Writes basic tags (Artist, Title, Comment with URL) using `tag.tag_from_yt`.
   - **Phase 2 (Discogs - Optional)**: If enabled, calls `discogs.search_discogs_with_prompt` and `tag.tag_mp3_with_discogs` to enrich the file with official release data.
5. **Finalization**: Renames the temporary ID-named file to the final sanitized filename.

## Key Components

- **`yt-dlp`**: Configured with `quiet` mode and a custom progress hook for a clean CLI experience.
- **`yaspin`**: Used to show a "Searching" spinner while extracting playlist information, which can be slow for large lists.
- **`ffmpeg`**: The heavy lifter for audio transcoding. The path is hardcoded for the specific environment but can be modified in the `FFMPEG_PATH` constant.

## Error Handling

- **Unavailable Videos**: Skips entries that return `None` (common in restricted or deleted videos).
- **Redundant Downloads**: Checkpoints exist to ensure that if renaming fails or a file is missing post-download, the script logs a warning rather than crashing.
- **Discogs Fallback**: If no Discogs release is selected or found, the script falls back to standard YouTube metadata.
