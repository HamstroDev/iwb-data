#!/usr/bin/env python3
"""Validate, then build deployable data files from data/.

Writes:
  <outdir>/v1/all-data.json     - all sites, each with a "language" field
  <outdir>/v1/<lang>-data.json  - one file per language (e.g. en-data.json)
  <outdir>/favicons/            - copy of the favicon tree
  <outdir>/_headers             - Cloudflare Pages headers
"""

import datetime
import json
import os
import shutil
import sys

import validate

HEADERS = """\
/v1/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=3600

/favicons/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=86400
"""


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "dist"
    outdir = arg if os.path.isabs(arg) else os.path.join(validate.ROOT, arg)

    if validate.main() != 0:
        print("Build aborted: fix validation errors first.")
        return 1

    generated = (
        datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    )
    commit = os.environ.get("GITHUB_SHA", "local")

    def envelope(sites):
        return {
            "schemaVersion": 1,
            "generated": generated,
            "commit": commit,
            "count": len(sites),
            "sites": sites,
        }

    def write_json(path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    v1_dir = os.path.join(outdir, "v1")
    os.makedirs(v1_dir, exist_ok=True)

    all_sites = []
    for lang, path in validate.data_files()[0]:
        with open(path, encoding="utf-8") as f:
            lang_sites = json.load(f)
        for site in lang_sites:
            site["language"] = lang
        all_sites.extend(lang_sites)
        write_json(os.path.join(v1_dir, f"{lang.lower()}-data.json"), envelope(lang_sites))

    out_path = os.path.join(v1_dir, "all-data.json")
    write_json(out_path, envelope(all_sites))

    favicon_out = os.path.join(outdir, "favicons")
    if os.path.isdir(favicon_out):
        shutil.rmtree(favicon_out)
    shutil.copytree(validate.FAVICON_DIR, favicon_out, ignore=shutil.ignore_patterns(".*"))
    icon_count = sum(len(files) for _, _, files in os.walk(favicon_out))

    with open(os.path.join(outdir, "_headers"), "w", encoding="utf-8") as f:
        f.write(HEADERS)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Wrote {out_path}: {len(all_sites)} sites, {size_kb:.0f} KB")
    print(f"Copied {icon_count} favicons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
