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

#: A pattern on its own relaxes nothing. LSP-lemminx's own defaults pair every
#: pattern with the relaxations it wants, and a filter entry mirrors the whole
#: `xml.validation.*` object, so it can carry any of those keys.
#:
#: `enabled: False` is the decisive one: lemminx documents `schema.enabled` as
#: governing "schema based validation", which is ambiguous about whether a DTD
#: counts, and DITA validates against a DTD. The other two are belt and braces
#: and cost nothing, so a change in how lemminx reads any single key cannot
#: quietly bring the errors back.
DITA_FILTER: Dict[str, Any] = {
    "pattern": DITA_FILTER_PATTERN,
    "enabled": False,
    "noGrammar": "ignore",
    "schema": {"enabled": "never"},
}


def needs_dita_filter(filters: Optional[List[Any]]) -> bool:
    """Return True unless the complete DITA filter is already present.

    An entry that carries the pattern but not the relaxations still needs
    replacing, because it matches DITA files and then changes no behaviour.
    """
    if not filters:
        return True
    return not any(entry == DITA_FILTER for entry in filters)


def with_dita_filter(filters: Optional[List[Any]]) -> List[Any]:
    """Return the filter list with the complete DITA entry, idempotently.

    Any existing entry for the DITA pattern is replaced rather than kept, so an
    incomplete entry written by an earlier version gets upgraded in place.
    """
    result: List[Any] = [
        copy.deepcopy(entry)
        for entry in (filters or [])
        if not (isinstance(entry, dict) and entry.get("pattern") == DITA_FILTER_PATTERN)
    ]
    result.append(copy.deepcopy(DITA_FILTER))
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
