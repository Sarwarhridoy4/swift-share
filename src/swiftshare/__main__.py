import argparse
import asyncio
import os
from pathlib import Path
import uvicorn
from .config import settings
from .main import app


def _detect_workers() -> int:
    try:
        return max(1, os.cpu_count() or 1)
    except (NotImplementedError, TypeError):
        return 1


def main():
    parser = argparse.ArgumentParser(description="Portable File Transfer Server")
    parser.add_argument("--host", default=settings.host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to listen on")
    parser.add_argument("--shared-dir", default=str(settings.shared_dir), help="Directory to share")
    parser.add_argument("--max-upload-size", type=int, default=settings.max_upload_size, help="Maximum upload size in bytes")
    parser.add_argument("--enable-auth", action="store_true", default=settings.enable_auth, help="Enable basic auth")
    parser.add_argument("--share-expiry-hours", type=int, default=settings.share_expiry_hours, help="Default share expiry in hours")
    parser.add_argument("--workers", type=int, default=_detect_workers(), help="Number of worker processes")
    parser.add_argument("--threads", type=int, default=min(32, (_detect_workers() * 4) + 1), help="Thread pool size")
    parser.add_argument("--no-access-log", action="store_true", help="Disable access log for better performance")
    parser.add_argument("--log-level", default="warning", help="Log level (default: warning)")
    parser.add_argument("--backlog", type=int, default=2048, help="Socket backlog")
    parser.add_argument("--limit-concurrency", type=int, default=None, help="Max concurrent requests")
    parser.add_argument("--limit-max-requests", type=int, default=None, help="Max requests before worker restart")
    parser.add_argument("--timeout-keep-alive", type=int, default=5, help="Keep-alive timeout in seconds")
    parser.add_argument("--no-compression", action="store_true", help="Disable response compression")

    args = parser.parse_args()

    settings.shared_dir = Path(args.shared_dir)
    settings.port = args.port
    settings.host = args.host
    settings.max_upload_size = args.max_upload_size
    settings.enable_auth = args.enable_auth
    settings.share_expiry_hours = args.share_expiry_hours

    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("UVICORN_CONNECTION_LIMIT", str(args.limit_concurrency or 0))
    os.environ.setdefault("UVICORN_MAX_REQUESTS", str(args.limit_max_requests or 0))

    loop = "uvloop" if _uvloop_available() else "asyncio"
    http = "httptools" if _httptools_available() else "h11"

    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        workers=args.workers,
        loop=loop,
        http=http,
        access_log=not args.no_access_log,
        log_level=args.log_level,
        server_header=False,
        date_header=False,
        backlog=args.backlog,
        limit_concurrency=args.limit_concurrency,
        limit_max_requests=args.limit_max_requests,
        timeout_keep_alive=args.timeout_keep_alive,
        ws="none",
    )

    if not args.no_compression:
        try:
            from fastapi.middleware.gzip import GZipMiddleware
            app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=4)
        except Exception:
            pass

    server = uvicorn.Server(config)
    server.run()


def _uvloop_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("uvloop") is not None  # type: ignore[import]
    except (ImportError, ValueError):
        return False


def _httptools_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("httptools") is not None  # type: ignore[import]
    except (ImportError, ValueError):
        return False


if __name__ == "__main__":
    main()
