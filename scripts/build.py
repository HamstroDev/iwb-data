#!/usr/bin/env python3
"""Validate, then merge data/ into one deployable file.

Writes:
  <outdir>/api/v1/data.json  - all sites, each with a "language" field
  <outdir>/api/favicons/     - copy of the favicon tree
  <outdir>/_headers          - Cloudflare Pages headers
"""

import datetime
import json
import os
import shutil
import sys

import validate

HEADERS = """\
/api/v1/data.json
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=3600

/api/favicons/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=86400
"""


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "dist"
    outdir = arg if os.path.isabs(arg) else os.path.join(validate.ROOT, arg)

    if validate.main() != 0:
        print("Build aborted: fix validation errors first.")
        return 1

    sites = []
    for lang, path in validate.data_files()[0]:
        with open(path, encoding="utf-8") as f:
            for site in json.load(f):
                site["language"] = lang
                sites.append(site)

    data = {
        "schemaVersion": 1,
        "generated": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "count": len(sites),
        "sites": sites,
    }

    api_dir = os.path.join(outdir, "api", "v1")
    os.makedirs(api_dir, exist_ok=True)
    out_path = os.path.join(api_dir, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    favicon_out = os.path.join(outdir, "api", "favicons")
    if os.path.isdir(favicon_out):
        shutil.rmtree(favicon_out)
    shutil.copytree(validate.FAVICON_DIR, favicon_out, ignore=shutil.ignore_patterns(".*"))
    icon_count = sum(len(files) for _, _, files in os.walk(favicon_out))

    with open(os.path.join(outdir, "_headers"), "w", encoding="utf-8") as f:
        f.write(HEADERS)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Wrote {out_path}: {len(sites)} sites, {size_kb:.0f} KB")
    print(f"Copied {icon_count} favicons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
