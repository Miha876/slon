import argparse
import queue
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


ADMIN_PASSWORD = "0098"


def show_info(parent: QWidget, title: str, message: str) -> None:
    MessageDialog(parent, title, message, "info").exec()


def show_warning(parent: QWidget, title: str, message: str) -> None:
    MessageDialog(parent, title, message, "warning").exec()


@dataclass
class CameraConfig:
    index: int
    width: int
    height: int
    fps: int


class CameraWorker:
    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.frames: queue.Queue[QImage] = queue.Queue(maxsize=1)
        self.status = f"Камера {config.index}: запуск"
        self.is_online = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _open_capture(self) -> cv2.VideoCapture:
        # DirectShow usually handles several USB cameras on Windows better than the default backend.
        capture = cv2.VideoCapture(self.config.index, cv2.CAP_DSHOW)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        capture.set(cv2.CAP_PROP_FPS, self.config.fps)
        return capture

    def _run(self) -> None:
        capture: Optional[cv2.VideoCapture] = None

        while not self._stop.is_set():
            if capture is None or not capture.isOpened():
                self.is_online = False
                self.status = f"Камера {self.config.index}: подключение"
                capture = self._open_capture()

                if not capture.isOpened():
                    self.status = f"Камера {self.config.index}: недоступна"
                    capture.release()
                    capture = None
                    time.sleep(2)
                    continue

            ok, frame = capture.read()
            if not ok or frame is None:
                self.is_online = False
                self.status = f"Камера {self.config.index}: нет сигнала"
                capture.release()
                capture = None
                time.sleep(1)
                continue

            self.is_online = True
            self.status = f"Камера {self.config.index}: видео"
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_frame.shape
            bytes_per_line = channels * width
            image = QImage(
                rgb_frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            ).copy()

            if self.frames.full():
                try:
                    self.frames.get_nowait()
                except queue.Empty:
                    pass

            self.frames.put(image)

        if capture is not None:
            capture.release()


class VideoLabel(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self._pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_video_frame(self, image: QImage) -> None:
        self._pixmap = QPixmap.fromImage(image)
        self._render_pixmap()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._render_pixmap()
        super().resizeEvent(event)

    def _render_pixmap(self) -> None:
        if self._pixmap is None:
            return

        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


class CameraCard(QFrame):
    def __init__(self, position: int, camera_index: int) -> None:
        super().__init__()
        self.setObjectName("cameraCard")

        self.title = QLabel(f"CAM {position + 1}")
        self.title.setObjectName("cameraTitle")

        self.status = QLabel(f"Камера {camera_index}: запуск")
        self.status.setObjectName("cameraStatus")

        self.dot = QLabel()
        self.dot.setObjectName("statusDotOffline")
        self.dot.setFixedSize(10, 10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.dot)
        header.addWidget(self.status)

        self.video = VideoLabel()
        self.video.setObjectName("videoSurface")
        self.video.setText("Нет видео")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(self.video, 1)

    def update_status(self, text: str, online: bool) -> None:
        self.status.setText(text)
        self.dot.setObjectName("statusDotOnline" if online else "statusDotOffline")
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)

        if not online and self.video.pixmap() is None:
            self.video.setText("Нет видео")


class PasswordDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Админ-доступ")
        self.setModal(True)
        self.setFixedWidth(300)

        label = QLabel("Введите пароль:")
        label.setObjectName("dialogLabel")

        self.password = QLineEdit()
        self.password.setObjectName("passwordInput")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.returnPressed.connect(self._try_accept)

        ok = QPushButton("OK")
        ok.setObjectName("primaryButton")
        ok.clicked.connect(self._try_accept)

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(ok)
        buttons.addWidget(cancel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(label)
        layout.addWidget(self.password)
        layout.addLayout(buttons)

    def _try_accept(self) -> None:
        if self.password.text() == ADMIN_PASSWORD:
            self.accept()
            return

        show_warning(self, "Админ-доступ", "Неверный пароль")
        self.password.clear()
        self.password.setFocus()


class MessageDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, message: str, kind: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(430)
        self.setObjectName("messageDialog")

        accent = QLabel("!" if kind == "warning" else "i")
        accent.setObjectName("warningBadge" if kind == "warning" else "infoBadge")
        accent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        accent.setFixedSize(42, 42)

        heading = QLabel(title)
        heading.setObjectName("messageTitle")

        body = QLabel(message)
        body.setObjectName("messageBody")
        body.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        text_layout.addWidget(heading)
        text_layout.addWidget(body)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(14)
        content.addWidget(accent, 0, Qt.AlignmentFlag.AlignTop)
        content.addLayout(text_layout, 1)

        ok = QPushButton("Понятно")
        ok.setObjectName("messageButton")
        ok.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(ok)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        layout.addLayout(content)
        layout.addLayout(buttons)


class AdminPage(QWidget):
    def __init__(self, configs: list[CameraConfig], log_callback) -> None:
        super().__init__()
        self.log_callback = log_callback
        self.setObjectName("adminPage")

        self.camera_select = QComboBox()
        self.camera_select.setObjectName("adminInput")
        for config in configs:
            self.camera_select.addItem(f"Камера {config.index}", config.index)

        self.model_path = QLineEdit("C:/Metrean/models/metran_4cam.pt")
        self.model_path.setObjectName("adminInput")

        browse = QPushButton("...")
        browse.setObjectName("smallButton")
        browse.clicked.connect(self._choose_model)

        self.width_input = QSpinBox()
        self.width_input.setObjectName("adminInput")
        self.width_input.setRange(160, 4096)
        self.width_input.setValue(configs[0].width)

        self.height_input = QSpinBox()
        self.height_input.setObjectName("adminInput")
        self.height_input.setRange(120, 2160)
        self.height_input.setValue(configs[0].height)

        self.fps_input = QSpinBox()
        self.fps_input.setObjectName("adminInput")
        self.fps_input.setRange(1, 120)
        self.fps_input.setValue(configs[0].fps)

        self.conf_input = QLineEdit("0.80")
        self.conf_input.setObjectName("adminInput")

        self.password_input = QLineEdit()
        self.password_input.setObjectName("adminInput")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Новый пароль администратора")

        self.db_host = QLineEdit("localhost")
        self.db_port = QSpinBox()
        self.db_port.setObjectName("adminInput")
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(5432)
        self.db_name = QLineEdit("metran_validation")
        self.db_user = QLineEdit("postgres")
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_password.setText("postgres")

        for widget in [self.db_host, self.db_name, self.db_user, self.db_password]:
            widget.setObjectName("adminInput")

        self.status = QLabel("Нет подключения")
        self.status.setObjectName("adminStatus")

        self.logs = QTextEdit()
        self.logs.setObjectName("logs")
        self.logs.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self._form_row("Камера", self.camera_select))

        model_row = QHBoxLayout()
        model_row.setSpacing(6)
        model_row.addWidget(self.model_path, 1)
        model_row.addWidget(browse)
        layout.addWidget(self._form_row("Модель ИИ", model_row))

        size_row = QHBoxLayout()
        size_row.setSpacing(10)
        size_row.addWidget(self.width_input)
        size_row.addWidget(QLabel("W"))
        size_row.addWidget(self.height_input)
        size_row.addWidget(QLabel("H"))
        size_row.addWidget(self.fps_input)
        size_row.addWidget(QLabel("FPS"))
        layout.addWidget(self._form_row("Видео", size_row))

        layout.addWidget(self._form_row("Порог conf", self.conf_input))
        layout.addWidget(self._form_row("Новый пароль", self.password_input))
        layout.addWidget(self._button("Сменить пароль", self._change_password))
        layout.addWidget(self._button("Снять панику", self._clear_panic))
        layout.addWidget(self._button("Сбросить конфиг", self._reset_config))

        layout.addSpacing(6)
        layout.addWidget(self._form_row("DB Host", self.db_host))
        layout.addWidget(self._form_row("DB Port", self.db_port))
        layout.addWidget(self._form_row("DB Name", self.db_name))
        layout.addWidget(self._form_row("DB User", self.db_user))
        layout.addWidget(self._form_row("DB Password", self.db_password))
        layout.addWidget(self._button("Подключиться к БД", self._connect_db))
        layout.addWidget(self._form_row("Статус", self.status))
        layout.addWidget(QLabel("Логи"))
        layout.addWidget(self.logs, 1)

        self.add_log("Админка готова. Все действия пока работают как безопасные заглушки.")

    def add_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{stamp}] {message}")

    def _form_row(self, title: str, widget_or_layout) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setObjectName("adminLabel")
        label.setFixedWidth(120)
        layout.addWidget(label)

        if isinstance(widget_or_layout, QHBoxLayout):
            layout.addLayout(widget_or_layout, 1)
        else:
            layout.addWidget(widget_or_layout, 1)

        return row

    def _button(self, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("adminButton")
        button.clicked.connect(callback)
        return button

    def _choose_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите модель",
            "",
            "Model files (*.pt *.onnx *.engine);;All files (*.*)",
        )
        if path:
            self.model_path.setText(path)
            self.add_log(f"Выбрана модель: {path}")

    def _change_password(self) -> None:
        if not self.password_input.text():
            self.add_log("Смена пароля: поле пустое, пароль не изменён.")
            show_info(self, "Заглушка", "Введите новый пароль. Реальное сохранение пока не подключено.")
            return

        self.add_log("Смена пароля: заглушка выполнена, пароль в файл не записывался.")
        show_info(self, "Заглушка", "Пароль принят, но постоянное хранение пока не подключено.")

    def _clear_panic(self) -> None:
        self.add_log("Паника снята: заглушка.")
        self.log_callback("Паника снята из админки.")
        show_info(self, "Паника", "Паника снята. Это безопасная заглушка.")

    def _reset_config(self) -> None:
        self.conf_input.setText("0.80")
        self.width_input.setValue(640)
        self.height_input.setValue(480)
        self.fps_input.setValue(30)
        self.add_log("Конфиг сброшен к значениям по умолчанию.")

    def _connect_db(self) -> None:
        self.status.setText("Проверка подключения выполнена")
        self.add_log(
            f"БД: заглушка подключения к {self.db_host.text()}:{self.db_port.value()} / {self.db_name.text()}"
        )
        show_info(self, "База данных", "Подключение к БД пока работает как заглушка.")


