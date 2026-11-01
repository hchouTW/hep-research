#!/usr/bin/env python3
"""Assemble a self-contained, content-addressed event-display bundle from exported files and a built web page.

Usage: python3 build_bundle.py bundle-spec.json
The spec (see bundle-spec.example.json; relative paths are relative to the spec file) names the event export
directory, geometry files, panels with their payload and sidecar files, the built web directory and the output
directory. Writes OUT/bundle.json, OUT/objects/<sha256>.<ext> (every data file, named by its content) and the web
files (index.html, assets/). The page reads only bundle.json and the objects it lists.
Event-bound panels: a missing per-event result is left out and listed in bundle.json "coverage" (shown as
"unavailable", never as zero).
Prints JSON {"status": ...}; exit 0 ok, 2 bad input.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

SCHEMA = "event-display-bundle/1"


def put_object(src: Path, objects: Path) -> tuple[str, str]:
    content_bytes = src.read_bytes()
    digest = hashlib.sha256(content_bytes).hexdigest()
    name = f"{digest}{src.suffix.lower()}"
    target = objects / name
    if not target.exists():
        target.write_bytes(content_bytes)
    return f"objects/{name}", digest


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(json.dumps({"status": "rejected", "reason": "usage: build_bundle.py bundle-spec.json"}))
        return 2
    spec_path = Path(argv[0]).resolve()
    base = spec_path.parent
    try:
        spec = json.loads(spec_path.read_text())
        out = (base / spec["out"]).resolve()
        web = (base / spec["web"]).resolve()
        record = json.loads((base / spec["events_export"] / "export-record.json").read_text())
        if not (web / "index.html").is_file():
            raise ValueError(f"{web} has no index.html; build the web page first (npm run build)")
        if out == web or web in out.parents:
            raise ValueError("out must not be inside the web build directory")
        if out.exists():
            shutil.rmtree(out)
        objects = out / "objects"
        objects.mkdir(parents=True)
        shutil.copytree(web, out, dirs_exist_ok=True)

        events = []
        for e in record["events"]:
            src = base / spec["events_export"] / e["file"]
            path, digest = put_object(src, objects)
            if digest != e["sha256"]:
                raise ValueError(f"{src} changed after export (sha256 differs from export-record.json)")
            key = f'{e["id"]["run"]}_{e["id"]["subrun"]}_{e["id"]["event"]}'
            events.append({"key": key, "id": e["id"], "scene": path, "sha256": digest, "objects": e["objects"]})
        keys = [e["key"] for e in events]
        default = spec.get("default_event", keys[0] if keys else None)
        if default not in keys:
            raise ValueError(f"default_event {default!r} is not an exported event")

        geometry = []
        for g in spec.get("geometry", []):
            if g.get("format") != "obj" or g.get("unit") != "mm":
                raise ValueError("this template takes OBJ geometry in mm (convert units upstream)")
            path, digest = put_object(base / g["file"], objects)
            geometry.append({"name": g["name"], "format": "obj", "object": path, "sha256": digest, "unit": "mm",
                             "labels": g.get("labels", [])})

        panels, coverage, verification = [], {}, []
        for p in spec["panels"]:
            if p["binding"] not in ("event", "dataset", "static"):
                raise ValueError(f"panel {p['id']}: binding must be event, dataset or static")
            entry = {k: p[k] for k in ("id", "title", "integration", "binding")}
            if p["binding"] == "event":
                entry["per_event"], missing = {}, []
                for key in keys:
                    f = base / p["per_event"].format(key=key)
                    if not f.is_file():
                        missing.append(key)
                        continue
                    path, digest = put_object(f, objects)
                    entry["per_event"][key] = {"payload": path, "sha256": digest}
                    s_path, s_digest = put_object(base / p["sidecar"].format(key=key), objects)
                    verification.append({"panel": p["id"], "event": key, "payload": path, "sidecar": s_path})
                coverage[p["id"]] = {"events": len(keys), "available": len(keys) - len(missing), "missing": missing}
            else:
                path, digest = put_object(base / p["payload"], objects)
                entry.update(payload=path, sha256=digest)
                s_path, _ = put_object(base / p["sidecar"], objects)
                verification.append({"panel": p["id"], "payload": path, "sidecar": s_path})
            panels.append(entry)
    except (KeyError, ValueError, OSError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 2

    bundle = {"schema": SCHEMA, "title": spec["title"],
              "labels": sorted(set(spec.get("labels", [])) | {record.get("status_label", "unvalidated")}),
              "events": events, "default_event": default, "geometry": geometry, "panels": panels,
              "view": spec.get("view", {}),
              "coverage": coverage, "verification": verification,   # verification: for check_bundle.py, not the page
              "provenance": {"event_export_inputs": record["inputs"]}}
    (out / "bundle.json").write_text(json.dumps(bundle, indent=1, allow_nan=False))
    print(json.dumps({"status": "ok", "out": str(out), "events": len(events), "panels": len(panels),
                      "objects": len(list(objects.iterdir())), "coverage": coverage}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
