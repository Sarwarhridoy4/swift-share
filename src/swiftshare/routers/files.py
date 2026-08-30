from fastapi import APIRouter, HTTPException
from pathlib import Path
from ..file_manager import FileManager
from ..models import FileItem, MkdirRequest
from ..config import settings

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
    try:
        name, content = await file_manager.download_file(path)
        from fastapi.responses import Response
        return Response(content=content, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={name}"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/download-folder")
async def download_folder(path: str):
    try:
        name, content = await file_manager.download_folder(path)
        from fastapi.responses import Response
        return Response(content=content, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={name}"})
    except ValueError as e:
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
