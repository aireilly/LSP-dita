"""Hover popups for DITA file references.

The server hovers `keyref` and `conkeyref`. This listener covers the direct
file references it does not, showing the target's title and short description.
Reference parsing returns None wherever the server already answers, so the two
popups never compete.
"""

import html
import os

import sublime
import sublime_plugin

from .constants import SETTINGS_FILE, SYNTAX_SCOPE
from .refs import reference_at, resolve_path
from .topics import read_topic_info

_STYLE = """
<style>
    body { margin: 0; padding: 0.4rem 0.6rem; font-size: 0.9rem; }
    .path { font-family: monospace; }
    .title { font-weight: bold; }
    .desc { padding-top: 0.3rem; }
    .missing { color: color(var(--redish) blend(var(--foreground) 60%)); }
</style>
"""


class DitaHoverListener(sublime_plugin.EventListener):
    """Show a popup describing the DITA topic under the cursor."""

    def on_hover(self, view: sublime.View, point: int, hover_zone: int) -> None:
        if hover_zone != sublime.HOVER_TEXT:
            return
        if not view.match_selector(point, SYNTAX_SCOPE):
            return
        if not sublime.load_settings(SETTINGS_FILE).get("hover_file_references", True):
            return
        text = view.substr(sublime.Region(0, view.size()))
        reference = reference_at(text, point)
        if reference is None:
            return
        path = resolve_path(reference, view.file_name() or "")
        if path is None:
            return
        sublime.set_timeout_async(lambda: self._show(view, point, path), 0)

    def _show(self, view: sublime.View, point: int, path: str) -> None:
        body = self._body(path)
        sublime.set_timeout(
            lambda: view.show_popup(
                _STYLE + body,
                sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                point,
                max_width=800,
                on_navigate=lambda href: view.window().open_file(href),
            ),
            0,
        )

    def _body(self, path: str) -> str:
        name = html.escape(os.path.basename(path))
        if not os.path.isfile(path):
            return '<div class="missing">{} does not exist</div>'.format(name)
        link = '<a class="path" href="{}">{}</a>'.format(html.escape(path), name)
        info = read_topic_info(path)
        if info is None:
            return "<div>{}</div>".format(link)
        parts = ["<div>{}</div>".format(link)]
        if info.title:
            parts.append('<div class="title">{}</div>'.format(html.escape(info.title)))
        if info.shortdesc:
            parts.append('<div class="desc">{}</div>'.format(html.escape(info.shortdesc)))
        return "".join(parts)
