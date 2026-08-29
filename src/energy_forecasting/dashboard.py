"""Dashboard-Bundle aus den von der Trainingspipeline erzeugten Dateien aufbauen."""

import glob
import json
import os
from datetime import datetime

import pandas as pd
from PIL import Image


BUNDLE_FILENAME = "dashboard_summary.json"
ASSET_DIRNAME = "dashboard_assets"

IMAGE_PATTERNS = {
    "lstm_forecast": "lstm_vorhersage_intervall_*.png",
    "rnn_forecast": "rnn_vorhersage_intervall_*.png",
    "lstm_learning_curve": "lstm_lernkurve_*.png",
    "rnn_learning_curve": "rnn_lernkurve_*.png",
    "eda_energy": "eda_energieerzeugung_*.png",
    "eda_daily_profile": "eda_tagesprofil_*.png",
    "eda_correlation": "eda_korrelations_heatmap_*.png",
    "lstm_calibration": "lstm_kalibrierung_*.png",
    "rnn_calibration": "rnn_kalibrierung_*.png",
    "lstm_feature_importance": "lstm_feature_importance_*.png",
    "rnn_feature_importance": "rnn_feature_importance_*.png",
}


def latest_file(output_dir, pattern):
    """Gib die zuletzt geänderte Datei eines Musters im Ausgabeordner zurück."""

    files = glob.glob(os.path.join(output_dir, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def json_safe(value):
    """Wandle Pandas- und NumPy-Skalare in JSON-kompatible Werte um."""

    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


def read_csv_records(path, limit=None):
    """Lese eine Semikolon-CSV als JSON-kompatible Datensatzliste."""

    if not path or not os.path.exists(path):
        return []
    df = pd.read_csv(path, sep=";")
    if limit is not None:
        df = df.head(limit)
    return [
        {str(key): json_safe(value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def read_metrics(output_dir, model_prefix):
    """Lade Pfad, Einzelwerte und Tabellenzeilen der neuesten Modellmetriken."""

    path = latest_file(output_dir, f"{model_prefix}_metriken_*.csv")
    records = read_csv_records(path)
    metrics = {}
    for row in records:
        metric = row.get("metric")
        value = row.get("value")
        if metric is not None:
            metrics[str(metric)] = value
    return {"path": path, "values": metrics, "records": records}


def read_metadata(output_dir, model_prefix):
    """Lade Pfad und Inhalt der neuesten Modellmetadaten."""

    path = latest_file(output_dir, f"{model_prefix}_modell_metadaten_*.json")
    if not path or not os.path.exists(path):
        return {"path": None, "values": {}}
    with open(path, "r", encoding="utf-8") as handle:
        return {"path": path, "values": json.load(handle)}


def read_log_tail(output_dir, max_chars=8000):
    """Lade Pfad und begrenzten Schlussabschnitt des Pipeline-Protokolls."""

    path = os.path.join(output_dir, "pipeline_protokoll.txt")
    if not os.path.exists(path):
        return {"path": None, "tail": ""}
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    return {"path": path, "tail": content[-max_chars:]}


def make_thumbnail(source_path, assets_dir, max_size=(1400, 900)):
    """Erzeuge eine RGB-Vorschau und verwende bei Lesefehlern das Original."""

    if not source_path or not os.path.exists(source_path):
        return None

    os.makedirs(assets_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    target_path = os.path.join(assets_dir, f"{base_name}_thumb.png")

    try:
        with Image.open(source_path) as image:
            image = image.convert("RGB")
            image.thumbnail(max_size)
            image.save(target_path, format="PNG", optimize=True)
    except Exception:
        return source_path

    return target_path


def collect_images(output_dir, create_thumbnails=True):
    """Ordne jedem Dashboard-Bildschlüssel Original- und optionalen Vorschaupfad zu."""

    assets_dir = os.path.join(output_dir, ASSET_DIRNAME)
    images = {}
    for key, pattern in IMAGE_PATTERNS.items():
        source_path = latest_file(output_dir, pattern)
        thumb_path = make_thumbnail(source_path, assets_dir) if source_path and create_thumbnails else None
        images[key] = {
            "source_path": source_path,
            "display_path": thumb_path,
        }
    return images


def collect_file_list(output_dir):
    """Beschreibe die direkt im Ausgabeordner liegenden Dateien für das Dashboard."""

    files = sorted(
        file_path for file_path in glob.glob(os.path.join(output_dir, "*")) if os.path.isfile(file_path)
    )
    return [
        {
            "Datei": os.path.basename(file_path),
            "Groesse_KB": round(os.path.getsize(file_path) / 1024, 1),
            "Pfad": file_path,
        }
        for file_path in files
    ]


def newest_output_mtime(output_dir):
    """Ermittle den neuesten Änderungszeitpunkt ohne Bundle-Zwischendateien."""

    newest = 0
    for file_path in glob.glob(os.path.join(output_dir, "*")):
        file_name = os.path.basename(file_path)
        if os.path.isfile(file_path) and file_name not in {BUNDLE_FILENAME, f"{BUNDLE_FILENAME}.tmp"}:
            newest = max(newest, os.path.getmtime(file_path))
    return newest


def bundle_path(output_dir):
    """Erzeuge den vollständigen Pfad des Dashboard-Bundles."""

    return os.path.join(output_dir, BUNDLE_FILENAME)


def build_dashboard_summary(output_dir, create_thumbnails=True):
    """Fasse die aktuellen Pipeline-Artefakte zu einer Dashboard-Struktur zusammen.

    Die Rückgabe enthält Erzeugungszeit, Metriken, Modellmetadaten,
    Tabellenauszüge, Bildpfade, Dateiliste und den Schluss des Laufprotokolls.
    Sie ist vollständig JSON-serialisierbar.
    """

    os.makedirs(output_dir, exist_ok=True)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metrics": {
            "lstm": read_metrics(output_dir, "lstm"),
            "rnn": read_metrics(output_dir, "rnn"),
        },
        "metadata": {
            "lstm": read_metadata(output_dir, "lstm"),
            "rnn": read_metadata(output_dir, "rnn"),
        },
        "tables": {
            "lstm_feature_importance": read_csv_records(latest_file(output_dir, "lstm_feature_importance_*.csv"), limit=12),
            "rnn_feature_importance": read_csv_records(latest_file(output_dir, "rnn_feature_importance_*.csv"), limit=12),
            "lstm_calibration": read_csv_records(latest_file(output_dir, "lstm_kalibrierung_daten_*.csv")),
            "rnn_calibration": read_csv_records(latest_file(output_dir, "rnn_kalibrierung_daten_*.csv")),
            "lstm_metrics": read_metrics(output_dir, "lstm")["records"],
            "rnn_metrics": read_metrics(output_dir, "rnn")["records"],
        },
        "images": collect_images(output_dir, create_thumbnails=create_thumbnails),
        "files": collect_file_list(output_dir),
        "log": read_log_tail(output_dir),
    }


def generate_dashboard_bundle(output_dir):
    """Erzeuge das Dashboard-Bundle atomar samt verkleinerten Vorschaubildern."""

    summary = build_dashboard_summary(output_dir, create_thumbnails=True)
    target_path = bundle_path(output_dir)
    tmp_path = f"{target_path}.tmp"

    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, target_path)
    return summary


def load_dashboard_bundle(output_dir):
    """Lade das Bundle oder baue eine schreibgeschützte Ansicht aus Einzeldateien."""

    path = bundle_path(output_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                summary = json.load(handle)
            summary["_stale"] = os.path.getmtime(path) < newest_output_mtime(output_dir)
            return summary
        except (json.JSONDecodeError, OSError):
            pass

    summary = build_dashboard_summary(output_dir, create_thumbnails=False)
    summary["_stale"] = True
    return summary
