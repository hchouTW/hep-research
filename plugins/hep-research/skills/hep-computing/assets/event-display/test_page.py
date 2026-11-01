#!/usr/bin/env python3
"""Browser test of a built bundle: serve it on loopback, drive headless Chromium, compare what the charts hold.

Usage: python3 test_page.py BUNDLE_DIR [--chromium PATH]
Needs Playwright for Python and a Chromium (Playwright's download, or --chromium / HEP_CHROMIUM for a system one).
Checks, in order:
  1. the default event is committed; window.EventDisplay is gone; no integrity error;
  2. every dataset/static panel is ready and its readback equals its payload exactly;
  3. selecting several events quickly ends on the last one, and the event panel shows that event's payload;
  4. a tampered scene object is refused: the event fails and the previous event stays displayed (the tampered
     event is one never fetched before, because objects are cached by digest; with a single event, a fresh page
     whose default scene is tampered must show no event);
  5. every request went to the loopback server (no external network).
Prints JSON {"status": "ok"|"failed", "checks": [...]} even when a step times out or raises (that step is a failed
check); exit 0 ok, 1 failed, 2 bad input, 3 missing dependency.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import sys
import threading
from pathlib import Path


def serve(root: Path):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    request_handler = functools.partial(Quiet, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), request_handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"


def expected_readback(integration: str, payload: dict):
    """What each module's readback() must return for this payload (the panel modules' readback contracts)."""
    if integration == "plotly":
        return [{"x": t["x"], "y": t["y"], "width": t["width"],
                 "error": t["error_y"]["array"] if "error_y" in t else None} for t in payload["data"]]
    if integration == "echarts":
        o = payload["option"]
        return {"categories": o["xAxis"]["data"], "series": [{"name": s["name"], "data": s["data"]} for s in o["series"]]}
    m = payload["members"]
    return {"fArray": m["fArray"], "fSumw2": m["fSumw2"], "fXbins": m["fXaxis"]["fXbins"],
            "fXmin": m["fXaxis"]["fXmin"], "fXmax": m["fXaxis"]["fXmax"],
            "fEntries": m["fEntries"] if m["fEntries"] is not None else 0}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle")
    ap.add_argument("--chromium", default=os.environ.get("HEP_CHROMIUM"))
    a = ap.parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(json.dumps({"status": "missing-dependency", "reason": str(exc)}))
        return 3
    root = Path(a.bundle)
    try:
        b = json.loads((root / "bundle.json").read_text())
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 2
    load = lambda rel: json.loads((root / rel).read_text())  # noqa: E731
    httpd, base = serve(root)
    checks, requests, errors = [], [], []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=a.chromium) if a.chromium else pw.chromium.launch()
            page = browser.new_page()
            page.on("request", lambda r: requests.append(r.url))
            page.on("pageerror", lambda e: errors.append(str(e)))
            keys = [e["key"] for e in b["events"]]
            scene_of = {e["key"]: e["scene"] for e in b["events"]}
            # never fetched before step 4: not the default event, and left out of the rapid switching
            others = [k for k in keys if k != b["default_event"]]
            tampered_key = others[-1] if others else None
            page.goto(base + "index.html")
            committed = "() => window.__eventDisplayTest && window.__eventDisplayTest.committed()"
            page.wait_for_function(f"(k) => {{ const c = ({committed})(); return c && c.key === k; }}",
                                   arg=b["default_event"], timeout=60000)
            state = page.evaluate(f"({committed})()")
            check("default event committed", state["key"] == b["default_event"], str(state))
            check("window.EventDisplay removed", page.evaluate("() => window.EventDisplay === undefined"))

            for p in b["panels"]:
                if p["binding"] == "event":
                    continue
                page.wait_for_function("(id) => window.__eventDisplayTest.panel(id).state !== 'loading'", arg=p["id"],
                                       timeout=30000)
                got = page.evaluate("(id) => window.__eventDisplayTest.panel(id)", p["id"])
                want = expected_readback(p["integration"], load(p["payload"]))
                check(f"panel {p['id']} ({p['integration']}, {p['binding']}) readback equals payload",
                      got["state"] == "ready" and got["data"] == want, got["state"])

            targets = [k for k in keys if k != tampered_key]
            for k in targets:                                           # rapid switching: last one must win
                page.evaluate("(k) => window.__eventDisplayTest.select(k)", k)
            last = targets[-1]
            page.wait_for_function(f"(k) => ({committed})().key === k", arg=last, timeout=30000)
            for p in b["panels"]:
                if p["binding"] != "event":
                    continue
                entry = p["per_event"].get(last)
                page.wait_for_function("(id) => window.__eventDisplayTest.panel(id).state !== 'loading'",
                                       arg=p["id"], timeout=30000)
                got = page.evaluate("(id) => window.__eventDisplayTest.panel(id)", p["id"])
                if entry is None:
                    check(f"panel {p['id']} shows unavailable for {last}", got["state"] == "unavailable", got["state"])
                else:
                    want = expected_readback(p["integration"], load(entry["payload"]))
                    check(f"panel {p['id']} (event) readback equals payload for {last}",
                          got["state"] == "ready" and got["data"] == want, got["state"])

            failed = "() => document.getElementById('status').classList.contains('failed')"
            tamper = lambda route: route.fulfill(status=200, content_type="application/json",  # noqa: E731
                                                 body='{"Hits": {}}')
            if tampered_key is not None:
                page.route(base + scene_of[tampered_key], tamper)
                before = page.evaluate(f"({committed})()")
                page.evaluate("(k) => window.__eventDisplayTest.select(k)", tampered_key)
                page.wait_for_function(failed, timeout=30000)
                after = page.evaluate(f"({committed})()")
                check("tampered scene refused and previous event kept",
                      after["key"] == before["key"] and after["revision"] == before["revision"],
                      page.evaluate("() => document.getElementById('status').textContent"))
            else:                                                    # one event: tamper it on a fresh page
                after = page.evaluate(f"({committed})()")
                fresh = browser.new_page()
                fresh.on("request", lambda r: requests.append(r.url))
                fresh.route(base + scene_of[b["default_event"]], tamper)
                fresh.goto(base + "index.html")
                fresh.wait_for_function(failed, timeout=60000)
                shown = fresh.evaluate(f"() => window.__eventDisplayTest ? ({committed})().key : null")
                check("tampered scene refused (single event: nothing displayed)", shown is None,
                      fresh.evaluate("() => document.getElementById('status').textContent"))
            check("no integrity error from outside the controller", after["integrityErrors"] == 0)
            browser.close()
    except Exception as exc:  # a timeout or a page crash is a failed check, reported as JSON like the others
        check("browser steps completed", False, f"{type(exc).__name__}: {str(exc).splitlines()[0]}")
    finally:
        httpd.shutdown()
    external = sorted({u for u in requests if not u.startswith(base) and not u.startswith("data:")})
    check("no external requests", not external, ", ".join(external[:5]))
    check("no uncaught page errors", not errors, "; ".join(errors[:3]))
    ok = all(c["ok"] for c in checks)
    print(json.dumps({"status": "ok" if ok else "failed", "checks": checks}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
