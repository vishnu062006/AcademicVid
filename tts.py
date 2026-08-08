"""
Step 4: narration audio via edge-tts — free, no billing account required.
Same voice engine covers both English (Phase 1) and Kannada (Phase 3).
"""
import asyncio
import edge_tts

VOICE_EN = "en-IN-NeerjaNeural"     # Indian English, female
VOICE_EN_MALE = "en-IN-PrabhatNeural"
VOICE_KN = "kn-IN-SapnaNeural"      # Kannada, female — Phase 3
VOICE_KN_MALE = "kn-IN-GaganNeural"


async def _synthesize_async(text: str, out_path: str, voice: str, rate: str = "+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(out_path)


def synthesize_narration(text: str, out_path: str, voice: str = VOICE_EN,
                          rate: str = "+0%") -> str:
    """
    Converts narration text to an mp3 file. `rate` accepts values like
    "+10%" or "-5%" to speed up/slow down without a separate pydub step.
    """
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    asyncio.run(_synthesize_async(text, out_path, voice, rate))
    return out_path


def get_audio_duration(audio_path: str) -> float:
    from moviepy.editor import AudioFileClip
    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()
    return duration