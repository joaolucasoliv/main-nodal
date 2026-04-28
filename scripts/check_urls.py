#!/usr/bin/env python3
"""
Ping every URL in the leaders CSV and flag anything that doesn't resolve cleanly.

Usage:
    python scripts/check_urls.py                                  # default: data/urban_changemakers_latam.csv
    python scripts/check_urls.py data/some_other.csv

Outputs a table to stdout:
    OK     2xx/3xx
    DEAD   4xx/5xx, DNS error, timeout
    SLOW   responded but >5s

Exits 0 always — this is a report, not a gate.
"""
import csv
import socket
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_CSV = Path(__file__).parent.parent / "data" / "urban_changemakers_latam.csv"
TIMEOUT = 6
HEADERS = {"User-Agent": "Mozilla/5.0 (NodalLinkChecker/1.0)"}

# Fall back to unverified TLS for environments where the system trust store is
# missing roots — browsers would still reach these sites, so SSL trust failures
# tell us about the runtime, not the domain.
INSECURE_CTX = ssl._create_unverified_context()


def _request(url: str, method: str, ctx) -> int:
    req = Request(url, headers=HEADERS, method=method)
    return urlopen(req, timeout=TIMEOUT, context=ctx).getcode()


def check(url: str) -> tuple[str, str, float]:
    """Return (status, detail, elapsed_seconds)."""
    if not url or not url.strip():
        return ("EMPTY", "", 0.0)
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)
    if parsed.netloc.endswith("example.com"):
        return ("PLACEHOLDER", "example.com is not a real host", 0.0)

    start = time.monotonic()
    note = ""
    code = None
    for ctx, ctx_name in ((ssl.create_default_context(), "verified"),
                          (INSECURE_CTX, "unverified")):
        try:
            try:
                code = _request(url, "HEAD", ctx)
            except HTTPError as e:
                if e.code in (405, 403, 501):
                    code = _request(url, "GET", ctx)
                else:
                    code = e.code
            if ctx_name == "unverified":
                note = "TLS-unverified"
            break
        except URLError as e:
            # urllib wraps SSL errors in URLError(reason=ssl.SSLError(...))
            if isinstance(e.reason, ssl.SSLError):
                continue
            return ("DEAD", f"URLError: {e.reason}", time.monotonic() - start)
        except (socket.timeout, ConnectionResetError) as e:
            return ("DEAD", f"{type(e).__name__}: {e}", time.monotonic() - start)
        except Exception as e:
            return ("DEAD", f"{type(e).__name__}: {e}", time.monotonic() - start)
    if code is None:
        return ("DEAD", "TLS handshake failed in both modes", time.monotonic() - start)

    elapsed = time.monotonic() - start
    detail = f"HTTP {code}" + (f" · {note}" if note else "")
    if 200 <= code < 400:
        return ("SLOW" if elapsed > 5 else "OK", detail, elapsed)
    return ("DEAD", detail, elapsed)


def main() -> int:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))

    targets = [(r["name"], r.get("website", "").strip()) for r in rows]

    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(check, url): (name, url) for name, url in targets}
        for fut in as_completed(futs):
            name, url = futs[fut]
            status, detail, elapsed = fut.result()
            results.append((status, name, url, detail, elapsed))

    # Stable order: DEAD/PLACEHOLDER first, then SLOW, then OK, then EMPTY
    order = {"DEAD": 0, "PLACEHOLDER": 1, "SLOW": 2, "OK": 3, "EMPTY": 4}
    results.sort(key=lambda r: (order.get(r[0], 9), r[1].lower()))

    name_w = max((len(r[1]) for r in results), default=20)
    counts = {}
    for status, name, url, detail, elapsed in results:
        counts[status] = counts.get(status, 0) + 1
        print(f"{status:<11} {name:<{name_w}}  {elapsed:5.2f}s  {detail:<24}  {url}")

    print()
    print("Summary: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
