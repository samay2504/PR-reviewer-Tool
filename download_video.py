#!/usr/bin/env python3
"""
download_video.py

Simple, robust downloader for large files (streams to disk).
Requires: requests (pip install requests)
"""

import sys
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = (
    "https://cdn.loom.com/sessions/transcoded/97347755a5544e20968bbd8abaec9382.mp4"
    "?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9jZG4ubG9vbS5jb20vc2Vzc2lvbnMvdHJhbnNjb2RlZC85NzM0Nzc1NWE1NTQ0ZTIwOTY4YmJkOGFiYWVjOTM4Mi5tcDQiLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjQwNzI4NTR9fX1dfQ__&Key-Pair-Id=KQOSYIR44AIC0&Signature=Xj3BLlpwy06YyTKCex7MpjyCJ5J-fvBHgA4fqYHYHDTNIJayBwpPtlmDJQfRHnMEPe4dBHuW5rZIgtKLFluUwVk7I2WAIbfz18g0khJSIws3bk-uyplcZQRqQNDCxz81PsRVL-RdkzMtZ0difc1L2MSka4J1h1Z3%7Ezk3NnLbEkLxV-Tzqz5FpwMw%7Eh-O0%7EFFZbXF4Nl77%7E8-mCv8GfOkbZre07SGJZYej8BNOQVrEN2hFU9%7EbCXp46BDWTUDAUIdUcN3TtBg477w2pNO7EMBu2qi96pAeyrJIS81r10wRwnMq-BhwSOWhgPc%7E6GWoFKoJpmBeJ0e%7ERXhUIpiIAd6sg__"
)

def create_session(retries: int = 5, backoff_factor: float = 0.8) -> requests.Session:
    s = requests.Session()
    r = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    adapter = HTTPAdapter(max_retries=r)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def download_file(url: str, dest: Path | str | None = None, chunk_size: int = 1024*1024):
    if dest is None:
        # Derive filename from URL (strip query params)
        filename = Path(url.split("?")[0]).name or "downloaded_video.mp4"
        dest = Path(filename)
    else:
        dest = Path(dest)

    session = create_session()

    with session.get(url, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        written = 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if total:
                    pct = written / total * 100
                    print(f"\r{pct:5.1f}% — {written//1024//1024}MiB / {total//1024//1024}MiB", end="", flush=True)
                else:
                    print(f"\rDownloaded {written//1024//1024} MiB", end="", flush=True)
    print(f"\nSaved to: {dest.resolve()}")
    return dest

if __name__ == "__main__":
    # optional CLI: pass destination filename as first arg
    out = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        download_file(URL, dest=out)
    except Exception as e:
        print("Download failed:", e, file=sys.stderr)
        sys.exit(1)
