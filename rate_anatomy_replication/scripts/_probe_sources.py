"""One-off probe: locate SF Fed yield-premium downloads and inspect FRED DGS10."""
from __future__ import annotations

import re
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

ctx = ssl.create_default_context()


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research-replication"})
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read()


def main() -> None:
    # FRED
    fred_path = RAW / "fred_dgs10.csv"
    if not fred_path.exists() or fred_path.stat().st_size < 100:
        print("Downloading FRED DGS10...")
        data = fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10")
        fred_path.write_bytes(data)
    text = fred_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    print(f"FRED DGS10: {fred_path} ({fred_path.stat().st_size} bytes)")
    print("  head:", text[:3])
    print("  tail:", text[-3:])

    # SF Fed page scrape
    page_url = (
        "https://www.frbsf.org/research-and-insights/data-and-indicators/"
        "treasury-yield-premiums/"
    )
    print("Fetching SF Fed page...")
    html = fetch(page_url).decode("utf-8", errors="replace")
    rel = sorted(set(re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv))["\']', html, flags=re.I)))
    abs_links = sorted(set(re.findall(r'https?://[^"\']+\.(?:xlsx?|xls|csv)', html, flags=re.I)))
    print(f"  relative file hrefs ({len(rel)}):")
    for L in rel:
        print("   ", L)
    print(f"  absolute file urls ({len(abs_links)}):")
    for L in abs_links:
        print("   ", L)

    # Also try common wp-content patterns mentioned on page
    candidates = []
    for L in rel + abs_links:
        if L.startswith("http"):
            candidates.append(L)
        elif L.startswith("/"):
            candidates.append("https://www.frbsf.org" + L)
        else:
            candidates.append("https://www.frbsf.org/" + L.lstrip("./"))

    for url in candidates:
        name = url.rsplit("/", 1)[-1]
        out = RAW / f"sf_fed_{name}"
        try:
            print(f"Trying download: {url}")
            blob = fetch(url)
            out.write_bytes(blob)
            print(f"  OK -> {out} ({len(blob)} bytes)")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {exc}")


if __name__ == "__main__":
    main()
