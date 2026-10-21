"""
Step 5: slides + narration -> video.

Every file written here is phone/Apple/browser friendly:
  * H.264 video, yuv420p pixel format
  * AAC audio (NOT MP3 - MP3 inside MP4 plays silent in QuickTime / iPhones / many galleries)
  * moov atom at the front (+faststart) so the video starts before it finishes downloading
Slides are static, so a low frame rate is enough and encodes much faster.
Clip duration always comes from the audio length - never hardcoded.
"""
import os
import subprocess
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips

FPS = 10
AUDIO_BITRATE = "64k"          # plenty for speech, half the size of the 128k default
_FF_PARAMS = ["-pix_fmt", "yuv420p", "-movflags", "+faststart"]


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg          # installed together with moviepy
    return imageio_ffmpeg.get_ffmpeg_exe()


def _write(video, out_path: str, fps: int = FPS) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    video.write_videofile(
        out_path, fps=fps, codec="libx264", audio_codec="aac",
        audio_bitrate=AUDIO_BITRATE, preset="veryfast",
        ffmpeg_params=_FF_PARAMS, logger=None,
    )


def build_clip_from_slide(image_path: str, audio_path: str) -> "ImageClip":
    audio_clip = AudioFileClip(audio_path)
    return ImageClip(image_path).set_duration(audio_clip.duration).set_audio(audio_clip)


def build_section_video(slide_paths: list, narration_audio_path: str, out_path: str,
                        fps: int = FPS) -> str:
    """One narration track for the whole section, split evenly across its slides."""
    audio_clip = AudioFileClip(narration_audio_path)
    per_slide = audio_clip.duration / len(slide_paths)
    clips = [ImageClip(p).set_duration(per_slide) for p in slide_paths]
    video = concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
    try:
        _write(video, out_path, fps)
    finally:
        audio_clip.close()
    return out_path


def concatenate_section_videos(section_video_paths: list, out_path: str) -> str:
    """Join the section videos into one file.

    Fast path: ffmpeg stream-copy (no re-encode: seconds instead of minutes, no quality
    loss). All section videos are written by build_section_video, so they share the same
    codec settings and can be joined this way. Fallback: re-encode with MoviePy using the
    same safe settings.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    list_file = out_path + ".list.txt"
    try:
        with open(list_file, "w") as f:
            for p in section_video_paths:
                safe = os.path.abspath(p).replace("'", "'\\''")
                f.write(f"file '{safe}'\n")
        cmd = [_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
               "-i", list_file, "-c", "copy", "-movflags", "+faststart", out_path]
        done = subprocess.run(cmd, capture_output=True, text=True)
        if done.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
        print("[video] stream-copy join failed, re-encoding instead:", done.stderr[-300:])
    except Exception as e:  # noqa: BLE001
        print("[video] stream-copy join error, re-encoding instead:", e)
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

    clips = [VideoFileClip(p) for p in section_video_paths]
    try:
        _write(concatenate_videoclips(clips, method="compose"), out_path)
    finally:
        for c in clips:
            c.close()
    return out_path