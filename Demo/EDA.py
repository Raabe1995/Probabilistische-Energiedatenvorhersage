import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Daten laden

try:
    df = pd.read_csv('Realisierte_Erzeugung_202604090000_202604200000_Viertelstunde.csv', sep=';')
    df['Timestamp'] = pd.to_datetime(df['Datum von'], format='%d.%m.%Y %H:%M')
    df.set_index('Timestamp', inplace=True)
except FileNotFoundError:
    print("Datei nicht gefunden! Bitte Pfad prüfen.")
    exit()

# 2. Daten bereinigen
cols_to_fix = df.columns[2:]
for col in cols_to_fix:
    df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.')
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Definition der Spaltennamen (Vorziehen, um NameError zu vermeiden)
pv_col = 'Photovoltaik [MWh] Originalauflösungen'
wind_col = 'Wind Onshore [MWh] Originalauflösungen'

# 3. Zyklisches Feature Engineering
df['hour'] = df.index.hour
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

# Zusätzliche Zeit-Features
df['weekday'] = df.index.weekday
df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)

# Aggregierte Profile visualisieren
daily_profile = df.groupby(df.index.hour)[[pv_col, wind_col]].mean()
daily_profile.plot(kind='line', title='Durchschnittliches Tagesprofil (April 2026)')
plt.ylabel('MWh')
plt.show()

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
    plt.title('Energieerzeugung April 2026')
    plt.legend()
    plt.grid(True)
    plt.show()

# 6. Korrelations-Check
# Breite leicht erhöht, um Platz für die Y-Beschriftung zu schaffen
plt.figure(figsize=(14, 10))

# Heatmap erstellen
ax = sns.heatmap(
    df[cols_to_fix].corr(),
    annot=False,
    cmap='coolwarm',
    # Beschriftung für die Farbleiste
    cbar_kws={'label': 'Pearson-Korrelationskoeffizient (r)'}
)

# Optimierung der Beschriftungen

# X-Achsen-Beschriftungen rotieren (10 Grad) und nach rechts ausrichten
plt.xticks(rotation=10, ha='right', fontsize=9)

# Y-Achsen-Beschriftungen horizontal lassen, aber Schriftgröße leicht verkleinern
plt.yticks(rotation=0, fontsize=9)

plt.title('Korrelation zwischen den Energiequellen (SMARD-Rohdaten)', fontsize=14, pad=20)

# WICHTIG: Berechnet automatisch den benötigten Platz, damit nichts abgeschnitten wird
plt.tight_layout()

plt.show()

# 7. 3D-Array: Features (X), Target (y)

# Funktion für eine einzelne Spalte (Univariat)
def create_sequences(data, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size)])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)

# Funktion für mehrere Spalten gleichzeitig (Multivariat)
def create_multivariate_sequences(data, target_col_idx, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size), :])
        y.append(data[i + window_size, target_col_idx])
    return np.array(X), np.array(y)

# Vorbereitung für späteres Training (alle Features)
feature_cols = [pv_col, wind_col, 'hour_sin', 'hour_cos']
data_array = df[feature_cols].values
X_multi, y_multi = create_multivariate_sequences(data_array, target_col_idx=0, window_size=96)


# 8. Fenstergröße: 96 Schritte entsprechen genau 24 Stunden (4 * 24)
window_size = 96

# 9. Test an der Photovoltaik
if pv_col in df.columns:
    pv_values = df[pv_col].values
    X_pv, y_pv = create_sequences(pv_values, window_size)

    print("\n--- Daten-Transformation für ML ---")
    print(f"Eingabe-Sequenzen (X) Shape: {X_pv.shape}")
    print(f"Ziel-Werte (y) Shape: {y_pv.shape}")

    # 10. Blick in die erste Sequenz
    if len(y_pv) > 0:
        print("\nErster Zielwert, den das Modell lernen soll:", y_pv[0])

# 11. Daten abspeichern als .csv
df.to_csv('Realisierte_Erzeugung_Cleaned.csv', sep=';')

df.to_pickle('cleaned_data.pkl')

print("\n--- Daten erfolgreich gespeichert! ---")