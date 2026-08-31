"""Utility functions for tracking download progress and persisting it to progress.json.

No terminal UI is involved: progress is kept in a plain in-memory structure and
written to a JSON file that the web frontend reads to show progress to the user.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

# Default path for the progress JSON file (can be overridden at runtime).
PROGRESS_JSON_PATH = Path("/app/frontend/progress.json")

# Internal lock so concurrent episode threads don't corrupt the JSON file.
_json_lock = threading.Lock()


def save_progress_json(
    anime_name: str,
    episodes_progress: dict[int, dict],
    json_path: Path = PROGRESS_JSON_PATH,
) -> None:
    """Persist the current download progress to a JSON file.

    Args:
        anime_name: Name of the anime being downloaded.
        episodes_progress: Mapping of
            {episode_index: {"label": str, "percentage": float}}.
        json_path: Destination path for the JSON file.
    """
    episodes = [
        {
            "id": index,
            "label": data["label"],
            "percentage": round(data["percentage"], 1),
            "done": data["percentage"] >= 100.0,
        }
        for index, data in sorted(episodes_progress.items())
    ]

    total = len(episodes)
    completed = sum(1 for episode in episodes if episode["done"])
    overall_pct = round((completed / total * 100) if total else 0.0, 1)

    payload = {
        "anime_name": anime_name,
        "overall": {
            "completed": completed,
            "total": total,
            "percentage": overall_pct,
        },
        "episodes": episodes,
        "last_updated": datetime.now().isoformat(timespec="seconds"),
    }

    with _json_lock:
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
