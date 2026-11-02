import os
import uuid
import zipfile
import tempfile
import asyncio
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, PlainTextResponse, Response
from ..file_manager import FileManager
from ..models import FileItem, FileListResponse, MkdirRequest, HealthResponse
from ..config import settings
from ..socketio_server import (
    start_transfer, update_transfer, complete_transfer, fail_transfer,
    broadcast_file_change, sio,
)

router = APIRouter()
file_manager = FileManager(cache_ttl=2.0)

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000


def _etag_headers(etag: str) -> dict:
    return {"ETag": etag, "Cache-Control": "private, max-age=2"}


@router.get("/health", response_model=HealthResponse)
async def health():
    import time
    return HealthResponse(
        status="ok",
        version="1.0.0",
        shared_dir=str(settings.shared_dir),
        uptime_seconds=0.0,
    )


@router.get("/", response_model=FileListResponse)
async def list_files(
    request: Request,
    path: str = "",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
):
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT
    if offset < 0:
        offset = 0

    items, total = await file_manager.list_directory(path, limit=limit, offset=offset)
    etag = file_manager.etag_for_path(path)

    if if_none_match and if_none_match == etag:
        return Response(status_code=304, headers=_etag_headers(etag))

    return FileListResponse(
        items=[FileItem(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/info", response_model=FileItem)
async def get_file_info(path: str):
    try:
        info = await file_manager.get_file_info(path)
        return FileItem(**info)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.head("/")
async def head_files(path: str = ""):
    try:
        await file_manager.list_directory(path, limit=1, offset=0)
        return PlainTextResponse(content="", status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/")
async def delete_file(path: str):
    try:
        await file_manager.delete(path)
        await broadcast_file_change("delete", path)
        return {"message": "Deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/mkdir")
async def create_directory(req: MkdirRequest):
    try:
        result = await file_manager.create_directory(req.path, req.name)
        await broadcast_file_change("create", result["path"], result)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download")
async def download_file(
    request: Request,
    path: str,
    range: Optional[str] = Header(default=None, alias="Range"),
):
    transfer_id = str(uuid.uuid4())
    try:
        full_path = file_manager._resolve_path(path)
        exists = await asyncio.to_thread(full_path.exists)
        is_file = await asyncio.to_thread(full_path.is_file)
        if not exists or not is_file:
            raise ValueError("File not found")

        stat = await asyncio.to_thread(full_path.stat)
        total = stat.st_size
        await start_transfer(transfer_id, full_path.name, total)

        # Handle Range requests for resume/seek support
        start = 0
        end = total - 1
        status_code = 200
        content_range = None

        if range:
            try:
                units, spec = range.strip().split("=", 1)
                if units.strip() != "bytes":
                    raise ValueError("Invalid range unit")
                start_str, end_str = spec.split("-", 1)
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else total - 1
                start = max(0, min(start, total - 1))
                end = max(start, min(end, total - 1))
                status_code = 206
                content_range = f"bytes {start}-{end}/{total}"
            except (ValueError, IndexError):
                pass

        chunk_size = 256 * 1024

        async def _stream():
            loaded = start
            async with aiofiles.open(full_path, "rb") as f:
                await f.seek(start)
                while loaded <= end:
                    to_read = min(chunk_size, end - loaded + 1)
                    chunk = await f.read(to_read)
                    if not chunk:
                        break
                    loaded += len(chunk)
                    await update_transfer(transfer_id, loaded - start, end - start + 1)
                    yield chunk
            await complete_transfer(transfer_id)

        headers = {
            "Content-Disposition": f'attachment; filename="{full_path.name}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
        }
        if content_range:
            headers["Content-Range"] = content_range

        return StreamingResponse(
            _stream(),
            media_type="application/octet-stream",
            status_code=status_code,
            headers=headers,
        )
    except ValueError as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.head("/download")
async def head_download_file(path: str):
    try:
        full_path = file_manager._resolve_path(path)
        exists = await asyncio.to_thread(full_path.exists)
        is_file = await asyncio.to_thread(full_path.is_file)
        if not exists or not is_file:
            raise ValueError("File not found")
        stat = await asyncio.to_thread(full_path.stat)
        return Response(
            status_code=200,
            headers={
                "Content-Length": str(stat.st_size),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'attachment; filename="{full_path.name}"',
                "Cache-Control": "private, max-age=3600",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/download-folder")
async def download_folder(path: str):
    transfer_id = str(uuid.uuid4())
    try:
        full_path = file_manager._resolve_path(path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Not a directory")

        zip_name = f"{full_path.name}.zip"
        total = 0
        # Compute total size for progress
        async for _, _ in file_manager.iter_folder_files(path):
            pass  # iter_folder_files yields paths; we'll stream the zip

        await start_transfer(transfer_id, zip_name, 0)

        async def _stream_zip():
            loaded = 0
            async for chunk in file_manager.download_folder_stream(path):
                loaded += len(chunk)
                await update_transfer(transfer_id, loaded, 0)
                yield chunk
            await complete_transfer(transfer_id)

        return StreamingResponse(
            _stream_zip(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_name}"',
                "Accept-Ranges": "bytes",
                "Cache-Control": "private, max-age=3600",
            },
        )
    except ValueError as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/preview")
async def preview_file(path: str):
    try:
        content = await file_manager.read_preview(path)
        return {"content": content}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/mime-type")
async def get_mime_type(path: str):
    mime_type = file_manager.get_mime_type(path)
    return {"mime_type": mime_type}
