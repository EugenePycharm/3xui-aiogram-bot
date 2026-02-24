# ===========================================
# VPN Bot - Database Backup Script (Windows PowerShell)
# ===========================================
# Usage: .\backup-db.ps1 [backup_dir]

param([string]$BackupDir = "./backup")

# Configuration
$DATE = Get-Date -Format "yyyyMMdd_HHmmss"
$PROJECT_NAME = "vpn-bot"

# Colors
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Blue }
function Write-Success { Write-Host "[SUCCESS] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARNING] $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Check if using PostgreSQL or SQLite
$postgresRunning = docker ps --format '{{.Names}}' | Select-String -Pattern "vpn-postgres" -Quiet

if ($postgresRunning) {
    # PostgreSQL backup
    Write-Info "PostgreSQL detected. Creating backup..."
    
    $DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "vpnbot" }
    $DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "vpnbot" }
    
    $BACKUP_FILE = "$BackupDir/postgres_${DB_NAME}_${DATE}.sql.gz"
    
    docker exec vpn-postgres pg_dump -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE
    
    Write-Success "PostgreSQL backup created: $BACKUP_FILE"
} else {
    # SQLite backup
    Write-Info "SQLite detected. Creating backup..."
    
    $BACKUP_FILE = "$BackupDir/sqlite_bot_${DATE}.db"
    
    # Stop containers for consistent backup
    Write-Warning "Stopping containers for consistent backup..."
    docker compose stop
    
    # Copy database file from volume
    docker run --rm `
        -v vpn-bot-data:/data `
        -v ${PWD}/$BackupDir:/backup `
        alpine cp /data/bot.db /backup/
    
    # Move to dated backup
    Move-Item "$BackupDir/bot.db" $BACKUP_FILE -Force
    
    Write-Success "SQLite backup created: $BACKUP_FILE"
    
    # Restart containers
    Write-Info "Restarting containers..."
    docker compose start
    Write-Success "Containers restarted"
}

# Cleanup old backups (keep last 7)
Write-Info "Cleaning up old backups..."
Set-Location $BackupDir
$backups = Get-ChildItem -Include *.sql.gz,*.db -Recurse | Sort-Object LastWriteTime -Descending
if ($backups.Count -gt 7) {
    $backups | Select-Object -Skip 7 | Remove-Item -Force
}
Write-Success "Old backups cleaned up"

# Show backup info
Write-Host ""
Write-Info "Backup summary:"
Get-Item $BACKUP_FILE | Select-Object Name, Length, LastWriteTime
Write-Host ""
Write-Info "Keep at least 7 backups for safety"
