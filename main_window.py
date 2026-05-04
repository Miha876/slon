"""Main application window."""
import argparse
import queue
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import CameraConfig
from camera_worker import CameraWorker
from styles import build_stylesheet
from ui_components import AdminPage, CameraCard, PasswordDialog, show_info
from utils import save_snapshot, open_snapshots_folder


class CameraGridWindow(QMainWindow):
    """Main application window showing 4 camera feeds."""

    def __init__(self, configs: list[CameraConfig]) -> None:
        super().__init__()
        self.setWindowTitle("Слон - видеомониторинг")
        self.resize(1100, 730)
        self.setMinimumSize(980, 640)
        self.admin_unlocked = False

        self.workers = [CameraWorker(config) for config in configs]
        self.cards = [
            CameraCard(position=position, camera_index=config.index)
            for position, config in enumerate(configs)
        ]

        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)

        root = QVBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_tabs())

        self.stack = QStackedWidget()
        self.operator_page = self._build_operator_page()
        self.admin_page = AdminPage(configs, self._log_admin_event)
        self.stack.addWidget(self.operator_page)
        self.stack.addWidget(self.admin_page)
        root.addWidget(self.stack, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self._refresh)

    def start(self) -> None:
        """Start all camera workers and refresh timer."""
        for worker in self.workers:
            worker.start()
        self.timer.start()

    def closeEvent(self, event) -> None:  # noqa: N802
        """Handle window close event."""
        self.timer.stop()
        for worker in self.workers:
            worker.stop()
        event.accept()

    def _build_tabs(self) -> QWidget:
        """Build tab navigation."""
        tabs = QFrame()
        tabs.setObjectName("tabs")

        self.operator_tab = QPushButton("Слон")
        self.operator_tab.setObjectName("tabActive")
        self.operator_tab.clicked.connect(self._show_operator)

        self.admin_tab = QPushButton("Админка")
        self.admin_tab.setObjectName("tabInactive")
        self.admin_tab.clicked.connect(self._request_admin)

        layout = QHBoxLayout(tabs)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.operator_tab)
        layout.addWidget(self.admin_tab)
        layout.addStretch()
        return tabs

    def _build_operator_page(self) -> QWidget:
        """Build operator main page."""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._build_camera_grid(), 1)
        layout.addWidget(self._build_sidebar())
        return page

    def _build_sidebar(self) -> QWidget:
        """Build right sidebar with controls."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)

        status_banner = QLabel("Камера недоступна")
        status_banner.setObjectName("statusBanner")
        status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        serial = QLabel("Серийный номер: н/д")
        serial.setObjectName("infoText")

        code = QLabel("Код модели:        н/д")
        code.setObjectName("infoText")

        signs = QLabel("Признаки")
        signs.setObjectName("sectionTitle")

        table = QTableWidget(3, 2)
        table.setObjectName("featuresTable")
        table.setHorizontalHeaderLabels(["Элемент", "Статус"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setShowGrid(False)
        table.setFixedHeight(192)

        for row, (name, value) in enumerate(
            [("Коробка", "Нет"), ("Датчик", "Нет"), ("Документ...", "Нет")]
        ):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(value))

        self.summary = QLabel("0 / 4 камер online")
        self.summary.setObjectName("summary")

        snapshot = QPushButton("Снимок")
        snapshot.setObjectName("snapshotButton")
        snapshot.clicked.connect(self._take_snapshot)

        open_folder = QPushButton("Открыть папку")
        open_folder.setObjectName("snapshotButton")
        open_folder.clicked.connect(self._open_screenshots_folder)

        error_report = QPushButton("Сообщить об ошибке")
        error_report.setObjectName("errorButton")
        error_report.clicked.connect(self._report_error)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(status_banner)
        layout.addWidget(serial)
        layout.addWidget(code)
        layout.addWidget(signs)
        layout.addWidget(table)
        layout.addWidget(self.summary)
        layout.addStretch()
        layout.addWidget(snapshot)
        layout.addWidget(open_folder)
        layout.addWidget(error_report)
        return sidebar

    def _build_camera_grid(self) -> QWidget:
        """Build 2x2 camera grid."""
        grid_host = QFrame()
        grid_host.setObjectName("videoPanel")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        for position, card in enumerate(self.cards):
            grid.addWidget(card, position // 2, position % 2)

        return grid_host

    def _show_operator(self) -> None:
        """Switch to operator page."""
        self.stack.setCurrentWidget(self.operator_page)
        self.operator_tab.setObjectName("tabActive")
        self.admin_tab.setObjectName("tabInactive")
        self._refresh_tab_styles()

    def _request_admin(self) -> None:
        """Request admin access with password."""
        if not self.admin_unlocked:
            dialog = PasswordDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.admin_unlocked = True
            self.admin_page.add_log("Вход администратора выполнен.")

        self.stack.setCurrentWidget(self.admin_page)
        self.operator_tab.setObjectName("tabInactive")
        self.admin_tab.setObjectName("tabActive")
        self._refresh_tab_styles()

    def _refresh_tab_styles(self) -> None:
        """Refresh tab button styles."""
        for tab in [self.operator_tab, self.admin_tab]:
            tab.style().unpolish(tab)
            tab.style().polish(tab)

    def _refresh(self) -> None:
        """Refresh video frames and status."""
        online_count = 0

        for index, worker in enumerate(self.workers):
            card = self.cards[index]

            if worker.is_online:
                online_count += 1

            card.update_status(worker.status, worker.is_online)

            try:
                frame = worker.frames.get_nowait()
            except queue.Empty:
                continue

            card.video.set_video_frame(frame)
            card.video.setText("")

        self.summary.setText(f"{online_count} / {len(self.workers)} камер online")

    def _take_snapshot(self) -> None:
        """Take snapshots from all cameras."""
        self._log_admin_event("Снимок выполнен.")
        show_info(self, "", "")

    def _open_screenshots_folder(self) -> None:
        """Open screenshots folder in file explorer."""
        open_snapshots_folder()
        self._log_admin_event("Папка со снимками открыта.")

    def _report_error(self) -> None:
        """Report an error."""
        self._log_admin_event("Ошибка сообщена.")
        show_info(self, "", "")

    def _log_admin_event(self, message: str) -> None:
        """Log event to admin page."""
        if hasattr(self, "admin_page"):
            self.admin_page.add_log(message)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Show 4 connected cameras in one modern window.")
    parser.add_argument(
        "--cameras",
        nargs=4,
        type=int,
        default=[0, 1, 2, 3],
        metavar=("CAM1", "CAM2", "CAM3", "CAM4"),
        help="Camera indexes to open. Default: 0 1 2 3",
    )
    parser.add_argument("--width", type=int, default=640, help="Requested camera width.")
    parser.add_argument("--height", type=int, default=480, help="Requested camera height.")
    parser.add_argument("--fps", type=int, default=30, help="Requested camera FPS.")
    return parser.parse_args()


def main() -> None:
    """Run the application."""
    args = parse_args()
    configs = [
        CameraConfig(index=camera, width=args.width, height=args.height, fps=args.fps)
        for camera in args.cameras
    ]

    app = QApplication(sys.argv)
    app.setApplicationName("Слон - видеомониторинг")
    app.setStyleSheet(build_stylesheet())
    app.setFont(QFont("Segoe UI Variable", 10))

    window = CameraGridWindow(configs)
    window.show()
    window.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
