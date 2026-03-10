# Implementation Plan - Missing Cues Finder

The goal is to create a Python script `missing_cues.py` that recursively scans a directory for MP3 files longer than 25 minutes and checks if a corresponding `.cue` file exists in the same folder. If not, it logs the MP3 path.

## Proposed Changes

### [Buccaneer]

#### [NEW] [missing_cues.py](file:///c:/mycode/Buccaneer/missing_cues.py)
- Import `os`, `argparse`, `mutagen.mp3`.
- Implement `find_missing_cues(start_dir)` function.
- Use `os.walk` to traverse directories.
- For each `.mp3` file:
    - Use `mutagen.mp3.MP3(path).info.length` to get duration.
    - If duration > 1500 seconds (25 mins):
        - Check for `.cue` files in the current directory (`files` list from `os.walk`).
        - If no `.cue` file is found, add MP3 path to a list.
- Write the list of missing cue MP3s to `missing_cues_report.txt` in the script's directory.
- Use `argparse` to allow specifying the root directory (default to current working directory).

## Verification Plan

### Automated Tests
- Create a temporary test script `test_missing_cues_logic.py` that mocks `mutagen.mp3.MP3` and `os.walk` to verify the logic without needing actual large MP3 files.
    - Mock a directory structure:
        - `dir1`: long mp3, no cue (Should be reported)
        - `dir2`: long mp3, has cue (Should NOT be reported)
        - `dir3`: short mp3, no cue (Should NOT be reported)
    - Run the test script and assert the output matches expectations.

### Manual Verification
- User can run the script on their music library: `python missing_cues.py` or `python missing_cues.py --path "C:\Path\To\Music"`
- Check `missing_cues_report.txt` for results.
