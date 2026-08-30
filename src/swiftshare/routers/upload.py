from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from ..file_manager import FileManager
from ..config import settings
from ..socketio_server import start_transfer, update_transfer, complete_transfer, fail_transfer
import asyncio
import aiofiles
import uuid

router = APIRouter()
file_manager = FileManager()


@router.post("/")
async def upload_file(path: str = Form(""), file: UploadFile = File(...)):
    transfer_id = str(uuid.uuid4())
    try:
        filename = file.filename or "upload"
        full_path = file_manager._resolve_path(path)
        is_dir = await asyncio.to_thread(full_path.is_dir)
        if not is_dir:
            raise ValueError("Parent is not a directory")

        dest = full_path / filename
        total = 0
        loaded = 0

        await start_transfer(transfer_id, filename, 0)

        async with aiofiles.open(dest, "wb") as out:
            while True:
                chunk = await file.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_upload_size:
                    raise HTTPException(status_code=413, detail="File too large")
                await out.write(chunk)
                loaded += len(chunk)
                await update_transfer(transfer_id, loaded, total)

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
