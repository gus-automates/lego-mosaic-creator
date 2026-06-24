# Lego Mosaic Creator
> Convert any photo into a buildable LEGO mosaic with live preview and BrickLink export

![Main interface showing a sunflower converted to a LEGO mosaic](screenshots/main.png)

## What is it
A desktop GUI application that converts any photo into a buildable LEGO mosaic — with live controls, colour editing, real-world size calculations, and a BrickLink-ready shopping list.

## Why use it
Turning a photo into a buildable LEGO mosaic by hand means manually picking colours, counting pieces, and guessing at sizing. This app automates all of it: perceptual (LAB) colour matching gives more natural results than naive RGB distance, live sliders let you tune the result in real time, and one click produces a BrickLink Wanted List XML you can upload directly to order the parts.

### Source photo → mosaic

| Original photo | Mosaic result |
|---|---|
| <img src="screenshots/mosaic-import.jpg" width="400"> | <img src="screenshots/mosaic-result.png" width="400"> |

### Colour editor

Click any colour row in the breakdown panel (or any tile in the preview) to open the colour picker and replace it across the entire mosaic.

| Replace a whole colour | Replace a single tile |
|---|---|
| ![Colour picker opened from a breakdown row](screenshots/edit-image2.png) | ![Colour picker opened from a tile click](screenshots/edit-image.png) |

## Installation

**Prerequisites:** Python 3.10+, pip

```bash
git clone https://github.com/gus-automates/lego-mosaic-creator.git
cd lego-mosaic-creator
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Usage

1. Click **Load Image** and choose any PNG, JPG, BMP, or WebP photo.
2. Set **Width (studs)** and **Max colours** (2–30), fine-tune **Brightness**/**Contrast**, and pick a **Piece type**.
3. Click any row in the **Colour Breakdown** panel — or any tile in the preview — to edit colours.
4. Click **Save Mosaic** to export a PNG, or **Export XML** to save a BrickLink Wanted List ready for upload.

## Features

**Done**
- ✅ Live preview — drag any slider and the mosaic updates within milliseconds
- ✅ LAB colour matching — perceptual colour space gives more natural results than raw RGB distance
- ✅ 33-colour LEGO palette — curated set of commonly available LEGO colours
- ✅ Three piece types — 1×1 Tile (3070), 1×1 Plate (3024), 1×1 Round Plate (98138)
- ✅ Adjustable stud width — set exact mosaic width in studs; height is derived from the aspect ratio
- ✅ Colour budget — limit how many distinct colours appear (2–30)
- ✅ Brightness & contrast controls — tweak the source image before matching
- ✅ Grid lines toggle — show or hide stud borders in the preview
- ✅ Real-world size display — instant cm and inch dimensions (1 stud = 8 mm)
- ✅ Click-to-edit colours — click any tile in the preview, or any row in the colour breakdown, to swap that colour across the whole mosaic
- ✅ PNG export — high-resolution output at 20 px per stud
- ✅ BrickLink XML export — upload directly to a BrickLink Wanted List

---

## Piece Type Reference

| Part Number | Name | Description |
|---|---|---|
| **3070** | 1×1 Tile | Flat tile with no stud on top; very smooth mosaic look |
| **3024** | 1×1 Plate | Thin plate with a stud; the classic mosaic building block |
| **98138** | 1×1 Round Plate | Round stud tile; gives a soft, circular pixel look |

All three parts are widely available on BrickLink and in LEGO Pick-A-Brick stores.

## BrickLink XML Export

The exported XML follows the standard BrickLink Wanted List format and can be uploaded directly via **My BrickLink → Wanted List → Upload**. Each entry contains the part number, BrickLink colour ID, quantity, and condition (New).

## How It Works

### LAB Colour Matching

Raw RGB distance is a poor proxy for how humans perceive colour differences. This app converts every pixel and the entire LEGO palette to **CIELAB** colour space, then uses vectorised nearest-neighbour matching:

```
diff  = pixels_lab[:, None, :] - palette_lab[None, :, :]  # (P, N, 3)
dist² = (diff ** 2).sum(axis=2)                            # (P, N)
best  = argmin(dist², axis=1)                              # (P,)
```

The palette LAB array is pre-computed once at import time so slider changes are fast.

### Colour Budget Enforcement

After the full LAB match, if more than `max_colours` distinct LEGO colours were used, the least-used ones are dropped and their pixels are re-assigned to the nearest remaining colour — also in LAB space.

### Debounced Controls

All slider and spinbox changes feed into a 100 ms single-shot `QTimer`. If the user keeps dragging, the timer resets; `_recompute()` runs only once the user pauses. This prevents UI jank on rapid drags.

## Tech Stack

| Library | Purpose |
|---|---|
| Python 3.10+ | Language |
| PyQt6 | Desktop GUI framework |
| Pillow | Image loading, resizing |
| NumPy | Vectorised colour distance calculations |
| scikit-image | RGB → CIELAB colour space conversion |

## Project Structure

```
lego_mosaic/
  __init__.py        Package marker
  lego_colors.py     33-colour LEGO palette + helper functions
  mosaic.py          Core image-processing pipeline
  app.py             PyQt6 MainWindow and all UI code
  export.py          PNG renderer and BrickLink XML exporter
main.py              Application entry point
requirements.txt     Python dependencies
```

## Adding New LEGO Colours

Open `lego_mosaic/lego_colors.py` and append a new entry to `LEGO_COLORS`:

```python
{"name": "Pearl Gold", "rgb": (170, 127, 46), "bricklink_id": "115"},
```

The new colour is picked up automatically by the LAB matching on the next run — no other changes needed.
