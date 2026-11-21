from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
import requests

from rnc_cql_translator import TranslationError, translate_cql
from rnc_provider import (
    AUTH_CHECK_URL,
    CONCORDANCE_URL,
    ConcordanceResult,
    SubcorpusFilters,
    build_subcorpus,
    filter_form_counts,
    merge_subcorpus,
    parse_concordance_response,
)


APP_NAME = "Corpus Querier RNC"
APP_VERSION = "0.2.0"
BASE_URL = CONCORDANCE_URL
COMMON_CORPORA = [
    "MAIN", "PAPER", "REGIONAL", "SCHOOL", "DIALECT", "POETIC",
    "SPOKEN", "ACCENT", "KIDS", "CLASSICS", "BLOGS", "SYNTAX",
    "OLD_RUS", "MID_RUS", "BIRCHBARK", "ORTHLIB", "EPIGRAPHICA",
]
PLACEHOLDER_RE = re.compile(r"\{(?:WORD|LEMMA)\}|\b(?:WORD|LEMMA)\b")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class QueryError(RuntimeError):
    pass


def column_letter_to_index(column: str) -> int:
    column = column.strip().upper()
    if not column or not column.isalpha():
        raise ValueError(f"Invalid Excel column: {column!r}")
    result = 0
    for character in column:
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def column_letters_to_indices(value: str) -> list[int]:
    columns = [item.strip() for item in value.split(",") if item.strip()]
    if not columns:
        raise ValueError("Enter at least one query column.")
    return [column_letter_to_index(item) for item in columns]


def index_to_column_letter(index: int) -> str:
    index += 1
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def escape_template_value(value: object) -> str:
    return str(value).strip().replace("\\", "\\\\").replace('"', '\\"')


def generate_query(template: str, value: object) -> str:
    escaped = escape_template_value(value)
    result = template.replace("{WORD}", escaped).replace("{LEMMA}", escaped)
    result = re.sub(r"\bWORD\b", lambda _: escaped, result)
    return re.sub(r"\bLEMMA\b", lambda _: escaped, result)


def compact_query_to_payload(
    expression: str,
    corpus: str,
    subcorpus: dict | None = None,
) -> dict:
    """Translate compact RNC notation into the official lex-gramm JSON schema.

    Supported examples:
      [lex="бежать"]
      [lex="бежать" & gramm="V,indic"]
      [lex="синий"] [lex="мяч" & dist="-3:3"]

    A complete official JSON request is also accepted unchanged, except that the
    corpus selected in the interface is supplied when JSON omits it.
    """
    expression = expression.strip()
    if not expression:
        raise ValueError("The query is empty.")

    if expression.startswith("{"):
        try:
            payload = json.loads(expression)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid query JSON: {error}") from error
        if not isinstance(payload, dict):
            raise ValueError("A JSON query must be an object.")
        payload.setdefault("corpus", {"type": corpus})
        if "lexGramm" not in payload:
            raise ValueError("The JSON query does not contain 'lexGramm'.")
        return merge_subcorpus(payload, subcorpus)

    # CQL-like input is handled by the deliberately conservative translator.
    # It raises rather than guessing whenever equivalent RNC semantics have not
    # been implemented and verified.
    try:
        return merge_subcorpus(translate_cql(expression, corpus).payload, subcorpus)
    except TranslationError as error:
        raise ValueError(str(error)) from error

def extract_total(data: dict) -> int:
    return parse_concordance_response(data).total_occurrences


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


@dataclass
class JobConfig:
    mode: str
    token: str
    input_file: Path | None
    output_file: Path
    corpus: str
    columns: list[int]
    start_row: int
    end_row: int | None
    words_text: str
    word_source: str
    word_column: int
    templates: list[str]
    delay: float
    timeout: float
    attempts: int
    save_every: int
    subcorpus: dict | None
    output_mode: str
    ignore_case: bool
    minimum_form_frequency: int


