#!/usr/bin/env python3
"""
VIBE CODED
Rename files in a directory to sequential numbers (1, 2, 3, ...),
sorted by their original filename (works well for timestamp-named
screenshots like "Screenshot 2026-06-20 at 14.01.45.png").

Usage:
    python3 rename_sequential.py /path/to/directory
    python3 rename_sequential.py /path/to/directory --start 1
    python3 rename_sequential.py /path/to/directory --pad 3
"""

import argparse
import os
import sys


def rename_sequential(directory: str, start: int = 1, pad: int = 0):
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"No such directory: {directory}")

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files.sort()  # alphabetical sort = chronological for "Screenshot YYYY-MM-DD at HH.MM.SS" names

    if not files:
        print("No files found.")
        return

    digits = pad if pad > 0 else len(str(start + len(files) - 1))

    # do renames via a temp pass first to avoid collisions (e.g. renaming 2->1 before 1 exists yet)
    temp_names = []
    for i, filename in enumerate(files):
        ext = os.path.splitext(filename)[1]
        temp_name = f"__tmp_{i}{ext}"
        os.rename(os.path.join(directory, filename), os.path.join(directory, temp_name))
        temp_names.append((temp_name, ext))

    for i, (temp_name, ext) in enumerate(temp_names):
        new_number = start + i
        new_name = f"{str(new_number).zfill(digits)}{ext}"
        os.rename(os.path.join(directory, temp_name), os.path.join(directory, new_name))
        print(f"  -> {new_name}")

    print(f"\nRenamed {len(files)} file(s) in {directory}")


def main():
    parser = argparse.ArgumentParser(description="Rename files in a directory to sequential numbers.")
    parser.add_argument("directory", help="Directory containing the files")
    parser.add_argument("--start", type=int, default=1, help="Starting number (default: 1)")
    parser.add_argument("--pad", type=int, default=0,
                         help="Zero-pad to this many digits (default: auto, based on file count)")
    args = parser.parse_args()

    try:
        rename_sequential(args.directory, args.start, args.pad)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()