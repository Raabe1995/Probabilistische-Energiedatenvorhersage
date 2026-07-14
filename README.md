# Probabilistische Energiedatenvorhersage mit LSTM/RNN

Dieses Projekt trainiert probabilistische Modelle zur Vorhersage der Photovoltaik-Einspeisung auf Basis von SMARD-Marktdaten. Statt nur eine Punktprognose zu erzeugen, sagen LSTM und RNN drei Quantile voraus (`q0.1`, `q0.5`, `q0.9`). Daraus entsteht ein 80%-Unsicherheitsintervall, das die Planungssicherheit der Prognose sichtbar macht.

## Projektstruktur

- `main.py`: Streamlit-Oberfläche für Upload, Pipeline-Start und Ergebnis-Dashboard.
- `eda.py`: CSV-Import, Bereinigung, optionale Wetterdatenintegration und EDA-Plots.
- `training_utils.py`: Gemeinsame Trainings-, Split-, Skalierungs-, Evaluations- und Plotlogik.
- `train_lstm.py`: LSTM-Architektur und Aufruf der gemeinsamen Trainingspipeline.
- `train_rnn.py`: RNN-Architektur und Aufruf der gemeinsamen Trainingspipeline.
- `smard_daten/input`: Eingabedaten für Docker-/Streamlit-Runs.
- `smard_daten/output`: Generierte Modelle, Scaler, Plots, Metriken und Protokolle.

## Was verbessert wurde

- Die `MinMaxScaler` werden nur noch auf dem chronologischen Trainingssplit gefittet. Validierungs- und Testdaten fließen nicht mehr in die Skalierung ein.
- LSTM und RNN nutzen dieselbe Trainings- und Evaluationslogik; nur die Modellarchitektur unterscheidet sich noch.
- Reproduzierbarkeit wurde durch feste Seeds und gepinnte Dependency-Versionen verbessert.
- Optional können Wetterfeatures per separater CSV eingebunden werden.
- Die Evaluation enthält neben PICP jetzt auch mittlere Intervallbreite, Pinball Loss pro Quantil, Winkler Score, Kalibrierungsdaten/-plot und Quantile-Crossing-Rate.
- Das Training bestraft Quantilkreuzungen zusätzlich im Loss; vor der Ausgabe werden Quantile außerdem monoton sortiert.
- Nach erfolgreichem Lauf werden die Ergebnisse zusätzlich direkt in einem Streamlit-Dashboard aufbereitet.
- Für das Dashboard wird nach der Pipeline ein kompaktes Bundle (`dashboard_summary.json` plus verkleinerte Vorschaubilder) erzeugt, damit die Ergebnisansicht nicht jedes Mal alle Originaldateien neu laden muss.
- Eine echte `.gitignore` ignoriert neue generierte Modelle, Scaler, Plots und Rohdaten.

## Lokale Ausführung

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Pipeline ohne Streamlit:

```bash
python eda.py "Test csv/Alle/Realisierte_Erzeugung_202604090000_202604200000_Viertelstunde.csv"
python train_lstm.py
python train_rnn.py
```

Mit optionaler Wetterdatei:

```bash
python eda.py "pfad/zur/smard.csv" --weather-csv "pfad/zur/weather.csv"
python train_lstm.py
python train_rnn.py
```

Streamlit lokal:

```bash
streamlit run main.py
```

Nach dem Upload der SMARD-CSV und dem Klick auf `Pipeline starten` wechselt die App nach einem erfolgreichen Lauf automatisch in die Ansicht `Ergebnisse`. Dort werden Metriken, Prognoseplots, Kalibrierung, Feature Importance, Output-Dateien und das Pipeline-Protokoll direkt im Browser angezeigt.

Wenn im Output-Ordner schon Ergebnisse liegen, kannst du sie über `Vorhandene Ergebnisse anzeigen` laden.

Tests:

```bash
python -m unittest discover -s tests
```

## Docker

Mit Docker Compose starten:

```bash
docker compose up --build
```

Danach ist die App unter `http://localhost:8501` erreichbar.

Die Compose-Konfiguration deaktiviert den Streamlit-Dateiwatcher. Das ist für dieses Projekt sinnvoll, weil während der Pipeline viele Output-Dateien entstehen und diese Änderungen sonst unnötige Streamlit-Neuladungen auslösen können.

Wenn Compose im Vordergrund läuft, stoppst du die App zuerst mit `Ctrl + C`.
Danach kannst du Container und Compose-Netzwerk aufräumen:

```bash
docker compose down
```

Wenn du Compose im Hintergrund startest, nutzt du direkt:

```bash
docker compose up --build -d
docker compose down
```

