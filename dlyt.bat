@echo off
setlocal

REM ===========================================================================
REM  Music video pipeline:   download  ->  shrink  ->  tag
REM
REM  Usage:   run_all.bat "https://www.youtube.com/playlist?list=..."
REM           run_all.bat                 no argument = prompts for the URL
REM
REM  Set NOPAUSE=1 to run this unattended, e.g. from a scheduler.
REM
REM  Tuning: edit the CRF / PRESET / CODEC lines below. Higher CRF = smaller
REM  file but more compression. See compress_videos.py --help for details.
REM ===========================================================================

REM  Interpreter that has yt_dlp + tqdm installed.
set "PY=C:\Users\djniz\anaconda3\envs\python3_13\python.exe"

REM  Quality settings for the shrink step.
set "CODEC=libx265"
set "CRF=26"
set "PRESET=medium"

REM  Run from this script's folder so logs/ and downloaded_ids.txt resolve
REM  to the same place they always have.
cd /d "%~dp0"

if not exist "%PY%" (
    echo [ERROR] Python interpreter not found:
    echo         %PY%
    echo         Edit the PY line in this file to point at yours.
    if not defined NOPAUSE pause
    exit /b 1
)

set "URL=%~1"

echo.
echo ===========================================================================
echo  STEP 1 of 3   Download
echo ===========================================================================
if defined URL (
    "%PY%" yt_video_dl.py "%URL%"
) else (
    "%PY%" yt_video_dl.py
)
if errorlevel 1 goto :fail

echo.
echo ===========================================================================
echo  STEP 2 of 3   Shrink oversized videos - %CODEC% CRF %CRF% preset %PRESET%
echo                 Resolution is never changed, only the bitrate.
echo                 A file is replaced only if the result is smaller.
echo ===========================================================================
"%PY%" compress_videos.py --codec %CODEC% --crf %CRF% --preset %PRESET% --audio copy
if errorlevel 1 goto :fail

echo.
echo ===========================================================================
echo  STEP 3 of 3   Embed thumbnails and clean up image files
echo ===========================================================================
"%PY%" tag_videos.py
if errorlevel 1 goto :fail

echo.
echo ===========================================================================
echo  Done. All three steps finished.
echo ===========================================================================
if not defined NOPAUSE pause
exit /b 0

:fail
echo.
echo ===========================================================================
echo  Pipeline stopped at the step shown above.
echo  Your originals are safe: the shrink step only replaces a file after it
echo  has verified the replacement, and it refuses to touch files another tool
echo  already encoded.
echo ===========================================================================
if not defined NOPAUSE pause
exit /b 1