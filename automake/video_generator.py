from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from automake.config import ProjectValidationError


class VideoGenerator(ABC):
    @abstractmethod
    def generate_scene(self, scene: dict[str, Any]) -> Path:
        """Generate a video asset for one scene and return its path."""


def get_scene_duration(scene: dict[str, Any]) -> int:
    duration = scene.get("duration")
    if not isinstance(duration, int) or duration <= 0:
        raise ProjectValidationError("Scene duration must be a positive integer.")

    return duration


def get_generated_scene_asset_path(scene: dict[str, Any], generated_dir: Path) -> Path:
    clip_name = scene.get("clip")
    if isinstance(clip_name, str) and clip_name:
        clip_path = Path(clip_name)
        if clip_path.is_absolute():
            return clip_path
        if clip_path.parts and clip_path.parts[0] == "generated":
            return generated_dir / Path(*clip_path.parts[1:])
        return generated_dir / clip_path.name

    number = scene.get("number")
    scene_number = number if isinstance(number, int) and number > 0 else 1
    return generated_dir / f"scene_{scene_number:02d}.mp4"


class DummyVideoGenerator(VideoGenerator):
    def __init__(
        self,
        generated_dir: Path,
        width: int,
        height: int,
        fps: int,
    ) -> None:
        self.generated_dir = generated_dir
        self.width = width
        self.height = height
        self.fps = fps

    def generate_scene(self, scene: dict[str, Any]) -> Path:
        try:
            from moviepy import ColorClip
        except ImportError as error:
            raise ProjectValidationError(
                "MoviePy is not installed. Run: python3 -m pip install -r requirements.txt"
            ) from error

        duration = get_scene_duration(scene)
        output_path = get_generated_scene_asset_path(scene, self.generated_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        base_clip = ColorClip(
            size=(self.width, self.height),
            color=self.get_scene_color(scene),
            duration=duration,
        )
        try:
            base_clip.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx264",
                audio=False,
                preset="medium",
                threads=4,
                logger=None,
                pixel_format="yuv420p",
            )
        finally:
            base_clip.close()

        return output_path

    def get_scene_color(self, scene: dict[str, Any]) -> tuple[int, int, int]:
        number = scene.get("number")
        scene_index = number if isinstance(number, int) and number > 0 else 1
        palette = [
            (24, 34, 45),
            (32, 47, 52),
            (47, 43, 38),
            (38, 44, 61),
            (45, 38, 51),
        ]
        return palette[(scene_index - 1) % len(palette)]
