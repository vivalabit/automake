from pathlib import Path

from automake.plan import VideoPlan


def generate_script(video_plan: VideoPlan) -> str:
    return "\n".join(
        [
            f"Тема: {video_plan.topic}",
            f"Длительность: {video_plan.duration_seconds} секунд",
            f"Стиль: {video_plan.style}",
            f"Цель: {video_plan.goal}",
            "",
            "Сценарий:",
            f"1. Хук: {video_plan.topic}. Начни с короткой фразы, которая сразу показывает проблему или пользу для зрителя.",
            "2. Контекст: объясни, почему тема важна именно сейчас и что зритель узнает за следующие секунды.",
            "3. Основная мысль: дай 2-3 конкретных пункта без длинных вступлений.",
            "4. Пример: покажи, как это выглядит на практике, простым языком и в одном визуальном действии.",
            f"5. Финал: заверши призывом, связанным с целью ролика: {video_plan.goal}.",
            "",
            "Текст для озвучки:",
            f"Если ты работаешь с темой «{video_plan.topic}», начни с главной ошибки или выгоды. "
            "Покажи суть быстро, подкрепи ее примером и закончи понятным действием для зрителя.",
        ]
    )


def save_script(script_text: str, scripts_dir: Path) -> Path:
    script_path = scripts_dir / "script.txt"
    script_path.write_text(script_text + "\n", encoding="utf-8")
    return script_path
