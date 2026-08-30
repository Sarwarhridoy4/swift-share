from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from ..file_manager import FileManager
from ..config import settings

router = APIRouter()
file_manager = FileManager()


@router.post("/")
async def upload_file(path: str = Form(""), file: UploadFile = File(...)):
    try:
        content = await file.read()
        if len(content) > settings.max_upload_size:
            raise HTTPException(status_code=413, detail="File too large")

        result = await file_manager.upload_file(path, file.filename, content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
