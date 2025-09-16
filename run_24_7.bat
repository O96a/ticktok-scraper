@echo off
title TikTok Scraper 24/7 Monitor
color 0A

echo ========================================
echo TikTok Scraper 24/7 Monitoring Service
echo ========================================
echo.

:start
echo [%date% %time%] Starting TikTok Scraper...
echo.

python tiktok_scraper.py

echo.
echo [%date% %time%] Scraper stopped. Restarting in 30 seconds...
echo Press Ctrl+C to stop the service
echo.

timeout /t 30 /nobreak >nul

goto start
