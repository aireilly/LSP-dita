"""LSP session management for the DITA language server.

The server is a shadow JAR published as a GitHub release asset. It is fetched
on first run, verified against a pinned digest, and launched with the Java
found on PATH. The Java version is checked before launch so an old JRE
produces a readable message instead of an UnsupportedClassVersionError.
"""

import os
import shutil
import subprocess
from typing import Any, List, Optional

import sublime

from LSP.plugin import AbstractPlugin, ClientConfig

from .constants import JAR_NAME, MINIMUM_JAVA, PACKAGE_NAME, SERVER_VERSION, SESSION_NAME
from .java import parse_java_major
from .server import install, jar_path, needs_install


def _find_java() -> Optional[str]:
    found = shutil.which("java")
    if found:
        return found
    java_home = os.environ.get("JAVA_HOME", "")
    if java_home:
        candidate = os.path.join(java_home, "bin", "java")
        if os.path.isfile(candidate):
            return candidate
    return None


def _java_major(java_bin: str) -> Optional[int]:
    try:
        completed = subprocess.run(
            [java_bin, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_java_major(completed.stdout)


class DitaLsp(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return SESSION_NAME

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), PACKAGE_NAME)

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        return needs_install(cls.basedir(), JAR_NAME, SERVER_VERSION)

    @classmethod
    def install_or_update(cls) -> None:
        install(cls.basedir())

    @classmethod
    def can_start(cls, window: sublime.Window, initiating_view: sublime.View,
                  workspace_folders: List[Any], configuration: ClientConfig) -> Optional[str]:
        java_bin = _find_java()
        if not java_bin:
            return (
                "LSP-dita requires Java {} or newer, but 'java' was not found on PATH. "
                "Install a JDK and restart Sublime Text.".format(MINIMUM_JAVA)
            )
        major = _java_major(java_bin)
        if major is None:
            return "LSP-dita could not determine the version of {}.".format(java_bin)
        if major < MINIMUM_JAVA:
            return (
                "LSP-dita requires Java {} or newer, but {} reports version {}.".format(
                    MINIMUM_JAVA, java_bin, major)
            )
        return None

    @classmethod
    def additional_variables(cls) -> dict:
        java_bin = _find_java() or "java"
        return {
            "java_bin": java_bin,
            "server_jar": jar_path(cls.basedir()),
        }

    @classmethod
    def on_post_start(cls, window: sublime.Window, initiating_view: sublime.View,
                      workspace_folders: List[Any], configuration: ClientConfig) -> None:
        """Re-send the stored root map so a server restart keeps the key space."""
        from .rootmap import WINDOW_SETTING, apply_root_map
        stored = str(window.settings().get(WINDOW_SETTING) or "")
        if stored and os.path.isfile(stored):
            sublime.set_timeout(lambda: apply_root_map(window, stored), 1000)
