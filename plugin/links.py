"""Underline the DITA references that Ctrl+Click can follow.

Without a visual cue there is nothing to tell you which attribute values are
navigable, so every href looks like ordinary text. This draws a faint underline
under exactly the spans that `lsp_dita_goto` will act on, which keeps the hint
honest: if it is underlined it will open, and if it is not it will not.
"""

import sublime
import sublime_plugin

from .constants import SETTINGS_FILE, SYNTAX_SCOPE
from .refs import all_references

REGION_KEY = "lsp_dita_links"

# Drawn with the comment scope so the line picks up a dimmed colour in most
# themes rather than competing with the text.
_REGION_SCOPE = "comment"
_REGION_FLAGS = (
    sublime.DRAW_NO_FILL
    | sublime.DRAW_NO_OUTLINE
    | sublime.DRAW_SOLID_UNDERLINE
    | sublime.PERSISTENT
)

_DEBOUNCE_MS = 300


def _enabled() -> bool:
    return bool(sublime.load_settings(SETTINGS_FILE).get("underline_file_references", True))


def update_links(view: sublime.View) -> None:
    """Redraw the underlines for this view."""
    if not view.match_selector(0, SYNTAX_SCOPE):
        return
    if not _enabled():
        view.erase_regions(REGION_KEY)
        return
    text = view.substr(sublime.Region(0, view.size()))
    regions = [sublime.Region(start, end) for start, end, _ in all_references(text)]
    if regions:
        view.add_regions(REGION_KEY, regions, _REGION_SCOPE, "", _REGION_FLAGS)
    else:
        view.erase_regions(REGION_KEY)


class DitaLinkListener(sublime_plugin.EventListener):
    """Keep the underlines in step with the buffer."""

    def on_load_async(self, view: sublime.View) -> None:
        update_links(view)

    def on_activated_async(self, view: sublime.View) -> None:
        update_links(view)

    def on_post_save_async(self, view: sublime.View) -> None:
        update_links(view)

    def on_modified_async(self, view: sublime.View) -> None:
        # Rescanning the whole buffer on every keystroke is wasted work, so
        # only the last change in a burst redraws.
        change_count = view.change_count()

        def redraw() -> None:
            if view.is_valid() and view.change_count() == change_count:
                update_links(view)

        sublime.set_timeout_async(redraw, _DEBOUNCE_MS)
