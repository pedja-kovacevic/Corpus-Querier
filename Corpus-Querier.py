"""Corpus Querier 3.0 provider launcher."""

from __future__ import annotations

import customtkinter as ctk

from app_identity import APP_VERSION, apply_window_icon, load_brand_image
from corpus_querier_noske import CorpusQuerierNoSketchApp
from corpus_querier_rnc import CorpusQuerierRNCApp
from corpus_querier_sketchengine import CorpusQuerierSketchEngineApp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ProviderChooser(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(className="CorpusQuerier")
        apply_window_icon(self)
        self.provider: str | None = None
        self.title(f"Corpus Querier {APP_VERSION}")
        self.geometry("1120x590")
        self.minsize(1020, 540)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.brand_image = load_brand_image((88, 88))
        ctk.CTkLabel(self, text="", image=self.brand_image).grid(
            row=0, column=0, pady=(24, 0)
        )

        ctk.CTkLabel(
            self,
            text="CORPUS QUERIER",
            font=ctk.CTkFont(size=31, weight="bold"),
        ).grid(row=1, column=0, pady=(4, 4))
        ctk.CTkLabel(
            self,
            text=f"Version {APP_VERSION} · Choose a corpus provider",
            text_color=("#526070", "#94A3B8"),
            font=ctk.CTkFont(size=14),
        ).grid(row=2, column=0, pady=(0, 20))

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=3, column=0, sticky="nsew", padx=34, pady=(0, 18))
        cards.grid_columnconfigure((0, 1, 2), weight=1, uniform="provider")
        cards.grid_rowconfigure(0, weight=1)

        self._provider_card(
            cards,
            column=0,
            title="NoSketch Engine",
            subtitle="Public Bonito corpus service",
            description=(
                "Run CQL queries, obtain exact total frequencies, and extract "
                "complete form-frequency lists from compatible NoSketch Engine corpora."
            ),
            details="CQL · exact totals · exact form lists",
            button_text="Open NoSketch Engine",
            provider="noske",
        )
        self._provider_card(
            cards,
            column=1,
            title="Sketch Engine",
            subtitle="Authenticated official API",
            description=(
                "Use a personal API key to query the British National Corpus "
                "and other corpora available in your Sketch Engine account."
            ),
            details="CQL · BNC · authenticated API",
            button_text="Open Sketch Engine",
            provider="sketchengine",
        )
        self._provider_card(
            cards,
            column=2,
            title="Russian National Corpus",
            subtitle="Official RNC public API",
            description=(
                "Build native lexical–grammatical searches, apply subcorpus "
                "filters, and save exact totals with concordance samples."
            ),
            details="RNC formulas · exact totals · sampled forms",
            button_text="Open RNC querier",
            provider="rnc",
        )

        ctk.CTkLabel(
            self,
            text=(
                "Provider-specific query syntax and result scope are kept explicit. "
                "RNC sampled forms are never presented as exhaustive counts."
            ),
            wraplength=980,
            justify="center",
            text_color=("#526070", "#94A3B8"),
        ).grid(row=4, column=0, padx=30, pady=(0, 24))

    def _provider_card(
        self,
        parent,
        *,
        column: int,
        title: str,
        subtitle: str,
        description: str,
        details: str,
        button_text: str,
        provider: str,
    ) -> None:
        card = ctk.CTkFrame(parent, corner_radius=16)
        card.grid(row=0, column=column, sticky="nsew", padx=8)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            card, text=title, font=ctk.CTkFont(size=21, weight="bold")
        ).grid(row=0, column=0, padx=22, pady=(24, 3))
        ctk.CTkLabel(
            card, text=subtitle, text_color=("#526070", "#94A3B8")
        ).grid(row=1, column=0, padx=22, pady=(0, 18))
        ctk.CTkLabel(
            card, text=description, wraplength=285, justify="left", anchor="nw"
        ).grid(row=2, column=0, sticky="ew", padx=25)
        ctk.CTkLabel(
            card,
            text=details,
            text_color=("#1D4ED8", "#93C5FD"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=3, column=0, sticky="s", padx=22, pady=18)
        ctk.CTkButton(
            card,
            text=button_text,
            height=42,
            command=lambda: self._select(provider),
        ).grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 22))

    def _select(self, provider: str) -> None:
        self.provider = provider
        self.destroy()


def main() -> None:
    chooser = ProviderChooser()
    chooser.mainloop()
    if chooser.provider == "noske":
        CorpusQuerierNoSketchApp().mainloop()
    elif chooser.provider == "sketchengine":
        CorpusQuerierSketchEngineApp().mainloop()
    elif chooser.provider == "rnc":
        CorpusQuerierRNCApp().mainloop()


if __name__ == "__main__":
    main()
