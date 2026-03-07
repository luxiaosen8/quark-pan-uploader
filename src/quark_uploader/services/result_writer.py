from __future__ import annotations

from pathlib import Path


class ResultWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.share_links_path = self.output_dir / "share_links.txt"

    def append_share_url(self, url: str) -> None:
        with self.share_links_path.open("a", encoding="utf-8") as handle:
            handle.write(url + "\n")
