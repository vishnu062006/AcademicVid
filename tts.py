"""
Step 4: narration audio via edge-tts — free, no billing account required.
Same voice engine covers both English (Phase 1) and Kannada (Phase 3).
"""
import asyncio
import os
import re
import edge_tts

VOICE_EN = "en-IN-NeerjaNeural"     # Indian English, female
VOICE_EN_MALE = "en-IN-PrabhatNeural"
VOICE_KN = "kn-IN-SapnaNeural"      # Kannada, female — Phase 3
VOICE_KN_MALE = "kn-IN-GaganNeural"

# Safety net: if a raw chemical formula/equation slips through despite
# prompt instructions, replace symbols with spoken equivalents so TTS
# doesn't read garbage like "Mg+O2" as mashed-together characters.
EQUATION_SYMBOLS = {
    '->': ' gives ',
    '+': ' plus ',
    '=': ' equals ',
    '^': ' to the power ',
}


def _sanitize_for_speech(text: str) -> str:
    # order matters: replace "->" before "-" or "+" get touched individually
    for symbol, spoken in EQUATION_SYMBOLS.items():
        text = text.replace(symbol, spoken)
    return text


async def _synthesize_async(text: str, out_path: str, voice: str, rate: str = "-15%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(out_path)


def synthesize_narration(text: str, out_path: str, voice: str = VOICE_EN,
                          rate: str = "-8%") -> str:
    """
    Converts narration text to an mp3 file.
    `rate` accepts values like "+10%" or "-15%" to speed up/slow down —
    default is slowed down for a calmer, teacher-like pace.
    """
    text = _sanitize_for_speech(text)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    asyncio.run(_synthesize_async(text, out_path, voice, rate))
    return out_path


# ---------------------------------------------------------------------------
# Fast path: many sections at once, with a disk cache.
# Each section is a separate request to the voice service, so doing them together
# instead of one after another cuts the wait from ~30 s to a few seconds for a
# 6-section lesson. Identical text + voice is never synthesized twice (e.g. a
# teacher fixing one word in the review step only re-records that one section).
# ---------------------------------------------------------------------------
AUDIO_CACHE_DIR = os.path.join("output_cache", "audio")
MAX_PARALLEL = 6        # measured: 6 sections in parallel 2.3 s vs 1 at a time 12-109 s
REQUEST_TIMEOUT = 90    # seconds; a stuck request is retried instead of hanging the lesson
RETRIES = 2


def _audio_cache_path(text: str, voice: str, rate: str) -> str:
    import hashlib
    key = hashlib.sha256("{}|{}|{}".format(voice, rate, text).encode("utf-8")).hexdigest()[:24]
    return os.path.join(AUDIO_CACHE_DIR, key + ".mp3")


async def _synthesize_one(text, voice, rate, out_path, sem):
    async with sem:
        last = None
        for _ in range(RETRIES + 1):
            try:
                tmp = out_path + ".part"
                await asyncio.wait_for(edge_tts.Communicate(text, voice, rate=rate).save(tmp),
                                       timeout=REQUEST_TIMEOUT)
                if os.path.getsize(tmp) == 0:
                    raise RuntimeError("empty audio")
                os.replace(tmp, out_path)
                return
            except Exception as exc:     # a dropped connection: try again
                last = exc
                await asyncio.sleep(1)
        raise last


async def _synthesize_all(jobs):
    sem = asyncio.Semaphore(MAX_PARALLEL)
    await asyncio.gather(*(_synthesize_one(t, v, r, p, sem) for t, v, r, p in jobs))


def synthesize_many(texts, voice: str = VOICE_EN, rate: str = "-8%") -> list:
    """Narration mp3 for each text, made in parallel and cached on disk.
    Returns the mp3 paths in the same order as `texts`."""
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    paths, jobs = [], []
    for text in texts:
        clean = _sanitize_for_speech(text)
        path = _audio_cache_path(clean, voice, rate)
        paths.append(path)
        if not (os.path.exists(path) and os.path.getsize(path) > 0):
            if all(job[3] != path for job in jobs):     # same text twice: make it once
                jobs.append((clean, voice, rate, path))
    if jobs:
        asyncio.run(_synthesize_all(jobs))
    return paths


def get_audio_duration(audio_path: str) -> float:
    from moviepy.editor import AudioFileClip
    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()
    return duration