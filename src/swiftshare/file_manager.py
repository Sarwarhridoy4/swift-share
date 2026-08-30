import os
import shutil
import zipfile
import io
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import aiofiles
from .config import settings


class FileManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or settings.shared_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, relative_path: str) -> Path:
        full_path = (self.base_dir / relative_path).resolve()
        if not str(full_path).startswith(str(self.base_dir.resolve())):
            raise ValueError("Path traversal detected")
        return full_path

    async def list_directory(self, relative_path: str = "") -> List[dict]:
        full_path = self._resolve_path(relative_path)
        if not full_path.is_dir():
            raise ValueError("Not a directory")

        items = []
        for entry in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry.relative_to(self.base_dir)),
                "is_dir": entry.is_dir(),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return items

    async def get_file_info(self, relative_path: str) -> dict:
        full_path = self._resolve_path(relative_path)
        if not full_path.exists():
            raise ValueError("File not found")

        stat = full_path.stat()
        return {
            "name": full_path.name,
            "path": str(full_path.relative_to(self.base_dir)),
            "is_dir": full_path.is_dir(),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def delete(self, relative_path: str) -> None:
        full_path = self._resolve_path(relative_path)
        if not full_path.exists():
            raise ValueError("File not found")

        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()

    async def create_directory(self, relative_path: str, name: str) -> dict:
        full_path = self._resolve_path(relative_path)
        if not full_path.is_dir():
            raise ValueError("Parent is not a directory")

        new_dir = full_path / name
        new_dir.mkdir(exist_ok=True)
        stat = new_dir.stat()
        return {
            "name": new_dir.name,
            "path": str(new_dir.relative_to(self.base_dir)),
            "is_dir": True,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def upload_file(self, relative_path: str, filename: str, content: bytes) -> dict:
        full_path = self._resolve_path(relative_path)
        if not full_path.is_dir():
            raise ValueError("Parent is not a directory")

        file_path = full_path / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(self.base_dir)),
            "is_dir": False,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def download_file(self, relative_path: str) -> tuple[str, bytes]:
        full_path = self._resolve_path(relative_path)
        if not full_path.exists() or full_path.is_dir():
            raise ValueError("File not found")

        async with aiofiles.open(full_path, "rb") as f:
            content = await f.read()

        return full_path.name, content

    async def download_folder(self, relative_path: str) -> tuple[str, bytes]:
        full_path = self._resolve_path(relative_path)
        if not full_path.is_dir():
            raise ValueError("Not a directory")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in full_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(full_path)
                    zipf.write(file_path, arcname)

        return f"{full_path.name}.zip", zip_buffer.getvalue()

    async def read_preview(self, relative_path: str, max_size: int = 1024 * 1024) -> str:
        full_path = self._resolve_path(relative_path)
        if not full_path.exists() or full_path.is_dir():
            raise ValueError("File not found")

        stat = full_path.stat()
        if stat.st_size > max_size:
            raise ValueError("File too large for preview")

        async with aiofiles.open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = await f.read()
        return content

    def get_mime_type(self, relative_path: str) -> Optional[str]:
        import mimetypes
        full_path = self._resolve_path(relative_path)
        mime_type, _ = mimetypes.guess_type(str(full_path))
        return mime_type