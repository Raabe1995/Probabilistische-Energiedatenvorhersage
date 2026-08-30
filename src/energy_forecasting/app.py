"""Streamlit-Oberfläche zum Starten und Auswerten der Prognosepipeline.

Das Modul verwaltet Uploads, startet die Verarbeitungsschritte als getrennte
Python-Prozesse und stellt vorhandene Ergebnisartefakte im Dashboard dar.
"""

import base64
import glob
import html
import json
import os
import shutil
import subprocess
import sys
import traceback

import pandas as pd
import streamlit as st

from energy_forecasting.dashboard import generate_dashboard_bundle, load_dashboard_bundle


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PACKAGE_DIR))
IS_DOCKER = os.path.exists("/.dockerenv") or os.path.exists("/run/secrets/kubernetes.io")
STREAMLIT_ERROR_LOG = "streamlit_error.log"

if IS_DOCKER:
    # Docker Compose bindet hier die persistenten Ein- und Ausgabeordner ein.
    INPUT_DIR = "/app/data/input"
    OUTPUT_DIR = "/app/data/output"
else:
    # Lokale Datenpfade werden unabhängig vom Arbeitsverzeichnis aufgelöst.
    INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "input")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")

METRIC_LABELS = {
    "PICP_80_percent": "Intervallabdeckung",
    "Mean_Interval_Width_MWh": "Mittlere Intervallbreite",
    "Median_RMSE_MWh": "Median-RMSE",
    "Winkler_Score_80_MWh": "Winkler Score",
    "Quantile_Crossing_Rate_percent": "Quantilkreuzungen",
    "Raw_Quantile_Crossing_Rate_before_sort_percent": "Roh-Quantilkreuzungen vor Sortierung",
    "Pinball_Loss_q0_1_MWh": "Pinball Loss q0.1",
    "Pinball_Loss_q0_5_MWh": "Pinball Loss q0.5",
    "Pinball_Loss_q0_9_MWh": "Pinball Loss q0.9",
}

TABLE_COLUMN_LABELS = {
    "Datei": "Datei",
    "Groesse_KB": "Groesse KB",
    "Pfad": "Pfad",
    "metric": "Metrik",
    "value": "Wert",
}

DASHBOARD_TABS = [
    "Überblick",
    "Prognosen und EDA",
    "Diagnose",
    "Dateien und Protokoll",
]

DASHBOARD_TAB_KEYS = {
    "Überblick": "overview",
    "Prognosen und EDA": "forecasts",
    "Diagnose": "diagnostics",
    "Dateien und Protokoll": "files",
}


def move_to_output(file_path):
    """Verschiebe ein erzeugtes Artefakt in den Ausgabeordner.

    Relative Pfade werden gegen die Projektwurzel aufgelöst. Eine bereits
    vorhandene Datei gleichen Namens wird durch das neue Artefakt ersetzt.
    """

    source_path = file_path if os.path.isabs(file_path) else os.path.join(PROJECT_ROOT, file_path)
    if os.path.exists(source_path):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        target_path = os.path.join(OUTPUT_DIR, os.path.basename(source_path))
        if os.path.exists(target_path):
            os.remove(target_path)
        shutil.move(source_path, target_path)


