import asyncio
import io
import os
import uuid
import zipfile
from pathlib import Path
from typing import Optional
import socketio
import aiofiles
from .config import settings
from .file_manager import FileManager

CHUNK_SIZE = 256 * 1024
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    max_http_buffer_size=50 * 1024 * 1024,
)
socket_app = socketio.ASGIApp(sio)
file_manager = FileManager()


class TransferProgress:
    def __init__(self, transfer_id: str, filename: str, total: Optional[int] = None):
        self.transfer_id = transfer_id
        self.filename = filename
        self.total = total or 0
        self.loaded = 0
        self.status = "in_progress"
        self.error: Optional[str] = None

    def to_dict(self):
        return {
            "transfer_id": self.transfer_id,
            "filename": self.filename,
            "total": self.total,
            "loaded": self.loaded,
            "percent": self._percent(),
            "status": self.status,
            "error": self.error,
        }

    def _percent(self) -> int:
        if self.total <= 0:
            return 0
        return min(100, int((self.loaded / self.total) * 100))

    def update(self, loaded: int, total: Optional[int] = None):
        if total is not None:
            self.total = total
        self.loaded = loaded
        return self.to_dict()

    def complete(self):
        self.status = "completed"
        self.loaded = self.total
        return self.to_dict()

    def fail(self, error: str):
        self.status = "error"
        self.error = error
        return self.to_dict()


_transfers: dict[str, TransferProgress] = {}
_upload_handles: dict[str, tuple[Path, "aiofiles.base.AiofilesBase"]] = {}


@sio.event
async def connect(sid, environ):
    pass


@sio.event
async def disconnect(sid):
    for transfer_id, entry in list(_upload_handles.items()):
        file_path, handle = entry
        try:
            await handle.close()
        except Exception:
            pass
        _upload_handles.pop(transfer_id, None)


