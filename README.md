# Probabilistische Energiedatenvorhersage mit LSTM und RNN

Dieses Projekt erstellt probabilistische Prognosen für die Photovoltaik-Einspeisung aus historischen SMARD-Erzeugungsdaten. Zwei rekurrente neuronale Netze - ein LSTM und ein klassisches RNN – prognostizieren die Quantile `q0.1`, `q0.5` und `q0.9`. Das Intervall zwischen `q0.1` und `q0.9` bildet damit ein nominelles 80-%-Prognoseintervall ab.

Eine Streamlit-Anwendung führt durch den vollständigen Ablauf: Datenupload, explorative Analyse, Training beider Modelle, Evaluation und Ergebnisdarstellung. Die Pipeline kann alternativ vollständig über die Kommandozeile ausgeführt werden.

> **Projektstatus:** Das Repository ist ein Forschungs- und Demonstrationsprojekt. Es ist nicht als operatives Prognosesystem oder als Grundlage für betriebliche Entscheidungen vorgesehen.

## Funktionen

- Verarbeitung von SMARD-CSV-Exporten mit deutschem Zahlen- und Datumsformat
- optionale Einbindung numerischer Wettermerkmale über zeitbasierten Join
- gemeinsame Trainings- und Evaluationslogik für LSTM und RNN
- chronologische Aufteilung in Trainings-, Validierungs- und Testdaten (MinMaxScaler fit nur auf Train)
- Quantilregression für $q_{0.1}$, $q_{0.5}$ und $q_{0.9}$ mittels Pinball Loss
- Quantile-Crossing-Penalty zur Reduktion ungeordneter Quantile
- Kennzahlen für Punktprognose (RMSE), Intervallqualität (PICP, Winkler-Score) und Kalibrierung
- Permutation Feature Importance zur modellagnostischen Interpretation
- Reproduzierbare Läufe durch feste Seeds und deterministische PyTorch-Einstellungen
- browserbasiertes Dashboard mit Grafiken, Tabellen und Pipeline-Protokoll
- Ausführung lokal oder mit Docker Compose
- Containerisierte Ausführung via Docker Compose oder native lokale Installation

## Schnellstart mit Docker

### Voraussetzungen

- Docker Desktop oder eine Docker-Installation mit Docker Compose
- ein freier lokaler Port `8503`

Repository herunterladen, in das Projektverzeichnis wechseln und die Anwendung starten:

```bash
docker compose up --build
```

Anschließend im Browser öffnen:

