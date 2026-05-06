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
.env.example
.gitignore
README.md
```

## Getting Started

1. Copy `.env.example` to `.env` and fill in required values.
2. Add a text plan to `input/plan.txt`.
3. Add source clips to `assets/clips/`.
4. Add background music to `assets/music/`.
5. Run:

```bash
python main.py
```

Generated files will be written to `output/` and `scripts/`.
