"""Gemeinsame Datenaufbereitung, Trainings- und Evaluationslogik für LSTM und RNN.

Das Modul hält Split, Skalierung, Verlustfunktionen, Metriken und Artefaktexport
für beide Architekturen identisch. Modellmodule liefern lediglich die jeweilige
PyTorch-Architektur über eine Fabrikfunktion.
"""

from __future__ import annotations

import json
import os
import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Sequence

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, TensorDataset


CLEANED_DATA_PATH = "Realisierte_Erzeugung_Cleaned.csv"
DEFAULT_SEED = 42
DEFAULT_QUANTILES = (0.1, 0.5, 0.9)
TARGET_COVERAGE = 0.8
DEFAULT_CROSSING_PENALTY_WEIGHT = 0.2

WEATHER_FEATURE_KEYWORDS = (
    "weather_",
    "globalstrahlung",
    "solarstrahlung",
    "irradiance",
    "radiation",
    "ghi",
    "dni",
    "dhi",
    "bewoelkung",
    "bewolkung",
    "cloud",
    "temperatur",
    "temperature",
    "humidity",
    "feuchte",
    "wind_speed",
    "windgeschwindigkeit",
)


@dataclass
class PreparedData:
    """Chronologisch getrennte Tensoren samt Skalierern und Testzeitpunkten.

    Featuretensoren haben die Form ``(Sequenzen, Fenster, Features)``;
    Zieltensoren enthalten pro Sequenz den unmittelbar folgenden PV-Wert.
    """

    X_train: torch.Tensor
    y_train: torch.Tensor
    X_val: torch.Tensor
    y_val: torch.Tensor
    X_test: torch.Tensor
    y_test: torch.Tensor
    test_index: pd.DatetimeIndex
    scaler_features: MinMaxScaler
    scaler_target: MinMaxScaler
    split_counts: dict[str, int]


def set_reproducibility(seed: int = DEFAULT_SEED) -> None:
    """Setze Zufallsquellen und CuDNN-Optionen für reproduzierbare Läufe."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def coerce_german_number_series(series: pd.Series) -> pd.Series:
    """Konvertiere eine Spalte mit deutschen Zahlenformaten in numerische Werte."""

    cleaned = series.astype(str).str.strip()
    cleaned = cleaned.mask(cleaned.isin(["", "-", "–", "—"]))
    cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def make_safe_name(value: str) -> str:
    """Erzeuge einen ASCII-Bezeichner für Feature- und Dateinamen."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^0-9A-Za-z_]+", "_", normalized.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "feature"


def read_csv_flexible(path: str) -> pd.DataFrame:
    """Lese eine CSV mit Semikolon-, Komma- oder automatisch erkanntem Trenner."""

    for sep in (";", ","):
        df = pd.read_csv(path, sep=sep)
        if len(df.columns) > 1:
            return df
    return pd.read_csv(path)


def find_timestamp_column(df: pd.DataFrame) -> str:
    """Finde eine übliche Zeitstempelspalte oder löse einen verständlichen Fehler aus."""

    preferred = ("Timestamp", "Datum von", "datetime", "DateTime", "date", "Date", "time", "Time")
    for col in preferred:
        if col in df.columns:
            return col

    for col in df.columns:
        lower = col.lower()
        if "zeit" in lower or "datum" in lower or "date" in lower or "time" in lower:
            return col

    raise ValueError("Keine Zeitstempelspalte gefunden. Erwartet z.B. 'Timestamp' oder 'Datum von'.")


