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

# ---------------------------------------------------------------------------
# Fast path (used by the app): the whole lesson in ONE ffmpeg run.
#
# Slides are still pictures, so there is no need to draw 10 frames a second through
# MoviePy. Each slide becomes ONE video frame that lasts for its share of the narration
# (variable frame rate), with x264 tuned for still images. Measured on a 6-section,
# 12 min lesson: 22 s -> ~2.5 s to encode, 6.65 MB -> ~4 MB, and slides stay exactly in
# sync with the voice. (A fixed 2 fps rounded every slide up and drifted 17 s behind.)
# Output stays phone-safe: H.264 yuv420p + AAC, faststart.
# ---------------------------------------------------------------------------
FAST_CRF = "30"               # still slides compress very well; text stays sharp
FAST_AUDIO_BITRATE = "40k"    # mono speech; the voice source itself is 48 kbps mp3


def _ff_escape(path: str) -> str:
    return os.path.abspath(path).replace("'", "'\\''")


def media_duration(path: str) -> float:
    """Length of an audio/video file in seconds (reads ffmpeg's header info)."""
    import re
    info = subprocess.run([_ffmpeg_exe(), "-hide_banner", "-i", path],
                          capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
    if not m:
        raise RuntimeError("could not read duration of " + path)
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def build_lesson_video(sections, out_path: str) -> str:
    """sections: list of (slide_paths, audio).
    audio is either a LIST of mp3s, one per slide (each slide stays up exactly as long as
    its own audio: what is on screen is what is being said), or one mp3 for the whole
    section, split evenly across its slides (older behaviour). Returns out_path."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    img_list, aud_list = out_path + ".images.txt", out_path + ".audio.txt"
    tmp = out_path + ".part.mp4"
    try:
        last_slide = None
        with open(img_list, "w") as fi, open(aud_list, "w") as fa:
            fi.write("ffconcat version 1.0\n")
            for slide_paths, audio in sections:
                if isinstance(audio, (list, tuple)):
                    if len(audio) != len(slide_paths):
                        raise ValueError("need one audio file per slide")
                    durations = [media_duration(a) for a in audio]
                    audios = list(audio)
                else:
                    durations = [media_duration(audio) / max(1, len(slide_paths))] * len(slide_paths)
                    audios = [audio]
                for p, d in zip(slide_paths, durations):
                    fi.write("file '{}'\nduration {:.3f}\n".format(_ff_escape(p), d))
                    last_slide = p
                for a in audios:
                    fa.write("file '{}'\n".format(_ff_escape(a)))
            # ffmpeg ignores the last duration unless the last picture is listed again
            if last_slide:
                fi.write("file '{}'\n".format(_ff_escape(last_slide)))
        def cmd(vfr_flag):
            return [
                _ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", img_list,
                "-f", "concat", "-safe", "0", "-i", aud_list,
                "-map", "0:v", "-map", "1:a",
                vfr_flag, "vfr", "-vf", "format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-crf", FAST_CRF, "-g", "1",          # every slide is a keyframe: instant seeking
                "-c:a", "aac", "-b:a", FAST_AUDIO_BITRATE, "-ac", "1",
                "-movflags", "+faststart", tmp,
            ]
        done = subprocess.run(cmd("-fps_mode"), capture_output=True, text=True)
        if done.returncode != 0:               # ffmpeg older than 5.1 only knows -vsync
            done = subprocess.run(cmd("-vsync"), capture_output=True, text=True)
        if done.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            raise RuntimeError("ffmpeg failed: " + done.stderr[-400:])
        os.replace(tmp, out_path)
    finally:
        for f in (img_list, aud_list, tmp):
            if os.path.exists(f):
                os.remove(f)
    return out_path


def join_audio(mp3_paths, out_path: str) -> str:
    """Join narration mp3s into one mp3 (no re-encode). Used for the PPT's audio track."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    lst = out_path + ".list.txt"
    try:
        with open(lst, "w") as f:
            for p in mp3_paths:
                f.write("file '{}'\n".format(_ff_escape(p)))
        done = subprocess.run([_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
                               "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_path],
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError("ffmpeg join failed: " + done.stderr[-300:])
    finally:
        if os.path.exists(lst):
            os.remove(lst)
    return out_path
