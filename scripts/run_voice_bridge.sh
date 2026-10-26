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
adb connect "$STATION_ADB_SERIAL" >/dev/null 2>&1 || true
exec python3 -m station_music.watch \
    --adb-serial "$STATION_ADB_SERIAL" \
    --allow-http \
    --token-file "$token_file"