def latest_file(pattern):
    """Gib die zuletzt geänderte Ausgabedatei für ein Glob-Muster zurück."""

    files = glob.glob(os.path.join(OUTPUT_DIR, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def read_csv(path):
    """Lese eine von der Pipeline erzeugte Semikolon-CSV."""

    return pd.read_csv(path, sep=";")


def read_metrics(model_prefix):
    """Lade die neuesten Metriken eines Modells als Name-Wert-Abbildung."""

    path = latest_file(f"{model_prefix}_metriken_*.csv")
    if not path:
        return {}, None
    df = read_csv(path)
    return dict(zip(df["metric"], df["value"])), path


def read_table(pattern):
    """Lade die neueste zum Muster passende CSV samt Quelldateipfad."""

    path = latest_file(pattern)
    if not path:
        return None, None
    return read_csv(path), path


def read_metadata(model_prefix):
    """Lade die neuesten JSON-Metadaten eines Modells."""

    path = latest_file(f"{model_prefix}_modell_metadaten_*.json")
    if not path:
        return {}, None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle), path


def dataframe_records(pattern, limit=8):
    """Liefere die ersten Zeilen der neuesten passenden CSV als Datensätze."""

    df, _ = read_table(pattern)
    if df is None:
        return []
    return df.head(limit).to_dict(orient="records")


def read_log_tail(max_chars=5000):
    """Lese höchstens die letzten ``max_chars`` Zeichen des Pipeline-Protokolls."""

    log_path = os.path.join(OUTPUT_DIR, "pipeline_protokoll.txt")
    if not os.path.exists(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    return content[-max_chars:]


def rerun_app():
    """Starte die Streamlit-App versionsübergreifend erneut."""

    rerun = getattr(st, "rerun", None)
    if rerun is not None:
        rerun()
    st.experimental_rerun()


def write_streamlit_error(exc):
    """Ergänze einen unbehandelten Streamlit-Fehler im Ausgabeprotokoll."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(OUTPUT_DIR, STREAMLIT_ERROR_LOG)
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write("\n" + "=" * 80 + "\n")
        handle.write(f"{type(exc).__name__}: {exc}\n")
        handle.write(traceback.format_exc())
    return log_path


def is_streamlit_control_exception(exc):
    """Erkenne Streamlit-interne Ausnahmen für Seitenwechsel und Abbruch."""

    return type(exc).__name__ in {"RerunException", "StopException"}


def format_number(value, suffix=""):
    """Formatiere einen numerischen Wert mit deutschen Trennzeichen."""

    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


def render_dashboard_styles():
    """Binde die CSS-Regeln für Ergebnisbilder und Tabellen ein."""

    st.markdown(
        """
        <style>
        .result-figure {
            margin: 0 0 1.4rem 0;
        }
        .result-figure img {
            display: block;
            width: 100%;
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: #ffffff;
        }
        .result-figure figcaption {
            margin-top: 0.45rem;
            color: rgba(250, 250, 250, 0.72);
            font-size: 0.88rem;
        }
        .result-table-wrap {
            overflow-x: auto;
            margin: 0.35rem 0 1.25rem 0;
        }
        .result-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }
        .result-table th,
        .result-table td {
            border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            padding: 0.48rem 0.58rem;
            text-align: left;
            vertical-align: top;
            overflow-wrap: anywhere;
        }
        .result-table th {
            color: rgba(250, 250, 250, 0.9);
            font-weight: 700;
            background: rgba(148, 163, 184, 0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def html_escape(value):
    """Maskiere einen Wert für die sichere Ausgabe in eigenem HTML."""

    if value is None:
        return ""
    return html.escape(str(value))


def image_data_uri(path):
    """Kodiere eine lokale Bilddatei als direkt einbettbare Data-URI."""

    extension = os.path.splitext(path)[1].lower()
    mime_type = "image/png" if extension == ".png" else "application/octet-stream"
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_safe_image(path, caption):
    """Zeige ein lokales Bild mit maskierter Beschriftung und Fehlerhinweis."""

    try:
        data_uri = image_data_uri(path)
    except OSError as exc:
        st.warning(f"{caption} konnte nicht geladen werden: {exc}")
        return

    st.markdown(
        f"""
        <figure class="result-figure">
            <img src="{data_uri}" alt="{html_escape(caption)}">
            <figcaption>{html_escape(caption)}</figcaption>
        </figure>
        """,
        unsafe_allow_html=True,
    )


def render_html_table(records):
    """Rendere eine Liste von Datensätzen als maskierte HTML-Tabelle."""

    if not records:
        return

    columns = []
    for record in records:
        for key in record.keys():
            if key not in columns:
                columns.append(key)

    header = "".join(f"<th>{html_escape(TABLE_COLUMN_LABELS.get(column, column))}</th>" for column in columns)
    rows = []
    for record in records:
        cells = "".join(f"<td>{html_escape(record.get(column, ''))}</td>" for column in columns)
        rows.append(f"<tr>{cells}</tr>")

    st.markdown(
        f"""
        <div class="result-table-wrap">
            <table class="result-table">
                <thead><tr>{header}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_status(metrics):
    """Erzeuge eine regelbasierte Kurzinterpretation probabilistischer Metriken.

    Die PICP-Abweichungen von höchstens drei beziehungsweise acht Prozentpunkten
    sind Darstellungsheuristiken für das Dashboard und keine statistischen
    Signifikanzgrenzen. Intervallbreite und Fehlermaße werden deshalb stets nur
    gemeinsam mit der erreichten Abdeckung beschrieben.
    """

    if not metrics:
        return "Keine Metriken gefunden."

    picp = metrics.get("PICP_80_percent")
    width = metrics.get("Mean_Interval_Width_MWh")
    rmse = metrics.get("Median_RMSE_MWh")
    winkler = metrics.get("Winkler_Score_80_MWh")
    crossing = metrics.get("Quantile_Crossing_Rate_percent", 0)
    raw_crossing = metrics.get("Raw_Quantile_Crossing_Rate_before_sort_percent")

    notes = []
    if picp is not None:
        target_picp = 80
        picp_delta = picp - target_picp
        abs_delta = abs(picp_delta)
        if abs_delta <= 3:
            notes.append(
                "Die Intervallabdeckung liegt sehr nah am nominellen 80%-Ziel "
                f"({format_number(picp, ' %')}, Abweichung {format_number(picp_delta, ' Prozentpunkte')})."
            )
        elif abs_delta <= 8:
            direction = "darüber" if picp_delta > 0 else "darunter"
            tendency = "leicht konservativ" if picp_delta > 0 else "leicht zu eng"
            notes.append(
                f"Die Intervallabdeckung liegt {format_number(abs_delta, ' Prozentpunkte')} {direction}; "
                f"das Intervall wirkt damit {tendency}."
            )
        elif picp_delta < 0:
            notes.append(
                "Das 80%-Intervall ist deutlich zu eng kalibriert "
                f"({format_number(picp, ' %')}, Abweichung {format_number(picp_delta, ' Prozentpunkte')})."
            )
        else:
            notes.append(
                "Das 80%-Intervall ist deutlich konservativ breit "
                f"({format_number(picp, ' %')}, Abweichung +{format_number(picp_delta, ' Prozentpunkte')})."
            )

    if crossing and crossing > 0:
        notes.append(
            "Nach der Ausgabe treten noch Quantilkreuzungen auf "
            f"({format_number(crossing, ' %')}); die Quantilordnung sollte weiter stabilisiert werden."
        )
    else:
        notes.append("Nach der Ausgabe bleiben die Quantile in der richtigen Reihenfolge.")

    if raw_crossing is not None and raw_crossing > crossing:
        notes.append(
            "Vor der Sortier-Absicherung lagen "
            f"{format_number(raw_crossing, ' %')} der Rohprognosen nicht in monotoner Quantilordnung."
        )

    if rmse is not None:
        notes.append(f"Der Median-RMSE liegt bei {format_number(rmse, ' MWh')}.")
    if winkler is not None:
        notes.append(f"Der Winkler Score liegt bei {format_number(winkler, ' MWh')}.")
    if width is not None:
        notes.append(
            "Die mittlere Intervallbreite beträgt "
            f"{format_number(width, ' MWh')} und sollte zusammen mit PICP und Winkler Score interpretiert werden."
        )

    return " ".join(notes)


def compare_models(lstm_metrics, rnn_metrics):
    """Vergleiche LSTM und RNN anhand dreier gleich gewichteter Kriterien.

    Ein Modell erhält je einen Vorteil für den niedrigeren Median-RMSE, den
    niedrigeren Winkler Score und die kleinere PICP-Abweichung vom 80%-Ziel.
    Die Intervallbreite wird nur als Kontext ausgegeben und nicht als isoliertes
    Gütekriterium gewertet.
    """

    if not lstm_metrics or not rnn_metrics:
        return "Für den Modellvergleich fehlen noch Metrikdateien."

    metric_checks = [
        ("Median-RMSE", "Median_RMSE_MWh", "niedriger"),
        ("Winkler Score", "Winkler_Score_80_MWh", "niedriger"),
        ("PICP-Abweichung vom 80%-Ziel", "PICP_80_percent", "naeher_an_80"),
    ]

    wins = {"LSTM": [], "RNN": []}
    details = []
    for label, key, criterion in metric_checks:
        lstm_value = lstm_metrics.get(key)
        rnn_value = rnn_metrics.get(key)
        if lstm_value is None or rnn_value is None:
            continue

        if criterion == "naeher_an_80":
            lstm_score = abs(lstm_value - 80)
            rnn_score = abs(rnn_value - 80)
        else:
            lstm_score = lstm_value
            rnn_score = rnn_value

        if abs(lstm_score - rnn_score) < 1e-9:
            details.append(f"{label}: Gleichstand.")
            continue

        winner = "LSTM" if lstm_score < rnn_score else "RNN"
        wins[winner].append(label)
        details.append(
            f"{label}: {winner} günstiger "
            f"(LSTM {format_number(lstm_value)}, RNN {format_number(rnn_value)})."
        )

    if not details:
        return "Für einen Modellvergleich fehlen vergleichbare Metriken."

    if len(wins["RNN"]) > len(wins["LSTM"]):
        headline = "Im aktuellen Lauf wirkt das RNN insgesamt stärker."
    elif len(wins["LSTM"]) > len(wins["RNN"]):
        headline = "Im aktuellen Lauf wirkt das LSTM insgesamt stärker."
    else:
        headline = "Der aktuelle Lauf zeigt kein eindeutiges Siegerbild zwischen LSTM und RNN."

    width_context = ""
    lstm_width = lstm_metrics.get("Mean_Interval_Width_MWh")
    rnn_width = rnn_metrics.get("Mean_Interval_Width_MWh")
    if lstm_width is not None and rnn_width is not None:
        width_context = (
            " Die mittlere Intervallbreite wird nur als Kontext betrachtet, weil ein schmaleres Intervall "
            "ohne passende Abdeckung nicht automatisch besser ist "
            f"(LSTM {format_number(lstm_width, ' MWh')}, RNN {format_number(rnn_width, ' MWh')})."
        )

    return f"{headline} " + " ".join(details) + width_context


def render_metric_cards(model_name, metrics):
    """Zeige die zentralen Metriken und ihre Kurzinterpretation für ein Modell."""

    st.subheader(model_name)
    if not metrics:
        st.info("Keine Metriken gefunden.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("PICP", format_number(metrics.get("PICP_80_percent"), " %"))
    col2.metric("RMSE", format_number(metrics.get("Median_RMSE_MWh"), " MWh"))
    col3.metric("Breite", format_number(metrics.get("Mean_Interval_Width_MWh"), " MWh"))
    col4.metric("Crossing", format_number(metrics.get("Quantile_Crossing_Rate_percent"), " %"))
    st.caption(metric_status(metrics))


def render_image(pattern, caption):
    """Zeige das neueste Bild für ein Dateimuster oder einen Leerzustand."""

    path = latest_file(pattern)
    if path:
        render_safe_image(path, caption)
    else:
        st.info(f"{caption} wurde noch nicht erzeugt.")


def render_bundle_image(dashboard, image_key, caption):
    """Zeige ein Vorschaubild aus dem Dashboard-Bundle mit Original-Fallback."""

    image_info = dashboard.get("images", {}).get(image_key, {})
    path = image_info.get("display_path") or image_info.get("source_path")
    if path and os.path.exists(path):
        render_safe_image(path, caption)
    else:
        st.info(f"{caption} wurde noch nicht erzeugt.")


def render_records_table(records, title, download_path=None, download_key=None):
    """Zeige Datensätze als Tabelle und optional als herunterladbare CSV."""

    if not records:
        st.info(f"{title} wurde noch nicht erzeugt.")
        return
    st.subheader(title)
    render_html_table(records)
    if download_path and os.path.exists(download_path):
        with open(download_path, "rb") as handle:
            st.download_button(
                label=f"{os.path.basename(download_path)} herunterladen",
                data=handle,
                file_name=os.path.basename(download_path),
                mime="text/csv",
                key=download_key or f"download_{title}_{os.path.basename(download_path)}",
            )


def render_table(pattern, title):
    """Zeige die neueste CSV eines Musters als Tabelle mit Download-Schaltfläche."""

    df, path = read_table(pattern)
    if df is None:
        st.info(f"{title} wurde noch nicht erzeugt.")
        return
    st.subheader(title)
    render_html_table(df.to_dict(orient="records"))
    with open(path, "rb") as handle:
        st.download_button(
            label=f"{os.path.basename(path)} herunterladen",
            data=handle,
            file_name=os.path.basename(path),
            mime="text/csv",
            key=f"download_{title}_{os.path.basename(path)}",
        )


def render_dashboard_tab_bar():
    """Rendere die Dashboard-Navigation und gib den aktiven Reiter zurück."""

    if (
        "dashboard_tab" not in st.session_state
        or st.session_state["dashboard_tab"] not in DASHBOARD_TABS
    ):
        st.session_state["dashboard_tab"] = "Überblick"

    columns = st.columns([1.0, 1.45, 1.0, 1.65, 1.1])
    for column, tab_label in zip(columns, DASHBOARD_TABS):
        with column:
            if st.button(
                tab_label,
                key=f"dashboard_tab_{DASHBOARD_TAB_KEYS[tab_label]}",
                type="primary" if st.session_state["dashboard_tab"] == tab_label else "secondary",
                use_container_width=True,
            ):
                st.session_state["dashboard_tab"] = tab_label
                rerun_app()

    st.divider()
    return st.session_state["dashboard_tab"]


def render_dashboard():
    """Stelle Metriken, Diagramme, Diagnosen und Dateien eines Laufs dar."""

    st.title("Ergebnis-Dashboard")
    render_dashboard_styles()

    dashboard = load_dashboard_bundle(OUTPUT_DIR)
    lstm_metric_bundle = dashboard.get("metrics", {}).get("lstm", {})
    rnn_metric_bundle = dashboard.get("metrics", {}).get("rnn", {})
    lstm_metrics = lstm_metric_bundle.get("values", {})
    rnn_metrics = rnn_metric_bundle.get("values", {})
    lstm_metrics_path = lstm_metric_bundle.get("path")
    rnn_metrics_path = rnn_metric_bundle.get("path")
    lstm_metadata = dashboard.get("metadata", {}).get("lstm", {}).get("values", {})
    rnn_metadata = dashboard.get("metadata", {}).get("rnn", {}).get("values", {})

    if not lstm_metrics and not rnn_metrics:
        st.warning("Noch keine Ergebnisdateien gefunden. Starte zuerst die Pipeline.")
        if st.button("Zur Pipeline"):
            st.session_state["active_page"] = "Pipeline"
            rerun_app()
        return

    st.success("Pipeline-Ergebnisse geladen.")
    if dashboard.get("_stale"):
        st.info(
            "Das vorberechnete Dashboard-Bundle ist nicht aktueller als alle Output-Dateien. "
            "Die Ansicht wird trotzdem read-only aus den vorhandenen Ergebnissen geladen."
        )
    st.write(compare_models(lstm_metrics, rnn_metrics))

    active_dashboard_tab = render_dashboard_tab_bar()

    if active_dashboard_tab == "Überblick":
        st.subheader("Überblick")
        render_metric_cards("LSTM", lstm_metrics)
        render_metric_cards("RNN", rnn_metrics)

        st.subheader("Trainingsumfang")
        meta = rnn_metadata or lstm_metadata
        if meta:
            split_counts = meta.get("split_counts", {})
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Train", split_counts.get("train_sequences", "-"))
            col2.metric("Validierung", split_counts.get("validation_sequences", "-"))
            col3.metric("Test", split_counts.get("test_sequences", "-"))
            col4.metric("Fenster", split_counts.get("window_size", "-"))
            st.write("Features:", ", ".join(meta.get("feature_columns", [])))
            weather_features = meta.get("weather_feature_columns", [])
            st.write("Wetterfeatures:", ", ".join(weather_features) if weather_features else "Keine")

    elif active_dashboard_tab == "Prognosen und EDA":
        st.subheader("Prognosen und EDA")
        left, right = st.columns(2)
        with left:
            render_bundle_image(dashboard, "lstm_forecast", "LSTM Vorhersageintervall")
            render_bundle_image(dashboard, "lstm_learning_curve", "LSTM Lernkurve")
        with right:
            render_bundle_image(dashboard, "rnn_forecast", "RNN Vorhersageintervall")
            render_bundle_image(dashboard, "rnn_learning_curve", "RNN Lernkurve")

        st.subheader("Explorative Analyse")
        eda_left, eda_right = st.columns(2)
        with eda_left:
            render_bundle_image(dashboard, "eda_energy", "Energieerzeugung")
            render_bundle_image(dashboard, "eda_daily_profile", "Tagesprofil")
        with eda_right:
            render_bundle_image(dashboard, "eda_correlation", "Korrelationsheatmap")

    elif active_dashboard_tab == "Diagnose":
        st.subheader("Diagnose")
        left, right = st.columns(2)
        with left:
            render_bundle_image(dashboard, "lstm_calibration", "LSTM Kalibrierung")
            render_bundle_image(dashboard, "lstm_feature_importance", "LSTM Feature Importance")
            render_records_table(
                dashboard.get("tables", {}).get("lstm_metrics", []),
                "LSTM Metriken",
                lstm_metrics_path,
                "download_lstm_metrics_bundle",
            )
        with right:
            render_bundle_image(dashboard, "rnn_calibration", "RNN Kalibrierung")
            render_bundle_image(dashboard, "rnn_feature_importance", "RNN Feature Importance")
            render_records_table(
                dashboard.get("tables", {}).get("rnn_metrics", []),
                "RNN Metriken",
                rnn_metrics_path,
                "download_rnn_metrics_bundle",
            )

    elif active_dashboard_tab == "Dateien und Protokoll":
        st.subheader("Dateien und Protokoll")
        render_html_table(dashboard.get("files", []))

        log_tail = dashboard.get("log", {}).get("tail", "")
        if log_tail:
            st.text_area("Pipeline-Protokoll", log_tail, height=300)

        for path in [lstm_metrics_path, rnn_metrics_path]:
            if path:
                with open(path, "rb") as handle:
                    st.download_button(
                        label=f"{os.path.basename(path)} herunterladen",
                        data=handle,
                        file_name=os.path.basename(path),
                        mime="text/csv",
                        key=f"download_files_{os.path.basename(path)}",
                    )

    if st.button("Neue Pipeline starten"):
        st.session_state["active_page"] = "Pipeline"
        rerun_app()


def run_pipeline(uploaded_file, weather_file):
    """Speichere Uploads und führe EDA, LSTM und RNN nacheinander aus.

    Jeder Schritt läuft als eigener Python-Prozess in der Projektwurzel. Die
    erzeugten Dateien und das gemeinsame Protokoll werden anschließend nach
    ``OUTPUT_DIR`` verschoben und zu einem Dashboard-Bundle zusammengefasst.
    """

    os.makedirs(INPUT_DIR, exist_ok=True)
    input_csv_path = os.path.join(INPUT_DIR, "aktuelle_erzeugung.csv")

    with open(input_csv_path, "wb") as file_handle:
        file_handle.write(uploaded_file.getbuffer())
    st.success("Datei erfolgreich geladen und im System aktualisiert!")

    weather_csv_path = None
    if weather_file is not None:
        weather_csv_path = os.path.join(INPUT_DIR, "weather_features.csv")
        with open(weather_csv_path, "wb") as file_handle:
            file_handle.write(weather_file.getbuffer())
        st.success("Wetterdatei erfolgreich geladen und wird in die Features integriert!")

    with st.spinner("Pipeline läuft... Bitte warten (EDA -> LSTM -> RNN)"):
        fehler_aufgetreten = False

        log_path = os.path.join(PROJECT_ROOT, "pipeline_protokoll.txt")
        source_dir = os.path.join(PROJECT_ROOT, "src")
        pipeline_env = os.environ.copy()
        existing_pythonpath = pipeline_env.get("PYTHONPATH")
        pipeline_env["PYTHONPATH"] = (
            source_dir if not existing_pythonpath else source_dir + os.pathsep + existing_pythonpath
        )

        with open(log_path, "w") as log_file:
            try:
                st.text("Starte EDA...")
                eda_command = [sys.executable, "-m", "energy_forecasting.data_preparation", input_csv_path]
                if weather_csv_path:
                    eda_command.extend(["--weather-csv", weather_csv_path])
                subprocess.run(
                    eda_command,
                    cwd=PROJECT_ROOT,
                    env=pipeline_env,
                    stdout=log_file,
                    stderr=log_file,
                    check=True,
                )

                st.text("Trainiere LSTM Modell...")
                subprocess.run(
                    [sys.executable, "-m", "energy_forecasting.models.lstm"],
                    cwd=PROJECT_ROOT,
                    env=pipeline_env,
                    stdout=log_file,
                    stderr=log_file,
                    check=True,
                )

                st.text("Trainiere RNN Modell...")
                subprocess.run(
                    [sys.executable, "-m", "energy_forecasting.models.rnn"],
                    cwd=PROJECT_ROOT,
                    env=pipeline_env,
                    stdout=log_file,
                    stderr=log_file,
                    check=True,
                )

                os.makedirs(OUTPUT_DIR, exist_ok=True)

                fixed_artifacts = [
                    "Realisierte_Erzeugung_Cleaned.csv",
                    "cleaned_data.pkl",
                    "scaler_features.pkl",
                    "scaler_target.pkl",
                    "scaler_features_rnn.pkl",
                    "scaler_target_rnn.pkl",
                    "best_prob_model.pth",
                    "final_probabilistic_lstm.pth",
                    "best_prob_model_rnn.pth",
                    "final_probabilistic_rnn.pth",
                ]

                for artifact in fixed_artifacts:
                    move_to_output(artifact)

                for png_file in glob.glob(os.path.join(PROJECT_ROOT, "*.png")):
                    move_to_output(png_file)

                generated_csvs = []
                for pattern in [
                    "*_daten_*.csv",
                    "*_metriken_*.csv",
                    "*_kalibrierung_daten_*.csv",
                    "*_feature_importance_*.csv",
                ]:
                    generated_csvs.extend(glob.glob(os.path.join(PROJECT_ROOT, pattern)))
                for csv_file in generated_csvs:
                    move_to_output(csv_file)

                for model_file in glob.glob(os.path.join(PROJECT_ROOT, "final_probabilistic_*.pth")):
                    move_to_output(model_file)

                for metadata_file in glob.glob(os.path.join(PROJECT_ROOT, "*_modell_metadaten_*.json")):
                    move_to_output(metadata_file)

            except subprocess.CalledProcessError:
                st.error("Fehler während der Ausführung! Ein Skript ist abgebrochen.")
                st.info("Bitte prüfe die Datei 'pipeline_protokoll.txt' im Output-Ordner.")
                fehler_aufgetreten = True
            except Exception as exc:
                st.error(f"Unerwarteter Systemfehler: {exc}")
                fehler_aufgetreten = True

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    move_to_output(log_path)

    if not fehler_aufgetreten:
        generate_dashboard_bundle(OUTPUT_DIR)
        st.session_state["active_page"] = "Ergebnisse"
        rerun_app()


def render_pipeline_page():
    """Zeige Upload, optionalen Wetterdaten-Upload und Pipeline-Start."""

    st.title("SMARD Probabilistische Energiedatenvorhersage")
    st.write("Lade eine SMARD-CSV-Datei hoch, um die EDA und das Modelltraining zu starten.")

    uploaded_file = st.file_uploader("SMARD CSV-Datei auswählen", type=["csv"])
    weather_file = st.file_uploader("Optionale Wetter-CSV auswählen", type=["csv"])

    if uploaded_file is not None and st.button("Pipeline starten"):
        run_pipeline(uploaded_file, weather_file)

    if glob.glob(os.path.join(OUTPUT_DIR, "*_metriken_*.csv")):
        st.divider()
        if st.button("Vorhandene Ergebnisse anzeigen"):
            st.session_state["active_page"] = "Ergebnisse"
            rerun_app()


def render_project_information_page():
    """Erläutere Ziel, Ablauf, Auswertung und Grenzen des Projekts."""

    st.title("Projektinformationen")
    st.caption("Überblick über Datenbasis, Modellierung und Aussagekraft der Ergebnisse")

    st.markdown(
        """
## Worum geht es?

Diese Anwendung erstellt eine probabilistische Vorhersage für die Photovoltaik-Einspeisung. Statt einer reinen 
Punktprognose berechnet das System zusätzlich einen Unsicherheitsbereich um die Schätzung herum, um transparent 
darzustellen, wie verlässlich eine Prognose in der jeweiligen Situation ist.

**Beispiel:** Eine klassische Punktprognose liefert einen fixen Wert (z. B. 20.000 MWh zu einem bestimmten Zeitpunkt). 
Eine probabilistische Vorhersage ergänzt diesen Median um ein Intervall (z. B. 17.000 bis 23.000 MWh). Dieser 
Korridor ist für Netzbetreiber, Risikomanagement und Ausgleichsenergieplanung deutlich informativer.

## Warum das Projekt sinnvoll ist

Die Photovoltaik-Einspeisung unterliegt starken witterungs- und tageszeitbedingten Fluktuationen. Nachts wird kein 
Strom erzeugt, während tagsüber Sonnenstand, Bewölkung, Temperatur und Aerosole die Einspeisung bestimmen. Um den 
Bedarf an kurzfristiger, kostenintensiver Ausgleichsenergie zu minimieren, quantifiziert diese Pipeline die 
verbleibende Unsicherheit mathematisch über eine Quantilregression mit Pinball Loss.

## Verwendete Datenbasis

- **SMARD-Marktdaten:** Die Pipeline verarbeitet CSV-Exporte der Bundesnetzagentur (SMARD). Genutzt werden primär die Zeitreihen der Photovoltaik-Einspeisung sowie Wind-Onshore- und Erdgaserzeugung.
- **Zyklische Merkmale:** Uhrzeit und Wochentag werden trigonometrisch (`hour_sin`, `hour_cos`, `weekday_sin`, `weekday_cos`, `is_weekend`) kodiert, um stetige Übergänge (z. B. von 23:00 Uhr auf 00:00 Uhr) abzubilden.
- **Optionale Wetterdaten:** Über eine separate CSV-Datei können meteorologische Parameter (z. B. Globalstrahlung, Bewölkung, Temperatur) integriert werden, die über einen zeitbasierten Join mit den Marktdaten zusammengeführt werden.

## Pipeline-Ablauf

1. **Bereinigung:** Konvertierung deutscher Zahlenformate (Komma/Punkt), Validierung des Zeitstempel-Indexes und automatisches Erkennen der zeitlichen Granularität.
2. **Explorative Datenanalyse (EDA):** Erstellung von Summenverläufen, mittleren Tagesprofilen und Korrelationsmatrizen.
3. **Chronologischer Split & Skalierung:** Strikt sequentieller Split in Training, Validierung und Test. Der `MinMaxScaler` wird zur Vermeidung von Data Leakage ausschließlich auf dem Trainingssplit angepasst.
4. **Sequenzerstellung:** Umwandlung in dreidimensionale PyTorch-Tensoren mit einem 24-Stunden-Lookback-Fenster.
5. **Modelltraining (LSTM vs. RNN):** Vergleich eines Long Short-Term Memory Netzwerks mit einem klassischen Recurrent Neural Network unter identischen Hyperparametern und Optimierungsbedingungen.
6. **Probabilistische Ausgabe:** Schätzung dreier Quantile (`q0.1`, `q0.5`, `q0.9`) über den Pinball Loss mit integrierter Quantile Crossing Penalty zur Absicherung der monotonen Ordnung.

## Evaluationsmetriken

- **PICP (Prediction Interval Coverage Probability):** Misst den Anteil der Testdaten, der real innerhalb des 80-%-Intervalls liegt (Sollwert: ca. 80 %).
- **Mittlere Intervallbreite:** Gibt die durchschnittliche Breite des Unsicherheitsbandes in MWh an (je schmaler bei korrekter Abdeckung, desto präziser).
- **Median-RMSE:** Wurzel der mittleren Fehlerquadratsumme der zentralen Punktprognose (`q0.5`).
- **Pinball Loss:** Spezifische Quantilsverlustfunktion zur individuellen Gütebewertung aller drei Quantilsgrenzen.
- **Winkler Score:** Kombinierte Metrik, die schmale Intervalle honoriert und Werte außerhalb der Grenzen mathematisch sanktioniert.
- **Quantile Crossing Rate:** Überprüft, ob die physikalisch monotone Ordnung (`q0.1 <= q0.5 <= q0.9`) eingehalten wurde.

## Erklärbarkeit & Dashboard

Das Dashboard fasst Metriken, Visualisierungen und Protokolle zusammen. Über eine **Permutation Feature Importance** wird ermittelt, welche Eingangsmerkmale den größten Einfluss auf die Reduktion des Pinball Loss haben. Die textlichen Bewertungen basieren auf festen, nachvollziehbaren Schwellenwerten (z. B. bis zu drei Prozentpunkte Abweichung vom 80-%-PICP-Ziel gelten als gut kalibriert).

## Grenzen des Systems

- Es handelt sich um ein akademisches Demonstrations- und Forschungsprojekt, nicht um ein operatives Handelssystem.
- Ohne hochaufgelöste numerische Wettervorhersagen basieren die Prognosen primär auf der historischen Persistenz und zeitlichen Periodizitäten.
- Eventuelle Datenlücken werden vor dem chronologischen Split zeitlich interpoliert; dieser Aspekt ist bei der Interpretation der Metriken zu berücksichtigen.

## Datenschutz und lokaler Betrieb

Die Bereitstellung erfolgt containerisiert via Docker. Die gesamte Datenverarbeitung erfolgt lokal in den Verzeichnissen `data/input` und `data/output`. Es werden keine Daten an externe Schnittstellen oder Cloud-Dienste übermittelt.
        """
    )


st.set_page_config(page_title="SMARD Energiedatenvorhersage", layout="wide")


def render_sidebar_navigation():
    """Zeige die Seitennavigation und aktualisiere den aktiven Seitenzustand."""

    st.sidebar.markdown("### Navigation")

    if st.sidebar.button(
        "Pipeline",
        key="sidebar_pipeline_button",
        type="primary" if st.session_state["active_page"] == "Pipeline" else "secondary",
        use_container_width=True,
    ):
        st.session_state["active_page"] = "Pipeline"
        rerun_app()

    if st.sidebar.button(
        "Ergebnisse",
        key="sidebar_results_button",
        type="primary" if st.session_state["active_page"] == "Ergebnisse" else "secondary",
        use_container_width=True,
    ):
        st.session_state["active_page"] = "Ergebnisse"
        rerun_app()

    if st.sidebar.button(
        "Projektinformationen",
        key="sidebar_project_information_button",
        type="primary" if st.session_state["active_page"] == "Projektinformationen" else "secondary",
        use_container_width=True,
    ):
        st.session_state["active_page"] = "Projektinformationen"
        rerun_app()


def main():
    """Initialisiere den Seitenzustand und rendere die ausgewählte Ansicht."""

    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "Pipeline"

    render_sidebar_navigation()

    if st.session_state["active_page"] == "Projektinformationen":
        render_project_information_page()
    elif st.session_state["active_page"] == "Ergebnisse":
        render_dashboard()
    else:
        render_pipeline_page()


try:
    main()
except Exception as exc:
    if is_streamlit_control_exception(exc):
        raise
    error_log_path = write_streamlit_error(exc)
    st.error("Die Streamlit-Ansicht ist in einen Python-Fehler gelaufen.")
    st.info(f"Details wurden in `{error_log_path}` gespeichert.")
    st.exception(exc)
