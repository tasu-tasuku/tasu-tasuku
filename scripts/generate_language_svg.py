#!/usr/bin/env python3
"""
Generate language percentage pie-chart SVGs from all GitHub repositories via the GitHub API.
Falls back to scanning the local repository if GH_TOKEN is not set.
Writes: languages_programming.svg and languages_markup.svg at the repo root.

Note / 表記:
This script was created or updated with the assistance of an AI model.
このスクリプトは AI の支援により作成または更新されました。
"""
import html
import math
import os
from collections import defaultdict

try:
    import requests as _requests
except ImportError:
    _requests = None

GH_TOKEN = os.environ.get('GH_TOKEN')
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTPUT_PROG = os.path.join(REPO_ROOT, 'languages_programming.svg')
OUTPUT_MARK = os.path.join(REPO_ROOT, 'languages_markup.svg')

MARKUP_KEYS = {'Markdown', 'HTML', 'CSS', 'SVG', 'XML'}

# Colorblind-friendly palette (Okabe-Ito based)
PALETTE = [
    '#0072b2', '#e69f00', '#009e73', '#cc79a7',
    '#56b4e9', '#d55e00', '#f0e442', '#999999',
    '#332288', '#88ccee',
]

# Hatch patterns overlaid on slices for colorblind / print accessibility
_PATTERN_OVERLAYS = [
    '',                                                                  # 0: solid
    '<line x1="0" y1="8" x2="8" y2="0" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 1: diagonal /
    '<line x1="0" y1="4" x2="8" y2="4" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 2: horizontal
    '<line x1="4" y1="0" x2="4" y2="8" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 3: vertical
    '<line x1="0" y1="8" x2="8" y2="0" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>'
    '<line x1="0" y1="0" x2="8" y2="8" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 4: cross-diagonal
    '<circle cx="4" cy="4" r="1.5" fill="rgba(0,0,0,0.28)"/>',          # 5: dots
    '<line x1="0" y1="0" x2="8" y2="8" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 6: diagonal \
    '<line x1="0" y1="2" x2="8" y2="2" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>'
    '<line x1="0" y1="6" x2="8" y2="6" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 7: double horizontal
    '<line x1="2" y1="0" x2="2" y2="8" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>'
    '<line x1="6" y1="0" x2="6" y2="8" stroke="rgba(0,0,0,0.22)" stroke-width="1.5"/>',  # 8: double vertical
    '<rect x="2" y="2" width="4" height="4" fill="none" stroke="rgba(0,0,0,0.22)" stroke-width="1"/>',  # 9: squares
]


