import os
import glob
import subprocess
import shutil
import streamlit as st

INPUT_DIR = "/app/data/input"
OUTPUT_DIR = "/app/data/output"

st.title("📊 SMARD Probabilistische Energiedatenvorhersage")
st.write("Lade eine SMARD-CSV-Datei hoch, um die EDA und das Modelltraining zu starten.")

# 1. Datei-Upload im Frontend
uploaded_file = st.file_uploader("SMARD CSV-Datei auswählen", type=["csv"])

if uploaded_file is not None:
    # Button zum Starten der Pipeline
    if st.button("Pipeline starten"):

        # SCHRITT 1: NEUE DATEI SPEICHERN & ALTE ÜBERSCHREIBEN
        os.makedirs(INPUT_DIR, exist_ok=True)
        input_csv_path = os.path.join(INPUT_DIR, "aktuelle_erzeugung.csv")

        with open(input_csv_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("Datei erfolgreich geladen und im System aktualisiert!")

        # SCHRITT 2: PIPELINE AUSFÜHREN & KONSOLENAUSGABE ABFANGEN
        with st.spinner("Pipeline läuft... Bitte warten (EDA -> LSTM -> RNN)"):

            # Standardwert definieren, um NameError zu verhindern
            fehler_aufgetreten = False

            with open("pipeline_protokoll.txt", "w") as log_file:
                try:
                    st.text("Starte EDA (Grafiken werden im Hintergrund berechnet)...")
                    subprocess.run(["python", "eda.py", input_csv_path], stdout=log_file, stderr=log_file, check=True)

                    st.text("Trainiere LSTM Modell (Pinball Loss)...")
                    subprocess.run(["python", "train_lstm.py"], stdout=log_file, stderr=log_file, check=True)

                    st.text("Trainiere RNN Modell (Pinball Loss)...")
                    subprocess.run(["python", "train_rnn.py"], stdout=log_file, stderr=log_file, check=True)

                    # SCHRITT 3: ERGEBNISSE IN DEN OUTPUT-ORDNER VERSCHIEBEN
                    os.makedirs(OUTPUT_DIR, exist_ok=True)

                    feste_artifacts = [
                        "Realisierte_Erzeugung_Cleaned.csv",
                        "cleaned_data.pkl",
                        "scaler_features.pkl",
                        "scaler_target.pkl",
                        "scaler_features_rnn.pkl",
                        "scaler_target_rnn.pkl",
                        "best_prob_model.pth",
                        "final_probabilistic_lstm.pth",
                        "best_prob_model_rnn.pth",
                        "final_probabilistic_rnn.pth"
                    ]

                    # 1. Verschiebt alle festen Dateien
                    for artifact in feste_artifacts:
                        if os.path.exists(artifact):
                            shutil.move(artifact, os.path.join(OUTPUT_DIR, artifact))

                    # 2. Verschiebt alle generierten PNG-Grafiken
                    generierte_pngs = glob.glob("*.png")
                    for png_file in generierte_pngs:
                        shutil.move(png_file, os.path.join(OUTPUT_DIR, png_file))

                    # 3. Verschiebt alle dynamischen Daten-CSVs (Tagesprofile, Lernkurven, Prognosen)
                    # Der Filter greift bei eda_*, lstm_* und rnn_* gleichermaßen
                    generierte_csvs = glob.glob("*_daten_*.csv")
                    for csv_file in generierte_csvs:
                        shutil.move(csv_file, os.path.join(OUTPUT_DIR, csv_file))

                    # 4. Verschiebt die archivierten PyTorch-Modelle mit Datumsstempel
                    archivierte_modelle = glob.glob("final_probabilistic_*.pth")
                    for model_file in archivierte_modelle:
                        # Falls die Datei durch feste_artifacts bereits verschoben wurde, ignorieren
                        if os.path.exists(model_file):
                            shutil.move(model_file, os.path.join(OUTPUT_DIR, model_file))

                # Fängt Subprocess-Fehler ab (z.B. Fehler im LSTM-Skript)
                except subprocess.CalledProcessError as e:
                    st.error("Fehler während der Ausführung! Ein Skript ist abgebrochen.")
                    st.info(
                        "Bitte prüfe die Datei 'pipeline_protokoll.txt' im Output-Ordner auf genaue Fehlermeldungen.")
                    fehler_aufgetreten = True

                # Fängt alle anderen Fehler ab (z.B. Pfad- oder Dateiprobleme beim Verschieben)
                except Exception as e:
                    st.error(f"Unerwarteter Systemfehler: {e}")
                    fehler_aufgetreten = True

            # SCHRITT 4: PROTOKOLL RETTEN
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            if os.path.exists("pipeline_protokoll.txt"):
                shutil.move("pipeline_protokoll.txt", os.path.join(OUTPUT_DIR, "pipeline_protokoll.txt"))

            if not fehler_aufgetreten:
                st.success(
                    "🎉 Pipeline erfolgreich beendet! Alle Grafiken, Modelle und das Text-Protokoll liegen im Output-Ordner.")