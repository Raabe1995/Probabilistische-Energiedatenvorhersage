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

        # --- SCHRITT 1: ALTE DATEIEN LÖSCHEN ---
        st.info("Bereinige alten Input-Ordner...")
        alte_csvs = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
        for f in alte_csvs:
            try:
                os.remove(f)
            except Exception as e:
                st.warning(f"Konnte alte Datei {os.path.basename(f)} nicht löschen: {e}")

        # --- SCHRITT 2: NEUE DATEI SPEICHERN ---
        os.makedirs(INPUT_DIR, exist_ok=True)
        input_csv_path = os.path.join(INPUT_DIR, uploaded_file.name)
        with open(input_csv_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Datei erfolgreich geladen: {uploaded_file.name}")

        # --- SCHRITT 3: PIPELINE AUSFÜHREN & KONSOLENAUSGABE ABFANGEN ---
        with st.spinner("Pipeline läuft... Bitte warten (EDA -> LSTM -> RNN)"):
            try:
                # Öffnet eine Protokolldatei und leitet alle Prints dort hinein
                with open("pipeline_protokoll.txt", "w") as log_file:
                    st.text("Starte EDA (Grafiken werden im Hintergrund berechnet)...")
                    subprocess.run(["python", "eda.py", input_csv_path], stdout=log_file, stderr=log_file, check=True)

                    st.text("Trainiere LSTM Modell (Pinball Loss)...")
                    subprocess.run(["python", "train_lstm.py"], stdout=log_file, stderr=log_file, check=True)

                    st.text("Trainiere RNN Modell (Pinball Loss)...")
                    subprocess.run(["python", "train_rnn.py"], stdout=log_file, stderr=log_file, check=True)

                # --- SCHRITT 4: ERGEBNISSE IN DEN OUTPUT-ORDNER VERSCHIEBEN ---
                os.makedirs(OUTPUT_DIR, exist_ok=True)

                # Die erweiterte Liste mit ALLEN Modellen, Skalierungsdateien, Grafiken und dem Protokoll
                artifacts = [
                    # Daten & Scaler
                    "Realisierte_Erzeugung_Cleaned.csv",
                    "cleaned_data.pkl",
                    "scaler_features.pkl",
                    "scaler_target.pkl",
                    "scaler_features_rnn.pkl",
                    "scaler_target_rnn.pkl",

                    # Modell-Gewichte
                    "best_prob_model.pth",
                    "final_probabilistic_lstm.pth",
                    "best_prob_model_rnn.pth",
                    "final_probabilistic_rnn.pth",

                    # Generierte EDA-Grafiken
                    "eda_tagesprofil.png",
                    "eda_energieerzeugung.png",
                    "eda_korrelations_heatmap.png",

                    # Generierte Modell-Grafiken
                    "lstm_lernkurve.png",
                    "lstm_vorhersage_intervall.png",
                    "rnn_lernkurve.png",
                    "rnn_vorhersage_intervall.png",

                    # Text-Protokoll der Konsolenausgaben
                    "pipeline_protokoll.txt"
                ]

                # Verschiebt jede existierende Datei in das gemappte PC-Verzeichnis
                for artifact in artifacts:
                    if os.path.exists(artifact):
                        shutil.move(artifact, os.path.join(OUTPUT_DIR, artifact))

                st.success(
                    "🎉 Pipeline erfolgreich beendet! Alle Grafiken, Modelle und das Text-Protokoll liegen im Output-Ordner.")

            except subprocess.CalledProcessError as e:
                st.error(f"Fehler während der Ausführung! Ein Skript ist abgebrochen.")
                st.info("Bitte prüfe die Datei 'pipeline_protokoll.txt' im Output-Ordner auf genaue Fehlermeldungen.")

                # Selbst wenn es crashed, wird versucht das Protokoll zu retten
                if os.path.exists("pipeline_protokoll.txt"):
                    shutil.move("pipeline_protokoll.txt", os.path.join(OUTPUT_DIR, "pipeline_protokoll.txt"))