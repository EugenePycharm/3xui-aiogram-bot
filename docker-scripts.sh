#!/bin/bash
# ===========================================
# VPN Bot - Docker Management Script (Linux/Ubuntu)
# ===========================================
# Usage: ./docker-scripts.sh [command]
# Commands: start, stop, restart, logs, status, build, clean, init-db

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="vpn-bot"

# Helper functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_info "Copy .env.docker.example to .env and fill in the values:"
        echo "  cp .env.docker.example .env"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
}

# Get docker compose command
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# Commands
cmd_start() {
    print_info "Starting VPN Bot containers..."
    check_env
    
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE up -d
    
    print_success "Containers started successfully!"
    echo ""
    print_info "Use './docker-scripts.sh logs' to view logs"
    print_info "Use './docker-scripts.sh status' to check status"
}

cmd_stop() {
    print_info "Stopping VPN Bot containers..."
    
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE down
    
    print_success "Containers stopped successfully!"
}

cmd_restart() {
    print_info "Restarting VPN Bot containers..."
    cmd_stop
    sleep 2
    cmd_start
}

cmd_logs() {
    local service=${1:-""}
    
    if [ -z "$service" ]; then
        print_info "Showing logs for all containers (Ctrl+C to exit)..."
        COMPOSE_CMD=$(get_compose_cmd)
        $COMPOSE_CMD -f $COMPOSE_FILE logs -f
    else
        print_info "Showing logs for $service (Ctrl+C to exit)..."
        COMPOSE_CMD=$(get_compose_cmd)
        $COMPOSE_CMD -f $COMPOSE_FILE logs -f "$service"
    fi
}

cmd_status() {
    print_info "Container status:"
    echo ""
    
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE ps
    
    echo ""
    print_info "Disk usage:"
    docker system df -v | grep -E "(vpn-bot|bot-data|bot-logs|admin-logs)" || echo "No volumes found"
}

cmd_build() {
    print_info "Building Docker images..."
    
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE build --no-cache
    
    print_success "Images built successfully!"
}

cmd_clean() {
    print_warning "This will remove all containers, volumes, and images!"
    read -p "Are you sure? (y/N): " confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        print_info "Cleaning up..."

        COMPOSE_CMD=$(get_compose_cmd)
        $COMPOSE_CMD -f $COMPOSE_FILE down -v --remove-orphans

        # Remove volumes (ignore errors if not found)
        docker volume rm vpn-bot-data 2>/dev/null || true
        docker volume rm vpn-bot-logs 2>/dev/null || true
        docker volume rm vpn-admin-logs 2>/dev/null || true

        # Remove images
        docker rmi $(docker images -q pythonproject-*) 2>/dev/null || true

        print_success "Cleanup completed!"
    else
        print_info "Cleanup cancelled"
    fi
}

cmd_init_db() {
    print_info "Initializing database..."
    
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE run --rm db-init
    
    print_success "Database initialized!"
}

cmd_shell() {
    local service=${1:-user-bot}
    print_info "Opening shell in $service..."
    
    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE exec "$service" /bin/bash
}

cmd_health() {
    print_info "Checking container health..."
    
    for container in vpn-user-bot vpn-admin-bot; do
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")
        
        if [ "$health" = "healthy" ]; then
            echo -e "${GREEN}✓${NC} $container: $health"
        elif [ "$health" = "not_found" ]; then
            echo -e "${YELLOW}!${NC} $container: container not running"
        else
            echo -e "${RED}✗${NC} $container: $health"
        fi
    done
}

cmd_help() {
    echo "VPN Bot Docker Management Script"
    echo ""
    echo "Usage: ./docker-scripts.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start all containers"
    echo "  stop        Stop all containers"
    echo "  restart     Restart all containers"
    echo "  logs        View container logs (optionally specify service: user-bot|admin-bot)"
    echo "  status      Show container status"
    echo "  build       Build Docker images"
    echo "  clean       Remove all containers, volumes, and images"
    echo "  init-db     Initialize database"
    echo "  shell       Open shell in container (default: user-bot)"
    echo "  health      Check container health status"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-scripts.sh start"
    echo "  ./docker-scripts.sh logs user-bot"
    echo "  ./docker-scripts.sh shell admin-bot"
}

# Main
main() {
    check_docker
    
    local command=${1:-help}
    shift || true
    
    case "$command" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        logs)
            cmd_logs "$@"
            ;;
        status)
            cmd_status
            ;;
        build)
            cmd_build
            ;;
        clean)
            cmd_clean
            ;;
        init-db)
            cmd_init_db
            ;;
        shell)
            cmd_shell "$@"
            ;;
        health)
            cmd_health
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            print_error "Unknown command: $command"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
