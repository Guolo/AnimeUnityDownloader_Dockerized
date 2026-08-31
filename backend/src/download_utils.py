"""Utilities for handling file downloads with progress tracking."""

from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from .config import (
    DOWNLOAD_WORKERS,
    LARGE_FILE_CHUNK_SIZE,
    THRESHOLDS,
)
from .progress_utils import save_progress_json

if TYPE_CHECKING:
    from requests import Response


def remove_special_characters(input_string: str) -> str:
    """Remove special characters from the input string."""
    return re.sub(r"[^a-zA-Z0-9_.-]", "", input_string)


def get_episode_filename(download_link: str) -> str | None:
    """Extract the file name from the provided episode download link."""
    if download_link:
        try:
            filename = unquote(download_link.split("=")[-1])  # Original name
            return remove_special_characters(filename)        # Cleaned name

        except IndexError as indx_err:
            message = f"Error while extracting the file name: {indx_err}"
            logging.exception(message)

    return None


def get_chunk_size(file_size: int) -> int:
    """Determine the optimal chunk size based on the file size."""
    for threshold, chunk_size in THRESHOLDS:
        if file_size < threshold:
            return chunk_size

    return LARGE_FILE_CHUNK_SIZE


def save_file_with_progress(
    response: Response,
    final_path: str,
    task_info: tuple,
) -> None:
    """Save a file to the specified path while tracking and persisting progress."""
    episode_index, anime_name, episodes_progress, progress_lock = task_info
    file_size = int(response.headers.get("Content-Length", -1))
    chunk_size = get_chunk_size(file_size)
    total_downloaded = 0

    with Path(final_path).open("wb") as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                file.write(chunk)
                total_downloaded += len(chunk)
                percentage = (
                    (total_downloaded / file_size) * 100 if file_size > 0 else 0.0
                )
                with progress_lock:
                    episodes_progress[episode_index]["percentage"] = percentage
                    save_progress_json(anime_name, episodes_progress)

    # Final save to mark episode as 100% done
    with progress_lock:
        episodes_progress[episode_index]["percentage"] = 100.0
        save_progress_json(anime_name, episodes_progress)


def run_in_parallel(
    func: callable,
    items: list,
    anime_name: str,
    *args: tuple,
) -> None:
    """Execute a function in parallel for a list of items, tracking progress.

    Progress for every item is kept in a shared dict (protected by a lock) and
    persisted to ``progress.json`` after each update, so the web frontend can
    poll it. There is no terminal UI involved.
    """
    num_items = len(items)
    episodes_progress: dict[int, dict] = {
        indx + 1: {"label": f"Episode {indx + 1}/{num_items}", "percentage": 0.0}
        for indx in range(num_items)
    }
    progress_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        futures = [
            executor.submit(
                func,
                item,
                *args,
                (indx + 1, anime_name, episodes_progress, progress_lock),
            )
            for indx, item in enumerate(items)
        ]
        for future in futures:
            future.result()
