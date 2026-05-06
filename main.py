import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProjectValidationError(Exception):
    """Raised when required project inputs are missing or invalid."""


@dataclass(frozen=True)
class VideoPlan:
    topic: str
    duration_seconds: int
    style: str
    goal: str


@dataclass(frozen=True)
class Scene:
    number: int
    duration: int
    text: str
    clip: str


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise ProjectValidationError(f"Missing config file: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as error:
        raise ProjectValidationError(
            f"Invalid JSON in {config_path}: {error.msg}"
        ) from error

    if not isinstance(config, dict):
        raise ProjectValidationError("config.json must contain a JSON object.")

    return config


def require_config_section(config: dict[str, Any], section: str) -> dict[str, Any]:
    value = config.get(section)
    if not isinstance(value, dict):
        raise ProjectValidationError(f"Missing or invalid config section: {section}")

    return value


def resolve_project_path(project_root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        return path

    return project_root / path


def validate_project_paths(project_root: Path, config: dict[str, Any]) -> dict[str, Path]:
    paths_config = require_config_section(config, "paths")

    required_path_keys = (
        "input_plan",
        "clips_dir",
        "music_dir",
        "output_dir",
        "scripts_dir",
    )
    missing_keys = [key for key in required_path_keys if key not in paths_config]
    if missing_keys:
        raise ProjectValidationError(
            f"Missing config path keys: {', '.join(missing_keys)}"
        )

    paths: dict[str, Path] = {}
    for key in required_path_keys:
        value = paths_config[key]
        if not isinstance(value, str) or not value.strip():
            raise ProjectValidationError(f"Config path '{key}' must be a string.")
        paths[key] = resolve_project_path(project_root, value)

    required_dirs = ("clips_dir", "music_dir", "output_dir", "scripts_dir")
    missing_dirs = [str(paths[key]) for key in required_dirs if not paths[key].is_dir()]
    if missing_dirs:
        raise ProjectValidationError(
            "Missing required directories: " + ", ".join(missing_dirs)
        )

    input_plan = paths["input_plan"]
    if not input_plan.is_file():
        raise ProjectValidationError(f"Missing input plan file: {input_plan}")

    return paths


def load_input_plan(input_plan_path: Path) -> str:
    plan = input_plan_path.read_text(encoding="utf-8").strip()
    if not plan:
        raise ProjectValidationError(f"Input plan is empty: {input_plan_path}")

    return plan


def extract_plan_field(plan: str, field_name: str) -> str | None:
    pattern = rf"^\s*{re.escape(field_name)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, plan, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None

    value = match.group(1).strip()
    return value or None


def parse_duration_seconds(plan: str, config: dict[str, Any]) -> int:
    video_config = require_config_section(config, "video")
    default_duration = int(video_config.get("min_duration_seconds", 15))
    min_duration = int(video_config.get("min_duration_seconds", default_duration))
    max_duration = int(video_config.get("max_duration_seconds", default_duration))

    duration_source = extract_plan_field(plan, "Длина") or extract_plan_field(
        plan, "Длительность"
    )
    if not duration_source:
        return default_duration

    match = re.search(r"\d+", duration_source)
    if not match:
        return default_duration

    duration = int(match.group(0))
    return max(min_duration, min(duration, max_duration))


def parse_video_plan(plan: str, config: dict[str, Any]) -> VideoPlan:
    topic = extract_plan_field(plan, "Тема")
    if not topic:
        first_line = next((line.strip() for line in plan.splitlines() if line.strip()), "")
        topic = first_line or "Короткий вертикальный ролик"

    return VideoPlan(
        topic=topic,
        duration_seconds=parse_duration_seconds(plan, config),
        style=extract_plan_field(plan, "Стиль") or "динамично и понятно",
        goal=extract_plan_field(plan, "Цель") or "удержать внимание зрителя до конца",
    )


def generate_script(video_plan: VideoPlan) -> str:
    return "\n".join(
        [
            f"Тема: {video_plan.topic}",
            f"Длительность: {video_plan.duration_seconds} секунд",
            f"Стиль: {video_plan.style}",
            f"Цель: {video_plan.goal}",
            "",
            "Сценарий:",
            f"1. Хук: {video_plan.topic}. Начни с короткой фразы, которая сразу показывает проблему или пользу для зрителя.",
            "2. Контекст: объясни, почему тема важна именно сейчас и что зритель узнает за следующие секунды.",
            "3. Основная мысль: дай 2-3 конкретных пункта без длинных вступлений.",
            "4. Пример: покажи, как это выглядит на практике, простым языком и в одном визуальном действии.",
            f"5. Финал: заверши призывом, связанным с целью ролика: {video_plan.goal}.",
            "",
            "Текст для озвучки:",
            f"Если ты работаешь с темой «{video_plan.topic}», начни с главной ошибки или выгоды. "
            "Покажи суть быстро, подкрепи ее примером и закончи понятным действием для зрителя.",
        ]
    )


def save_script(script_text: str, scripts_dir: Path) -> Path:
    script_path = scripts_dir / "script.txt"
    script_path.write_text(script_text + "\n", encoding="utf-8")
    return script_path


def get_clip_names(clips_dir: Path) -> list[str]:
    return [
        path.name
        for path in sorted(clips_dir.iterdir())
        if path.is_file() and path.suffix.lower() == ".mp4"
    ]


def split_duration(total_duration: int, scene_count: int) -> list[int]:
    base_duration = total_duration // scene_count
    remainder = total_duration % scene_count

    return [
        base_duration + (1 if index < remainder else 0)
        for index in range(scene_count)
    ]


def determine_scene_count(video_plan: VideoPlan) -> int:
    if video_plan.duration_seconds <= 18:
        return 3
    if video_plan.duration_seconds <= 24:
        return 4
    return 5


def build_scene_texts(video_plan: VideoPlan, scene_count: int) -> list[str]:
    scene_templates = [
        f"{video_plan.topic}: начни с главной проблемы или выгоды.",
        "Покажи, почему это важно для зрителя прямо сейчас.",
        "Дай первый конкретный пункт без длинного вступления.",
        "Добавь пример, который легко понять с одного взгляда.",
        f"Заверши действием: {video_plan.goal}.",
    ]

    if scene_count == 3:
        return [
            scene_templates[0],
            f"{scene_templates[2]} {scene_templates[3]}",
            scene_templates[4],
        ]
    if scene_count == 4:
        return [
            scene_templates[0],
            scene_templates[1],
            f"{scene_templates[2]} {scene_templates[3]}",
            scene_templates[4],
        ]

    return scene_templates


def generate_scenes(video_plan: VideoPlan, clips_dir: Path) -> dict[str, Any]:
    scene_count = determine_scene_count(video_plan)
    durations = split_duration(video_plan.duration_seconds, scene_count)
    scene_texts = build_scene_texts(video_plan, scene_count)
    clip_names = get_clip_names(clips_dir)
    if not clip_names:
        raise ProjectValidationError(
            f"No .mp4 clips found in {clips_dir}. Add at least one source clip."
        )

    scenes = []
    for index, duration in enumerate(durations):
        clip = clip_names[index % len(clip_names)]
        scene = Scene(
            number=index + 1,
            duration=duration,
            text=scene_texts[index],
            clip=clip,
        )
        scenes.append(
            {
                "number": scene.number,
                "duration": scene.duration,
                "text": scene.text,
                "clip": scene.clip,
            }
        )

    return {
        "title": video_plan.topic,
        "duration": video_plan.duration_seconds,
        "format": "vertical",
        "scenes": scenes,
    }


def save_scenes(scenes_data: dict[str, Any], scripts_dir: Path) -> Path:
    scenes_path = scripts_dir / "scenes.json"
    scenes_path.write_text(
        json.dumps(scenes_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return scenes_path


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
    return CompositeVideoClip([clip, caption_clip], size=(width, height)).with_duration(duration)


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
    duration = scene.get("duration")
    text = scene.get("text")
    if not isinstance(clip_name, str) or not clip_name:
        raise ProjectValidationError("Scene clip must be a non-empty string.")
    if not isinstance(duration, int) or duration <= 0:
        raise ProjectValidationError("Scene duration must be a positive integer.")
    if not isinstance(text, str) or not text:
        raise ProjectValidationError("Scene text must be a non-empty string.")

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


def assemble_video(scenes_data: dict[str, Any], config: dict[str, Any], paths: dict[str, Path]) -> Path:
    try:
        from moviepy import concatenate_videoclips
    except ImportError as error:
        raise ProjectValidationError(
            "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    video_config = require_config_section(config, "video")
    width = int(video_config.get("width", 1080))
    height = int(video_config.get("height", 1920))
    fps = int(video_config.get("fps", 30))
    output_filename = str(video_config.get("output_filename", "final.mp4"))
    output_path = paths["output_dir"] / output_filename

    scenes = scenes_data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ProjectValidationError("No scenes available for video assembly.")

    scene_clips = []
    final_clip = None
    try:
        scene_clips = [
            prepare_scene_clip(scene, paths["clips_dir"], width, height)
            for scene in scenes
        ]
        final_clip = concatenate_videoclips(scene_clips, method="compose")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_clip.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio=False,
            preset="medium",
            threads=4,
            logger=None,
            pixel_format="yuv420p",
        )
    finally:
        if final_clip is not None:
            final_clip.close()
        for clip in scene_clips:
            clip.close()

    return output_path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    config_path = project_root / "config.json"

    try:
        config = load_config(config_path)
        paths = validate_project_paths(project_root, config)
        plan = load_input_plan(paths["input_plan"])
        video_plan = parse_video_plan(plan, config)
        script_path = save_script(generate_script(video_plan), paths["scripts_dir"])
        scenes_data = generate_scenes(video_plan, paths["clips_dir"])
        scenes_path = save_scenes(
            scenes_data,
            paths["scripts_dir"],
        )
        output_path = assemble_video(scenes_data, config, paths)
    except ProjectValidationError as error:
        print(f"Validation error: {error}")
        return

    print("Project inputs loaded successfully.")
    print(f"Plan file: {paths['input_plan']}")
    print(f"Plan length: {len(plan)} characters")
    print(f"Topic: {video_plan.topic}")
    print(f"Duration: {video_plan.duration_seconds} seconds")
    print(f"Script file: {script_path}")
    print(f"Scenes file: {scenes_path}")
    print(f"Video file: {output_path}")
    print(f"Config file: {config_path}")
    print(f"Output directory: {paths['output_dir']}")


if __name__ == "__main__":
    main()