def merge_weather_features(df: pd.DataFrame, weather_csv: str | None) -> tuple[pd.DataFrame, list[str]]:
    """Füge numerische Wetterspalten zeitlich passend mit ``weather_``-Präfix ein.

    Fehlende Wetterwerte werden wie in der bisherigen Pipeline über die gesamte
    Zeitachse interpoliert und anschließend vorwärts beziehungsweise rückwärts
    aufgefüllt. Dieses Verhalten bleibt aus Gründen der Ergebnisreproduzierbarkeit
    unverändert.
    """

    if not weather_csv:
        return df, []

    if not os.path.exists(weather_csv):
        raise FileNotFoundError(f"Wetter-CSV nicht gefunden: {weather_csv}")

    weather_df = read_csv_flexible(weather_csv)
    timestamp_col = find_timestamp_column(weather_df)
    weather_df["Timestamp"] = pd.to_datetime(weather_df[timestamp_col], dayfirst=True, errors="coerce")
    weather_df = weather_df.dropna(subset=["Timestamp"]).set_index("Timestamp").sort_index()

    feature_columns: list[str] = []
    renamed_columns: dict[str, str] = {}

    for col in weather_df.columns:
        if col == timestamp_col or col == "Timestamp":
            continue

        numeric = coerce_german_number_series(weather_df[col])
        if numeric.notna().any():
            new_col = col if col.startswith("weather_") else f"weather_{make_safe_name(col)}"
            weather_df[col] = numeric
            renamed_columns[col] = new_col
            feature_columns.append(new_col)

    if not feature_columns:
        return df, []

    weather_features = weather_df[list(renamed_columns)].rename(columns=renamed_columns)
    weather_features = weather_features[~weather_features.index.duplicated(keep="last")]

    merged = df.sort_index().join(weather_features, how="left")
    merged[feature_columns] = merged[feature_columns].interpolate(method="time").ffill().bfill()
    return merged, feature_columns


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ergänze zyklische Uhrzeit- und Wochentagsmerkmale auf einer Kopie."""

    df = df.copy()
    weekday = df.index.weekday
    df["hour"] = df.index.hour
    df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
    df["weekday"] = weekday
    df["weekday_sin"] = np.sin(2 * np.pi * weekday / 7)
    df["weekday_cos"] = np.cos(2 * np.pi * weekday / 7)
    df["is_weekend"] = np.isin(weekday, [5, 6]).astype(int)
    return df


def load_training_dataframe(path: str = CLEANED_DATA_PATH) -> pd.DataFrame:
    """Lade bereinigte Energiedaten mit sortiertem Zeitindex und Zeitmerkmalen."""

    df = pd.read_csv(path, sep=";")
    timestamp_col = "Datum von" if "Datum von" in df.columns else find_timestamp_column(df)
    df["Timestamp"] = pd.to_datetime(df[timestamp_col], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Timestamp"]).set_index("Timestamp").sort_index()
    df = add_time_features(df)
    return df.dropna(how="all")


def find_required_column(df: pd.DataFrame, needle: str) -> str:
    """Finde die erste Spalte, die den gesuchten Begriff ohne Beachtung der Großschreibung enthält."""

    matches = [col for col in df.columns if needle.lower() in col.lower()]
    if not matches:
        raise ValueError(f"Pflichtspalte mit '{needle}' nicht gefunden.")
    return matches[0]


def detect_weather_feature_columns(df: pd.DataFrame) -> list[str]:
    """Erkenne verwendbare numerische Wettermerkmale anhand bekannter Namensbestandteile."""

    weather_cols: list[str] = []
    for col in df.columns:
        lower = col.lower()
        if any(keyword in lower for keyword in WEATHER_FEATURE_KEYWORDS):
            if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any():
                weather_cols.append(col)
    return weather_cols


def select_feature_columns(df: pd.DataFrame) -> tuple[list[str], str, list[str]]:
    """Bestimme Eingabefeatures, PV-Zielspalte und optionale Wetterfeatures."""

    pv_col = find_required_column(df, "Photovoltaik")
    wind_col = find_required_column(df, "Wind Onshore")
    gas_col = find_required_column(df, "Erdgas")

    base_features = [
        pv_col,
        "hour_sin",
        "hour_cos",
        "weekday_sin",
        "weekday_cos",
        "is_weekend",
        wind_col,
        gas_col,
    ]
    weather_features = [col for col in detect_weather_feature_columns(df) if col not in base_features]

    feature_cols: list[str] = []
    for col in base_features + weather_features:
        if col in df.columns and col not in feature_cols:
            feature_cols.append(col)

    return feature_cols, pv_col, weather_features


def infer_window_size(index: pd.DatetimeIndex) -> tuple[float, int]:
    """Leite Datenauflösung und Anzahl der Schritte eines 24-Stunden-Fensters ab."""

    if len(index) < 2:
        raise ValueError("Mindestens zwei Zeitpunkte werden benoetigt.")

    time_delta_min = (index[1] - index[0]).total_seconds() / 60
    if time_delta_min <= 0:
        raise ValueError("Zeitindex ist nicht streng aufsteigend.")

    window_size = int(round((24 * 60) / time_delta_min))
    if window_size < 1:
        raise ValueError("Ungueltige Zeitaufloesung erkannt.")

    return time_delta_min, window_size


def date_range_strings(index: pd.DatetimeIndex) -> tuple[str, str]:
    """Erzeuge lesbare und dateisichere Monatsangaben für Ergebnisnamen."""

    start_date_str = index.min().strftime("%m.%Y")
    end_date_str = index.max().strftime("%m.%Y")
    date_range_str = start_date_str if start_date_str == end_date_str else f"{start_date_str} - {end_date_str}"
    safe_date_str = date_range_str.replace(".", "_").replace(" ", "").replace("-", "_")
    return date_range_str, safe_date_str


def create_sequences(features: np.ndarray, target: np.ndarray, window_size: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Erzeuge gleitende Featurefenster und den jeweils folgenden Zielwert."""

    X, y = [], []
    for i in range(len(features) - window_size):
        X.append(features[i : i + window_size])
        y.append(target[i + window_size])
    return torch.FloatTensor(np.array(X)), torch.FloatTensor(np.array(y))


