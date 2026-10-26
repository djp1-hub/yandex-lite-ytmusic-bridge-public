import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from typing import Optional

from .core import BridgeError, Track, youtube_uri


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BridgeError("HA redirect refused; use the final HA URL")


class HomeAssistant:
    def __init__(self, url: str, token: str, allow_http: bool = False):
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/")):
            raise BridgeError("HA_URL must be an origin without credentials or a path")
        if parsed.scheme == "http" and not allow_http:
            raise BridgeError("Plain HTTP requires --allow-http on a trusted LAN")
        if not token or any(c.isspace() for c in token):
            raise BridgeError("HA_TOKEN is missing or invalid")
        self.url, self.token = url.rstrip("/"), token
        # No ambient proxy forwarding of the bearer token; TLS validation stays on.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path: str, payload: Optional[dict] = None):
        body = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(self.url + path, data=body, headers={
            "Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=15) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise BridgeError("HA response too large")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise BridgeError(f"HA HTTP {exc.code}; request was not retried") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise BridgeError("HA connection failed; request was not retried") from None
        except (ValueError, UnicodeError):
            raise BridgeError("HA returned invalid JSON") from None

    def service(self, name: str, payload: dict, response: bool = False):
        return self.request("/api/services/music_assistant/" + name
                            + ("?return_response" if response else ""), payload)

    def call(self, domain: str, name: str, payload: dict):
        if not re.fullmatch(r"[a-z0-9_]+", domain) or not re.fullmatch(r"[a-z0-9_]+", name):
            raise BridgeError("Invalid HA service name")
        return self.request(f"/api/services/{domain}/{name}", payload)


class MusicAssistant:
    """HA facade; MA owns YouTube authentication, stream URLs and Glagol."""

    def __init__(self, ha: HomeAssistant, entry: str, entity: str,
                 provider: str = "ytmusic", native_entity: str = ""):
        if not entry or not re.fullmatch(r"media_player\.[a-z0-9_]+", entity):
            raise BridgeError("Set MA_CONFIG_ENTRY_ID and MA_PLAYER_ENTITY")
        if not re.fullmatch(r"ytmusic(?:--[A-Za-z0-9_-]+)?", provider):
            raise BridgeError("YT_PROVIDER must be ytmusic or its instance identifier")
        if native_entity and not re.fullmatch(r"media_player\.[a-z0-9_]+", native_entity):
            raise BridgeError("STATION_NATIVE_ENTITY must be a media_player entity")
        self.ha, self.entry, self.entity = ha, entry, entity
        self.provider, self.native_entity = provider, native_entity

    def preflight(self):
        services = self.ha.request("/api/services")
        if not isinstance(services, list) or not any(
            isinstance(s, dict) and s.get("domain") == "music_assistant"
            and {"search", "play_media"} <= set(s.get("services", {})) for s in services
        ):
            raise BridgeError("Required Music Assistant services are unavailable")
        state = self.ha.request("/api/states/" + self.entity)
        if not isinstance(state, dict) or state.get("state") in (None, "unknown", "unavailable"):
            raise BridgeError("Configured MA player is unavailable")

    def search(self, query: str) -> list[Track]:
        result = self.ha.service("search", {
            "config_entry_id": self.entry, "name": query, "media_type": ["track"],
            "limit": 25, "library_only": False}, response=True)
        data = result.get("service_response") if isinstance(result, dict) else None
        items = data.get("tracks") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise BridgeError("Unexpected MA search response schema")
        # HA search is global. Never silently fall back to Spotify, library or Yandex.
        return [Track(t["uri"], t["name"]) for t in items
                if isinstance(t, dict) and isinstance(t.get("name"), str)
                and youtube_uri(t.get("uri"), self.provider)]

    def play(self, track: Track) -> None:
        if not youtube_uri(track.uri, self.provider):
            raise BridgeError("Refusing a non-YouTube Music URI")
        # A native Yandex queue can remain active alongside the MA queue. Pause it
        # first, then replace the MA queue with exactly one non-radio track.
        if self.native_entity:
            self.ha.call("media_player", "media_pause", {"entity_id": self.native_entity})
        self.ha.service("play_media", {"entity_id": self.entity,
                        "media_id": track.uri, "media_type": "track",
                        "enqueue": "replace", "radio_mode": False})
