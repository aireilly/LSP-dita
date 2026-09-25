"""Parse and resolve DITA address attributes.

The language server resolves `keyref` and `conkeyref` only. Direct file
references are left to the client, so this module parses the DITA addressing
syntax `path#topic-id/element-id` and turns it into a filesystem path.

The parsing half is pure so it can be tested without Sublime Text. The Sublime
adapter lives in `sublime_adapter`, which is imported lazily by the commands.
"""

import os
import re
from typing import Dict, NamedTuple, Optional, Tuple
from urllib.parse import unquote

#: DITA attributes whose value is a resolvable address. `conaction` is absent
#: because it carries a push directive rather than a target, and `data-href`
#: because it belongs to Markdown DITA rather than XML DITA.
RESOLVABLE_ATTRIBUTES = ("href", "conref", "conrefend", "copy-to")

_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_ATTR_RE = re.compile(r'([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"')


class Reference(NamedTuple):
    raw: str
    path: str
    topic_id: str
    element_id: str
    attribute: str


def parse_address(value: str) -> Tuple[str, str, str]:
    """Split a DITA address into (path, topic_id, element_id)."""
    value = value.strip()
    path, _, fragment = value.partition("#")
    topic_id, _, element_id = fragment.partition("/")
    return path, topic_id, element_id


def _element_span(text: str, offset: int) -> Tuple[int, int]:
    """Return the (start, end) span of the tag enclosing offset."""
    start = text.rfind("<", 0, offset + 1)
    if start == -1:
        start = 0
    end = text.find(">", offset)
    end = len(text) if end == -1 else end + 1
    return start, end


def reference_at(text: str, offset: int) -> Optional[Reference]:
    """Return the resolvable Reference whose attribute value contains offset.

    Returns None when the offset is not inside an address attribute value, when
    the attribute is not resolvable, when the element opts out with
    `scope="external"` or `format="html"`, or when the value is a URI.
    """
    start, end = _element_span(text, offset)
    element = text[start:end]
    local = offset - start
    found = None  # type: Optional[Tuple[str, str]]
    attributes = {}  # type: Dict[str, str]
    for match in _ATTR_RE.finditer(element):
        attributes[match.group(1)] = match.group(2)
        if match.start(2) <= local <= match.end(2):
            found = (match.group(1), match.group(2))
    if found is None:
        return None
    name, value = found
    if name not in RESOLVABLE_ATTRIBUTES:
        return None
    if attributes.get("scope") == "external" or attributes.get("format") == "html":
        return None
    if _URI_SCHEME_RE.match(value.strip()):
        return None
    path, topic_id, element_id = parse_address(value)
    if not path and not topic_id:
        return None
    return Reference(raw=value, path=path, topic_id=topic_id,
                     element_id=element_id, attribute=name)


def resolve_path(reference: Reference, current_file: str) -> Optional[str]:
    """Resolve a Reference to an absolute filesystem path.

    A reference with no path addresses the current file. Backslashes are
    normalised to forward slashes, and percent-encoding is decoded, because
    DITA addresses are URIs.
    """
    if not current_file:
        return None
    if not reference.path:
        return current_file
    relative = unquote(reference.path).replace("\\", "/")
    base = os.path.dirname(current_file)
    return os.path.normpath(os.path.join(base, relative))