def prepare_time_series_data(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
    target_col: str,
    window_size: int,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> PreparedData:
    """Bereite skalierte Sequenzen für einen chronologischen Split vor.

    ``train_ratio`` bezeichnet den Anteil vor dem Testsplit. ``val_ratio`` wird
    innerhalb dieses Anteils als Validierung abgetrennt. Die Skalierer werden
    ausschließlich auf den Trainingszeilen gefittet. Die Imputation erfolgt wie
    bisher vor dem Split über die vollständige Zeitreihe; dadurch bleiben bereits
    erzeugte Ergebnisse reproduzierbar.
    """

    needed_cols = list(dict.fromkeys(list(feature_cols) + [target_col]))
    working_df = df[needed_cols].copy()
    for col in working_df.columns:
        working_df[col] = pd.to_numeric(working_df[col], errors="coerce")
    working_df = working_df.interpolate(method="time").ffill().bfill().dropna()

    if len(working_df) <= window_size + 3:
        raise ValueError("Datensatz ist fuer das 24h-Zeitfenster zu kurz.")

    features_raw = working_df[list(feature_cols)].values
    target_raw = working_df[[target_col]].values
    total_sequences = len(working_df) - window_size

    train_val_count = int(total_sequences * train_ratio)
    test_count = total_sequences - train_val_count
    val_count = max(1, int(train_val_count * val_ratio))
    train_count = train_val_count - val_count

    if train_count < 1 or val_count < 1 or test_count < 1:
        raise ValueError("Train/Validation/Test-Split ist fuer diesen Datensatz zu klein.")

    train_feature_rows = train_count + window_size
    train_target_start = window_size
    train_target_end = window_size + train_count

    scaler_features = MinMaxScaler()
    scaler_target = MinMaxScaler()
    scaler_features.fit(features_raw[:train_feature_rows])
    scaler_target.fit(target_raw[train_target_start:train_target_end])

    scaled_features = scaler_features.transform(features_raw)
    scaled_target = scaler_target.transform(target_raw)
    X, y = create_sequences(scaled_features, scaled_target, window_size)

    X_train = X[:train_count]
    y_train = y[:train_count]
    X_val = X[train_count:train_val_count]
    y_val = y[train_count:train_val_count]
    X_test = X[train_val_count:]
    y_test = y[train_val_count:]
    target_index = working_df.index[window_size:]

    return PreparedData(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        X_test=X_test,
        y_test=y_test,
        test_index=target_index[train_val_count:],
        scaler_features=scaler_features,
        scaler_target=scaler_target,
        split_counts={
            "train_sequences": train_count,
            "validation_sequences": val_count,
            "test_sequences": test_count,
            "window_size": window_size,
        },
    )


def make_train_loader(prepared: PreparedData, seed: int, batch_size: int = 32) -> DataLoader:
    """Erzeuge einen reproduzierbar gemischten DataLoader für den Trainingssplit."""

    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        TensorDataset(prepared.X_train, prepared.y_train),
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
    )


def pinball_loss(preds: torch.Tensor, target: torch.Tensor, quantiles: Sequence[float]) -> torch.Tensor:
    """Summiere den mittleren Pinball Loss über alle vorhergesagten Quantile."""

    losses = []
    for i, q in enumerate(quantiles):
        error = target - preds[:, i : i + 1]
        losses.append(torch.max((q - 1) * error, q * error).mean())
    return sum(losses)


