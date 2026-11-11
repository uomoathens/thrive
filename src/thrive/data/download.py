import hashlib
import json
import shutil
import time
import urllib.parse
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


def payload_rows(raw: bytes) -> list[dict]:
    payload = json.loads(raw)
    keys = [k for k in payload if k != "metadata"]
    if len(keys) != 1:
        raise ValueError(f"unexpected OpenFEMA response keys: {sorted(payload)}")
    return payload[keys[0]]


def openfema_records(endpoint: str, page_size: int = 1000, fetcher: Fetcher = fetch, max_pages: int = 2000) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    digests: list[str] = []
    skip = 0
    while True:
        if len(digests) >= max_pages:
            raise RuntimeError(f"stopped after {max_pages} pages; the source may be ignoring $skip")
        query = urllib.parse.urlencode({"$top": page_size, "$skip": skip}, safe="$")
        raw = fetcher(f"{endpoint}?{query}")
        digest = sha256(raw)
        if digests and digest == digests[-1]:
            raise RuntimeError("the same page came back twice; the source may be ignoring $skip")
        digests.append(digest)
        page = payload_rows(raw)
        rows.extend(page)
        if len(page) < page_size:
            return rows, digests
        skip += page_size


def discover_openfema_endpoint(name: str, catalog_url: str, fetcher: Fetcher = fetch) -> str:
    rows = payload_rows(fetcher(catalog_url))
    versions = []
    for r in rows:
        if str(r.get("name", "")).lower() == name.lower():
            try:
                versions.append(int(float(r.get("version"))))
            except (TypeError, ValueError):
                continue
    if not versions:
        raise ValueError(f"{name} not listed in the OpenFEMA catalog")
    return f"https://www.fema.gov/api/open/v{max(versions)}/{name}"


def arcgis_records(query_url: str, page_size: int = 2000, fetcher: Fetcher = fetch, max_pages: int = 500) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    digests: list[str] = []
    offset = 0
    while True:
        if len(digests) >= max_pages:
            raise RuntimeError(f"stopped after {max_pages} pages of {query_url}")
        params = {
            "where": "1=1",
            "outFields": "*",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "OBJECTID ASC",
            "returnGeometry": "false",
            "f": "json",
        }
        raw = fetcher(f"{query_url}?{urllib.parse.urlencode(params)}")
        digest = sha256(raw)
        if digests and digest == digests[-1]:
            raise RuntimeError("the same page came back twice from the ArcGIS service")
        digests.append(digest)
        payload = json.loads(raw)
        if "error" in payload:
            raise RuntimeError(f"ArcGIS service error: {payload['error']}")
        features = payload.get("features", [])
        rows.extend(f.get("attributes", {}) for f in features)
        if not features or (len(features) < page_size and not payload.get("exceededTransferLimit")):
            return rows, digests
        offset += len(features)


def probe(url: str, fetcher: Fetcher = fetch) -> dict:
    try:
        data = fetcher(url)
        return {"url": url, "ok": True, "bytes": len(data), "error": None}
    except Exception as exc:
        return {"url": url, "ok": False, "bytes": 0, "error": str(exc)}
