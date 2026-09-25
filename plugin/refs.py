"""Parse and resolve DITA address attributes.

The language server resolves `keyref` and `conkeyref` only. Direct file
references are left to the client, so this module parses the DITA addressing
syntax `path#topic-id/element-id` and turns it into a filesystem path.

The parsing half is pure so it can be tested without Sublime Text. The Sublime
adapter lives in `sublime_adapter`, which is imported lazily by the commands.
"""

import os
import re
from typing import Dict, List, NamedTuple, Optional, Tuple
from urllib.parse import unquote

#: DITA attributes whose value is a resolvable address. `conaction` is absent
#: because it carries a push directive rather than a target, and `data-href`
#: because it belongs to Markdown DITA rather than XML DITA.
RESOLVABLE_ATTRIBUTES = ("href", "conref", "conrefend", "copy-to")

_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# XML permits either quote style, and DITA files in the wild use both. The
# backreference keeps a double quote inside a single-quoted value intact.
_ATTR_RE = re.compile(r"""([A-Za-z_][\w.:-]*)\s*=\s*(["'])(.*?)\2""", re.DOTALL)


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


def _build(name: str, value: str, attributes: Dict[str, str]) -> Optional[Reference]:
    """Turn one attribute into a Reference, or None when it is not resolvable."""
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


_TAG_RE = re.compile(r"<[^>]*>", re.DOTALL)


def all_references(text: str) -> List[Tuple[int, int, Reference]]:
    """Return (start, end, Reference) for every resolvable address in the buffer.

    Spans cover the attribute value only, excluding its quotes, so a caller can
    underline exactly the clickable text.
    """
    found: List[Tuple[int, int, Reference]] = []
    for tag in _TAG_RE.finditer(text):
        element = tag.group(0)
        matches = list(_ATTR_RE.finditer(element))
        attributes = {m.group(1): m.group(3) for m in matches}
        for m in matches:
            reference = _build(m.group(1), m.group(3), attributes)
            if reference is not None:
                found.append((tag.start() + m.start(3), tag.start() + m.end(3), reference))
    return found


def reference_at(text: str, offset: int) -> Optional[Reference]:
    """Return the resolvable Reference whose attribute value contains offset.

    Returns None when the offset is not inside an address attribute value, when
    the attribute is not resolvable, when the element opts out with
    `scope="external"` or `format="html"`, or when the value is a URI.
    """
    start, end = _element_span(text, offset)
    element = text[start:end]
    local = offset - start
    found: Optional[Tuple[str, str]] = None
    attributes: Dict[str, str] = {}
    for match in _ATTR_RE.finditer(element):
        attributes[match.group(1)] = match.group(3)
        if match.start(3) <= local <= match.end(3):
            found = (match.group(1), match.group(3))
    if found is None:
        return None
    return _build(found[0], found[1], attributes)


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
