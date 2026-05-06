# Automake

Python project for generating short vertical videos from a text plan and local media assets.

## Project Structure

```text
input/
assets/
  clips/
  music/
output/
scripts/
main.py
config.json
requirements.txt
.env.example
.gitignore
README.md
```

## Getting Started

1. Copy `.env.example` to `.env` and fill in required values.
2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

3. Add a text plan to `input/plan.txt`.
4. Add source `.mp4` clips to `assets/clips/`.
5. Run:

```bash
python3 main.py
```

Generated files will be written to `scripts/` and `output/final.mp4`.
