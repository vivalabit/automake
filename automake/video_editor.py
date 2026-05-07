import math
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automake.config import ProjectValidationError, require_config_section
from automake.media import get_background_music_path, get_media_source


@dataclass(frozen=True)
class VideoAssemblySettings:
    width: int
    height: int
    fps: int
    music_volume: float
    output_filename: str


def get_video_assembly_settings(config: dict[str, Any]) -> VideoAssemblySettings:
    video_config = require_config_section(config, "video")
    return VideoAssemblySettings(
        width=int(video_config.get("width", 1080)),
        height=int(video_config.get("height", 1920)),
        fps=int(video_config.get("fps", 30)),
        music_volume=float(video_config.get("music_volume", 0.18)),
        output_filename=str(video_config.get("output_filename", "final.mp4")),
    )


def resize_and_crop_vertical(clip: Any, width: int, height: int) -> Any:
    scale = max(width / clip.w, height / clip.h)
    resized_width = math.ceil(clip.w * scale)
    resized_height = math.ceil(clip.h * scale)

    return clip.resized(new_size=(resized_width, resized_height)).cropped(
        x_center=resized_width // 2,
        y_center=resized_height // 2,
        width=width,
        height=height,
    )


def get_caption_font(size: int) -> Any:
    try:
        from PIL import ImageFont
    except ImportError as error:
        raise ProjectValidationError(
            "Pillow is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]

    for font_path in font_paths:
        if Path(font_path).is_file():
            return ImageFont.truetype(font_path, size=size)

    return ImageFont.load_default()


def measure_text(draw: Any, text: str, font: Any, stroke_width: int = 0) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_caption_text(draw: Any, text: str, font: Any, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = words[0]

    for word in words[1:]:
        candidate = f"{current_line} {word}"
        candidate_width, _ = measure_text(draw, candidate, font)
        if candidate_width <= max_width:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)

    wrapped_lines = []
    for line in lines:
        line_width, _ = measure_text(draw, line, font)
        if line_width <= max_width:
            wrapped_lines.append(line)
            continue

        average_char_width = max(measure_text(draw, "А", font)[0], 1)
        max_chars = max(max_width // average_char_width, 8)
        wrapped_lines.extend(textwrap.wrap(line, width=max_chars) or [line])

    return wrapped_lines


def create_caption_image(text: str, width: int, height: int) -> Any:
    try:
        import numpy as np
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError as error:
        raise ProjectValidationError(
            "Pillow and NumPy are required. Run: python3 -m pip install -r requirements.txt"
        ) from error

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    shadow_draw = ImageDraw.Draw(shadow)

    font_size = max(width // 14, 58)
    font = get_caption_font(font_size)
    horizontal_padding = width // 12
    max_text_width = width - horizontal_padding * 2
    lines = wrap_caption_text(draw, text, font, max_text_width)

    max_lines = 4
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "..."

    stroke_width = max(font_size // 18, 3)
    line_spacing = font_size // 4
    line_sizes = [measure_text(draw, line, font, stroke_width) for line in lines]
    text_block_width = max((line_width for line_width, _ in line_sizes), default=0)
    text_block_height = sum(line_height for _, line_height in line_sizes)
    text_block_height += line_spacing * max(len(lines) - 1, 0)

    box_padding_x = width // 18
    box_padding_y = font_size // 2
    box_width = min(width - horizontal_padding, text_block_width + box_padding_x * 2)
    box_height = text_block_height + box_padding_y * 2
    box_x = (width - box_width) // 2
    box_y = int(height * 0.62)
    box_y = min(box_y, height - box_height - height // 12)
    box_radius = 28

    box = (box_x, box_y, box_x + box_width, box_y + box_height)
    shadow_draw.rounded_rectangle(
        (box_x + 8, box_y + 10, box_x + box_width + 8, box_y + box_height + 10),
        radius=box_radius,
        fill=(0, 0, 0, 130),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    image = Image.alpha_composite(shadow, image)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=box_radius, fill=(0, 0, 0, 170))

    current_y = box_y + box_padding_y
    for line, (line_width, line_height) in zip(lines, line_sizes):
        line_x = (width - line_width) // 2
        draw.text(
            (line_x, current_y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 230),
        )
        current_y += line_height + line_spacing

    return np.array(image)


def add_scene_caption(clip: Any, text: str, width: int, height: int, duration: int) -> Any:
    try:
        from moviepy import CompositeVideoClip, ImageClip
    except ImportError as error:
        raise ProjectValidationError(
            "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    caption_clip = ImageClip(
        create_caption_image(text, width, height),
        transparent=True,
        duration=duration,
    )
    return CompositeVideoClip([clip, caption_clip], size=(width, height)).with_duration(
        duration
    )


def build_background_music(music_path: Path, duration: float, volume: float) -> Any:
    try:
        from moviepy import AudioFileClip, afx
    except ImportError as error:
        raise ProjectValidationError(
            "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    music = AudioFileClip(str(music_path))
    if music.duration is None or music.duration <= 0:
        music.close()
        raise ProjectValidationError(f"Music file has invalid duration: {music_path}")

    if music.duration < duration:
        music = music.with_effects([afx.AudioLoop(duration=duration)])
    else:
        music = music.subclipped(0, duration)

    return music.with_duration(duration).with_effects([afx.MultiplyVolume(volume)])


def require_scene_duration_and_text(scene: dict[str, Any]) -> tuple[int, str]:
    duration = scene.get("duration")
    text = scene.get("text")
    if not isinstance(duration, int) or duration <= 0:
        raise ProjectValidationError("Scene duration must be a positive integer.")
    if not isinstance(text, str) or not text:
        raise ProjectValidationError("Scene text must be a non-empty string.")

    return duration, text


def prepare_scene_clip(
    scene: dict[str, Any],
    clips_dir: Path,
    width: int,
    height: int,
) -> Any:
    try:
        from moviepy import VideoFileClip, vfx
    except ImportError as error:
        raise ProjectValidationError(
            "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    clip_name = scene.get("clip")
    duration, text = require_scene_duration_and_text(scene)
    if not isinstance(clip_name, str) or not clip_name:
        raise ProjectValidationError("Scene clip must be a non-empty string.")

    clip_path = clips_dir / clip_name
    if not clip_path.is_file():
        raise ProjectValidationError(f"Scene clip not found: {clip_path}")

    source_clip = VideoFileClip(str(clip_path))
    if source_clip.duration is None or source_clip.duration <= 0:
        source_clip.close()
        raise ProjectValidationError(f"Scene clip has invalid duration: {clip_path}")

    if source_clip.duration < duration:
        scene_clip = source_clip.with_effects([vfx.Loop(duration=duration)])
    else:
        scene_clip = source_clip.subclipped(0, duration)

    scene_clip = scene_clip.with_duration(duration)
    scene_clip = resize_and_crop_vertical(scene_clip, width, height)
    return add_scene_caption(scene_clip, text, width, height, duration)


def prepare_generated_scene_clip(
    scene: dict[str, Any],
    width: int,
    height: int,
) -> Any:
    try:
        from moviepy import ColorClip
    except ImportError as error:
        raise ProjectValidationError(
            "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    duration, text = require_scene_duration_and_text(scene)
    number = scene.get("number")
    scene_index = number if isinstance(number, int) and number > 0 else 1
    palette = [
        (24, 34, 45),
        (32, 47, 52),
        (47, 43, 38),
        (38, 44, 61),
        (45, 38, 51),
    ]
    color = palette[(scene_index - 1) % len(palette)]
    base_clip = ColorClip(size=(width, height), color=color, duration=duration)
    return add_scene_caption(base_clip, text, width, height, duration)


def prepare_scene_clips(
    scenes: list[dict[str, Any]],
    clips_dir: Path,
    settings: VideoAssemblySettings,
    media_source: str,
) -> list[Any]:
    if media_source == "generated":
        return [
            prepare_generated_scene_clip(scene, settings.width, settings.height)
            for scene in scenes
        ]

    if media_source == "local":
        return [
            prepare_scene_clip(scene, clips_dir, settings.width, settings.height)
            for scene in scenes
        ]

    if media_source == "mixed":
        generated_clips = []
        try:
            for scene in scenes:
                generated_clips.append(
                    prepare_generated_scene_clip(scene, settings.width, settings.height)
                )
            return generated_clips
        except ProjectValidationError:
            for clip in generated_clips:
                clip.close()
            return [
                prepare_scene_clip(scene, clips_dir, settings.width, settings.height)
                for scene in scenes
            ]

    raise ProjectValidationError(
        "Media source must be one of: generated, local, mixed."
    )


def assemble_video(
    scenes_data: dict[str, Any],
    config: dict[str, Any],
    paths: dict[str, Path],
) -> Path:
    scenes = scenes_data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ProjectValidationError("No scenes available for video assembly.")

    return assemble_video_from_scenes(
        scenes=scenes,
        clips_dir=paths["clips_dir"],
        music_dir=paths["music_dir"],
        output_dir=paths["output_dir"],
        settings=get_video_assembly_settings(config),
        media_source=get_media_source(config),
    )


def assemble_video_from_scenes(
    scenes: list[dict[str, Any]],
    clips_dir: Path,
    music_dir: Path,
    output_dir: Path,
    settings: VideoAssemblySettings,
    media_source: str = "local",
) -> Path:
    try:
        from moviepy import concatenate_videoclips
    except ImportError as error:
        raise ProjectValidationError(
            "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    if not scenes:
        raise ProjectValidationError("No scenes available for video assembly.")

    output_path = output_dir / settings.output_filename
    scene_clips = []
    final_clip = None
    background_music = None
    try:
        scene_clips = prepare_scene_clips(scenes, clips_dir, settings, media_source)
        final_clip = concatenate_videoclips(scene_clips, method="compose")
        music_path = get_background_music_path(music_dir)
        if music_path is not None:
            background_music = build_background_music(
                music_path,
                final_clip.duration,
                settings.music_volume,
            )
            final_clip = final_clip.with_audio(background_music)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_clip.write_videofile(
            str(output_path),
            fps=settings.fps,
            codec="libx264",
            audio=background_music is not None,
            audio_codec="aac" if background_music is not None else None,
            preset="medium",
            threads=4,
            logger=None,
            pixel_format="yuv420p",
        )
    finally:
        if final_clip is not None:
            final_clip.close()
        if background_music is not None:
            background_music.close()
        for clip in scene_clips:
            clip.close()

    return output_path
