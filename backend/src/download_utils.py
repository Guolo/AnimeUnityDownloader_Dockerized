"""Utilities for handling file downloads with progress tracking."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from .config import (
    DOWNLOAD_WORKERS,
    LARGE_FILE_CHUNK_SIZE,
    TASK_COLOR,
    THRESHOLDS,
)
from .progress_utils import save_progress_json

if TYPE_CHECKING:
    from requests import Response
    from rich.progress import Progress


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
    """Save a file to the specified path while tracking and updating progress."""
    job_progress, task, overall_task, anime_name, episode_tasks = task_info
    file_size = int(response.headers.get("Content-Length", -1))
    chunk_size = get_chunk_size(file_size)
    total_downloaded = 0

    with Path(final_path).open("wb") as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                file.write(chunk)
                total_downloaded += len(chunk)
                progress_percentage = (total_downloaded / file_size) * 100
                job_progress.update(task, completed=progress_percentage)
                # Persist progress to JSON after every chunk update
                save_progress_json(
                    anime_name, job_progress, overall_task, episode_tasks
                )

    job_progress.update(task, completed=100, visible=False)
    job_progress.advance(overall_task)
    # Final save to mark episode as 100% done
    save_progress_json(anime_name, job_progress, overall_task, episode_tasks)


def manage_running_tasks(futures: dict, job_progress: Progress) -> None:
    """Manage the status of running tasks and update their progress."""
    while futures:
        for future in list(futures.keys()):
            if future.running():
                task = futures.pop(future)
                job_progress.update(task, visible=True)


def run_in_parallel(
    func: callable,
    items: list,
    job_progress: Progress,
    anime_name: str,
    *args: tuple,
) -> None:
    """Execute a function in parallel for a list of items, updating progress.

    The ``anime_name`` parameter is forwarded to each worker so that every
    chunk write can persist progress to ``progress.json``.
    """
    num_items = len(items)
    futures = {}
    # Shared registry: task_id -> {index, label}  (populated before threads start)
    episode_tasks: dict[int, dict] = {}

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        overall_task = job_progress.add_task(
            f"[{TASK_COLOR}]Progress", total=num_items, visible=True,
        )
        for indx, item in enumerate(items):
            label = f"Episode {indx + 1}/{num_items}"
            task = job_progress.add_task(
                f"[{TASK_COLOR}]{label}",
                total=100,
                visible=False,
            )
            episode_tasks[task] = {"index": indx + 1, "label": label}
            # Pass anime_name and episode_tasks registry inside task_info
            task_info = (job_progress, task, overall_task, anime_name, episode_tasks)
            future = executor.submit(func, item, *args, task_info)
            futures[future] = task
            manage_running_tasks(futures, job_progress)
