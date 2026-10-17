from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
MAX_BYTES = 500 * 1024 * 1024
ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "instagram.com", "www.instagram.com",
    "vimeo.com", "www.vimeo.com", "player.vimeo.com",
    "dailymotion.com", "www.dailymotion.com", "dai.ly",
    "facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    "reddit.com", "www.reddit.com", "old.reddit.com", "redd.it",
}
DIRECT_EXTS = {".mp4", ".webm", ".mov", ".m4v"}

app = FastAPI(title="Kratos Video Downloader", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class URLRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class DownloadRequest(URLRequest):
    format_id: str | None = Field(default=None, max_length=100)


def validate_url(raw: str) -> str:
    raw = raw.strip()
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(400, "Please use a full HTTPS video URL.")
    host = parsed.hostname.lower().rstrip(".")
    if host not in ALLOWED_HOSTS and Path(parsed.path.lower()).suffix not in DIRECT_EXTS:
        raise HTTPException(400, "Unsupported site. Try a supported public platform or direct video file URL.")
    try:
        addresses = {entry[4][0] for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if any(not ipaddress.ip_address(addr.split("%")[0]).is_global for addr in addresses):
            raise HTTPException(400, "Private or local network URLs are not allowed.")
    except HTTPException:
        raise
    except (socket.gaierror, ValueError):
        raise HTTPException(400, "Could not resolve the URL host.")
    return raw


def base_opts() -> dict:
    return {"quiet": True, "no_warnings": True, "noplaylist": True,
            "socket_timeout": 20, "retries": 1, "fragment_retries": 1,
            "max_filesize": MAX_BYTES, "restrictfilenames": True, "overwrites": False}


@app.get("/api/health")
def health():
    return {"ok": True, "service": "Kratos Video Downloader"}


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.post("/api/info")
def info(body: URLRequest):
    url = validate_url(body.url)
    try:
        with yt_dlp.YoutubeDL(base_opts() | {"skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
        if not data:
            raise HTTPException(422, "No video information found.")
        formats, seen = [], set()
        for fmt in data.get("formats", []):
            if not fmt.get("url") or fmt.get("vcodec") in (None, "none"):
                continue
            height, ext = fmt.get("height"), fmt.get("ext") or ""
            label = f"{height}p" if height else (ext.upper() or "Video")
            if fmt.get("acodec") in (None, "none"):
                label += " (video only; FFmpeg may be needed)"
            key = (str(fmt.get("format_id", "")), label)
            if key in seen:
                continue
            seen.add(key)
            formats.append({"format_id": str(fmt.get("format_id", "")), "label": label,
                            "height": height or 0, "ext": ext})
        formats.sort(key=lambda f: (f["height"], "video only" not in f["label"]), reverse=True)
        return {"title": data.get("title") or "Video", "thumbnail": data.get("thumbnail"),
                "duration": data.get("duration"), "uploader": data.get("uploader") or data.get("channel"),
                "formats": formats[:30]}
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "private video" in msg or "login" in msg or "sign in" in msg:
            detail = "This content may be private or require login. Login-protected downloads are not supported."
        else:
            detail = "Could not fetch this video. The link may be unavailable or platform support may have changed."
        raise HTTPException(422, detail)


@app.post("/api/download")
def download(body: DownloadRequest):
    url = validate_url(body.url)
    fmt_id = body.format_id.strip() if body.format_id else ""
    if fmt_id and not re.fullmatch(r"[\w.-]{1,100}", fmt_id):
        raise HTTPException(400, "Invalid quality selection.")
    temp = Path(tempfile.mkdtemp(prefix="kratos_dl_"))
    options = base_opts() | {
        "format": f"{fmt_id}+bestaudio/best" if fmt_id else "best",
        "outtmpl": str(temp / "%(title).100B_%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        outputs = [p for p in temp.iterdir() if p.is_file()]
        if not outputs:
            raise RuntimeError("No output file created.")
        output = max(outputs, key=lambda p: p.stat().st_size)
        if output.stat().st_size > MAX_BYTES:
            raise HTTPException(413, "Video exceeds the 500 MB limit.")
        safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", output.name).strip(" .") or "video.mp4"
        return FileResponse(output, filename=safe_name,
                            media_type="video/mp4" if output.suffix.lower() == ".mp4" else "application/octet-stream",
                            background=BackgroundTask(shutil.rmtree, temp, ignore_errors=True))
    except HTTPException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise HTTPException(422, "Download failed. The URL may be unsupported, private, unavailable, too large, or require FFmpeg.")
