#!/bin/bash
# ===========================================
# VPN Bot - Database Backup Script (Linux/Ubuntu)
# ===========================================
# Usage: ./backup-db.sh [backup_dir]

set -e

# Configuration
BACKUP_DIR=${1:-"./backup"}
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_NAME="vpn-bot"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if using SQLite or PostgreSQL
if docker ps --format '{{.Names}}' | grep -q "vpn-postgres"; then
    # PostgreSQL backup
    print_info "PostgreSQL detected. Creating backup..."
    
    DB_USER=${DB_USER:-vpnbot}
    DB_NAME=${DB_NAME:-vpnbot}
    
    BACKUP_FILE="$BACKUP_DIR/postgres_${DB_NAME}_${DATE}.sql.gz"
    
    docker exec vpn-postgres pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"
    
    print_success "PostgreSQL backup created: $BACKUP_FILE"
else
    # SQLite backup
    print_info "SQLite detected. Creating backup..."
    
    BACKUP_FILE="$BACKUP_DIR/sqlite_bot_${DATE}.db"
    
    # Stop containers to ensure data consistency
    print_warning "Stopping containers for consistent backup..."
    docker compose stop
    
    # Copy database file from volume
    docker run --rm \
        -v vpn-bot-data:/data \
        -v "$(pwd)/$BACKUP_DIR":/backup \
        alpine cp /data/bot.db /backup/
    
    # Rename to dated backup
    mv "$BACKUP_DIR/bot.db" "$BACKUP_FILE"
    
    print_success "SQLite backup created: $BACKUP_FILE"
    
    # Restart containers
    print_info "Restarting containers..."
    docker compose start
    print_success "Containers restarted"
fi

# Cleanup old backups (keep last 7)
print_info "Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t *.sql.gz *.db 2>/dev/null | tail -n +8 | xargs -r rm --
print_success "Old backups cleaned up"

# Show backup info
echo ""
print_info "Backup summary:"
ls -lh "$BACKUP_FILE"
echo ""
print_info "Keep at least 7 backups for safety"
