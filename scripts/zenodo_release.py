#!/usr/bin/env python3
"""Publish a new version of the ClockInToday dataset on Zenodo, under the existing concept DOI.

Usage: ZENODO_TOKEN=... python scripts/zenodo_release.py VERSION [--sandbox] [--dry-run]
Keeps concept DOI 10.5281/zenodo.24058617; each run adds one version with the current CSV.
"""
import datetime, json, os, sys, urllib.request, urllib.error

CONCEPT = "24058617"
FILES = ["clockintoday-no-interview-jobs-data.csv"]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args: sys.exit("usage: zenodo_release.py VERSION [--dry-run]")
VERSION = args[0].lstrip("v")
DRY = "--dry-run" in sys.argv
BASE = "https://zenodo.org/api"
TOKEN = os.environ.get("ZENODO_TOKEN") or sys.exit("ZENODO_TOKEN is not set")

def call(method, url, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url if url.startswith("http") else BASE + url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": ctype, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            t = r.read(); return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} -> {e.code}: {e.read().decode()[:800]}")

latest = call("GET", f"/records/{CONCEPT}/versions/latest")
print("latest published version:", latest["id"], latest["metadata"].get("version"))
if latest["metadata"].get("version") == VERSION:
    sys.exit(f"version {VERSION} is already published; nothing to do")
if DRY:
    print("dry run: token works and the record was found; stopping before any change"); sys.exit(0)

# start a new version (copies the current files and metadata into a draft)
dep = call("POST", f"/deposit/depositions/{latest['id']}/actions/newversion")
draft = call("GET", dep["links"]["latest_draft"])
did = draft["id"]
print("draft:", did)
for f in draft.get("files", []):
    call("DELETE", f"/deposit/depositions/{did}/files/{f['id']}")
for name in FILES:
    with open(name, "rb") as fh:
        call("PUT", f"{draft['links']['bucket']}/{name}", raw=fh.read(), ctype="application/octet-stream")
    print("uploaded", name)
md = draft["metadata"]
for k in ("doi", "prereserve_doi"): md.pop(k, None)
md["version"] = VERSION
md["publication_date"] = datetime.date.today().isoformat()
call("PUT", f"/deposit/depositions/{did}", body={"metadata": md})
pub = call("POST", f"/deposit/depositions/{did}/actions/publish")
print("published", pub.get("doi"), "concept", pub.get("conceptdoi"), pub.get("links", {}).get("html"))
