# TikTok Live Scraper

This project is a Python-based scraper for capturing comments from TikTok live streams. It is designed for robust, 24/7 operation and includes features for monitoring multiple streamers, handling errors, and preventing duplicate comments.

## Features

- **Multi-Streamer Monitoring**: Monitor multiple TikTok users simultaneously in parallel.
- **Real-time Comment Capture**: Captures all public comments from live streams.
- **Comments-Only Mode**: Filters out all other events like likes, shares, and follows to provide clean, comment-focused data.
- **Robust Error Handling**: Automatically reconnects to dropped streams and handles rate limits intelligently.
- **Deduplication**: Prevents duplicate comments from being saved.
- **Easy Configuration**: Uses a simple `config.json` for settings and a `streamers.txt` file for the list of users to monitor.
- **24/7 Operation**: Includes scripts for running the scraper as a persistent service on Windows.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ticktok-scraper
   ```

2. **Create a Python virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Configure Streamers:**
   - Create a `streamers.txt` file in the root directory (you can rename `streamers.txt.example`).
   - Add the TikTok usernames you want to monitor, one per line.

2. **Adjust Scraper Settings (Optional):**
   - The `config.json` file contains settings for delays, rate limiting, and connection timeouts. You can modify these values to fine-tune the scraper's behavior.

## Usage

### Running the Scraper

- **On Windows:**
  - Use the `run.bat` script to start the scraper:
    ```bash
    run.bat
    ```
- **On macOS/Linux:**
  - Activate the virtual environment and run the Python script directly:
    ```bash
    source venv/bin/activate
    python tiktok_scraper.py
    ```

### 24/7 Operation (Windows)

This project includes scripts for running the scraper continuously on Windows.

**Method 1: Simple Batch Script (for testing)**

- Run `run_24_7.bat`. This will automatically restart the scraper if it crashes, but it will stop when you close the command prompt window.

**Method 2: PowerShell Monitor (Advanced)**

- Run `run_24_7.ps1` in a PowerShell terminal. This provides better logging and customizable restart delays.

**Method 3: Windows Task Scheduler (for production)**

- Run `setup_service.ps1` as an administrator. This will create a scheduled task that runs the scraper as a service, ensuring it survives system restarts.

**Managing the Service (Task Scheduler):**

- **Check status:** `Get-ScheduledTask -TaskName "TikTokScraperService"`
- **Start:** `Start-ScheduledTask -TaskName "TikTokScraperService"`
- **Stop:** `Stop-ScheduledTask -TaskName "TikTokScraperService"`
- **Remove:** `Unregister-ScheduledTask -TaskName "TikTokScraperService"`

### 24/7 Operation (Linux)

For running the scraper as a persistent service on Linux, a `systemd` service is recommended.

- **Setup and Management:**
  - A setup script (`setup_service.sh`) is provided to automate the installation.
  - For detailed instructions on setting up, managing, and removing the service, please see the [24/7 Setup Guide for Linux](./24_7_SETUP_GUIDE.md).

## Output

- **Scraped Data**: The captured comments are saved in `.txt` files in the `output/` directory. Each file is named with the streamer's username and a timestamp (`tiktok-rawdata-[username]-YYYYMMDD_HHMMSS.txt`).
- **Logs**: Detailed logs are saved in the `output/` directory (`scraper_YYYYMMDD.log`).
- **Statistics**: Scraper statistics are saved in `output/scraper_stats.json`.

### Output Format

The output files contain the captured comments, one per line. System messages (like connection status) are prefixed with `SYSTEM:`.

**Example:**
```
SYSTEM: Connected to @username's live stream
This is the first comment.
And here is another one.
```

## Contributing

Contributions are welcome! If you have any suggestions, bug reports, or feature requests, please open an issue or submit a pull request.