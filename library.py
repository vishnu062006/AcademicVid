"""
Library chapter files.

A manifest entry (manifest.py) is either:
  * a local path, e.g. "jesc101.pdf" (already in the repo), or
  * {"url": <official PDF link>, "pages": (first, last)}: downloaded from the official
    government site (NCERT / KTBS) the first time it is opened and cached on disk.
    "pages" are 0-based PDF page indexes (inclusive) and cut one lesson out of a book.

Why download instead of committing the PDFs: NCERT and KTBS books are marked
"not to be republished", so we link to the official copy rather than re-host it,
and the repo stays small.
"""
import hashlib
import os
import urllib.request

CACHE_DIR = "library_cache"
MAX_DOWNLOAD_BYTES = 60 * 1024 * 1024
TIMEOUT_SECONDS = 90


class LibraryDownloadError(Exception):
    """The official site could not be reached or did not return a PDF."""


def _cache_path(entry: dict) -> str:
    key = "{}|{}".format(entry["url"], entry.get("pages"))
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode()).hexdigest()[:16] + ".pdf")


def _download(url: str, attempts: int = 4) -> bytes:
    """Download a whole file. The NCERT server often drops the connection part-way
    (seen: 10.5 of 13.8 MB), so read in chunks, check the size against Content-Length,
    and resume from where it stopped (HTTP Range) instead of keeping a cut-off file."""
    data = bytearray()
    expected = None
    last_error = None
    for _ in range(attempts):
        headers = {"User-Agent": "Mozilla/5.0 (lesson-library)"}
        if data:
            headers["Range"] = "bytes={}-".format(len(data))
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                if data and resp.status != 206:     # server ignored Range: start again
                    data = bytearray()
                if expected is None and resp.status == 200:
                    length = resp.headers.get("Content-Length")
                    expected = int(length) if length and length.isdigit() else None
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > MAX_DOWNLOAD_BYTES:
                        raise LibraryDownloadError("file too large: " + url)
        except LibraryDownloadError:
            raise
        except Exception as exc:               # dropped connection, timeout, ...
            last_error = exc
            continue
        if expected is None or len(data) >= expected:
            break
    else:
        raise LibraryDownloadError("download kept failing: {}".format(last_error))
    if expected is not None and len(data) < expected:
        raise LibraryDownloadError("incomplete download: " + url)
    if not bytes(data[:5]) == b"%PDF-":
        raise LibraryDownloadError("not a PDF: " + url)
    return bytes(data)


def resolve_library_pdf(entry) -> str:
    """Return a local PDF path for a manifest entry, downloading it once if needed."""
    if isinstance(entry, str):
        return entry
    path = _cache_path(entry)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path

    import fitz
    data = _download(entry["url"])
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = path + ".part"
    try:
        src = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise LibraryDownloadError("unreadable PDF: {}".format(exc)) from exc
    if src.page_count == 0:
        src.close()
        raise LibraryDownloadError("PDF has no pages: " + entry["url"])
    with src:
        pages = entry.get("pages")
        if pages:
            first, last = pages
            out = fitz.open()
            out.insert_pdf(src, from_page=first, to_page=min(last, src.page_count - 1))
            out.save(tmp)
            out.close()
        else:
            src.save(tmp)
    os.replace(tmp, path)   # atomic: never leave a half-written file in the cache
    return path


def entry_is_available(entry) -> bool:
    """For the picker: local files must exist; remote entries are assumed reachable."""
    return (not isinstance(entry, str)) or os.path.exists(entry)
