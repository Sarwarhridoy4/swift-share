import asyncio
import io
import os
import uuid
import zipfile
import time
from pathlib import Path
from typing import Optional, Dict, Set
import socketio
import aiofiles
from .config import settings
from .file_manager import FileManager

CHUNK_SIZE = 256 * 1024
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    max_http_buffer_size=256 * 1024 * 1024,
    ping_timeout=60,
    ping_interval=25,
)
socket_app = socketio.ASGIApp(sio)
file_manager = FileManager(cache_ttl=2.0)


class TransferProgress:
    def __init__(self, transfer_id: str, filename: str, total: Optional[int] = None):
        self.transfer_id = transfer_id
        self.filename = filename
        self.total = total or 0
        self.loaded = 0
        self.status = "in_progress"
        self.error: Optional[str] = None
        self.created_at = time.monotonic()

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


_transfers: Dict[str, TransferProgress] = {}
_upload_handles: Dict[str, tuple] = {}
_connected_sids: Set[str] = set()
_room_sids: Dict[str, Set[str]] = {}


def _add_to_room(sid: str, room: str) -> None:
    _room_sids.setdefault(room, set()).add(sid)


def _remove_from_room(sid: str, room: str) -> None:
    sids = _room_sids.get(room)
    if sids:
        sids.discard(sid)
        if not sids:
            _room_sids.pop(room, None)


async def _emit_to_room(room: str, event: str, data: dict) -> None:
    await sio.emit(event, data, room=room)


@sio.event
async def connect(sid, environ):
    _connected_sids.add(sid)
    await sio.emit("connected", {"sid": sid}, room=sid)


@sio.event
async def disconnect(sid):
    _connected_sids.discard(sid)
    for room in list(_room_sids.keys()):
        _remove_from_room(sid, room)
    for transfer_id, entry in list(_upload_handles.items()):
        if entry[1] == sid:
            file_path, handle = entry
            try:
                await handle.close()
            except Exception:
                pass
            _upload_handles.pop(transfer_id, None)
            await fail_transfer(transfer_id, "Client disconnected")


@sio.event
async def join_room(sid, data):
    room = data.get("room")
    if room:
        await sio.enter_room(sid, room)
        _add_to_room(sid, room)


@sio.event
async def leave_room(sid, data):
    room = data.get("room")
    if room:
        await sio.leave_room(sid, room)
        _remove_from_room(sid, room)


@sio.event
async def ping(sid, data):
    await sio.emit("pong", {"timestamp": time.monotonic()}, room=sid)


async def broadcast_progress(transfer_id: str):
    data = _transfers.get(transfer_id)
    if data:
        await sio.emit("transfer:progress", data.to_dict(), room=transfer_id)


async def broadcast_file_change(action: str, path: str, item: Optional[dict] = None):
    payload = {"action": action, "path": path, "item": item, "timestamp": time.monotonic()}
    await sio.emit("file:changed", payload)


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
        # Cleanup after a delay
        asyncio.create_task(_cleanup_transfer(transfer_id, delay=30))
        return data
    return None


async def fail_transfer(transfer_id: str, error: str):
    progress = _transfers.get(transfer_id)
    if progress:
        data = progress.fail(error)
        await sio.emit("transfer:error", data, room=transfer_id)
        asyncio.create_task(_cleanup_transfer(transfer_id, delay=10))
        return data
    return None


async def _cleanup_transfer(transfer_id: str, delay: int):
    await asyncio.sleep(delay)
    _transfers.pop(transfer_id, None)


@sio.event
async def upload_chunk(sid, data):
    """Receive a chunk of a file via WebSocket for resumable chunked upload."""
    transfer_id = data.get("transfer_id")
    chunk_index = data.get("chunk_index", 0)
    total_chunks = data.get("total_chunks", 1)
    filename = data.get("filename")
    rel_path = data.get("path", "")
    chunk_data = data.get("data")  # base64-encoded

    if not transfer_id or not filename or chunk_data is None:
        await sio.emit("upload:error", {"error": "Missing required fields"}, room=sid)
        return

    import base64
    try:
        raw = base64.b64decode(chunk_data)
    except Exception:
        await sio.emit("upload:error", {"error": "Invalid chunk data"}, room=sid)
        return

    try:
        full_path = file_manager._resolve_path(rel_path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        dest = full_path / filename
        mode = "ab" if chunk_index > 0 else "wb"
        async with aiofiles.open(dest, mode) as f:
            await f.write(raw)

        stat = await asyncio.to_thread(dest.stat)
        progress_pct = int(((chunk_index + 1) / total_chunks) * 100)
        await sio.emit("upload:progress", {
            "transfer_id": transfer_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "progress": progress_pct,
            "size": stat.st_size,
        }, room=sid)

        if chunk_index + 1 >= total_chunks:
            await sio.emit("upload:complete", {
                "transfer_id": transfer_id,
                "filename": filename,
                "path": str(dest.relative_to(file_manager.base_dir)),
                "size": stat.st_size,
            }, room=sid)
            await broadcast_file_change("create", str(dest.relative_to(file_manager.base_dir)))
    except Exception as e:
        await sio.emit("upload:error", {"transfer_id": transfer_id, "error": str(e)}, room=sid)


@sio.event
async def download_request(sid, data):
    """Initiate a download via WebSocket, streaming chunks back."""
    path = data.get("path")
    transfer_id = data.get("transfer_id") or str(uuid.uuid4())
    if not path:
        await sio.emit("download:error", {"error": "Missing path"}, room=sid)
        return

    try:
        full_path = file_manager._resolve_path(path)
        is_file = await asyncio.to_thread(full_path.is_file)
        if not is_file:
            raise ValueError("File not found")

        stat = await asyncio.to_thread(full_path.stat)
        total = stat.st_size
        await start_transfer(transfer_id, full_path.name, total)

        chunk_index = 0
        async with aiofiles.open(full_path, "rb") as f:
            while True:
                chunk = await f.read(CHUNK_SIZE)
                if not chunk:
                    break
                import base64
                await sio.emit("download:chunk", {
                    "transfer_id": transfer_id,
                    "chunk_index": chunk_index,
                    "filename": full_path.name,
                    "size": total,
                    "data": base64.b64encode(chunk).decode(),
                }, room=sid)
                chunk_index += 1

        await complete_transfer(transfer_id)
        await sio.emit("download:complete", {"transfer_id": transfer_id}, room=sid)
    except Exception as e:
        await fail_transfer(transfer_id, str(e))
        await sio.emit("download:error", {"transfer_id": transfer_id, "error": str(e)}, room=sid)