[http://localhost:8503](http://localhost:8503)

In der Anwendung:

1. Unter `Pipeline` eine SMARD-CSV auswählen. Zum Ausprobieren liegt eine Datei unter `data/examples/` bereit.
2. Optional eine Wetter-CSV auswählen.
3. `Pipeline starten` anklicken.
4. Nach dem Training die Auswertung unter `Ergebnisse` ansehen.

Das Training von LSTM und RNN läuft nacheinander und kann auf einer CPU einige Zeit benötigen. Statusmeldungen erscheinen in der Oberfläche; das vollständige Protokoll wird unter `data/output/pipeline_protokoll.txt` gespeichert.

Die Anwendung mit `Ctrl + C` beenden und anschließend Container sowie Compose-Netzwerk entfernen:

```bash
docker compose down
```

Für einen Start im Hintergrund:

```bash
docker compose up --build -d
```

Die Verzeichnisse `data/input` und `data/output` sind in den Container eingebunden. Hochgeladene Daten und erzeugte Ergebnisse bleiben daher auch nach `docker compose down` lokal erhalten.

### Docker-Fehlersuche

Containerstatus und letzte Protokollzeilen anzeigen:

```bash
docker compose ps -a
docker compose logs --tail=120 smard-probabilistic
```

`0.0.0.0:8501` ist die interne Bind-Adresse der Anwendung im Container. Im Browser wird bei Docker Compose ausschließlich `http://localhost:8503` verwendet.

## Lokale Installation

Das Docker-Image verwendet Python 3.10. Für eine lokale Installation wird deshalb ebenfalls Python 3.10 empfohlen.

### macOS und Linux

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Falls Python 3.10 auf dem System als `python3` verfügbar ist, kann der erste Befehl entsprechend mit `python3` ausgeführt werden.

Anwendung starten:

```bash
PYTHONPATH=src python -m streamlit run src/energy_forecasting/app.py
```

Danach ist die Anwendung normalerweise unter [http://localhost:8501](http://localhost:8501) erreichbar.

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m streamlit run src/energy_forecasting/app.py
```

Die gesetzte `PYTHONPATH`-Variable gilt nur für das aktuelle Terminalfenster.

## Ausführung über die Kommandozeile

Die drei Schritte müssen in dieser Reihenfolge ausgeführt werden:

1. Daten aufbereiten und EDA-Artefakte erzeugen
2. LSTM trainieren und auswerten
3. RNN trainieren und auswerten

Lege die Eingabedatei beispielsweise als `data/input/smard.csv` ab. Die folgenden Befehle werden aus der Projektwurzel gestartet und schreiben die Ergebnisse geordnet nach `data/output`:

```bash
mkdir -p data/output
cd data/output
PYTHONPATH=../../src python -m energy_forecasting.data_preparation ../input/smard.csv
PYTHONPATH=../../src python -m energy_forecasting.models.lstm
PYTHONPATH=../../src python -m energy_forecasting.models.rnn
```

Mit einer zusätzlichen Wetterdatei, ebenfalls von der Projektwurzel aus:

```bash
cd data/output
PYTHONPATH=../../src python -m energy_forecasting.data_preparation ../input/smard.csv --weather-csv ../input/weather.csv
PYTHONPATH=../../src python -m energy_forecasting.models.lstm
PYTHONPATH=../../src python -m energy_forecasting.models.rnn
```

Unter Windows PowerShell wird nach dem Wechsel in `data/output` einmalig `$env:PYTHONPATH = "../../src"` gesetzt. Die drei Python-Module können danach ohne vorangestelltes `PYTHONPATH=...` aufgerufen werden.

Ohne den Wechsel nach `data/output` legt die Kommandozeilen-Pipeline ihre Artefakte im aktuellen Arbeitsverzeichnis ab. Die Streamlit-Anwendung verschiebt ihre Ergebnisse dagegen automatisch nach `data/output`.

## Eingabedaten

### SMARD-Datei

Erwartet wird eine Semikolon-getrennte CSV mit stündlichen oder viertelstündlichen Werten. Die Datei muss mindestens folgende Spalten enthalten:

- `Datum von`
- `Datum bis`
- eine Spalte, deren Name `Photovoltaik` enthält
- eine Spalte, deren Name `Wind Onshore` enthält
- eine Spalte, deren Name `Erdgas` enthält

Zeitstempel müssen dem Format `TT.MM.JJJJ HH:MM` entsprechen, beispielsweise `09.04.2026 00:00`. Deutsche Zahlenformate wie `4.167,28` werden automatisch in numerische Werte umgewandelt. Nicht numerische Einträge wie `-` werden in den Erzeugungsspalten als fehlende Werte behandelt und zu `0` konvertiert.

Ein kleiner SMARD-Beispieldatensatz für einen technischen Testlauf befindet sich unter `data/examples/`. Er dient ausschließlich zur Prüfung des Ablaufs; Ergebnisse aus diesem kurzen Zeitraum sind nicht belastbar.

### Optionale Wetterdatei

Die Wetterdatei kann über die Streamlit-Oberfläche oder mit `--weather-csv` eingebunden werden. Sie benötigt eine Zeitspalte mit einem der unterstützten Namen, zum Beispiel `Timestamp`, `Datum von`, `datetime`, `date` oder `time`, sowie mindestens eine numerische Wetterspalte.

Empfohlenes Format:

```csv
Timestamp;Globalstrahlung;Bewoelkung;Temperatur
09.04.2026 00:00;0,0;85;8,4
09.04.2026 01:00;0,0;82;8,1
```

Semikolon und Komma werden als Trennzeichen erkannt. Die numerischen Wetterspalten erhalten intern das Präfix `weather_`, werden über den Zeitstempel mit den SMARD-Daten verbunden und bei Lücken zeitlich interpoliert. Da die aktuelle Einleselogik Tag vor Monat interpretiert, sollten Wetterzeitstempel ebenfalls als `TT.MM.JJJJ HH:MM` angegeben werden. ISO-Datumsangaben mit Jahr an erster Stelle werden derzeit nicht zuverlässig interpretiert.

## Ablauf und Methodik

```text
SMARD-CSV (+ optionale Wetter-CSV)
        │
        ▼
Datenbereinigung und Zeitmerkmale
        │
        ▼
chronologische Sequenzen und Datensplits
        │
        ├──► LSTM ──► Quantile, Metriken und Grafiken
        │
        └──► RNN  ──► Quantile, Metriken und Grafiken
                         │
                         ▼
                 Streamlit-Dashboard
```

Die Modelle verwenden ein 24-Stunden-Fenster, dessen Anzahl an Zeitschritten aus der Auflösung der Eingabedaten abgeleitet wird. Die `MinMaxScaler` werden ausschließlich auf dem chronologischen Trainingssplit angepasst. Validierungs- und Testwerte fließen nicht in die Skalierungsparameter ein.

Die Trainingsfunktion verwendet standardmäßig:

- Seed `42`
- `150` Epochen mit Early Stopping nach `25` Epochen ohne Verbesserung
- Quantile `0.1`, `0.5` und `0.9`
- Crossing-Penalty mit Gewicht `0.2`
- Batch-Größe `32`
- Lernrate `0.0005`

LSTM und RNN teilen dieselbe Datenaufbereitung, Verlustfunktion und Evaluation. Damit lässt sich der Einfluss der Modellarchitektur direkt vergleichen. Eine Crossing-Penalty reduziert Quantilkreuzungen während des Trainings. Vor Evaluation und Export werden die drei Vorhersagen zusätzlich je Zeitpunkt sortiert; die ursprüngliche Kreuzungsrate wird separat protokolliert.

### Evaluationskennzahlen

| Kennzahl | Bedeutung |
| --- | --- |
| Median-RMSE | Fehler der mittleren Quantilprognose `q0.5` |
| Pinball Loss | quantilspezifischer Prognosefehler |
| PICP | beobachtete Abdeckung des 80-%-Intervalls |
| mittlere Intervallbreite | durchschnittliche Breite zwischen `q0.1` und `q0.9` |
| Winkler Score | gemeinsame Bewertung von Breite und Fehlabdeckung |
| Kalibrierung | Vergleich von Zielquantil und empirischer Abdeckung |
| Quantilkreuzungsrate | Anteil ungeordneter Rohprognosen vor der Sortierung |

Für ein gut kalibriertes 80-%-Intervall sollte die PICP in der Nähe von 80 % liegen. Eine hohe Abdeckung allein genügt nicht: Ein unnötig breites Intervall ist weniger informativ und wird unter anderem durch Intervallbreite und Winkler Score sichtbar.

## Ergebnisdateien

Ein vollständiger Lauf erzeugt – abhängig von Modell und Datumsbereich – unter anderem:

- `Realisierte_Erzeugung_Cleaned.csv` und `cleaned_data.pkl`
- EDA-Grafiken und die zugehörigen CSV-Dateien
- `final_probabilistic_lstm.pth` und `final_probabilistic_rnn.pth`
- datierte Modellstände und `best_prob_model*.pth`
- Feature- und Ziel-Scaler als `.pkl`
- Prognosedaten und Prognosegrafiken je Modell
- Lernkurven, Kalibrierungsdaten und Kalibrierungsgrafiken
- Feature-Importance-Daten und -Grafiken
- Metrik-CSV und Modellmetadaten als JSON
- `dashboard_summary.json` und Vorschaubilder unter `dashboard_assets/`
- `pipeline_protokoll.txt`
- `streamlit_error.log`, falls die Oberfläche einen Python-Fehler protokolliert

Generierte Laufzeitdaten unter `data/input` und `data/output` werden mit Ausnahme der `.gitkeep`-Dateien nicht versioniert.

## Projektstruktur

```text
Probabilistische-Energiedatenvorhersage/
├── src/
│   └── energy_forecasting/
│       ├── __init__.py
│       ├── app.py                 # Streamlit-Oberfläche und Pipeline-Steuerung
│       ├── dashboard.py           # kompaktes Ergebnis-Bundle für die Oberfläche
│       ├── data_preparation.py    # CSV-Aufbereitung, EDA und Feature-Erzeugung
│       ├── training.py            # gemeinsame Trainings- und Evaluationslogik
│       └── models/
│           ├── __init__.py
│           ├── lstm.py            # LSTM-Architektur und Trainingsaufruf
│           └── rnn.py             # RNN-Architektur und Trainingsaufruf
├── tests/
│   └── test_training.py
├── data/
│   ├── input/                     # lokale Uploads und Eingabedaten
│   ├── output/                    # generierte Modelle, Metriken und Grafiken
│   └── examples/                  # kleiner Beispieldatensatz
├── docs/
│   ├── praesentationen/           # vorhandene Projektdokumentation: Projektpräsentation
│ 	├── bericht/				   # vorhandene Projektdokumentation: Projektbericht
├── .streamlit/
│   └── config.toml
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

Der ausführbare Python-Code liegt vollständig im Paket `energy_forecasting`. Daten, Tests und Projektdokumentation sind davon getrennt. Es gibt keine Skripte zur automatischen Erstellung von Präsentationen.

## Tests

Nach der lokalen Installation werden die Regressionstests aus der Projektwurzel ausgeführt:

```bash
python -m unittest discover -s tests -v
```

Die Tests prüfen insbesondere, dass die Scaler nur auf Trainingsdaten angepasst werden, probabilistische Kennzahlen vorhanden sind, Quantilkreuzungen erkannt werden und Wettermerkmale korrekt verbunden werden.

## Bekannte Einschränkungen

- Die Pipeline interpoliert fehlende Werte derzeit vor dem chronologischen Split über die vollständige Zeitachse. Bei Lücken kann dadurch Information aus späteren Zeitpunkten in frühere interpolierte Werte einfließen. Eine ausschließlich vorwärtsgerichtete oder splitweise Imputation würde frühere Ergebnisse verändern und sollte als methodische Weiterentwicklung separat geprüft werden.
- Ohne eine externe Wetterdatei basieren die Modelle nur auf historischen Erzeugungs- und Zeitmerkmalen. Für eine reale Zukunftsprognose müssten auch zum Prognosezeitpunkt verfügbare Einflussgrößen konsistent bereitgestellt werden.
- Sehr kurze Eingabezeiträume eignen sich zum Funktionstest, nicht für eine belastbare Modellbewertung.
- Training und Permutations-Feature-Importance können auf reinen CPU-Systemen längere Zeit beanspruchen.
- Wetterzeitstempel im ISO-Format `JJJJ-MM-TT` werden von der aktuellen `dayfirst`-Verarbeitung nicht zuverlässig erkannt.

## Technischer Hinweis zur Reproduzierbarkeit

Die Abhängigkeiten sind in `requirements.txt` auf feste Versionen gesetzt. Modellmetadaten dokumentieren zusätzlich Trainingsparameter, Datensplits, Quantile, Crossing-Penalty und die Sortierung der exportierten Quantile. Reproduzierbarkeit kann dennoch durch Hardware, Betriebssystem und numerische Unterschiede einzelner PyTorch-Operationen beeinflusst werden.

## Datenquelle und Lizenz

Die im Ordner `\data\examples` hinterlegten Strommarktdaten stammen von der Plattform [SMARD.de](https://www.smard.de/) der Bundesnetzagentur.
Sie stehen unter der Lizenz [Creative Commons Namensnennung 4.0 International (CC BY 4.0)](https://creativecommons.org).

**Quellenangabe:**
© Bundesnetzagentur 2026, smard.de, abgerufen am [04.2026].