from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    mime_type: Optional[str] = None


class FileListResponse(BaseModel):
    items: List[FileItem]
    total: int
    limit: int
    offset: int
    has_more: bool


class MkdirRequest(BaseModel):
    path: str = ""
    name: str


class ShareCreate(BaseModel):
    path: str
    expires_in_hours: Optional[int] = None
    password: Optional[str] = None


class ShareInfo(BaseModel):
    id: str
    path: str
    created_at: datetime
    expires_at: datetime
    download_count: int
    password_protected: bool


class UploadProgress(BaseModel):
    file_id: str
    filename: str
    progress: float
    status: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    shared_dir: str
    uptime_seconds: float


class WSMessage(BaseModel):
    type: str
    data: dict


class WSFileListUpdate(BaseModel):
    action: str
    path: str
    item: Optional[dict] = None


class WSUploadChunk(BaseModel):
    transfer_id: str
    chunk_index: int
    total_chunks: int
    filename: str
    path: str
    size: int
    data: Optional[str] = None  # base64-encoded chunk


class WSDownloadChunk(BaseModel):
    transfer_id: str
    chunk_index: int
    total_chunks: int
    filename: str
    size: int
    data: Optional[str] = None  # base64-encoded chunk
