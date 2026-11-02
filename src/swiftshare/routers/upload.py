from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from pathlib import Path
from typing import Optional
from ..file_manager import FileManager
from ..config import settings
from ..socketio_server import start_transfer, update_transfer, complete_transfer, fail_transfer
import asyncio
import aiofiles
import uuid

router = APIRouter()
file_manager = FileManager(cache_ttl=2.0)


@router.post("/")
async def upload_file(
    request: Request,
    path: str = Form(""),
    file: UploadFile = File(...),
):
    transfer_id = str(uuid.uuid4())
    try:
        filename = file.filename or "upload"
        full_path = file_manager._resolve_path(path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        dest = full_path / filename
        loaded = 0

        await start_transfer(transfer_id, filename, 0)

        async with aiofiles.open(dest, "wb") as out:
            while True:
                chunk = await file.read(256 * 1024)
                if not chunk:
                    break
                loaded += len(chunk)
                if loaded > settings.max_upload_size:
                    await out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large")
                await out.write(chunk)
                await update_transfer(transfer_id, loaded, 0)

        await complete_transfer(transfer_id)
        stat = await asyncio.to_thread(dest.stat)
        return {
            "name": dest.name,
            "path": str(dest.relative_to(file_manager.base_dir)),
            "is_dir": False,
            "size": stat.st_size,
        }
    except HTTPException:
        raise
    except ValueError as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunk")
async def upload_chunk(
    request: Request,
    transfer_id: str = Form(...),
    chunk_index: int = Form(0),
    total_chunks: int = Form(1),
    filename: str = Form(...),
    path: str = Form(""),
    file: UploadFile = File(...),
):
    """Resumable chunked upload endpoint."""
    try:
        full_path = file_manager._resolve_path(path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        dest = full_path / filename
        mode = "ab" if chunk_index > 0 else "wb"

        content = await file.read()
        async with aiofiles.open(dest, mode) as out:
            await out.write(content)

        progress_pct = int(((chunk_index + 1) / max(total_chunks, 1)) * 100)
        await update_transfer(transfer_id, chunk_index + 1, total_chunks)

        if chunk_index + 1 >= total_chunks:
            await complete_transfer(transfer_id)
            stat = await asyncio.to_thread(dest.stat)
            return {
                "name": dest.name,
                "path": str(dest.relative_to(file_manager.base_dir)),
                "is_dir": False,
                "size": stat.st_size,
                "complete": True,
            }

        return {"transfer_id": transfer_id, "chunk_index": chunk_index, "progress": progress_pct}
    except ValueError as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
