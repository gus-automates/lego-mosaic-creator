"""
Export utilities for the LEGO Mosaic Converter.

Provides:
  save_mosaic_image    – render the colour grid to a PNG file
  export_shopping_list – write a BrickLink-ready CSV shopping list
"""

from __future__ import annotations

import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from lego_mosaic.lego_colors import LEGO_COLORS
from lego_mosaic.mosaic import count_colors

# Piece-type identifier strings
PIECE_TILE       = "3070"    # 1×1 Tile
PIECE_PLATE      = "3024"    # 1×1 Plate
PIECE_ROUND      = "98138"   # 1×1 Round Plate


def _draw_cell(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    cell_size: int,
    rgb: tuple[int, int, int],
    piece_type: str,
    draw_grid: bool,
) -> None:
    """Draw a single stud cell onto *draw* at pixel position (x, y)."""
    r, g, b = rgb
    fill = (r, g, b, 255)

    if piece_type == PIECE_ROUND:
        # Filled circle with a thin dark ring
        margin = max(1, cell_size // 8)
        bbox = [x + margin, y + margin, x + cell_size - margin, y + cell_size - margin]
        draw.ellipse(bbox, fill=fill)
        if draw_grid:
            draw.ellipse(bbox, outline=(40, 40, 40, 180), width=1)
    elif piece_type == PIECE_PLATE:
        # Filled square with a white inner border (suggests thicker edge)
        draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=fill)
        if draw_grid:
            border_w = max(1, cell_size // 10)
            draw.rectangle(
                [x, y, x + cell_size - 1, y + cell_size - 1],
                outline=(255, 255, 255, 120),
                width=border_w,
            )
    else:
        # 3070b Tile — filled square with a subtle dark border
        draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=fill)
        if draw_grid:
            draw.rectangle(
                [x, y, x + cell_size - 1, y + cell_size - 1],
                outline=(40, 40, 40, 160),
                width=1,
            )


def render_mosaic_image(
    color_grid: np.ndarray,
    piece_type: str,
    cell_size: int = 20,
    draw_grid: bool = True,
) -> Image.Image:
    """
    Render the colour-index grid to a PIL RGBA image.

    Parameters
    ----------
    color_grid:
        2-D int32 array of indices into LEGO_COLORS.
    piece_type:
        One of ``"3070b"``, ``"3024"``, or ``"98138"``.
    cell_size:
        Pixel size of each stud in the output image.
    draw_grid:
        Whether to draw border lines between studs.

    Returns
    -------
    PIL RGBA image.
    """
    rows, cols = color_grid.shape
    img_w = cols * cell_size
    img_h = rows * cell_size

    img = Image.new("RGBA", (img_w, img_h), (240, 240, 240, 255))
    draw = ImageDraw.Draw(img)

    for r in range(rows):
        for c in range(cols):
            idx = int(color_grid[r, c])
            rgb = LEGO_COLORS[idx]["rgb"]
            x = c * cell_size
            y = r * cell_size
            _draw_cell(draw, x, y, cell_size, rgb, piece_type, draw_grid)

    return img


def save_mosaic_image(
    color_grid: np.ndarray,
    piece_type: str,
    output_path: str | Path,
    cell_size: int = 20,
    draw_grid: bool = True,
) -> None:
    """
    Render the mosaic and save it as a PNG file.

    Parameters
    ----------
    color_grid:
        2-D int32 array of indices into LEGO_COLORS.
    piece_type:
        One of ``"3070b"``, ``"3024"``, or ``"98138"``.
    output_path:
        Destination file path (will be created / overwritten).
    cell_size:
        Pixel size of each stud in the output PNG (default 20).
    draw_grid:
        Whether to draw border lines between studs.
    """
    img = render_mosaic_image(color_grid, piece_type, cell_size, draw_grid)
    img.convert("RGB").save(str(output_path), format="PNG")


def export_shopping_list(
    color_grid: np.ndarray,
    piece_type: str,
    output_path: str | Path,
) -> None:
    """
    Write a BrickLink-compatible CSV shopping list.

    Columns: Colour Name, BrickLink ID, Piece Type, Count

    Parameters
    ----------
    color_grid:
        2-D int32 array of indices into LEGO_COLORS.
    piece_type:
        BrickLink part number string (e.g. ``"3070b"``).
    output_path:
        Destination ``.csv`` file path.
    """
    counts = count_colors(color_grid)
    output_path = Path(output_path)

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Colour Name", "BrickLink Colour ID", "Piece Type", "Count"])
        for idx, count in counts.items():
            colour = LEGO_COLORS[idx]
            writer.writerow([
                colour["name"],
                colour["bricklink_id"],
                piece_type,
                count,
            ])


def export_bricklink_xml(
    color_grid: np.ndarray,
    piece_type: str,
    output_path: str | Path,
) -> None:
    """
    Write a BrickLink Wanted List XML file.

    The format is the standard BrickLink wanted-list XML that can be
    uploaded directly via My BrickLink → Wanted List → Upload.

    Parameters
    ----------
    color_grid:
        2-D int32 array of indices into LEGO_COLORS.
    piece_type:
        BrickLink part number string (e.g. ``"3070b"``).
    output_path:
        Destination ``.xml`` file path.
    """
    counts = count_colors(color_grid)
    output_path = Path(output_path)

    root = ET.Element("INVENTORY")
    for idx, count in counts.items():
        colour = LEGO_COLORS[idx]
        item = ET.SubElement(root, "ITEM")
        ET.SubElement(item, "ITEMTYPE").text = "P"
        ET.SubElement(item, "ITEMID").text = piece_type
        ET.SubElement(item, "COLOR").text = colour["bricklink_id"]
        ET.SubElement(item, "MINQTY").text = str(count)
        ET.SubElement(item, "CONDITION").text = "N"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    with output_path.open("w", encoding="utf-8") as fh:
        fh.write(ET.tostring(root, encoding="unicode"))
