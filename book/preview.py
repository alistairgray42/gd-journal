#!/usr/bin/env python3
"""
Preview Server for Grateful Dead Setlist Book

Runs a local web server that:
- Serves generated HTML files
- Auto-regenerates when source files change
- Provides live reload capability

Usage:
    python preview.py                    # Start preview server
    python preview.py --era 1            # Preview specific era
    python preview.py --port 8080        # Custom port
"""

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time
from functools import partial
from pathlib import Path


class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with better defaults for our use case"""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self):
        # Disable caching for easier iteration
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        # Cleaner logging
        print(f"[{self.log_date_time_string()}] {args[0]}")


def regenerate(args, script_dir: Path):
    """Regenerate the HTML files"""
    cmd = [sys.executable, str(script_dir / "generate.py")]

    if args.era:
        cmd.extend(["--era", args.era])

    cmd.append("--preview")

    print(f"Regenerating: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=script_dir)


def watch_for_changes(args, script_dir: Path, watched_files: list[Path]):
    """Watch files for changes and regenerate"""
    mtimes = {f: f.stat().st_mtime if f.exists() else 0 for f in watched_files}

    while True:
        time.sleep(1)
        changed = False

        for f in watched_files:
            if f.exists():
                mtime = f.stat().st_mtime
                if mtime != mtimes.get(f, 0):
                    print(f"\nFile changed: {f.name}")
                    mtimes[f] = mtime
                    changed = True

        if changed:
            regenerate(args, script_dir)
            print("\n✓ Regenerated. Refresh your browser to see changes.\n")


def main():
    parser = argparse.ArgumentParser(description="Preview server for setlist book")

    parser.add_argument(
        "--port", type=int, default=8000, help="Port to serve on (default: 8000)"
    )
    parser.add_argument(
        "--era",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
        help="Preview specific era",
    )
    parser.add_argument("--no-watch", action="store_true", help="Disable file watching")

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Initial generation
    regenerate(args, script_dir)

    # Determine which file to preview
    if args.era:
        html_file = f"gd-{args.era}.html"
    else:
        html_file = "gd-complete.html"

    # Start file watcher
    if not args.no_watch:
        watched_files = [
            script_dir / "templates" / "style.css",
            script_dir / "generate.py",
            script_dir.parent / "data" / "setlist.tsv",
            script_dir / "parse_shows.py",
        ]
        watcher_thread = threading.Thread(
            target=watch_for_changes,
            args=(args, script_dir, watched_files),
            daemon=True,
        )
        watcher_thread.start()
        print("Watching for changes to style.css, generate.py, and setlist.tsv")

    # Start server
    os.chdir(script_dir)

    handler = partial(PreviewHandler, directory=str(script_dir))

    with socketserver.TCPServer(("", args.port), handler) as httpd:
        url = f"http://localhost:{args.port}/output/{html_file}"
        print(f"\n{'=' * 60}")
        print("Preview server running!")
        print(f"{'=' * 60}")
        print(f"\nOpen in browser: {url}")
        print("\nPress Ctrl+C to stop\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()


if __name__ == "__main__":
    main()
