import os
import uuid
import zipfile
import tempfile
import asyncio
import aiofiles
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..file_manager import FileManager
from ..models import FileItem, MkdirRequest
from ..config import settings
from ..socketio_server import start_transfer, update_transfer, complete_transfer, fail_transfer

router = APIRouter()
file_manager = FileManager()


@router.get("/", response_model=list[FileItem])
async def list_files(path: str = ""):
    try:
        items = await file_manager.list_directory(path)
        return [FileItem(**item) for item in items]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/info", response_model=FileItem)
async def get_file_info(path: str):
    try:
        info = await file_manager.get_file_info(path)
        return FileItem(**info)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/")
async def delete_file(path: str):
    try:
        await file_manager.delete(path)
        return {"message": "Deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/mkdir")
async def create_directory(req: MkdirRequest):
    try:
        result = await file_manager.create_directory(req.path, req.name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download")
async def download_file(path: str):
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

        async def _stream():
            async with aiofiles.open(full_path, "rb") as f:
                loaded = 0
                while True:
                    chunk = await f.read(256 * 1024)
                    if not chunk:
                        break
                    loaded += len(chunk)
                    await update_transfer(transfer_id, loaded, total)
                    yield chunk
            await complete_transfer(transfer_id)

        return StreamingResponse(
            _stream(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={full_path.name}", "Content-Length": str(total)},
        )
    except ValueError as e:
        await fail_transfer(transfer_id, str(e))
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
        temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        temp_zip.close()

        def _build_zip():
            with zipfile.ZipFile(temp_zip.name, "w", zipfile.ZIP_DEFLATED, compresslevel=4) as zipf:
                for dirpath, dirnames, filenames in os.walk(str(full_path)):
                    dirnames.sort()
                    for filename in filenames:
                        abs_path = os.path.join(dirpath, filename)
                        arcname = os.path.relpath(abs_path, str(full_path))
                        try:
                            zipf.write(abs_path, arcname)
                        except (PermissionError, OSError):
                            continue

        await asyncio.to_thread(_build_zip)
        total = os.path.getsize(temp_zip.name)
        await start_transfer(transfer_id, zip_name, total)

        async def _stream_zip():
            async with aiofiles.open(temp_zip.name, "rb") as f:
                loaded = 0
                while True:
                    chunk = await f.read(256 * 1024)
                    if not chunk:
                        break
                    loaded += len(chunk)
                    await update_transfer(transfer_id, loaded, total)
                    yield chunk
            await complete_transfer(transfer_id)
            try:
                os.unlink(temp_zip.name)
            except OSError:
                pass

        return StreamingResponse(
            _stream_zip(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_name}", "Content-Length": str(total)},
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
