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

# The Python watcher owns the ADB reconnect loop. Keeping one process avoids the
# monitor/bridge recursion which previously left only the monitor running.
exec python3 -m station_music.watch \
    --adb-serial "$STATION_ADB_SERIAL" \
    --allow-http \
    --token-file "$token_file"

