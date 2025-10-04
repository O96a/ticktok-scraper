# 24/7 Setup Guide for Linux

This guide provides instructions for setting up the TikTok Scraper to run as a persistent service on a Linux system using `systemd`. This ensures the scraper runs continuously, restarts automatically on failure, and launches on system boot.

## Prerequisites

- A Linux distribution that uses `systemd` (e.g., Ubuntu, Debian, CentOS, Fedora).
- `sudo` or root privileges.
- All Python dependencies installed (`pip install -r requirements.txt`).

## Setup Instructions

1.  **Make the Setup Script Executable:**
    Before running the setup script, ensure it has execute permissions.
    ```bash
    chmod +x setup_service.sh
    ```

2.  **Run the Setup Script:**
    Execute the `setup_service.sh` script with `sudo` to create and install the `systemd` service file. The script will automatically detect the project's absolute path and configure the service to run under the current user.
    ```bash
    sudo ./setup_service.sh
    ```
    The script will copy a configured `tiktok_scraper.service` file to `/etc/systemd/system/`.

3.  **Enable the Service:**
    Enable the service to start automatically at boot.
    ```bash
    sudo systemctl enable tiktok_scraper.service
    ```

4.  **Start the Service:**
    Start the scraper service immediately.
    ```bash
    sudo systemctl start tiktok_scraper.service
    ```

## Managing the Service

You can manage the service using standard `systemctl` commands:

-   **Check the Status:**
    To see if the service is running correctly and view recent logs, use:
    ```bash
    sudo systemctl status tiktok_scraper.service
    ```

-   **View Full Logs:**
    For more detailed, real-time logs, use `journalctl`:
    ```bash
    sudo journalctl -u tiktok_scraper.service -f
    ```

-   **Stop the Service:**
    To manually stop the scraper:
    ```bash
    sudo systemctl stop tiktok_scraper.service
    ```

-   **Restart the Service:**
    To restart the scraper after making configuration changes (e.g., updating `streamers.txt`):
    ```bash
    sudo systemctl restart tiktok_scraper.service
    ```

## Removing the Service

If you need to remove the service:

1.  **Stop the Service:**
    ```bash
    sudo systemctl stop tiktok_scraper.service
    ```

2.  **Disable the Service:**
    ```bash
    sudo systemctl disable tiktok_scraper.service
    ```

3.  **Remove the Service File:**
    ```bash
    sudo rm /etc/systemd/system/tiktok_scraper.service
    ```

4.  **Reload Systemd:**
    ```bash
    sudo systemctl daemon-reload
    ```