class QueryWorker(threading.Thread):
    def __init__(self, config: JobConfig, events: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.config = config
        self.events = events
        self.stop_event = stop_event
        self.form_rows: list[dict] = []
        self.concordance_rows: list[dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/json",
            "User-Agent": f"Corpus-Querier-RNC/{APP_VERSION}",
        })

    def emit(self, kind: str, **payload) -> None:
        self.events.put((kind, payload))

    def log(self, text: str) -> None:
        self.emit("log", text=text)

    def fetch_result(self, expression: str) -> tuple[ConcordanceResult, int, float]:
        if expression.lstrip().startswith("{"):
            payload = compact_query_to_payload(
                expression, self.config.corpus, self.config.subcorpus
            )
        else:
            report = translate_cql(expression, self.config.corpus)
            payload = merge_subcorpus(report.payload, self.config.subcorpus)
            for warning in report.warnings:
                self.log(f"Translation warning: {warning}")
        valid_results: list[ConcordanceResult] = []
        last_error: Exception | None = None
        started = time.monotonic()

        for attempt in range(1, self.config.attempts + 1):
            if self.stop_event.is_set():
                raise InterruptedError
            self.log(f"Attempt {attempt}/{self.config.attempts}")
            self.log(f"POST {BASE_URL}")
            try:
                response = self.session.post(BASE_URL, json=payload, timeout=self.config.timeout)
                if response.status_code == 401:
                    raise QueryError("Authentication failed. Check or regenerate the RNC API token.")
                response.raise_for_status()
                result = parse_concordance_response(response.json())
                valid_results.append(result)
                self.log(
                    f"Occurrences on attempt {attempt}: "
                    f"{result.total_occurrences:,} in {result.matching_texts:,} texts"
                )
            except Exception as error:
                last_error = error
                self.log(f"Error: {error}")
            if attempt < self.config.attempts and self.stop_event.wait(1):
                raise InterruptedError

        if not valid_results:
            raise QueryError(str(last_error or "All query attempts failed."))
        best = max(
            valid_results,
            key=lambda item: (
                item.total_occurrences,
                sum(item.sampled_form_counts.values()),
            ),
        )
        duration = time.monotonic() - started
        self.log(
            f"Highest valid result: {best.total_occurrences:,} "
            f"({len(valid_results)}/{self.config.attempts} successful attempts; {duration:.1f} s)"
        )
        if self.config.output_mode != "Exact total frequency":
            self.log(
                "Form counts below are sampled from the returned concordance page; "
                "the total frequency is exact."
            )
        return best, len(valid_results), duration

    def load_job(self) -> tuple[pd.DataFrame, list[tuple[int, int, str]]]:
        cfg = self.config
        if cfg.mode == "existing":
            dataframe = pd.read_excel(cfg.input_file, header=None)
            end_row = min(cfg.end_row or len(dataframe), len(dataframe))
            if cfg.start_row > len(dataframe):
                raise ValueError("The starting row is outside the spreadsheet.")
            tasks = []
            for row in range(cfg.start_row - 1, end_row):
                for column in cfg.columns:
                    if column >= len(dataframe.columns):
                        raise ValueError(f"Column {index_to_column_letter(column)} is outside the spreadsheet.")
                    value = dataframe.iat[row, column]
                    if pd.isna(value) or not str(value).strip():
                        continue
                    expression = str(value).strip()
                    compact_query_to_payload(expression, cfg.corpus, cfg.subcorpus)
                    tasks.append((row, column, expression))
            return dataframe, tasks

        if cfg.word_source == "spreadsheet":
            source = pd.read_excel(cfg.input_file, header=None)
            if cfg.word_column >= len(source.columns):
                raise ValueError("The selected word column is outside the spreadsheet.")
            end_row = min(cfg.end_row or len(source), len(source))
            values = source.iloc[cfg.start_row - 1:end_row, cfg.word_column].tolist()
            words = [str(value).strip() for value in values if not pd.isna(value) and str(value).strip()]
        else:
            words = [item.strip() for item in re.split(r"[,;\n]+", cfg.words_text) if item.strip()]

        if not words:
            raise ValueError("No words or lemmas were supplied.")
        if not cfg.templates:
            raise ValueError("Enter at least one query template.")

        dataframe = pd.DataFrame([["INPUT", *cfg.templates]])
        tasks = []
        for word in words:
            row = len(dataframe)
            queries = [generate_query(template, word) for template in cfg.templates]
            dataframe.loc[row] = [word, *queries]
            for offset, expression in enumerate(queries, start=1):
                compact_query_to_payload(expression, cfg.corpus, cfg.subcorpus)
                tasks.append((row, offset, expression))
        return dataframe, tasks

    def save(self, dataframe: pd.DataFrame) -> None:
        self.config.output_file.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(self.config.output_file, engine="openpyxl") as writer:
            dataframe.to_excel(writer, sheet_name="Results", index=False, header=False)
            if self.config.output_mode != "Exact total frequency":
                form_columns = [
                    "source_cell", "query", "exact_total", "form",
                    "sample_count", "scope",
                ]
                pd.DataFrame(self.form_rows, columns=form_columns).to_excel(
                    writer, sheet_name="Sampled forms", index=False
                )
                context_columns = [
                    "source_cell", "query", "exact_total", "hits",
                    "context", "document_id", "title",
                ]
                pd.DataFrame(self.concordance_rows, columns=context_columns).to_excel(
                    writer, sheet_name="Concordance sample", index=False
                )
        self.log(f"Saved: {self.config.output_file}")

    def record_samples(
        self,
        *,
        cell: str,
        expression: str,
        result: ConcordanceResult,
    ) -> None:
        if self.config.output_mode == "Exact total frequency":
            return
        counts = filter_form_counts(
            result.sampled_form_counts,
            minimum=self.config.minimum_form_frequency,
            ignore_case=self.config.ignore_case,
        )
        for form, count in counts.items():
            self.form_rows.append({
                "source_cell": cell,
                "query": expression,
                "exact_total": result.total_occurrences,
                "form": form,
                "sample_count": count,
                "scope": "returned concordance sample, not the whole result set",
            })
        for example in result.examples:
            self.concordance_rows.append({
                "source_cell": cell,
                "query": expression,
                "exact_total": result.total_occurrences,
                "hits": "; ".join(example.hits),
                "context": example.text,
                "document_id": example.document_id,
                "title": example.metadata.get("Название", example.metadata.get("title", "")),
            })
        if counts:
            preview = "; ".join(f"{form} ({count})" for form, count in list(counts.items())[:8])
            self.log(f"Sampled forms: {preview}")
        else:
            self.log("No sampled forms met the selected minimum.")

    def run(self) -> None:
        started = time.monotonic()
        completed = failed = 0
        dataframe: pd.DataFrame | None = None
        try:
            dataframe, tasks = self.load_job()
            total = len(tasks)
            if not total:
                raise ValueError("No valid queries were found.")
            self.emit("started", total=total)
            self.log(f"Prepared {total:,} queries for RNC corpus '{self.config.corpus}'.")

            for position, (row, column, expression) in enumerate(tasks, start=1):
                if self.stop_event.is_set():
                    break
                cell = f"{index_to_column_letter(column)}{row + 1}"
                self.emit("current", position=position, cell=cell, query=expression)
                self.log(f"\n[{position:,}/{total:,}] Cell {cell}\nRunning query: {expression}")
                try:
                    result, successful_attempts, duration = self.fetch_result(expression)
                    self.record_samples(
                        cell=cell, expression=expression, result=result
                    )
                    if self.config.output_mode == "Sampled forms only":
                        dataframe.iat[row, column] = "SEE 'Sampled forms' SHEET"
                    else:
                        dataframe.iat[row, column] = result.total_occurrences
                    completed += 1
                    self.emit("result", success=True, hits=result.total_occurrences,
                              attempts=successful_attempts, duration=duration)
                except QueryError as error:
                    dataframe.iat[row, column] = "ERROR"
                    failed += 1
                    self.log(f"Query failed: {error}")
                    self.emit("result", success=False, error=str(error))

                processed = completed + failed
                elapsed = time.monotonic() - started
                eta = (elapsed / processed) * (total - processed) if processed else None
                self.emit("progress", completed=completed, failed=failed, processed=processed,
                          total=total, elapsed=elapsed, eta=eta)
                if processed % self.config.save_every == 0:
                    self.save(dataframe)
                if position < total and self.stop_event.wait(self.config.delay):
                    break

            self.save(dataframe)
            self.emit("finished", stopped=self.stop_event.is_set(), completed=completed,
                      failed=failed, elapsed=time.monotonic() - started,
                      output=str(self.config.output_file))
        except Exception as error:
            if dataframe is not None:
                try:
                    self.save(dataframe)
                except Exception:
                    pass
            self.emit("fatal", error=str(error))
        finally:
            self.session.close()


class CorpusQuerierRNCApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1280x980")
        self.minsize(1120, 820)
        self.events: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: QueryWorker | None = None
        self.total = 0
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_workspace()
        self.after(100, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_sidebar(self) -> None:
        side = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=("#E8EEF5", "#111827"))
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="CORPUS\nQUERIER", font=ctk.CTkFont(size=26, weight="bold"),
                     justify="left").pack(anchor="w", padx=28, pady=(30, 4))
        ctk.CTkLabel(side, text="Russian National Corpus", text_color=("#526070", "#94A3B8"),
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=28, pady=(0, 30))
        self.status_pill = ctk.CTkLabel(side, text="●  READY", fg_color=("#D9F7E8", "#123D2B"),
                                        text_color=("#087443", "#6EE7B7"), corner_radius=12, height=34)
        self.status_pill.pack(fill="x", padx=24)
        ctk.CTkLabel(side, text="RUN SUMMARY", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=("#64748B", "#94A3B8")).pack(anchor="w", padx=28, pady=(32, 10))
        self.summary_labels = {}
        for key, title in [("total", "Total queries"), ("done", "Completed"),
                           ("failed", "Failed"), ("elapsed", "Elapsed"), ("eta", "Estimated left")]:
            row = ctk.CTkFrame(side, fg_color="transparent")
            row.pack(fill="x", padx=28, pady=5)
            ctk.CTkLabel(row, text=title, text_color=("#526070", "#94A3B8")).pack(side="left")
            label = ctk.CTkLabel(row, text="0" if key in {"total", "done", "failed"} else "—",
                                 font=ctk.CTkFont(weight="bold"))
            label.pack(side="right")
            self.summary_labels[key] = label
        ctk.CTkLabel(side, text="Appearance", text_color=("#526070", "#94A3B8")).pack(
            anchor="w", padx=28, pady=(35, 6))
        ctk.CTkOptionMenu(side, values=["Dark", "Light", "System"],
                          command=ctk.set_appearance_mode, height=34).pack(fill="x", padx=24)

    def _build_workspace(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=24, pady=22)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="Configure RNC query run",
                     font=ctk.CTkFont(size=25, weight="bold")).pack(side="left")
        self.stop_button = ctk.CTkButton(header, text="Stop & save", fg_color="#B91C1C",
                                         hover_color="#991B1B", state="disabled", command=self._stop)
        self.stop_button.pack(side="right", padx=(10, 0))
        self.start_button = ctk.CTkButton(header, text="▶  Start queries", width=160, command=self._start)
        self.start_button.pack(side="right")

        auth = ctk.CTkFrame(main)
        auth.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        auth.grid_columnconfigure(1, weight=1)
        self.api_token = ctk.StringVar(value=os.environ.get("RNC_API_TOKEN", ""))
        ctk.CTkLabel(auth, text="RNC API token").grid(row=0, column=0, padx=(16, 10), pady=10)
        ctk.CTkEntry(auth, textvariable=self.api_token, show="•",
                     placeholder_text="Paste your personal token; it is not saved in the workbook").grid(
                         row=0, column=1, sticky="ew", padx=(0, 8), pady=10)
        self.test_token_button = ctk.CTkButton(
            auth, text="Test connection", width=120, command=self._test_connection
        )
        self.test_token_button.grid(row=0, column=2, padx=(0, 16), pady=10)

        self._build_filters(main)

        self.tabs = ctk.CTkTabview(main, height=405)
        self.tabs.grid(row=3, column=0, sticky="ew")
        existing = self.tabs.add("Existing query spreadsheet")
        generated = self.tabs.add("Generate RNC queries")
        self._build_existing(existing)
        self._build_generated(generated)

        monitor = ctk.CTkFrame(main)
        monitor.grid(row=4, column=0, sticky="nsew", pady=(14, 0))
        monitor.grid_columnconfigure(0, weight=1)
        monitor.grid_rowconfigure(3, weight=1)
        top = ctk.CTkFrame(monitor, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 5))
        ctk.CTkLabel(top, text="Live run monitor", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.percent_label = ctk.CTkLabel(top, text="0%", font=ctk.CTkFont(weight="bold"))
        self.percent_label.pack(side="right")
        self.progress = ctk.CTkProgressBar(monitor, height=10)
        self.progress.grid(row=1, column=0, sticky="ew", padx=16)
        self.progress.set(0)
        self.current_label = ctk.CTkLabel(monitor, text="No query is running.", anchor="w",
                                          text_color=("#526070", "#94A3B8"))
        self.current_label.grid(row=2, column=0, sticky="ew", padx=16, pady=7)
        self.log_box = ctk.CTkTextbox(monitor, font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        self.log_box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_box.insert("end", "Ready. Enter your RNC API token and configure a run.\n")
        self.log_box.configure(state="disabled")

    def _build_filters(self, parent) -> None:
        panel = ctk.CTkFrame(parent)
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for column in range(8):
            panel.grid_columnconfigure(column, weight=1 if column % 2 else 0)

        self.output_mode = ctk.StringVar(value="Exact total frequency")
        self.ignore_case = ctk.BooleanVar(value=True)
        self.minimum_form_frequency = ctk.StringVar(value="1")
        self.metadata_vars = {
            "year_from": ctk.StringVar(), "year_to": ctk.StringVar(),
            "sex": ctk.StringVar(value="Any"),
            "category": ctk.StringVar(value="Any"),
            "author": ctk.StringVar(), "sphere": ctk.StringVar(),
            "topic": ctk.StringVar(), "text_type": ctk.StringVar(),
            "genre": ctk.StringVar(), "extra_field": ctk.StringVar(),
            "extra_value": ctk.StringVar(),
        }

        title = ctk.CTkFrame(panel, fg_color="transparent")
        title.grid(row=0, column=0, columnspan=8, sticky="ew", padx=14, pady=(8, 3))
        ctk.CTkLabel(
            title, text="OUTPUT & SUBCORPUS", font=ctk.CTkFont(size=11, weight="bold")
        ).pack(side="left")
        ctk.CTkLabel(
            title,
            text="Exact totals come from queryStats; form frequencies are labelled samples.",
            text_color=("#526070", "#94A3B8"),
        ).pack(side="right")

        ctk.CTkLabel(panel, text="Output").grid(row=1, column=0, padx=(14, 6), pady=4)
        ctk.CTkComboBox(
            panel,
            variable=self.output_mode,
            values=[
                "Exact total frequency",
                "Exact total + sampled forms",
                "Sampled forms only",
            ],
            width=220,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)
        ctk.CTkCheckBox(
            panel, text="Merge capitalization", variable=self.ignore_case, width=155
        ).grid(row=1, column=2, columnspan=2, sticky="w", padx=(0, 12), pady=4)
        ctk.CTkLabel(panel, text="Sample minimum").grid(row=1, column=4, padx=(0, 6), pady=4)
        ctk.CTkEntry(panel, textvariable=self.minimum_form_frequency, width=70).grid(
            row=1, column=5, sticky="ew", padx=(0, 12), pady=4
        )
        ctk.CTkLabel(panel, text="(within returned sample)", text_color=("#526070", "#94A3B8")).grid(
            row=1, column=6, columnspan=2, sticky="w", pady=4
        )

        fields = [
            ("Year from", "year_from", None),
            ("Year to", "year_to", None),
            ("Author sex", "sex", ["Any", "Male", "Female"]),
            ("Category", "category", ["Any", "Non-fiction", "Fiction"]),
        ]
        for pair, (label, key, values) in enumerate(fields):
            column = pair * 2
            ctk.CTkLabel(panel, text=label).grid(row=2, column=column, padx=(14 if column == 0 else 6, 6), pady=4)
            if values:
                widget = ctk.CTkComboBox(panel, variable=self.metadata_vars[key], values=values)
            else:
                widget = ctk.CTkEntry(panel, textvariable=self.metadata_vars[key])
            widget.grid(row=2, column=column + 1, sticky="ew", padx=(0, 10), pady=4)

        fields = [
            ("Author", "author", None),
            ("Sphere", "sphere", ["", "публицистика"]),
            ("Topic", "topic", ["", "дом и домашнее хозяйство"]),
            ("Text type", "text_type", ["", "доклад", "лекция", "монография", "рецензия"]),
        ]
        for pair, (label, key, values) in enumerate(fields):
            column = pair * 2
            ctk.CTkLabel(panel, text=label).grid(row=3, column=column, padx=(14 if column == 0 else 6, 6), pady=4)
            widget = (
                ctk.CTkComboBox(panel, variable=self.metadata_vars[key], values=values)
                if values else ctk.CTkEntry(panel, textvariable=self.metadata_vars[key])
            )
            widget.grid(row=3, column=column + 1, sticky="ew", padx=(0, 10), pady=4)

        ctk.CTkLabel(panel, text="Genre").grid(row=4, column=0, padx=(14, 6), pady=(4, 9))
        ctk.CTkEntry(panel, textvariable=self.metadata_vars["genre"]).grid(
            row=4, column=1, sticky="ew", padx=(0, 10), pady=(4, 9)
        )
        ctk.CTkLabel(panel, text="Extra RNC field").grid(row=4, column=2, padx=(6, 6), pady=(4, 9))
        ctk.CTkEntry(panel, textvariable=self.metadata_vars["extra_field"], placeholder_text="e.g. audience_age").grid(
            row=4, column=3, sticky="ew", padx=(0, 10), pady=(4, 9)
        )
        ctk.CTkLabel(panel, text="Value(s)").grid(row=4, column=4, padx=(6, 6), pady=(4, 9))
        ctk.CTkEntry(
            panel,
            textvariable=self.metadata_vars["extra_value"],
            placeholder_text="Separate alternatives with |",
        ).grid(row=4, column=5, columnspan=3, sticky="ew", padx=(0, 14), pady=(4, 9))

    def _entry_row(self, parent, row, label, variable, browse=None, placeholder=""):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=(16, 10), pady=7)
        entry = ctk.CTkEntry(parent, textvariable=variable, placeholder_text=placeholder)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=7)
        if browse:
            ctk.CTkButton(parent, text="Browse", width=78, command=browse).grid(
                row=row, column=2, padx=(0, 16), pady=7)
        return entry

    def _build_existing(self, tab) -> None:
        tab.grid_columnconfigure(1, weight=1)
        self.existing_input = ctk.StringVar()
        self.existing_output = ctk.StringVar()
        self.existing_corpus = ctk.StringVar(value="MAIN")
        self.existing_columns = ctk.StringVar(value="A")
        self.existing_start = ctk.StringVar(value="1")
        self.existing_end = ctk.StringVar()
        self._entry_row(tab, 0, "Input Excel file", self.existing_input,
                        lambda: self._choose_open(self.existing_input))
        self._entry_row(tab, 1, "Output Excel file", self.existing_output,
                        lambda: self._choose_save(self.existing_output))
        ctk.CTkLabel(tab, text="RNC corpus").grid(row=2, column=0, sticky="w", padx=(16, 10), pady=7)
        ctk.CTkComboBox(tab, values=COMMON_CORPORA, variable=self.existing_corpus).grid(
            row=2, column=1, sticky="ew", padx=(0, 8), pady=7)
        ranges = ctk.CTkFrame(tab, fg_color="transparent")
        ranges.grid(row=3, column=0, columnspan=3, sticky="ew", padx=16, pady=7)
        for i in range(6):
            ranges.grid_columnconfigure(i, weight=1 if i in {1, 3, 5} else 0)
        ctk.CTkLabel(ranges, text="Query columns").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkEntry(ranges, textvariable=self.existing_columns).grid(row=0, column=1, sticky="ew", padx=(0, 16))
        ctk.CTkLabel(ranges, text="Start row").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkEntry(ranges, textvariable=self.existing_start, width=90).grid(row=0, column=3, sticky="ew", padx=(0, 16))
        ctk.CTkLabel(ranges, text="End row").grid(row=0, column=4, padx=(0, 8))
        ctk.CTkEntry(ranges, textvariable=self.existing_end, placeholder_text="Last row").grid(row=0, column=5, sticky="ew")
        self._build_advanced(tab, 4, "existing")

    def _build_generated(self, tab) -> None:
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(4, weight=1)
        self.word_source = ctk.StringVar(value="spreadsheet")
        self.generated_input = ctk.StringVar()
        self.generated_output = ctk.StringVar()
        self.generated_corpus = ctk.StringVar(value="MAIN")
        self.word_column = ctk.StringVar(value="A")
        self.generated_start = ctk.StringVar(value="1")
        self.generated_end = ctk.StringVar()
        source = ctk.CTkSegmentedButton(tab, values=["Spreadsheet", "Type or paste words"],
                                        command=self._source_changed)
        source.grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(10, 6))
        source.set("Spreadsheet")
        self.generated_file_label = ctk.CTkLabel(tab, text="Words Excel file")
        self.generated_file_label.grid(row=1, column=0, sticky="w", padx=(16, 10), pady=7)
        self.generated_input_entry = ctk.CTkEntry(tab, textvariable=self.generated_input)
        self.generated_input_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=7)
        self.generated_browse = ctk.CTkButton(tab, text="Browse", width=78,
                                               command=lambda: self._choose_open(self.generated_input))
        self.generated_browse.grid(row=1, column=2, padx=(0, 16), pady=7)
        self.words_box = ctk.CTkTextbox(tab, height=70)
        self.words_box.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=7)
        self.words_box.insert("1.0", "бежать, писать, читать")
        self.words_box.grid_remove()
        details = ctk.CTkFrame(tab, fg_color="transparent")
        details.grid(row=3, column=0, columnspan=3, sticky="ew", padx=16, pady=5)
        for i in range(6):
            details.grid_columnconfigure(i, weight=1 if i in {1, 3, 5} else 0)
        for n, (label, variable) in enumerate([
            ("Word column", self.word_column), ("Start row", self.generated_start),
            ("End row", self.generated_end),
        ]):
            ctk.CTkLabel(details, text=label).grid(row=0, column=n * 2, padx=(0, 6) if n == 0 else (12, 6))
            ctk.CTkEntry(details, textvariable=variable, width=85,
                         placeholder_text="Last" if n == 2 else "").grid(row=0, column=n * 2 + 1, sticky="ew")
        self.word_details = details
        template_frame = ctk.CTkFrame(tab, fg_color="transparent")
        template_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=16, pady=5)
        template_frame.grid_columnconfigure(1, weight=1)
        builder = ctk.CTkFrame(template_frame, fg_color="transparent")
        builder.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        builder.grid_columnconfigure(1, weight=1)
        builder.grid_columnconfigure(3, weight=1)
        self.builder_field = ctk.StringVar(value="Lemma")
        self.builder_value = ctk.StringVar(value="{LEMMA}")
        self.builder_grammar = ctk.StringVar()
        ctk.CTkComboBox(
            builder,
            variable=self.builder_field,
            values=["Lemma", "Word form", "Lemma regex", "Word regex"],
            width=125,
        ).grid(row=0, column=0, padx=(0, 7))
        ctk.CTkEntry(
            builder, textvariable=self.builder_value, placeholder_text="Value or pattern"
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(builder, text="RNC grammar").grid(row=0, column=2, padx=(0, 7))
        ctk.CTkEntry(
            builder,
            textvariable=self.builder_grammar,
            placeholder_text='optional, e.g. (S) & -(gen|gen2)',
        ).grid(row=0, column=3, sticky="ew", padx=(0, 8))
        ctk.CTkButton(builder, text="Add template", width=105, command=self._add_built_template).grid(
            row=0, column=4
        )
        ctk.CTkLabel(template_frame, text="RNC templates\n(one per line)", justify="left").grid(
            row=1, column=0, sticky="nw", padx=(0, 10))
        self.templates_box = ctk.CTkTextbox(template_frame, height=86,
                                             font=ctk.CTkFont(family="Consolas", size=12))
        self.templates_box.grid(row=1, column=1, sticky="ew")
        self.templates_box.insert("1.0", '[lemma="{LEMMA}"]')
        lower = ctk.CTkFrame(tab, fg_color="transparent")
        lower.grid(row=5, column=0, columnspan=3, sticky="ew", padx=16, pady=(3, 8))
        lower.grid_columnconfigure(1, weight=1)
        lower.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(lower, text="RNC corpus").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkComboBox(lower, values=COMMON_CORPORA, variable=self.generated_corpus).grid(
            row=0, column=1, sticky="ew", padx=(0, 15))
        ctk.CTkLabel(lower, text="Output file").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkEntry(lower, textvariable=self.generated_output).grid(row=0, column=3, sticky="ew", padx=(0, 8))
        ctk.CTkButton(lower, text="Browse", width=78,
                      command=lambda: self._choose_save(self.generated_output)).grid(row=0, column=4)
        self._build_advanced(tab, 6, "generated")

    def _build_advanced(self, parent, row, prefix) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=16, pady=(4, 10))
        variables = {
            "delay": ctk.StringVar(value="5"), "timeout": ctk.StringVar(value="60"),
            "attempts": ctk.StringVar(value="2"), "save": ctk.StringVar(value="25"),
        }
        setattr(self, f"{prefix}_advanced", variables)
        for i, (label, key) in enumerate([
            ("Delay (s)", "delay"), ("Timeout (s)", "timeout"),
            ("Attempts", "attempts"), ("Save every", "save"),
        ]):
            ctk.CTkLabel(frame, text=label, text_color=("#526070", "#94A3B8")).grid(
                row=0, column=i * 2, padx=(0 if i == 0 else 14, 6))
            ctk.CTkEntry(frame, textvariable=variables[key], width=65).grid(row=0, column=i * 2 + 1)

    def _add_built_template(self) -> None:
        field_map = {
            "Lemma": "lemma",
            "Word form": "word",
            "Lemma regex": "lemma_regex",
            "Word regex": "word_regex",
        }
        value = self.builder_value.get().strip()
        if not value:
            messagebox.showerror(APP_NAME, "Enter a lemma, word form, or pattern.")
            return
        value = escape_template_value(value)
        parts = [f'{field_map[self.builder_field.get()]}="{value}"']
        grammar = self.builder_grammar.get().strip()
        if grammar:
            parts.append(f'gramm="{escape_template_value(grammar)}"')
        template = f"[{' & '.join(parts)}]"
        existing = self.templates_box.get("1.0", "end").strip()
        self.templates_box.delete("1.0", "end")
        self.templates_box.insert("1.0", f"{existing}\n{template}".strip())

    def _collect_subcorpus(self) -> dict | None:
        values = self.metadata_vars

        def optional_year(name: str) -> int | None:
            value = values[name].get().strip()
            if not value:
                return None
            try:
                return int(value)
            except ValueError as error:
                raise ValueError(f"{name.replace('_', ' ').title()} must be a year.") from error

        extra = ()
        extra_field = values["extra_field"].get().strip()
        extra_value = values["extra_value"].get().strip()
        if bool(extra_field) != bool(extra_value):
            raise ValueError("Enter both an extra RNC field name and its value.")
        if extra_field:
            extra = ((extra_field, extra_value),)

        filters = SubcorpusFilters(
            created_from=optional_year("year_from"),
            created_to=optional_year("year_to"),
            author=values["author"].get().strip(),
            author_sex=values["sex"].get().strip().lower(),
            category=values["category"].get().strip().lower(),
            sphere=values["sphere"].get().strip(),
            topic=values["topic"].get().strip(),
            text_type=values["text_type"].get().strip(),
            genre=values["genre"].get().strip(),
            extra_text_fields=extra,
        )
        return build_subcorpus(filters)

    def _test_connection(self) -> None:
        token = self.api_token.get().strip()
        if not token:
            messagebox.showerror(APP_NAME, "Paste your RNC API token first.")
            return
        self.test_token_button.configure(state="disabled", text="Testing…")

        def run_test() -> None:
            error = ""
            try:
                response = requests.get(
                    AUTH_CHECK_URL,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                    timeout=30,
                )
                if response.status_code == 401:
                    raise QueryError("Authentication failed. Check or regenerate the token.")
                response.raise_for_status()
                if response.json() is not True:
                    raise QueryError("The RNC did not confirm authentication.")
            except Exception as exception:
                error = str(exception)

            def finish() -> None:
                self.test_token_button.configure(state="normal", text="Test connection")
                if error:
                    messagebox.showerror(APP_NAME, error)
                else:
                    messagebox.showinfo(APP_NAME, "Connection successful. The RNC token is valid.")

            self.after(0, finish)

        threading.Thread(target=run_test, daemon=True).start()

    def _source_changed(self, value: str) -> None:
        spreadsheet = value == "Spreadsheet"
        self.word_source.set("spreadsheet" if spreadsheet else "typed")
        for widget in (self.generated_file_label, self.generated_input_entry, self.generated_browse, self.word_details):
            widget.grid() if spreadsheet else widget.grid_remove()
        self.words_box.grid_remove() if spreadsheet else self.words_box.grid()

    def _choose_open(self, variable) -> None:
        path = filedialog.askopenfilename(filetypes=[("Excel workbooks", "*.xlsx"), ("All files", "*.*")])
        if path:
            variable.set(path)

    def _choose_save(self, variable) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel workbooks", "*.xlsx")])
        if path:
            variable.set(path)

    def _number(self, value: str, name: str, integer=False, optional=False):
        value = value.strip()
        if optional and not value:
            return None
        try:
            number = int(value) if integer else float(value)
        except ValueError as error:
            raise ValueError(f"{name} must be a number.") from error
        if number <= 0:
            raise ValueError(f"{name} must be greater than zero.")
        return number

    def _collect_config(self) -> JobConfig:
        token = self.api_token.get().strip()
        if not token:
            raise ValueError("Enter your RNC API token.")
        generated = self.tabs.get() == "Generate RNC queries"
        prefix = "generated" if generated else "existing"
        advanced = getattr(self, f"{prefix}_advanced")
        output_text = getattr(self, f"{prefix}_output").get().strip().strip('"')
        if not output_text:
            raise ValueError("Choose an output Excel file.")
        output = Path(output_text)
        corpus = getattr(self, f"{prefix}_corpus").get().strip().upper()
        if corpus not in COMMON_CORPORA:
            raise ValueError("Choose a supported RNC corpus.")
        common = (
            self._number(advanced["delay"].get(), "Delay"),
            self._number(advanced["timeout"].get(), "Timeout"),
            self._number(advanced["attempts"].get(), "Attempts", True),
            self._number(advanced["save"].get(), "Save interval", True),
        )
        if common[2] < 2:
            raise ValueError("Attempts must be at least 2; both verification queries are mandatory.")
        output_settings = (
            self._collect_subcorpus(),
            self.output_mode.get(),
            bool(self.ignore_case.get()),
            self._number(
                self.minimum_form_frequency.get(),
                "Sample minimum",
                True,
            ),
        )
        if generated:
            input_text = self.generated_input.get().strip().strip('"')
            input_file = Path(input_text) if self.word_source.get() == "spreadsheet" else None
            if self.word_source.get() == "spreadsheet" and (not input_text or not input_file.exists()):
                raise ValueError("Choose a valid Excel file containing the words.")
            templates = [line.strip() for line in self.templates_box.get("1.0", "end").splitlines() if line.strip()]
            bad = [template for template in templates if not PLACEHOLDER_RE.search(template)]
            if bad:
                raise ValueError("Every template must contain {WORD} or {LEMMA}.")
            start = self._number(self.generated_start.get(), "Start row", True) if input_file else 1
            end = self._number(self.generated_end.get(), "End row", True, True) if input_file else None
            return JobConfig("generated", token, input_file, output, corpus, [], start, end,
                             self.words_box.get("1.0", "end"), self.word_source.get(),
                             column_letter_to_index(self.word_column.get()), templates,
                             *common, *output_settings)

        input_text = self.existing_input.get().strip().strip('"')
        input_file = Path(input_text)
        if not input_text or not input_file.exists():
            raise ValueError("Choose a valid input Excel file.")
        return JobConfig(
            "existing", token, input_file, output, corpus,
            column_letters_to_indices(self.existing_columns.get()),
            self._number(self.existing_start.get(), "Start row", True),
            self._number(self.existing_end.get(), "End row", True, True),
            "", "spreadsheet", 0, [], *common, *output_settings,
        )

    def _start(self) -> None:
        try:
            config = self._collect_config()
        except Exception as error:
            messagebox.showerror(APP_NAME, str(error))
            return
        self.stop_event.clear()
        self._reset_monitor()
        self._set_running(True)
        self.worker = QueryWorker(config, self.events, self.stop_event)
        self.worker.start()

    def _stop(self) -> None:
        self.stop_event.set()
        self.status_pill.configure(text="●  STOPPING", fg_color=("#FEF3C7", "#4A3510"),
                                   text_color=("#92400E", "#FCD34D"))
        self._append_log("\nStop requested. The current request will finish, then results will be saved.\n")

    def _set_running(self, running: bool) -> None:
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.tabs.configure(state="disabled" if running else "normal")
        if running:
            self.status_pill.configure(text="●  RUNNING", fg_color=("#DBEAFE", "#17345C"),
                                       text_color=("#1D4ED8", "#93C5FD"))

    def _reset_monitor(self) -> None:
        self.progress.set(0)
        self.percent_label.configure(text="0%")
        for key in ("total", "done", "failed"):
            self.summary_labels[key].configure(text="0")
        self.summary_labels["elapsed"].configure(text="—")
        self.summary_labels["eta"].configure(text="—")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + ("" if text.endswith("\n") else "\n"))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._append_log(payload["text"])
                elif kind == "started":
                    self.total = payload["total"]
                    self.summary_labels["total"].configure(text=f"{self.total:,}")
                elif kind == "current":
                    self.current_label.configure(
                        text=f'{payload["position"]:,}/{self.total:,} · {payload["cell"]} · {payload["query"]}'
                    )
                elif kind == "progress":
                    ratio = payload["processed"] / payload["total"]
                    self.progress.set(ratio)
                    self.percent_label.configure(text=f"{ratio:.0%}")
                    self.summary_labels["done"].configure(text=f'{payload["completed"]:,}')
                    self.summary_labels["failed"].configure(text=f'{payload["failed"]:,}')
                    self.summary_labels["elapsed"].configure(text=format_duration(payload["elapsed"]))
                    self.summary_labels["eta"].configure(text=format_duration(payload["eta"]))
                elif kind == "finished":
                    self._set_running(False)
                    status = "STOPPED · SAVED" if payload["stopped"] else "COMPLETE"
                    self.status_pill.configure(text=f"●  {status}", fg_color=("#D9F7E8", "#123D2B"),
                                               text_color=("#087443", "#6EE7B7"))
                    self.current_label.configure(text=f'Results saved to {payload["output"]}')
                    messagebox.showinfo(
                        APP_NAME,
                        f'{status.title()}\n\nCompleted: {payload["completed"]:,}\n'
                        f'Failed: {payload["failed"]:,}\nElapsed: {format_duration(payload["elapsed"])}',
                    )
                elif kind == "fatal":
                    self._set_running(False)
                    self.status_pill.configure(text="●  ERROR", fg_color=("#FEE2E2", "#4A1515"),
                                               text_color=("#B91C1C", "#FCA5A5"))
                    self._append_log(f'\nFatal error: {payload["error"]}')
                    messagebox.showerror(APP_NAME, payload["error"])
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(APP_NAME, "A run is active. Stop, save, and close when possible?"):
                return
            self.stop_event.set()
        self.destroy()


if __name__ == "__main__":
    CorpusQuerierRNCApp().mainloop()
