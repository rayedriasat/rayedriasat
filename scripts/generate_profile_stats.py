#!/usr/bin/env python3
"""Render self-hosted GitHub stat cards (dark + light) as animated SVG.

Why this exists: the popular third-party widgets (github-readme-stats,
github-profile-trophy, github-readme-activity-graph) run on shared Vercel
deployments that are regularly paused, rate-limited or over quota, which
leaves broken images on the profile. This renders the same information from
the GitHub REST API into SVGs committed to the repo, so the profile has no
runtime dependency on anyone else's uptime.

Usage:
    GITHUB_TOKEN=... python scripts/generate_profile_stats.py
    python scripts/generate_profile_stats.py --from-file repos.json  # offline
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter

USER = "rayedriasat"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# GitHub linguist colours - readable on both light and dark backgrounds.
LANG_COLORS = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "JavaScript": "#F1E05A",
    "HTML": "#E34C26", "TypeScript": "#3178C6", "Dart": "#00B4AB", "PHP": "#4F5D95",
    "Java": "#B07219", "C": "#8A8A8A", "C++": "#F34B7D", "Lua": "#5C7FD0",
    "CSS": "#563D7C", "Shell": "#89E051", "TeX": "#3D6117", "Go": "#00ADD8",
    "Rust": "#DEA584", "Ruby": "#701516", "Kotlin": "#A97BFF", "Swift": "#F05138",
}
OTHER_COLOR = "#7C8FA3"

DARK = dict(
    key="dark", bg1="#050A16", bg2="#0A1626", bg3="#071C1A", border="#1E3A4A",
    grid="#22D3EE", grid_op=".06", title="#34D399", value="#E6EDF3",
    label="#6B8299", sub="#A8BACD", tile="#0B1B2B", tile_stroke="#16394A",
    track="#132A3A", accent="#34D399", accent2="#22D3EE",
)
LIGHT = dict(
    key="light", bg1="#FFFFFF", bg2="#F1F6FA", bg3="#ECFDF6", border="#D5DEE6",
    grid="#0F766E", grid_op=".07", title="#047857", value="#0B1B2B",
    label="#64798F", sub="#41566B", tile="#FFFFFF", tile_stroke="#DCE5EC",
    track="#E6EDF2", accent="#047857", accent2="#0369A1",
)

W, H = 1000, 290


def api(path, token):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-stats",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos(token):
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}", token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def summarise(repos):
    """Public, non-fork repositories only - that is what a visitor can actually see."""
    pub = [r for r in repos if not r.get("private") and not r.get("fork")]
    langs = Counter(r["language"] for r in pub if r.get("language"))
    return dict(
        repos=len(pub),
        stars=sum(r.get("stargazers_count", 0) for r in pub),
        forks=sum(r.get("forks_count", 0) for r in pub),
        langs=langs,
        lang_repos=sum(langs.values()),
        top_repo=max(pub, key=lambda r: r.get("stargazers_count", 0), default=None),
    )


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(p, s):
    mono = "ui-monospace,'SFMono-Regular','JetBrains Mono',Menlo,Consolas,monospace"
    sans = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif"
    o = []
    a = o.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'fill="none" role="img" aria-label="GitHub statistics for {USER}">')
    a('<defs>')
    a(f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{p["bg1"]}"/><stop offset=".6" stop-color="{p["bg2"]}"/>'
      f'<stop offset="1" stop-color="{p["bg3"]}"/></linearGradient>')
    a(f'<pattern id="grid" width="26" height="26" patternUnits="userSpaceOnUse">'
      f'<path d="M26 0H0V26" fill="none" stroke="{p["grid"]}" stroke-opacity="{p["grid_op"]}"/></pattern>')
    a(f'<linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{p["accent"]}"/><stop offset="1" stop-color="{p["accent2"]}"/></linearGradient>')
    a('<clipPath id="card"><rect x="1" y="1" width="998" height="288" rx="16"/></clipPath>')
    a(f'<clipPath id="barClip"><rect x="0" y="0" width="900" height="16" rx="8"/></clipPath>')
    a('</defs>')

    a('<g clip-path="url(#card)">')
    a(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    a(f'<rect width="{W}" height="{H}" fill="url(#grid)" opacity=".55"/>')

    # header
    a(f'<rect x="50" y="34" width="4" height="18" rx="2" fill="url(#hdr)"/>')
    a(f'<text x="66" y="49" font-family="{sans}" font-size="16" font-weight="700" '
      f'fill="{p["title"]}" letter-spacing=".3">GitHub at a glance</text>')
    a(f'<text x="950" y="49" text-anchor="end" font-family="{mono}" font-size="11" '
      f'fill="{p["label"]}">public repositories only</text>')

    # metric tiles
    top = s["top_repo"]
    tiles = [
        (str(s["repos"]), "public repos"),
        (str(s["stars"]), "stars earned"),
        (str(s["forks"]), "forks"),
        (str(len(s["langs"])), "languages shipped"),
    ]
    tw, gap, x0, ty = 212, 13, 50, 68
    for i, (val, lab) in enumerate(tiles):
        x = x0 + i * (tw + gap)
        a(f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur=".55s" '
          f'begin="{0.10 * i:.2f}s" fill="freeze"/>')
        a(f'<rect x="{x}" y="{ty}" width="{tw}" height="78" rx="12" fill="{p["tile"]}" '
          f'stroke="{p["tile_stroke"]}"/>')
        a(f'<rect x="{x}" y="{ty}" width="3" height="78" rx="1.5" fill="url(#hdr)" opacity=".8"/>')
        a(f'<text x="{x + 22}" y="{ty + 42}" font-family="{sans}" font-size="34" font-weight="800" '
          f'fill="{p["value"]}">{esc(val)}</text>')
        a(f'<text x="{x + 22}" y="{ty + 63}" font-family="{mono}" font-size="11.5" '
          f'fill="{p["label"]}" letter-spacing=".4">{esc(lab)}</text>')
        a('</g>')

    # language bar
    by = 182
    a(f'<text x="50" y="{by - 10}" font-family="{mono}" font-size="11.5" fill="{p["label"]}" '
      f'letter-spacing=".4">PRIMARY LANGUAGE ACROSS {s["lang_repos"]} PUBLIC REPOSITORIES</text>')
    a(f'<rect x="50" y="{by}" width="900" height="16" rx="8" fill="{p["track"]}"/>')

    ranked = s["langs"].most_common()
    shown, rest = ranked[:8], ranked[8:]
    segs = [(n, c, LANG_COLORS.get(n, OTHER_COLOR)) for n, c in shown]
    if rest:
        segs.append(("Other", sum(c for _, c in rest), OTHER_COLOR))

    total = sum(c for _, c, _c in segs) or 1
    a(f'<g transform="translate(50,{by})" clip-path="url(#barClip)">')
    off = 0.0
    for i, (name, cnt, col) in enumerate(segs):
        w = 900 * cnt / total
        a(f'<rect x="{off:.1f}" y="0" width="0" height="16" fill="{col}">'
          f'<animate attributeName="width" values="0;{w:.1f}" dur=".8s" '
          f'begin="{0.45 + 0.07 * i:.2f}s" fill="freeze" calcMode="spline" '
          f'keySplines=".25 .1 .25 1" keyTimes="0;1"/></rect>')
        off += w
    a('</g>')

    # legend
    ly = by + 42
    lx = 50
    for i, (name, cnt, col) in enumerate(segs):
        pct = 100.0 * cnt / total
        label = f"{name} {pct:.0f}%"
        a(f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur=".5s" '
          f'begin="{0.75 + 0.06 * i:.2f}s" fill="freeze"/>')
        a(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{col}"/>')
        a(f'<text x="{lx + 17}" y="{ly}" font-family="{mono}" font-size="12" '
          f'fill="{p["sub"]}">{esc(label)}</text>')
        a('</g>')
        lx += 22 + int(7.25 * len(label))

    # footer
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")
    note = f"most-starred: {top['name']} ({top.get('stargazers_count', 0)}★)" if top else ""
    a(f'<line x1="50" y1="{ly + 20}" x2="950" y2="{ly + 20}" stroke="{p["border"]}"/>')
    a(f'<text x="50" y="{ly + 42}" font-family="{mono}" font-size="11.5" fill="{p["label"]}">'
      f'{esc(note)}</text>')
    a(f'<text x="950" y="{ly + 42}" text-anchor="end" font-family="{mono}" font-size="11.5" '
      f'fill="{p["label"]}">self-hosted · refreshed {stamp}</text>')

    a('</g>')
    a(f'<rect x="1" y="1" width="998" height="288" rx="16" fill="none" stroke="{p["border"]}" '
      f'stroke-width="1.4"/>')
    a('</svg>')
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", help="JSON file with a repo list (offline rendering)")
    args = ap.parse_args()

    if args.from_file:
        raw = json.load(open(args.from_file))
        repos = raw["items"] if isinstance(raw, dict) and "items" in raw else raw
    else:
        repos = fetch_repos(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))

    s = summarise(repos)
    if not s["repos"]:
        sys.exit("no public repositories found - refusing to write empty cards")

    os.makedirs(OUT_DIR, exist_ok=True)
    for pal in (DARK, LIGHT):
        path = os.path.join(OUT_DIR, f"stats-{pal['key']}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build(pal, s))
        print("wrote", path)
    print(f"repos={s['repos']} stars={s['stars']} forks={s['forks']} langs={dict(s['langs'])}")


if __name__ == "__main__":
    main()
