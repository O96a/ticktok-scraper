# TikTok Scraper - Windows Task Scheduler Setup
# This script creates a Windows Task that runs the scraper 24/7

param(
    [string]$TaskName = "TikTokScraperService",
    [string]$ScriptPath = (Get-Location).Path
)

$Host.UI.RawUI.WindowTitle = "TikTok Scraper - Task Scheduler Setup"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TikTok Scraper Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "❌ This script requires administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Running with administrator privileges" -ForegroundColor Green
Write-Host ""

# Task configuration
$batchFile = Join-Path $ScriptPath "run_24_7.bat"
$logPath = Join-Path $ScriptPath "task_scheduler.log"

if (-not (Test-Path $batchFile)) {
    Write-Host "❌ Batch file not found: $batchFile" -ForegroundColor Red
    Write-Host "Please ensure run_24_7.bat exists in the script directory." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "📁 Script path: $ScriptPath" -ForegroundColor Green
Write-Host "📄 Batch file: $batchFile" -ForegroundColor Green
Write-Host "📝 Task name: $TaskName" -ForegroundColor Green
Write-Host ""

try {
    # Remove existing task if it exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "🔄 Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # Create new task action
    $action = New-ScheduledTaskAction -Execute $batchFile -WorkingDirectory $ScriptPath

    # Create task trigger (start at system startup)
    $trigger = New-ScheduledTaskTrigger -AtStartup

    # Create task settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartOnFailure -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 5)

    # Create task principal (run as SYSTEM with highest privileges)
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

    # Register the task
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "TikTok Scraper 24/7 Service - Monitors TikTok streamers continuously"

    Write-Host ""
    Write-Host "✅ Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "- Name: $TaskName" -ForegroundColor White
    Write-Host "- Trigger: Start at system startup" -ForegroundColor White  
    Write-Host "- Action: Run $batchFile" -ForegroundColor White
    Write-Host "- Restart: On failure (every 5 minutes, max 999 times)" -ForegroundColor White
    Write-Host "- User: SYSTEM account" -ForegroundColor White
    Write-Host ""
    
    # Ask if user wants to start the task now
    $startNow = Read-Host "Do you want to start the task now? (y/n)"
    if ($startNow -eq 'y' -or $startNow -eq 'Y') {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ Task started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "The TikTok scraper is now running as a system service." -ForegroundColor Green
        Write-Host "It will automatically restart if it crashes and start on system boot." -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "Management Commands:" -ForegroundColor Cyan
    Write-Host "- View task: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "- Start task: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "- Stop task: Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "- Remove task: Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White

} catch {
    Write-Host "❌ Failed to create scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Ensure you're running as Administrator" -ForegroundColor White
    Write-Host "2. Check that the batch file exists" -ForegroundColor White
    Write-Host "3. Verify PowerShell execution policy allows scripts" -ForegroundColor White
}

Write-Host ""
pause