def _color(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


def _make_defs(n: int) -> str:
    """Return SVG <defs> with n fill patterns (color + hatch overlay)."""
    lines = ['<defs>']
    for i in range(n):
        pid = f'p{i}'
        overlay = _PATTERN_OVERLAYS[i % len(_PATTERN_OVERLAYS)]
        lines.append(
            f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="8" height="8">'
            f'<rect width="8" height="8" fill="{_color(i)}"/>'
            f'{overlay}'
            f'</pattern>'
        )
    lines.append('</defs>')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

def _gh_headers() -> dict:
    return {
        'Authorization': f'Bearer {GH_TOKEN}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }


def fetch_all_repo_languages() -> dict:
    """Aggregate language bytes across all repos owned by the authenticated user."""
    req = _requests
    headers = _gh_headers()

    r = req.get('https://api.github.com/user', headers=headers, timeout=30)
    r.raise_for_status()
    username = r.json()['login']
    print(f'Authenticated as: {username}')

    repos, page = [], 1
    while True:
        r = req.get(
            f'https://api.github.com/users/{username}/repos',
            headers=headers,
            params={'per_page': 100, 'page': page, 'type': 'owner'},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    print(f'Found {len(repos)} repositories')

    totals: dict = defaultdict(int)
    for repo in repos:
        full_name = repo['full_name']
        r = req.get(
            f'https://api.github.com/repos/{full_name}/languages',
            headers=headers,
            timeout=30,
        )
        if r.status_code == 200:
            for lang, byte_count in r.json().items():
                totals[lang] += byte_count
    return dict(totals)


# ---------------------------------------------------------------------------
# Local fallback
# ---------------------------------------------------------------------------

EXT_LANG = {
    '.py': 'Python', '.pyw': 'Python', '.ipynb': 'Jupyter Notebook',
    '.go': 'Go',
    '.js': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript', '.jsx': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript',
    '.java': 'Java', '.kt': 'Kotlin', '.kts': 'Kotlin',
    '.swift': 'Swift', '.scala': 'Scala',
    '.rb': 'Ruby', '.rs': 'Rust',
    '.cpp': 'C++', '.cc': 'C++', '.cxx': 'C++', '.c': 'C', '.h': 'C/C++ Header', '.hpp': 'C++ Header',
    '.cs': 'C#', '.php': 'PHP',
    '.dart': 'Dart', '.lua': 'Lua', '.r': 'R', '.jl': 'Julia',
    '.hs': 'Haskell', '.elm': 'Elm',
    '.ex': 'Elixir', '.exs': 'Elixir', '.erl': 'Erlang', '.hrl': 'Erlang',
    '.fs': 'F#', '.fsx': 'F#',
    '.f': 'Fortran', '.f90': 'Fortran', '.f95': 'Fortran',
    '.adb': 'Ada', '.ads': 'Ada',
    '.pas': 'Pascal',
    '.vb': 'Visual Basic', '.groovy': 'Groovy', '.coffee': 'CoffeeScript',
    '.sol': 'Solidity',
    '.vhd': 'VHDL', '.vhdl': 'VHDL', '.v': 'Verilog', '.sv': 'SystemVerilog',
    '.s': 'Assembly', '.asm': 'Assembly',
    '.lisp': 'Lisp', '.cl': 'Common Lisp', '.scm': 'Scheme', '.ss': 'Scheme',
    '.ml': 'OCaml', '.mli': 'OCaml',
    '.pl': 'Perl',
    '.pro': 'Prolog',
    '.sql': 'SQL',
    '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell',
    '.ps1': 'PowerShell', '.psm1': 'PowerShell',
    '.html': 'HTML', '.htm': 'HTML', '.css': 'CSS',
    '.md': 'Markdown', '.markdown': 'Markdown',
    '.xml': 'XML', '.json': 'JSON', '.yml': 'YAML', '.yaml': 'YAML',
    '.ini': 'INI', '.cfg': 'Config', '.toml': 'TOML',
    '.txt': 'Text', '.svg': 'SVG',
    '.tex': 'LaTeX', '.sty': 'LaTeX', '.cls': 'LaTeX', '.bib': 'BibTeX',
}

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.github'}


def scan_bytes(root: str) -> dict:
    counts: dict = defaultdict(int)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            try:
                full = os.path.join(dirpath, fn)
                size = os.path.getsize(full)
            except OSError:
                continue
            ext = os.path.splitext(fn)[1].lower()
            lang = EXT_LANG.get(ext)
            if lang is None and size > 0 and ext == '':
                try:
                    with open(full, 'rb') as f:
                        start = f.read(128)
                    if b'python' in start:
                        lang = 'Python'
                    elif b'node' in start or b'js' in start:
                        lang = 'JavaScript'
                except Exception:
                    pass
            counts[lang or 'Other'] += size
    return dict(counts)


# ---------------------------------------------------------------------------
# SVG pie chart
# ---------------------------------------------------------------------------

def _top_items(counter: dict, n: int = 8):
    items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    top, others = [], 0
    for i, (lang, size) in enumerate(items):
        if i < n and lang != 'Other':
            top.append((lang, size))
        else:
            others += size
    if others:
        top.append(('Other', others))
    return top


def make_pie_svg(counter: dict, title: str, outpath: str) -> None:
    """Write an accessible pie-chart SVG to *outpath*."""
    total = sum(counter.values())
    svg_id = os.path.splitext(os.path.basename(outpath))[0]
    title_id = f'{svg_id}-title'
    desc_id = f'{svg_id}-desc'

    if total == 0:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="60" '
            f'role="img" aria-labelledby="{title_id} {desc_id}">\n'
            f'<title id="{title_id}">{html.escape(title)}</title>\n'
            f'<desc id="{desc_id}">No data found</desc>\n'
            f'<text x="10" y="30" font-family="sans-serif" font-size="14">No data found</text>\n'
            f'</svg>\n'
        )
        with open(outpath, 'w') as f:
            f.write(svg)
        return

    top = _top_items(counter)
    n = len(top)

    # Layout
    width = 520
    cx, cy, r = 160, 160, 130   # pie center and radius
    legend_x = 310
    legend_y_start = 30
    legend_item_h = 26
    height = max(340, legend_y_start + n * legend_item_h + 40)

    # Accessible description (machine-readable summary for screen readers)
    desc_text = f'{title}. ' + ', '.join(
        f'{lang}: {size / total * 100:.1f}%' for lang, size in top
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'role="img" aria-labelledby="{title_id} {desc_id}">',
        f'<title id="{title_id}">{html.escape(title)}</title>',
        f'<desc id="{desc_id}">{html.escape(desc_text)}</desc>',
        _make_defs(n),
        '<style>text { font-family: sans-serif; }</style>',
        # Chart title
        f'<text x="{width // 2}" y="22" font-size="15" font-weight="bold" '
        f'text-anchor="middle">{html.escape(title)}</text>',
    ]

    # Pie slices
    angle = -math.pi / 2  # start at 12 o'clock
    for i, (lang, size) in enumerate(top):
        frac = size / total
        sweep = frac * 2 * math.pi
        end_angle = angle + sweep
        large = 1 if sweep > math.pi else 0

        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(end_angle)
        y2 = cy + r * math.sin(end_angle)

        d = f'M {cx} {cy} L {x1:.3f} {y1:.3f} A {r} {r} 0 {large} 1 {x2:.3f} {y2:.3f} Z'
        pct_label = f'{frac * 100:.1f}%'
        aria = html.escape(f'{lang}: {pct_label}')

        parts.append(
            f'<path d="{d}" fill="url(#p{i})" stroke="white" stroke-width="1.5" '
            f'role="img" aria-label="{aria}">'
            f'<title>{aria}</title>'
            f'</path>'
        )

        # Percentage label inside slice (hidden from AT; legend carries the info)
        if frac > 0.06:
            mid = angle + sweep / 2
            lx = cx + r * 0.62 * math.cos(mid)
            ly = cy + r * 0.62 * math.sin(mid)
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" fill="#fff" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'aria-hidden="true">{html.escape(pct_label)}</text>'
            )

        angle = end_angle

    # Legend
    for i, (lang, size) in enumerate(top):
        frac = size / total
        ly = legend_y_start + i * legend_item_h
        pct_label = f'{frac * 100:.1f}%'
        parts.append(
            f'<rect x="{legend_x}" y="{ly}" width="14" height="14" '
            f'fill="url(#p{i})" rx="2" stroke="{_color(i)}" stroke-width="1" '
            f'aria-hidden="true"/>'
        )
        parts.append(
            f'<text x="{legend_x + 22}" y="{ly + 11}" font-size="13" aria-hidden="true">'
            f'{html.escape(lang)}\u2009{html.escape(pct_label)}</text>'
        )

    parts.append('</svg>')
    with open(outpath, 'w') as f:
        f.write('\n'.join(parts))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if GH_TOKEN and _requests is not None:
        print('Fetching language stats from GitHub API …')
        counts = fetch_all_repo_languages()
        print(f'Aggregated {len(counts)} language(s) across all repositories')
    else:
        print('GH_TOKEN not set or `requests` unavailable — scanning local repo …')
        counts = scan_bytes(REPO_ROOT)

    markup = {k: v for k, v in counts.items() if k in MARKUP_KEYS}
    programming = {k: v for k, v in counts.items() if k not in MARKUP_KEYS}

    make_pie_svg(programming, 'Language distribution (programming & scripts)', OUTPUT_PROG)
    make_pie_svg(markup, 'Markup & docs distribution', OUTPUT_MARK)
    print('Wrote', OUTPUT_PROG, OUTPUT_MARK)
