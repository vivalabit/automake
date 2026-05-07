import json
from pathlib import Path
from typing import Any


class ProjectValidationError(Exception):
    """Raised when required project inputs are missing or invalid."""


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
