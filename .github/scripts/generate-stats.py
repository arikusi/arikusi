#!/usr/bin/env python3
"""Generate GitHub stats SVG cards for profile README.

Uses the gh CLI to fetch data from GitHub's GraphQL API, then produces
three SVG files that match the gold-on-transparent theme:

  stats/github-stats.svg   - stars, commits, PRs, issues, contrib count
  stats/top-langs.svg      - language breakdown (compact bar chart)
  stats/github-streak.svg  - contribution streak with ring + fire animation
"""

import json
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

USERNAME = "arikusi"
COLOR = "#e4a700"
FONT = "\"Segoe UI\", Ubuntu, sans-serif"

# Octicons SVG paths (16x16 viewBox, MIT license)
ICONS = {
    "star": (
        "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 "
        ".416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347"
        "l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 "
        "0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"
    ),
    "commit": (
        "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32"
        "a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.5a2.5"
        " 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z"
    ),
    "pr": (
        "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 "
        "0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0"
        " 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 "
        "1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 "
        "3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 "
        "0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75"
        "a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"
    ),
    "issue": (
        "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 "
        "16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"
    ),
    "person": (
        "M10.561 8.073a6.005 6.005 0 0 1 3.432 5.142.75.75 0 1 1-1.498"
        ".07 4.5 4.5 0 0 0-8.99 0 .75.75 0 0 1-1.498-.07 6.004 6.004 0 "
        "0 1 3.431-5.142 3.999 3.999 0 1 1 5.123 0ZM10.5 5a2.5 2.5 0 1 "
        "0-5 0 2.5 2.5 0 0 0 5 0Z"
    ),
    "fire": (
        "M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 "
        "9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 "
        "C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 "
        "22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C "
        "-2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 "
        "12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 "
        "4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z"
    ),
}


def gh_graphql(query: str) -> dict:
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"GraphQL error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)["data"]["user"]


def fetch_data() -> dict:
    return gh_graphql(
        "{"
        f'  user(login: "{USERNAME}") {{'
        "    repositories(first: 100, ownerAffiliations: OWNER,"
        "      orderBy: {field: STARGAZERS, direction: DESC}) {"
        "      nodes {"
        "        stargazerCount"
        "        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {"
        "          edges { size node { name color } }"
        "        }"
        "      }"
        "    }"
        "    pullRequests { totalCount }"
        "    issues { totalCount }"
        "    repositoriesContributedTo("
        "      contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]"
        "    ) { totalCount }"
        "    contributionsCollection {"
        "      totalCommitContributions"
        "      restrictedContributionsCount"
        "      contributionCalendar {"
        "        totalContributions"
        "        weeks {"
        "          contributionDays { contributionCount date }"
        "        }"
        "      }"
        "    }"
        "  }"
        "}"
    )


def make_stats_svg(data: dict) -> str:
    repos = data["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)
    cc = data["contributionsCollection"]
    total_commits = (
        cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    )
    total_prs = data["pullRequests"]["totalCount"]
    total_issues = data["issues"]["totalCount"]
    contributed_to = data["repositoriesContributedTo"]["totalCount"]

    year = datetime.now().year
    rows = [
        ("star", "Total Stars Earned", total_stars),
        ("commit", f"Total Commits ({year})", total_commits),
        ("pr", "Total PRs", total_prs),
        ("issue", "Total Issues", total_issues),
        ("person", "Contributed to (last year)", contributed_to),
    ]

    row_svg = ""
    for i, (icon_key, label, value) in enumerate(rows):
        y = 60 + i * 25
        row_svg += (
            f'    <g transform="translate(25, {y})">\n'
            f'      <path d="{ICONS[icon_key]}" fill="{COLOR}" '
            f'fill-opacity="0.9" fill-rule="evenodd" '
            f'transform="translate(0, -2) scale(0.875)"/>\n'
            f'      <text x="24" y="11" font-size="12px" '
            f'fill="{COLOR}">{label}:</text>\n'
            f'      <text x="340" y="11" font-size="12px" '
            f'font-weight="700" fill="{COLOR}" '
            f'text-anchor="end">{value:,}</text>\n'
            f"    </g>\n"
        )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195"'
        ' viewBox="0 0 495 195" fill="none">\n'
        "  <style>\n"
        f"    text {{ font-family: {FONT}; }}\n"
        "  </style>\n"
        f'  <text x="25" y="35" font-size="18px" font-weight="600"'
        f' fill="{COLOR}">{USERNAME}\'s GitHub Stats</text>\n'
        f"{row_svg}"
        "</svg>\n"
    )


