"""Read-only Quasar log watcher: station transcript -> HA/MA -> Yandex Station."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .core import BridgeError, ManualText, query_from_text, run
from .ha import HomeAssistant, MusicAssistant
from .quasar import QuasarLogEvents


def _adapter(allow_http: bool, token_file: str = "") -> MusicAssistant:
    token = os.getenv("HA_TOKEN", "")
    if token_file:
        path = Path(token_file)
        if not path.is_file() or path.is_symlink():
            raise BridgeError("HA token file must be a regular file")
        token = path.read_text(encoding="utf-8").strip()
    ha = HomeAssistant(os.getenv("HA_URL", ""), token, allow_http)
    adapter = MusicAssistant(
        ha,
        os.getenv("MA_CONFIG_ENTRY_ID", ""),
        os.getenv("MA_PLAYER_ENTITY", ""),
        os.getenv("YT_PROVIDER", "ytmusic"),
        os.getenv("STATION_NATIVE_ENTITY", ""),
    )
    adapter.preflight()
    return adapter


def _adb_ready(serial: str) -> bool:
    """Connect to exactly one configured station and verify its transport."""
    subprocess.run(
        ["adb", "connect", serial],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )
    state = subprocess.run(
        ["adb", "-s", serial, "get-state"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
        check=False,
    )
    return state.returncode == 0 and state.stdout.strip() == "device"


def _lines_from_adb(serial: str, retry_delay: float = 5.0):
    if not serial or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:-_" for ch in serial):
        raise BridgeError("Invalid ADB serial")
    while True:
        process = None
        try:
            if not _adb_ready(serial):
                print("Station ADB unavailable; retrying", file=sys.stderr, flush=True)
                yield None
                time.sleep(retry_delay)
                continue

            print("Station ADB connected; watching Quasar log", file=sys.stderr, flush=True)
            # Start at EOF: never replay voice requests after a reconnect.
            process = subprocess.Popen(
                ["adb", "-s", serial, "shell", "tail", "-n", "0", "-F",
                 "/data/quasar/daemons_logs/maind.log"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            if process.stdout is None:
                raise BridgeError("ADB log stream unavailable")
            yield from process.stdout
        except (OSError, subprocess.SubprocessError) as exc:
            print("ADB stream error: " + str(exc), file=sys.stderr, flush=True)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        print("Station ADB stream ended; reconnecting", file=sys.stderr, flush=True)
        # Reset pending speech before the next station session. This prevents a
        # phrase heard before reboot from being paired with IDLE after reboot.
        yield None
        time.sleep(retry_delay)


def watch(lines, adapter: MusicAssistant, *, cooldown: float = 5.0):
    events = QuasarLogEvents()
    last_phrase = ""
    last_time = 0.0
    for line in lines:
        if line is None:
            events = QuasarLogEvents()
            continue
        phrase = events.feed(line)
        if phrase is None:
            continue
        try:
            query_from_text(phrase)
        except BridgeError:
            continue
        now = time.monotonic()
        if phrase.casefold() == last_phrase and now - last_time < cooldown:
            continue
        last_phrase, last_time = phrase.casefold(), now
        try:
            result = run(ManualText(phrase), adapter, adapter, execute=True)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        except BridgeError as exc:
            print(str(exc), file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Quasar log -> MA bridge")
    parser.add_argument("--adb-serial", default=os.getenv("STATION_ADB_SERIAL", ""))
    parser.add_argument("--allow-http", action="store_true")
    parser.add_argument("--token-file", default="", help="Read HA token from a local file")
    parser.add_argument("--stdin", action="store_true", help="Read prepared log lines from stdin")
    args = parser.parse_args()
    try:
        adapter = _adapter(args.allow_http, args.token_file)
        watch(sys.stdin if args.stdin else _lines_from_adb(args.adb_serial), adapter)
        return 0
    except (BridgeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
