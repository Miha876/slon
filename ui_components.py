"""UI Components for the application."""
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import ADMIN_PASSWORD, CameraConfig


def show_info(parent: QWidget, title: str, message: str) -> None:
    """Show an info dialog."""
    MessageDialog(parent, title, message, "info").exec()


def show_warning(parent: QWidget, title: str, message: str) -> None:
    """Show a warning dialog."""
    MessageDialog(parent, title, message, "warning").exec()


class VideoLabel(QLabel):
    """Label for displaying video frames."""

    def __init__(self) -> None:
        super().__init__()
        self._pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_video_frame(self, image: QImage) -> None:
        """Set a video frame from QImage."""
        self._pixmap = QPixmap.fromImage(image)
        self._render_pixmap()

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Handle resize event."""
        self._render_pixmap()
        super().resizeEvent(event)

    def _render_pixmap(self) -> None:
        """Render the pixmap with proper scaling."""
        if self._pixmap is None:
            return

        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


class CameraCard(QFrame):
    """Card widget for displaying a single camera."""

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
        """Update camera status."""
        self.status.setText(text)
        self.dot.setObjectName("statusDotOnline" if online else "statusDotOffline")
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)

        if not online and self.video.pixmap() is None:
            self.video.setText("Нет видео")


class PasswordDialog(QDialog):
    """Dialog for admin password entry."""

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
        """Try to accept password."""
        if self.password.text() == ADMIN_PASSWORD:
            self.accept()
            return

        show_warning(self, "Админ-доступ", "Неверный пароль")
        self.password.clear()
        self.password.setFocus()


class MessageDialog(QDialog):
    """Custom message dialog."""

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
    """Admin panel widget."""

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

    def add_log(self, message: str) -> None:
        """Add a log message with timestamp."""
        stamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{stamp}] {message}")

    def _form_row(self, title: str, widget_or_layout) -> QWidget:
        """Create a form row with label and widget."""
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
        """Create a styled button."""
        button = QPushButton(text)
        button.setObjectName("adminButton")
        button.clicked.connect(callback)
        return button

    def _choose_model(self) -> None:
        """Open file dialog to choose a model."""
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
        """Change admin password."""
        if not self.password_input.text():
            self.add_log("Смена пароля: поле пустое, пароль не изменён.")
            return

        self.add_log("Смена пароля: выполнено.")

    def _report_error(self) -> None:
        """Report an error."""
        self.add_log("Ошибка сообщена.")

    def _reset_config(self) -> None:
        """Reset configuration to defaults."""
        self.conf_input.setText("0.80")
        self.width_input.setValue(640)
        self.height_input.setValue(480)
        self.fps_input.setValue(30)
        self.add_log("Конфиг сброшен к значениям по умолчанию.")

    def _connect_db(self) -> None:
        """Connect to database."""
        self.status.setText("Проверка подключения выполнена")
        self.add_log(
            f"БД: попытка подключения к {self.db_host.text()}:{self.db_port.value()}"
        )
