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
    python generate.py --era 1            # Era
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from classes import LayoutType, Set, Show
from parse_shows import get_all_shows
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration


def format_song(song: str) -> tuple[str, bool]:
    """
    Parse a song entry, returning (song_name, is_segue, note)
    Songs starting with '>' indicate segue from previous
    Songs with '*' or other annotations at the end have notes
    """
    is_segue = song.startswith(">")
    if is_segue:
        song = song[1:].strip()

    return song.strip(), is_segue


def render_set_html(s: Set, is_only_set: bool) -> str:
    """Render a single set as HTML"""
    lines = []
    lines.append('    <section class="set">')

    if not is_only_set:
        label_html = f'<h3 class="set-label">{s.display_label}'
        if s.annotation:
            label_html += f' <span class="set-annotation">({s.annotation})</span>'
        label_html += "</h3>"
        lines.append(f"      {label_html}")

    lines.append('      <ul class="songs">')
    for song in s.songs:
        song_name, is_segue = format_song(song)
        class_attr = ' class="segue"' if is_segue else ""
        lines.append(f"        <li{class_attr}>{song_name}</li>")
    lines.append("      </ul>")
    lines.append("    </section>")

    return "\n".join(lines)


def render_show_header_html(show: Show) -> str:
    """Render just the show header (date, venue, notes)"""
    lines = []
    lines.append('  <header class="show-header">')
    lines.append(f'    <h2 class="show-date">{show.formatted_date}</h2>')
    lines.append(f'    <p class="show-venue">{show.venue_display}</p>')
    lines.append(f'    <p class="show-location">{show.location_display}</p>')

    if show.notes:
        notes = show.notes.strip()
        if notes.startswith("(") and notes.endswith(")"):
            notes = notes[1:-1]
        lines.append(f'    <p class="show-notes">{notes}</p>')

    lines.append("  </header>")
    return "\n".join(lines)


def render_show_single(show: Show) -> str:
    """Render a show that fits on a single page"""
    css_class = "show"

    lines = [f'<article class="{css_class}">']
    lines.append(render_show_header_html(show))
    lines.append('  <div class="sets">')
    for s in show.sets:
        lines.append(render_set_html(s, len(show.sets) == 1))
    lines.append("  </div>")
    lines.append("</article>")

    return "\n".join(lines)


def render_show_spread(show: Show) -> str:
    """
    Render a show as a two-page spread.

    Structure:
    - Page 1 (verso/left): Header + first set(s)
    - Page 2 (recto/right): Remaining sets

    Uses CSS to force page 1 to start on a left page.
    """
    sets = show.to_page_friendly_set_groupings()
    sets_page1, *remaining_sets = sets

    lines = []

    # Page 1: Verso (left page) - starts on left via CSS
    lines.append('<article class="show show-spread">')
    lines.append(render_show_header_html(show))
    lines.append('  <div class="sets">')
    for s in sets_page1:
        lines.append(render_set_html(s, False))
    lines.append("  </div>")
    lines.append("</article>")

    for set_page in remaining_sets:
        # Page 2: Recto (right page)
        # and further pages as needed
        lines.append('<article class="show show-spread">')
        # Condensed header for continuity
        lines.append('  <header class="show-header show-header-continued">')
        lines.append(
            f'    <p class="show-date-continued">{show.formatted_date} <span class="continued-label">(continued)</span></p>'
        )
        lines.append("  </header>")
        lines.append('  <div class="sets">')
        for s in set_page:
            lines.append(render_set_html(s, False))
        lines.append("  </div>")
        lines.append("</article>")

    return "\n".join(lines)


def render_show_html(show: Show) -> str:
    """Render a show with appropriate layout based on its size"""
    layout_type = show.classify_layout()

    if layout_type == LayoutType.SPREAD:
        return render_show_spread(show)
    else:
        return render_show_single(show)


def render_volume_title(
    title: str, subtitle: str, year_range: str, show_count: int
) -> str:
    """Render a volume title page"""
    return f"""
<div class="volume-title-page">
  <h1>{title}</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="year-range">{year_range}</p>
  <hr class="decorative-rule">
  <p class="show-count">{show_count} shows</p>
</div>
"""


def render_html_document(content: str, title: str = "Grateful Dead Setlists") -> str:
    """Wrap content in a full HTML document"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=Playfair+Display:wght@400;700&family=Source+Sans+Pro:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/templates/style.css">
</head>
<body>
{content}
</body>
</html>
"""


