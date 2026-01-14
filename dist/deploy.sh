#!/bin/bash
# CapacityReport Deployment Script
# Run this script on offline machine to import images and start services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "CapacityReport Deployment"
echo "=========================================="
echo ""

# Set permissions for dist directory and make scripts executable
echo "Setting permissions..."
chmod -R 0777 "$SCRIPT_DIR" 2>/dev/null || true
find "$SCRIPT_DIR" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \; 2>/dev/null || true
echo "  Permissions set"

echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found, please install Docker"
    exit 1
fi

# Check Docker Compose
DOCKER_COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "Error: Docker Compose not found, please install Docker Compose"
    exit 1
fi

# Check image file
if [ ! -f "images/capacity-images.tar" ]; then
    echo "Error: Image file not found: images/capacity-images.tar"
    exit 1
fi

echo "Step 1: Checking ports..."
# 检查端口是否被占用
check_port() {
    local port=$1
    local name=$2
    local in_use=false
    
    # 尝试多种方法检查端口
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            in_use=true
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            in_use=true
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            in_use=true
        fi
    fi
    
    if [ "$in_use" = true ]; then
        echo "Warning: Port $port ($name) is in use"
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

check_port 19081 "App"
check_port 13306 "MySQL"

echo ""
echo "Step 2: Loading images..."
docker load -i images/capacity-images.tar >/dev/null 2>&1

echo ""
echo "Step 3: Verifying images..."
if docker images | grep -q "capacity-report-app.*latest"; then
    echo "  App image: OK"
else
    echo "  App image: FAILED"
    exit 1
fi

if docker images | grep -q "capacity-mysql.*8.0.44"; then
    echo "  MySQL image: OK"
else
    echo "  MySQL image: FAILED"
    exit 1
fi

echo ""
echo "Step 4: Creating directories..."
mkdir -p cache logs
chmod 777 cache logs 2>/dev/null || true

echo ""
echo "Step 5: Checking config..."
if [ ! -f "Configure.json" ]; then
    echo "  Creating default Configure.json..."
    cat > Configure.json << 'EOF'
{
  "MySQL_DBInfo": {
    "host": "capacity-mysql",
    "port": 3306,
    "user": "root",
    "passwd": "gmcc123",
    "dbname": "CapacityReport"
  },
  "ExtractField": []
}
EOF
else
    # Update config for Docker environment
    if command -v python3 &> /dev/null || command -v python &> /dev/null; then
        (command -v python3 >/dev/null && python3 || python) << 'PYEOF'
import json
import sys

try:
    with open('Configure.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db_info = config.get('MySQL_DBInfo', {})
    needs_update = False
    
    if db_info.get('host') != 'capacity-mysql':
        db_info['host'] = 'capacity-mysql'
        needs_update = True
    
    if db_info.get('port') != 3306:
        db_info['port'] = 3306
        needs_update = True
    
    if db_info.get('user') != 'root':
        db_info['user'] = 'root'
        needs_update = True
    
    if db_info.get('passwd') != 'gmcc123':
        db_info['passwd'] = 'gmcc123'
        needs_update = True
    
    if db_info.get('dbname') != 'CapacityReport':
        db_info['dbname'] = 'CapacityReport'
        needs_update = True
    
    if needs_update:
        with open('Configure.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("  Updated Configure.json")
except:
    pass
PYEOF
    fi
fi

if [ ! -f "ReportScript.sql" ]; then
    touch ReportScript.sql
fi

echo ""
echo "Step 6: Starting services..."
$DOCKER_COMPOSE_CMD down 2>/dev/null || true
$DOCKER_COMPOSE_CMD up -d >/dev/null 2>&1

echo ""
echo "Step 7: Waiting for services..."
for i in {1..30}; do
    if docker exec capacity-mysql mysqladmin ping -h localhost -u root -pgmcc123 --silent 2>/dev/null; then
        echo "  MySQL: Ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  MySQL: Timeout"
        exit 1
    fi
    sleep 2
done

if command -v curl &> /dev/null; then
    for i in {1..30}; do
        if curl -f http://localhost:19081/health >/dev/null 2>&1; then
            echo "  App: Ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "  App: Timeout"
            echo "  Check logs: $DOCKER_COMPOSE_CMD logs capacity-app"
            exit 1
        fi
        sleep 2
    done
else
    for i in {1..30}; do
        if docker ps --filter "name=capacity-report-app" --filter "status=running" --format "{{.Names}}" | grep -q "capacity-report-app"; then
            if docker inspect capacity-report-app --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
                echo "  App: Ready"
                break
            elif [ $i -gt 10 ]; then
                echo "  App: Running"
                break
            fi
        fi
        if [ $i -eq 30 ]; then
            echo "  App: Timeout"
            exit 1
        fi
        sleep 2
    done
fi

echo ""
echo "=========================================="
echo "Deployment completed!"
echo "=========================================="
echo ""
echo "Access: http://localhost:19081"
echo ""
echo "Commands:"
echo "  Logs:    $DOCKER_COMPOSE_CMD logs -f"
echo "  Stop:    $DOCKER_COMPOSE_CMD down"
echo "  Restart: $DOCKER_COMPOSE_CMD restart"
echo "  Status:  $DOCKER_COMPOSE_CMD ps"
echo ""
echo "Database:"
echo "  Host:     localhost"
echo "  Port:     13306"
echo "  User:     root"
echo "  Password: gmcc123"
echo "  Database: CapacityReport"
echo ""
