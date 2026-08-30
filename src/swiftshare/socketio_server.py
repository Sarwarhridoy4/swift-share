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
    max_http_buffer_size=256 * 1024 * 1024,
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
