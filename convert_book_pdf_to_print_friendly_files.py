# REQUIRED SETUP
# pip install pdf2image --break-system-packages
# brew install poppler   # macOS — pdf2image needs poppler installed

BOOK_DIR = "/Users/tarek/github/gogogo/books"


#!/usr/bin/env python3
"""
Convert each page of a PDF into a high-quality PNG image.
 
Usage:
    python pdf_to_images.py /path/to/file.pdf
    python pdf_to_images.py /path/to/file.pdf --dpi 600
 
Creates a new directory named after the PDF (next to it) and saves
one PNG per page, named by page number (1.png, 2.png, ...).
"""
 
import argparse
import os
import sys
 
from pdf2image import convert_from_path
 
 
def pdf_to_images(pdf_path: str, dpi: int = 300) -> str:
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"No such file: {pdf_path}")
 
    base_dir = os.path.dirname(os.path.abspath(pdf_path))
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(base_dir, base_name)
    os.makedirs(output_dir, exist_ok=True)
 
    print(f"Converting '{pdf_path}' at {dpi} DPI...")
    images = convert_from_path(pdf_path, dpi=dpi)
 
    digits = len(str(len(images)))
    for i, image in enumerate(images, start=1):
        page_filename = f"{str(i).zfill(digits)}.png"
        page_path = os.path.join(output_dir, page_filename)
        # PNG is lossless by definition; optimize for max quality
        image.save(page_path, "PNG")
        print(f"  saved {page_path}")
 
    print(f"\nDone. {len(images)} page(s) saved to: {output_dir}")
    return output_dir
 
 
def main():
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG images.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--dpi", type=int, default=300, help="Resolution for output images (default: 300, use 600 for very high quality)"
    )
    args = parser.parse_args()
 
    try:
        pdf_to_images(args.pdf_path, dpi=args.dpi)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
 
 
if __name__ == "__main__":
    # to do: get rid of the annoying grey border around the tsumego -______-
    # to do: update this script to run ALL images in a dir
    # right now: use ipython convert_book_pdf_to_print_friendly_files.py FILEPATH_TO_ONE_FILE_ONLY
    # using this as a workaround:
#     for f in "books/Cho Chikun Encyclopedia of Life & Death - Intermediate Problems/"*.png; do
#   ipython book_convert_screenshots_to_print_friendly_images.py "$f"
# done
    main()
