from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    mime_type: Optional[str] = None


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
