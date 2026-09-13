"""BluePrint Map V1 server surface.

The blueprint pip package can vendor this module to serve the Map V1 shell
against a binder folder. Nothing in here is production BFF code — just enough
to make the /api/map/tree + /api/map/children + /api/file contract testable
and dogfoodable on a laptop.
"""

from .map_tree import (
    attach_project_state,
    build_tree,
    children_at,
    load_binder,
    render_file,
)

__all__ = [
    "attach_project_state",
    "build_tree",
    "children_at",
    "load_binder",
    "render_file",
]
