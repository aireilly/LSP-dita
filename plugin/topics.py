"""Read titles, short descriptions, and element positions from DITA files.

Extraction is deliberately regex-based rather than using ElementTree. DITA
files declare an external DTD and routinely use entities such as `&nbsp;` that
are defined only in that DTD, so a conforming XML parser raises on files that
are perfectly valid DITA. Hover and navigation must survive those files.
"""

import os
import re
from typing import Dict, NamedTuple, Optional, Pattern, Tuple

_TAG_RE = re.compile(r"<[^>]*>")
_WS_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.DOTALL)
_SHORTDESC_RE = re.compile(r"<shortdesc\b[^>]*>(.*?)</shortdesc>", re.DOTALL)

# Ordered so that &amp; is expanded last and cannot re-introduce another entity.
_ENTITIES = (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&"))

_cache: Dict[str, Tuple[float, Optional["TopicInfo"]]] = {}


class TopicInfo(NamedTuple):
    title: str
    shortdesc: str


def strip_markup(fragment: str) -> str:
    """Flatten a markup fragment to readable text, leaving unknown entities intact."""
    text = _TAG_RE.sub("", fragment)
    for entity, char in _ENTITIES:
        text = text.replace(entity, char)
    return _WS_RE.sub(" ", text).strip()


def _id_pattern(value: str) -> Pattern:
    return re.compile(
        r"""<([\w.:-]+)\b[^>]*?\bid\s*=\s*(["']){}\2""".format(re.escape(value))
    )


def find_fragment_offset(text: str, topic_id: str, element_id: str) -> Optional[int]:
    """Return the offset of the addressed element, scoped to the addressed topic.

    Element IDs are unique within a topic but not within a file, so a document
    holding several topics can define `step-1` more than once. Searching only
    within the addressed topic's extent is what makes the right one win.
    """
    if not topic_id:
        return None
    topic_match = _id_pattern(topic_id).search(text)
    if not topic_match:
        return None
    if not element_id:
        return topic_match.start()
    tag = topic_match.group(1)
    closing = text.find("</{}>".format(tag), topic_match.end())
    extent_end = len(text) if closing == -1 else closing
    element_match = _id_pattern(element_id).search(text, topic_match.end(), extent_end)
    if not element_match:
        return topic_match.start()
    return element_match.start()


def offset_to_row(text: str, offset: int) -> int:
    """Return the zero-based row containing offset."""
    return text.count("\n", 0, offset)


def read_topic_info(path: str) -> Optional[TopicInfo]:
    """Read title and shortdesc from a DITA file, cached on (path, mtime)."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _cache.get(path)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    title_match = _TITLE_RE.search(text)
    shortdesc_match = _SHORTDESC_RE.search(text)
    info = TopicInfo(
        title=strip_markup(title_match.group(1)) if title_match else "",
        shortdesc=strip_markup(shortdesc_match.group(1)) if shortdesc_match else "",
    )
    _cache[path] = (mtime, info)
    return info
