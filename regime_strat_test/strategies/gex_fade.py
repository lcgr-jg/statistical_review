"""GEX / vanna / charm tactical fade — stubbed for v2."""
from __future__ import annotations

from typing import Any

from strategies.base import BaseStrategy


class GEXFadeStrategy(BaseStrategy):
    """
    Deferred to v2: needs options OI + greeks (or external GEX feed).

    Calling run() raises NotImplementedError so it cannot silently produce
    fake P&L. Wire dealer gamma sign/magnitude here when data is available.
    """

    name = "gex_fade"

    def prepare(self, data: dict[str, Any]):
        raise NotImplementedError(
            "GEX/vanna/charm is deferred to v2. Provide dealer gamma series "
            "in data['gex'] and implement fade/lean rules before enabling."
        )

    def run(self, data: dict[str, Any]):
        raise NotImplementedError(
            "GEX/vanna/charm is deferred to v2 — see prepare() docstring."
        )
