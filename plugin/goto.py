"""Ctrl+click and F12 navigation for DITA file references.

The language server resolves definitions for `keyref` and `conkeyref` only.
This command handles the direct file references first and hands anything else
to the server's own definition provider, so one binding covers both.
"""

import os
from typing import Optional, Tuple

import sublime
import sublime_plugin

from .constants import SYNTAX_SCOPE
from .refs import reference_at, resolve_path
from .topics import find_fragment_offset, offset_to_row


class LspDitaGotoCommand(sublime_plugin.TextCommand):
    """Open the file a DITA address points at, or defer to the LSP session."""

    def run(self, edit: sublime.Edit, side_by_side: bool = False) -> None:
        target = self._target()
        if target is None:
            self.view.run_command("lsp_symbol_definition", {"side_by_side": side_by_side})
            return
        window = self.view.window()
        if window is None:
            return
        path, row = target
        if not os.path.isfile(path):
            window.status_message("LSP-dita: {} does not exist".format(path))
            return
        flags = sublime.ENCODED_POSITION
        if side_by_side:
            flags |= sublime.ADD_TO_SELECTION | sublime.SEMI_TRANSIENT
        window.open_file("{}:{}:{}".format(path, row + 1, 1), flags)

    def _target(self) -> Optional[Tuple[str, int]]:
        selections = self.view.sel()
        if not len(selections):
            return None
        offset = selections[0].begin()
        text = self.view.substr(sublime.Region(0, self.view.size()))
        reference = reference_at(text, offset)
        if reference is None:
            return None
        path = resolve_path(reference, self.view.file_name() or "")
        if path is None:
            return None
        return path, self._row_in_target(path, text, reference)

    def _row_in_target(self, path: str, current_text: str, reference) -> int:
        if not reference.topic_id:
            return 0
        if path == self.view.file_name():
            target_text = current_text
        else:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    target_text = f.read()
            except OSError:
                return 0
        offset = find_fragment_offset(target_text, reference.topic_id, reference.element_id)
        return 0 if offset is None else offset_to_row(target_text, offset)

    def is_enabled(self, side_by_side: bool = False) -> bool:
        return self.view.match_selector(0, SYNTAX_SCOPE)
