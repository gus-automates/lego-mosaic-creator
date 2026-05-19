# LEGO Mosaic Converter — Developer Notes

## Project Purpose

Converts any raster image into a LEGO mosaic by:
1. Downscaling the image so each pixel represents one stud.
2. Mapping each pixel to the nearest colour in a curated LEGO palette using
   perceptual (CIELAB) colour distance.
3. Rendering a live preview with selectable piece types and optional grid lines.
4. Exporting a high-resolution PNG and a BrickLink-compatible CSV shopping list.

---

## Architecture

```
main.py                     Entry point — creates QApplication and MainWindow
lego_mosaic/
  __init__.py               Package marker (empty)
  lego_colors.py            Palette data + helpers
  mosaic.py                 Pure image-processing logic (no Qt)
  app.py                    PyQt6 MainWindow + all UI code
  export.py                 PNG render + CSV export helpers
```

### lego_colors.py

Defines `LEGO_COLORS`: a plain Python list of dicts:

```python
{"name": str, "rgb": (R, G, B), "bricklink_id": str}
```

`get_palette_rgb()` returns an `(N, 3)` float64 NumPy array for vectorised
distance calculations.

### mosaic.py

| Function | Purpose |
|---|---|
| `pixelate(image, stud_size_px)` | Resize image; one pixel = one stud |
| `map_to_lego_colors(small_img, num_colors)` | Quantise then LAB-match to palette |
| `build_color_grid(image, stud_size_px, num_colors)` | Full pipeline |
| `count_colors(color_grid)` | Histogram of LEGO colour indices |

The LAB palette array is pre-computed once at import time (`_PALETTE_LAB`) to
avoid repeated conversions.

### app.py

`MainWindow` owns:
- `source_image` — the PIL Image loaded by the user
- `color_grid` — 2-D `int32` NumPy array of LEGO colour indices
- A `QTimer` debouncer (100 ms) so sliders don't trigger expensive recomputes
  on every tick

The preview is drawn with `QPainter` directly onto a `QPixmap` (no PIL
round-trip) and is scaled to fit the left panel without distortion by the
`PreviewLabel` subclass.

### export.py

| Function | Purpose |
|---|---|
| `render_mosaic_image(...)` | Return a PIL RGBA image of the mosaic |
| `save_mosaic_image(...)` | Render and save as PNG |
| `export_shopping_list(...)` | Write BrickLink CSV |

---

## How to Run

```bash
pip install -r requirements.txt
python main.py
```

Python 3.10 or newer is required.

---

## Key Algorithms

### LAB Colour Matching

1. The LEGO palette is converted from sRGB (0-255) to CIELAB at import time
   and stored as `_PALETTE_LAB` of shape `(N, 3)`.
2. For each batch of pixels (after PIL quantisation), the pixels are also
   converted to LAB.
3. A vectorised broadcast computes squared Euclidean distance:
   ```
   diff  = pixels_lab[:, None, :] - _PALETTE_LAB[None, :, :]  # (P, N, 3)
   dist² = (diff ** 2).sum(axis=2)                             # (P, N)
   best  = argmin(dist², axis=1)                               # (P,)
   ```
4. `argmin` gives the index of the closest LEGO colour for every pixel.

LAB distance approximates human colour perception, so results look more
natural than matching in raw RGB space.

### Debounced Slider Updates

`on_controls_changed()` calls `QTimer.start()` (single-shot, 100 ms).
If the slider moves again within 100 ms the timer restarts; `_recompute()`
runs only once the user pauses, preventing UI jank on rapid drags.

### Stud-to-Centimetre Formula

```
1 stud = 8 mm  →  width_cm = cols × 8 / 10
```

---

## Adding New LEGO Colours

Open `lego_mosaic/lego_colors.py` and append a new entry to `LEGO_COLORS`:

```python
{"name": "Pearl Gold", "rgb": (170, 127, 46), "bricklink_id": "115"},
```

The new colour will be picked up automatically by the LAB matching — no other
changes are needed. The palette LAB cache is rebuilt on the next import.
