from pathlib import Path
from typing import Any

from automake.config import ProjectValidationError


MEDIA_SOURCES = {"local", "generated", "mixed"}


def get_media_source(config: dict[str, Any]) -> str:
    media_config = config.get("media", {})
    if not isinstance(media_config, dict):
        raise ProjectValidationError("Config section 'media' must be a JSON object.")

    source = media_config.get("source", "local")
    if not isinstance(source, str):
        raise ProjectValidationError("Config media.source must be a string.")

    source = source.strip().lower()
    if source not in MEDIA_SOURCES:
        raise ProjectValidationError(
            "Config media.source must be one of: "
            + ", ".join(sorted(MEDIA_SOURCES))
        )

    return source


def get_clip_names(clips_dir: Path) -> list[str]:
    return [
        path.name
        for path in sorted(clips_dir.iterdir())
        if path.is_file() and path.suffix.lower() == ".mp4"
    ]


def get_background_music_path(music_dir: Path) -> Path | None:
    preferred_music = music_dir / "music.mp3"
    if preferred_music.is_file():
        return preferred_music

    music_files = sorted(
        path
        for path in music_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".mp3"
    )
    return music_files[0] if music_files else None