def make_langs_svg(data: dict) -> str:
    lang_map: dict = defaultdict(lambda: {"size": 0, "color": "#ccc"})
    for repo in data["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_map[name]["size"] += edge["size"]
            if edge["node"]["color"]:
                lang_map[name]["color"] = edge["node"]["color"]

    if not lang_map:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg"'
            ' width="495" height="170" viewBox="0 0 495 170"/>\n'
        )

    sorted_langs = sorted(
        lang_map.items(), key=lambda x: x[1]["size"], reverse=True
    )[:8]
    total_bytes = sum(v["size"] for _, v in sorted_langs)

    langs = []
    for name, info in sorted_langs:
        pct = info["size"] / total_bytes * 100 if total_bytes else 0
        langs.append({"name": name, "color": info["color"], "pct": pct})

    # progress bar
    bar_x, bar_y, bar_w, bar_h = 25, 55, 445, 8

    bar_rects = ""
    x = float(bar_x)
    for lang in langs:
        w = max(bar_w * lang["pct"] / 100, 1)
        bar_rects += (
            f'      <rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}"'
            f' height="{bar_h}" fill="{lang["color"]}"/>\n'
        )
        x += w

    # legend
    legend_svg = ""
    per_row = 4
    for i, lang in enumerate(langs):
        col = i % per_row
        row = i // per_row
        lx = 25 + col * 112
        ly = 80 + row * 24
        legend_svg += (
            f'    <g transform="translate({lx}, {ly})">\n'
            f'      <circle cx="5" cy="6" r="5" fill="{lang["color"]}"/>\n'
            f'      <text x="15" y="10" font-size="11px"'
            f' fill="{COLOR}">{lang["name"]} {lang["pct"]:.1f}%</text>\n'
            f"    </g>\n"
        )

    num_rows = (len(langs) - 1) // per_row + 1
    height = 80 + num_rows * 24 + 15

    return (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="495" height="{height}" viewBox="0 0 495 {height}"'
        ' fill="none">\n'
        "  <style>\n"
        f"    text {{ font-family: {FONT}; }}\n"
        "  </style>\n"
        f'  <text x="25" y="35" font-size="18px" font-weight="600"'
        f' fill="{COLOR}">Most Used Languages</text>\n'
        "  <defs>\n"
        '    <clipPath id="bar-clip">\n'
        f'      <rect x="{bar_x}" y="{bar_y}" width="{bar_w}"'
        f' height="{bar_h}" rx="4"/>\n'
        "    </clipPath>\n"
        "  </defs>\n"
        '  <g clip-path="url(#bar-clip)">\n'
        f"{bar_rects}"
        "  </g>\n"
        f"{legend_svg}"
        "</svg>\n"
    )


