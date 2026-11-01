#!/usr/bin/env python3
"""Generate a "Most Used Languages" SVG card for a GitHub profile README.

Runs inside GitHub Actions (see top-langs.yml). Uses only the Python
standard library and the GitHub API, so there is no third-party service
that can go down or hit rate limits.
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "Fictophilians")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = os.environ.get("OUTPUT", "top-langs.svg")
TOP_N = int(os.environ.get("TOP_N", "6"))
# Optional, comma-separated. Example: EXCLUDE_LANGS="HTML,CSS"
EXCLUDE_LANGS = {s.strip().lower() for s in os.environ.get("EXCLUDE_LANGS", "").split(",") if s.strip()}
EXCLUDE_REPOS = {s.strip().lower() for s in os.environ.get("EXCLUDE_REPOS", "").split(",") if s.strip()}

# Theme (matches the profile picture)
BG = "#0D1117"
TITLE = "#F06EA9"
TEXT = "#C9D1D9"
MUTED = "#9BA4B5"
PALETTE = ["#4F5BD5", "#F06EA9", "#7FDDEA", "#8B7BF0", "#F8A5C8", "#2FB3C8"]


def api_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "top-langs-card",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_repos():
    repos, page = [], 1
    while True:
        batch = api_get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def collect_languages():
    totals = {}
    for repo in list_repos():
        if repo.get("fork") or repo["name"].lower() in EXCLUDE_REPOS:
            continue
        for lang, size in api_get(repo["languages_url"]).items():
            if lang.lower() in EXCLUDE_LANGS:
                continue
            totals[lang] = totals.get(lang, 0) + size
    return totals


def render_svg(totals):
    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    width = 495
    pad = 25
    bar_w = width - 2 * pad

    if not items:
        height = 110
        body = f'<text x="{pad}" y="75" fill="{MUTED}" font-size="14">No language data yet</text>'
    else:
        total = sum(size for _, size in items)
        segments, legend = [], []
        x = float(pad)
        for i, (lang, size) in enumerate(items):
            pct = size / total * 100
            w = bar_w * size / total
            color = PALETTE[i % len(PALETTE)]
            segments.append(f'<rect x="{x:.2f}" y="55" width="{w:.2f}" height="10" fill="{color}"/>')
            x += w
            col, row = i % 2, i // 2
            lx = pad + col * 230
            ly = 95 + row * 24
            legend.append(
                f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>'
                f'<text x="{lx + 18}" y="{ly}" fill="{TEXT}" font-size="13">{escape(lang)}</text>'
                f'<text x="{lx + 200}" y="{ly}" fill="{MUTED}" font-size="13" text-anchor="end">{pct:.1f}%</text>'
            )
        rows = (len(items) + 1) // 2
        height = 95 + (rows - 1) * 24 + 25
        body = (
            f'<clipPath id="bar"><rect x="{pad}" y="55" width="{bar_w}" height="10" rx="5"/></clipPath>'
            f'<g clip-path="url(#bar)">{"".join(segments)}</g>'
            + "".join(legend)
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Most used languages">'
        f'<style>text{{font-family:"Segoe UI",Ubuntu,"Helvetica Neue",Arial,sans-serif}}</style>'
        f'<rect width="{width}" height="{height}" rx="8" fill="{BG}"/>'
        f'<text x="{pad}" y="35" fill="{TITLE}" font-size="18" font-weight="600">Most Used Languages</text>'
        f'{body}</svg>\n'
    )


def main():
    totals = collect_languages()
    svg = render_svg(totals)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT} with {len(totals)} languages")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail loudly so the Action shows a red X
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
