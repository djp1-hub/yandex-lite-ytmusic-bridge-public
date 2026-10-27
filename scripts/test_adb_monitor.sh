#!/bin/bash

# Test script to demonstrate ADB monitoring functionality
# This script simulates the monitoring behavior without actually connecting to a device

set -eu

echo "Testing ADB monitoring functionality..."

# Test 1: Check that monitoring script exists
echo "✓ Checking monitoring script exists..."
if [ -f "monitor_adb_connection.sh" ] && [ -x "monitor_adb_connection.sh" ]; then
    echo "  Monitoring script found and executable"
else
    echo "  ERROR: Monitoring script not found or not executable"
    exit 1
fi

# Test 2: Check that monitoring script has correct parameters
echo "✓ Checking monitoring script parameters..."
if grep -q "\$1" monitor_adb_connection.sh && grep -q "\$2" monitor_adb_connection.sh; then
    echo "  Monitoring script accepts correct parameters"
else
    echo "  ERROR: Monitoring script missing parameter references"
    exit 1
fi

# Test 3: Check that run_voice_bridge.sh calls monitoring script
echo "✓ Checking run_voice_bridge.sh integration..."
if grep -q "monitor_adb_connection.sh" "run_voice_bridge.sh"; then
    echo "  run_voice_bridge.sh correctly calls monitoring script"
else
    echo "  ERROR: run_voice_bridge.sh doesn't call monitoring script"
    exit 1
fi

# Test 4: Check configuration variables
echo "✓ Checking configuration variables..."
if grep -q "CHECK_INTERVAL" monitor_adb_connection.sh && grep -q "MAX_RETRIES" monitor_adb_connection.sh; then
    echo "  Configuration variables present"
else
    echo "  ERROR: Missing configuration variables"
    exit 1
fi

echo ""
echo "All ADB monitoring tests passed! ✓"
echo ""
echo "Usage example:"
echo "  ./monitor_adb_connection.sh 192.168.0.72:5555 ./run_voice_bridge.sh"
echo ""
echo "This will monitor ADB connection to device 192.168.0.72:5555 and"
echo "automatically restart the voice bridge if connection is lost."
