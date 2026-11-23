"""Authenticated Sketch Engine provider for Corpus Querier.

The provider deliberately reuses the CLARIN.SI/Bonito workflow.  The official
Sketch Engine service speaks the same CQL-based protocol, with authentication
and synchronous query processing added here as provider-specific settings.
"""

from __future__ import annotations

from corpus_querier_clarin import CorpusQuerierApp


SKETCH_ENGINE_ROOT = "https://api.sketchengine.eu/bonito/run.cgi"


class CorpusQuerierSketchEngineApp(CorpusQuerierApp):
    provider_name = "Sketch Engine"
    provider_subtitle = "Authenticated Sketch Engine research"
    available_corpora = [
        "preloaded/bnc2",
        "preloaded/bnc2_tt21",
        "preloaded/brown_1",
    ]
    default_corpus = "preloaded/bnc2"
    requires_api_key = True
    api_key_environment_variable = "SKETCHENGINE_API_KEY"
    view_url = f"{SKETCH_ENGINE_ROOT}/view"
    freqs_url = f"{SKETCH_ENGINE_ROOT}/freqs"
    corp_info_url = f"{SKETCH_ENGINE_ROOT}/corp_info"
    synchronous_queries = True

    def __init__(self) -> None:
        super().__init__()
        self.words_box.delete("1.0", "end")
        self.words_box.insert("1.0", "run, learn, travel")
        self.templates_box.delete("1.0", "end")
        self.templates_box.insert(
            "1.0",
            '[lemma="{LEMMA}"]\n[lemma="{LEMMA}" & tag="V.*"]',
        )
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert(
            "end",
            "Ready. Paste your Sketch Engine API key, select a corpus, "
            "and test the connection.\n",
        )
        self.log_box.configure(state="disabled")


if __name__ == "__main__":
    CorpusQuerierSketchEngineApp().mainloop()
