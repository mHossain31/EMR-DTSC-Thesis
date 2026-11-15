"""C0 ``static``: the explicit free-flow-shortest routes from the route file; no rerouting."""

from __future__ import annotations

from nycemis.controllers.base import Controller


class StaticController(Controller):
    name = "static"
