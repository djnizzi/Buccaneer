# Implementation Plan - Ant to MM5 Migration

## Goal
Implement `ant_to_mm5.py` to migrate data from `mymovies.csv` (exported from Ant Movie Catalog?) to MediaMonkey 5 database, enriching it with images and IMDB data.

## User Review Required
- **IMDB Scraping**: The comment mentions "I can give you the right block of html to parse". I might need user input for the specific CSS selector if I can't deduce it.
- **Image Paths**: Confirming the source path `C:\Users\djniz\OneDrive\dbz\Movies` is accessible.
- **Dry Run**: confirming the script defaults to dry-run or safest mode.

## Proposed Changes

### [MODIFY] [ant_to_mm5.py](file:///c:/mycode/Buccaneer/ant_to_mm5.py)
- **Dependencies**: `sqlite3`, `csv`, `shutil`, `re`, `requests`, `bs4`, `os`, `json`, `pathlib`.
- **DB Connection**: Re-use `mm5_video_tagger.py` logic (connect, custom collation `IUNICODE`, backup).
- **Triggers**: 
    - Query `sqlite_master` to find all triggers on `Songs`.
    - Drop them before update.
    - Re-create them after update (using stored SQL).
- **Match Logic**:
     1. iterate `Songs` where `SongPath LIKE '%Y:\The Best%'`.
     2. Clean `SongTitle`: `cleaned_title = re.sub(r'\[.*?\]', '', title).strip()`.
     3. Search in `mymovies.csv`:
        - Load CSV into memory (list of dicts) using `csv.DictReader(semicolon_delimited)`.
        - Find row where `OriginalTitle` == `cleaned_title`.
        - If not found, try `TranslatedTitle` == `cleaned_title`.
        - If multiple matches? (Take first).
        - If no match: log to `missing_matches.txt`.
- **Updates**:
    - **Director** -> `Artist` (replace `,` with `; `).
    - **Actors** -> `Actors` (replace `,` with `; `).
    - **Year** -> `Year` (append `0000`, e.g. `2007` -> `20070000`. If empty/invalid, skip?).
    - **Category** -> `Genre` (replace `,` with `; `).
    - **Composer** -> `InvolvedPeople` (replace `,` with `; `).
    - **OriginalTitle** -> `OrigTitle`.
    - **Producer** -> `Producer` (replace `,` with `; `).
    - **Writer** -> `Lyricist` (replace `,` with `; `).
    - **Certification** -> `ParentalRating`.
    - **Comment**: `Description` + `\n` + `Comments` (preserve newlines).
    - **ExtendedTags**:
        - Build list of dictionaries: `[{"title":"MyRating","value":...}, ...]`
        - Fields: `UserRating` -> MyRating, `Rating` -> IMDBRating, `URL`, `Country`, `Languages` -> Language, `MediaType` -> AdditionalMedia.
    - **Publisher (Production Companies)**:
        - Scrape from IMDB URL.
        - `requests.get(url, headers={'User-Agent': ...})`
        - `BeautifulSoup`. Find "Production companies" section.
        - Selector strategy: Look for `li` containing "Production companies" or `a` tags within that section. *Will use best-effort selector, might need tuning.*
- **Image Handling**:
    - Source: `C:\Users\djniz\OneDrive\dbz\Movies`.
    - Target: `dirname(SongPath) / folder.jpg`.
    - Filename logic:
        - `N = int(row['Number'])`.
        - If `N < 6440`: `pattern = f"{N:05d}_*.jpg"`. Glob match in source.
        - If `N >= 6440`: `filename = f"{N}.jpg"`.
    - Copy if target doesn't exist.

- **Logging**:
    - `processed_log.txt`: Store `SongID` or `SongPath` to skip in future runs.
    - Print summary stats.

## Verification Plan
### Automated Tests
- **Dry Run**: Use `--dry-run` to print all prospective SQL updates and file ops without executing.

### Manual Verification
- **CSV Parsing**: Check if special chars/newlines in comments are read correctly.
- **IMDB**: Verify a sample URL fetches companies correctly.
- **DB**: Check MM5 after run (or check backup if something goes wrong).
