import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from .models import ShareInfo, ShareCreate
from .config import settings
from .file_manager import FileManager


class ShareManager:
    def __init__(self):
        self.shares: Dict[str, dict] = {}

    def create_share(self, share: ShareCreate, file_manager: FileManager) -> ShareInfo:
        share_id = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(
            hours=share.expires_in_hours or settings.share_expiry_hours
        )

        self.shares[share_id] = {
            "path": share.path,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "download_count": 0,
            "password": hashlib.sha256(share.password.encode()).hexdigest() if share.password else None,
        }

        return ShareInfo(
            id=share_id,
            path=share.path,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            download_count=0,
            password_protected=share.password is not None,
        )

    def get_share(self, share_id: str, password: Optional[str] = None) -> Optional[dict]:
        share = self.shares.get(share_id)
        if not share:
            return None

        if datetime.utcnow() > share["expires_at"]:
            del self.shares[share_id]
            return None

        if share["password"]:
            if not password:
                raise ValueError("Password required")
            if hashlib.sha256(password.encode()).hexdigest() != share["password"]:
                raise ValueError("Invalid password")

        share["download_count"] += 1
        return share

    def list_shares(self) -> list[ShareInfo]:
        active = []
        for share_id, share in self.shares.items():
            if datetime.utcnow() <= share["expires_at"]:
                active.append(
                    ShareInfo(
                        id=share_id,
                        path=share["path"],
                        created_at=share["created_at"],
                        expires_at=share["expires_at"],
                        download_count=share["download_count"],
                        password_protected=share["password"] is not None,
                    )
                )
        return active

    def delete_share(self, share_id: str) -> None:
        if share_id in self.shares:
            del self.shares[share_id]


share_manager = ShareManager()
