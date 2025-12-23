#!/usr/bin/env python3
"""
Grateful Dead Setlist Book Generator

Generates beautifully formatted HTML/PDF books from setlist data.
Features intelligent pagination that avoids orphaned content and
creates intentional two-page spreads for longer shows.

Usage:
    python generate.py --help
    python generate.py --preview          # Generate HTML for preview
    python generate.py --pdf              # Generate PDF
    python generate.py --year 1972        # Single year
    python generate.py --era 70s          # Era (60s, 70s, 80s, 90s)
    python generate.py --all              # All volumes
"""

import argparse
import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


# Page geometry constants (in points, 1pt = 1/72 inch)
# Page: 6in × 9in = 432pt × 648pt
# Margins: 0.75in top, 0.625in sides, 0.875in bottom
PAGE_CONTENT_HEIGHT = 500  # Conservative usable height in points
PAGE_CONTENT_WIDTH = 342   # 4.75in in points

# Typography measurements (approximate, based on 11pt base)
HEADER_HEIGHT = 65         # Date + venue + location
NOTES_BASE_HEIGHT = 25     # Base height for notes
NOTES_CHARS_PER_LINE = 55  # Approximate characters per line
LINE_HEIGHT = 18           # Song line height (11pt × 1.6)
SET_LABEL_HEIGHT = 22      # Set label + margin
SET_GAP = 12               # Gap between sets


class LayoutType(Enum):
    SINGLE = "single"           # Fits on one page normally
    COMPACT = "compact"         # Fits with tighter spacing
    SPREAD = "spread"           # Needs two-page spread


@dataclass
class Set:
    label: str = ""
    annotation: Optional[str] = None
    songs: list = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.songs)

    def estimate_height(self) -> float:
        """Estimate height in points"""
        height = SET_LABEL_HEIGHT
        height += len(self.songs) * LINE_HEIGHT
        return height


