"""SMARD-Daten aufbereiten und Artefakte der explorativen Analyse erzeugen.

Das Kommandozeilenmodul vereinheitlicht Zahlen und Zeitstempel, ergänzt
Zeit- sowie optionale Wettermerkmale und speichert die bereinigte Grundlage
für die gemeinsame Trainingspipeline.
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob

from energy_forecasting.training import merge_weather_features

# Docker bindet Uploads unter /app/data ein; lokale Direktaufrufe nutzen den Projektordner.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
input_dir = '/app/data/input' if os.path.exists('/app/data/input') else os.path.join(project_root, 'data', 'input')

parser = argparse.ArgumentParser(description="EDA und Datenbereinigung fuer SMARD-Marktdaten.")
parser.add_argument("input_csv", nargs="?", help="Pfad zur SMARD-CSV-Datei")
parser.add_argument("--weather-csv", help="Optionale Wetter-CSV mit Zeitstempel und numerischen Wetterfeatures")
args = parser.parse_args()

# Ein expliziter Pfad hat Vorrang; andernfalls wird die neueste verfügbare CSV genutzt.
try:
    if args.input_csv:
        input_filename = args.input_csv
    else:
        csv_files = glob.glob(os.path.join(input_dir, '*.csv'))

        if not csv_files:
            csv_files = glob.glob('*.csv')

        if csv_files:
            input_filename = max(csv_files, key=os.path.getmtime)
        else:
            raise FileNotFoundError("Keine CSV-Datei im Verzeichnis gefunden!")

    print(f"--- EDA Skript verarbeitet jetzt aktiv die Datei: {input_filename} ---")

    df = pd.read_csv(input_filename, sep=';')
    df['Timestamp'] = pd.to_datetime(df['Datum von'], format='%d.%m.%Y %H:%M')
    df.set_index('Timestamp', inplace=True)

except Exception as exc:
    print(f"Fehler beim Laden der Daten: {exc}")
    raise SystemExit(1) from exc

# SMARD-Exporte verwenden deutsche Tausender- und Dezimaltrennzeichen.
cols_to_fix = df.columns[2:]
for col in cols_to_fix:
    df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.')
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Spaltenzusätze können je nach gewählter SMARD-Auflösung variieren.
pv_col = [c for c in df.columns if 'Photovoltaik' in c][0]
wind_col = [c for c in df.columns if 'Wind Onshore' in c][0]

# Messwerte bis Mitternacht nach dem letzten positiven PV-Wert beibehalten.
last_active_index = df[df[pv_col] > 0].index.max()
if pd.notna(last_active_index):
    last_valid_day = last_active_index.normalize() + pd.Timedelta(days=1)
    df = df.loc[:last_valid_day]

# Anzahl der Messpunkte eines 24-Stunden-Fensters aus der Eingabeauflösung ableiten.
time_delta_min = (df.index[1] - df.index[0]).total_seconds() / 60
steps_per_day = int((24 * 60) / time_delta_min)
window_size = steps_per_day

# Die bereinigte Variante wird ausschließlich in generierten Dateinamen verwendet.
start_date_str = df.index.min().strftime('%m.%Y')
end_date_str = df.index.max().strftime('%m.%Y')
date_range_str = start_date_str if start_date_str == end_date_str else f"{start_date_str} - {end_date_str}"
safe_date_str = date_range_str.replace('.', '_').replace(' ', '').replace('-', '_')

print(f"Erkannte Auflösung: Alle {time_delta_min} Minuten. Window Size für 24h: {window_size}")

# Zeilen entfernen, die nach der numerischen Konvertierung noch fehlende Werte enthalten.
df = df.dropna()

# Wettermerkmale sind optional und behalten nach dem Merge ihr weather_-Präfix.
df, weather_cols = merge_weather_features(df, args.weather_csv)
if weather_cols:
    print(f"Wetterfeatures eingebunden: {', '.join(weather_cols)}")
else:
    print("Keine Wetterfeatures eingebunden.")


# Zyklische Kodierungen erhalten die Nähe von Mitternacht und benachbarten Wochentagen.
df['hour'] = df.index.hour
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

df['weekday'] = df.index.weekday
df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)

# Plots speichern, damit das Skript ohne grafische Oberfläche in Docker funktioniert.
daily_profile = df.groupby(df.index.hour)[[pv_col, wind_col]].mean()
daily_profile.plot(kind='line', title=f'Durchschnittliches Tagesprofil ({date_range_str})')
plt.ylabel('MWh')
plt.tight_layout()
plt.savefig(f'eda_tagesprofil_{safe_date_str}.png')
plt.close()
daily_profile.to_csv(f'eda_tagesprofil_daten_{safe_date_str}.csv', sep=';')

print("--- Datensatz Info ---")
print(df.info())

if pv_col in df.columns:
    print("\n--- Statistische Kennzahlen (Auszug) ---")
    print(df[[pv_col, wind_col]].describe())

plt.figure(figsize=(15, 6))
if pv_col in df.columns:
    plt.plot(df[pv_col], label='Solar', color='orange')
    plt.plot(df[wind_col], label='Wind Onshore', color='blue')
    plt.title(f'Energieerzeugung {date_range_str}')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'eda_energieerzeugung_{safe_date_str}.png')
    plt.close()
    df[[pv_col, wind_col]].to_csv(f'eda_energieerzeugung_daten_{safe_date_str}.csv', sep=';')

plt.figure(figsize=(14, 10))
correlation_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]

ax = sns.heatmap(
    df[correlation_cols].corr(),
    annot=False,
    cmap='coolwarm',
    cbar_kws={'label': 'Pearson-Korrelationskoeffizient (r)'}
)

plt.xticks(rotation=10, ha='right', fontsize=9)
plt.yticks(rotation=0, fontsize=9)
plt.title('Korrelation zwischen den Energiequellen (SMARD-Rohdaten)', fontsize=14, pad=20)
plt.tight_layout()
plt.savefig(f'eda_korrelations_heatmap_{safe_date_str}.png')
plt.close()

def create_sequences(data, window_size):
    """Erzeuge eindimensionale Zeitfenster und den jeweils folgenden Zielwert."""

    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size)])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)

def create_multivariate_sequences(data, target_col_idx, window_size):
    """Erzeuge mehrdimensionale Zeitfenster mit einem Zielwert aus der Folgereihe."""

    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size), :])
        y.append(data[i + window_size, target_col_idx])
    return np.array(X), np.array(y)

feature_cols = [pv_col, wind_col, 'hour_sin', 'hour_cos']
data_array = df[feature_cols].values

X_multi, y_multi = create_multivariate_sequences(data_array, target_col_idx=0, window_size=window_size)

if pv_col in df.columns:
    pv_values = df[pv_col].values
    X_pv, y_pv = create_sequences(pv_values, window_size)

    print("\n--- Daten-Transformation für ML ---")
    print(f"Eingabe-Sequenzen (X) Shape: {X_pv.shape}")
    print(f"Ziel-Werte (y) Shape: {y_pv.shape}")

    if len(y_pv) > 0:
        print("\nErster Zielwert, den das Modell lernen soll:", y_pv[0])

df.to_csv('Realisierte_Erzeugung_Cleaned.csv', sep=';')
df.to_pickle('cleaned_data.pkl')

print("\n--- Daten erfolgreich gespeichert! ---")
