"""Process-wide cache of decoded QPixmaps keyed by (path, mtime, size).

QPixmap is implicitly shared in Qt — handing out the same QPixmap to many
QGraphicsPixmapItems shares the underlying image data, so caching here cuts
both decode time and RAM. Files are re-read if their mtime changes.
"""

from __future__ import annotations

import os
import threading
from typing import Dict, Tuple

from PySide6.QtGui import QPixmap


_lock = threading.Lock()
_cache: Dict[str, Tuple[float, int, QPixmap]] = {}  # path -> (mtime, size, pixmap)


def get_pixmap(path: str) -> QPixmap:
    """Return a cached QPixmap for `path`, decoding once per file change.

    On any error (missing file, decode failure) returns whatever QPixmap(path)
    produces — typically a null pixmap — so callers behave the same as before.
    """
    if not path:
        return QPixmap()

    try:
        st = os.stat(path)
        key = (st.st_mtime, st.st_size)
    except OSError:
        return QPixmap(path)

    with _lock:
        cached = _cache.get(path)
        if cached and (cached[0], cached[1]) == key:
            return cached[2]

    pix = QPixmap(path)
    with _lock:
        _cache[path] = (key[0], key[1], pix)
    return pix


def clear() -> None:
    with _lock:
        _cache.clear()
