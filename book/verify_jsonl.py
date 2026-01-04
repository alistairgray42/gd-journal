#!/usr/bin/env python3
"""Verify that JSONL reading produces the same results as TSV reading"""
from pathlib import Path

from parse_shows import get_all_shows, get_all_shows_from_tsv

def main():
    tsv_path = Path("../data/setlist.tsv")
    jsonl_path = Path("../data/setlist.jsonl")

    print("Reading from TSV...")
    tsv_shows = get_all_shows_from_tsv(tsv_path)
    print(f"Loaded {len(tsv_shows)} shows from TSV")

    print("Reading from JSONL...")
    jsonl_shows = get_all_shows(jsonl_path)
    print(f"Loaded {len(jsonl_shows)} shows from JSONL")

    # Compare counts
    if len(tsv_shows) != len(jsonl_shows):
        print(f"ERROR: Different number of shows! TSV: {len(tsv_shows)}, JSONL: {len(jsonl_shows)}")
        return False

    # Compare first few shows
    for i in range(min(5, len(tsv_shows))):
        tsv = tsv_shows[i]
        jsonl = jsonl_shows[i]

        if tsv.date != jsonl.date:
            print(f"ERROR: Show {i} dates don't match! TSV: {tsv.date}, JSONL: {jsonl.date}")
            return False

        if len(tsv.sets) != len(jsonl.sets):
            print(f"ERROR: Show {i} ({tsv.date}) has different number of sets! TSV: {len(tsv.sets)}, JSONL: {len(jsonl.sets)}")
            return False

        for j, (tsv_set, jsonl_set) in enumerate(zip(tsv.sets, jsonl.sets)):
            if len(tsv_set.songs) != len(jsonl_set.songs):
                print(f"ERROR: Show {i} ({tsv.date}) set {j} has different number of songs! TSV: {len(tsv_set.songs)}, JSONL: {len(jsonl_set.songs)}")
                return False

    print("\n✓ Verification successful! JSONL matches TSV data")
    print(f"  - {len(jsonl_shows)} shows")
    print(f"  - First show: {jsonl_shows[0].date} at {jsonl_shows[0].venue1}")
    print(f"  - Last show: {jsonl_shows[-1].date} at {jsonl_shows[-1].venue1}")
    return True

if __name__ == "__main__":
    main()
