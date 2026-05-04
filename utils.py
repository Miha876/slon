"""Utility functions for the application."""
import os
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from PySide6.QtGui import QImage


def get_snapshots_root() -> Path:
    """Get the root directory for snapshots on the system drive."""
    drive = Path.cwd().drive if Path.cwd().drive else "C:"
    snapshots_dir = Path(f"{drive}/Screenshots/Slon")
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    return snapshots_dir


def get_today_snapshots_dir() -> Path:
    """Get or create today's snapshots directory."""
    root = get_snapshots_root()
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = root / today
    today_dir.mkdir(parents=True, exist_ok=True)
    return today_dir


def save_snapshot(image: QImage, camera_index: int) -> str:
    """
    Save a snapshot with timestamp.
    
    Args:
        image: QImage from camera
        camera_index: Camera index number
        
    Returns:
        Path to saved file or error message
    """
    try:
        today_dir = get_today_snapshots_dir()
        timestamp = datetime.now().strftime("%H-%M-%S-%f")[:-3]  # HH-MM-SS-milliseconds
        filename = f"cam_{camera_index:02d}_{timestamp}.png"
        filepath = today_dir / filename
        
        # Convert QImage to OpenCV format
        width = image.width()
        height = image.height()
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)
        
        # Convert RGBA to BGR for OpenCV
        bgr_image = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        
        # Save the image
        cv2.imwrite(str(filepath), bgr_image)
        
        return str(filepath)
    except Exception as e:
        return f"Ошибка сохранения: {str(e)}"


def open_snapshots_folder() -> None:
    """Open the snapshots root directory in file explorer."""
    snapshots_dir = get_snapshots_root()
    if os.name == 'nt':  # Windows
        os.startfile(str(snapshots_dir))
    else:
        os.system(f"open {str(snapshots_dir)}")