@sio.on("upload:start")
async def upload_start(sid, data):
    transfer_id = str(uuid.uuid4())
    try:
        relative_path = data.get("path", "")
        filename = data.get("filename", "upload")
        total = int(data.get("total") or 0)

        full_path = file_manager._resolve_path(relative_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        file_path = full_path / filename
        handle = await aiofiles.open(file_path, "wb")
        progress = TransferProgress(transfer_id, filename, total)
        _transfers[transfer_id] = progress
        _upload_handles[transfer_id] = (file_path, handle)

        await sio.emit("transfer:started", progress.to_dict(), room=sid)
        return {"transfer_id": transfer_id}
    except Exception as e:
        return {"error": str(e)}


@sio.on("upload:chunk")
async def upload_chunk(sid, data):
    transfer_id = data.get("transfer_id")
    chunk = data.get("chunk")
    if not transfer_id or chunk is None:
        return {"error": "Invalid chunk"}

    progress = _transfers.get(transfer_id)
    entry = _upload_handles.get(transfer_id)
    if not progress or not entry:
        return {"error": "Unknown transfer"}

    file_path, handle = entry
    try:
        await handle.write(chunk)
        progress.loaded += len(chunk)
        await sio.emit("transfer:progress", progress.to_dict(), room=sid)
        return {"ok": True}
    except Exception as e:
        await fail_transfer(transfer_id, str(e))
        await sio.emit("transfer:error", progress.to_dict(), room=sid)
        return {"error": str(e)}


@sio.on("upload:complete")
async def upload_complete(sid, data):
    transfer_id = data.get("transfer_id")
    entry = _upload_handles.pop(transfer_id, None)
    progress = _transfers.get(transfer_id)
    if entry:
        file_path, handle = entry
        try:
            await handle.close()
        except Exception:
            pass
    if progress:
        progress.status = "completed"
        progress.loaded = progress.total
        await sio.emit("transfer:completed", progress.to_dict(), room=sid)
        _transfers.pop(transfer_id, None)
    return {"ok": True}


@sio.on("download:request")
async def download_request(sid, data):
    transfer_id = str(uuid.uuid4())
    try:
        relative_path = data.get("path", "")
        full_path = file_manager._resolve_path(relative_path)
        exists = await asyncio.to_thread(full_path.exists)
        is_file = await asyncio.to_thread(full_path.is_file)
        if not exists or not is_file:
            raise ValueError("File not found")

        stat = await asyncio.to_thread(full_path.stat)
        total = stat.st_size
        progress = TransferProgress(transfer_id, full_path.name, total)
        _transfers[transfer_id] = progress
        await sio.emit("transfer:started", progress.to_dict(), room=sid)

        async with aiofiles.open(full_path, "rb") as f:
            while True:
                chunk = await f.read(CHUNK_SIZE)
                if not chunk:
                    break
                progress.loaded += len(chunk)
                await sio.emit("transfer:progress", progress.to_dict(), room=sid)
                await sio.emit("download:chunk", {"transfer_id": transfer_id, "chunk": chunk}, room=sid)

        progress.status = "completed"
        progress.loaded = progress.total
        await sio.emit("transfer:completed", progress.to_dict(), room=sid)
        await sio.emit("download:complete", {"transfer_id": transfer_id}, room=sid)
        _transfers.pop(transfer_id, None)
        return {"transfer_id": transfer_id}
    except Exception as e:
        progress = _transfers.get(transfer_id)
        if progress:
            await sio.emit("transfer:error", progress.to_dict(), room=sid)
            _transfers.pop(transfer_id, None)
        return {"error": str(e)}


@sio.on("download-folder:request")
async def download_folder_request(sid, data):
    transfer_id = str(uuid.uuid4())
    try:
        relative_path = data.get("path", "")
        full_path = file_manager._resolve_path(relative_path)
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
        content = zip_buffer.getvalue()
        total = len(content)
        progress = TransferProgress(transfer_id, f"{full_path.name}.zip", total)
        _transfers[transfer_id] = progress
        await sio.emit("transfer:started", progress.to_dict(), room=sid)

        offset = 0
        while offset < total:
            end = min(offset + CHUNK_SIZE, total)
            chunk = content[offset:end]
            progress.loaded = end
            await sio.emit("transfer:progress", progress.to_dict(), room=sid)
            await sio.emit("download:chunk", {"transfer_id": transfer_id, "chunk": chunk}, room=sid)
            offset = end

        progress.status = "completed"
        progress.loaded = progress.total
        await sio.emit("transfer:completed", progress.to_dict(), room=sid)
        await sio.emit("download:complete", {"transfer_id": transfer_id}, room=sid)
        _transfers.pop(transfer_id, None)
        return {"transfer_id": transfer_id, "filename": f"{full_path.name}.zip", "total": total}
    except Exception as e:
        progress = _transfers.get(transfer_id)
        if progress:
            await sio.emit("transfer:error", progress.to_dict(), room=sid)
            _transfers.pop(transfer_id, None)
        return {"error": str(e)}


async def broadcast_progress(transfer_id: str):
    data = _transfers.get(transfer_id)
    if data:
        await sio.emit("transfer:progress", data.to_dict(), room=transfer_id)


async def start_transfer(transfer_id: str, filename: str, total: Optional[int] = None) -> TransferProgress:
    progress = TransferProgress(transfer_id, filename, total)
    _transfers[transfer_id] = progress
    await sio.emit("transfer:started", progress.to_dict(), room=transfer_id)
    return progress


async def update_transfer(transfer_id: str, loaded: int, total: Optional[int] = None):
    progress = _transfers.get(transfer_id)
    if progress:
        data = progress.update(loaded, total)
        await sio.emit("transfer:progress", data, room=transfer_id)
        return data
    return None


async def complete_transfer(transfer_id: str):
    progress = _transfers.get(transfer_id)
    if progress:
        data = progress.complete()
        await sio.emit("transfer:completed", data, room=transfer_id)
        return data
    return None


async def fail_transfer(transfer_id: str, error: str):
    progress = _transfers.get(transfer_id)
    if progress:
        data = progress.fail(error)
        await sio.emit("transfer:error", data, room=transfer_id)
        return data
    return None
