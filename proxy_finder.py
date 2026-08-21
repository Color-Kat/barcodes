"""Find working free Russian HTTP proxies.

Downloads free RU proxy lists, tests each concurrently:
  1) proxy answers and is actually RU (ip-api.com through proxy)
  2) proxy opens a Russian retail site
Working ones -> proxies.txt (best-first by latency).
Usage: .venv/bin/python proxy_finder.py [--target https://www.vkusvill.ru/]
Re-run any time: free proxies die within hours, refresh before each scrape run.
"""
import argparse
import concurrent.futures as cf
import json
import re
import time

import requests

LISTS = [
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/RU/data.txt",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=ru&protocol=http&proxy_format=protocolipport&format=text",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_geolocation/http.txt",
    "https://proxylist.geonode.com/api/proxy-list?country=RU&limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps",
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def collect():
    proxies = set()
    for url in LISTS:
        try:
            body = requests.get(url, timeout=25, headers={"User-Agent": UA}).text
        except requests.RequestException as e:
            print(f"list failed: {url.split('/')[2]}: {e}")
            continue
        if body.lstrip().startswith("{"):  # geonode JSON
            for p in json.loads(body).get("data", []):
                proxies.add(f"http://{p['ip']}:{p['port']}")
        else:
            for m in re.finditer(r"(?:(https?|socks[45])://)?(\d+\.\d+\.\d+\.\d+):(\d+)", body):
                scheme = m.group(1) or "http"
                if scheme.startswith("http"):
                    proxies.add(f"http://{m.group(2)}:{m.group(3)}")
        # monosans list is global: RU filtering happens at test stage anyway
    return proxies


def test(proxy, target):
    px = {"http": proxy, "https": proxy}
    try:
        t0 = time.time()
        r = requests.get("http://ip-api.com/json", proxies=px, timeout=10)
        geo = r.json()
        if geo.get("countryCode") != "RU":
            return None
        r = requests.get(target, proxies=px, timeout=15,
                         headers={"User-Agent": UA}, allow_redirects=True)
        if r.status_code >= 500 or r.status_code in (403, 429):
            return None
        return (time.time() - t0, proxy, geo.get("isp", "?"), r.status_code)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="https://www.vkusvill.ru/")
    ap.add_argument("--workers", type=int, default=64)
    args = ap.parse_args()

    cand = collect()
    print(f"candidates: {len(cand)}")
    ok = []
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for res in ex.map(lambda p: test(p, args.target), cand):
            if res:
                ok.append(res)
                print(f"OK {res[1]} {res[0]:.1f}s {res[3]} {res[2]}")
    ok.sort()
    with open("proxies.txt", "w") as f:
        f.write("\n".join(p for _, p, _, _ in ok) + "\n")
    print(f"working RU proxies: {len(ok)} -> proxies.txt")


if __name__ == "__main__":
    main()
