"""Shared scraping helpers: one curl_cffi session style + one progress loop, so
every source gets identical observable behaviour (the thing the blind v1 run
lacked) and the orchestrator can parse a uniform heartbeat line.

Rules baked in (per project constraint): 5s hard timeout, NO retries, and a
loud bail when the IP is being throttled instead of grinding silently.
"""
import os
import sys
import time

from curl_cffi import requests

TIMEOUT = 5
SLEEP = 0.4


def proxies():
    """Read BARCODES_PROXY env -> curl_cffi proxies dict, or None.

    Set it to route every source through a RU exit (the datacenter IP is
    blocked by most retailers):
      export BARCODES_PROXY=socks5://127.0.0.1:10808
      export BARCODES_PROXY=http://user:pass@host:port
    """
    p = os.environ.get("BARCODES_PROXY")
    return {"http": p, "https": p} if p else None


def session(headers=None, impersonate="chrome"):
    s = requests.Session(impersonate=impersonate, timeout=TIMEOUT)
    px = proxies()
    if px:
        s.proxies.update(px)
    if headers:
        s.headers.update(headers)
    return s


def _line(source, i, total, ok, dead, t0, last_name):
    el = time.time() - t0
    rate = i / max(el, 1e-9)
    eta = int((total - i) / max(rate, 1e-9)) if total else 0
    print(f"\r[{source}] {i}/{total} | ok {ok} dead {dead} | {rate:.1f}/s | "
          f"ETA {eta}s | {last_name[:32]}", end="", file=sys.stderr, flush=True)


def scrape_urls(source, urls, fetch_one, sleep=SLEEP, bail_dead=25):
    """Drive a URL list through fetch_one(url)->dict|None, yielding dicts and
    printing live progress. Bails loudly if the first `bail_dead` fetches all
    fail (IP throttled) so the user isn't left staring at a silent hang.

    fetch_one must do its own GET+parse and return a source dict or None. It
    should not raise for a dead page (return None); unexpected raises are
    swallowed here as one dead item.
    """
    total = len(urls)
    if not total:
        print(f"[{source}] no URLs to scrape — source unreachable? Aborting.",
              file=sys.stderr, flush=True)
        return
    print(f"[{source}] scraping {total} pages (5s timeout, no retry)...",
          file=sys.stderr, flush=True)
    t0, ok, dead = time.time(), 0, 0
    for i, url in enumerate(urls, 1):
        try:
            d = fetch_one(url)
        except Exception:
            d = None
        if d:
            ok += 1
            yield d
        else:
            dead += 1
        if i % 10 == 0 or i == total:
            _line(source, i, total, ok, dead, t0, (d or {}).get("name", "-") if d else "-")
        if dead >= bail_dead and ok == 0:
            print(f"\n[{source}] {bail_dead} dead fetches, 0 ok — IP is being "
                  f"throttled. Stop and run from a RU IP / proxy.",
                  file=sys.stderr, flush=True)
            return
        time.sleep(sleep)
    print(file=sys.stderr)
