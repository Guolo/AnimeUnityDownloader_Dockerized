"""Utility functions for managing download directories.

This module includes methods to sanitize directory names and create the
directory structure used to store downloaded episodes.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

from .config import DOWNLOAD_FOLDER


def sanitize_directory_name(directory_name: str) -> str:
    """Sanitize a given directory name.

    Replace invalid characters with underscores. Handles the invalid characters specific
    to Windows, macOS, and Linux.
    """
    invalid_chars_dict = {
        "nt": r'[\\/:*?"<>|]',  # Windows
        "posix": r"[/:]",       # macOS and Linux
    }
    invalid_chars = invalid_chars_dict.get(os.name)
    return re.sub(invalid_chars, "_", directory_name)


def create_download_directory(
    directory_name: str, custom_path: str | None = None, subfolder: str | None = None,
) -> str:
    """Create a directory for downloads if it doesn't exist.

    ``subfolder`` (if provided) is created *inside* the anime's own directory,
    e.g. .../Downloads/Anime Name/S3, useful for organizing by season.
    """
    sanitized_directory_name = sanitize_directory_name(directory_name)
    download_path = (
        Path(custom_path) / DOWNLOAD_FOLDER / sanitized_directory_name
        if custom_path is not None
        else Path(DOWNLOAD_FOLDER) / sanitized_directory_name
    )

    if subfolder:
        download_path = download_path / sanitize_directory_name(subfolder)

    try:
        Path(download_path).mkdir(parents=True, exist_ok=True)

    except OSError as os_err:
        message = f"Error creating directory: {os_err}"
        logging.exception(message)
        sys.exit(1)

    return download_path
