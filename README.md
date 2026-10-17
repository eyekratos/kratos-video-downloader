# Kratos Video Downloader

A dark, responsive video downloader starter using FastAPI + yt-dlp.

## Run on Windows 11
1. Install Python 3.11+ from https://www.python.org/downloads/ (enable **Add Python to PATH**).
2. Install FFmpeg from https://ffmpeg.org/download.html and add it to PATH (recommended).
3. Open this repository folder in File Explorer, type `cmd` in the address bar and press Enter.
4. Run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app:app --reload
```

5. Open http://127.0.0.1:8000

Keep the terminal open while using the site. Press Ctrl+C to stop it.

## GitHub and deployment
GitHub stores this source code but does not run the Python server. To make the website public, deploy it to a Python-capable host and configure HTTPS. Before public deployment, add authentication/quotas, rate limits, request timeouts, storage cleanup, monitoring, and abuse prevention.

## Limits and responsible use
- Supports public URLs handled by yt-dlp on a limited platform allowlist and direct public video-file URLs.
- Platform support can change; not every URL is guaranteed to work.
- Private/login-protected videos and DRM/restriction bypass are not supported.
- Download only content you own or have permission to save, and follow platform terms and local law.
- Downloads are temporary; the starter has a 500 MB limit.
- FFmpeg is recommended for merging separate audio/video streams.

## API
- GET /api/health
- POST /api/info with JSON {"url":"https://..."}
- POST /api/download with JSON {"url":"https://...","format_id":"..."}
