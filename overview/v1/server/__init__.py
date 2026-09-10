"""BluePrint Overview V1 server surface.

Local-only stubs for the Mission Control glass: agents · jobs · pulse.
The blueprint pip package can vendor this module to serve the shell against
a local truth source. Nothing here is production BFF code — just enough to
make the /api/overview/{agents,jobs,pulse} contract testable and dogfoodable
on a laptop.

Overview is the landing lens; Map is dig. This module never speaks Map's
verbs (dig, lot, hub, fan, trail, md-viewer, binder, crumb) and never
paints anything the local desk cannot see.
"""

from .overview_state import (
    load_agents,
    load_jobs,
    load_pulse,
    load_from_fixture,
    empty_state,
)

__all__ = [
    "load_agents",
    "load_jobs",
    "load_pulse",
    "load_from_fixture",
    "empty_state",
]
