"""Shared HTTP for source modules: Chrome TLS impersonation (curl_cffi),
retries, polite per-host rate limit, optional RU proxy rotation.

Russian retailers block plain-curl TLS fingerprints (RST on handshake), so we
impersonate Chrome. If proxies.txt exists (proxy_finder.py), requests rotate
through RU proxies — needed for the few hosts that block datacenter IPs.
"""
import itertools
import os
import time

from curl_cffi import requests

IMPERSONATE = "chrome"
_last = {}
_proxy_pool = None
_current_proxy = None


def _next_proxy():
    global _proxy_pool, _current_proxy
    if _proxy_pool is None:
        path = os.path.join(os.path.dirname(__file__), "..", "proxies.txt")
        lines = [l.strip() for l in open(path)] if os.path.exists(path) else []
        lines = [l for l in lines if l]
        _proxy_pool = itertools.cycle(lines) if lines else None
    _current_proxy = next(_proxy_pool) if _proxy_pool else None
    return _current_proxy


def session(extra_headers=None):
    s = requests.Session(impersonate=IMPERSONATE)
    if extra_headers:
        s.headers.update(extra_headers)
    return s


def get(s, url, min_interval=0.5, tries=3, **kw):
    """Rate-limited GET with retries, Chrome TLS, RU-proxy rotation on failure."""
    return _req(s.get, url, min_interval, tries, **kw)


def post(s, url, min_interval=0.5, tries=3, **kw):
    return _req(s.post, url, min_interval, tries, **kw)


def _req(fn, url, min_interval, tries, **kw):
    host = url.split("/")[2]
    wait = _last.get(host, 0) + min_interval - time.time()
    if wait > 0:
        time.sleep(wait)
    proxy = _current_proxy or _next_proxy()
    r = None
    for attempt in range(tries):
        _last[host] = time.time()
        if proxy:
            kw["proxies"] = {"http": proxy, "https": proxy}
        try:
            r = fn(url, timeout=25, **kw)
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            return r
        except requests.RequestsError:
            proxy = _next_proxy()
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt * 2)
    return r
