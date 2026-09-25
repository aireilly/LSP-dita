"""Run DITA-OT over the focused map or module and surface diagnostics in a panel.

DITA-OT exits 0 even when it logs errors, so success is judged by counting
error lines rather than by the exit code. The output panel carries a
result_file_regex, which is what turns a diagnostic into a clickable jump to
the offending line.
"""

import os
import re
import subprocess
import threading
import webbrowser
from typing import Dict, Iterable, List, Optional, Tuple

#: Matches the positional form DITA-OT uses, for example:
#:   Error: file:/p/good.dita:7:39: [DOTX031E]: The 'y.dita' resource is not available.
#: Groups are (path, line, column, message), which is the order Sublime expects.
RESULT_FILE_REGEX = r"^(?:Error|Warning|Fatal|Info):\s+file:(/[^\s:]+):(\d+):(\d+):\s*(.*)$"

PANEL_NAME = "LSP-dita Build"
BUILDABLE_EXTENSIONS = (".dita", ".ditamap")

_ERROR_RE = re.compile(r"^\s*(?:Error|Fatal):")
_WARNING_RE = re.compile(r"^\s*Warning:")


def build_argv(dita_bin: str, input_path: str, transtype: str,
               output: str, extra_args: List[str]) -> List[str]:
    """Assemble the DITA-OT command line."""
    return [dita_bin, "-i", input_path, "-f", transtype, "-o", output] + list(extra_args)


def resolve_output(input_path: str, output: str) -> str:
    """Resolve the output directory, relative paths landing beside the input."""
    target = output or "out"
    if os.path.isabs(target):
        return os.path.normpath(target)
    return os.path.normpath(os.path.join(os.path.dirname(input_path), target))


def focused_input(path: Optional[str]) -> Optional[str]:
    """Return a saved DITA map or module path suitable for a build."""
    if not path or not os.path.isfile(path):
        return None
    if os.path.splitext(path)[1].lower() not in BUILDABLE_EXTENSIONS:
        return None
    return os.path.normpath(path)


def count_problems(lines: Iterable[str]) -> Tuple[int, int]:
    """Return (errors, warnings) counted from DITA-OT output lines."""
    errors = 0
    warnings = 0
    for line in lines:
        if _ERROR_RE.match(line):
            errors += 1
        elif _WARNING_RE.match(line):
            warnings += 1
    return errors, warnings


def summarise(errors: int, warnings: int, returncode: int) -> str:
    """Build the status line shown when a build finishes."""
    if returncode != 0:
        return "LSP-dita: build failed (exit {}), {} errors, {} warnings".format(
            returncode, errors, warnings)
    if errors:
        return "LSP-dita: build finished with {} errors, {} warnings".format(errors, warnings)
    if warnings:
        return "LSP-dita: build succeeded with {} warnings".format(warnings)
    return "LSP-dita: build succeeded"


try:
    import sublime
    import sublime_plugin
except ImportError:  # imported by the test suite, not by Sublime Text
    sublime = None
    sublime_plugin = None


