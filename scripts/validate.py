#!/usr/bin/env python3
"""Check the files in data/. Print every problem and exit 1 if any."""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
FAVICON_DIR = os.path.join(ROOT, "favicons")

FILENAME_RE = re.compile(r"^sites([A-Z]+)\.json$")
# Lowercase host, optional port. Non-ASCII letters allowed.
HOST_RE = re.compile(r"^[a-z0-9\-\u00a1-\uffff]+(\.[a-z0-9\-\u00a1-\uffff]+)+(:\d+)?$")

# Characters that look empty but survive str.strip().
INVISIBLE_CHARS = "\u200b\u200c\u200d\u2060\ufeff"

# Allowed values. Extend when the data adds a new one.
KNOWN_PLATFORMS = {"mediawiki", "dokuwiki", "moinmoin"}
KNOWN_TAGS = {"official"}
KNOWN_HOSTS = {"wiki.gg", "Miraheze", "ShoutWiki", "Hooded Horse", "Paradox", "Telepedia"}
KNOWN_ORIGIN_FARMS = {"fandom.com", "neoseeker.com", "fextralife.com"}

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def is_blank(value):
    return not value or all(c.isspace() or c in INVISIBLE_CHARS for c in value)


def check_known(value, known, const_name, field, where):
    if value not in known:
        err(
            f"{where}: unknown {field} '{value}' "
            f"(known: {', '.join(sorted(known))}; "
            f"extend {const_name} in scripts/validate.py if this is a new value)"
        )


def check_base_url(value, field, where):
    if "://" in value:
        err(f"{where}: {field} must not include a scheme: '{value}'")
        return
    if value.endswith("/"):
        err(f"{where}: {field} must not end with '/': '{value}'")
        return
    host, slash, path = value.partition("/")
    if not HOST_RE.match(host):
        err(f"{where}: {field} host '{host}' must be a lowercase hostname with optional port")
    if slash and not re.match(r"^[^\s?#]+$", path):
        err(f"{where}: {field} path '/{path}' must not contain whitespace, '?', or '#'")


def check_origin_base_url(value, field, where):
    check_base_url(value, field, where)
    host = value.partition("/")[0].partition(":")[0]
    if not any(host == farm or host.endswith("." + farm) for farm in KNOWN_ORIGIN_FARMS):
        err(
            f"{where}: {field} '{value}' is not on a known wiki farm "
            f"(known: {', '.join(sorted(KNOWN_ORIGIN_FARMS))}; "
            f"extend KNOWN_ORIGIN_FARMS in scripts/validate.py if this is a new farm)"
        )


def check_path(value, field, where):
    if not value.startswith("/"):
        err(f"{where}: {field} must start with '/': '{value}'")
    elif any(c.isspace() for c in value):
        err(f"{where}: {field} must not contain whitespace: '{value}'")
    elif ".." in value:
        err(f"{where}: {field} must not contain '..': '{value}'")


def check_main_page(value, field, where):
    if "://" in value:
        err(f"{where}: {field} must be a page name, not a URL: '{value}'")
    elif value != value.strip():
        err(f"{where}: {field} has leading or trailing whitespace: '{value}'")
    elif value.startswith("/"):
        err(f"{where}: {field} must not start with '/': '{value}'")


def check_platform(value, field, where):
    check_known(value, KNOWN_PLATFORMS, "KNOWN_PLATFORMS", field, where)


def check_host(value, field, where):
    check_known(value, KNOWN_HOSTS, "KNOWN_HOSTS", field, where)


def check_tags(value, field, where):
    for tag in value:
        if not isinstance(tag, str):
            err(f"{where}: tags must be strings")
        else:
            check_known(tag, KNOWN_TAGS, "KNOWN_TAGS", field, where)


# field name -> (type, required, format checker)
SITE_FIELDS = {
    "id": (str, True, None),  # checked in validate_site
    "origins_label": (str, True, None),
    "origins": (list, True, None),  # checked in validate_site
    "destination": (str, True, None),
    "destination_base_url": (str, True, check_base_url),
    "destination_platform": (str, True, check_platform),
    "destination_icon": (str, True, None),  # checked in validate_site
    "destination_main_page": (str, True, check_main_page),
    "destination_search_path": (str, True, check_path),
    "destination_content_path": (str, True, check_path),
    "destination_host": (str, False, check_host),
    "destination_content_prefix": (str, False, None),
    "destination_content_suffix": (str, False, None),
    "tags": (list, False, check_tags),
}

ORIGIN_FIELDS = {
    "origin": (str, True, None),
    "origin_base_url": (str, True, check_origin_base_url),
    "origin_content_path": (str, True, check_path),
    "origin_main_page": (str, True, check_main_page),
    "destination_content_prefix": (str, False, None),
}


