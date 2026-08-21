"""One-shot orchestrator: scrape every source in parallel, then match + merge.

    .venv/bin/python run_all.py                 # all default sources
    .venv/bin/python run_all.py vkusvill magnit # a subset
    .venv/bin/python run_all.py --limit 200     # cap each source (smoke test)

Each source runs as its own `run.py fetch <src>` process (own DB connection,
own host — parallelism is safe and per-host rate stays independent). A live
dashboard shows per-source progress read from logs/<src>.log. When every
source finishes, it runs `match`, `merge`, `stats` automatically — so you can
start it and walk away.

Sources hitting different hosts don't compete; a throttled/blocked source just
reports 'blocked' and the others keep going. Re-run any time — everything
upserts (actualization).
"""
import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable          # same interpreter that launched us (Win: python.exe, Linux: venv/bin/python)
LOGDIR = os.path.join(HERE, "logs")

# Default set = sources that work from a RU IP without a proxy, best first
# (metro carries EAN directly). Blocked ones (lenta/ozon/perekrestok — need app
# headers/captcha/proxy) are opt-in by naming them explicitly.
DEFAULT_SOURCES = ["metro", "wildberries", "vkusvill", "magnit"]

PROG_RE = re.compile(r"\[(\w+)\]\s+(\d+)/(\d+)\s+\|\s+ok\s+(\d+)\s+dead\s+(\d+)\s+\|\s+([\d.]+)/s")
SAVED_RE = re.compile(r"\[(\w+)\]\s+saved\s+(\d+)\s+total")
BAIL_RE = re.compile(r"throttled|unreachable|no URLs")


def last_status(logpath):
    """Return a short status string from the tail of a source log."""
    try:
        with open(logpath, encoding="utf-8", errors="replace") as f:
            tail = f.readlines()[-6:]
    except FileNotFoundError:
        return "starting..."
    text = "".join(tail)
    saved = None
    for line in reversed(tail):
        m = SAVED_RE.search(line)
        if m:
            saved = m.group(2)
            break
    prog = None
    for line in reversed(tail):
        m = PROG_RE.search(line)
        if m:
            prog = f"{m.group(2)}/{m.group(3)}  ok {m.group(4)} dead {m.group(5)}  {m.group(6)}/s"
            break
    if saved and not prog:
        return f"saved {saved} ✓"
    if prog:
        return prog
    if BAIL_RE.search(text):
        return "BLOCKED (needs RU IP/proxy)"
    return "starting..."


def run_step(label, *args):
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([PY, os.path.join(HERE, "run.py"), *args], cwd=HERE)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*", help="source names (default: working set)")
    ap.add_argument("--limit", type=int, default=None, help="cap each source")
    a = ap.parse_args()
    sources = a.sources or DEFAULT_SOURCES
    limit = a.limit
    os.makedirs(LOGDIR, exist_ok=True)

    procs = {}
    for src in sources:
        cmd = [PY, os.path.join(HERE, "run.py"), "fetch", src]
        if limit:
            cmd += ["--limit", str(limit)]
        log = open(os.path.join(LOGDIR, f"{src}.log"), "w")
        procs[src] = (subprocess.Popen(cmd, cwd=HERE, stdout=log, stderr=log), log)

    print(f"launched {len(procs)} scrapers: {', '.join(sources)}")
    print(f"logs in {LOGDIR}/<source>.log — full progress there\n")

    def stop(*_):
        for p, _log in procs.values():
            p.terminate()
        print("\nstopped.")
        sys.exit(1)
    signal.signal(signal.SIGINT, stop)

    # live dashboard until all processes exit
    t0 = time.time()
    while any(p.poll() is None for p, _ in procs.values()):
        lines = [f"  {src:14} {'running' if p.poll() is None else 'done   '}  "
                 f"{last_status(os.path.join(LOGDIR, src + '.log'))}"
                 for src, (p, _) in procs.items()]
        el = int(time.time() - t0)
        sys.stdout.write("\033[H\033[J")  # clear screen
        print(f"barcodes scrape — {el}s elapsed\n")
        print("\n".join(lines))
        print("\n(Ctrl-C to stop; then re-run any time, it resumes via upsert)")
        time.sleep(3)

    for _src, (p, log) in procs.items():
        log.close()
    print("\nall scrapers finished. Bridging + merging...\n")

    run_step("match (name -> barcode)", "match")
    run_step("merge", "merge")
    run_step("stats", "stats")
    print("\nDONE. Fully-enriched products are in the `products` table.")


if __name__ == "__main__":
    main()
