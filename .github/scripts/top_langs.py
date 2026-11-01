#!/usr/bin/env python3
"""Generate top-langs.svg (most used languages card) from a user's public repos.

Runs inside GitHub Actions using only the standard library.
Env vars:
  GH_USER        GitHub username (default: repository owner)
  GITHUB_TOKEN   token for the GitHub API (provided by Actions)
  MAX_LANGS      how many languages to show (default 6)
  EXCLUDE_LANGS  comma separated languages to hide, e.g. "Jupyter Notebook,Shell"
  OUTPUT         output path (default top-langs.svg)
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com"
USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Fictophilians"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MAX_LANGS = int(os.environ.get("MAX_LANGS", "6"))
EXCLUDE = {s.strip().lower() for s in os.environ.get("EXCLUDE_LANGS", "").split(",") if s.strip()}
OUTPUT = os.environ.get("OUTPUT", "top-langs.svg")

# Theme: indigo, rose pink, aqua (from the profile picture)
COLORS = ["#4F5BD5", "#F06EA9", "#7FDDEA"]
BG, TITLE, TEXT, TRACK = "#0D1117", "#F06EA9", "#C9D1D9", "#21262D"


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "top-langs-card",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    totals, page = {}, 1
    while True:
        repos = get(f"{API}/users/{USER}/repos?per_page=100&type=owner&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            for lang, size in get(repo["languages_url"]).items():
                if lang.lower() not in EXCLUDE:
                    totals[lang] = totals.get(lang, 0) + size
        page += 1
    return totals


def render(totals):
    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:MAX_LANGS]
    total = sum(totals.values()) or 1
    width, row_h, top = 495, 30, 62
    height = top + row_h * len(items) + 18
    bar_x, bar_w = 150, 270
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Most used languages">',
        "<style>",
        "text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif}",
        f".t{{font-size:18px;font-weight:600;fill:{TITLE}}}",
        f".n{{font-size:13px;fill:{TEXT}}}",
        ".p{font-size:12px;fill:#9BA4B5}",
        ".b{transform-box:fill-box;transform-origin:left center;animation:g .9s ease-out both}",
        "@keyframes g{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        "</style>",
        f'<rect width="{width}" height="{height}" rx="6" fill="{BG}"/>',
        '<text class="t" x="25" y="35">Most Used Languages</text>',
    ]
    for i, (lang, size) in enumerate(items):
        pct = size / total * 100
        y = top + i * row_h
        color = COLORS[i % len(COLORS)]
        fill_w = max(bar_w * pct / 100, 4)
        out += [
            f'<text class="n" x="25" y="{y + 11}">{escape(lang)}</text>',
            f'<rect x="{bar_x}" y="{y}" width="{bar_w}" height="12" rx="6" fill="{TRACK}"/>',
            f'<rect class="b" x="{bar_x}" y="{y}" width="{fill_w:.1f}" height="12" rx="6" fill="{color}" style="animation-delay:{i * 0.1:.1f}s"/>',
            f'<text class="p" x="{bar_x + bar_w + 12}" y="{y + 11}">{pct:.1f}%</text>',
        ]
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    totals = collect()
    if not totals:
        print("No language data found; leaving the card unchanged.", file=sys.stderr)
        return 1
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(render(totals))
    print(f"Wrote {OUTPUT} with {min(len(totals), MAX_LANGS)} languages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
