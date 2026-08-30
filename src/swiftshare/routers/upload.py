import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from ..file_manager import FileManager
from ..config import settings
from ..socketio_server import start_transfer, update_transfer, complete_transfer, fail_transfer

router = APIRouter()
file_manager = FileManager()


@router.post("/")
async def upload_file(path: str = Form(""), file: UploadFile = File(...)):
    transfer_id = str(uuid.uuid4())
    try:
        content = await file.read()
        total = len(content)
        if total > settings.max_upload_size:
            raise HTTPException(status_code=413, detail="File too large")

        progress = await start_transfer(transfer_id, file.filename or "upload", total)
        await update_transfer(transfer_id, total, total)

        result = await file_manager.upload_file(path, file.filename, content)
        await complete_transfer(transfer_id)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await fail_transfer(transfer_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
