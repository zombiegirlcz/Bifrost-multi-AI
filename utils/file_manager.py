"""
Bifrost 2.0 — File manager pro výstupní projekty
"""
import os
import json
import aiofiles
from pathlib import Path
from datetime import datetime


class FileManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.project_dir: Path | None = None

    def create_project(self, task_name: str) -> Path:
        """Vytvoří nový projektový adresář."""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_name[:40])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_dir = self.output_dir / f"{timestamp}_{safe_name}"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # Vytvoř log adresář
        (self.project_dir / "iterations").mkdir(exist_ok=True)
        return self.project_dir

    async def save_code(self, filename: str, content: str) -> Path:
        filepath = self.project_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(filepath, "w") as f:
            await f.write(content)
        return filepath

    async def save_iteration(self, iteration: int, phase: str, data: dict):
        """Uloží stav iterace pro debugging."""
        iter_dir = self.project_dir / "iterations" / f"iter_{iteration:03d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(iter_dir / f"{phase}.json", "w") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    async def read_file(self, filename: str) -> str:
        filepath = self.project_dir / filename
        async with aiofiles.open(filepath, "r") as f:
            return await f.read()

    def list_files(self) -> list[str]:
        if not self.project_dir:
            return []
        return [
            str(p.relative_to(self.project_dir))
            for p in self.project_dir.rglob("*")
            if p.is_file() and "iterations" not in str(p)
        ]
