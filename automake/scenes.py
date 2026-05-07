import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automake.config import ProjectValidationError
from automake.media import get_clip_names
from automake.plan import VideoPlan


@dataclass(frozen=True)
class Scene:
    number: int
    duration: int
    text: str
    clip: str


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


def build_scene_plan(video_plan: VideoPlan, clip_names: list[str]) -> dict[str, Any]:
    if not clip_names:
        raise ProjectValidationError("At least one source clip is required.")

    scene_count = determine_scene_count(video_plan)
    durations = split_duration(video_plan.duration_seconds, scene_count)
    scene_texts = build_scene_texts(video_plan, scene_count)

    scenes = []
    for index, duration in enumerate(durations):
        scene = Scene(
            number=index + 1,
            duration=duration,
            text=scene_texts[index],
            clip=clip_names[index % len(clip_names)],
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


def generate_scenes(video_plan: VideoPlan, clips_dir: Path) -> dict[str, Any]:
    clip_names = get_clip_names(clips_dir)
    if not clip_names:
        raise ProjectValidationError(
            f"No .mp4 clips found in {clips_dir}. Add at least one source clip."
        )

    return build_scene_plan(video_plan, clip_names)


def save_scenes(scenes_data: dict[str, Any], scripts_dir: Path) -> Path:
    scenes_path = scripts_dir / "scenes.json"
    scenes_path.write_text(
        json.dumps(scenes_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return scenes_path