def check_fields(obj, schema, where):
    for name, (ftype, required, checker) in schema.items():
        if name not in obj:
            if required:
                err(f"{where}: missing required field '{name}'")
            continue
        value = obj[name]
        if not isinstance(value, ftype):
            err(f"{where}: field '{name}' must be {ftype.__name__}")
            continue
        if ftype is str and is_blank(value):
            err(f"{where}: field '{name}' is empty")
            continue
        if checker:
            checker(value, name, where)
    for name in obj:
        if name not in schema:
            err(f"{where}: unknown field '{name}'")


def data_files():
    """Return (lang, path) pairs and rejected filenames. Skips dotfiles."""
    matched, rejected = [], []
    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.startswith("."):
            continue
        path = os.path.join(DATA_DIR, filename)
        m = FILENAME_RE.match(filename)
        if m and os.path.isfile(path):
            matched.append((m.group(1), path))
        else:
            rejected.append(filename)
    return matched, rejected


def validate_site(site, lang, id_re, where, seen_ids, seen_origins, favicon_names):
    check_fields(site, SITE_FIELDS, where)

    site_id = site.get("id")
    if isinstance(site_id, str):
        if not id_re.match(site_id):
            err(f"{where}: id '{site_id}' must match {id_re.pattern}")
        if site_id in seen_ids:
            err(f"{where}: duplicate id '{site_id}' (also in {seen_ids[site_id]})")
        else:
            seen_ids[site_id] = where

    icon = site.get("destination_icon")
    if isinstance(icon, str):
        if "/" in icon or "\\" in icon:
            err(f"{where}: destination_icon must be a bare filename: '{icon}'")
        elif icon not in favicon_names:
            err(f"{where}: destination_icon '{icon}' not found in favicons/{lang.lower()}/")

    origins = site.get("origins")
    if isinstance(origins, list):
        if not origins:
            err(f"{where}: origins must not be empty")
        for i, origin in enumerate(origins):
            owhere = f"{where} origins[{i}]"
            if not isinstance(origin, dict):
                err(f"{owhere}: must be an object")
                continue
            check_fields(origin, ORIGIN_FIELDS, owhere)
            key = (origin.get("origin_base_url"), origin.get("origin_content_path"))
            if all(isinstance(k, str) for k in key):
                if key in seen_origins:
                    err(f"{owhere}: duplicate origin {key[0]}{key[1]} (also in {seen_origins[key]})")
                else:
                    seen_origins[key] = owhere


def main():
    errors.clear()
    warnings.clear()

    if not os.path.isdir(DATA_DIR):
        print("error: data/ directory not found")
        return 1

    files, rejected = data_files()
    for filename in rejected:
        err(f"data/{filename}: filename must match sites<LANG>.json (uppercase language code)")
    if not files:
        err("data/ contains no sites<LANG>.json files")

    seen_ids = {}
    seen_origins = {}
    used_icons = set()

    for lang, path in files:
        filename = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                sites = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            err(f"data/{filename}: invalid JSON: {e}")
            continue

        if not isinstance(sites, list):
            err(f"data/{filename}: top level must be a list")
            continue

        favicon_lang_dir = os.path.join(FAVICON_DIR, lang.lower())
        if os.path.isdir(favicon_lang_dir):
            favicon_names = set(os.listdir(favicon_lang_dir))
        else:
            favicon_names = set()
            err(f"favicons/{lang.lower()}/ directory not found for data/{filename}")

        id_re = re.compile(rf"^{lang.lower()}-[a-z0-9_-]+$")
        ids_in_file = []
        for idx, site in enumerate(sites):
            where = f"data/{filename}[{idx}]"
            if not isinstance(site, dict):
                err(f"{where}: must be an object")
                continue
            if isinstance(site.get("id"), str):
                where = f"{where} '{site['id']}'"
                ids_in_file.append(site["id"])
            validate_site(site, lang, id_re, where, seen_ids, seen_origins, favicon_names)
            if isinstance(site.get("destination_icon"), str):
                used_icons.add((lang.lower(), site["destination_icon"]))

        if ids_in_file != sorted(ids_in_file):
            err(f"data/{filename}: entries must be sorted by id")

    # Warn on unused favicons; do not fail.
    if os.path.isdir(FAVICON_DIR):
        for lang_dir in sorted(os.listdir(FAVICON_DIR)):
            lang_path = os.path.join(FAVICON_DIR, lang_dir)
            if lang_dir.startswith(".") or not os.path.isdir(lang_path):
                continue
            for icon in sorted(os.listdir(lang_path)):
                if icon.startswith(".") or not os.path.isfile(os.path.join(lang_path, icon)):
                    continue
                if (lang_dir, icon) not in used_icons:
                    warnings.append(f"no site references favicons/{lang_dir}/{icon}")

    report()
    return 1 if errors else 0


def report():
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    if errors:
        print(f"\nValidation failed with {len(errors)} error(s).")
    else:
        print("Validation passed.")


if __name__ == "__main__":
    sys.exit(main())