class CameraGridWindow(QMainWindow):
    def __init__(self, configs: list[CameraConfig]) -> None:
        super().__init__()
        self.setWindowTitle("Жираф - камерная валидация")
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
        for worker in self.workers:
            worker.start()
        self.timer.start()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.timer.stop()
        for worker in self.workers:
            worker.stop()
        event.accept()

    def _build_tabs(self) -> QWidget:
        tabs = QFrame()
        tabs.setObjectName("tabs")

        self.operator_tab = QPushButton("Жираф")
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
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._build_camera_grid(), 1)
        layout.addWidget(self._build_sidebar())
        return page

    def _build_sidebar(self) -> QWidget:
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

        panic = QPushButton("ПАНИКА")
        panic.setObjectName("panicButton")
        panic.clicked.connect(self._panic)

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
        layout.addWidget(panic)
        return sidebar

    def _build_camera_grid(self) -> QWidget:
        grid_host = QFrame()
        grid_host.setObjectName("videoPanel")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        for position, card in enumerate(self.cards):
            grid.addWidget(card, position // 2, position % 2)

        return grid_host

    def _show_operator(self) -> None:
        self.stack.setCurrentWidget(self.operator_page)
        self.operator_tab.setObjectName("tabActive")
        self.admin_tab.setObjectName("tabInactive")
        self._refresh_tab_styles()

    def _request_admin(self) -> None:
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
        for tab in [self.operator_tab, self.admin_tab]:
            tab.style().unpolish(tab)
            tab.style().polish(tab)

    def _refresh(self) -> None:
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
        self._log_admin_event("Снимок: заглушка, файл не сохранялся.")
        show_info(self, "Снимок", "Снимок выполнен как заглушка. Сохранение файла можно подключить следующим шагом.")

    def _panic(self) -> None:
        self._log_admin_event("Нажата кнопка ПАНИКА.")
        show_warning(self, "ПАНИКА", "Паника активирована. Сейчас это безопасная заглушка.")

    def _log_admin_event(self, message: str) -> None:
        if hasattr(self, "admin_page"):
            self.admin_page.add_log(message)


def build_stylesheet() -> str:
    return """
        QWidget {
            color: #0f172a;
            font-family: "Segoe UI", "Segoe UI Variable";
        }

        #shell, #adminPage {
            background: #07529c;
        }

        #tabs {
            background: #074782;
            border-bottom: 1px solid rgba(255, 255, 255, 0.40);
            min-height: 40px;
            max-height: 40px;
        }

        #tabActive, #tabInactive {
            background: transparent;
            border: none;
            border-radius: 0;
            font-size: 15px;
            padding: 10px 8px 9px 8px;
            text-align: left;
        }

        #tabActive {
            color: #ffffff;
            border-bottom: 2px solid #ffffff;
        }

        #tabInactive {
            color: #9dc4ef;
        }

        #videoPanel {
            background: #0c121d;
            border-radius: 7px;
        }

        #cameraCard {
            background: #0c121d;
            border: 1px solid #111a29;
            border-radius: 5px;
        }

        #cameraCard:hover {
            border: 1px solid #2f6fb6;
        }

        #cameraTitle {
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
        }

        #cameraStatus {
            color: #95a3b8;
            font-size: 12px;
            font-weight: 500;
        }

        #videoSurface {
            background: #0c121d;
            border: none;
            border-radius: 0;
            color: #95a3b8;
            font-size: 14px;
        }

        #sidebar {
            background: #f1f4f8;
            border-radius: 8px;
            border: 4px solid #9fc4ee;
        }

        #statusBanner {
            background: #d4deec;
            border: 2px solid #b8c7dc;
            border-radius: 5px;
            color: #111827;
            font-size: 15px;
            font-weight: 700;
            min-height: 44px;
        }

        #adminPage #adminLabel,
        #dialogLabel {
            color: #f8fafc;
            font-size: 15px;
        }

        #sidebar #infoText, #sidebar #sectionTitle {
            color: #111827;
            font-size: 15px;
        }

        #featuresTable {
            background: #ffffff;
            border: none;
            color: #111827;
            font-size: 14px;
        }

        #featuresTable::item {
            padding-left: 10px;
            min-height: 30px;
        }

        QHeaderView::section {
            background: #d3deed;
            border: none;
            color: #111827;
            font-size: 12px;
            font-weight: 700;
            min-height: 38px;
        }

        #summary {
            color: #475569;
            font-size: 13px;
        }

        #snapshotButton, #adminButton, #primaryButton, #secondaryButton {
            background: #2e69bd;
            border: none;
            border-radius: 7px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            min-height: 38px;
            padding: 0 14px;
        }

        #snapshotButton:hover, #adminButton:hover, #primaryButton:hover, #secondaryButton:hover, #smallButton:hover {
            background: #3978cf;
        }

        #panicButton {
            background: #c91f25;
            border: none;
            border-radius: 7px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 800;
            min-height: 37px;
        }

        #panicButton:hover {
            background: #e12a30;
        }

        #adminInput, #passwordInput, QComboBox, QSpinBox {
            background: #134f8d;
            border: 1px solid #2b6fb3;
            border-radius: 5px;
            color: #ffffff;
            min-height: 27px;
            padding: 0 8px;
        }

        #adminInput:focus,
        #passwordInput:focus,
        QComboBox:focus,
        QSpinBox:focus {
            border: 1px solid #a7d8ff;
        }

        #smallButton {
            background: #2e69bd;
            border: none;
            border-radius: 5px;
            color: #ffffff;
            font-weight: 800;
            min-width: 34px;
            min-height: 27px;
        }

        #adminStatus {
            color: #d8e9ff;
            font-size: 15px;
        }

        #logs {
            background: #252525;
            border: 1px solid #3a3a3a;
            border-radius: 4px;
            color: #ffffff;
            font-family: Consolas, "Courier New";
            font-size: 12px;
        }

        QDialog {
            background: #1f1f24;
        }

        QDialog QLabel {
            color: #f8fafc;
            font-size: 14px;
        }

        QLineEdit::placeholder {
            color: #b8c7dc;
        }

        #messageDialog {
            background: #f8fafc;
        }

        #messageTitle {
            color: #0f172a;
            font-size: 17px;
            font-weight: 800;
        }

        #messageBody {
            color: #334155;
            font-size: 14px;
            line-height: 1.35;
        }

        #infoBadge {
            background: #2e69bd;
            border-radius: 21px;
            color: #ffffff;
            font-size: 22px;
            font-weight: 800;
        }

        #warningBadge {
            background: #f59e0b;
            border-radius: 21px;
            color: #111827;
            font-size: 22px;
            font-weight: 900;
        }

        #messageButton {
            background: #2e69bd;
            border: none;
            border-radius: 7px;
            color: #ffffff;
            font-size: 14px;
            font-weight: 800;
            min-width: 104px;
            min-height: 34px;
            padding: 0 16px;
        }

        #messageButton:hover {
            background: #3978cf;
        }

        #messageButton:pressed {
            background: #24549a;
        }

        #statusDotOnline {
            background: #22c55e;
            border-radius: 5px;
        }

        #statusDotOffline {
            background: #ef4444;
            border-radius: 5px;
        }
    """


def parse_args() -> argparse.Namespace:
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
    args = parse_args()
    configs = [
        CameraConfig(index=camera, width=args.width, height=args.height, fps=args.fps)
        for camera in args.cameras
    ]

    app = QApplication(sys.argv)
    app.setApplicationName("Жираф - камерная валидация")
    app.setStyleSheet(build_stylesheet())
    app.setFont(QFont("Segoe UI Variable", 10))

    window = CameraGridWindow(configs)
    window.show()
    window.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
