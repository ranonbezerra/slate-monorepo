"""Deterministic Concierge agent for tests and offline development.

Exercises the tool path (calls search_library) and emits a recommendation using
a real library id, so the service's UUID guard runs against real data without a
model. Include ``[invalid]`` in the message to force an out-of-library id and
exercise the reroll/degrade path.
"""

from __future__ import annotations

import re

from .base import AbstractConciergeAgent, ConciergeReply, ConciergeRequest

_ID_RE = re.compile(r"id:\s*([0-9a-fA-F-]{36})")
_FAKE_ID = "00000000-0000-0000-0000-000000000000"


class DummyConciergeAgent(AbstractConciergeAgent):
    async def respond(self, req: ConciergeRequest) -> ConciergeReply:
        listing = ""
        for tool in req.tools:
            if tool.name == "search_library":
                listing = await tool.coroutine()
                break

        if "[invalid]" in req.message.lower():
            return ConciergeReply(
                text=f"You should jump back into that one.\nRECOMMEND: {_FAKE_ID}",
            )

        match = _ID_RE.search(listing)
        if match:
            return ConciergeReply(
                text=(
                    "Based on your library and the time you have, give this a go.\n"
                    f"RECOMMEND: {match.group(1)}"
                ),
            )
        return ConciergeReply(
            text="I couldn't find anything in your library to suggest right now."
        )
