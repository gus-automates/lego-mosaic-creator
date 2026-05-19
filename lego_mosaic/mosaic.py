"""
Core image-processing logic for the LEGO mosaic converter.

No PyQt imports — pure Python / NumPy / Pillow / scikit-image.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from skimage.color import rgb2lab

from lego_mosaic.lego_colors import LEGO_COLORS, get_palette_rgb


# ---------------------------------------------------------------------------
# Pre-compute the palette in LAB space once at import time for speed.
# ---------------------------------------------------------------------------

def _build_palette_lab() -> np.ndarray:
    """Convert the entire LEGO palette to LAB and cache as (N, 3) float64."""
    palette_rgb = get_palette_rgb()  # (N, 3) float64, values 0-255
    # skimage expects float images in [0, 1]
    palette_rgb_norm = palette_rgb[np.newaxis, :, :] / 255.0  # (1, N, 3)
    palette_lab = rgb2lab(palette_rgb_norm)  # (1, N, 3)
    return palette_lab[0]  # (N, 3)


_PALETTE_LAB: np.ndarray = _build_palette_lab()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pixelate(image: Image.Image, stud_size_px: int) -> tuple[Image.Image, int, int]:
    """
    Resize *image* so that each pixel will represent one stud.

    Parameters
    ----------
    image:
        Source PIL image (any mode).
    stud_size_px:
        How many pixels in the *source* image correspond to one stud.

    Returns
    -------
    small_img:
        Downscaled RGB image where each pixel == one stud.
    cols:
        Number of studs horizontally.
    rows:
        Number of studs vertically.
    """
    img_rgb = image.convert("RGB")
    w, h = img_rgb.size
    cols = max(1, w // stud_size_px)
    rows = max(1, h // stud_size_px)
    small_img = img_rgb.resize((cols, rows), Image.Resampling.LANCZOS)
    return small_img, cols, rows


def map_to_lego_colors(small_img: Image.Image, num_colors: int) -> np.ndarray:
    """
    Map every pixel of *small_img* to the nearest LEGO colour, then limit the
    result to the *num_colors* most-used LEGO colours.

    Steps
    -----
    1. Match every pixel directly to the full LEGO palette using LAB distance.
    2. Count which LEGO colours were used and how often.
    3. Keep only the top *num_colors* by pixel count.
    4. Re-assign pixels whose colour was dropped to the nearest allowed colour.

    Pre-quantising with PIL before the LEGO match is deliberately avoided:
    PIL cluster centres can drift to hues that are far from any LEGO colour,
    producing wildly wrong results (e.g. blue+beige → greenish cluster → Green).

    Parameters
    ----------
    small_img:
        Downscaled RGB image (one pixel per stud).
    num_colors:
        Maximum number of distinct LEGO colours to use in the output.

    Returns
    -------
    index_grid : np.ndarray, shape (rows, cols), dtype int32
        Each cell holds an index into ``LEGO_COLORS``.
    """
    rows, cols = small_img.height, small_img.width

    # --- Step 1: full palette LAB match ------------------------------------
    pixels = np.array(small_img.convert("RGB"), dtype=np.float64)  # (rows, cols, 3)
    pixels_norm = pixels / 255.0
    pixels_lab = rgb2lab(pixels_norm)  # (rows, cols, 3)
    flat_lab = pixels_lab.reshape(-1, 3)  # (N_pixels, 3)

    diff = flat_lab[:, np.newaxis, :] - _PALETTE_LAB[np.newaxis, :, :]  # (N_pixels, N_palette, 3)
    dist_sq = np.sum(diff ** 2, axis=2)  # (N_pixels, N_palette)
    best_idx = np.argmin(dist_sq, axis=1)  # (N_pixels,)

    # --- Step 2: limit to top num_colors LEGO colours ----------------------
    num_colors_clamped = max(1, min(num_colors, len(_PALETTE_LAB)))
    unique, counts = np.unique(best_idx, return_counts=True)
    if len(unique) > num_colors_clamped:
        # Keep only the most-used colours
        order = np.argsort(counts)[::-1]
        allowed = set(unique[order[:num_colors_clamped]].tolist())
        allowed_arr = np.array(sorted(allowed), dtype=np.int64)

        # Re-assign dropped pixels to nearest allowed colour
        dropped_mask = ~np.isin(best_idx, allowed_arr)
        if dropped_mask.any():
            allowed_lab = _PALETTE_LAB[allowed_arr]  # (K, 3)
            dropped_lab = flat_lab[dropped_mask]      # (M, 3)
            d = dropped_lab[:, np.newaxis, :] - allowed_lab[np.newaxis, :, :]
            best_idx[dropped_mask] = allowed_arr[np.argmin(np.sum(d ** 2, axis=2), axis=1)]

    return best_idx.reshape(rows, cols).astype(np.int32)


def build_color_grid(
    image: Image.Image,
    stud_size_px: int,
    num_colors: int,
) -> np.ndarray:
    """
    Full pipeline: pixelate then map colours.

    Parameters
    ----------
    image:
        Source image.
    stud_size_px:
        Pixels per stud in the source image.
    num_colors:
        Colour budget passed to :func:`map_to_lego_colors`.

    Returns
    -------
    index_grid : np.ndarray, shape (rows, cols), dtype int32
    """
    small_img, _cols, _rows = pixelate(image, stud_size_px)
    return map_to_lego_colors(small_img, num_colors)


def build_color_grid_by_size(
    image: Image.Image,
    target_cols: int,
    num_colors: int,
) -> np.ndarray:
    """
    Full pipeline resizing to an exact stud width.

    Parameters
    ----------
    image:
        Source image.
    target_cols:
        Desired mosaic width in studs.  Rows are derived from the aspect ratio.
    num_colors:
        Colour budget passed to :func:`map_to_lego_colors`.

    Returns
    -------
    index_grid : np.ndarray, shape (rows, target_cols), dtype int32
    """
    img_rgb = image.convert("RGB")
    w, h = img_rgb.size
    target_rows = max(1, round(h * target_cols / w))
    small_img = img_rgb.resize((target_cols, target_rows), Image.Resampling.LANCZOS)
    return map_to_lego_colors(small_img, num_colors)


def count_colors(color_grid: np.ndarray) -> dict[int, int]:
    """
    Count how many times each LEGO colour index appears in the grid.

    Returns
    -------
    dict mapping lego_color_index → stud count, sorted by count descending.
    """
    indices, counts = np.unique(color_grid, return_counts=True)
    result = {int(idx): int(cnt) for idx, cnt in zip(indices, counts)}
    return dict(sorted(result.items(), key=lambda kv: kv[1], reverse=True))
