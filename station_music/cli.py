import argparse
import json
import os
import sys

from .core import BridgeError, ManualText, Track, run, query_from_text
from .ha import HomeAssistant, MusicAssistant


class Demo:
    def search(self, query):
        return [Track("ytmusic://track/DEMO_NOT_A_REAL_TRACK", "Synthetic demo track")]

    def play(self, track):
        raise BridgeError("Demo must never play")


def main():
    parser = argparse.ArgumentParser(description="Manual text → MA → Glagol; preview by default")
    parser.add_argument("text")
    parser.add_argument("--demo", action="store_true", help="Offline synthetic catalog")
    parser.add_argument("--execute", action="store_true", help="Replace MA queue and submit playback")
    parser.add_argument("--allow-http", action="store_true")
    args = parser.parse_args()
    try:
        query_from_text(args.text)  # Reject irrelevant commands before any network call.
        if args.demo:
            if args.execute:
                raise BridgeError("--demo and --execute cannot be combined")
            adapter = Demo()
        else:
            ha = HomeAssistant(os.getenv("HA_URL", ""), os.getenv("HA_TOKEN", ""), args.allow_http)
            adapter = MusicAssistant(ha, os.getenv("MA_CONFIG_ENTRY_ID", ""),
                                     os.getenv("MA_PLAYER_ENTITY", ""),
                                     os.getenv("YT_PROVIDER", "ytmusic"),
                                     os.getenv("STATION_NATIVE_ENTITY", ""))
            adapter.preflight()
        print(json.dumps(run(ManualText(args.text), adapter, adapter, args.execute), ensure_ascii=False))
        return 0
    except BridgeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
