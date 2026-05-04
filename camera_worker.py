"""Camera worker thread for capturing video frames."""
import queue
import threading
import time
from typing import Optional

import cv2
from PySide6.QtGui import QImage

from config import CameraConfig


class CameraWorker:
    """Handles video capture from a single camera in a separate thread."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.frames: queue.Queue[QImage] = queue.Queue(maxsize=1)
        self.status = f"Камера {config.index}: запуск"
        self.is_online = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Start the camera worker thread."""
        self._thread.start()

    def stop(self) -> None:
        """Stop the camera worker thread."""
        self._stop.set()
        self._thread.join(timeout=2)

    def _open_capture(self) -> cv2.VideoCapture:
        """Open video capture with proper settings."""
        # DirectShow usually handles several USB cameras on Windows better than the default backend.
        capture = cv2.VideoCapture(self.config.index, cv2.CAP_DSHOW)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        capture.set(cv2.CAP_PROP_FPS, self.config.fps)
        return capture

    def _run(self) -> None:
        """Main worker loop."""
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
