import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from .config import settings
from .routers import files, upload, shares
from .socketio_server import socket_app

app = FastAPI(title="Portable File Transfer", version="1.0.0")

_start_time = time.monotonic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_security_headers(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()

    response = await call_next(request)

    duration = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration:.2f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "private, max-age=0"
    return response


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "shared_dir": str(settings.shared_dir),
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
    }


app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(shares.router, prefix="/api/shares", tags=["shares"])

app.mount("/socket.io", socket_app)


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
