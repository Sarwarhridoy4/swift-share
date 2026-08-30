import asyncio
import io
import mimetypes
import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import aiofiles
from .config import settings


class FileManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or settings.shared_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._mime_cache: dict[str, Optional[str]] = {}

    def _resolve_path(self, relative_path: str) -> Path:
        full_path = (self.base_dir / relative_path).resolve()
        if not str(full_path).startswith(str(self.base_dir.resolve())):
            raise ValueError("Path traversal detected")
        return full_path

    async def _run_sync(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def list_directory(self, relative_path: str = "") -> List[dict]:
        full_path = await asyncio.to_thread(self._resolve_path, relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        def _scan() -> List[dict]:
            items = []
            try:
                entries = sorted(os.scandir(full_path), key=lambda e: (not e.is_dir(), e.name.lower()))
            except (FileNotFoundError, NotADirectoryError):
                return items
            for entry in entries:
                try:
                    stat = entry.stat()
                    items.append({
                        "name": entry.name,
                        "path": str(Path(relative_path) / entry.name) if relative_path else entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except (PermissionError, FileNotFoundError):
                    continue
            return items

        return await asyncio.to_thread(_scan)

    async def get_file_info(self, relative_path: str) -> dict:
        full_path = self._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        if not exists:
            raise ValueError("File not found")

        stat = await asyncio.to_thread(full_path.stat)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        return {
            "name": full_path.name,
            "path": str(full_path.relative_to(self.base_dir)),
            "is_dir": is_dir,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def delete(self, relative_path: str) -> None:
        full_path = self._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        if not exists:
            raise ValueError("File not found")

        is_dir = await asyncio.to_thread(full_path.is_dir)
        if is_dir:
            await asyncio.to_thread(shutil.rmtree, full_path)
        else:
            await asyncio.to_thread(full_path.unlink)

    async def create_directory(self, relative_path: str, name: str) -> dict:
        parent = await asyncio.to_thread(self._resolve_path, relative_path)
        is_dir = await asyncio.to_thread(parent.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        new_dir = parent / name
        await asyncio.to_thread(new_dir.mkdir, exist_ok=True)
        stat = await asyncio.to_thread(new_dir.stat)
        return {
            "name": new_dir.name,
            "path": str(new_dir.relative_to(self.base_dir)),
            "is_dir": True,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def upload_file(self, relative_path: str, filename: str, content: bytes) -> dict:
        full_path = await asyncio.to_thread(self._resolve_path, relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        file_path = full_path / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        stat = await asyncio.to_thread(file_path.stat)
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(self.base_dir)),
            "is_dir": False,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def download_file(self, relative_path: str) -> tuple[str, bytes]:
        full_path = self._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not exists or is_dir:
            raise ValueError("File not found")

        async with aiofiles.open(full_path, "rb") as f:
            content = await f.read()
        return full_path.name, content

    async def iter_folder_files(self, relative_path: str):
        full_path = self._resolve_path(relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        root_path = str(full_path)

        def _walk():
            for dirpath, dirnames, filenames in os.walk(root_path):
                for filename in filenames:
                    abs_path = os.path.join(dirpath, filename)
                    arcname = os.path.relpath(abs_path, root_path)
                    yield abs_path, arcname

        for abs_path, arcname in await asyncio.to_thread(lambda: list(_walk())):
            yield abs_path, arcname

    async def download_folder(self, relative_path: str) -> tuple[str, io.BytesIO]:
        full_path = self._resolve_path(relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        zip_buffer = io.BytesIO()
        root_path = str(full_path)

        def _build_zip():
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=4) as zipf:
                for dirpath, dirnames, filenames in os.walk(root_path):
                    dirnames.sort()
                    for filename in filenames:
                        abs_path = os.path.join(dirpath, filename)
                        arcname = os.path.relpath(abs_path, root_path)
                        try:
                            zipf.write(abs_path, arcname)
                        except (PermissionError, OSError):
                            continue
            zip_buffer.seek(0)

        await asyncio.to_thread(_build_zip)
        return f"{full_path.name}.zip", zip_buffer

    async def read_preview(self, relative_path: str, max_size: int = 1024 * 1024) -> str:
        full_path = self._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not exists or is_dir:
            raise ValueError("File not found")

        stat = await asyncio.to_thread(full_path.stat)
        if stat.st_size > max_size:
            raise ValueError("File too large for preview")

        async with aiofiles.open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            return await f.read()

    def get_mime_type(self, relative_path: str) -> Optional[str]:
        full_path = self._resolve_path(relative_path)
        suffix = Path(full_path.suffix.lower()).suffix
        if not suffix:
            suffix = full_path.name.lower()
            if "." in suffix:
                suffix = "." + suffix.rsplit(".", 1)[-1]
            else:
                return None
        if suffix not in self._mime_cache:
            mime_type, _ = mimetypes.guess_type(f"x{suffix}")
            self._mime_cache[suffix] = mime_type
        return self._mime_cache[suffix]
