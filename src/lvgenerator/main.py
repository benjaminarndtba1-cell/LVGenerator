import sys

from PySide6.QtWidgets import QApplication

from lvgenerator.controllers.main_controller import MainController
from lvgenerator.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LVGenerator")
    app.setOrganizationName("LVGenerator")

    window = MainWindow()
    controller = MainController(window)  # noqa: F841 - must stay alive
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
