#!/usr/bin/env python3
"""
Crop a screenshot down to just the white page in the center,
ignoring whatever else (dock, menu bar, desktop, other windows) is in the shot.

Usage:
    python3 crop_page.py screenshot.png
    python3 crop_page.py screenshot.png --output cropped.png
    python3 crop_page.py screenshot.png --threshold 235 --padding 5

How it works:
    Finds all "white" pixels (brightness above threshold), then finds
    the largest contiguous white region (the page) and crops to its
    bounding box. This works regardless of what's around it.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def crop_to_page(image_path: str, output_path: str = None, threshold: int = 235, padding: int = 0) -> str:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"No such file: {image_path}")

    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    height, width = arr.shape[:2]

    # brightness per pixel
    brightness = arr.mean(axis=2)

    # mask of "white" pixels
    white_mask = brightness > threshold

    # label connected white regions
    labeled, num_features = ndimage.label(white_mask)
    if num_features == 0:
        raise ValueError("No white region found — try lowering --threshold")

    # find the largest connected white region by pixel count
    sizes = ndimage.sum(white_mask, labeled, range(1, num_features + 1))
    largest_label = np.argmax(sizes) + 1

    # bounding box of that region
    rows = np.any(labeled == largest_label, axis=1)
    cols = np.any(labeled == largest_label, axis=0)
    top, bottom = np.where(rows)[0][[0, -1]]
    left, right = np.where(cols)[0][[0, -1]]

    # apply padding, clamped to image bounds
    top = max(0, top - padding)
    left = max(0, left - padding)
    bottom = min(height - 1, bottom + padding)
    right = min(width - 1, right + padding)

    cropped = img.crop((left, top, right + 1, bottom + 1))

    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_cropped{ext}"

    cropped.save(output_path)
    print(f"Found largest white region: {right - left + 1}x{bottom - top + 1} px")
    print(f"Cropped from {width}x{height} to {cropped.width}x{cropped.height}")
    print(f"Saved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Crop a screenshot to the white page region, ignoring surroundings.")
    parser.add_argument("image_path", help="Path to the screenshot image")
    parser.add_argument("--output", help="Output path (default: <input>_cropped.<ext>)")
    parser.add_argument("--threshold", type=int, default=235,
                         help="Brightness threshold (0-255) above which pixels count as 'white page' (default: 235)")
    parser.add_argument("--padding", type=int, default=0,
                         help="Extra pixels to keep around the detected page edges (default: 0)")
    args = parser.parse_args()

    try:
        crop_to_page(args.image_path, args.output, args.threshold, args.padding)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()