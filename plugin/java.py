"""Detect the installed Java version.

The language server is a shadow JAR that needs Java 17 or newer. Checking the
version before launch turns an opaque UnsupportedClassVersionError stack trace
into a message that names the version actually found.
"""

import re
from typing import Optional

_VERSION_RE = re.compile(r'version\s+"(\d+)(?:\.(\d+))?')


def parse_java_major(version_output: str) -> Optional[int]:
    """Return the Java major version from `java -version` output, or None.

    Handles the modern scheme ("17.0.20.1" -> 17) and the pre-9 scheme
    ("1.8.0_402" -> 8), where the leading 1 is a placeholder.
    """
    match = _VERSION_RE.search(version_output)
    if not match:
        return None
    first = int(match.group(1))
    if first == 1:
        second = match.group(2)
        return int(second) if second is not None else None
    return first
