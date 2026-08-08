"""
Step 5: direct image -> video clip, no GIF intermediate.
Clip duration is always audio.duration - never hardcoded.
"""
import os
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip


def build_clip_from_slide(image_path: str, audio_path: str) -> "ImageClip":
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration  # <- audio always drives duration, per PRD
    image_clip = ImageClip(image_path).set_duration(duration).set_audio(audio_clip)
    return image_clip


def build_section_video(slide_paths: list, narration_audio_path: str, out_path: str,
                         fps: int = 24) -> str:
    """
    One narration audio track for the whole section, split evenly across
    that section's slides (hook/concept/example/key_points/misconception).
    If you want per-slide narration instead, generate one audio file per
    slide and call build_clip_from_slide() per slide, then concatenate.
    """
    audio_clip = AudioFileClip(narration_audio_path)
    total_duration = audio_clip.duration
    per_slide_duration = total_duration / len(slide_paths)

    clips = []
    for i, slide_path in enumerate(slide_paths):
        img_clip = ImageClip(slide_path).set_duration(per_slide_duration)
        clips.append(img_clip)

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(audio_clip)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    video.write_videofile(out_path, fps=fps, codec="libx264", audio_codec="aac")

    audio_clip.close()
    return out_path


def concatenate_section_videos(section_video_paths: list, out_path: str) -> str:
    clips = [ImageClip(p) if p.endswith((".png", ".jpg")) else None for p in section_video_paths]
    from moviepy.editor import VideoFileClip
    clips = [VideoFileClip(p) for p in section_video_paths]
    final = concatenate_videoclips(clips, method="compose")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    final.write_videofile(out_path)
    for c in clips:
        c.close()
    return out_path