if sublime_plugin is not None:

    import shutil

    from .constants import SETTINGS_FILE
    _running: Dict[int, subprocess.Popen] = {}

    def _setting(window, key: str, default):
        project = (window.project_data() or {}).get("settings", {}).get("LSP-dita", {})
        if key in project:
            return project[key]
        return sublime.load_settings(SETTINGS_FILE).get(key, default)

    def _resolve_dita_binary(window):
        """Return (path, error). Exactly one of the two is set."""
        configured = str(_setting(window, "dita_ot_path", "") or "")
        if configured:
            if os.path.isfile(configured):
                return configured, None
            return None, (
                "LSP-dita: dita_ot_path points at {}, which is not a file".format(configured))
        found = shutil.which("dita")
        if found:
            return found, None
        return None, (
            "LSP-dita: 'dita' not found on PATH; set dita_ot_path in LSP-dita settings")

    def _resolve_focused_input(window) -> Optional[str]:
        view = window.active_view()
        name = view.file_name() if view is not None else None
        return focused_input(name)

    class LspDitaBuildCommand(sublime_plugin.WindowCommand):
        """Build the focused map or module with DITA-OT."""

        def run(self) -> None:
            window_id = self.window.id()
            if window_id in _running:
                self.window.status_message(
                    "LSP-dita: a build is already running; use Cancel DITA-OT Build to stop it")
                return

            dita_bin, error = _resolve_dita_binary(self.window)
            if error is not None:
                self.window.status_message(error)
                return

            input_path = _resolve_focused_input(self.window)
            if not input_path:
                self.window.status_message(
                    "LSP-dita: save a .dita or .ditamap file before building")
                return

            transtype = str(_setting(self.window, "dita_ot_transtype", "html5"))
            output = resolve_output(
                input_path, str(_setting(self.window, "dita_ot_output", "out")))
            extra = list(_setting(self.window, "dita_ot_args", []) or [])
            open_output = bool(_setting(self.window, "dita_ot_open_output", True))
            argv = build_argv(dita_bin, input_path, transtype, output, extra)

            panel = self.window.create_output_panel(PANEL_NAME)
            panel.settings().set("result_file_regex", RESULT_FILE_REGEX)
            panel.settings().set("result_base_dir", os.path.dirname(input_path))
            panel.settings().set("word_wrap", True)
            panel.settings().set("line_numbers", False)
            panel.settings().set("scroll_past_end", False)
            self.window.run_command("show_panel", {"panel": "output." + PANEL_NAME})

            self._append(panel, "> {}\n\n".format(" ".join(argv)))
            self.window.status_message(
                "LSP-dita: building {}".format(os.path.basename(input_path)))
            threading.Thread(
                target=self._run_build,
                args=(argv, panel, window_id, output, os.path.dirname(input_path),
                      open_output, input_path),
                daemon=True,
            ).start()

        def _append(self, panel, text: str) -> None:
            def do_append() -> None:
                panel.run_command("append", {"characters": text,
                                             "force": True, "scroll_to_end": True})
            sublime.set_timeout(do_append, 0)

        def _run_build(self, argv, panel, window_id: int, output: str,
                       working_dir: str, open_output: bool, input_path: str) -> None:
            lines: List[str] = []
            try:
                process = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    cwd=working_dir or None,
                )
            except OSError as error:
                self._append(panel, "Failed to start DITA-OT: {}\n".format(error))
                return
            _running[window_id] = process
            try:
                assert process.stdout is not None
                for line in process.stdout:
                    lines.append(line.rstrip("\n"))
                    self._append(panel, line)
                process.wait()
            finally:
                _running.pop(window_id, None)

            errors, warnings = count_problems(lines)
            status = summarise(errors, warnings, process.returncode)
            self._append(panel, "\n{}\n".format(status))
            sublime.set_timeout(lambda: sublime.status_message(status), 0)

            if process.returncode == 0 and not errors and open_output:
                sublime.set_timeout(lambda: _open_output(output, input_path), 0)

    def _open_output(output: str, input_path: str) -> None:
        index = os.path.join(output, "index.html")
        module = os.path.join(
            output, os.path.splitext(os.path.basename(input_path))[0] + ".html")
        target = index if os.path.isfile(index) else module
        if not os.path.exists(target):
            target = output
        if os.path.exists(target):
            webbrowser.open("file://" + target)

    class LspDitaCancelBuildCommand(sublime_plugin.WindowCommand):
        """Terminate the DITA-OT build running in this window."""

        def run(self) -> None:
            process = _running.get(self.window.id())
            if process is None:
                self.window.status_message("LSP-dita: no build is running")
                return
            process.terminate()
            self.window.status_message("LSP-dita: build cancelled")

        def is_enabled(self) -> bool:
            return self.window.id() in _running
