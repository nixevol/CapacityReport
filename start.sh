#!/bin/bash
# CapacityReport container startup script

set -e

mkdir -p /var/log/supervisor /var/run /app/cache

exec supervisord -c /app/supervisord.conf
