from pathlib import Path


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
