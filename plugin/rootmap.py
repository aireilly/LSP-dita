"""Find DITA maps and tell the language server which one is the root map.

The server builds its key space from a root map. Until one is set, keyref
completion, keyref hover, and profiling validation all stay inert, so the
picker is closer to required setup than to a convenience.
"""

import os
from typing import List, Optional
from urllib.parse import quote

EXCLUDED_DIRS = frozenset(("out", "temp", "build", ".git", ".svn", "node_modules"))

WINDOW_SETTING = "lsp_dita_root_map"


def discover_maps(folders: List[str], limit: int = 200) -> List[str]:
    """Return sorted, de-duplicated .ditamap paths under folders."""
    found = set()
    for folder in folders:
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
            for name in filenames:
                if name.endswith(".ditamap"):
                    found.add(os.path.normpath(os.path.join(dirpath, name)))
                    if len(found) >= limit:
                        return sorted(found)
    return sorted(found)


def nearest_map(start_file: str, stop_at: str = "") -> Optional[str]:
    """Walk upwards from start_file looking for a .ditamap sibling."""
    if not start_file:
        return None
    current = os.path.dirname(os.path.abspath(start_file))
    while True:
        try:
            names = sorted(n for n in os.listdir(current) if n.endswith(".ditamap"))
        except OSError:
            names = []
        if names:
            return os.path.join(current, names[0])
        if stop_at and os.path.abspath(current) == os.path.abspath(stop_at):
            return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def to_uri(path: str) -> str:
    """Convert a filesystem path to a file:// URI the server accepts."""
    return "file://" + quote(os.path.abspath(path).replace(os.sep, "/"), safe="/:")


try:
    import sublime
    import sublime_plugin
except ImportError:  # imported by the test suite, not by Sublime Text
    sublime = None
    sublime_plugin = None


if sublime_plugin is not None:

    from .constants import SESSION_NAME

    def current_root_map(window) -> str:
        """Return the root map chosen for this window, or an empty string."""
        return str(window.settings().get(WINDOW_SETTING) or "")

    def apply_root_map(window, path: str) -> None:
        """Remember the root map and tell the server about it."""
        window.settings().set(WINDOW_SETTING, path)
        view = window.active_view()
        if view is None:
            return
        view.run_command("lsp_execute", {
            "session_name": SESSION_NAME,
            "command_name": "dita.setRootMap",
            "command_args": [to_uri(path)],
        })

    class LspDitaSetRootMapCommand(sublime_plugin.WindowCommand):
        """Pick a .ditamap from the project and set it as the server's root map."""

        def run(self) -> None:
            folders = self._search_folders()
            if not folders:
                self.window.status_message("LSP-dita: open a folder or a DITA file first")
                return
            maps = discover_maps(folders)
            if not maps:
                self.window.status_message("LSP-dita: no .ditamap files found")
                return
            base = folders[0]
            labels = [os.path.relpath(m, base) for m in maps]

            def on_done(index: int) -> None:
                if index < 0:
                    return
                apply_root_map(self.window, maps[index])
                self.window.status_message(
                    "LSP-dita: root map set to {}".format(os.path.basename(maps[index])))

            self.window.show_quick_panel(labels, on_done)

        def _search_folders(self) -> List[str]:
            folders = list(self.window.folders())
            if folders:
                return folders
            view = self.window.active_view()
            name = view.file_name() if view is not None else None
            return [os.path.dirname(name)] if name else []
