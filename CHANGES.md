# Changes Summary: ADB Connection Monitoring Solution

## Overview

This update adds automatic ADB connection monitoring and reconnection functionality to handle cases when Yandex Station Lite loses ADB connectivity (e.g., during device reboots).

## Files Changed

### New Files Created

1. **scripts/monitor_adb_connection.sh** - Main monitoring script
   - Monitors ADB connection status periodically
   - Automatically reconnects when connection is lost
   - Restarts the voice bridge when connection is restored
   - Configurable check interval and retry limits

2. **docs/adb_reconnection_solution.md** - Comprehensive documentation
   - Explains the problem and solution
   - Provides installation and configuration instructions
   - Includes troubleshooting guide
   - Describes future improvement possibilities

3. **scripts/test_adb_monitor.sh** - Test script
   - Validates monitoring script functionality
   - Checks integration with main scripts
   - Provides usage examples

4. **tests/test_adb_monitoring.py** - Unit tests
   - Tests monitoring script existence and permissions
   - Verifies parameter handling
   - Tests ADB process termination detection
   - Validates script integration

### Modified Files

1. **scripts/run_voice_bridge.sh**
   - Now calls the monitoring script instead of directly starting the bridge
   - Passes ADB serial and bridge script as parameters
   - Maintains backward compatibility

2. **station_music/watch.py**
   - Enhanced `_lines_from_adb()` function to detect ADB process termination
   - Added process state checking in the reading loop
   - Throws `BridgeError` when ADB process terminates unexpectedly
   - Allows monitoring script to detect and handle connection loss

## Key Features

### Automatic Reconnection
- Monitors ADB connection every 30 seconds (configurable)
- Attempts to reconnect up to 5 times (configurable)
- Waits 60 seconds between retry attempts
- Logs all actions for debugging

### Graceful Error Handling
- Detects when ADB process terminates
- Properly cleans up resources
- Allows monitoring script to restart the bridge
- Maintains clean error messages

### Configuration
- `CHECK_INTERVAL=30` - Connection check frequency (seconds)
- `MAX_RETRIES=5` - Maximum reconnection attempts
- `RETRY_DELAY=60` - Delay between retry attempts (seconds)

## Usage

### Basic Usage
```bash
# Start the voice bridge with monitoring
./scripts/run_voice_bridge.sh
```

### Manual Monitoring (for testing)
```bash
# Monitor a specific device and restart bridge on connection loss
./scripts/monitor_adb_connection.sh 192.168.0.72:5555 ./scripts/run_voice_bridge.sh
```

### Configuration
1. Create `work/installation.env` with your settings
2. Create `work/ha_token` with your Home Assistant token
3. Set `STATION_ADB_SERIAL` to your device's IP:port

## Testing

### Run All Tests
```bash
python3 -m unittest discover -s tests -v
python3 -m unittest tests/test_adb_monitoring -v
```

### Test Monitoring Script
```bash
cd scripts
./test_adb_monitor.sh
```

### Test CLI
```bash
python3 -m station_music.cli 'Алиса, включи на ютубе Queen Bohemian Rhapsody' --demo
```

## Benefits

1. **Automatic Recovery**: No manual intervention needed when device reboots
2. **Reliability**: Continues working even during network connectivity issues
3. **Debugging**: Comprehensive logging helps identify issues
4. **Backward Compatible**: Existing configurations continue to work
5. **Safe**: No changes to device firmware or Alias settings required

## Troubleshooting

See `docs/adb_reconnection_solution.md` for detailed troubleshooting information.

## Future Improvements

- Home Assistant notifications when connection is lost/restored
- More intelligent retry logic based on error types
- Automatic IP address detection for the station
- Integration with monitoring systems (Prometheus, Grafana)

## Compatibility

- Works with existing Home Assistant and Music Assistant installations
- Compatible with all Yandex Station Lite devices
- No changes required to device firmware or Alias configuration
- Maintains all existing functionality and API compatibility
