# TikTok Scraper 24/7 PowerShell Monitor
# Advanced restart service with logging and error handling

param(
    [int]$RestartDelay = 30,
    [string]$LogFile = "monitor.log"
)

$Host.UI.RawUI.WindowTitle = "TikTok Scraper 24/7 Service"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry
}

function Test-Dependencies {
    # Check if Python is available
    try {
        $pythonVersion = python --version 2>&1
        Write-Log "Python available: $pythonVersion"
        return $true
    } catch {
        Write-Log "Python not found in PATH" "ERROR"
        return $false
    }
}

function Start-Scraper {
    Write-Log "Starting TikTok Scraper process..."
    
    try {
        # Start Python scraper process
        $process = Start-Process -FilePath "python" -ArgumentList "tiktok_scraper.py" -PassThru -Wait
        
        if ($process.ExitCode -eq 0) {
            Write-Log "Scraper exited normally (code: $($process.ExitCode))"
        } else {
            Write-Log "Scraper exited with error code: $($process.ExitCode)" "WARNING"
        }
        
        return $process.ExitCode
        
    } catch {
        Write-Log "Failed to start scraper: $($_.Exception.Message)" "ERROR"
        return -1
    }
}

# Main execution
Clear-Host
Write-Host "========================================" -ForegroundColor Green
Write-Host "TikTok Scraper 24/7 Monitoring Service" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check dependencies
if (-not (Test-Dependencies)) {
    Write-Log "Dependency check failed. Exiting." "ERROR"
    exit 1
}

Write-Log "24/7 monitoring service started"
Write-Log "Restart delay: $RestartDelay seconds"
Write-Log "Log file: $LogFile"
Write-Log "Press Ctrl+C to stop the service"
Write-Host ""

$restartCount = 0

try {
    while ($true) {
        $restartCount++
        Write-Log "=== Restart #$restartCount ==="
        
        # Start the scraper
        $exitCode = Start-Scraper
        
        # Log restart info
        Write-Log "Scraper stopped. Waiting $RestartDelay seconds before restart..."
        
        # Wait before restart
        Start-Sleep -Seconds $RestartDelay
    }
} catch {
    Write-Log "Service interrupted: $($_.Exception.Message)" "INFO"
} finally {
    Write-Log "24/7 monitoring service stopped after $restartCount restarts"
}
