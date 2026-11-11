import hashlib
import io
import json
import time
import urllib.parse
import urllib.request
import zipfile
from typing import Callable, Sequence

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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def openfema_records(endpoint: str, page_size: int = 10000, fetcher: Fetcher = fetch, max_pages: int = 500) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    digests: list[str] = []
    skip = 0
    while True:
        if len(digests) >= max_pages:
            raise RuntimeError(f"stopped after {max_pages} pages; the source may be ignoring $skip")
        query = urllib.parse.urlencode({"$top": page_size, "$skip": skip, "$format": "json"}, safe="$")
        raw = fetcher(f"{endpoint}?{query}")
        digest = sha256(raw)
        if digests and digest == digests[-1]:
            raise RuntimeError("the same page came back twice; the source may be ignoring $skip")
        digests.append(digest)
        payload = json.loads(raw)
        keys = [k for k in payload if k != "metadata"]
        if len(keys) != 1:
            raise ValueError(f"unexpected OpenFEMA response keys: {sorted(payload)}")
        page = payload[keys[0]]
        rows.extend(page)
        if len(page) < page_size:
            return rows, digests
        skip += page_size


def first_working(urls: Sequence[str], fetcher: Fetcher = fetch) -> tuple[str, bytes]:
    errors = []
    for url in urls:
        try:
            return url, fetcher(url)
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("no source could be downloaded: " + " | ".join(errors))


def zip_member(data: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        match = [n for n in names if n.rsplit("/", 1)[-1].lower() == name.lower()]
        if not match:
            raise ValueError(f"{name} not found in archive, which holds: {names}")
        return zf.read(match[0])
