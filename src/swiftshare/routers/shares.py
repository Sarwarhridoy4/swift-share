from fastapi import APIRouter, HTTPException, Request
from ..models import ShareCreate, ShareInfo
from ..share_manager import share_manager
from ..file_manager import FileManager

router = APIRouter()
file_manager = FileManager()


@router.post("/", response_model=ShareInfo)
async def create_share(share: ShareCreate):
    try:
        return share_manager.create_share(share, file_manager)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[ShareInfo])
async def list_shares():
    return share_manager.list_shares()


@router.get("/{share_id}")
async def get_share(share_id: str, request: Request):
    password = request.query_params.get("password")
    try:
        share = share_manager.get_share(share_id, password)
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or expired")
        return {"path": share["path"]}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{share_id}")
async def delete_share(share_id: str):
    share_manager.delete_share(share_id)
    return {"message": "Share deleted"}
