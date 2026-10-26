"""Bounded parser for final phrases already written by Quasar to maind.log."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


_FINAL = re.compile(
    r"onRequestStateChanged:\s*LISTENING,\s*recognizedPhrase='([^'\r\n]{1,512})'"
)
_IDLE = re.compile(r"onAliceStateChanged:\s*IDLE(?:\s|$)")


@dataclass
class QuasarLogEvents:
    """Emit one final phrase after Alice returns to IDLE.

    Quasar repeats recognizedPhrase on BUSY and SPEAKING transitions.  Only the
    LISTENING request transition is accepted, then held until IDLE so MA does not
    start audio over Alice's response.
    """

    pending: Optional[str] = None

    def feed(self, line: str) -> Optional[str]:
        if not isinstance(line, str) or len(line) > 16_384:
            return None
        match = _FINAL.search(line)
        if match:
            self.pending = " ".join(match.group(1).split())
            return None
        if self.pending and _IDLE.search(line):
            phrase, self.pending = self.pending, None
            return phrase
        return None
