import json
import re
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


def main() -> None:
    project_root = Path(__file__).resolve().parent
    config_path = project_root / "config.json"

    try:
        config = load_config(config_path)
        paths = validate_project_paths(project_root, config)
        plan = load_input_plan(paths["input_plan"])
        video_plan = parse_video_plan(plan, config)
        script_path = save_script(generate_script(video_plan), paths["scripts_dir"])
        scenes_path = save_scenes(
            generate_scenes(video_plan, paths["clips_dir"]),
            paths["scripts_dir"],
        )
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
    print(f"Config file: {config_path}")
    print(f"Output directory: {paths['output_dir']}")


if __name__ == "__main__":
    main()
