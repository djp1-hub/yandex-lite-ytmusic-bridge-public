from dataclasses import dataclass
from typing import Protocol
import re
from urllib.parse import urlsplit


class BridgeError(Exception):
    """Safe to display: never include credentials or remote response bodies."""


@dataclass(frozen=True)
class Track:
    uri: str
    name: str


class TranscriptSource(Protocol):
    def read(self) -> str: ...


class Catalog(Protocol):
    def search(self, query: str) -> list[Track]: ...


class Player(Protocol):
    def play(self, track: Track) -> None: ...


@dataclass
class ManualText:
    text: str

    def read(self) -> str:
        return self.text


class QuasarSource:
    def read(self) -> str:
        raise BridgeError("Quasar transcript source is unverified and disabled")


def query_from_text(text: str) -> str:
    if not isinstance(text, str) or len(text) > 512:
        raise BridgeError("Expected text of at most 512 characters")
    text = " ".join(text.split())
    match = re.fullmatch(
        r"(?:алиса[, ]+)?(?:"
        r"включи\s+(?:на\s+ютубе|через\s+ютуб)|"
        r"включи\s+(?:песню|трек|группу|исполнителя)|"
        r"попроси\s+музыкальный\s+(?:мост|мозг)\s+включить"
        r")\s+(.+)",
        text,
        re.I,
    )
    if match:
        return match[1]
    generic = re.fullmatch(r"(?:алиса[, ]+)?включи\s+(.+)", text, re.I)
    if generic:
        query = generic[1]
        # Keep the convenient native Alice wording while refusing common smart-home
        # targets.  Explicit music markers above always remain the safest form.
        device = re.match(
            r"(?:на\s+ютубе|через\s+ютуб|музык[ауи]|свет|ламп\w*|"
            r"телевизор\w*|тв|чайник\w*|пылесос\w*|"
            r"кондиционер\w*|вентилятор\w*|обогреватель\w*|увлажнитель\w*|"
            r"розетк\w*|отоплени\w*|штор\w*|сценари\w*|режим\w*|камер\w*|"
            r"гирлянд\w*)(?:\s|$)",
            query,
            re.I,
        )
        if not device:
            return query
    raise BridgeError("Use a music command such as: Алиса, включи песню …")


def youtube_uri(uri: str, provider: str = "ytmusic") -> bool:
    if not isinstance(uri, str):
        return False
    try:
        value = urlsplit(uri)
        # MA instance IDs are case-sensitive even though urlsplit lowercases schemes.
        return (uri.partition("://")[0] == provider and value.netloc == "track"
                and bool(value.path.strip("/")) and not value.query and not value.fragment)
    except ValueError:
        return False


def run(source: TranscriptSource, catalog: Catalog, player: Player,
        execute: bool = False) -> dict:
    query = query_from_text(source.read())
    tracks = catalog.search(query)
    if not tracks:
        raise BridgeError("No direct YouTube Music track found; playback skipped")
    # Explicit manual requests only. Automatic ASR ingestion is deliberately absent.
    chosen = tracks[0]
    if execute:
        player.play(chosen)
    return {"status": "submitted" if execute else "preview", "track": chosen.name,
            "uri": chosen.uri, "candidate_count": len(tracks)}
