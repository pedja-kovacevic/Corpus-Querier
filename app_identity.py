"""Shared application identity, version and icon helpers."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image


APP_NAME = "Corpus Querier"
APP_VERSION = "3.0.1"


def resource_path(relative_path: str) -> Path:
    """Resolve an asset both from source and from a PyInstaller bundle."""

    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / relative_path


def apply_window_icon(window: tk.Misc) -> None:
    """Apply the shared icon to a Tk/CustomTkinter top-level window."""

    try:
        icon = tk.PhotoImage(file=str(resource_path("assets/corpus-querier.png")))
        window.iconphoto(True, icon)
        window._corpus_querier_icon = icon  # Keep the Tk image alive.
    except (OSError, tk.TclError):
        # The executable and installer still carry their native embedded icon.
        pass


def load_brand_image(size: tuple[int, int]) -> ctk.CTkImage:
    """Return the shared transparent mark for in-app branding."""

    image = Image.open(resource_path("assets/corpus-querier.png"))
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)
