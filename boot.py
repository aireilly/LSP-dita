"""Sublime Text entry point for LSP-dita.

Sublime imports this module at the package root. Everything else lives under
`plugin/` and is re-exported here so Sublime can find the commands.
"""

from LSP.plugin import register_plugin, unregister_plugin

from .plugin.build import LspDitaBuildCommand, LspDitaCancelBuildCommand  # noqa: F401
from .plugin.client import DitaLsp
from .plugin.goto import LspDitaGotoCommand  # noqa: F401
from .plugin.hover import DitaHoverListener  # noqa: F401
from .plugin.rootmap import LspDitaSetRootMapCommand  # noqa: F401


def plugin_loaded() -> None:
    register_plugin(DitaLsp)


def plugin_unloaded() -> None:
    unregister_plugin(DitaLsp)
