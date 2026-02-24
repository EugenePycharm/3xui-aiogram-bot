# ===========================================
# VPN Bot - Docker Management Script (Windows PowerShell)
# ===========================================
# Usage: .\docker-scripts.ps1 [command]
# Commands: start, stop, restart, logs, status, build, clean, init-db

param(
    [string]$Command = "help",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RestArgs
)

# Configuration
$COMPOSE_FILE = "docker-compose.yml"
$PROJECT_NAME = "vpn-bot"

# Colors
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Blue }
function Write-Success { Write-Host "[SUCCESS] $args" -ForegroundColor Green }
function Write-Warning-Message { Write-Host "[WARNING] $args" -ForegroundColor Yellow }
function Write-Error-Message { Write-Host "[ERROR] $args" -ForegroundColor Red }

# Check environment
function Check-Env {
    if (-not (Test-Path ".env")) {
        Write-Error-Message ".env file not found!"
        Write-Info "Copy .env.docker.example to .env and fill in the values:"
        Write-Host "  Copy-Item .env.docker.example .env"
        exit 1
    }
}

# Check Docker
function Check-Docker {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        Write-Error-Message "Docker is not installed or not in PATH!"
        Write-Info "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    $composeCmd = Get-ComposeCmd
    $composeVersion = & $composeCmd version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Docker Compose is not installed!"
        exit 1
    }
}

# Get docker compose command
function Get-ComposeCmd {
    $dockerCompose = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($dockerCompose) {
        return "docker-compose"
    }
    return "docker compose"
}

# Commands
function Cmd-Start {
    Write-Info "Starting VPN Bot containers..."
    Check-Env
    
    $COMPOSE_CMD = Get-ComposeCmd
    & $COMPOSE_CMD -f $COMPOSE_FILE up -d
    
    Write-Success "Containers started successfully!"
    Write-Host ""
    Write-Info "Use '.\docker-scripts.ps1 logs' to view logs"
    Write-Info "Use '.\docker-scripts.ps1 status' to check status"
}

function Cmd-Stop {
    Write-Info "Stopping VPN Bot containers..."
    
    $COMPOSE_CMD = Get-ComposeCmd
    & $COMPOSE_CMD -f $COMPOSE_FILE down
    
    Write-Success "Containers stopped successfully!"
}

function Cmd-Restart {
    Write-Info "Restarting VPN Bot containers..."
    Cmd-Stop
    Start-Sleep -Seconds 2
    Cmd-Start
}

function Cmd-Logs {
    param([array]$Args)
    
    $COMPOSE_CMD = Get-ComposeCmd
    $Service = if ($Args -and $Args[0]) { $Args[0] } else { "" }
    
    if ([string]::IsNullOrEmpty($Service)) {
        Write-Info "Showing logs for all containers (Ctrl+C to exit)..."
        & $COMPOSE_CMD -f $COMPOSE_FILE logs -f
    } else {
        Write-Info "Showing logs for $Service (Ctrl+C to exit)..."
        & $COMPOSE_CMD -f $COMPOSE_FILE logs -f $Service
    }
}

function Cmd-Status {
    Write-Info "Container status:"
    Write-Host ""
    
    $COMPOSE_CMD = Get-ComposeCmd
    & $COMPOSE_CMD -f $COMPOSE_FILE ps
    
    Write-Host ""
    Write-Info "Disk usage:"
    docker system df -v 2>$null | Select-String -Pattern "(vpn-bot|bot-data|bot-logs|admin-logs)"
}

function Cmd-Build {
    Write-Info "Building Docker images..."
    
    $COMPOSE_CMD = Get-ComposeCmd
    & $COMPOSE_CMD -f $COMPOSE_FILE build --no-cache
    
    Write-Success "Images built successfully!"
}

function Cmd-Clean {
    Write-Warning-Message "This will remove all containers, volumes, and images!"
    $confirm = Read-Host "Are you sure? (y/N)"
    
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Info "Cleaning up..."
        
        $COMPOSE_CMD = Get-ComposeCmd
        & $COMPOSE_CMD -f $COMPOSE_FILE down -v --remove-orphans
        
        # Remove volumes
        docker volume rm -f vpn-bot-data vpn-bot-logs vpn-admin-logs 2>$null
        
        # Remove images
        docker images -q vpn-bot* 2>$null | ForEach-Object { docker rmi -f $_ 2>$null }
        
        Write-Success "Cleanup completed!"
    } else {
        Write-Info "Cleanup cancelled"
    }
}

function Cmd-Init-Db {
    Write-Info "Initializing database..."
    
    $COMPOSE_CMD = Get-ComposeCmd
    & $COMPOSE_CMD -f $COMPOSE_FILE run --rm db-init
    
    Write-Success "Database initialized!"
}

function Cmd-Shell {
    param([array]$Args)
    $Service = if ($Args -and $Args[0]) { $Args[0] } else { "user-bot" }
    Write-Info "Opening shell in $Service..."
    
    $COMPOSE_CMD = Get-ComposeCmd
    & $COMPOSE_CMD -f $COMPOSE_FILE exec $Service /bin/bash
}

function Cmd-Health {
    Write-Info "Checking container health..."
    
    $containers = @("vpn-user-bot", "vpn-admin-bot")
    
    foreach ($container in $containers) {
        $health = docker inspect --format '{{.State.Health.Status}}' $container 2>$null
        if (-not $health) {
            $health = "not_found"
        }
        
        if ($health -eq "healthy") {
            Write-Host "OK $container : $health" -ForegroundColor Green
        } elseif ($health -eq "not_found") {
            Write-Host "! $container : container not running" -ForegroundColor Yellow
        } else {
            Write-Host "X $container : $health" -ForegroundColor Red
        }
    }
}

function Cmd-Help {
    Write-Host "VPN Bot Docker Management Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker-scripts.ps1 [command]"
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  start       Start all containers"
    Write-Host "  stop        Stop all containers"
    Write-Host "  restart     Restart all containers"
    Write-Host "  logs        View container logs (optionally specify service: user-bot|admin-bot)"
    Write-Host "  status      Show container status"
    Write-Host "  build       Build Docker images"
    Write-Host "  clean       Remove all containers, volumes, and images"
    Write-Host "  init-db     Initialize database"
    Write-Host "  shell       Open shell in container (default: user-bot)"
    Write-Host "  health      Check container health status"
    Write-Host "  help        Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\docker-scripts.ps1 start"
    Write-Host "  .\docker-scripts.ps1 logs user-bot"
    Write-Host "  .\docker-scripts.ps1 shell admin-bot"
}

# Main execution
Check-Docker

switch ($Command) {
    "start" { Cmd-Start }
    "stop" { Cmd-Stop }
    "restart" { Cmd-Restart }
    "logs" { Cmd-Logs $RestArgs }
    "status" { Cmd-Status }
    "build" { Cmd-Build }
    "clean" { Cmd-Clean }
    "init-db" { Cmd-Init-Db }
    "shell" { Cmd-Shell $RestArgs }
    "health" { Cmd-Health }
    "help" { Cmd-Help }
    default {
        if ([string]::IsNullOrEmpty($Command)) {
            Cmd-Help
        } else {
            Write-Error-Message "Unknown command: $Command"
            Cmd-Help
            exit 1
        }
    }
}
