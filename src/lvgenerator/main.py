import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from lvgenerator.controllers.main_controller import MainController
from lvgenerator.views.main_window import MainWindow


def _load_dark_theme(app: QApplication) -> None:
    """Load the VS Code-inspired dark theme."""
    qss_path = Path(__file__).parent / "resources" / "styles" / "dark.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # QPalette for native dialogs
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#cccccc"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#252526"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2a2d2e"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3c3c3c"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#cccccc"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#264f78"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#252526"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#cccccc"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6e6e6e"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#0078d4"))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor("#0078d4"))

    # Disabled colors
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#6e6e6e")
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#6e6e6e")
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#6e6e6e")
    )

    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LVGenerator")
    app.setOrganizationName("LVGenerator")

    _load_dark_theme(app)

    window = MainWindow()
    controller = MainController(window)  # noqa: F841 - must stay alive
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