@dataclass
class Show:
    date: str = ""
    venue1: str = ""
    venue2: Optional[str] = None
    city: str = ""
    state_or_country: str = ""
    notes: Optional[str] = None
    sets: list = field(default_factory=list)

    @property
    def year(self) -> int:
        return int(self.date.split("/")[0])

    @property
    def formatted_date(self) -> str:
        """Convert YYYY/MM/DD to a readable format"""
        try:
            parts = self.date.split("/")
            if len(parts) == 3:
                dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                return dt.strftime("%B %d, %Y")
        except (ValueError, IndexError):
            pass
        return self.date

    @property
    def venue_display(self) -> str:
        if self.venue2:
            return f"{self.venue1} {self.venue2}"
        return self.venue1

    @property
    def location_display(self) -> str:
        return f"{self.city}, {self.state_or_country}"

    def __len__(self) -> int:
        return sum(len(s) for s in self.sets)

    def estimate_header_height(self) -> float:
        """Estimate header height including notes"""
        height = HEADER_HEIGHT
        if self.notes:
            # Estimate wrapped lines for notes
            note_lines = max(1, len(self.notes) // NOTES_CHARS_PER_LINE + 1)
            height += NOTES_BASE_HEIGHT + (note_lines - 1) * LINE_HEIGHT
        return height

    def estimate_total_height(self) -> float:
        """Estimate total height in points"""
        height = self.estimate_header_height()
        for i, s in enumerate(self.sets):
            height += s.estimate_height()
            if i < len(self.sets) - 1:
                height += SET_GAP
        return height

    def classify_layout(self) -> LayoutType:
        """Determine the best layout strategy for this show"""
        total_height = self.estimate_total_height()

        # Comfortable single page
        if total_height <= PAGE_CONTENT_HEIGHT * 0.92:
            return LayoutType.SINGLE

        # Can fit with compact styling (reduce line-height, gaps)
        # Compact mode saves roughly 15% vertical space
        if total_height <= PAGE_CONTENT_HEIGHT * 1.08:
            return LayoutType.COMPACT

        # Needs a two-page spread
        return LayoutType.SPREAD

    def find_split_point(self) -> int:
        """
        Find the optimal index to split sets for a two-page spread.
        Returns the index of the first set that should go on page 2.

        Strategy: Put header + first set(s) on verso (left page),
        remaining sets on recto (right page).
        """
        if len(self.sets) <= 1:
            return 1  # Can't split a single set

        header_height = self.estimate_header_height()
        page_budget = PAGE_CONTENT_HEIGHT

        # Try to fit header + first N sets on page 1
        cumulative_height = header_height
        split_after = 0

        for i, s in enumerate(self.sets):
            set_height = s.estimate_height()
            if i > 0:
                set_height += SET_GAP

            if cumulative_height + set_height <= page_budget * 0.95:
                cumulative_height += set_height
                split_after = i + 1
            else:
                break

        # Ensure we split somewhere reasonable
        if split_after == 0:
            split_after = 1  # At minimum, first set on page 1
        if split_after >= len(self.sets):
            split_after = len(self.sets) - 1  # Keep at least one set for page 2

        return split_after


def parse_shows(data_path: Path) -> list[Show]:
    """Parse the TSV file into Show objects"""
    with open(data_path) as f:
        reader = csv.reader(f, delimiter="\t", quotechar='"')
        rows = list(reader)

    shows = []
    current_show = None

    for row in rows:
        if len(row) == 0:
            continue

        if len(row) < 3 and current_show is not None:
            possible_set_label, song = row[0], row[1] if len(row) > 1 else ""

            if possible_set_label != '' or len(current_show.sets) == 0:
                s = Set()
                s.label = possible_set_label if possible_set_label else 'I'

                if song.startswith('(electric)') or song.startswith('(acoustic)'):
                    paren_idx = song.index(')')
                    s.annotation = song[1:paren_idx]
                    song = song[paren_idx + 2:]

                s.songs = [song] if song else []
                current_show.sets.append(s)
            else:
                if song:
                    current_show.sets[-1].songs.append(song)

            continue
        elif len(row) < 3:
            continue

        # New show
        if current_show is not None and len(current_show) > 0:
            shows.append(current_show)

        date_or_set, _band, venue1, venue2, city, state_or_country, *rest = row + [''] * 7
        notes = rest[0] if rest else None

        current_show = Show(
            date=date_or_set,
            venue1=venue1,
            venue2=venue2 if venue2 else None,
            city=city,
            state_or_country=state_or_country,
            notes=notes if notes else None,
            sets=[]
        )

    if current_show is not None and len(current_show) > 0:
        shows.append(current_show)

    return shows


def format_song(song: str) -> tuple[str, bool, Optional[str]]:
    """
    Parse a song entry, returning (song_name, is_segue, note)
    Songs starting with '>' indicate segue from previous
    Songs with '*' or other annotations at the end have notes
    """
    is_segue = song.startswith(">")
    if is_segue:
        song = song[1:].strip()

    # Extract trailing notes (like * or parenthetical remarks)
    note = None
    if song.endswith("*"):
        song = song[:-1]
        note = "*"
    elif "*" in song:
        match = re.match(r'^(.+?)(\*.*?)$', song)
        if match:
            song = match.group(1)
            note = match.group(2)

    return song.strip(), is_segue, note


def render_set_html(s: Set) -> str:
    """Render a single set as HTML"""
    lines = []
    lines.append('    <section class="set">')

    label_html = f'<h3 class="set-label">Set {s.label}'
    if s.annotation:
        label_html += f' <span class="set-annotation">({s.annotation})</span>'
    label_html += '</h3>'
    lines.append(f'      {label_html}')

    lines.append('      <ul class="songs">')
    for song in s.songs:
        song_name, is_segue, note = format_song(song)
        class_attr = ' class="segue"' if is_segue else ''
        if note:
            lines.append(f'        <li{class_attr}>{song_name} <span class="song-note">{note}</span></li>')
        else:
            lines.append(f'        <li{class_attr}>{song_name}</li>')
    lines.append('      </ul>')
    lines.append('    </section>')

    return '\n'.join(lines)


def render_show_header_html(show: Show) -> str:
    """Render just the show header (date, venue, notes)"""
    lines = []
    lines.append('  <header class="show-header">')
    lines.append(f'    <h2 class="show-date">{show.formatted_date}</h2>')
    lines.append(f'    <p class="show-venue">{show.venue_display}</p>')
    lines.append(f'    <p class="show-location">{show.location_display}</p>')

    if show.notes:
        notes = show.notes.strip()
        if notes.startswith('(') and notes.endswith(')'):
            notes = notes[1:-1]
        lines.append(f'    <p class="show-notes">{notes}</p>')

    lines.append('  </header>')
    return '\n'.join(lines)


def render_show_single(show: Show, layout_type: LayoutType) -> str:
    """Render a show that fits on a single page"""
    css_class = "show"
    if layout_type == LayoutType.COMPACT:
        css_class += " show-compact"

    lines = [f'<article class="{css_class}">']
    lines.append(render_show_header_html(show))
    lines.append('  <div class="sets">')
    for s in show.sets:
        lines.append(render_set_html(s))
    lines.append('  </div>')
    lines.append('</article>')

    return '\n'.join(lines)


def render_show_spread(show: Show) -> str:
    """
    Render a show as a two-page spread.

    Structure:
    - Page 1 (verso/left): Header + first set(s)
    - Page 2 (recto/right): Remaining sets

    Uses CSS to force page 1 to start on a left page.
    """
    split_point = show.find_split_point()
    sets_page1 = show.sets[:split_point]
    sets_page2 = show.sets[split_point:]

    lines = []

    # Page 1: Verso (left page) - starts on left via CSS
    lines.append('<article class="show show-spread show-spread-verso">')
    lines.append(render_show_header_html(show))
    lines.append('  <div class="sets">')
    for s in sets_page1:
        lines.append(render_set_html(s))
    lines.append('  </div>')
    lines.append('</article>')

    # Page 2: Recto (right page)
    lines.append('<article class="show show-spread show-spread-recto">')
    # Condensed header for continuity
    lines.append('  <header class="show-header show-header-continued">')
    lines.append(f'    <p class="show-date-continued">{show.formatted_date} <span class="continued-label">(continued)</span></p>')
    lines.append('  </header>')
    lines.append('  <div class="sets">')
    for s in sets_page2:
        lines.append(render_set_html(s))
    lines.append('  </div>')
    lines.append('</article>')

    return '\n'.join(lines)


def render_show_html(show: Show) -> str:
    """Render a show with appropriate layout based on its size"""
    layout_type = show.classify_layout()

    if layout_type == LayoutType.SPREAD:
        return render_show_spread(show)
    else:
        return render_show_single(show, layout_type)


def render_year_divider(year: int, show_count: int) -> str:
    """Render a year divider page"""
    return f'''
<div class="year-divider">
  <h1 class="year">{year}</h1>
  <p class="show-count">{show_count} shows</p>
</div>
'''


def render_volume_title(title: str, subtitle: str, year_range: str, show_count: int) -> str:
    """Render a volume title page"""
    return f'''
<div class="volume-title-page">
  <h1>{title}</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="year-range">{year_range}</p>
  <hr class="decorative-rule">
  <p class="show-count">{show_count} shows</p>
</div>
'''


def render_html_document(content: str, title: str = "Grateful Dead Setlists",
                         layout: str = "compact") -> str:
    """Wrap content in a full HTML document"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=Playfair+Display:wght@400;700&family=Source+Sans+Pro:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="templates/style.css">
</head>
<body class="layout-{layout}">
{content}
</body>
</html>
'''


def get_era_years(era: str) -> tuple[int, int]:
    """Return start and end years for an era"""
    eras = {
        '60s': (1966, 1969),
        '70s': (1970, 1979),
        '80s': (1980, 1989),
        '90s': (1990, 1995),
    }
    return eras.get(era, (1966, 1995))


def generate_book(shows: list[Show], output_path: Path,
                  year: Optional[int] = None,
                  era: Optional[str] = None,
                  layout: str = "compact",
                  include_year_dividers: bool = True,
                  debug_layout: bool = False) -> None:
    """Generate an HTML book from shows"""

    # Filter shows
    if year:
        shows = [s for s in shows if s.year == year]
        title = f"Grateful Dead {year}"
        year_range = str(year)
    elif era:
        start, end = get_era_years(era)
        shows = [s for s in shows if start <= s.year <= end]
        title = f"Grateful Dead: The {era.upper()}"
        year_range = f"{start}–{end}"
    else:
        title = "Grateful Dead: Complete Setlists"
        years = sorted(set(s.year for s in shows))
        year_range = f"{min(years)}–{max(years)}" if years else ""

    if not shows:
        print("No shows found for the specified filter")
        return

    # Layout statistics
    layout_counts = {LayoutType.SINGLE: 0, LayoutType.COMPACT: 0, LayoutType.SPREAD: 0}
    for show in shows:
        layout_counts[show.classify_layout()] += 1

    if debug_layout:
        print(f"\nLayout breakdown:")
        print(f"  Single page: {layout_counts[LayoutType.SINGLE]}")
        print(f"  Compact:     {layout_counts[LayoutType.COMPACT]}")
        print(f"  Spread:      {layout_counts[LayoutType.SPREAD]}")

    # Group by year
    shows_by_year = {}
    for show in shows:
        if show.year not in shows_by_year:
            shows_by_year[show.year] = []
        shows_by_year[show.year].append(show)

    # Build content
    content_parts = []

    # Volume title page
    content_parts.append(render_volume_title(
        "Grateful Dead",
        "Complete Setlists",
        year_range,
        len(shows)
    ))

    # Render shows grouped by year
    for yr in sorted(shows_by_year.keys()):
        year_shows = shows_by_year[yr]

        if include_year_dividers and len(shows_by_year) > 1:
            content_parts.append(render_year_divider(yr, len(year_shows)))

        for show in year_shows:
            content_parts.append(render_show_html(show))

    # Generate final HTML
    html = render_html_document(
        '\n'.join(content_parts),
        title=title,
        layout=layout
    )

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Generated: {output_path}")
    print(f"  Shows: {len(shows)} (single: {layout_counts[LayoutType.SINGLE]}, "
          f"compact: {layout_counts[LayoutType.COMPACT]}, spread: {layout_counts[LayoutType.SPREAD]})")


def generate_pdf(html_path: Path, pdf_path: Path) -> None:
    """Convert HTML to PDF using weasyprint"""
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()

        print(f"Generating PDF: {pdf_path}")
        HTML(filename=str(html_path)).write_pdf(
            str(pdf_path),
            font_config=font_config
        )
        print(f"PDF generated: {pdf_path}")

    except ImportError:
        print("Error: weasyprint not installed.")
        print("Install with: pip install weasyprint")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Grateful Dead setlist books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate.py --preview                    # Preview all shows
    python generate.py --year 1972 --preview        # Preview 1972
    python generate.py --era 70s --pdf              # Generate 70s PDF
    python generate.py --all --pdf                  # Generate all era PDFs
        """
    )

    parser.add_argument('--data', type=Path, default=Path('../data/setlist.tsv'),
                        help='Path to setlist TSV file')
    parser.add_argument('--output', type=Path, default=Path('output'),
                        help='Output directory')

    # Selection
    parser.add_argument('--year', type=int, help='Generate for a specific year')
    parser.add_argument('--era', choices=['60s', '70s', '80s', '90s'],
                        help='Generate for an era')
    parser.add_argument('--all', action='store_true',
                        help='Generate all eras as separate volumes')

    # Output format
    parser.add_argument('--preview', action='store_true',
                        help='Generate HTML for preview (default)')
    parser.add_argument('--pdf', action='store_true',
                        help='Generate PDF output')

    # Layout
    parser.add_argument('--layout', choices=['compact', 'full'],
                        default='compact',
                        help='Layout style: compact (multiple per page) or full (one per page)')
    parser.add_argument('--debug-layout', action='store_true',
                        help='Print layout classification details')

    args = parser.parse_args()

    # Resolve data path relative to script location
    script_dir = Path(__file__).parent
    data_path = args.data
    if not data_path.is_absolute():
        data_path = script_dir / data_path

    if not data_path.exists():
        print(f"Error: Data file not found: {data_path}")
        return

    # Parse all shows
    print(f"Loading shows from {data_path}...")
    shows = parse_shows(data_path)
    print(f"Loaded {len(shows)} shows")

    # Output directory
    output_dir = args.output
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir

    # Generate based on mode
    if args.all:
        for era in ['60s', '70s', '80s', '90s']:
            html_path = output_dir / f"gd-{era}.html"
            generate_book(shows, html_path, era=era, layout=args.layout,
                         debug_layout=args.debug_layout)

            if args.pdf:
                pdf_path = output_dir / f"gd-{era}.pdf"
                generate_pdf(html_path, pdf_path)
    else:
        if args.year:
            filename = f"gd-{args.year}"
        elif args.era:
            filename = f"gd-{args.era}"
        else:
            filename = "gd-complete"

        html_path = output_dir / f"{filename}.html"
        generate_book(shows, html_path, year=args.year, era=args.era,
                     layout=args.layout, debug_layout=args.debug_layout)

        if args.pdf:
            pdf_path = output_dir / f"{filename}.pdf"
            generate_pdf(html_path, pdf_path)

    if not args.pdf:
        print(f"\nTo preview, open the HTML file in your browser")
        print(f"Or run: python preview.py")


if __name__ == "__main__":
    main()
