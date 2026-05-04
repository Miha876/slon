"""Configuration and constants for the application."""
from dataclasses import dataclass


ADMIN_PASSWORD = "0098"


@dataclass
class CameraConfig:
    """Camera configuration parameters."""
    index: int
    width: int
    height: int
    fps: int