Die lokalen Ordner `smard_daten/input` und `smard_daten/output` bleiben dabei erhalten.

Falls die Browserseite eine `Connection error`-Meldung zeigt, prüfe zuerst den Containerstatus und die letzten Logs:

```bash
docker compose ps -a
docker compose logs --tail=120 smard-probabilistic
```

Wenn Streamlit in einen Python-Fehler läuft, schreibt die App zusätzlich Details nach `smard_daten/output/streamlit_error.log`.

Alternativ ohne Compose:

Image bauen:

```bash
docker build -t smard-probabilistic .
```

Streamlit-App mit lokalen Input-/Output-Ordnern starten:

```bash
docker run --rm -p 8501:8501 \
  -v "$PWD/smard_daten/input:/app/data/input" \
  -v "$PWD/smard_daten/output:/app/data/output" \
  smard-probabilistic
```

Danach ist die App unter `http://localhost:8501` erreichbar.

## Datenformat

Die SMARD-Datei wird als Semikolon-CSV erwartet und sollte mindestens diese Spalten enthalten:

- `Datum von`
- `Datum bis`
- eine Spalte mit `Photovoltaik`
- eine Spalte mit `Wind Onshore`
- eine Spalte mit `Erdgas`

Deutsche Zahlenformate wie `4.167,28` werden automatisch konvertiert.

## Optionale Wetterdaten

Eine Wetter-CSV kann über die Streamlit-Oberfläche oder per `eda.py --weather-csv` eingebunden werden. Sie benötigt eine Zeitstempelspalte wie `Timestamp` oder `Datum von` sowie numerische Wetterspalten, zum Beispiel:

```csv
Timestamp;Globalstrahlung;Bewoelkung;Temperatur
2026-04-09 00:00;0,0;85;8,4
2026-04-09 01:00;0,0;82;8,1
```

Alle numerischen Wetterspalten werden mit dem Präfix `weather_` gespeichert, zeitlich auf die SMARD-Reihe gemergt und bei Bedarf interpoliert.

## Outputs

Nach einem erfolgreichen Lauf entstehen unter anderem:

- `final_probabilistic_lstm.pth`, `final_probabilistic_rnn.pth`
- `scaler_features*.pkl`, `scaler_target*.pkl`
- `lstm_vorhersage_daten_*.csv`, `rnn_vorhersage_daten_*.csv`
- `*_metriken_*.csv`
- `*_kalibrierung_*.png`
- `*_feature_importance_*.csv`
- `*_modell_metadaten_*.json`
- `dashboard_summary.json`
- `dashboard_assets/*_thumb.png`
- `pipeline_protokoll.txt`
- `streamlit_error.log` nur falls die Streamlit-Ansicht einen Python-Fehler protokolliert

Die Modellmetadaten dokumentieren zusätzlich, ob die Quantil-Sortierung für Outputs aktiv war und mit welchem Gewicht Quantilkreuzungen im Training bestraft wurden.

## Dashboard und Ergebnisinterpretation

Die Streamlit-App hat drei Ansichten: `Pipeline`, `Ergebnisse` und `Impressum`. Nach erfolgreichem Pipeline-Lauf wird ein Dashboard-Bundle vorbereitet. Dieses Bundle enthält die wichtigsten Metriken, Metadaten, kleine Tabellenauszüge, einen Logauszug und verkleinerte Vorschaubilder. Die Ergebnisansicht nutzt primär dieses Bundle, statt bei jedem Klick alle Originaldateien neu einzulesen. Beim Öffnen der Ergebnisansicht wird das Bundle nur gelesen und nicht automatisch neu geschrieben.

Das Dashboard enthält Reiter für `Überblick`, `Prognosen und EDA`, `Diagnose` sowie `Dateien und Protokoll`. Die kurzen interpretierenden Sätze im Überblick werden regelbasiert aus den berechneten Metriken erzeugt. Dadurch bleiben die Ergebnisse reproduzierbar, transparent und methodisch klar nachvollziehbar.

## Hinweise zur Interpretation

Ein gutes probabilistisches Modell sollte nicht nur einen niedrigen RMSE haben. Für das 80%-Intervall sollte die PICP nahe bei 80% liegen, die mittlere Intervallbreite nicht unnötig groß sein und die Quantile sollten nicht kreuzen. Die Pipeline stabilisiert die Quantilordnung durch eine Crossing-Penalty im Training und durch Sortierung vor Evaluation und Plot-Ausgabe. Eine sehr hohe PICP, zum Beispiel deutlich über 90%, kann bedeuten, dass das Unsicherheitsband zu breit und damit wenig informativ ist.
