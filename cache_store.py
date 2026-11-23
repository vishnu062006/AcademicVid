"""
Disk caches that make repeat work instant and save Gemini quota.

1. Lessons (the AI's structured JSON):
     lessons/       committed, pre-made for every library chapter  (scripts/pregenerate_lessons.py)
     lesson_cache/  made at runtime (not committed; survives reruns, cleared on server reboot)
   Key = chapter text + language + lesson mode + model + LESSON_FORMAT_VERSION.
   Bump LESSON_FORMAT_VERSION after a prompt change that should refresh old lessons.

2. Finished outputs (video, PPT, notes PDF, narration mp3) in output_cache/, keyed by the
   exact lesson content, so the same chapter in the same language is never rebuilt:
   the second teacher to open it gets the file at once.
"""
import hashlib
import json
import os

from schema import Chapter

LESSON_FORMAT_VERSION = "1"
COMMITTED_LESSONS_DIR = "lessons"
RUNTIME_LESSONS_DIR = "lesson_cache"
OUTPUT_DIR = "output_cache"


def _sha(text: str, n: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def lesson_key(text: str, language: str, mode: str, model: str) -> str:
    return _sha("|".join((LESSON_FORMAT_VERSION, model, mode, language, text)))


def load_lesson(key: str):
    for folder in (COMMITTED_LESSONS_DIR, RUNTIME_LESSONS_DIR):
        path = os.path.join(folder, key + ".json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return Chapter.model_validate(json.load(f))
            except Exception:
                pass      # a damaged cache file is ignored, the lesson is made again
    return None


def save_lesson(key: str, chapter, folder: str = RUNTIME_LESSONS_DIR) -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, key + ".json")
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def output_path(chapter, language: str, kind: str, ext: str) -> str:
    """Where the finished file for this exact lesson lives (it may not exist yet)."""
    content = json.dumps(chapter.model_dump(), ensure_ascii=False, sort_keys=True)
    key = _sha("|".join((kind, language, content)))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, "{}_{}.{}".format(kind, key, ext))


def is_ready(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def prune_outputs(max_bytes: int = 800 * 1024 * 1024) -> None:
    """Keep output_cache/ under max_bytes by deleting the least recently used files.
    Never raises: cleaning up must not break the app."""
    try:
        files = []
        for root, _dirs, names in os.walk(OUTPUT_DIR):
            for name in names:
                p = os.path.join(root, name)
                st_ = os.stat(p)
                files.append((max(st_.st_atime, st_.st_mtime), st_.st_size, p))
        total = sum(size for _t, size, _p in files)
        for _t, size, p in sorted(files):            # oldest first
            if total <= max_bytes:
                break
            try:
                os.remove(p)
                total -= size
            except OSError:
                pass
    except Exception:
        pass
