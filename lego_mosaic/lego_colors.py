"""
LEGO colour palette data.

Each entry contains:
  name        : human-readable colour name
  rgb         : (R, G, B) tuple of integers 0-255
  bricklink_id: BrickLink catalogue ID string
"""

from __future__ import annotations

import numpy as np

LEGO_COLORS: list[dict] = [
    # Neutrals
    {"name": "White",               "rgb": (242, 243, 242), "bricklink_id": "1"},
    {"name": "Black",               "rgb": (27,  42,  52),  "bricklink_id": "11"},
    {"name": "Light Bluish Gray",   "rgb": (171, 173, 172), "bricklink_id": "86"},
    {"name": "Dark Bluish Gray",    "rgb": (99,  95,  97),  "bricklink_id": "85"},
    # Warm neutrals / browns
    {"name": "Tan",                 "rgb": (222, 198, 154), "bricklink_id": "2"},
    {"name": "Dark Tan",            "rgb": (138, 115, 88),  "bricklink_id": "69"},
    {"name": "Nougat",              "rgb": (204, 142, 105), "bricklink_id": "28"},
    {"name": "Light Nougat",        "rgb": (253, 195, 154), "bricklink_id": "90"},
    {"name": "Medium Nougat",       "rgb": (170, 125, 85),  "bricklink_id": "150"},
    {"name": "Reddish Brown",       "rgb": (95,  49,  9),   "bricklink_id": "88"},
    {"name": "Dark Brown",          "rgb": (53,  33,  0),   "bricklink_id": "120"},
    # Reds / pinks
    {"name": "Red",                 "rgb": (179, 0,   6),   "bricklink_id": "5"},
    {"name": "Dark Red",            "rgb": (114, 14,  15),  "bricklink_id": "59"},
    {"name": "Coral",               "rgb": (255, 112, 99),  "bricklink_id": "220"},
    {"name": "Sand Red",            "rgb": (149, 121, 119), "bricklink_id": "58"},
    {"name": "Magenta",             "rgb": (144, 31,  118), "bricklink_id": "71"},
    {"name": "Pink",                "rgb": (255, 161, 202), "bricklink_id": "9"},
    # Oranges / yellows
    {"name": "Orange",              "rgb": (208, 88,  10),  "bricklink_id": "4"},
    {"name": "Bright Light Orange", "rgb": (255, 167, 11),  "bricklink_id": "110"},
    {"name": "Yellow",              "rgb": (255, 196, 0),   "bricklink_id": "3"},
    {"name": "Bright Light Yellow", "rgb": (255, 240, 91),  "bricklink_id": "226"},
    # Greens
    {"name": "Lime",                "rgb": (187, 226, 7),   "bricklink_id": "34"},
    {"name": "Bright Green",        "rgb": (68,  192, 0),   "bricklink_id": "36"},
    {"name": "Green",               "rgb": (68,  143, 52),  "bricklink_id": "6"},
    {"name": "Dark Green",          "rgb": (0,   105, 47),  "bricklink_id": "80"},
    {"name": "Sand Green",          "rgb": (94,  135, 108), "bricklink_id": "48"},
    {"name": "Olive Green",         "rgb": (119, 119, 78),  "bricklink_id": "155"},
    # Blues
    {"name": "Sky Blue",            "rgb": (118, 180, 238), "bricklink_id": "87"},
    {"name": "Medium Blue",         "rgb": (70,  140, 198), "bricklink_id": "72"},
    {"name": "Blue",                "rgb": (13,  105, 171), "bricklink_id": "23"},
    {"name": "Dark Blue",           "rgb": (0,   32,  96),  "bricklink_id": "63"},
    # Purples
    {"name": "Medium Lavender",     "rgb": (172, 120, 186), "bricklink_id": "157"},
    {"name": "Dark Purple",         "rgb": (81,  13,  133), "bricklink_id": "89"},
]


def get_palette_rgb() -> np.ndarray:
    """Return an array of shape (N, 3) float64 with all palette RGB values."""
    return np.array([c["rgb"] for c in LEGO_COLORS], dtype=np.float64)
