import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Daten laden

try:
    # Wenn ein Dateiname übergeben wurde, wird dieser übernommen. Ansonsten den Standard-Namen.
    input_filename = sys.argv[1] if len(
        sys.argv) > 1 else 'Realisierte_Erzeugung_202604090000_202604200000_Viertelstunde.csv'

    df = pd.read_csv(input_filename, sep=';')
    df['Timestamp'] = pd.to_datetime(df['Datum von'], format='%d.%m.%Y %H:%M')
    df.set_index('Timestamp', inplace=True)
except FileNotFoundError:
    print(f"Datei '{input_filename}' nicht gefunden! Bitte Pfad prüfen.")
    exit()

# 2. Daten bereinigen
cols_to_fix = df.columns[2:]
for col in cols_to_fix:
    df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.')
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Definition der Spaltennamen
# Definition der Spaltennamen (dynamisch suchen)
pv_col = [c for c in df.columns if 'Photovoltaik' in c][0]
wind_col = [c for c in df.columns if 'Wind Onshore' in c][0]

# Schneidet unvollständige Tage am Ende ab (wo alles 0 ist)
# Sucht den letzten Zeitpunkt, an dem überhaupt noch Strom erzeugt wurde
last_active_index = df[df[pv_col] > 0].index.max()
if pd.notna(last_active_index):
    # Rundet auf das Ende dieses Tages auf, um die Zeitreihe sauber zu halten
    last_valid_day = last_active_index.normalize() + pd.Timedelta(days=1)
    df = df.loc[:last_valid_day]

# Dynamische Auflösungserkennung und Zeitraum-Ermittlung
# Abstand zwischen den ersten beiden Zeilen in Minuten berechnen
time_delta_min = (df.index[1] - df.index[0]).total_seconds() / 60

# Wie viele Schritte hat ein Tag (24h)?
steps_per_day = int((24 * 60) / time_delta_min)
# Entspricht immer genau 24 Stunden Historie!
window_size = steps_per_day

# Dynamischen Zeitraum für die Plot-Beschriftungen ermitteln (z.B. "04.2026")
start_date_str = df.index.min().strftime('%m.%Y')
end_date_str = df.index.max().strftime('%m.%Y')
date_range_str = start_date_str if start_date_str == end_date_str else f"{start_date_str} - {end_date_str}"

print(f"Erkannte Auflösung: Alle {time_delta_min} Minuten. Window Size für 24h: {window_size}")

# Flexibles Schneiden / Bereinigen von leeren Zeilen am Ende
df = df.dropna()


# 3. Zyklisches Feature Engineering
df['hour'] = df.index.hour
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

# Zusätzliche Zeit-Features
df['weekday'] = df.index.weekday
df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)

# Aggregierte Profile visualisieren
daily_profile = df.groupby(df.index.hour)[[pv_col, wind_col]].mean()
daily_profile.plot(kind='line', title=f'Durchschnittliches Tagesprofil ({date_range_str})')
plt.ylabel('MWh')
plt.tight_layout()
# Speichern statt anzeigen
plt.savefig('eda_tagesprofil.png')
plt.close()

# 4. Erste Analyse-Ausgaben
print("--- Datensatz Info ---")
print(df.info())

if pv_col in df.columns:
    print("\n--- Statistische Kennzahlen (Auszug) ---")
    print(df[[pv_col, wind_col]].describe())

# 5. Visualisierung
plt.figure(figsize=(15, 6))
if pv_col in df.columns:
    plt.plot(df[pv_col], label='Solar', color='orange')
    plt.plot(df[wind_col], label='Wind Onshore', color='blue')
    plt.title(f'Energieerzeugung {date_range_str}')
    plt.legend()
    plt.grid(True)
    plt.savefig('eda_energieerzeugung.png')
    plt.close()

# 6. Korrelations-Check
plt.figure(figsize=(14, 10))

# Heatmap erstellen
ax = sns.heatmap(
    df[cols_to_fix].corr(),
    annot=False,
    cmap='coolwarm',
    cbar_kws={'label': 'Pearson-Korrelationskoeffizient (r)'}
)

# Optimierung der Beschriftungen
plt.xticks(rotation=10, ha='right', fontsize=9)
plt.yticks(rotation=0, fontsize=9)
plt.title('Korrelation zwischen den Energiequellen (SMARD-Rohdaten)', fontsize=14, pad=20)
plt.tight_layout()
plt.savefig('eda_korrelations_heatmap.png')
plt.close()

# 7. 3D-Array: Features (X), Target (y)

def create_sequences(data, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size)])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)

def create_multivariate_sequences(data, target_col_idx, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size), :])
        y.append(data[i + window_size, target_col_idx])
    return np.array(X), np.array(y)

# Vorbereitung für späteres Training (alle Features)
feature_cols = [pv_col, wind_col, 'hour_sin', 'hour_cos']
data_array = df[feature_cols].values

# Dynamische Window-Size
X_multi, y_multi = create_multivariate_sequences(data_array, target_col_idx=0, window_size=window_size)

# 8. Test an der Photovoltaik
if pv_col in df.columns:
    pv_values = df[pv_col].values
    X_pv, y_pv = create_sequences(pv_values, window_size)

    print("\n--- Daten-Transformation für ML ---")
    print(f"Eingabe-Sequenzen (X) Shape: {X_pv.shape}")
    print(f"Ziel-Werte (y) Shape: {y_pv.shape}")

    # 9. Blick in die erste Sequenz
    if len(y_pv) > 0:
        print("\nErster Zielwert, den das Modell lernen soll:", y_pv[0])

# 10. Daten abspeichern als .csv
df.to_csv('Realisierte_Erzeugung_Cleaned.csv', sep=';')
df.to_pickle('cleaned_data.pkl')

print("\n--- Daten erfolgreich gespeichert! ---")