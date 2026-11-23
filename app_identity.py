"""Shared application identity, version and icon helpers."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageChops, ImageDraw


APP_NAME = "Corpus Querier"
APP_VERSION = "3.1.0"


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


def _load_bird_layer() -> Image.Image:
    """Extract the bird from the shared mark while preserving its exact design."""

    image = Image.open(resource_path("assets/corpus-querier.png")).convert("RGBA")
    width, height = image.size

    # The platform is redrawn by the widget so it can remain still while the
    # bird moves. Keep the complete bird body and the beak that crosses the
    # platform boundary.
    keep = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(keep)
    draw.rectangle((0, 0, width, int(height * 0.687)), fill=255)
    beak_points = [
        (int(width * 0.588), int(height * 0.553)),
        (int(width * 0.700), int(height * 0.566)),
        (int(width * 0.616), int(height * 0.790)),
    ]
    draw.polygon(beak_points, fill=255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), keep))
    # Redraw the beak inside the retained triangle. In the source mark its tip
    # touches the highlighted corpus point, so those two orange shapes share a
    # few pixels. A clean triangle prevents the static point from moving with
    # the bird when the two layers are separated for animation.
    ImageDraw.Draw(image).polygon(beak_points, fill=(255, 174, 0, 255))
    return image.crop(
        (
            int(width * 0.115),
            int(height * 0.075),
            int(width * 0.790),
            int(height * 0.825),
        )
    )


class PeckingBird(ctk.CTkFrame):
    """A restrained in-app animation built from the shared data-bird mark."""

    WIDTH = 210
    HEIGHT = 205
    _REST_Y = 12
    _CONTACT_Y = 24
    _FRAME_DELAY_MS = 82
    _POSITIONS = (10, 10, 11, 13, 16, 20, 24, 24, 21, 18, 15, 12)

    def __init__(self, master) -> None:
        super().__init__(
            master,
            width=self.WIDTH,
            height=self.HEIGHT,
            fg_color="transparent",
        )
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._running = False
        self._frame = 0
        self._after_id: str | None = None

        platform = ctk.CTkFrame(
            self,
            width=198,
            height=32,
            corner_radius=16,
            fg_color=("#123F6A", "#0A3158"),
        )
        platform.place(x=6, y=170)

        for x in (36, 68, 100, 132, 164):
            dot = ctk.CTkLabel(
                self,
                text="",
                width=16,
                height=16,
                corner_radius=8,
                fg_color=("#12C9C9", "#18D1CF"),
            )
            dot.place(x=x, y=178)

        self._contact_dot = ctk.CTkLabel(
            self,
            text="",
            width=16,
            height=16,
            corner_radius=8,
            fg_color=("#12C9C9", "#18D1CF"),
        )
        self._contact_dot.place(x=132, y=178)

        bird = _load_bird_layer()
        self._bird_image = ctk.CTkImage(
            light_image=bird,
            dark_image=bird,
            size=(154, 170),
        )
        self._bird = ctk.CTkLabel(
            self,
            text="",
            image=self._bird_image,
            fg_color="transparent",
        )
        self._bird.place(x=18, y=self._REST_Y)
        self._show_contact(False)

    def _show_contact(self, active: bool) -> None:
        if active:
            self._contact_dot.configure(
                width=20,
                height=20,
                corner_radius=10,
                fg_color=("#FFB000", "#FFB000"),
            )
            self._contact_dot.place(x=130, y=176)
        else:
            self._contact_dot.configure(
                width=16,
                height=16,
                corner_radius=8,
                fg_color=("#12C9C9", "#18D1CF"),
            )
            self._contact_dot.place(x=132, y=178)

    def _animate(self) -> None:
        if not self._running:
            return
        y = self._POSITIONS[self._frame]
        self._bird.place_configure(y=y)
        self._show_contact(y >= self._CONTACT_Y)
        self._frame = (self._frame + 1) % len(self._POSITIONS)
        self._after_id = self.after(self._FRAME_DELAY_MS, self._animate)

    def set_running(self, running: bool) -> None:
        """Start pecking for a run, or return quietly to the resting pose."""

        running = bool(running)
        if running == self._running:
            return
        self._running = running
        if running:
            self._frame = 0
            self._animate()
        else:
            if self._after_id is not None:
                try:
                    self.after_cancel(self._after_id)
                except tk.TclError:
                    pass
            self._after_id = None
            self._bird.place_configure(y=self._REST_Y)
            self._show_contact(False)

    def destroy(self) -> None:
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()
