"""Shared application identity, version and icon helpers."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageChops, ImageDraw


APP_NAME = "Corpus Querier"
APP_VERSION = "3.3.0"


def resource_path(relative_path: str) -> Path:
    """Resolve an asset both from source and from a PyInstaller bundle."""

    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / relative_path


def apply_window_icon(window: tk.Misc) -> None:
    """Apply the shared icon to a Tk/CustomTkinter top-level window."""

    candidates = (
        "assets/corpus-querier-data-bird.png",
        "assets/corpus-querier.png",
    )
    for relative_path in candidates:
        try:
            icon = tk.PhotoImage(file=str(resource_path(relative_path)))
            window.iconphoto(True, icon)
            # Reapply after the X11 window is mapped. Some Linux panels read
            # _NET_WM_ICON only after realization and otherwise keep the
            # generic Tk/PyInstaller icon.
            window.after_idle(lambda saved=icon: window.iconphoto(True, saved))
            window._corpus_querier_icon = icon  # Keep the Tk image alive.
            return
        except (OSError, tk.TclError):
            continue
    # The executable and installer still carry their native embedded icon.


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


_SIDEBAR_LIGHT = (232, 238, 245, 255)
_SIDEBAR_DARK = (17, 24, 39, 255)


def _render_pecking_frame(angle: float, contact: bool, background: tuple[int, ...]) -> Image.Image:
    """Render one seamless animation frame on the sidebar's exact colour.

    The whole bird/platform composition is rasterized into one opaque image.
    This avoids the black transparency rectangle that some packaged Tk/Pillow
    combinations display around moving transparent labels.
    """

    width, height = 210, 205
    rgba = tuple(background[:3]) + (255,)
    frame = Image.new("RGBA", (width, height), rgba)
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((6, 170, 204, 202), radius=16, fill=(10, 49, 88, 255))
    for x in (36, 68, 100, 132, 164):
        colour = (255, 176, 0, 255) if contact and x == 132 else (24, 209, 207, 255)
        radius = 10 if contact and x == 132 else 8
        centre_x = x + 8
        centre_y = 186
        draw.ellipse(
            (centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius),
            fill=colour,
        )

    bird = _load_bird_layer().resize((154, 170), Image.Resampling.LANCZOS)
    bird_stage = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    bird_stage.alpha_composite(bird, (18, 3))
    # Pivot close to the bird's feet/tail. A small clockwise rotation moves the
    # head and beak towards the data point while the body stays grounded.
    bird_stage = bird_stage.rotate(
        angle,
        resample=Image.Resampling.BICUBIC,
        center=(58, 160),
        expand=False,
    )
    frame.alpha_composite(bird_stage)
    return frame


class PeckingBird(ctk.CTkLabel):
    """A seamless, restrained tilt animation built from the data-bird mark."""

    WIDTH = 210
    HEIGHT = 205
    _FRAME_DELAY_MS = 95
    _ANGLES = (
        3.0, 3.0, 2.0, 0.5, -1.5, -4.0, -6.5, -8.0,
        -8.0, -5.5, -3.0, -0.5, 1.5, 3.0,
    )

    def __init__(self, master) -> None:
        self._frames: list[ctk.CTkImage] = []
        for angle in self._ANGLES:
            contact = angle <= -7.5
            self._frames.append(
                ctk.CTkImage(
                    light_image=_render_pecking_frame(angle, contact, _SIDEBAR_LIGHT),
                    dark_image=_render_pecking_frame(angle, contact, _SIDEBAR_DARK),
                    size=(self.WIDTH, self.HEIGHT),
                )
            )
        super().__init__(
            master,
            text="",
            width=self.WIDTH,
            height=self.HEIGHT,
            corner_radius=0,
            fg_color=("#E8EEF5", "#111827"),
            image=self._frames[0],
        )
        self._running = False
        self._frame = 0
        self._after_id: str | None = None

    def _animate(self) -> None:
        if not self._running:
            return
        self.configure(image=self._frames[self._frame])
        self._frame = (self._frame + 1) % len(self._frames)
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
            self._frame = 0
            self.configure(image=self._frames[0])

    def destroy(self) -> None:
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()
