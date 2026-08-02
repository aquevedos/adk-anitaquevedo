"""Utilities for file handling and smart logging."""

import logging
import os
import random
import string

ENABLE_FILE_LOGGING = False


def truncate(text: str, max_len: int = 500) -> str:
  """Truncates a string for logging, indicating remaining characters."""
  if len(text) <= max_len:
    return text
  return (
      text[:max_len]
      + f"\n... [Truncated, {len(text) - max_len} characters remaining]"
  )


def log_to_file(content: str, filename_base: str) -> None:
  """Writes content to a unique file in /tmp or logs truncated version based on settings."""
  if ENABLE_FILE_LOGGING:
    suffix = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    file_path = os.path.join("/tmp", f"{filename_base}_{suffix}")
    try:
      with open(file_path, "w") as f:
        f.write(content)
      logging.info(f"Saved {filename_base} to: {file_path}")
    except Exception as e:
      logging.warning(f"Could not save to {file_path}: {e}")
  else:
    logging.info(f"{filename_base}:\n{truncate(content, 500)}")
