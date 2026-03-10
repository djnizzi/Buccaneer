# Walkthrough - Ant to MM5 Migration

## Overview
The `ant_to_mm5.py` script has been implemented to migrate movie metadata from `mymovies.csv` to your MediaMonkey 5 database.

## Dry Run Results
I executed a dry run (`python ant_to_mm5.py --dry-run`).
- **Path Correction**: Adjusted the script to handle MM5 paths (e.g. `:\The Best...`) by prepending `Y` for file operations.
- **Image Copying**: Successfully identified image targets (e.g., `Y:\The Best\Goldfinger\folder.jpg`).
- **Metadata Matching**: 
    - Many movies were successfully matched.
    - **231 files** could not be matched. See `missing_matches.txt` for the full list.
    - Common mismatch causes: Sequels (e.g., `Star Wars Episode IV`), Punctuation differences (`300 Rise of an Empire` vs potentially `300: Rise...`).

## How to Run
To perform the actual migration, run the following command in your terminal:

```powershell
python ant_to_mm5.py --force
```

> [!WARNING]
> This will modify your MM5 database. Ensure MediaMonkey is closed. A backup of the DB will be created automatically before changes are applied.

## Reviewing Missed Matches
You can review `c:\mycode\Buccaneer\missing_matches.txt` to see which files were skipped. 
To fix these, you might need to:
1. Rename the files in MM5 to match the CSV `OriginalTitle`.
2. Or update the script to have fuzzier matching logic (currently it strips `[...]` and looks for exact case-insensitive match).