def quantile_crossing_penalty(preds: torch.Tensor) -> torch.Tensor:
    """Messe die mittlere positive Verletzung der aufsteigenden Quantilordnung."""

    if preds.shape[1] < 2:
        return torch.tensor(0.0, device=preds.device)
    crossing_amounts = torch.relu(preds[:, :-1] - preds[:, 1:])
    return crossing_amounts.mean()


def probabilistic_training_loss(
    preds: torch.Tensor,
    target: torch.Tensor,
    quantiles: Sequence[float],
    crossing_penalty_weight: float = DEFAULT_CROSSING_PENALTY_WEIGHT,
) -> torch.Tensor:
    """Kombiniere Pinball Loss und gewichtete Strafe für Quantilkreuzungen."""

    return pinball_loss(preds, target, quantiles) + crossing_penalty_weight * quantile_crossing_penalty(preds)


def quantile_crossing_rate_numpy(pred_matrix: np.ndarray) -> float:
    """Berechne den Anteil von Zeitpunkten mit mindestens einer Quantilkreuzung."""

    if pred_matrix.shape[1] < 2:
        return 0.0
    crossing = np.any(np.diff(pred_matrix, axis=1) < 0, axis=1)
    return float(np.mean(crossing) * 100)


def sort_quantile_predictions(preds: np.ndarray) -> np.ndarray:
    """Sortiere die vorhergesagten Quantile je Zeitschritt für konsistente Outputs."""

    return np.sort(preds, axis=1)


