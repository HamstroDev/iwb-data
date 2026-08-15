#!/usr/bin/env python3
"""One-off: rewrite data/ files so every object lists its fields in one order.

The order comes from SITE_FIELDS and ORIGIN_FIELDS in validate.py.
Fields not in those lists are kept at the end.
"""

import json

import validate

SITE_ORDER = list(validate.SITE_FIELDS)
ORIGIN_ORDER = list(validate.ORIGIN_FIELDS)


def reorder(obj, order):
    out = {key: obj[key] for key in order if key in obj}
    out.update({key: value for key, value in obj.items() if key not in out})
    return out


def main():
    for _, path in validate.data_files()[0]:
        with open(path, encoding="utf-8") as f:
            before = f.read()
        sites = []
        for site in json.loads(before):
            site = reorder(site, SITE_ORDER)
            if isinstance(site.get("origins"), list):
                site["origins"] = [
                    reorder(o, ORIGIN_ORDER) if isinstance(o, dict) else o
                    for o in site["origins"]
                ]
            sites.append(site)
        after = json.dumps(sites, ensure_ascii=False, indent=2) + "\n"
        if after == before:
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(after)
        print(f"rewrote {path}")


if __name__ == "__main__":
    main()
