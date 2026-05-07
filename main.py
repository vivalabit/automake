from pathlib import Path

from automake.config import ProjectValidationError, load_config, validate_project_paths
from automake.media import get_media_source
from automake.plan import load_input_plan, parse_video_plan
from automake.scenes import generate_scenes, save_scenes
from automake.script import generate_script, save_script
from automake.video_editor import assemble_video


def main() -> None:
    project_root = Path(__file__).resolve().parent
    config_path = project_root / "config.json"

    try:
        config = load_config(config_path)
        paths = validate_project_paths(project_root, config)
        media_source = get_media_source(config)
        plan = load_input_plan(paths["input_plan"])
        video_plan = parse_video_plan(plan, config)
        script_path = save_script(generate_script(video_plan), paths["scripts_dir"])
        scenes_data = generate_scenes(video_plan, paths["clips_dir"], media_source)
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
    print(f"Media source: {media_source}")
    print(f"Script file: {script_path}")
    print(f"Scenes file: {scenes_path}")
    print(f"Video file: {output_path}")
    print(f"Config file: {config_path}")
    print(f"Output directory: {paths['output_dir']}")


if __name__ == "__main__":
    main()
