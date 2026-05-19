"""
PyQt6 MainWindow for the LEGO Mosaic Converter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageEnhance

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QRectF,
    QSize,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QBrush,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from lego_mosaic.lego_colors import LEGO_COLORS
from lego_mosaic.mosaic import build_color_grid, build_color_grid_by_size, count_colors
from lego_mosaic.export import (
    save_mosaic_image,
    export_bricklink_xml,
    PIECE_TILE,
    PIECE_PLATE,
    PIECE_ROUND,
    render_mosaic_image,
)

# 1 stud = 8 mm in real life
MM_PER_STUD: float = 8.0
CM_PER_IN:   float = 2.54

PIECE_OPTIONS: list[tuple[str, str]] = [
    ("3070 (1×1 Tile)",          PIECE_TILE),
    ("3024 (1×1 Plate)",         PIECE_PLATE),
    ("98138 (1×1 Round Plate)",  PIECE_ROUND),
]

PREVIEW_CELL_PX: int = 12   # pixels per stud in the live preview render


# ---------------------------------------------------------------------------
# Colour swatch label
# ---------------------------------------------------------------------------

class SwatchLabel(QLabel):
    """A small fixed-size label painted with a solid background colour."""

    def __init__(self, rgb: tuple[int, int, int], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        r, g, b = rgb
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            "border: 1px solid #555555; "
            "border-radius: 2px;"
        )


# ---------------------------------------------------------------------------
# Colour picker popup  (Win11-style floating list)
# ---------------------------------------------------------------------------

class ColorPopup(QWidget):
    """
    Frameless popup list of all LEGO colours.
    Emits *color_selected(idx)* and closes itself when a colour is clicked,
    or closes silently when the user clicks anywhere outside.
    """

    color_selected = pyqtSignal(int)
    dismissed      = pyqtSignal()

    _ROW_H    = 28
    _WIDTH    = 220
    _MAX_ROWS = 12

    def __init__(self, current_idx: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Visible card
        card = QFrame(self)
        card.setObjectName("card")
        card.setStyleSheet(
            "QFrame#card {"
            "  background-color: #1f1f1f;"
            "  border: 1px solid #3a3a3a;"
            "  border-radius: 8px;"
            "}"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)   # shadow margin
        root_layout.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 5px; border: none; }"
            "QScrollBar::handle:vertical { background: #4a4a4a; border-radius: 2px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(1)

        self._rows: list[QWidget] = []
        for i, colour in enumerate(LEGO_COLORS):
            row = self._make_row(i, colour, i == current_idx)
            vbox.addWidget(row)
            self._rows.append(row)

        scroll.setWidget(container)
        n_vis = min(len(LEGO_COLORS), self._MAX_ROWS)
        scroll.setFixedWidth(self._WIDTH)
        scroll.setFixedHeight(n_vis * self._ROW_H)
        card_layout.addWidget(scroll)

        self.adjustSize()

        if current_idx < len(self._rows):
            scroll.ensureWidgetVisible(self._rows[current_idx])

    def _make_row(self, idx: int, colour: dict, is_current: bool) -> QWidget:
        r, g, b = colour["rgb"]
        row = QWidget()
        row.setFixedHeight(self._ROW_H)
        row.setAttribute(Qt.WidgetAttribute.WA_Hover)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_current:
            row.setStyleSheet(
                "QWidget { background-color: #0060c0; border-radius: 4px; }"
            )
        else:
            row.setStyleSheet(
                "QWidget { background-color: transparent; border-radius: 4px; }"
                "QWidget:hover { background-color: #2d2d2d; }"
            )

        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(9)

        swatch = QLabel()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            "border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 2px; background: transparent;"   # override parent
        )
        swatch.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            "border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 2px;"
        )

        name_lbl = QLabel(colour["name"])
        name_lbl.setStyleSheet(
            f"color: {'#ffffff' if is_current else '#cccccc'}; "
            "font-size: 11px; background: transparent;"
        )

        layout.addWidget(swatch)
        layout.addWidget(name_lbl)
        layout.addStretch()

        row.mousePressEvent = lambda _e, i=idx: self._select(i)
        return row

    def _select(self, idx: int) -> None:
        self.color_selected.emit(idx)
        self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.dismissed.emit()
        super().closeEvent(event)

    def popup_at(self, global_pos) -> None:
        """Show near *global_pos*, nudging inward if it would go off-screen."""
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        x = min(global_pos.x(), screen.right()  - self.width())
        y = min(global_pos.y(), screen.bottom() - self.height())
        self.move(max(screen.left(), x), max(screen.top(), y))
        self.show()


# ---------------------------------------------------------------------------
# Clickable breakdown row
# ---------------------------------------------------------------------------

class ClickableRow(QWidget):
    """A breakdown row that emits *clicked(color_idx)* on left-press."""

    clicked = pyqtSignal(int)

    def __init__(self, color_idx: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color_idx = color_idx
        self._pending = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background-color: transparent;")

    def set_pending(self, active: bool) -> None:
        self._pending = active
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._color_idx)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        if not self._pending:
            self.setStyleSheet("background-color: #3a3a3a;")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._apply_style()
        super().leaveEvent(event)

    def _apply_style(self) -> None:
        if self._pending:
            self.setStyleSheet("background-color: #0060c0; border-radius: 4px;")
        else:
            self.setStyleSheet("background-color: transparent;")


# ---------------------------------------------------------------------------
# Resizable preview label
# ---------------------------------------------------------------------------

class PreviewLabel(QLabel):
    """
    QLabel that keeps the mosaic pixmap centred and scaled to fit, without
    distorting aspect ratio, whenever it is resized.
    """

    tile_clicked = pyqtSignal(int, int)  # row, col

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._source_pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)
        self.setStyleSheet("background-color: #2b2b2b;")
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_mosaic_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self._source_pixmap = pixmap
        self._refresh()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return
        pw = self._source_pixmap.width()
        ph = self._source_pixmap.height()
        lw = self.width()
        lh = self.height()
        scale = min(lw / pw, lh / ph)
        scaled_w = pw * scale
        scaled_h = ph * scale
        offset_x = (lw - scaled_w) / 2
        offset_y = (lh - scaled_h) / 2
        cx = event.pos().x() - offset_x
        cy = event.pos().y() - offset_y
        if cx < 0 or cy < 0 or cx >= scaled_w or cy >= scaled_h:
            return
        col = int(cx / scale) // PREVIEW_CELL_PX
        row = int(cy / scale) // PREVIEW_CELL_PX
        self.tile_clicked.emit(row, col)

    def _refresh(self) -> None:
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.setPixmap(scaled)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.source_image: Optional[Image.Image] = None
        self.color_grid: Optional[np.ndarray] = None
        self._pending_tile: Optional[tuple[int, int]] = None
        self._breakdown_rows: dict[int, ClickableRow] = {}
        self._syncing: bool = False

        # Debounce timer — recompute 100 ms after the last control change
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(100)
        self._debounce_timer.timeout.connect(self._recompute)

        self._build_ui()
        self._set_controls_enabled(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Toolbar ────────────────────────────────────────────────────
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar { background: #3c3f41; border: none; padding: 4px 8px; spacing: 6px; }"
        )
        self.addToolBar(toolbar)

        self.btn_load = QPushButton("Load Image")
        self.btn_save = QPushButton("Save Mosaic")
        self.btn_xml  = QPushButton("Export XML")

        for btn in (self.btn_load, self.btn_save, self.btn_xml):
            btn.setFixedHeight(32)
            btn.setStyleSheet(
                "QPushButton {"
                "  background-color: #4e9a6f;"
                "  color: white;"
                "  border: none;"
                "  border-radius: 4px;"
                "  padding: 0 14px;"
                "  font-weight: bold;"
                "}"
                "QPushButton:hover { background-color: #5cb87f; }"
                "QPushButton:pressed { background-color: #3d7a57; }"
                "QPushButton:disabled { background-color: #555555; color: #888888; }"
            )

        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_xml)

        self.btn_load.clicked.connect(self.on_load_image)
        self.btn_save.clicked.connect(self.on_save_mosaic)
        self.btn_xml.clicked.connect(self.on_export_xml)

        # ── Central widget (left preview + right controls) ─────────────
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background-color: #2b2b2b; color: #e0e0e0;")

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Left: preview ──────────────────────────────────────────────
        self.preview_label = PreviewLabel()

        self.placeholder_label = QLabel("Load an image to begin")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(
            "color: #777777; font-size: 18px; background-color: #2b2b2b;"
        )
        self.placeholder_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Stack preview + placeholder in a single widget
        preview_container = QWidget()
        preview_container.setStyleSheet("background-color: #2b2b2b;")
        preview_stack = QVBoxLayout(preview_container)
        preview_stack.setContentsMargins(0, 0, 0, 0)
        preview_stack.addWidget(self.preview_label)
        preview_stack.addWidget(self.placeholder_label)
        self.preview_label.hide()

        main_layout.addWidget(preview_container, stretch=1)

        # ── Divider ────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFixedWidth(1)
        divider.setStyleSheet("color: #444444;")
        main_layout.addWidget(divider)

        # ── Right: controls panel ──────────────────────────────────────
        right_panel = QWidget()
        right_panel.setFixedWidth(290)
        right_panel.setStyleSheet(
            "QWidget { background-color: #313335; color: #e0e0e0; }"
            "QLabel { background-color: transparent; }"
        )
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        main_layout.addWidget(right_panel)

        # --- Stud size slider ---
        right_layout.addWidget(self._section_label("Stud size"))
        stud_row = QHBoxLayout()
        self.stud_slider = QSlider(Qt.Orientation.Horizontal)
        self.stud_slider.setRange(4, 64)
        self.stud_slider.setValue(16)
        self.stud_slider.setSingleStep(2)
        self.stud_slider.setPageStep(4)
        self.stud_slider.setTickInterval(8)
        self.stud_value_label = QLabel("16 px")
        self.stud_value_label.setFixedWidth(44)
        self.stud_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        stud_row.addWidget(self.stud_slider)
        stud_row.addWidget(self.stud_value_label)
        right_layout.addLayout(stud_row)

        # --- Width in studs spinbox ---
        right_layout.addWidget(self._section_label("Width (studs)"))
        studs_row = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 9999)
        self.width_spin.setValue(50)
        self.width_spin.setFixedHeight(28)
        self.width_spin.setStyleSheet(
            "QSpinBox {"
            "  background-color: #45494a; color: #e0e0e0;"
            "  border: 1px solid #555; border-radius: 3px; padding: 2px 4px;"
            "}"
            "QSpinBox::up-button, QSpinBox::down-button { width: 16px; }"
        )
        self.width_spin_hint = QLabel("")
        self.width_spin_hint.setStyleSheet("color: #777777; font-size: 10px;")
        self.width_spin_hint.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        studs_row.addWidget(self.width_spin)
        studs_row.addWidget(self.width_spin_hint)
        right_layout.addLayout(studs_row)

        # --- Colour count slider ---
        right_layout.addWidget(self._section_label("Max colours"))
        color_row = QHBoxLayout()
        self.color_slider = QSlider(Qt.Orientation.Horizontal)
        self.color_slider.setRange(2, 30)
        self.color_slider.setValue(12)
        self.color_slider.setSingleStep(1)
        self.color_slider.setPageStep(5)
        self.color_value_label = QLabel("12")
        self.color_value_label.setFixedWidth(44)
        self.color_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        color_row.addWidget(self.color_slider)
        color_row.addWidget(self.color_value_label)
        right_layout.addLayout(color_row)

        # --- Brightness slider ---
        right_layout.addWidget(self._section_label("Brightness"))
        brightness_row = QHBoxLayout()
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(50, 150)
        self.brightness_slider.setValue(100)
        self.brightness_slider.setSingleStep(1)
        self.brightness_slider.setPageStep(10)
        self.brightness_value_label = QLabel("100%")
        self.brightness_value_label.setFixedWidth(44)
        self.brightness_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        brightness_row.addWidget(self.brightness_slider)
        brightness_row.addWidget(self.brightness_value_label)
        right_layout.addLayout(brightness_row)

        # --- Contrast slider ---
        right_layout.addWidget(self._section_label("Contrast"))
        contrast_row = QHBoxLayout()
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(50, 150)
        self.contrast_slider.setValue(100)
        self.contrast_slider.setSingleStep(1)
        self.contrast_slider.setPageStep(10)
        self.contrast_value_label = QLabel("100%")
        self.contrast_value_label.setFixedWidth(44)
        self.contrast_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        contrast_row.addWidget(self.contrast_slider)
        contrast_row.addWidget(self.contrast_value_label)
        right_layout.addLayout(contrast_row)

        # --- Piece type ---
        right_layout.addWidget(self._section_label("Piece type"))
        self.piece_combo = QComboBox()
        self.piece_combo.setStyleSheet(
            "QComboBox { background-color: #45494a; border: 1px solid #555; "
            "border-radius: 3px; padding: 3px 6px; color: #e0e0e0; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #45494a; color: #e0e0e0; "
            "selection-background-color: #4e9a6f; }"
        )
        for label, _ in PIECE_OPTIONS:
            self.piece_combo.addItem(label)
        right_layout.addWidget(self.piece_combo)

        # --- Grid lines checkbox ---
        self.grid_check = QCheckBox("Show grid lines")
        self.grid_check.setChecked(True)
        self.grid_check.setStyleSheet(
            "QCheckBox { spacing: 6px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
        )
        right_layout.addWidget(self.grid_check)

        # --- Separator ---
        right_layout.addWidget(self._hline())

        # --- Size info ---
        self.size_label = QLabel("Size: — × — studs")
        self.size_label.setWordWrap(True)
        self.cm_label   = QLabel("— × — cm  (— × — in)")
        self.cm_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        right_layout.addWidget(self.size_label)
        right_layout.addWidget(self.cm_label)

        # --- Separator ---
        right_layout.addWidget(self._hline())

        # --- Colour breakdown ---
        right_layout.addWidget(self._section_label("Colour Breakdown"))
        self.breakdown_scroll = QScrollArea()
        self.breakdown_scroll.setWidgetResizable(True)
        self.breakdown_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.breakdown_scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #444444; border-radius: 4px; background-color: #2b2b2b; }"
            "QScrollBar:vertical { background: #2b2b2b; width: 8px; }"
            "QScrollBar::handle:vertical { background: #555555; border-radius: 3px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )
        self.breakdown_inner = QWidget()
        self.breakdown_inner.setStyleSheet("background-color: #2b2b2b;")
        self.breakdown_layout = QVBoxLayout(self.breakdown_inner)
        self.breakdown_layout.setContentsMargins(6, 6, 6, 6)
        self.breakdown_layout.setSpacing(4)
        self.breakdown_layout.addStretch(1)
        self.breakdown_scroll.setWidget(self.breakdown_inner)
        right_layout.addWidget(self.breakdown_scroll, stretch=1)

        # ── Slider style sheet ─────────────────────────────────────────
        slider_style = (
            "QSlider::groove:horizontal {"
            "  height: 4px; background: #555555; border-radius: 2px;}"
            "QSlider::handle:horizontal {"
            "  background: #4e9a6f; border: none;"
            "  width: 14px; height: 14px; margin: -5px 0;"
            "  border-radius: 7px;}"
            "QSlider::sub-page:horizontal {"
            "  background: #4e9a6f; border-radius: 2px;}"
            "QSlider:disabled::groove:horizontal { background: #444444; }"
            "QSlider:disabled::handle:horizontal { background: #666666; }"
            "QSlider:disabled::sub-page:horizontal { background: #444444; }"
        )
        self.stud_slider.setStyleSheet(slider_style)
        self.color_slider.setStyleSheet(slider_style)
        self.brightness_slider.setStyleSheet(slider_style)
        self.contrast_slider.setStyleSheet(slider_style)

        # ── Signal connections ─────────────────────────────────────────
        self.stud_slider.valueChanged.connect(self._on_stud_slider_changed)
        self.color_slider.valueChanged.connect(self._on_color_slider_changed)
        self.brightness_slider.valueChanged.connect(self._on_brightness_slider_changed)
        self.contrast_slider.valueChanged.connect(self._on_contrast_slider_changed)
        self.width_spin.valueChanged.connect(self._on_width_studs_changed)
        self.piece_combo.currentIndexChanged.connect(self.on_controls_changed)
        self.grid_check.stateChanged.connect(self.on_controls_changed)
        self.preview_label.tile_clicked.connect(self.on_tile_clicked)

    # ------------------------------------------------------------------
    # Helper widget factories
    # ------------------------------------------------------------------

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        lbl.setFont(font)
        lbl.setStyleSheet("color: #aaaaaa; background-color: transparent;")
        return lbl

    @staticmethod
    def _hline() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("color: #444444; background-color: #444444;")
        return line

    # ------------------------------------------------------------------
    # Control enable / disable
    # ------------------------------------------------------------------

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.btn_save.setEnabled(enabled)
        self.btn_xml.setEnabled(enabled)
        self.stud_slider.setEnabled(enabled)
        self.width_spin.setEnabled(enabled)
        self.color_slider.setEnabled(enabled)
        self.brightness_slider.setEnabled(enabled)
        self.contrast_slider.setEnabled(enabled)
        self.piece_combo.setEnabled(enabled)
        self.grid_check.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Slot: slider value display updates + debounce
    # ------------------------------------------------------------------

    def _on_stud_slider_changed(self, value: int) -> None:
        self.stud_value_label.setText(f"{value} px")
        if self.source_image is not None and not self._syncing:
            self._syncing = True
            cols = max(1, self.source_image.width // value)
            self.width_spin.setValue(cols)
            self._syncing = False
        self.on_controls_changed()

    def _on_width_studs_changed(self, value: int) -> None:
        if self.source_image is not None and not self._syncing:
            self._syncing = True
            w = self.source_image.width
            stud_px = max(1, w // value)
            stud_px = max(self.stud_slider.minimum(), min(self.stud_slider.maximum(), stud_px))
            self.stud_slider.setValue(stud_px)
            self.stud_value_label.setText(f"{stud_px} px")
            self._syncing = False
        self.on_controls_changed()

    def _on_color_slider_changed(self, value: int) -> None:
        self.color_value_label.setText(str(value))
        self.on_controls_changed()

    def _on_brightness_slider_changed(self, value: int) -> None:
        self.brightness_value_label.setText(f"{value}%")
        self.on_controls_changed()

    def _on_contrast_slider_changed(self, value: int) -> None:
        self.contrast_value_label.setText(f"{value}%")
        self.on_controls_changed()

    def on_controls_changed(self) -> None:
        """Schedule a recompute after a short debounce delay."""
        self._debounce_timer.start()

    # ------------------------------------------------------------------
    # Image adjustment helper
    # ------------------------------------------------------------------

    def _adjusted_image(self) -> Image.Image:
        img = self.source_image
        brightness = self.brightness_slider.value() / 100.0
        contrast   = self.contrast_slider.value()   / 100.0
        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
        return img

    # ------------------------------------------------------------------
    # Core recompute
    # ------------------------------------------------------------------

    def _recompute(self) -> None:
        if self.source_image is None:
            return
        num_colors = self.color_slider.value()
        target_cols = self.width_spin.value()
        self.color_grid = build_color_grid_by_size(self._adjusted_image(), target_cols, num_colors)
        self._refresh_view()

    def _refresh_view(self) -> None:
        """Re-render the preview and breakdown from the current color_grid."""
        if self.color_grid is None:
            return
        rows, cols = self.color_grid.shape
        _, piece_code = PIECE_OPTIONS[self.piece_combo.currentIndex()]
        draw_grid = self.grid_check.isChecked()

        self.size_label.setText(f"Size: {cols} × {rows} studs")
        w_cm = cols * MM_PER_STUD / 10.0
        h_cm = rows * MM_PER_STUD / 10.0
        w_in = w_cm / CM_PER_IN
        h_in = h_cm / CM_PER_IN
        self.cm_label.setText(
            f"{w_cm:.1f} × {h_cm:.1f} cm  ({w_in:.1f} × {h_in:.1f} in)"
        )
        self.width_spin_hint.setText(f"→ {w_cm:.1f} cm / {w_in:.1f} in wide")

        pixmap = self._render_preview(self.color_grid, piece_code, draw_grid)
        self.preview_label.set_mosaic_pixmap(pixmap)
        self._rebuild_breakdown(self.color_grid)

    # ------------------------------------------------------------------
    # QPainter-based mosaic renderer
    # ------------------------------------------------------------------

    def _render_preview(
        self,
        color_grid: np.ndarray,
        piece_type: str,
        draw_grid: bool,
    ) -> QPixmap:
        rows, cols = color_grid.shape
        cell = PREVIEW_CELL_PX
        img_w = cols * cell
        img_h = rows * cell

        pixmap = QPixmap(img_w, img_h)
        pixmap.fill(QColor(40, 40, 40))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, piece_type == PIECE_ROUND)

        for r in range(rows):
            for c in range(cols):
                idx = int(color_grid[r, c])
                rgb = LEGO_COLORS[idx]["rgb"]
                qcolor = QColor(rgb[0], rgb[1], rgb[2])

                x = c * cell
                y = r * cell

                if piece_type == PIECE_ROUND:
                    self._draw_round(painter, x, y, cell, qcolor, draw_grid)
                elif piece_type == PIECE_PLATE:
                    self._draw_plate(painter, x, y, cell, qcolor, draw_grid)
                else:
                    self._draw_tile(painter, x, y, cell, qcolor, draw_grid)

        if self._pending_tile is not None:
            pr, pc = self._pending_tile
            if 0 <= pr < rows and 0 <= pc < cols:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                pen = QPen(QColor(255, 255, 255, 230), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(pc * cell + 1, pr * cell + 1, cell - 2, cell - 2)

        painter.end()
        return pixmap

    def _draw_tile(
        self,
        painter: QPainter,
        x: int, y: int, cell: int,
        color: QColor,
        draw_grid: bool,
    ) -> None:
        """3070b: filled rect with 1 px dark border, radius 1."""
        painter.setBrush(QBrush(color))
        if draw_grid:
            painter.setPen(QPen(QColor(40, 40, 40, 160), 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(x + 0.5, y + 0.5, cell - 1, cell - 1)
        painter.drawRoundedRect(rect, 1.0, 1.0)

    def _draw_plate(
        self,
        painter: QPainter,
        x: int, y: int, cell: int,
        color: QColor,
        draw_grid: bool,
    ) -> None:
        """3024: filled rect with a white inner border (thicker edge feel)."""
        # Fill
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(x, y, cell, cell)

        if draw_grid:
            border_w = max(1, cell // 10)
            pen = QPen(QColor(255, 255, 255, 100), border_w)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            half = border_w / 2.0
            painter.drawRect(
                QRectF(x + half, y + half, cell - border_w, cell - border_w)
            )

    def _draw_round(
        self,
        painter: QPainter,
        x: int, y: int, cell: int,
        color: QColor,
        draw_grid: bool,
    ) -> None:
        """98138: filled circle within the cell."""
        margin = max(1, cell // 8)
        painter.setBrush(QBrush(color))
        if draw_grid:
            painter.setPen(QPen(QColor(40, 40, 40, 180), 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(x + margin, y + margin, cell - 2 * margin, cell - 2 * margin)
        painter.drawEllipse(rect)

    # ------------------------------------------------------------------
    # Colour breakdown list
    # ------------------------------------------------------------------

    def _rebuild_breakdown(self, color_grid: np.ndarray) -> None:
        counts = count_colors(color_grid)
        total = int(color_grid.size)

        self._breakdown_rows.clear()

        # Clear existing rows (but keep the trailing stretch)
        while self.breakdown_layout.count() > 1:
            item = self.breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, count in counts.items():
            colour = LEGO_COLORS[idx]
            pct = 100.0 * count / total if total > 0 else 0.0

            row_widget = ClickableRow(idx)
            row_widget.clicked.connect(self.on_color_replace)
            self._breakdown_rows[idx] = row_widget
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(2, 1, 2, 1)
            row_layout.setSpacing(6)

            swatch = SwatchLabel(colour["rgb"])
            name_lbl = QLabel(colour["name"])
            name_lbl.setStyleSheet("font-size: 10px; color: #dddddd;")
            name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            count_lbl = QLabel(str(count))
            count_lbl.setStyleSheet("font-size: 10px; color: #aaaaaa;")
            count_lbl.setFixedWidth(36)
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            pct_lbl = QLabel(f"{pct:.0f}%")
            pct_lbl.setStyleSheet("font-size: 10px; color: #777777;")
            pct_lbl.setFixedWidth(30)
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row_layout.addWidget(swatch)
            row_layout.addWidget(name_lbl)
            row_layout.addWidget(count_lbl)
            row_layout.addWidget(pct_lbl)

            # Insert before the trailing stretch
            self.breakdown_layout.insertWidget(
                self.breakdown_layout.count() - 1, row_widget
            )

    # ------------------------------------------------------------------
    # Colour editing handlers
    # ------------------------------------------------------------------

    def _refresh_preview_pixmap(self) -> None:
        """Re-render just the preview pixmap (no breakdown rebuild)."""
        if self.color_grid is None:
            return
        _, piece_code = PIECE_OPTIONS[self.piece_combo.currentIndex()]
        draw_grid = self.grid_check.isChecked()
        pixmap = self._render_preview(self.color_grid, piece_code, draw_grid)
        self.preview_label.set_mosaic_pixmap(pixmap)

    def _clear_pending_highlight(self) -> None:
        """Remove all pending highlights from tile and breakdown row."""
        self._pending_tile = None
        for row_widget in self._breakdown_rows.values():
            row_widget.set_pending(False)
        self._refresh_preview_pixmap()

    def on_color_replace(self, old_idx: int) -> None:
        """Replace every tile of *old_idx* with a user-chosen colour."""
        if self.color_grid is None:
            return
        if old_idx in self._breakdown_rows:
            self._breakdown_rows[old_idx].set_pending(True)
        self._color_popup = ColorPopup(old_idx, self)
        self._color_popup.color_selected.connect(
            lambda new_idx: self._apply_color_replace(old_idx, new_idx)
        )
        self._color_popup.dismissed.connect(self._clear_pending_highlight)
        self._color_popup.popup_at(QCursor.pos())

    def _apply_color_replace(self, old_idx: int, new_idx: int) -> None:
        if self.color_grid is None or new_idx == old_idx:
            return
        self.color_grid[self.color_grid == old_idx] = new_idx
        self._refresh_view()

    def on_tile_clicked(self, row: int, col: int) -> None:
        """Replace the colour of a single tile."""
        if self.color_grid is None:
            return
        rows, cols = self.color_grid.shape
        if not (0 <= row < rows and 0 <= col < cols):
            return
        current_idx = int(self.color_grid[row, col])
        self._pending_tile = (row, col)
        self._refresh_preview_pixmap()
        self._color_popup = ColorPopup(current_idx, self)
        self._color_popup.color_selected.connect(
            lambda new_idx, r=row, c=col: self._apply_tile_color(r, c, new_idx)
        )
        self._color_popup.dismissed.connect(self._clear_pending_highlight)
        self._color_popup.popup_at(QCursor.pos())

    def _apply_tile_color(self, row: int, col: int, new_idx: int) -> None:
        if self.color_grid is None:
            return
        if new_idx == int(self.color_grid[row, col]):
            return
        self.color_grid[row, col] = new_idx
        self._refresh_view()

    # ------------------------------------------------------------------
    # Toolbar button handlers
    # ------------------------------------------------------------------

    def on_load_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if not path:
            return

        try:
            self.source_image = Image.open(path).convert("RGB")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open image:\n{exc}")
            return

        # Initialise the width spinbox from the current stud slider value.
        w, h = self.source_image.size
        init_cols = max(1, w // self.stud_slider.value())
        self._syncing = True
        self.width_spin.setRange(1, w)
        self.width_spin.setValue(init_cols)
        self._syncing = False

        self.placeholder_label.hide()
        self.preview_label.show()
        self._set_controls_enabled(True)
        self.on_controls_changed()

    def on_save_mosaic(self) -> None:
        if self.color_grid is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Mosaic PNG",
            "mosaic.png",
            "PNG Images (*.png);;All Files (*)",
        )
        if not path:
            return

        _, piece_code = PIECE_OPTIONS[self.piece_combo.currentIndex()]
        draw_grid = self.grid_check.isChecked()

        try:
            save_mosaic_image(
                self.color_grid,
                piece_code,
                path,
                cell_size=20,
                draw_grid=draw_grid,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not save image:\n{exc}")
            return

        QMessageBox.information(self, "Saved", f"Mosaic saved to:\n{path}")

    def on_export_xml(self) -> None:
        if self.color_grid is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export BrickLink Wanted List XML",
            "wanted_list.xml",
            "XML Files (*.xml);;All Files (*)",
        )
        if not path:
            return

        _, piece_code = PIECE_OPTIONS[self.piece_combo.currentIndex()]

        try:
            export_bricklink_xml(self.color_grid, piece_code, path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not export XML:\n{exc}")
            return

        QMessageBox.information(self, "Exported", f"BrickLink XML saved to:\n{path}")
