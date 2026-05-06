from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    input_plan = project_root / "input" / "plan.txt"
    output_dir = project_root / "output"

    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_plan.exists():
        print("Missing input/plan.txt. Create it before running the project.")
        return

    print("Project structure is ready.")
    print(f"Plan file: {input_plan}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
