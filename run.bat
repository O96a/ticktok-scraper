@echo off
echo ========================================
echo TikTok Live Stream Scraper
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if tiktok_scraper.py exists
if not exist "tiktok_scraper.py" (
    echo Error: tiktok_scraper.py not found
    echo Please ensure you're running this from the correct directory
    pause
    exit /b 1
)

REM Check if streamers.txt exists, create if not
if not exist "streamers.txt" (
    echo Creating streamers.txt template...
    echo # TikTok Streamers Configuration > streamers.txt
    echo # Add one username per line (without @) >> streamers.txt
    echo # Lines starting with # are comments >> streamers.txt
    echo. >> streamers.txt
    echo # Examples (replace with actual usernames): >> streamers.txt
    echo # username1 >> streamers.txt
    echo # username2 >> streamers.txt
    echo # username3 >> streamers.txt
    echo.
    echo Created streamers.txt template. Please add usernames and run again.
    pause
    exit /b 0
)

REM Create output directory if it doesn't exist
if not exist "output" mkdir "output"

echo Starting TikTok Scraper...
echo Press Ctrl+C to stop the scraper
echo.

REM Run the scraper
python tiktok_scraper.py

echo.
echo Scraper stopped.
pause
