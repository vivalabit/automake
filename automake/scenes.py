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
    clip: str | None = None
    prompt: str | None = None
    fallback_clip: str | None = None


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


def infer_visual_subject(video_plan: VideoPlan, scene_text: str) -> str:
    scene_source = scene_text.casefold()
    topic_source = video_plan.topic.casefold()

    if (
        ("длин" in scene_source and "начал" in scene_source)
        or "long intro" in scene_source
    ):
        return (
            "close-up of a beginner editing timeline, cutting a long intro into "
            "quick clips"
        )
    if "важно" in scene_source or "сейчас" in scene_source:
        return (
            "creator rapidly improving a vertical video edit while audience "
            "attention drops"
        )
    if "пример" in scene_source:
        return (
            "hands trimming dead air from a vertical video timeline, quick "
            "before-and-after pacing demonstration"
        )
    if "пункт" in scene_source:
        return "hands making three precise cuts in a vertical video timeline"
    if (
        "действ" in scene_source
        or "сохрани" in scene_source
        or "финал" in scene_source
    ):
        return (
            "creator exporting a polished vertical video after organizing clips "
            "on an editing timeline"
        )
    if "ошиб" in scene_source and (
        "монтаж" in topic_source or "editing" in topic_source
    ):
        return (
            "close-up of a beginner editing timeline, fixing common editing "
            "mistakes"
        )
    if "монтаж" in topic_source or "editing" in topic_source:
        return "hands editing a vertical social media video on a modern timeline"

    return (
        "cinematic b-roll visualizing the scene idea with a creator working on "
        "a vertical video"
    )


def build_scene_prompt(video_plan: VideoPlan, scene_text: str) -> str:
    subject = infer_visual_subject(video_plan, scene_text)
    return (
        "Vertical 9:16 short video, fast energetic editing, "
        f"{subject}, dynamic camera movement, realistic modern workspace, "
        "no text on screen, no captions, no subtitles, no readable letters, no logos"
    )


def get_generated_clip_name(scene_number: int) -> str:
    return f"generated/scene_{scene_number:02d}.mp4"


def build_scene_plan(
    video_plan: VideoPlan,
    clip_names: list[str] | None = None,
    use_generated_assets: bool = False,
) -> dict[str, Any]:
    scene_count = determine_scene_count(video_plan)
    durations = split_duration(video_plan.duration_seconds, scene_count)
    scene_texts = build_scene_texts(video_plan, scene_count)

    scenes = []
    for index, duration in enumerate(durations):
        scene_number = index + 1
        clip_name = None
        prompt = build_scene_prompt(video_plan, scene_texts[index])
        fallback_clip = None
        if clip_names:
            clip_name = clip_names[index % len(clip_names)]
        if use_generated_assets:
            fallback_clip = clip_name
            clip_name = get_generated_clip_name(scene_number)

        scene = Scene(
            number=scene_number,
            duration=duration,
            text=scene_texts[index],
            clip=clip_name,
            prompt=prompt,
            fallback_clip=fallback_clip,
        )
        scene_data: dict[str, Any] = {
            "number": scene.number,
            "duration": scene.duration,
            "text": scene.text,
        }
        if scene.prompt is not None:
            scene_data["prompt"] = scene.prompt
        if scene.clip is not None:
            scene_data["clip"] = scene.clip
        if scene.fallback_clip is not None:
            scene_data["fallback_clip"] = scene.fallback_clip
        scenes.append(scene_data)

    return {
        "title": video_plan.topic,
        "duration": video_plan.duration_seconds,
        "format": "vertical",
        "scenes": scenes,
    }


def generate_scenes(
    video_plan: VideoPlan,
    clips_dir: Path,
    media_source: str = "local",
) -> dict[str, Any]:
    clip_names = get_clip_names(clips_dir)
    if media_source == "local" and not clip_names:
        raise ProjectValidationError(
            f"No .mp4 clips found in {clips_dir}. Add at least one source clip."
        )
    if media_source == "generated":
        return build_scene_plan(video_plan, use_generated_assets=True)

    return build_scene_plan(
        video_plan,
        clip_names,
        use_generated_assets=media_source == "mixed",
    )


def save_scenes(scenes_data: dict[str, Any], scripts_dir: Path) -> Path:
    scenes_path = scripts_dir / "scenes.json"
    scenes_path.write_text(
        json.dumps(scenes_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return scenes_path
