#!/bin/bash

set -eu

# Configuration
ADB_SERIAL="$1"
BRIDGE_SCRIPT="$2"
CHECK_INTERVAL=30
MAX_RETRIES=5

# Function to check ADB connection
check_adb_connection() {
    if adb get-state 2>/dev/null | grep -q "device"; then
        return 0
    else
        return 1
    fi
}

# Function to reconnect ADB
reconnect_adb() {
    echo "$(date): ADB connection lost. Attempting to reconnect..."
    for ((i=1; i<=MAX_RETRIES; i++)); do
        if adb connect "$ADB_SERIAL" >/dev/null 2>&1; then
            echo "$(date): ADB reconnected successfully"
            return 0
        else
            echo "$(date): ADB reconnection attempt $i failed. Retrying..."
            sleep 5
        fi
    done
    echo "$(date): Failed to reconnect ADB after $MAX_RETRIES attempts"
    return 1
}

# Main monitoring loop
echo "$(date): Starting ADB connection monitor for $ADB_SERIAL"

while true; do
    if ! check_adb_connection; then
        if reconnect_adb; then
            # If reconnection successful, restart the bridge
            echo "$(date): Restarting voice bridge..."
            exec "$BRIDGE_SCRIPT"
        else
            echo "$(date): Waiting before retrying..."
            sleep 60
        fi
    fi
    
    # Check connection status periodically
    sleep "$CHECK_INTERVAL"
done
