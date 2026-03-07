from __future__ import annotations

from pathlib import PurePosixPath


def split_relative_parts(relative_file_path: str) -> list[str]:
    path = PurePosixPath(relative_file_path.replace("\\", "/"))
    return list(path.parts[:-1])