def get_era_dates(era: str) -> tuple[int, int, int, int, int, int, str]:
    """Return start and end dates for an era"""
    eras = {
        "1": (1966, 1, 8, 1970, 1, 30, "The Bus Came by and I Got On"),
        "2": (1970, 1, 31, 1972, 6, 17, "Down on Bourbon Street"),
        "3": (1972, 6, 18, 1974, 10, 20, "I'll Walk You in the Sunshine"),
        "4": (1974, 10, 21, 1977, 6, 9, "A Rainbow Full of Sound"),
        "5": (1977, 6, 10, 1979, 2, 17, "The Compass Always Points to Terrapin"),
        "6": (1979, 2, 18, 1981, 8, 31, "So Far from Me"),
        "7": (1981, 9, 1, 1983, 12, 31, "Wheel to the Storm and Fly"),
        "8": (1984, 1, 1, 1986, 7, 7, "Maybe the Sun Is Shining"),
        "9": (1986, 7, 8, 1988, 12, 31, "We Will Survive"),
        "10": (1989, 2, 5, 1990, 7, 23, "Shall We Go, You and I While We Can?"),
        "11": (1990, 7, 24, 1993, 4, 5, "So Many Roads to Ease My Soul"),
        "12": (1993, 4, 6, 1995, 7, 9, "I Sang Love's Sweet Song"),
    }
    return eras.get(era, (1966, 1, 8, 1995, 7, 9, "Complete"))


def generate_book(
    shows: list[Show],
    output_path: Path,
    era: Optional[str] = None,
    debug_layout: bool = False,
) -> None:
    """Generate an HTML book from shows"""

    # Filter shows
    if era:
        start_year, start_month, start_day, end_year, end_month, end_day, nickname = (
            get_era_dates(era)
        )
        start_date = datetime(start_year, start_month, start_day)
        end_date = datetime(end_year, end_month, end_day)

        era_shows = []
        for s in shows:
            show_date = datetime(s.year, s.month, s.day)
            if start_date <= show_date <= end_date:
                era_shows.append(s)
        shows = era_shows
        title = f"Grateful Dead: {nickname}"
        year_range = (
            f"{start_month}/{start_day}/{start_year}–{end_month}/{end_day}/{end_year}"
        )
    else:
        title = "Grateful Dead: Complete Setlists"
        years = sorted(set(s.year for s in shows))
        year_range = f"{min(years)}–{max(years)}" if years else ""

    if not shows:
        print("No shows found for the specified filter")
        return

    # Layout statistics
    layout_counts = {LayoutType.SINGLE: 0, LayoutType.SPREAD: 0}
    for show in shows:
        layout_counts[show.classify_layout()] += 1

    if debug_layout:
        print("\nLayout breakdown:")
        print(f"  Single page: {layout_counts[LayoutType.SINGLE]}")
        print(f"  Spread:      {layout_counts[LayoutType.SPREAD]}")

    # Build content
    content_parts = []

    # Volume title page
    content_parts.append(
        render_volume_title(
            "Grateful Dead", "Complete Setlists", year_range, len(shows)
        )
    )

    for show in shows:
        content_parts.append(render_show_html(show))

    # Generate final HTML
    html = render_html_document("\n".join(content_parts), title=title)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Generated: {output_path}")
    print(
        f"  Shows: {len(shows)} (single: {layout_counts[LayoutType.SINGLE]}, spread: {layout_counts[LayoutType.SPREAD]})"
    )


def generate_pdf(html_path: Path, pdf_path: Path) -> None:
    """Convert HTML to PDF using weasyprint"""
    font_config = FontConfiguration()

    print(f"Generating PDF: {pdf_path}")
    HTML(filename=str(html_path)).write_pdf(str(pdf_path), font_config=font_config)
    print(f"PDF generated: {pdf_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Grateful Dead setlist books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate.py --preview                    # Preview all shows
    python generate.py --era 1 --pdf                # Generate PDF for era 1
    python generate.py --all --pdf                  # Generate all era PDFs
        """,
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=Path("../data/setlist.tsv"),
        help="Path to setlist TSV file",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output"), help="Output directory"
    )

    # Selection
    parser.add_argument(
        "--era",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
        help="Generate for a specific era",
    )

    # Output format
    parser.add_argument(
        "--preview", action="store_true", help="Generate HTML for preview (default)"
    )
    parser.add_argument("--pdf", action="store_true", help="Generate PDF output")

    parser.add_argument(
        "--debug-layout",
        action="store_true",
        help="Print layout classification details",
    )

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
    shows = get_all_shows(data_path)
    print(f"Loaded {len(shows)} shows")

    # Output directory
    output_dir = args.output
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir

    # Generate based on mode
    if args.era:
        filename = f"gd-{args.era}"

        html_path = output_dir / f"{filename}.html"
        generate_book(
            shows,
            html_path,
            era=args.era,
            debug_layout=args.debug_layout,
        )

        if args.pdf:
            pdf_path = output_dir / f"{filename}.pdf"
            generate_pdf(html_path, pdf_path)
    else:
        for era in [str(i) for i in range(1, 13)]:
            html_path = output_dir / f"gd-{era}.html"
            generate_book(
                shows,
                html_path,
                era=era,
                debug_layout=args.debug_layout,
            )

            if args.pdf:
                pdf_path = output_dir / f"gd-{era}.pdf"
                generate_pdf(html_path, pdf_path)

    if not args.pdf:
        print("\nTo preview, open the HTML file in your browser")
        print("Or run: python preview.py")


if __name__ == "__main__":
    main()