def pinball_loss_numpy(y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
    """Berechne den mittleren Pinball Loss eines einzelnen Quantils mit NumPy."""

    error = y_true - y_pred
    return float(np.maximum((quantile - 1) * error, quantile * error).mean())


def compute_probabilistic_metrics(
    y_true: np.ndarray,
    preds_by_quantile: Sequence[np.ndarray],
    quantiles: Sequence[float],
    target_coverage: float = TARGET_COVERAGE,
) -> tuple[dict[str, float], pd.DataFrame]:
    """Berechne Intervall-, Punkt- und Quantilmetriken in der Originaleinheit."""

    y = y_true.reshape(-1)
    pred_matrix = np.column_stack([pred.reshape(-1) for pred in preds_by_quantile])
    lower = pred_matrix[:, 0]
    median = pred_matrix[:, 1]
    upper = pred_matrix[:, 2]

    alpha = 1 - target_coverage
    below = y < lower
    above = y > upper
    interval_width = upper - lower
    winkler = interval_width.copy()
    winkler[below] += (2 / alpha) * (lower[below] - y[below])
    winkler[above] += (2 / alpha) * (y[above] - upper[above])

    metrics = {
        "PICP_80_percent": float(np.mean((y >= lower) & (y <= upper)) * 100),
        "Mean_Interval_Width_MWh": float(np.mean(interval_width)),
        "Median_RMSE_MWh": float(np.sqrt(np.mean((y - median) ** 2))),
        "Winkler_Score_80_MWh": float(np.mean(winkler)),
        "Quantile_Crossing_Rate_percent": quantile_crossing_rate_numpy(pred_matrix),
    }

    for i, q in enumerate(quantiles):
        metrics[f"Pinball_Loss_q{str(q).replace('.', '_')}_MWh"] = pinball_loss_numpy(
            y,
            pred_matrix[:, i],
            q,
        )

    calibration = pd.DataFrame(
        {
            "quantile": list(quantiles),
            "expected_coverage_percent": [q * 100 for q in quantiles],
            "observed_coverage_percent": [
                float(np.mean(y <= pred_matrix[:, i]) * 100) for i, q in enumerate(quantiles)
            ],
        }
    )
    return metrics, calibration


def save_learning_curve(
    history: dict[str, list[float]],
    architecture: str,
    safe_date_str: str,
    best_epoch: int,
    output_prefix: str,
) -> None:
    """Speichere Lernkurve und zugrunde liegende Loss-Werte als PNG und CSV."""

    plt.figure(figsize=(10, 5))
    plt.plot(history["train_loss"], label="Train Loss")
    plt.plot(history["val_loss"], label="Validation Loss")
    if best_epoch > 0:
        plt.axvline(x=best_epoch - 1, color="r", linestyle="--", label="Bester Checkpoint")
    plt.title(f"{architecture} Lernkurve (Pinball Loss + Crossing Penalty)")
    plt.xlabel("Epoche")
    plt.ylabel("Trainingsziel")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_lernkurve_{safe_date_str}.png")
    plt.close()

    df_history = pd.DataFrame(history)
    df_history.index.name = "Epoch"
    df_history.to_csv(f"{output_prefix}_lernkurve_daten_{safe_date_str}.csv", sep=";")


def save_forecast_plot(
    y_true: np.ndarray,
    preds_by_quantile: Sequence[np.ndarray],
    architecture: str,
    date_range_str: str,
    safe_date_str: str,
    output_prefix: str,
    color: str,
) -> None:
    """Speichere Messwerte, Medianprognose und 80%-Intervall als Diagramm."""

    plt.figure(figsize=(15, 7))
    plt.plot(y_true, label="Echte Erzeugung", color="black", alpha=0.6)
    plt.plot(preds_by_quantile[1], label=f"{architecture} Median Vorhersage (q0.5)", color=color, linestyle="--")
    plt.fill_between(
        range(len(y_true)),
        preds_by_quantile[0].flatten(),
        preds_by_quantile[2].flatten(),
        color=color,
        alpha=0.2,
        label="80% Unsicherheitsbereich (q0.1-q0.9)",
    )
    plt.title(f"Probabilistische Photovoltaik-Vorhersage ({architecture} {date_range_str})")
    plt.ylabel("MWh")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_vorhersage_intervall_{safe_date_str}.png")
    plt.close()


def save_calibration_plot(
    calibration: pd.DataFrame,
    architecture: str,
    safe_date_str: str,
    output_prefix: str,
) -> None:
    """Speichere erwartete gegen beobachtete Quantilabdeckung als Diagramm."""

    plt.figure(figsize=(6, 6))
    plt.plot([0, 100], [0, 100], color="gray", linestyle="--", label="Ideal")
    plt.scatter(
        calibration["expected_coverage_percent"],
        calibration["observed_coverage_percent"],
        color="black",
        zorder=3,
        label="Modell",
    )
    plt.title(f"{architecture} Quantil-Kalibrierung")
    plt.xlabel("Erwartete Abdeckung (%)")
    plt.ylabel("Beobachtete Abdeckung (%)")
    plt.xlim(0, 100)
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_kalibrierung_{safe_date_str}.png")
    plt.close()


def save_forecast_csv(
    test_index: pd.DatetimeIndex,
    y_true: np.ndarray,
    preds_by_quantile: Sequence[np.ndarray],
    output_prefix: str,
    safe_date_str: str,
) -> None:
    """Speichere Testzeitpunkte, Messwerte und drei Quantilprognosen als CSV."""

    df_forecast = pd.DataFrame(
        {
            "Timestamp": test_index.astype(str),
            "Echte_Erzeugung_MWh": y_true.flatten(),
            "Quantil_0_1_MWh": preds_by_quantile[0].flatten(),
            "Median_q0_5_MWh": preds_by_quantile[1].flatten(),
            "Quantil_0_9_MWh": preds_by_quantile[2].flatten(),
        }
    )
    df_forecast.to_csv(f"{output_prefix}_vorhersage_daten_{safe_date_str}.csv", sep=";", index=False)


def save_metrics(
    metrics: dict[str, float],
    calibration: pd.DataFrame,
    output_prefix: str,
    safe_date_str: str,
) -> None:
    """Speichere Modellmetriken und Kalibrierungswerte in getrennten CSV-Dateien."""

    metrics_df = pd.DataFrame(
        [{"metric": metric, "value": value} for metric, value in metrics.items()]
    )
    metrics_df.to_csv(f"{output_prefix}_metriken_{safe_date_str}.csv", sep=";", index=False)
    calibration.to_csv(f"{output_prefix}_kalibrierung_daten_{safe_date_str}.csv", sep=";", index=False)


def compute_feature_importance(
    model: torch.nn.Module,
    X_test: torch.Tensor,
    y_test: torch.Tensor,
    feature_cols: Sequence[str],
    quantiles: Sequence[float],
    seed: int,
) -> pd.DataFrame:
    """Schätze Feature-Einfluss über Permutation vollständiger Testsequenzen."""

    model.eval()
    with torch.no_grad():
        baseline_loss = pinball_loss(model(X_test), y_test, quantiles).item()

    rows = []
    generator = torch.Generator().manual_seed(seed)
    for i, col in enumerate(feature_cols):
        X_test_permuted = X_test.clone()
        permutation = torch.randperm(X_test.size(0), generator=generator)
        X_test_permuted[:, :, i] = X_test_permuted[permutation, :, i]

        with torch.no_grad():
            permuted_loss = pinball_loss(model(X_test_permuted), y_test, quantiles).item()

        rows.append(
            {
                "feature": col,
                "delta_pinball_loss_scaled": permuted_loss - baseline_loss,
            }
        )

    return pd.DataFrame(rows).sort_values("delta_pinball_loss_scaled", ascending=False)


def save_feature_importance(
    importance: pd.DataFrame,
    architecture: str,
    output_prefix: str,
    safe_date_str: str,
) -> None:
    """Speichere Permutationswichtigkeiten als sortierte CSV und Balkendiagramm."""

    importance.to_csv(f"{output_prefix}_feature_importance_{safe_date_str}.csv", sep=";", index=False)

    plot_data = importance.sort_values("delta_pinball_loss_scaled", ascending=True)
    plt.figure(figsize=(10, max(4, 0.45 * len(plot_data))))
    plt.barh(plot_data["feature"], plot_data["delta_pinball_loss_scaled"], color="#4C78A8")
    plt.title(f"{architecture} Permutation Feature Importance")
    plt.xlabel("Delta Pinball Loss (skaliert)")
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_feature_importance_{safe_date_str}.png")
    plt.close()


def save_metadata(
    output_prefix: str,
    safe_date_str: str,
    architecture: str,
    feature_cols: Sequence[str],
    weather_cols: Sequence[str],
    prepared: PreparedData,
    seed: int,
    quantiles: Sequence[float],
    crossing_penalty_weight: float,
    sort_quantiles_for_outputs: bool,
) -> None:
    """Dokumentiere Konfiguration, Features, Split und Skalierung eines Modelllaufs."""

    metadata = {
        "architecture": architecture,
        "seed": seed,
        "quantiles": list(quantiles),
        "crossing_penalty_weight": crossing_penalty_weight,
        "sort_quantiles_for_outputs": sort_quantiles_for_outputs,
        "feature_columns": list(feature_cols),
        "weather_feature_columns": list(weather_cols),
        "split_counts": prepared.split_counts,
        "scaling": "MinMaxScaler fit only on chronological training split",
        "training_loss": "Pinball Loss plus quantile crossing penalty",
    }
    with open(f"{output_prefix}_modell_metadaten_{safe_date_str}.json", "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)


def run_probabilistic_training(
    model_factory: Callable[[int], torch.nn.Module],
    architecture: str,
    output_prefix: str,
    color: str,
    checkpoint_path: str,
    final_model_path: str,
    scaler_features_path: str,
    scaler_target_path: str,
    cleaned_data_path: str = CLEANED_DATA_PATH,
    seed: int = DEFAULT_SEED,
    quantiles: Sequence[float] = DEFAULT_QUANTILES,
    epochs: int = 150,
    patience: int = 25,
    batch_size: int = 32,
    learning_rate: float = 0.0005,
    crossing_penalty_weight: float = DEFAULT_CROSSING_PENALTY_WEIGHT,
    sort_quantiles_for_outputs: bool = True,
) -> None:
    """Führe Training, Evaluation und Export für eine Modellarchitektur aus.

    Die Modellfabrik ist der einzige architekturspezifische Teil. Split,
    Hyperparameter, Metriken und Artefaktnamen bleiben für LSTM und RNN über
    diese gemeinsame Pipeline konsistent.
    """

    set_reproducibility(seed)

    df = load_training_dataframe(cleaned_data_path)
    time_delta_min, window_size = infer_window_size(df.index)
    date_range_str, safe_date_str = date_range_strings(df.index)
    feature_cols, target_col, weather_cols = select_feature_columns(df)

    print(f"Erkannte Aufloesung: Alle {time_delta_min} Minuten. Window Size (24h): {window_size}")
    print(f"Feature-Spalten ({len(feature_cols)}): {', '.join(feature_cols)}")
    print(f"Quantile-Crossing-Penalty Gewicht: {crossing_penalty_weight}")
    print(f"Quantile-Sortierung fuer Outputs aktiv: {sort_quantiles_for_outputs}")
    if weather_cols:
        print(f"Wetterfeatures aktiv: {', '.join(weather_cols)}")
    else:
        print(
            "Keine Wetterfeatures gefunden. Optional kann eine Wetter-CSV ueber "
            "energy_forecasting.data_preparation --weather-csv eingebunden werden."
        )

    prepared = prepare_time_series_data(df, feature_cols, target_col, window_size)
    train_loader = make_train_loader(prepared, seed=seed, batch_size=batch_size)

    model = model_factory(len(feature_cols))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=7,
    )

    best_val_loss = float("inf")
    best_epoch = 0
    counter = 0
    history = {"train_loss": [], "val_loss": []}

    print(f"Starte {architecture} Training...")
    for epoch in range(epochs):
        model.train()
        total_train_loss = 0.0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            preds = model(batch_X)
            loss = probabilistic_training_loss(preds, batch_y, quantiles, crossing_penalty_weight)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item()

        model.eval()
        with torch.no_grad():
            val_preds = model(prepared.X_val)
            val_loss = probabilistic_training_loss(val_preds, prepared.y_val, quantiles, crossing_penalty_weight)

        val_loss_value = val_loss.item()
        scheduler.step(val_loss_value)

        train_loss_value = total_train_loss / len(train_loader)
        history["train_loss"].append(train_loss_value)
        history["val_loss"].append(val_loss_value)

        if (epoch + 1) % 10 == 0:
            print(
                f"Epoch [{epoch + 1}/{epochs}] | "
                f"Train Loss: {train_loss_value:.5f} | Val Loss: {val_loss_value:.5f}"
            )

        if val_loss_value < best_val_loss:
            best_val_loss = val_loss_value
            best_epoch = epoch + 1
            torch.save(model.state_dict(), checkpoint_path)
            counter = 0
        else:
            counter += 1
            if counter >= patience:
                print(f"Early Stopping in Epoche {epoch + 1}")
                break

    model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
    save_learning_curve(history, architecture, safe_date_str, best_epoch, output_prefix)

    print(f"\n--- {architecture} Modell Struktur ---")
    print(model)

    model.eval()
    with torch.no_grad():
        preds_test = model(prepared.X_test).numpy()
        raw_crossing_rate = quantile_crossing_rate_numpy(preds_test)
        if sort_quantiles_for_outputs:
            preds_test = sort_quantile_predictions(preds_test)
        y_test_mwh = prepared.scaler_target.inverse_transform(prepared.y_test.numpy())
        preds_rescaled = [
            prepared.scaler_target.inverse_transform(preds_test[:, i : i + 1])
            for i in range(len(quantiles))
        ]

    metrics, calibration = compute_probabilistic_metrics(y_test_mwh, preds_rescaled, quantiles)
    metrics["Raw_Quantile_Crossing_Rate_before_sort_percent"] = raw_crossing_rate

    print(f"\n--- {architecture} Modell Evaluation ---")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

    save_forecast_plot(y_test_mwh, preds_rescaled, architecture, date_range_str, safe_date_str, output_prefix, color)
    save_forecast_csv(prepared.test_index, y_test_mwh, preds_rescaled, output_prefix, safe_date_str)
    save_metrics(metrics, calibration, output_prefix, safe_date_str)
    save_calibration_plot(calibration, architecture, safe_date_str, output_prefix)

    importance = compute_feature_importance(
        model,
        prepared.X_test,
        prepared.y_test,
        feature_cols,
        quantiles,
        seed=seed,
    )
    print(f"\n--- {architecture} Feature Importance (Einfluss auf Pinball Loss) ---")
    for _, row in importance.iterrows():
        print(f"{row['feature']}: {row['delta_pinball_loss_scaled']:.6f}")
    save_feature_importance(importance, architecture, output_prefix, safe_date_str)

    torch.save(model.state_dict(), final_model_path)
    torch.save(model.state_dict(), f"{os.path.splitext(final_model_path)[0]}_{safe_date_str}.pth")
    joblib.dump(prepared.scaler_features, scaler_features_path)
    joblib.dump(prepared.scaler_target, scaler_target_path)
    save_metadata(
        output_prefix,
        safe_date_str,
        architecture,
        feature_cols,
        weather_cols,
        prepared,
        seed,
        quantiles,
        crossing_penalty_weight,
        sort_quantiles_for_outputs,
    )

    print(f"\n--- Finales {architecture} Modell, Scaler und Metriken wurden gesichert! ---")
