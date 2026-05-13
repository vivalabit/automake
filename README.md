# Automake

Python project for generating short vertical videos from a text plan and local media assets.

## Project Structure

```text
automake/
  config.py
  media.py
  plan.py
  scenes.py
  script.py
  video_generator.py
  video_editor.py
input/
assets/
  clips/
  generated/
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

`main.py` orchestrates the default pipeline. The reusable parts live in `automake/`:

- `plan.py` parses the text plan into a video plan.
- `script.py` creates and saves the script artifact.
- `scenes.py` creates and saves scene plans with video-generation prompts.
- `video_generator.py` defines the video provider interface and dummy provider.
- `video_editor.py` assembles a video from prepared scenes and clips.
- `media.py` finds source clips and music assets.
- `config.py` loads config and validates project paths.

Media source modes are configured in `config.json`:

```json
{
  "media": {
    "source": "local"
  }
}
```

- `local` uses `.mp4` clips from `assets/clips/`.
- `generated` creates scene videos in `assets/generated/` and references them as `generated/scene_01.mp4`.
- `mixed` tries generated scene videos first, then falls back to local clips.

Each scene includes a visual `prompt` for video generation. Prompts describe the shot
and motion, while on-screen text is handled by Automake captions instead of the
generated video.

`DummyVideoGenerator` creates simple color placeholder videos so generated and mixed
pipelines can run without a paid video-generation API.

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
