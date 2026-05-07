import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automake.config import ProjectValidationError, require_config_section


@dataclass(frozen=True)
class VideoPlan:
    topic: str
    duration_seconds: int
    style: str
    goal: str


def load_input_plan(input_plan_path: Path) -> str:
    plan = input_plan_path.read_text(encoding="utf-8").strip()
    if not plan:
        raise ProjectValidationError(f"Input plan is empty: {input_plan_path}")

    return plan


def extract_plan_field(plan: str, field_name: str) -> str | None:
    pattern = rf"^\s*{re.escape(field_name)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, plan, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None

    value = match.group(1).strip()
    return value or None


def parse_duration_seconds(plan: str, config: dict[str, Any]) -> int:
    video_config = require_config_section(config, "video")
    default_duration = int(video_config.get("min_duration_seconds", 15))
    min_duration = int(video_config.get("min_duration_seconds", default_duration))
    max_duration = int(video_config.get("max_duration_seconds", default_duration))

    duration_source = extract_plan_field(plan, "Длина") or extract_plan_field(
        plan, "Длительность"
    )
    if not duration_source:
        return default_duration

    match = re.search(r"\d+", duration_source)
    if not match:
        return default_duration

    duration = int(match.group(0))
    return max(min_duration, min(duration, max_duration))


def parse_video_plan(plan: str, config: dict[str, Any]) -> VideoPlan:
    topic = extract_plan_field(plan, "Тема")
    if not topic:
        first_line = next((line.strip() for line in plan.splitlines() if line.strip()), "")
        topic = first_line or "Короткий вертикальный ролик"

    return VideoPlan(
        topic=topic,
        duration_seconds=parse_duration_seconds(plan, config),
        style=extract_plan_field(plan, "Стиль") or "динамично и понятно",
        goal=extract_plan_field(plan, "Цель") or "удержать внимание зрителя до конца",
    )
