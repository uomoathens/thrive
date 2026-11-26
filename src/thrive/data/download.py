import hashlib
import shutil
import time
import urllib.request
from typing import Callable

USER_AGENT = "thrive-research (+https://github.com/uomoathens/thrive)"

Fetcher = Callable[[str], bytes]


def fetch(url: str, retries: int = 4, timeout: int = 180) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"could not download {url}: {last}")


def fetch_to_file(url: str, path, retries: int = 4, timeout: int = 900) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            digest = hashlib.sha256()
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(path, "wb") as out:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    digest.update(chunk)
                    out.write(chunk)
            return digest.hexdigest()
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"could not download {url}: {last}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def probe(url: str, fetcher: Fetcher = fetch) -> dict:
    try:
        data = fetcher(url)
        return {"url": url, "ok": True, "bytes": len(data), "error": None}
    except Exception as exc:
        return {"url": url, "ok": False, "bytes": 0, "error": str(exc)}
