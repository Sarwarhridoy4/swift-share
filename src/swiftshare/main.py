from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .config import settings
from .routers import files, upload, shares

app = FastAPI(title="Portable File Transfer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(shares.router, prefix="/api/shares", tags=["shares"])


def _find_static_dir() -> Path:
    candidates = [
        Path(__file__).parent.parent.parent / "static",
        Path(__file__).parent.parent / "static",
        Path(__file__).parent / "static",
        Path.cwd() / "static",
        Path("/usr/share/swiftshare/static"),
        Path("/usr/lib/swiftshare/static"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return Path.cwd() / "static"


static_dir = _find_static_dir()
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/ip")
async def get_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return {"ip": ip, "port": settings.port}
    except Exception:
        return {"ip": "127.0.0.1", "port": settings.port}
