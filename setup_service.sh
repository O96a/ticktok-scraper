#!/bin/bash

# Get the absolute path of the script
SCRIPT_DIR=$(cd $(dirname "$0") && pwd)

# Get the current user and group
USER=$(whoami)
GROUP=$(id -gn)

# Replace placeholders in the service file
sed -e "s|__ABSOLUTE_PATH__|$SCRIPT_DIR|g" \
    -e "s|__USER__|$USER|g" \
    -e "s|__GROUP__|$GROUP|g" \
    "$SCRIPT_DIR/tiktok_scraper.service" > "$SCRIPT_DIR/tiktok_scraper.service.tmp"

# Move the temporary file to the final destination
mv "$SCRIPT_DIR/tiktok_scraper.service.tmp" "/etc/systemd/system/tiktok_scraper.service"

echo "Service file created at /etc/systemd/system/tiktok_scraper.service"
echo "To enable and start the service, run the following commands:"
echo "sudo systemctl enable tiktok_scraper.service"
echo "sudo systemctl start tiktok_scraper.service"
echo "To check the status of the service, run:"
echo "sudo systemctl status tiktok_scraper.service"