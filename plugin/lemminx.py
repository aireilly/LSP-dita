"""Stop LSP-lemminx validating DITA files.

Lemminx validates a DITA topic by resolving its DTD chain, which reaches the
SVG 1.1 DTD and blows past the JAXP 64,000 entity expansion limit. The result
is a red banner on every file, reported against a DTD the author never wrote.

Raising the limit is the obvious move and it does not work: LSP-lemminx runs a
GraalVM native binary by default, where `java_vmargs` and `xml.server.vmargs`
are both ignored.

Turning validation off for DITA costs nothing, because the DITA language
server already validates these files with Schematron and its own DTD checks.
Lemminx keeps doing what it is uniquely good at here, which is formatting and
DTD-driven completion.

This cannot ship as a settings file. `settings` is a top-level key in
LSP-lemminx's own defaults, Sublime merges top-level keys shallowly, and
`LSP-lemminx` sorts after `LSP-dita`, so its block would replace ours. Writing
to the User layer is the only reliable route, and that is the user's file, so
it happens on an explicit command rather than on load.
"""

import copy
from typing import Any, Dict, List, Optional

LEMMINX_SETTINGS_FILE = "LSP-lemminx.sublime-settings"
FILTERS_KEY = "xml.validation.filters"
DITA_FILTER_PATTERN = "**{.dita,.ditamap,.ditaval}"


def needs_dita_filter(filters: Optional[List[Any]]) -> bool:
    """Return True when the DITA validation filter is not present yet."""
    if not filters:
        return True
    for entry in filters:
        if isinstance(entry, dict) and entry.get("pattern") == DITA_FILTER_PATTERN:
            return False
    return True


def with_dita_filter(filters: Optional[List[Any]]) -> List[Any]:
    """Return the filter list with the DITA pattern appended, idempotently."""
    result = copy.deepcopy(list(filters)) if filters else []
    if needs_dita_filter(result):
        result.append({"pattern": DITA_FILTER_PATTERN})
    return result


try:
    import sublime
    import sublime_plugin
except ImportError:  # imported by the test suite, not by Sublime Text
    sublime = None
    sublime_plugin = None


if sublime_plugin is not None:

    class LspDitaConfigureLemminxCommand(sublime_plugin.WindowCommand):
        """Exclude DITA files from LSP-lemminx validation, in User settings."""

        def run(self) -> None:
            settings = sublime.load_settings(LEMMINX_SETTINGS_FILE)
            # .get() returns the merged value, so the write preserves whatever
            # the defaults and the user already had.
            merged: Dict[str, Any] = dict(settings.get("settings") or {})
            if not needs_dita_filter(merged.get(FILTERS_KEY)):
                self.window.status_message(
                    "LSP-dita: LSP-lemminx already skips validation for DITA files")
                return
            merged[FILTERS_KEY] = with_dita_filter(merged.get(FILTERS_KEY))
            settings.set("settings", merged)
            sublime.save_settings(LEMMINX_SETTINGS_FILE)
            self.window.status_message(
                "LSP-dita: LSP-lemminx will skip validation for DITA files; "
                "restart the server to apply")

        def is_enabled(self) -> bool:
            return sublime.load_settings(LEMMINX_SETTINGS_FILE) is not None