def make_streak_svg(data: dict) -> str:
    cal = data["contributionsCollection"]["contributionCalendar"]
    total = cal["totalContributions"]

    days = []
    for week in cal["weeks"]:
        for d in week["contributionDays"]:
            days.append((date.fromisoformat(d["date"]), d["contributionCount"]))
    days.sort()

    today = date.today()
    first_day = days[0][0] if days else today

    # current streak — walk backwards, allow today to have 0 (day not over)
    current = 0
    current_start = today
    for dt, count in reversed(days):
        if dt > today:
            continue
        if dt == today and count == 0:
            continue
        if count > 0:
            current += 1
            current_start = dt
        else:
            break

    # longest streak
    longest = 0
    longest_start = first_day
    longest_end = first_day
    run = 0
    run_start = first_day
    for dt, count in days:
        if count > 0:
            if run == 0:
                run_start = dt
            run += 1
            if run > longest:
                longest = run
                longest_start = run_start
                longest_end = dt
        else:
            run = 0

    def fmt_range(start: date, end: date) -> str:
        return f"{start.strftime('%b %d')} - {end.strftime('%b %d')}"

    total_range = f"{first_day.strftime('%b %d, %Y')} - Present"
    current_range = fmt_range(current_start, today) if current > 0 else ""
    longest_range = (
        fmt_range(longest_start, longest_end) if longest > 0 else ""
    )

    fire = ICONS["fire"]

    return (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"\n'
        '     style="isolation: isolate" viewBox="0 0 495 195"'
        ' width="495px" height="195px" direction="ltr">\n'
        "  <style>\n"
        f"    text {{ font-family: {FONT}; }}\n"
        "    @keyframes currstreak {\n"
        "      0% { font-size: 3px; opacity: 0.2; }\n"
        "      80% { font-size: 34px; opacity: 1; }\n"
        "      100% { font-size: 28px; opacity: 1; }\n"
        "    }\n"
        "    @keyframes fadein {\n"
        "      0% { opacity: 0; }\n"
        "      100% { opacity: 1; }\n"
        "    }\n"
        "  </style>\n"
        "  <defs>\n"
        '    <clipPath id="outer_rectangle">\n'
        '      <rect width="495" height="195" rx="4.5"/>\n'
        "    </clipPath>\n"
        '    <mask id="mask_out_ring_behind_fire">\n'
        '      <rect width="495" height="195" fill="white"/>\n'
        '      <ellipse cx="247.5" cy="32" rx="13" ry="18" fill="black"/>\n'
        "    </mask>\n"
        "  </defs>\n"
        '  <g clip-path="url(#outer_rectangle)">\n'
        "    <!-- background -->\n"
        '    <rect fill="#000000" fill-opacity="0" rx="4.5"'
        ' x="0.5" y="0.5" width="494" height="194"/>\n'
        "\n"
        "    <!-- column dividers -->\n"
        f'    <line x1="165" y1="28" x2="165" y2="170"'
        f' stroke="{COLOR}" stroke-opacity="0.25" stroke-width="1"/>\n'
        f'    <line x1="330" y1="28" x2="330" y2="170"'
        f' stroke="{COLOR}" stroke-opacity="0.25" stroke-width="1"/>\n'
        "\n"
        "    <!-- total contributions -->\n"
        '    <g transform="translate(82.5, 48)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        font-weight="700" font-size="28px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        f' forwards 0.6s">{total:,}</text>\n'
        "    </g>\n"
        '    <g transform="translate(82.5, 84)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        font-weight="400" font-size="14px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        ' forwards 0.7s">Total Contributions</text>\n'
        "    </g>\n"
        '    <g transform="translate(82.5, 114)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        fill-opacity="0.4" font-size="12px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        f' forwards 0.8s">{total_range}</text>\n'
        "    </g>\n"
        "\n"
        "    <!-- current streak -->\n"
        '    <g mask="url(#mask_out_ring_behind_fire)">\n'
        f'      <circle cx="247.5" cy="71" r="40" fill="none"'
        f' stroke="{COLOR}" stroke-width="5"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        ' forwards 0.4s"/>\n'
        "    </g>\n"
        '    <g transform="translate(247.5, 19.5)" stroke-opacity="0"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        ' forwards 0.6s">\n'
        f'      <path d="{fire}" fill="{COLOR}"/>\n'
        "    </g>\n"
        '    <g transform="translate(247.5, 48)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        font-weight="700" font-size="28px"\n'
        '        style="animation: currstreak 0.6s linear'
        f' forwards">{current}</text>\n'
        "    </g>\n"
        '    <g transform="translate(247.5, 108)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        font-weight="700" font-size="14px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        ' forwards 0.9s">Current Streak</text>\n'
        "    </g>\n"
        '    <g transform="translate(247.5, 145)">\n'
        f'      <text x="0" y="21" text-anchor="middle" fill="{COLOR}"'
        '        fill-opacity="0.4" font-size="12px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        f' forwards 0.9s">{current_range}</text>\n'
        "    </g>\n"
        "\n"
        "    <!-- longest streak -->\n"
        '    <g transform="translate(412.5, 48)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        font-weight="700" font-size="28px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        f' forwards 1.2s">{longest}</text>\n'
        "    </g>\n"
        '    <g transform="translate(412.5, 84)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        font-weight="400" font-size="14px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        ' forwards 1.3s">Longest Streak</text>\n'
        "    </g>\n"
        '    <g transform="translate(412.5, 114)">\n'
        f'      <text x="0" y="32" text-anchor="middle" fill="{COLOR}"'
        '        fill-opacity="0.4" font-size="12px"\n'
        '        style="opacity: 0; animation: fadein 0.5s linear'
        f' forwards 1.4s">{longest_range}</text>\n'
        "    </g>\n"
        "  </g>\n"
        "</svg>\n"
    )


def main():
    print(f"Fetching GitHub data for {USERNAME}...")
    data = fetch_data()

    out = Path("stats")
    out.mkdir(exist_ok=True)

    print("Generating stats card...")
    (out / "github-stats.svg").write_text(make_stats_svg(data))

    print("Generating languages card...")
    (out / "top-langs.svg").write_text(make_langs_svg(data))

    print("Generating streak card...")
    (out / "github-streak.svg").write_text(make_streak_svg(data))

    print("Done.")


if __name__ == "__main__":
    main()
