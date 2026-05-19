"""
Entry point for the LEGO Mosaic Converter.

Usage:
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

from lego_mosaic.app import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.setWindowTitle("LEGO Mosaic Converter")
    window.resize(1100, 700)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
