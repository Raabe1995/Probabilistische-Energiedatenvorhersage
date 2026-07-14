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

from dashboard_utils import generate_dashboard_bundle, load_dashboard_bundle


INPUT_DIR = "/app/data/input" if os.path.exists("/app") else "smard_daten/input"
OUTPUT_DIR = "/app/data/output" if os.path.exists("/app") else "smard_daten/output"
STREAMLIT_ERROR_LOG = "streamlit_error.log"

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
    if os.path.exists(file_path):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        target_path = os.path.join(OUTPUT_DIR, os.path.basename(file_path))
        if os.path.exists(target_path):
            os.remove(target_path)
        shutil.move(file_path, target_path)


def latest_file(pattern):
    files = glob.glob(os.path.join(OUTPUT_DIR, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def read_csv(path):
    return pd.read_csv(path, sep=";")


def read_metrics(model_prefix):
    path = latest_file(f"{model_prefix}_metriken_*.csv")
    if not path:
        return {}, None
    df = read_csv(path)
    return dict(zip(df["metric"], df["value"])), path


def read_table(pattern):
    path = latest_file(pattern)
    if not path:
        return None, None
    return read_csv(path), path


def read_metadata(model_prefix):
    path = latest_file(f"{model_prefix}_modell_metadaten_*.json")
    if not path:
        return {}, None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle), path


def dataframe_records(pattern, limit=8):
    df, _ = read_table(pattern)
    if df is None:
        return []
    return df.head(limit).to_dict(orient="records")


def read_log_tail(max_chars=5000):
    log_path = os.path.join(OUTPUT_DIR, "pipeline_protokoll.txt")
    if not os.path.exists(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    return content[-max_chars:]


def rerun_app():
    rerun = getattr(st, "rerun", None)
    if rerun is not None:
        rerun()
    st.experimental_rerun()


def write_streamlit_error(exc):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(OUTPUT_DIR, STREAMLIT_ERROR_LOG)
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write("\n" + "=" * 80 + "\n")
        handle.write(f"{type(exc).__name__}: {exc}\n")
        handle.write(traceback.format_exc())
    return log_path


def is_streamlit_control_exception(exc):
    return type(exc).__name__ in {"RerunException", "StopException"}


def format_number(value, suffix=""):
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


def render_dashboard_styles():
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
    if value is None:
        return ""
    return html.escape(str(value))


def image_data_uri(path):
    extension = os.path.splitext(path)[1].lower()
    mime_type = "image/png" if extension == ".png" else "application/octet-stream"
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_safe_image(path, caption):
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
    path = latest_file(pattern)
    if path:
        render_safe_image(path, caption)
    else:
        st.info(f"{caption} wurde noch nicht erzeugt.")


def render_bundle_image(dashboard, image_key, caption):
    image_info = dashboard.get("images", {}).get(image_key, {})
    path = image_info.get("display_path") or image_info.get("source_path")
    if path and os.path.exists(path):
        render_safe_image(path, caption)
    else:
        st.info(f"{caption} wurde noch nicht erzeugt.")


def render_records_table(records, title, download_path=None, download_key=None):
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

        with open("pipeline_protokoll.txt", "w") as log_file:
            try:
                st.text("Starte EDA...")
                eda_command = [sys.executable, "eda.py", input_csv_path]
                if weather_csv_path:
                    eda_command.extend(["--weather-csv", weather_csv_path])
                subprocess.run(eda_command, stdout=log_file, stderr=log_file, check=True)

                st.text("Trainiere LSTM Modell...")
                subprocess.run([sys.executable, "train_lstm.py"], stdout=log_file, stderr=log_file, check=True)

                st.text("Trainiere RNN Modell...")
                subprocess.run([sys.executable, "train_rnn.py"], stdout=log_file, stderr=log_file, check=True)

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

                for png_file in glob.glob("*.png"):
                    move_to_output(png_file)

                generated_csvs = []
                for pattern in [
                    "*_daten_*.csv",
                    "*_metriken_*.csv",
                    "*_kalibrierung_daten_*.csv",
                    "*_feature_importance_*.csv",
                ]:
                    generated_csvs.extend(glob.glob(pattern))
                for csv_file in generated_csvs:
                    move_to_output(csv_file)

                for model_file in glob.glob("final_probabilistic_*.pth"):
                    move_to_output(model_file)

                for metadata_file in glob.glob("*_modell_metadaten_*.json"):
                    move_to_output(metadata_file)

            except subprocess.CalledProcessError:
                st.error("Fehler während der Ausführung! Ein Skript ist abgebrochen.")
                st.info("Bitte prüfe die Datei 'pipeline_protokoll.txt' im Output-Ordner.")
                fehler_aufgetreten = True
            except Exception as exc:
                st.error(f"Unerwarteter Systemfehler: {exc}")
                fehler_aufgetreten = True

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    move_to_output("pipeline_protokoll.txt")

    if not fehler_aufgetreten:
        generate_dashboard_bundle(OUTPUT_DIR)
        st.session_state["active_page"] = "Ergebnisse"
        rerun_app()


def render_pipeline_page():
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


def render_impressum_page():
    st.title("Impressum und Projekterklärung")
    st.caption(
        "Diese Seite erklärt das Projekt verständlich für Außenstehende. "
        "Rechtliche Anbieterangaben wie Name, Anschrift und Kontakt müssen bei einer Veröffentlichung ergänzt werden."
    )

    st.markdown(
        """
## Kurz erklärt

Diese Anwendung erstellt eine probabilistische Vorhersage für die Photovoltaik-Einspeisung. Das bedeutet:
Sie versucht nicht nur einen einzelnen zukünftigen Wert zu schätzen, sondern zusätzlich einen Unsicherheitsbereich
um diese Schätzung herum. Dadurch wird sichtbar, wie sicher oder unsicher eine Prognose ist.

Ein einfaches Beispiel: Eine klassische Vorhersage sagt vielleicht: Morgen um 12 Uhr werden 20.000 MWh
Photovoltaik-Strom eingespeist. Eine probabilistische Vorhersage sagt zusätzlich: Der realistische Bereich
liegt wahrscheinlich zwischen 17.000 und 23.000 MWh. Diese zweite Aussage ist für Planung und Risikobewertung
oft wertvoller als nur ein einzelner Punktwert.

## Warum dieses Projekt sinnvoll ist

Strom aus Photovoltaik schwankt stark. Nachts wird kein Solarstrom erzeugt, tagsüber hängt die Erzeugung von
Sonnenstand, Jahreszeit, Wolken, Temperatur, Wetterlage und vielen weiteren Faktoren ab. Für Stromnetz,
Energiehandel und Versorgungssicherheit ist es wichtig, solche Schwankungen möglichst gut einzuschätzen.

Der zentrale Gedanke dieses Projekts ist deshalb: Eine Prognose sollte nicht so tun, als wäre die Zukunft exakt
bekannt. Stattdessen soll sie ihre eigene Unsicherheit sichtbar machen. Genau das leistet der probabilistische
Ansatz mit Quantilen.

## Welche Daten verwendet werden

Die Anwendung erwartet eine SMARD-CSV-Datei mit Energiedaten. SMARD stellt öffentliche Strommarktdaten bereit.
Im Projekt werden insbesondere Spalten zur Photovoltaik-Erzeugung und weitere Energiegrößen wie Wind Onshore
oder Erdgas genutzt, sofern sie in der Datei vorhanden sind.

Optional kann zusätzlich eine Wetter-CSV hochgeladen werden. Wetterdaten sind fachlich besonders wichtig,
weil Photovoltaik direkt vom Wetter abhängt. Nützliche Wettermerkmale wären zum Beispiel Globalstrahlung,
Bewölkung, Temperatur oder Wettervorhersagen. Wenn solche Daten vorliegen, kann die Pipeline sie als zusätzliche
Eingangsvariablen verwenden.

## Was beim Start der Pipeline passiert

Nach dem Upload der CSV-Datei führt die Anwendung mehrere Schritte automatisch aus.

### 1. Daten einlesen und bereinigen

Zuerst wird die CSV-Datei eingelesen. Da deutsche Energiedaten häufig Semikolon-getrennt sind und Zahlen im
deutschen Format enthalten können, werden Datumswerte, Spaltennamen und Zahlenformate vereinheitlicht. Aus
Textwerten wie `4.167,28` werden numerische Werte, mit denen Python rechnen kann.

### 2. Explorative Datenanalyse

Danach erstellt die Anwendung erste Analyse-Grafiken. Diese zeigen zum Beispiel den zeitlichen Verlauf der
Energieerzeugung, typische Tagesprofile und Zusammenhänge zwischen den Variablen. Dieser Schritt hilft dabei,
die Daten überhaupt zu verstehen, bevor Modelle trainiert werden.

### 3. Feature Engineering

Maschinelle Lernmodelle brauchen erklärende Eingangsgrößen, sogenannte Features. Neben den Energiedaten werden
zeitliche Informationen ergänzt. Die Uhrzeit und der Wochentag werden nicht einfach als Zahl verwendet, sondern
zyklisch codiert. Das ist wichtig, weil 23 Uhr und 0 Uhr zeitlich nah beieinander liegen, obwohl die Zahlen 23
und 0 weit auseinander aussehen.

### 4. Chronologischer Train/Test-Split

Zeitreihendaten dürfen nicht zufällig gemischt werden, weil sonst Informationen aus der Zukunft ins Training
gelangen könnten. Deshalb teilt die Pipeline die Daten zeitlich auf: Erst kommt der Trainingszeitraum, danach
Validierung und Test. Auch die Skalierung wird nur auf den Trainingsdaten gelernt. So wird vermieden, dass das
Modell indirekt Informationen aus dem Testzeitraum sieht.

### 5. Modelltraining mit LSTM und RNN

Die Anwendung trainiert zwei neuronale Zeitreihenmodelle: ein LSTM und ein einfacheres RNN. Beide Modelle sehen
nicht nur einen einzelnen Zeitpunkt, sondern ein Fenster vergangener Werte. Daraus lernen sie zeitliche Muster,
zum Beispiel Tagesrhythmen oder wiederkehrende Verläufe.

Das LSTM ist eine weiterentwickelte RNN-Variante und kann langfristige Zusammenhänge oft besser speichern. Das
RNN ist einfacher und dient als Vergleichsmodell. Durch beide Modelle kann man sehen, ob die komplexere Struktur
im konkreten Lauf wirklich Vorteile bringt.

### 6. Probabilistische Vorhersage über Quantile

Die Modelle geben drei Quantile aus:

- `q0.1`: ein eher niedriger Schätzwert
- `q0.5`: der Median, also die mittlere Prognose
- `q0.9`: ein eher hoher Schätzwert

Zwischen `q0.1` und `q0.9` entsteht ein 80%-Vorhersageintervall. Wenn das Modell gut kalibriert ist, sollten
ungefähr 80% der echten Werte in diesem Bereich liegen.

## Wie die Ergebnisse bewertet werden

Die Anwendung berechnet mehrere Kennzahlen, weil eine einzelne Kennzahl nicht ausreicht.

### PICP

PICP misst, wie viele echte Werte innerhalb des Vorhersageintervalls liegen. Bei einem 80%-Intervall wäre ein
Wert nahe 80% wünschenswert. Ein deutlich niedrigerer Wert bedeutet, dass das Intervall zu eng ist. Ein deutlich
höherer Wert kann bedeuten, dass das Intervall zu breit und damit wenig informativ ist.

### Mittlere Intervallbreite

Diese Kennzahl zeigt, wie breit der Unsicherheitsbereich im Durchschnitt ist. Ein sehr breites Intervall deckt
zwar viele reale Werte ab, hilft aber weniger bei konkreter Planung. Gute probabilistische Prognosen sollen also
nicht nur viele Werte abdecken, sondern dabei möglichst präzise bleiben.

### Median-RMSE

Der RMSE misst den Fehler der mittleren Prognose, also des Medians `q0.5`. Er zeigt, wie weit die zentrale
Vorhersage im Durchschnitt von der Realität entfernt ist. Je niedriger der RMSE, desto näher liegt die
Punktprognose an den echten Werten.

### Pinball Loss

Der Pinball Loss bewertet die einzelnen Quantile. Er ist speziell für Quantilprognosen gedacht und bestraft
falsche Unsicherheitsgrenzen passend zu ihrem Quantilniveau.

### Winkler Score

Der Winkler Score bewertet Intervallprognosen. Er berücksichtigt sowohl die Breite des Intervalls als auch
Fehler, wenn echte Werte außerhalb des Intervalls liegen. Dadurch ist er nützlich, um zu erkennen, ob ein Modell
präzise und gut kalibriert ist.

### Quantilkreuzungen

Bei einer sauberen Quantilprognose muss gelten: `q0.1 <= q0.5 <= q0.9`. Wenn diese Reihenfolge verletzt wird,
spricht man von Quantilkreuzungen. Die Pipeline bestraft solche Kreuzungen im Training und sortiert die Quantile
vor der Ausgabe zusätzlich, damit die Ergebnisdarstellung fachlich konsistent bleibt.

## Was das Dashboard zeigt

Nach erfolgreichem Pipeline-Lauf wechselt die Anwendung in ein Ergebnis-Dashboard. Dort werden die wichtigsten
Metriken, Vorhersagegrafiken, Lernkurven, Kalibrierungsplots, Feature Importance und erzeugten Dateien
strukturiert angezeigt.

Die Feature Importance hilft zu verstehen, welche Eingangsvariablen für die Modellvorhersage besonders relevant
waren. Sie ersetzt keine vollständige Kausalanalyse, gibt aber eine erste Orientierung, welche Merkmale das
Modell stark nutzt.

## Wie die regelbasierte Interpretation funktioniert

Das Dashboard enthält kurze erklärende Sätze zu den wichtigsten Kennzahlen. Diese Sätze werden nicht frei
formuliert oder generativ erzeugt, sondern durch feste, transparente Regeln aus den berechneten Metriken
abgeleitet.

Ein Beispiel ist die Intervallabdeckung, also PICP. Weil das Modell mit `q0.1` und `q0.9` arbeitet, entsteht ein
nominelles 80%-Vorhersageintervall. Die Interpretation vergleicht deshalb den gemessenen PICP-Wert mit dem
80%-Ziel. Liegt der Wert sehr nah bei 80%, wird das Intervall als gut kalibriert eingeordnet. Liegt er deutlich
darunter, wirkt das Intervall zu eng. Liegt er deutlich darüber, wirkt das Intervall eher konservativ breit.

Konkret verwendet das Dashboard feste Schwellenwerte: Bis zu 3 Prozentpunkte Abweichung vom 80%-Ziel gelten als
sehr nah am Zielbereich. Zwischen 3 und 8 Prozentpunkten wird die Abweichung als leicht eingeordnet. Bei mehr als
8 Prozentpunkten spricht das Dashboard von einer deutlichen Fehlkalibrierung, entweder zu eng oder zu breit.

Auch Quantilkreuzungen werden regelbasiert eingeordnet. Bei einer konsistenten Quantilprognose muss gelten:
`q0.1 <= q0.5 <= q0.9`. Wenn diese Reihenfolge verletzt wird, weist das Dashboard darauf hin. Zusätzlich wird
angezeigt, ob Rohprognosen vor der Sortier-Absicherung solche Kreuzungen enthielten.

Für den Vergleich zwischen LSTM und RNN betrachtet das Dashboard mehrere Metriken gemeinsam: Median-RMSE,
Winkler Score und die Nähe des PICP-Werts zum 80%-Ziel. Das Modell mit dem niedrigeren Median-RMSE, dem
niedrigeren Winkler Score und der kleineren PICP-Abweichung erhält jeweils einen Vorteil. Die mittlere
Intervallbreite wird bewusst nur als Kontext genannt, weil ein engeres Intervall nicht automatisch besser ist,
wenn dadurch echte Werte häufiger außerhalb des Intervalls liegen.

Diese regelbasierte Interpretation soll die Zahlen verständlicher machen. Sie ersetzt keine fachliche Bewertung,
sondern zeigt nachvollziehbar, warum ein Ergebnis als eher eng, eher breit oder näher am Zielbereich beschrieben
wird. Der Vorteil ist, dass dieselben Zahlen immer dieselbe Einordnung erzeugen und die Aussagen reproduzierbar
bleiben.

## Was diese Anwendung nicht leisten kann

Die Anwendung ist ein Forschungs- und Demonstrationsprojekt. Sie ersetzt keine professionelle operative
Energieprognose. Insbesondere ohne echte Wettervorhersagen bleibt die Prognose fachlich begrenzt, weil
Photovoltaik stark wetterabhängig ist.

Außerdem arbeitet das Modell mit historischen Mustern. Unerwartete Ereignisse, Datenfehler, extreme Wetterlagen
oder strukturelle Änderungen im Stromsystem können zu schlechten Vorhersagen führen. Die Ergebnisse sollten
deshalb immer kritisch geprüft und nicht blind übernommen werden.

## Warum das Projekt trotzdem wertvoll ist

Das Projekt zeigt den gesamten Weg von Rohdaten über Datenbereinigung, Feature Engineering, Modelltraining,
probabilistische Bewertung und Ergebnisinterpretation. Es macht sichtbar, dass moderne Prognosesysteme nicht nur
einen Wert ausgeben sollten, sondern auch Unsicherheit kommunizieren müssen.

Gerade für Präsentationen oder wissenschaftliche Arbeiten ist das wichtig: Die Qualität eines Modells besteht
nicht nur darin, manchmal nah am echten Wert zu liegen, sondern auch darin, ehrlich mit Unsicherheit umzugehen.

## Datenschutz und lokaler Betrieb

Die Anwendung ist für den lokalen Betrieb ausgelegt. Eingabedaten werden in den lokalen Projektordnern
`smard_daten/input` und `smard_daten/output` verarbeitet. Es sind keine externen Cloud-Dienste erforderlich.

## Verantwortlichkeit bei Veröffentlichung

Diese Seite erklärt das Projekt fachlich. Falls die Anwendung öffentlich bereitgestellt wird, sollten hier
zusätzlich echte Impressumsangaben ergänzt werden, zum Beispiel verantwortliche Person, Anschrift, Kontakt und
gegebenenfalls institutioneller Kontext.
        """
    )


st.set_page_config(page_title="SMARD Energiedatenvorhersage", layout="wide")


def render_sidebar_navigation():
    st.sidebar.markdown("### Workspace")

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
        "Impressum",
        key="sidebar_impressum_button",
        type="primary" if st.session_state["active_page"] == "Impressum" else "secondary",
        use_container_width=True,
    ):
        st.session_state["active_page"] = "Impressum"
        rerun_app()


def main():
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "Pipeline"

    render_sidebar_navigation()

    if st.session_state["active_page"] == "Impressum":
        render_impressum_page()
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
