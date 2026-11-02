import asyncio
import io
import mimetypes
import os
import shutil
import zipfile
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple, AsyncIterator
import aiofiles
from .config import settings


class DirectoryCacheEntry:
    def __init__(self, items: List[dict], ttl: float = 2.0):
        self.items = items
        self.expires_at = time.monotonic() + ttl

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class FileManager:
    def __init__(self, base_dir: Optional[Path] = None, cache_ttl: float = 2.0):
        self.base_dir = (base_dir or settings.shared_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._mime_cache: dict[str, Optional[str]] = {}
        self._dir_cache: dict[str, DirectoryCacheEntry] = {}
        self._cache_ttl = cache_ttl
        self._dir_size_cache: dict[str, Tuple[int, float]] = {}
        self._dir_size_cache_ttl = 10.0

    def _resolve_path(self, relative_path: str) -> Path:
        full_path = (self.base_dir / relative_path).resolve()
        base_resolved = str(self.base_dir.resolve())
        full_resolved = str(full_path)
        if full_resolved != base_resolved and not full_resolved.startswith(base_resolved + os.sep):
            raise ValueError("Path traversal detected")
        return full_path

    def _invalidate_dir_cache(self, relative_path: str) -> None:
        keys_to_remove = [k for k in self._dir_cache if k == relative_path or k.startswith(relative_path + "/")]
        for k in keys_to_remove:
            self._dir_cache.pop(k, None)

    def _get_cached_dir(self, relative_path: str) -> Optional[List[dict]]:
        entry = self._dir_cache.get(relative_path)
        if entry and not entry.is_expired():
            return entry.items
        if entry:
            self._dir_cache.pop(relative_path, None)
        return None

    def _set_cached_dir(self, relative_path: str, items: List[dict]) -> None:
        self._dir_cache[relative_path] = DirectoryCacheEntry(items, ttl=self._cache_ttl)

    def _get_cached_dir_size(self, path_str: str) -> Optional[int]:
        entry = self._dir_size_cache.get(path_str)
        if entry and time.monotonic() < entry[1]:
            return entry[0]
        if entry:
            self._dir_size_cache.pop(path_str, None)
        return None

    def _set_cached_dir_size(self, path_str: str, size: int) -> None:
        self._dir_size_cache[path_str] = (size, time.monotonic() + self._dir_size_cache_ttl)

    def _dir_size_sync(self, path: str | Path) -> int:
        path_str = str(path)
        cached = self._get_cached_dir_size(path_str)
        if cached is not None:
            return cached
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(str(path)):
                dirnames.sort()
                for filename in filenames:
                    abs_path = os.path.join(dirpath, filename)
                    try:
                        total += os.path.getsize(abs_path)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        self._set_cached_dir_size(path_str, total)
        return total

    async def _run_sync(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def list_directory(
        self, relative_path: str = "", limit: int = 200, offset: int = 0
    ) -> Tuple[List[dict], int]:
        full_path = await asyncio.to_thread(self._resolve_path, relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        cached = self._get_cached_dir(relative_path)
        if cached is not None:
            total = len(cached)
            return cached[offset:offset + limit], total

        def _scan() -> List[dict]:
            items = []
            try:
                entries = sorted(os.scandir(full_path), key=lambda e: (not e.is_dir(), e.name.lower()))
            except (FileNotFoundError, NotADirectoryError):
                return items
            for entry in entries:
                try:
                    stat = entry.stat()
                    size = stat.st_size
                    if entry.is_dir(follow_symlinks=False):
                        size = self._dir_size_sync(entry.path)
                    items.append({
                        "name": entry.name,
                        "path": str(Path(relative_path) / entry.name) if relative_path else entry.name,
                        "is_dir": entry.is_dir(),
                        "size": size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except (PermissionError, FileNotFoundError):
                    continue
            return items

        items = await asyncio.to_thread(_scan)
        self._set_cached_dir(relative_path, items)
        total = len(items)
        return items[offset:offset + limit], total

    async def get_file_info(self, relative_path: str) -> dict:
        full_path = self._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        if not exists:
            raise ValueError("File not found")

        stat = await asyncio.to_thread(full_path.stat)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        size = stat.st_size
        if is_dir:
            size = await asyncio.to_thread(self._dir_size_sync, full_path)
        return {
            "name": full_path.name,
            "path": str(full_path.relative_to(self.base_dir)),
            "is_dir": is_dir,
            "size": size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mime_type": self.get_mime_type(relative_path),
        }

    async def delete(self, relative_path: str) -> None:
        full_path = self._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        if not exists:
            raise ValueError("File not found")

        parent_path = str(Path(relative_path).parent) if Path(relative_path).parent != Path(".") else ""
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if is_dir:
            await asyncio.to_thread(shutil.rmtree, full_path)
        else:
            await asyncio.to_thread(full_path.unlink)
        self._invalidate_dir_cache(parent_path)

    async def create_directory(self, relative_path: str, name: str) -> dict:
        parent = await asyncio.to_thread(self._resolve_path, relative_path)
        is_dir = await asyncio.to_thread(parent.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        new_dir = parent / name
        await asyncio.to_thread(new_dir.mkdir, exist_ok=True)
        stat = await asyncio.to_thread(new_dir.stat)
        self._invalidate_dir_cache(relative_path)
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
        self._invalidate_dir_cache(relative_path)
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(self.base_dir)),
            "is_dir": False,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def iter_folder_files(self, relative_path: str) -> AsyncIterator[Tuple[str, str]]:
        full_path = self._resolve_path(relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        root_path = str(full_path)

        def _walk() -> List[Tuple[str, str]]:
            results = []
            for dirpath, dirnames, filenames in os.walk(root_path):
                dirnames.sort()
                for filename in filenames:
                    abs_path = os.path.join(dirpath, filename)
                    arcname = os.path.relpath(abs_path, root_path)
                    results.append((abs_path, arcname))
            return results

        for abs_path, arcname in await asyncio.to_thread(_walk):
            yield abs_path, arcname

    async def download_folder_stream(self, relative_path: str) -> AsyncIterator[bytes]:
        """Stream a folder as ZIP without building the entire archive in memory/disk."""
        import zipfile as _zipfile
        full_path = self._resolve_path(relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        root_path = str(full_path)
        zip_name = f"{full_path.name}.zip"

        def _build_zip_to_buffer() -> bytes:
            buf = io.BytesIO()
            with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED, compresslevel=4) as zipf:
                for dirpath, dirnames, filenames in os.walk(root_path):
                    dirnames.sort()
                    for filename in filenames:
                        abs_path = os.path.join(dirpath, filename)
                        arcname = os.path.relpath(abs_path, root_path)
                        try:
                            zipf.write(abs_path, arcname)
                        except (PermissionError, OSError):
                            continue
            buf.seek(0)
            return buf.read()

        data = await asyncio.to_thread(_build_zip_to_buffer)
        chunk_size = 256 * 1024
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

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

    def etag_for_path(self, relative_path: str) -> str:
        """Generate a weak ETag based on path, size, and mtime."""
        try:
            full_path = self._resolve_path(relative_path)
            stat = full_path.stat()
            mtime = stat.st_mtime
            size = stat.st_size
            raw = f"{relative_path}:{size}:{mtime}".encode()
            return f'W/"{hashlib.sha256(raw).hexdigest()[:16]}"'
        except (OSError, ValueError):
            return f'W/"{hashlib.sha256(relative_path.encode()).hexdigest()[:16]}"'
