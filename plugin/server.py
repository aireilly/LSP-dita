"""Download and verify the DITA language server JAR.

The JAR is published as a GitHub release asset. It is fetched into the
package storage directory on first run and re-fetched when the pinned
version changes. The download is verified against a pinned SHA256 before it
is moved into place, so a truncated or substituted file never gets launched.
"""

import hashlib
import os
import shutil
import urllib.request
from typing import Optional

from .constants import JAR_NAME, JAR_SHA256, JAR_URL, SERVER_VERSION

MARKER = "VERSION"


def needs_install(basedir: str, jar_name: str, version: str) -> bool:
    """Return True when the JAR is missing or belongs to a different version."""
    if not os.path.isfile(os.path.join(basedir, jar_name)):
        return True
    marker = os.path.join(basedir, MARKER)
    if not os.path.isfile(marker):
        return True
    try:
        with open(marker, "r", encoding="utf-8") as f:
            return f.read().strip() != version
    except OSError:
        return True


def verify_sha256(path: str, expected: str) -> bool:
    """Return True when the file at path hashes to the expected digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower() == expected.strip().lower()


def download_jar(url: str, dest: str) -> None:
    with urllib.request.urlopen(url, timeout=180) as response:
        with open(dest, "wb") as out:
            shutil.copyfileobj(response, out)


def jar_path(basedir: str) -> str:
    return os.path.join(basedir, JAR_NAME)


def install(basedir: str) -> None:
    """Fetch the pinned JAR into basedir, verifying its digest first."""
    os.makedirs(basedir, exist_ok=True)
    final = jar_path(basedir)
    partial = final + ".part"
    download_jar(JAR_URL, partial)
    if not verify_sha256(partial, JAR_SHA256):
        os.remove(partial)
        raise RuntimeError(
            "Checksum mismatch for {}. Expected sha256 {}. "
            "The download was discarded.".format(JAR_NAME, JAR_SHA256)
        )
    os.replace(partial, final)
    with open(os.path.join(basedir, MARKER), "w", encoding="utf-8") as f:
        f.write(SERVER_VERSION)


def find_local_jar(basedir: str) -> Optional[str]:
    """Return the installed JAR path, or None when it is not present."""
    candidate = jar_path(basedir)
    return candidate if os.path.isfile(candidate) else None
