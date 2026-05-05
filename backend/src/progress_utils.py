"""Utility functions for tracking download progress using the Rich library.

This module includes features for creating a progress bar and a formatted progress table
specifically designed for monitoring the download status of current tasks.

Progress is also persisted to a `progress.json` file so external tools can read it.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

# Default path for the progress JSON file (can be overridden at runtime).
PROGRESS_JSON_PATH = Path("/app/frontend/progress.json")

# Internal lock so concurrent episode threads don't corrupt the JSON file.
_json_lock = threading.Lock()


def create_progress_bar() -> Progress:
    """Create a progress bar for tracking download progress."""
    return Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        "•",
        TimeRemainingColumn(),
    )


def create_progress_table(title: str, job_progress: Progress) -> Table:
    """Create a progress table for tracking the download status of the current task."""
    progress_table = Table.grid()
    progress_table.add_row(
        Panel.fit(
            job_progress,
            title=f"[b]{title}",
            border_style="red",
            padding=(1, 1),
        ),
    )
    return progress_table


def save_progress_json(
    anime_name: str,
    job_progress: Progress,
    overall_task_id: int,
    episode_tasks: dict[int, dict],
    json_path: Path = PROGRESS_JSON_PATH,
) -> None:
    """Persist the current download progress to a JSON file.

    Args:
        anime_name:       Name of the anime being downloaded.
        job_progress:     The Rich Progress instance managing all tasks.
        overall_task_id:  Task ID of the overall progress bar.
        episode_tasks:    Mapping of {task_id: {"index": int, "label": str}}.
        json_path:        Destination path for the JSON file.
    """
    tasks = {t.id: t for t in job_progress.tasks}

    # --- Overall progress ---
    overall = tasks.get(overall_task_id)
    if overall is not None:
        overall_completed = int(overall.completed)
        overall_total = int(overall.total) if overall.total else 0
        overall_pct = round(
            (overall_completed / overall_total * 100) if overall_total else 0.0, 1
        )
    else:
        overall_completed = overall_total = 0
        overall_pct = 0.0

    # --- Per-episode progress ---
    episodes = []
    for task_id, meta in episode_tasks.items():
        task = tasks.get(task_id)
        if task is None:
            continue
        pct = round(task.percentage, 1)
        episodes.append(
            {
                "id": meta["index"],
                "label": meta["label"],
                "percentage": pct,
                "done": pct >= 100.0,
            }
        )
    episodes.sort(key=lambda e: e["id"])

    payload = {
        "anime_name": anime_name,
        "overall": {
            "completed": overall_completed,
            "total": overall_total,
            "percentage": overall_pct,
        },
        "episodes": episodes,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
    }

    with _json_lock:
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
