#!/bin/sh
set -eu
PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
base_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
config_file=${BRIDGE_CONFIG:-"$base_dir/work/installation.env"}
token_file=${HA_TOKEN_FILE:-"$base_dir/work/ha_token"}
set -a
. "$config_file"
set +a
: "${STATION_ADB_SERIAL:?Set STATION_ADB_SERIAL in the bridge config}"

# Start the monitoring script instead of directly starting the bridge
# The monitoring script will handle ADB reconnection and bridge restart
exec "$base_dir/scripts/monitor_adb_connection.sh" "$STATION_ADB_SERIAL" "$0"

